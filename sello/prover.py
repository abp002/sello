"""Nivel 2 de verificación: el probador.

Z3 intenta demostrar cada `ensures` de una función a partir de su `requires` y de los
contratos de las funciones que llama. Verificación modular al estilo Dafny: cada función es
una función no interpretada más el axioma «requires → ensures» (con su llamada como patrón
de instanciación), el cuerpo se traduce a un término, una llamada recursiva usa el propio
contrato como hipótesis de inducción y hace falta una medida que decrezca en cada una.

Tres salidas:

  proven          todas las obligaciones son válidas y la recursión termina -> certificado de nivel 2
  counterexample  Z3 dio una entrada, el intérprete la ejecutó y falló de verdad -> el error de
                  siempre (E201, E300, E500), con esa entrada y `found_by: prover`
  unknown         timeout, contraejemplo que no reproduce (los contratos de las llamadas son más
                  débiles que sus cuerpos), sin medida de terminación... -> se queda en nivel 1

Un contraejemplo que el intérprete no confirma nunca se reporta: el probador no añade rechazos
nuevos, solo adelanta a compilación errores que ya existían para alguna entrada.

Lo que promete un certificado de nivel 2: si las funciones llamadas devuelven lo que dice su
contrato, la función termina y su resultado cumple `ensures` para toda entrada que cumpla
`requires`. Las llamadas se modelan por contrato, no por cuerpo: lo que ve `sello sig`.

Z3 no siempre atiende a su `timeout` (funciones recursivas sobre secuencias, 2026-09-06), y
un bucle de instanciación puede comerse la memoria o hacer que segfaultee. Por eso el probador
corre en un proceso hijo (`prove_program`), que escribe un veredicto por función según los
tiene; dentro, cada función usa su propio contexto y cada consulta corre en un hilo con reloj
de pared. Lo que no vuelve se queda en unknown; el compilador nunca cae por culpa de Z3.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import z3

from .builtins import NAMES as BUILTINS
from .checker import Checker
from .errors import SelloError
from .hash import _sccs, callees
from .interp import NONE, Interpreter, Some, fmt
from .nodes import (
    BOOL, INT, Binary, BoolLit, Call, Expr, Fn, If, IntLit, ListLit, Match, Name, NoneLit,
    PCons, PEmpty, PNone, PSome, PWild, Pattern, Program, Quant, SomeExpr, TAny, TBool, TextLit,
    TInt, TList, TOption, TText, Type, Unary, unify,
)
from .parser import parse
from .pretty import unparse, unparse_fn

QUERY_MS = 1000      # por consulta a Z3 (todas sus fases)
FN_MS = 3000         # por función
PROGRAM_MS = 30000   # por programa: lo que quede sin probar se queda en nivel 1
MAX_INT = 10 ** 6    # un contraejemplo con enteros mayores no se ejecuta
MAX_LEN = 64         # ni con listas más largas

PROVEN, COUNTEREXAMPLE, UNKNOWN = "proven", "counterexample", "unknown"

# Un bucle de instanciación puede comerse la memoria antes de que Z3 mire el reloj (un mutante
# `t -> xs` de max_subarray mató el proceso, 2026-09-06): con tope Z3 lanza una excepción.
z3.set_param("memory_max_size", 512)

CONTAINS = "exists"   # medido el 2026-09-06 sobre 44 funciones: exists 21, native 19, count 18
# Hechos que la teoría de secuencias de Z3 no deriva sola (medidos el 2026-09-06 sobre las 36
# soluciones: sin hechos 45/92 funciones probadas, cons 50, concat 47, cons+concat 49-50).
FACTS: frozenset = frozenset({"cons", "concat"})
# Fases de cada consulta: (solver, mbqi, ms). "s" es el solver sin patrones de instanciación
# explícitos; "p", el que los lleva (`xs[i]` en cada cuantificador). Medido el 2026-09-06 sobre
# las 36 soluciones: dos fases "s" 52/92 funciones probadas; con patrones bajan las pruebas por
# E-matching (41/92), y como fases extra no suben ni pruebas ni mutantes muertos (49/89 y 25/48
# en la medición completa frente a 49/89 y 27/48). Solo en el orden «patrones primero» MBQI
# encontró un bug real más (find_max_helper([4, 6], [], Some(4)) de most_frequent, haiku), a
# cambio de 4-7 pruebas menos: se queda documentado, no activado.
PHASES: tuple = (("s", False, 300), ("s", True, 700))


@dataclass
class Verdict:
    status: str
    reason: str = ""                  # para unknown
    error: SelloError | None = None   # para counterexample: el error real, ya ejecutado
    ms: int = 0

    def to_dict(self) -> dict:
        d: dict = {"level": 2 if self.status == PROVEN else 1}
        if self.status == UNKNOWN:
            d["unproven"] = self.reason
        return d


class Unsupported(Exception):
    """Construcción que el traductor no cubre. Sale como unknown, nunca como error."""


class Stuck(Exception):
    """Z3 no atendió ni al timeout ni a la interrupción: su contexto se abandona."""


_ABANDONED: list = []  # contextos con un hilo dentro: liberarlos segfaultea, se guardan hasta salir


class Budget:
    """Tiempo por programa y por función; cada consulta a Z3 recibe lo que quede, como
    mucho QUERY_MS. Los límites se leen al usarse para poder cambiarlos desde bench."""

    def __init__(self, program_ms: int | None = None) -> None:
        self.program_end = time.monotonic() + (PROGRAM_MS if program_ms is None else program_ms) / 1000
        self.fn_end = self.program_end

    def start_fn(self, fn_ms: int | None = None) -> None:
        self.fn_end = min(self.program_end, time.monotonic() + (FN_MS if fn_ms is None else fn_ms) / 1000)

    def query_ms(self) -> int:
        left = int((min(self.fn_end, self.program_end) - time.monotonic()) * 1000)
        return min(QUERY_MS, left)


def check(s: z3.Solver, ctx: z3.Context, ms: int, mbqi: bool) -> tuple[z3.CheckSatResult, z3.ModelRef | None]:
    """`s.check()` con reloj de pared y el modelo si lo hay (también el candidato de un unknown:
    el intérprete dirá si vale). Stuck si Z3 no vuelve ni tras interrumpirlo."""
    s.set("timeout", ms)
    s.set("smt.mbqi", mbqi)
    out: list = []

    def run() -> None:
        try:
            out.append(s.check())
        except z3.Z3Exception as z:  # sin memoria, por ejemplo
            out.append(z)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(ms / 1000 + 0.25)
    if t.is_alive():
        ctx.interrupt()
        t.join(1.0)
        if t.is_alive():
            _ABANDONED.append((ctx, s))
            raise Stuck()
        return z3.unknown, None
    if not out or isinstance(out[0], Exception):
        _ABANDONED.append((ctx, s))
        raise Stuck()  # el contexto ya no es de fiar
    r = out[0]
    if r == z3.unsat:
        return r, None
    try:
        return r, s.model()
    except z3.Z3Exception:
        return r, None


def decide(runs: list, ctx: z3.Context, budget: Budget, confirm_model) -> tuple[bool | None, object]:
    """¿Es válida una obligación? `runs` son fases (solver, camino, proposición, mbqi, ms) en
    orden: primero solo E-matching (rápido: decide la mayoría de las pruebas y da candidatos a
    contraejemplo), luego con MBQI. Devuelve (True probada | False refutada | None sin decidir,
    lo que devolvió confirm_model)."""
    open_ = None  # solver con la obligación ya apilada: fases seguidas sobre el mismo solver
    try:              # comparten el estado (lo aprendido en la primera sirve a la segunda)
        for s, path, prop, mbqi, cap in runs:
            ms = min(budget.query_ms(), cap)
            if ms <= 0:
                return None, None
            if s is not open_:
                if open_ is not None:
                    open_.pop()
                s.push()
                s.add(*path)
                s.add(z3.Not(prop))
                open_ = s
            r, model = check(s, ctx, ms, mbqi)  # si Z3 se atasca, Stuck: el contexto se abandona sin pop
            if r == z3.unsat:
                return True, None
            if model is not None:
                found = confirm_model(model)
                if found is not None:
                    return False, found
        return None, None
    except Stuck:
        open_ = None
        raise
    finally:
        if open_ is not None:
            open_.pop()


def concrete(t: Type, want: Type | None = None) -> Type:
    """Tipo sin `?`: se unifica con lo que espera el contexto y lo que quede sin decidir
    (el elemento de un `[]` suelto) es Int, que a la prueba le da igual."""
    u = unify(t, want) if want is not None else t
    if u is None:
        u = t
    if isinstance(u, TAny):
        return INT
    if isinstance(u, TList):
        return TList(concrete(u.elem))
    if isinstance(u, TOption):
        return TOption(concrete(u.elem))
    return u


def floordiv(a: z3.ArithRef, b: z3.ArithRef) -> z3.ArithRef:
    """`/` de Sello redondea hacia abajo como Python; el `div` de Z3 es euclídeo (resto no
    negativo) y difiere con divisor negativo: a // b == (-a) // (-b) lo arregla."""
    return z3.If(b > 0, a / b, (-a) / (-b))


# ---------- entorno y obligaciones ----------

@dataclass
class Env:
    vals: dict[str, z3.ExprRef] = field(default_factory=dict)
    types: dict[str, Type] = field(default_factory=dict)

    def bind(self, name: str, v: z3.ExprRef, t: Type) -> Env:
        return Env({**self.vals, name: v}, {**self.types, name: t})


@dataclass
class Obligation:
    path: list            # condiciones de camino bajo las que se evalúa
    prop: z3.BoolRef      # lo que tiene que valer
    code: str             # E500 | E300 | E201
    what: str             # para el motivo de un unknown


@dataclass
class Binder:
    """Un cuantificador abierto mientras se traduce su cuerpo: variable índice, guarda y
    cuántas condiciones del camino estaban ya fuera de él."""
    var: z3.ArithRef
    guard: z3.BoolRef
    depth: int


class Translator:
    def __init__(self, program: Program, fn: Fn, ctx: z3.Context, patterns: bool = False,
                 shared: Translator | None = None) -> None:
        self.ctx = ctx
        self.patterns = patterns
        self.fns = {f.name: f for f in program.fns}
        self.fn = fn
        self.checker = Checker(program)
        self.checker.fns = self.fns
        self.checker.in_contract = True  # el programa ya pasó el checker: aquí todo vale
        # Sorts, funciones recursivas y símbolos se comparten entre los dos traductores de una
        # función: un datatype o una RecFunction definidos dos veces en el mismo contexto no son
        # el mismo.
        self.options: dict[str, z3.DatatypeSortRef] = shared.options if shared else {}
        self.counts: dict[str, z3.FuncDeclRef] = shared.counts if shared else {}
        self.ufs: dict[str, z3.FuncDeclRef | z3.ExprRef] = shared.ufs if shared else {}
        self.n = shared.n if shared else 0
        self.obligations: list[Obligation] = []
        self.self_calls: list[tuple[list, list]] = []  # (camino, args) de cada llamada recursiva del cuerpo
        self.facts: list[z3.BoolRef] = []  # identidades de la teoría que ayudan a instanciar
        self.binders: list[Binder] = []
        self.collect = True   # False mientras se traducen axiomas de otras funciones
        self.in_body = False

    def fresh(self, name: str) -> str:
        self.n += 1
        return f"{name}!{self.n}"

    def true(self) -> z3.BoolRef:
        return z3.BoolVal(True, self.ctx)

    def conj(self, xs: list) -> z3.BoolRef:
        return self.true() if not xs else (xs[0] if len(xs) == 1 else z3.And(*xs))

    def int(self, v: int) -> z3.ArithRef:
        return z3.IntVal(v, self.ctx)

    def type_at(self, e: Expr, env: Env, want: Type | None) -> Type:
        return concrete(self.checker.type_of(e, env.types, self.fn), want)

    # ---- tipos -> sorts ----
    def sort(self, t: Type) -> z3.SortRef:
        if isinstance(t, TInt):
            return z3.IntSort(self.ctx)
        if isinstance(t, TBool):
            return z3.BoolSort(self.ctx)
        if isinstance(t, TText):
            return z3.StringSort(self.ctx)
        if isinstance(t, TList):
            return z3.SeqSort(self.sort(t.elem))
        if isinstance(t, TOption):
            key = str(t)
            if key not in self.options:
                dt = z3.Datatype(key, self.ctx)
                dt.declare("None")
                dt.declare("Some", ("val", self.sort(t.elem)))
                self.options[key] = dt.create()
            return self.options[key]
        raise Unsupported(f"type {t}")

    def count_fn(self, elem: z3.SortRef) -> z3.FuncDeclRef:
        """`count(xs, x)` como función recursiva de Z3 sobre la secuencia."""
        key = str(elem)
        if key not in self.counts:
            seq = z3.SeqSort(elem)
            f = z3.RecFunction(f"count[{key}]", seq, elem, z3.IntSort(self.ctx))
            s, x = z3.Const(f"s[{key}]", seq), z3.Const(f"x[{key}]", elem)
            z3.RecAddDefinition(f, [s, x], z3.If(
                z3.Length(s) == 0, self.int(0),
                z3.If(s[0] == x, self.int(1), self.int(0)) + f(z3.SubSeq(s, self.int(1), z3.Length(s) - 1), x)))
            self.counts[key] = f
        return self.counts[key]

    # ---- funciones como símbolos ----
    def uf(self, g: Fn):
        if g.name not in self.ufs:
            if g.params:
                self.ufs[g.name] = z3.Function(f"fn!{g.name}", *[self.sort(p.type) for p in g.params], self.sort(g.ret))
            else:
                self.ufs[g.name] = z3.Const(f"fn!{g.name}", self.sort(g.ret))
        return self.ufs[g.name]

    def apply(self, g: Fn, args: list) -> z3.ExprRef:
        f = self.uf(g)
        return f(*args) if g.params else f

    def axiom(self, g: Fn) -> z3.BoolRef:
        """`forall params: requires -> ensures[result := g(params)]`, instanciado solo cuando
        aparece una llamada `g(...)`: es lo que un llamador puede asumir de `sello sig`."""
        ps = [z3.Const(self.fresh(p.name), self.sort(p.type)) for p in g.params]
        env = Env({p.name: c for p, c in zip(g.params, ps)}, {p.name: p.type for p in g.params})
        res = self.apply(g, ps)
        self.collect = False
        try:
            req = [self.expr(r, env, [], BOOL) for r in g.requires]
            ens = [self.expr(c, env.bind("result", res, g.ret), [], BOOL) for c in g.ensures]
        finally:
            self.collect = True
        body = z3.Implies(self.conj(req), self.conj(ens))
        return z3.ForAll(ps, body, patterns=[res]) if ps else body

    # ---- obligaciones ----
    def obligate(self, path: list, prop: z3.BoolRef, code: str, what: str) -> None:
        if not self.collect:
            return
        if self.binders:
            # dentro de un cuantificador la obligación vale para todo índice que cumpla las guardas
            # y las condiciones de camino abiertas dentro de él
            d = self.binders[0].depth
            inner = [b.guard for b in self.binders] + list(path[d:])
            prop = z3.ForAll([b.var for b in self.binders], z3.Implies(self.conj(inner), prop))
            path = path[:d]
        self.obligations.append(Obligation(list(path), prop, code, what))

    # ---- expresiones ----
    def expr(self, e: Expr, env: Env, path: list, want: Type | None = None) -> z3.ExprRef:
        if isinstance(e, IntLit):
            return self.int(e.value)
        if isinstance(e, BoolLit):
            return z3.BoolVal(e.value, self.ctx)
        if isinstance(e, TextLit):
            return z3.StringVal(e.value, self.ctx)
        if isinstance(e, NoneLit):
            return self.sort(self.type_at(e, env, want)).constructor(0)()
        if isinstance(e, SomeExpr):
            t = self.type_at(e, env, want)
            assert isinstance(t, TOption)
            return self.sort(t).constructor(1)(self.expr(e.inner, env, path, t.elem))
        if isinstance(e, ListLit):
            t = self.type_at(e, env, want)
            assert isinstance(t, TList)
            items = [z3.Unit(self.expr(x, env, path, t.elem)) for x in e.items]
            if not items:
                return z3.Empty(self.sort(t))
            return items[0] if len(items) == 1 else z3.Concat(*items)
        if isinstance(e, Name):
            return env.vals[e.id]
        if isinstance(e, Call):
            return self.builtin(e, env, path) if e.name in BUILTINS else self.call(e, env, path)
        if isinstance(e, Unary):
            v = self.expr(e.operand, env, path, BOOL if e.op == "not" else INT)
            return z3.Not(v) if e.op == "not" else -v
        if isinstance(e, Binary):
            return self.binary(e, env, path, want)
        if isinstance(e, If):
            c = self.expr(e.cond, env, path, BOOL)
            t = self.type_at(e, env, want)
            return z3.If(c, self.expr(e.then, env, path + [c], t),
                         self.expr(e.otherwise, env, path + [z3.Not(c)], t))
        if isinstance(e, Match):
            return self.match(e, env, path, want)
        if isinstance(e, Quant):
            return self.quant(e, env, path)
        raise Unsupported(f"node {type(e).__name__}")

    def binary(self, e: Binary, env: Env, path: list, want: Type | None) -> z3.ExprRef:
        op = e.op
        if op in ("and", "or"):
            l = self.expr(e.left, env, path, BOOL)
            r = self.expr(e.right, env, path + [l if op == "and" else z3.Not(l)], BOOL)
            return z3.And(l, r) if op == "and" else z3.Or(l, r)
        if op in ("+", "-", "*", "/", "%", "<", "<=", ">", ">="):
            l = self.expr(e.left, env, path, INT)
            r = self.expr(e.right, env, path, INT)
            if op in ("/", "%"):
                self.obligate(path, r != 0, "E500", f"division by zero in `{unparse(e)}`")
                q = floordiv(l, r)
                return q if op == "/" else l - r * q
            return {"+": lambda: l + r, "-": lambda: l - r, "*": lambda: l * r, "<": lambda: l < r,
                    "<=": lambda: l <= r, ">": lambda: l > r, ">=": lambda: l >= r}[op]()
        if op in ("==", "!="):
            t = concrete(unify(self.checker.type_of(e.left, env.types, self.fn),
                               self.checker.type_of(e.right, env.types, self.fn)) or INT)
            l = self.expr(e.left, env, path, t)
            r = self.expr(e.right, env, path, t)
            return l == r if op == "==" else l != r
        if op == "++":
            t = self.type_at(e, env, want)
            a, b = self.expr(e.left, env, path, t), self.expr(e.right, env, path, t)
            ab = z3.Concat(a, b)
            if isinstance(t, TList):
                self.facts_concat(a, b, ab)
            return ab
        raise Unsupported(f"operator {op}")

    def call(self, e: Call, env: Env, path: list) -> z3.ExprRef:
        g = self.fns[e.name]
        args = [self.expr(a, env, path, p.type) for a, p in zip(e.args, g.params)]
        genv = Env({p.name: a for p, a in zip(g.params, args)}, {p.name: p.type for p in g.params})
        prev: list = []
        for r in g.requires:
            prop = self.expr(r, genv, path + prev, BOOL)
            self.obligate(path + prev, prop, "E300",
                          f"`{unparse(e)}` may violate `requires {unparse(r)}` of `{g.name}`")
            prev.append(prop)
        if g is self.fn and self.in_body and self.collect and not self.binders:
            self.self_calls.append((list(path), args))
        return self.apply(g, args)

    def builtin(self, e: Call, env: Env, path: list) -> z3.ExprRef:
        st = self.type_at(e.args[0], env, None)
        assert isinstance(st, TList)
        xs = self.expr(e.args[0], env, path, st)
        if e.name == "len":
            return z3.Length(xs)
        if e.name in ("count", "contains"):
            x = self.expr(e.args[1], env, path, st.elem)
            if e.name == "contains":
                if CONTAINS == "count":
                    return self.count_fn(self.sort(st.elem))(xs, x) > 0
                if CONTAINS == "exists":
                    i = z3.Int(self.fresh("i"), self.ctx)
                    return z3.Exists([i], z3.And(i >= 0, i < z3.Length(xs), xs[i] == x), **self.pat(xs[i]))
                return z3.Contains(xs, z3.Unit(x))
            return self.count_fn(self.sort(st.elem))(xs, x)
        i = z3.Int(self.fresh("i"), self.ctx)
        if e.name == "sorted":
            return z3.ForAll([i], z3.Implies(z3.And(i >= 0, i + 1 < z3.Length(xs)), xs[i] <= xs[i + 1]),
                             **self.pat(xs[i]))
        if e.name == "distinct":
            j = z3.Int(self.fresh("j"), self.ctx)
            return z3.ForAll([i, j], z3.Implies(z3.And(i >= 0, i < j, j < z3.Length(xs)), xs[i] != xs[j]),
                             **self.pat(z3.MultiPattern(xs[i], xs[j])))
        raise Unsupported(f"builtin {e.name}")

    def pat(self, p) -> dict:
        """`patterns=` para un cuantificador generado, en el traductor con patrones."""
        return {"patterns": [p]} if self.patterns else {}

    def quant(self, e: Quant, env: Env, path: list) -> z3.ExprRef:
        st = self.type_at(e.subject, env, None)
        assert isinstance(st, TList)
        xs = self.expr(e.subject, env, path, st)
        i = z3.Int(self.fresh("i"), self.ctx)
        guard = z3.And(i >= 0, i < z3.Length(xs))
        self.binders.append(Binder(i, guard, len(path)))
        try:
            body = self.expr(e.body, env.bind(e.var, xs[i], st.elem), path, BOOL)
        finally:
            self.binders.pop()
        if e.kind == "forall":
            return z3.ForAll([i], z3.Implies(guard, body), **self.pat(xs[i]))
        return z3.Exists([i], z3.And(guard, body), **self.pat(xs[i]))

    def match(self, e: Match, env: Env, path: list, want: Type | None) -> z3.ExprRef:
        st = self.type_at(e.subject, env, None)
        s = self.expr(e.subject, env, path, st)
        t = self.type_at(e, env, want)
        arms: list[tuple[z3.BoolRef, z3.ExprRef]] = []
        negs: list = []
        for arm in e.arms:
            cond, binds = self.pattern(arm.pattern, s, st)
            env2 = env
            for name, (v, vt) in binds.items():
                env2 = env2.bind(name, v, vt)
            arms.append((cond, self.expr(arm.body, env2, path + negs + [cond], t)))
            negs.append(z3.Not(cond))
        out = arms[-1][1]  # el checker garantiza que el último brazo cubre lo que queda (E404)
        for cond, body in reversed(arms[:-1]):
            out = z3.If(cond, body, out)
        return out

    def pattern(self, p: Pattern, s: z3.ExprRef, st: Type) -> tuple[z3.BoolRef, dict]:
        if isinstance(p, PEmpty):
            return z3.Length(s) == 0, {}
        if isinstance(p, PCons):
            assert isinstance(st, TList)
            head, tail = s[0], z3.SubSeq(s, self.int(1), z3.Length(s) - 1)
            # `s == [h] ++ t` es un teorema de la teoría, pero dicho así Z3 lo usa para partir
            # los cuantificadores sobre `s` en el elemento y la cola (la forma de la inducción).
            # Probado el 2026-09-06 con h y t como constantes nuevas en vez de términos: no ayuda.
            if self.collect:
                self.facts.append(z3.Implies(z3.Length(s) > 0, s == z3.Concat(z3.Unit(head), tail)))
                self.facts_cons(s, tail)
            binds = {}
            if p.head != "_":
                binds[p.head] = (head, st.elem)
            if p.tail != "_":
                binds[p.tail] = (tail, st)
            return z3.Length(s) > 0, binds
        if isinstance(p, (PNone, PSome)):
            assert isinstance(st, TOption)
            dt = self.sort(st)
            if isinstance(p, PNone):
                return dt.recognizer(0)(s), {}
            return dt.recognizer(1)(s), {p.name: (dt.accessor(1, 0)(s), st.elem)}
        if isinstance(p, PWild):
            return self.true(), ({p.name: (s, st)} if p.name else {})
        raise Unsupported(f"pattern {type(p).__name__}")

    # ---- hechos derivados ----
    def facts_cons(self, s: z3.ExprRef, tail: z3.ExprRef) -> None:
        """Lo que relaciona `s` con su cola elemento a elemento, con patrones sobre el
        índice: así un testigo `s[i]` de un cuantificador negado alcanza `t[i - 1]`, donde
        vive la hipótesis de inducción, y al revés."""
        if "cons" not in FACTS or self.binders:
            return
        n = z3.Length(s)
        i = z3.Int(self.fresh("i"), self.ctx)
        self.facts.append(z3.Implies(n > 0, z3.Length(tail) == n - 1))
        self.facts.append(z3.ForAll([i], z3.Implies(z3.And(n > 0, i >= 0, i < z3.Length(tail)), tail[i] == s[i + 1]),
                                    **self.pat(tail[i])))
        self.facts.append(z3.ForAll([i], z3.Implies(z3.And(i >= 1, i < n), s[i] == tail[i - 1]),
                                    **self.pat(s[i])))

    def facts_concat(self, a: z3.ExprRef, b: z3.ExprRef, ab: z3.ExprRef) -> None:
        """Longitud e índices de `a ++ b` por tramos."""
        if "concat" not in FACTS or not self.collect or self.binders:
            return
        la, lb = z3.Length(a), z3.Length(b)
        i = z3.Int(self.fresh("i"), self.ctx)
        self.facts.append(z3.Length(ab) == la + lb)
        self.facts.append(z3.ForAll([i], z3.Implies(z3.And(i >= 0, i < la), ab[i] == a[i]), **self.pat(ab[i])))
        self.facts.append(z3.ForAll([i], z3.Implies(z3.And(i >= la, i < la + lb), ab[i] == b[i - la]), **self.pat(ab[i])))
        self.facts.append(z3.ForAll([i], z3.Implies(z3.And(i >= 0, i < lb), ab[la + i] == b[i]), **self.pat(b[i])))

    # ---- terminación ----
    def terminates(self, s: z3.Solver, params: list, budget: Budget) -> bool | None:
        """Alguna medida (un Int, la longitud de una lista o la diferencia de dos Int) decrece
        y no es negativa en todas las llamadas recursivas. None si se acabó el tiempo."""
        cands: list[tuple[z3.ArithRef, object]] = []
        ints = [i for i, p in enumerate(self.fn.params) if isinstance(p.type, TInt)]
        for i, p in enumerate(self.fn.params):
            if isinstance(p.type, TInt):
                cands.append((params[i], lambda args, i=i: args[i]))
            elif isinstance(p.type, TList):
                cands.append((z3.Length(params[i]), lambda args, i=i: z3.Length(args[i])))
        for i in ints:
            for j in ints:
                if i != j:
                    cands.append((params[j] - params[i], lambda args, i=i, j=j: args[j] - args[i]))
        for measure, of in cands:
            ok = True
            for path, args in self.self_calls:
                ms = budget.query_ms()
                if ms <= 0:
                    return None
                prop = z3.And(of(args) < measure, measure >= 0)
                valid, _ = decide([(s, path, prop, False, 300), (s, path, prop, True, 700)], self.ctx, budget, lambda m: None)
                if valid is None and budget.query_ms() <= 0:
                    return None
                if not valid:
                    ok = False
                    break
            if ok:
                return True
        return False


# ---------- del modelo al intérprete ----------

def value(v: z3.ExprRef, t: Type) -> object:
    """Un valor del modelo de Z3 como valor del intérprete. Unsupported si no es concreto."""
    if isinstance(t, TInt):
        if z3.is_int_value(v):
            return v.as_long()
    elif isinstance(t, TBool):
        if z3.is_true(v):
            return True
        if z3.is_false(v):
            return False
    elif isinstance(t, TText):
        if z3.is_string_value(v):
            return v.as_string()
    elif isinstance(t, TList):
        name = v.decl().name()
        if name == "seq.empty":
            return []
        if name == "seq.unit":
            return [value(v.arg(0), t.elem)]
        if name == "seq.++":
            out: list = []
            for k in range(v.num_args()):
                out.extend(value(v.arg(k), t))
            return out
        if name in ("str.++", "seq.extract"):
            return value(z3.simplify(v), t)
    elif isinstance(t, TOption):
        name = v.decl().name()
        if name == "None":
            return NONE
        if name == "Some":
            return Some(value(v.arg(0), t.elem))
    raise Unsupported(f"model value {v}")


def too_big(v: object) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return abs(v) > MAX_INT
    if isinstance(v, list):
        return len(v) > MAX_LEN or any(too_big(x) for x in v)
    if isinstance(v, Some):
        return too_big(v.value)
    return False


def confirm(program: Program, fn: Fn, params: list, model: z3.ModelRef,
            interp: Interpreter | None) -> SelloError | None:
    """Ejecuta la entrada del modelo. Devuelve el error real o None si no reproduce."""
    try:
        args = [value(model.eval(c, model_completion=True), p.type) for p, c in zip(fn.params, params)]
    except (Unsupported, z3.Z3Exception):
        return None
    if any(too_big(a) for a in args):
        return None
    interp = interp or Interpreter(program)
    shown = f"{fn.name}(" + ", ".join(fmt(a) for a in args) + ")"
    try:
        interp.call(fn.name, args)
    except SelloError as e:
        if e.code == "E300" and e.extra.get("call") == shown and e.function == fn.name:
            return None  # el modelo no cumple el requires de verdad (cuantificadores): espurio
        if e.code == "E500" and "recursion" in e.detail:
            return None  # una entrada grande, no un bug demostrado
        e.extra["found_by"] = "prover"
        e.extra["input"] = shown
        e.detail = f"{e.detail} (input found by the prover: {shown}; the examples do not cover it)"
        return e
    except RecursionError:
        return None
    return None


# ---------- la prueba ----------

def _mutual(program: Program, fn: Fn) -> bool:
    graph = {f.name: callees(f) for f in program.fns}
    return any(fn.name in comp and len(comp) > 1 for comp in _sccs(graph))


def _setup(tr: Translator, fn: Fn, env: Env) -> z3.Solver:
    """Traduce requires, cuerpo y ensures (recogiendo obligaciones) y monta el solver con los
    axiomas de las funciones que aparecen, el requires y los hechos."""
    s = z3.Solver(ctx=tr.ctx)
    req: list = []
    for r in fn.requires:
        req.append(tr.expr(r, env, req, BOOL))
    tr.in_body = True
    body = tr.expr(fn.body, env, [], fn.ret)
    tr.in_body = False
    renv = env.bind("result", body, fn.ret)
    prev: list = []
    for c in fn.ensures:
        prop = tr.expr(c, renv, prev, BOOL)
        tr.obligate(prev, prop, "E201", f"`ensures {unparse(c)}`")
        prev.append(prop)
    # Solo los axiomas de las funciones que aparecen (y de las que aparecen en ellos): un
    # cuantificador de más cambia la estrategia de Z3 y `div` pasaba de 10 ms a unknown.
    seen: set[str] = set()
    while set(tr.ufs) - seen:
        name = sorted(set(tr.ufs) - seen)[0]
        seen.add(name)
        try:
            s.add(tr.axiom(tr.fns[name]))
        except Unsupported:
            continue  # sin axioma la función queda libre: más débil, nunca falso
    s.add(*req)
    s.add(*tr.facts)
    return s


def prove(program: Program, fn: Fn, interp: Interpreter | None = None,
          budget: Budget | None = None) -> Verdict:
    t0 = time.monotonic()
    budget = budget or Budget()
    budget.start_fn()

    def done(status: str, reason: str = "", error: SelloError | None = None) -> Verdict:
        return Verdict(status, reason, error, int((time.monotonic() - t0) * 1000))

    ctx = z3.Context()
    try:
        tr = Translator(program, fn, ctx)
        params = [z3.Const(p.name, tr.sort(p.type)) for p in fn.params]
        env = Env({p.name: c for p, c in zip(fn.params, params)}, {p.name: p.type for p in fn.params})
        s = _setup(tr, fn, env)
        sp, trp = s, tr
        if any(kind == "p" for kind, _, _ in PHASES):
            trp = Translator(program, fn, ctx, patterns=True, shared=tr)
            sp = _setup(trp, fn, env)
            if len(trp.obligations) != len(tr.obligations):  # no debería pasar: mismo recorrido
                sp, trp = s, tr
    except Unsupported as u:
        return done(UNKNOWN, f"unsupported: {u}")
    except z3.Z3Exception as z:
        return done(UNKNOWN, f"z3: {str(z).strip()[:120]}")

    reason = ""
    try:
        for ob, obp in zip(tr.obligations, trp.obligations):
            if budget.query_ms() <= 0:
                return done(UNKNOWN, reason or "timeout")
            runs = [((sp, obp) if kind == "p" else (s, ob)) + (mbqi, cap) for kind, mbqi, cap in PHASES]
            valid, err = decide([(sv, o.path, o.prop, mbqi, cap) for sv, o, mbqi, cap in runs], ctx, budget,
                                lambda m: confirm(program, fn, params, m, interp))
            if valid is False:
                return done(COUNTEREXAMPLE, error=err)
            if valid is None:
                reason = reason or f"undecided: {ob.what}"
        if reason:
            return done(UNKNOWN, reason)
        if _mutual(program, fn):
            return done(UNKNOWN, "mutual recursion: termination not checked")
        if tr.self_calls:
            t = tr.terminates(s, params, budget)
            if t is None:
                return done(UNKNOWN, "timeout")
            if not t:
                return done(UNKNOWN, "termination: no argument decreases at every recursive call")
    except Stuck:
        return done(UNKNOWN, reason or "timeout: the solver did not answer")
    except z3.Z3Exception as z:
        return done(UNKNOWN, f"z3: {str(z).strip()[:120]}")
    return done(PROVEN)


def prove_here(program: Program, interp: Interpreter | None = None,
               budget: Budget | None = None) -> dict[str, Verdict]:
    """Cada función del programa, en orden, en este proceso. Para en el primer contraejemplo."""
    budget = budget or Budget()
    interp = interp or Interpreter(program)
    out: dict[str, Verdict] = {}
    for fn in program.fns:
        v = prove(program, fn, interp, budget)
        out[fn.name] = v
        if v.error is not None:
            break
    return out


def _error_dict(e: SelloError) -> dict:
    return {"code": e.code, "detail": e.detail, "line": e.line, "col": e.col,
            "function": e.function, "extra": e.extra}


def first_error(verdicts: dict[str, Verdict]) -> SelloError | None:
    return next((v.error for v in verdicts.values() if v.error is not None), None)


def prove_program(program: Program, program_ms: int | None = None) -> dict[str, Verdict]:
    """El probador en un proceso hijo, con reloj de pared. Lo que el hijo no llegue a decir
    (cuelgue, segfault, sin memoria) queda en unknown. Un contraejemplo real viene en el
    veredicto de su función y el hijo para ahí: lo que sigue queda sin intentar."""
    ms = PROGRAM_MS if program_ms is None else program_ms
    src = "\n\n".join(unparse_fn(f) for f in program.fns)
    cmd = [sys.executable, "-m", "sello.prover", "--program-ms", str(ms), "--fn-ms", str(FN_MS),
           "--query-ms", str(QUERY_MS)]
    try:
        r = subprocess.run(cmd, input=src, capture_output=True, text=True, timeout=ms / 1000 + 5,
                           cwd=str(Path(__file__).resolve().parents[1]))
        out = r.stdout
    except subprocess.TimeoutExpired as t:
        out = t.stdout.decode() if isinstance(t.stdout, bytes) else (t.stdout or "")
    verdicts: dict[str, Verdict] = {}
    fatal = ""
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "fatal" in d:
            fatal = d["fatal"]
            continue
        err = None
        if d.get("error"):
            e = d["error"]
            err = SelloError(e["code"], e["detail"], e["line"], e["col"], e["function"], e["extra"])
        verdicts[d["name"]] = Verdict(d["status"], d["reason"], err, d["ms"])
    failed = first_error(verdicts) is not None
    for fn in program.fns:
        reason = "not attempted: an earlier function failed" if failed else (fatal or "timeout: the prover did not answer")
        verdicts.setdefault(fn.name, Verdict(UNKNOWN, reason))
    return {fn.name: verdicts[fn.name] for fn in program.fns}


def _main(argv: list[str]) -> int:
    """El proceso hijo: programa por stdin, un veredicto JSON por línea según los tiene."""
    import argparse
    import os
    global PROGRAM_MS, FN_MS, QUERY_MS, FACTS, PHASES
    if "SELLO_MS" in os.environ:  # experimento: "query,fn"
        QUERY_MS, FN_MS = (int(x) for x in os.environ["SELLO_MS"].split(","))
    if "SELLO_FACTS" in os.environ:  # experimento
        FACTS = frozenset(x for x in os.environ["SELLO_FACTS"].split(",") if x)
    if "SELLO_PHASES" in os.environ:  # experimento: p. ej. "s0:300,s1:700,p1:700"
        PHASES = tuple((x[0], x[1] == "1", int(x.split(":")[1])) for x in os.environ["SELLO_PHASES"].split(","))
    ap = argparse.ArgumentParser()
    ap.add_argument("--program-ms", type=int, default=PROGRAM_MS)
    ap.add_argument("--fn-ms", type=int, default=FN_MS)
    ap.add_argument("--query-ms", type=int, default=QUERY_MS)
    a = ap.parse_args(argv)
    PROGRAM_MS, FN_MS, QUERY_MS = a.program_ms, a.fn_ms, a.query_ms
    try:
        program = parse(sys.stdin.read())
        Checker(program).check()
    except SelloError as e:
        print(json.dumps({"fatal": f"prover could not load the program: {e.code} {e.detail}"}), flush=True)
        return 1
    interp = Interpreter(program)
    budget = Budget()
    for fn in program.fns:
        v = prove(program, fn, interp, budget)
        print(json.dumps({"name": fn.name, "status": v.status, "reason": v.reason, "ms": v.ms,
                          "error": None if v.error is None else _error_dict(v.error)}, ensure_ascii=False),
              flush=True)
        if v.error is not None:
            break
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
