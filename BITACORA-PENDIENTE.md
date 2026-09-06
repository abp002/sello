# Bitácora pendiente de pasar al vault

Sesiones hechas desde Claude Code, sin acceso al vault de Obsidian. Cada sección es una
entrada de bitácora con fecha absoluta (qué se hizo, qué se midió, qué falló) y, aparte,
las decisiones tomadas con el título como afirmación, para copiarlas como notas propias en
`Proyectos/Lenguaje para IA/`. Cuando algo pase al vault, se borra de aquí. Este fichero
no es documentación del proyecto: es un buzón.

---

## 2026-09-06 · Fase 3 arranca: el nivel 2 (el probador)

Rama `claude/sello-work-bgacgo`, commit `29b928c`.

### Qué se hizo

- `sello/prover.py`: Z3 intenta demostrar cada `ensures` a partir de `requires` y de los
  contratos de las funciones llamadas. Verificación modular al estilo Dafny: cada función es
  una función no interpretada más el axioma `forall params: requires -> ensures[result :=
  f(params)]`, instanciado solo cuando aparece una llamada `f(...)` (patrón explícito). El
  cuerpo se traduce a un término (`if` → `If`, `match` → `If` encadenado con recognizers y
  accessors, `[h, ..t]` → `s[0]` y `extract(s, 1, len-1)` más el hecho `s == [h] ++ t`).
  Una llamada recursiva usa el propio contrato como hipótesis de inducción; para el
  certificado hace falta además una medida que decrezca en todas las llamadas recursivas
  (un `Int`, la longitud de una lista o la diferencia de dos `Int`; se prueba que decrece y
  no es negativa). Recursión mutua: sin terminación, se queda en nivel 1.
- Tipos: `Int`/`Bool`/`Text` nativos, `List[T]` como `Seq` de Z3, `Option[T]` como datatype.
  `/` y `%` con la semántica de Python (`a // b == (-a) // (-b)` arregla el `div` euclídeo
  de Z3; test de propiedad con hypothesis). Vocabulario: `len` = `Length`, `contains` =
  `exists i`, `count` = función recursiva de Z3, `sorted`/`distinct`/`forall`/`exists` =
  cuantificadores sobre índices.
- Obligaciones: `b != 0` en cada división (E500), el `requires` del llamado en cada llamada
  (E300), cada cláusula `ensures` bajo las anteriores (E201). Dentro de un cuantificador la
  obligación se cuantifica con las guardas. Cada consulta en dos fases: solo E-matching
  (300 ms, decide casi todas las pruebas y da modelos candidatos) y luego con MBQI lo que
  quede del presupuesto (1 s por consulta, 3 s por función, 30 s por programa).
- Un contraejemplo (modelo de Z3, también el candidato de un `unknown`) solo se reporta si el
  intérprete lo reproduce: se extraen los valores del modelo, se llama a la función y el
  error real (E201/E300/E500) sale con `found_by: prover` e `input`. Si no reproduce
  (contratos de las llamadas más débiles que sus cuerpos, cuantificadores), unknown y nivel 1.
- Integración: `sello check` (campos `level`, `unproven`, `proven`), `sello test` (el juez
  débil del harness lo incluye), `sello run`; flag `--no-prover`. Almacén: certificado de
  nivel 2 cuando prueba, fallido con el error si encuentra contraejemplo. `verify` igual.
- `bench/probador.py` (sin modelo): sobre soluciones aceptadas de corridas del juez y sobre
  mutantes de corridas de mutantes, vía `sello check` en proceso aparte. `mutantes.py`
  distingue la muerte «por el probador» (señal `Exxx/prover`).
- Spec: tres frases sobre el nivel 2 en §4, el certificado en §5, la salida de `check` en §7.
  Tests: `tests/test_prover.py` (15), `tests/test_probador.py` (3), almacén (3 más).
- Bug real en `ejemplos/basicos.sello`, presente desde el arranque: `div` decía
  `ensures result * b <= a`, falso con divisor negativo (`div(-85, -2) = 42`, `42 * -2 = -84
  > -85`). Lo encontró el probador en su primera ejecución. Corregido con dos cláusulas por
  signo del divisor.

### Qué se midió

`bench/resultados/probador-2026-09-06-1135.md`, sobre las 36 soluciones aceptadas del 5 de
septiembre (`juez-2026-09-05-0015-{haiku,sonnet}`, `juez-2026-09-05-1920-haiku-contrato`) y
los mutantes de `mutantes-2026-09-05-1931`.

| | sello·haiku | sello·sonnet | sello_contrato·haiku |
|---|---|---|---|
| funciones en nivel 2 | 11/23 (48 %) | 19/35 (54 %) | 16/31 (52 %) |
| principal en nivel 2 | 7/12 | 7/12 | 4/12 |
| · Z3 no decide | 9 | 13 | 13 |
| · sin tiempo | 1 | 3 | 2 |
| · recursión mutua | 2 | 0 | 0 |
| · sin medida de terminación | 0 | 0 | 0 |
| bugs reales en soluciones aceptadas | 0 | 0 | 1 |
| mutantes que llegaban a producción | 24 | 2 | 22 |
| **matados por el probador / llegaban** | **15/24 (62 %)** | **1/2** | **9/22 (41 %)** |
| · de los silenciosos | 11/19 (58 %) | - | - |
| · de los cazados en producción | 4/5 | 0/1 | 7/19 |
| · de los ruidosos | - | 1/1 | 2/3 |
| equivalentes en el dominio matados (bug fuera del oráculo) | 3/32 | 6/51 | 6/35 |
| tiempo (s), 4 workers | 18 + 37 | 37 + 171 | 28 + 153 |

- Total: 46/89 funciones en nivel 2 (52 %); 25/48 mutantes que llegaban muertos en
  compilación (52 %); 15/118 equivalentes con bug fuera del oráculo; 34 muertes E201, 6 E300,
  0 E500.
- El bug real: `int_sqrt` de haiku con el contrato de sonnet (aceptada por el juez débil y
  por 345 llamadas del oráculo). El helper `search(n, low, high)` con `requires low <= high`
  devuelve `low` cuando `low == high`; `search(0, 1, 1) = 1` viola `result * result <= n`.
  El `requires` del helper era demasiado débil (faltaba `low * low <= n`); desde `int_sqrt`
  no se alcanza, pero el helper es una función certificada por derecho propio y su
  certificado mentía.
- Lo que Z3 no decide es casi siempre un cuantificador sobre secuencias: `forall x in xs:
  x <= result` (max_of), `forall y in result: contains(xs, y)` (drop/take), `sorted(result)`
  (merge_sorted), `distinct(result)` (dedupe), y el `requires contains(xs, x)` de la llamada
  recursiva de index_of/remove_one. Todo es de primer orden dada la hipótesis de inducción;
  es la teoría de secuencias de Z3 con cuantificadores la que no llega.
- Los «silenciosos» que el probador mata no contradicen la definición: eran silenciosos en
  los casos del oráculo; el probador encuentra otra entrada donde el mismo `ensures` sí los
  rechaza. Es cobertura, no fuerza del contrato.

### Qué falló

- Z3 no atiende a su `timeout` en algunas consultas con funciones recursivas sobre
  secuencias (se colgó en `find_max_helper` de most_frequent, haiku). Primero hilo con reloj
  de pared e `interrupt()`; luego un mutante `t -> xs` de max_subarray (sonnet) se comió la
  memoria y el kernel mató el proceso (137); con tope de memoria (`memory_max_size`) Z3
  segfaulteó (139) al liberar un contexto con el hilo dentro. Solución final: el probador
  corre en un proceso hijo (`python -m sello.prover`) que escribe un veredicto por línea
  según los tiene; el padre lo mata al vencer el reloj y lo que no llegó queda en unknown.
  Dentro, contexto Z3 propio por función, hilo con reloj por consulta, contextos abandonados
  guardados hasta salir. El compilador ya no puede caer por culpa de Z3.
- Añadir los axiomas de *todas* las funciones del programa hacía que Z3 cambiara de
  estrategia y `div` pasaba de contraejemplo en 10 ms a unknown. Solo se añaden los axiomas
  de las funciones que aparecen (cierre).
- Las pruebas sobre secuencias son sensibles al estado del contexto: `contains_in` salía
  probada en 17 ms o unknown según el orden. Medidas tres codificaciones de `contains`
  sobre 44 funciones de una muestra: `exists i: xs[i] == x` 21 probadas, `Contains` nativo
  19, `count > 0` 18. Con `smt.mbqi` apagado: 19 en 8 s (frente a 41 s). De ahí las dos
  fases por consulta. `h` y `t` como constantes nuevas con `s == [h] ++ t` (forma de
  constructor) en vez de términos: 20, no ayuda; descartado.
- El probador encontró contratos falsos en tres programas de juguete de los tests
  (`test_checker`, `test_contratos` PRIMERO, `test_mutantes` SELLO, `test_store`
  FORALL_OPERANDO): se adaptaron los tests, que ahora también comprueban que el probador los
  caza con una entrada que los ejemplos no cubren.

### Decisiones tomadas (una nota por decisión)

#### El nivel 2 es modular y nunca rechaza sin reproducir el contraejemplo

Una función se prueba a partir de su `requires` y de los *contratos* de lo que llama, no de
sus cuerpos: exactamente lo que ve `sello sig`. Un certificado de nivel 2 promete: si las
funciones llamadas devuelven lo que dice su contrato, la función termina y su resultado
cumple `ensures` para toda entrada que cumpla `requires`. Un contraejemplo de Z3 solo se
reporta si el intérprete lo reproduce; así el probador nunca añade rechazos nuevos (un
contrato de un helper más débil que su cuerpo da unknown, no error) y el coste en intentos
del bucle es cero salvo cuando hay un bug de verdad. Por qué: la métrica es lo que llega a
producción; un rechazo indebido (ruidoso) cuesta intentos y confianza.

#### Los errores del probador son los de siempre, con la entrada

No hay códigos nuevos: E201, E300 y E500 con `found_by: prover` e `input`. El modelo ya sabe
arreglarlos y la spec sigue en dos páginas. Por qué: cada código nuevo es una frase de spec y
una regla más que aprender; la única información nueva es la entrada, y va en el mensaje.

#### `contains` se codifica como un existencial sobre índices

Medido el 2026-09-06 sobre 44 funciones: `exists` 21, `Contains` nativo de Z3 19, `count > 0`
18. Se elige `exists`. Se revisa si cambia la teoría de secuencias que se use.

#### El probador corre en un proceso hijo con reloj de pared

Porque Z3 no siempre atiende a su timeout, puede comerse la memoria y segfaultear al
interrumpirlo. Presupuestos: 1 s por consulta, 3 s por función, 30 s por programa, 300 ms de
primera fase solo con E-matching. El compilador nunca cae por culpa de Z3; lo que no
responde se queda en nivel 1.

#### Un certificado de nivel 2 exige una medida de terminación

Sin ella, `f(n) = if n == 0 then 42 else f(n)` se probaría a sí misma. La medida es un `Int`
que decrece y no es negativa, la longitud de una lista o la diferencia de dos `Int`
(`n - guess` en int_sqrt). Recursión mutua: nivel 1 hasta tener medidas entre funciones.

### Prerregistro de la siguiente medición

- Pregunta: ¿sube la tasa de funciones en nivel 2 con otra codificación de las listas
  (axiomas de secuencias al estilo Dafny, listas algebraicas con definiciones recursivas, o
  hechos derivados en los puntos de ligadura)? Criterio: sobre las mismas 36 soluciones,
  funciones en nivel 2 > 46/89 sin que baje el número de mutantes muertos (25/48) ni aparezca
  ningún rechazo no confirmado por el intérprete, con los mismos presupuestos de tiempo.

---

## 2026-09-06 (tarde) · Hechos para las listas, servidor MCP y reconocimiento de la fase 4

Rama `claude/sello-work-bgacgo`. Sesión con el límite de uso por medio: el intento de
lanzar cuatro variantes de codificación en paralelo (agentes en worktrees) murió antes de
empezar; se hizo en secuencia, a mano.

### Qué se hizo

- Hechos derivados para la teoría de secuencias de Z3 (`sello/prover.py`, `FACTS`): al ligar
  `[h, ..t]` sobre `s`, `len(t) == len(s) - 1`, `forall i: t[i] == s[i+1]` y `forall i >= 1:
  s[i] == t[i-1]`; para cada `a ++ b`, la longitud y los índices por tramos. Son teoremas de la
  teoría, pero dichos así un testigo `s[i]` de un cuantificador negado alcanza `t[i-1]`, donde
  vive la hipótesis de inducción.
- Cada consulta se decide en fases configurables (`PHASES`): solver sin patrones de
  instanciación explícitos, primero solo E-matching (300 ms) y luego MBQI (700 ms). Fases
  seguidas sobre el mismo solver comparten el scope (`decide`). El traductor puede poner
  patrones explícitos (`xs[i]`) en cada cuantificador (`Translator(patterns=True)`), pero está
  apagado: ver «qué se midió».
- Servidor MCP (`sello/mcp.py`, `uv run sello mcp --store PATH`, paquete `mcp` 2.x,
  `MCPServer` por stdio): tools `sello_spec` (la spec, el prompt), `sello_check`, `sello_add`,
  `sello_sig`, `sello_view`, `sello_deps`, `sello_users`, `sello_names`, `sello_verify`,
  `sello_eval`, con los mismos JSON que la CLI y `{ok: false, error}` en vez de excepción.
  Comprobado en proceso (las diez tools sobre `ejemplos/basicos.sello`); sin tests (glue).
- Reconocimiento del benchmark de vericoding para la fase 4 (abajo).

### Qué se midió

Medición rápida (`prove_program` sobre las 36 soluciones aceptadas del 5 de septiembre,
funciones probadas de 92; varía ±1-2 entre corridas por el tiempo):

| configuración | probadas |
|---|---|
| sin hechos, dos fases (referencia) | 45/92 |
| hechos de cons | 50/92 |
| hechos de concat | 47/92 |
| cons + concat | 49-50/92 |
| cons + concat con patrones explícitos en todo | 41/92 |
| solo patrones explícitos | 41/92 (y un contraejemplo real más, ver abajo) |
| cons + concat, cuatro fases (s0, s1, p0, p1) | 50-51/92 |
| cons + concat, patrones primero (p0, p1, s0, s1) | 45-46/92 (con el contraejemplo) |
| **cons + concat, dos fases sin patrones (elegida)** | **52/92** |

Medición completa (`bench/probador.py`, mismas 36 soluciones y mutantes del 5 de septiembre):

| | funciones en nivel 2 | mutantes muertos / llegaban | equivalentes muertos | tiempo (s) |
|---|---|---|---|---|
| original (mañana) | 46/89 (52 %) | 25/48 | 15/118 | 83 + 361 |
| hechos de cons, dos fases (`probador-2026-09-06-1312`) | 49/89 (55 %) | 27/48 | 12/118 | 68 + 373 |
| cons + concat, cuatro fases (`probador-2026-09-06-1324`) | 49/89 (55 %) | 25/48 | 15/118 | 47 + 352 |
| **cons + concat, dos fases: la definitiva (`probador-2026-09-06-1329`)** | **49/89 (55 %)** | **27/48 (56 %)** | 14/118 | 59 + 311 |

- La definitiva por columna: funciones en nivel 2 12/23, 20/35, 17/31; principal 7, 7, 5 de
  12; mutantes muertos 15/24, 2/2, 10/22; silenciosos de haiku 12/19; sin fallos de
  herramienta; el bug de `search` sigue saliendo.

- Los patrones explícitos bajan las pruebas por E-matching, pero con ellos MBQI converge en un
  modelo que sin ellos no encuentra: `find_max_helper([4, 6], [], Some(4))` de most_frequent
  (haiku) devuelve `Some(4)` y viola su `ensures` (4 y 6 empatan; el `requires` del helper no
  dice que `best` sea el más frecuente de lo ya visto). Es el segundo bug real en una
  solución aceptada, de la misma familia que `search` de int_sqrt: un helper con `requires`
  demasiado débil. Solo sale con las fases de patrones *antes* que las otras, y eso cuesta
  4-7 pruebas y tiempo; como fases posteriores (frías) no sale. Queda documentado en
  `prover.py`, no activado.
- Lo que sigue en unknown con los hechos: `sorted(result)` y `distinct(result)` (merge_sorted,
  dedupe), `forall x in xs: x <= result` cuando la recursión pasa por un `match` anidado, y
  los contratos por helper Bool con `ensures` débil (max_subarray de sonnet: `start_sum_le`).

### Qué falló

- El torneo de codificaciones por agentes (axiomas al estilo Dafny, listas algebraicas, hechos
  derivados, tuning): el límite de uso mató a los seis agentes con 0 resultados. Las dos
  variantes no probadas (axiomas al estilo Dafny con sort no interpretado; listas algebraicas
  con definiciones recursivas) siguen siendo las candidatas para `sorted`/`distinct`.
- Los patrones explícitos como cuarta fase: ni pruebas ni mutantes de más. La ganancia del
  contraejemplo depende del orden y del estado del solver entre obligaciones (con el scope
  compartido desaparece): frágil, no se adopta.
- `mcp` 2.x renombró FastMCP a `MCPServer`; el wrapper de errores tiene que conservar la
  firma (`functools.wraps`) o MCP no ve los parámetros de la tool.

### Decisiones tomadas

#### Los hechos de cons y concat entran; los patrones explícitos no

Medido: cons +5 funciones probadas sobre 92; concat +2 sola y neutra con cons (se queda por
principio: es la misma familia de hechos y no cuesta); patrones -4 a -11. Presupuestos como
antes (300 ms E-matching, 700 ms MBQI, 3 s por función, 30 s por programa).

#### El servidor MCP es la API de lectura, sin lógica propia

Cada tool devuelve el dict de la CLI; el almacén se abre por llamada; la spec se sirve como
tool porque es el prompt. Sin tests, como la CLI.

### Fase 4: el benchmark de vericoding, reconocido

- Repo `github.com/Beneficial-AI-Foundation/vericoding-benchmark` (MIT), artículo arXiv
  2509.22908 (bloqueado por el proxy; el resumen dice: 12.504 especificaciones, 27 % Lean,
  44 % Verus, 82 % Dafny de éxito con modelos de serie). Los ficheros crudos sí bajan por
  el proxy (`raw.githubusercontent.com`); la API de GitHub y Hugging Face, no.
- 12.504 tareas: lean 7.141, dafny 3.029, verus 2.334. Dafny por fuente (total / sin
  `qa-issue`): apps 883/677, dafnybench 929/443, numpy_triple 603/603, verified_cogen 172/172,
  humaneval 164/162, verina 157/157, bignum 62/62, numpy_simple 59/58. Metadatos en
  `vericoding_benchmark_v1.csv` (id, language, source, source-id, qa-issue, qa-issue-type,
  qa-score); `vericoding_results_v1.csv` con 55.397 experimentos.
- Formato: `specs/<ID>_specs.dfy` (DA apps, DD dafnybench, DH humaneval, DT numpy_triple,
  DV verina, DJ verified_cogen, DB bignum, DS numpy_simple) con secciones `<vc-preamble>`
  (funciones y predicados que definen la spec), `<vc-helpers>` (vacía: para lo que añada el
  que resuelve), `<vc-spec>` (el `method` con `requires`/`ensures`) y `<vc-code>` con el
  hueco `assume {:axiom} false`. Éxito en el benchmark: el verificador acepta el fichero con
  la spec intacta.
- Qué cabe en Sello (escaneo heurístico de las 2.334 specs Dafny sin `qa-issue`, preámbulo +
  spec): 246 usan solo `int`/`bool`/`seq` sin índices ni cuantificadores acotados sobre
  enteros (apps 129, dafnybench 61, verina 23, humaneval 18); 578 si se traducen `s[i]` y
  `forall i :: 0 <= i < |s| ==> ...` con helpers (apps 283, dafnybench 99, humaneval 71,
  numpy_triple 53, verina 48). Fuera: `array<T>` (542), `real` (506), `string` (596),
  `set`/`multiset` (128), clases y datatypes (169), varios valores de retorno (158).
  Ejemplo que cabe tal cual: DA0001 (predicados sobre enteros, `==>` → `not a or b`, `abs`
  como helper).
- Diseño propuesto para `bench/vericoding/`: `bajar.py` (por id, de raw.githubusercontent),
  `traducir.py` (Dafny → esqueleto Sello: firma con tipos, predicados del preámbulo como
  `fn ... -> Bool`, `requires`/`ensures` del `method`; lo no traducible se cuenta y se
  descarta), y un harness como `sello_contrato`: el contrato lo escribe el benchmark, el
  modelo escribe el cuerpo, y el éxito es el certificado de nivel 2 (lo que en el benchmark
  es «el verificador acepta»), con el nivel 1 como segunda columna. Sin oráculo: el benchmark
  no trae tests.
- Lo que Sello no tiene y el benchmark pide a cada paso: índices `s[i]` y cuantificadores
  acotados sobre enteros en los contratos. Son las dos features candidatas de la fase 4, y
  entran solo si la medición dice que suben el nivel 2 sin subir los intentos.

### Prerregistro de la siguiente medición

- Fase 4, primera corrida: sobre las 246 tareas Dafny que caben tal cual (o una muestra de 50
  con semilla fija), condición `sello_contrato` con el contrato traducido del benchmark.
  Pregunta: qué fracción queda en nivel 2 con haiku y con sonnet, cuántos intentos, y qué
  errores dominan. Criterio de éxito de la fase: que el nivel 2 sea comparable con el 82 %
  de Dafny del artículo en ese subconjunto; si no, que los `unproven` digan qué codificación
  falta.

---

## 2026-09-06 (tarde, segunda sesión) · Fase 4: el benchmark de vericoding en Sello

Rama `claude/sello-work-bgacgo`, commit `9076c2e` y siguientes. Sesión desde Claude Code
remoto: hay `claude -p` (haiku y sonnet), `raw.githubusercontent.com` pasa el proxy (la API de
GitHub y Hugging Face, no), 4 CPUs.

### Qué se hizo

- `bench/vericoding/bajar.py`: el CSV de metadatos y las 3.029 specs Dafny del benchmark
  (`specs/<ID>_specs.dfy`) a `bench/vericoding/cache/` (gitignored). 16 hilos, 2 minutos.
- `bench/vericoding/traducir.py`: Dafny → Sello, con test (`tests/test_traducir.py`, 12).
  Lexer y parser del subconjunto de Dafny que aparece en las specs (declaraciones `function`,
  `predicate`, `method`; lo demás se salta y se anota), inferencia de tipos mínima (para
  distinguir `+` de `++` y dar tipo a las variables de un cuantificador), y traducción a AST
  de Sello (se reimprime con el formateador canónico, así que el modelo ve el mismo texto que
  en `sello_contrato`):
  - Los helpers no recursivos se inlinean en las cláusulas (beta-reducción sin captura: una
    variable ligada que choca con una libre del argumento se renombra; los `var x := e; b`
    también se sustituyen). Los recursivos quedan congelados como `fn`, con el `requires` de
    Dafny (o una tautología), `ensures result == <cuerpo>` (la definición: lo único que un
    llamador ve por contrato) más los `ensures` de Dafny, y dos `example` calculados con el
    intérprete sobre entradas pequeñas que cumplan el `requires`.
  - `==>` → `not a or b`, `<==>` → `==`, `|s|` → `len(s)`, `x in s` → `contains(s, x)`,
    `forall x :: x in s ==> P` → `forall x in s: P` (también `forall x | x in s :: P`,
    `forall x <- s :: P`, varias variables anidadas), `exists x :: x in s && P` → `exists x in
    s: P`, `+` de secuencias → `++`, `a <= b < c` → `a <= b and b < c`, `nat` → `Int` más
    `>= 0` en `requires`/`ensures` (`seq<nat>` → `forall x in s: x >= 0`), un `&&` de primer
    nivel se parte en cláusulas, el valor de retorno se llama `result`, los nombres reservados
    de Sello se renombran (`sorted` → `sorted_`). `abs`, `min` y `max` se suponen con su
    definición de siempre cuando la spec los usa sin definirlos (en el benchmark los define
    quien resuelve). `/` y `%` se traducen tal cual (Dafny es euclídeo, Sello redondea hacia
    abajo: coinciden con divisor positivo) y la tarea lleva la nota `div` si el divisor no es
    un literal positivo.
  - Lo que Sello no tiene no se traduce y se cuenta por motivo: índices `s[i]`, tramos,
    cuantificadores sobre enteros o sin dominio, `array`, `real`, `string`, `char`, `set`,
    `multiset`, `map`, datatypes, tuplas, genéricos, varios valores de retorno, `modifies`,
    `old`, `match`, comprensiones, lambdas, funciones sin cuerpo o sin definir.
  - Cada tarea traducida (`bench/vericoding/tareas/<ID>.json`) lleva el esqueleto Sello completo
    (principal con cuerpo y ejemplo de relleno, para parsear), los nombres de los helpers
    congelados, las notas y la spec Dafny original. El esqueleto pasa el checker de Sello; si
    no, la tarea no cabe («traducción inválida») y es un fallo del traductor, no del lenguaje.
- `bench/contrato.py`: `Contrato(ejemplos_libres=True)`: la cabecera congelada se compara sin
  los `example`, que los pone el modelo (el benchmark no trae casos). Test.
- `bench/vericoding/harness4.py`, con test (`tests/test_vericoding.py`): la condición
  `sello_contrato` con el contrato del benchmark. El modelo recibe la spec y el contrato
  congelado, escribe el cuerpo y los ejemplos; cada intento pasa por `contrato.violacion` y por
  `sello check` (compilador, ejemplos, probador). Lo que compila pero no se prueba vuelve al
  modelo con el motivo (`unproven` por función del cierre), como en el benchmark vuelve el error
  del verificador. Éxito: la principal y todo lo que llama, transitivamente, en nivel 2; los
  helpers congelados no cuentan (su contrato es su definición) y se anota cuántos quedan en
  nivel 1. Segunda columna: nivel 1. Hasta 5 intentos, 4 workers.
- `bench/README.md` y `README.md`.

### Qué se midió: la traducción (`bench/resultados/vericoding-traduccion-2026-09-06-1443.md`)

Sobre las 2.334 specs Dafny sin `qa-issue`, en 8 segundos:

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | numpy_simple | bignum | total |
|---|---|---|---|---|---|---|---|---|---|
| specs | 677 | 443 | 162 | 157 | 172 | 603 | 58 | 62 | 2334 |
| **caben** | 99 (15 %) | 57 (13 %) | 16 (10 %) | 18 (11 %) | 4 (2 %) | 1 | 1 | 3 | **199 (9 %)** |
| · con helpers recursivos congelados | 24 | 19 | 10 | 1 | 1 | 0 | 0 | 3 | 58 |

- Notas en las que caben: `requires vacío` (tautología) 31, `div` 31, `nat` 35, `función
  supuesta` 7 (`min` 4, `max` 2, `abs` 1). Longitud mediana del contrato 345 caracteres,
  máxima 2.606 (`var` inlineado que duplica subexpresiones).
- Por qué no caben las 2.135 restantes (una spec puede tener varios motivos): tipo no
  soportado 1.696 (`string` 554, `array` 501, `real` 376, `char` 249, datatypes 219, tuplas
  47), cuantificador sobre enteros 1.579, índice `s[i]` 682, tramo 321, helper recursivo con
  `|s|`/`in`/`forall` en el cuerpo 283, `modifies` 115, sin valor de retorno 111, varios
  valores de retorno 101, sin `ensures` 53, genéricos 37.
- Lo que desbloquearía cada feature (specs que **solo** bloquea esa familia): cuantificador
  sobre un rango de enteros **179**; índice `s[i]` 18; los dos juntos **220** (más los tramos, 220;
  más reescribir a `match` los helpers recursivos con `|s|` en el cuerpo, 264). Es la respuesta
  a la pregunta del reconocimiento: la feature de la fase 4 es el cuantificador acotado sobre
  enteros, y el índice solo vale con él.
- Fallos del traductor que quedan (no del lenguaje): sintaxis Dafny no cubierta 30 como única
  traba (`bv32`, operadores de bits, specs truncadas en el propio benchmark como `ensures
  result in` y fin de fichero), funciones sin definir en el propio benchmark 8 (p. ej.
  `tirednessForSteps` en DA0113), 2 helpers sin ejemplo (requires que las entradas pequeñas
  no cumplen).
- De los 81 helpers congelados de las 58 tareas, Z3 prueba 70 por su cuenta (4 timeout, 4
  `ensures result >= 0` de un `nat` que necesita inducción, 3 `gcd(b, a % b)` sin medida que
  el probador vea).
- El benchmark trae specs débiles que su `qa` no marcó: DA0003 solo dice `ensures result >= 0`
  (el `gcd` del preámbulo no se usa). Cuentan como tareas: son las del benchmark.

### Qué se midió: la corrida

(Pendiente: haiku y sonnet sobre la muestra de 50 con semilla 1 están corriendo.)

### Qué falló

- Primer recuento: 134 tareas. Eran 199: comprobaba el esqueleto con el checker *antes* de
  calcular los ejemplos de los helpers congelados (E100 en 60 specs); la proyección de tuplas
  `p.0` y las lambdas con `requires` (`seq(6, i requires ... => ...)`) tiraban el parser del
  método y salían como «sin método» o «función sin definir» (94 specs); una regla de lambda
  demasiado amplia (`x requires` fuera de una lista de argumentos) tiró 94 más en la corrida
  siguiente hasta acotarla.
- `ensures result == <cuerpo>` en un helper recursivo se reevalúa en cada nivel: el coste se
  dobla por nivel y `power(2, 100)` no termina. La búsqueda de ejemplos se colgó con
  candidatos hasta 100; ahora los enteros llegan a 12 y hay reloj (`SIGALRM`, 3 s por helper).
  En el harness, un ejemplo del modelo con entradas grandes sobre un helper congelado acabaría
  en el timeout de `sello check` (120 s). Es el precio de comprobar el `ensures` en ejecución.
- `pkill -f traducir.py` mató la propia shell de la sesión (dos veces): el patrón casaba con
  la línea de comandos que lo lanzaba.
- Una llamada a haiku con este prompt tarda 45 s y gasta unos 4.600 tokens de razonamiento
  incluso en `Abs`; DA0008 (búsqueda binaria con helpers de recursión mutua) se comió 79.000
  tokens de razonamiento y 0,48 USD en 5 intentos sin salir del nivel 1.

### Decisiones tomadas (una nota por decisión)

#### El contrato del benchmark se traduce inlineando los helpers no recursivos

Un predicado de Dafny es una definición; en Sello, la verificación es modular y un llamador
solo ve el contrato del helper, así que un helper como `fn` necesitaría `ensures result ==
<cuerpo>` y ejemplos propios para servir de algo. Inlineado, el contrato queda autocontenido y
el probador ve las fórmulas. Coste: cláusulas largas y subexpresiones duplicadas por los `var`
(mediana 345 caracteres, máxima 2.606). Los helpers recursivos no se pueden inlinear y quedan
congelados con la definición en el `ensures`.

#### Los ejemplos de la principal los pone el modelo

El benchmark no trae casos y Sello exige al menos un `example`. El contrato congelado se
compara sin los `example` (`Contrato(ejemplos_libres=True)`); el modelo añade los suyos y el
compilador los ejecuta. Son la parte del contrato que el benchmark no escribe.

#### El éxito en vericoding es el nivel 2 de todo lo que la principal llama, menos los helpers congelados

Un certificado de nivel 2 promete «si las funciones llamadas devuelven lo que dice su
contrato»: un helper propio con un `ensures` fuerte y un cuerpo sin probar dejaría la principal
en nivel 2 sin haber probado nada. Por eso cuenta el cierre. Los helpers congelados se dan por
buenos porque su contrato es su definición (y Z3 prueba 70 de 81 por su cuenta); se anota
cuántos quedan en nivel 1.

#### Cuando no hay nada que suponer, el contrato traducido lleva una tautología

31 de las 199 tareas no tienen `requires` en Dafny (una función total). Sello exige la cláusula
y rechaza el literal `true` (E102), así que el traductor pone `len(xs) >= 0` o `x == x`, con la
nota `requires vacío`. Es el mismo idioma que usan los modelos (`requires len(xs) >= 0` sale 4
veces en las soluciones aceptadas del 5 de septiembre). Hallazgo para revisar con datos: una
función total no tiene `requires` honesto; E102 sobre `requires` puede ser una regla de más.

#### `/` y `%` se traducen tal cual y la tarea lleva la nota `div`

Dafny es euclídeo y Sello redondea hacia abajo; coinciden con divisor positivo, que es casi
siempre el caso en las specs (`/ 2`, `% 10`). Traducir la división euclídea exacta haría
ilegible el contrato. Con divisor no literal positivo, nota `div` (31 tareas) para poder
filtrarlas si un resultado depende de ello.

### Prerregistro de la siguiente medición

(Pendiente de los números de la corrida.)
