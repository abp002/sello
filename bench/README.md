# bench — el experimento

Aquí vive la métrica. Antes que el compilador.

## Tres harness, tres preguntas

| Harness | Batería | Pregunta |
|---|---|---|
| `harness.py` | `problemas/`, `dificiles/` | ¿Cuántos intentos hasta compilar y pasar casos ocultos completos? Mide facilidad de generación. |
| `harness2.py` | `problemas2/` | ¿Leer solo `sig` (sin cuerpos) baja los aciertos? |
| `harness3.py` | `ambiguos/` | **¿Cuánto error silencioso llega a producción tras pasar un juez débil?** La métrica principal desde el 2026-09-02. |
| `mutantes.py` | soluciones de `resultados/juez-*.jsonl` | De los bugs de cuerpo que el juez débil deja pasar, ¿cuántos caza el contrato? Sin modelo. |
| `cotas.py` | soluciones de `resultados/juez-*.jsonl` | ¿Cuántas funciones principales tienen un `ensures` que solo acota el resultado? Sin modelo. |
| `probador.py` | soluciones de `juez-*.jsonl` y mutantes de `mutantes-*.jsonl` | ¿Cuántas funciones prueba el nivel 2 (Z3) y cuántos mutantes que llegaban a producción mata en compilación? Sin modelo. |
| `vericoding/harness4.py` | `vericoding/tareas/` | **Fase 4.** Con el contrato del benchmark de vericoding (traducido de Dafny), ¿qué fracción deja el modelo en nivel 2, en cuántos intentos y con qué errores? |

## El juez imperfecto (`harness3.py`)

El bucle solo ve el compilador (desde el 2026-09-06, con el probador de nivel 2 dentro) y
dos ejemplos visibles del enunciado. Lo aceptado pasa al
oráculo: referencia en Python y casos generados con semilla fija (`generar_ambiguos.py`,
se ejecuta una vez y se commitea). Cada llamada del oráculo es *correcto*, *silencioso*
(valor distinto sin señal), *rechazado* (E300/E500/excepción) o *cazado* (E201/assert), en
una de dos zonas: el dominio que el enunciado exige, o la zona ambigua que el enunciado
calla. La regla de clasificación está en `juez.py` y tiene test.

Tres condiciones: `sello`, `python`, `python_asserts`. La tercera separa el hábito de
escribir contratos del lenguaje que lo obliga.

    uv run python bench/harness3.py --model haiku
    uv run python bench/harness3.py --model sonnet --only nth --cond sello   # humo

**Condiciones comunes:** mismo modelo, misma temperatura, mismos problemas. Se registran
también tokens de salida, razonamiento, coste y tiempo. Los resultados van a
`resultados/` (`.jsonl` con todo, `.md` con la tabla).

Cada modelo se llama con `claude -p` en modo limpio: sin herramientas, sin settings, sin
MCP, con system prompt propio. Unos 300 tokens de sobrecarga por llamada.
Si la sesión desde la que se lanza tiene `CLAUDE_CONFIG_DIR` apuntando a otra cuenta, el
`claude -p` hijo sale con "Not logged in" y todo cae en `E000` con cero tokens: lanzar con
`env -u CLAUDE_CONFIG_DIR` (pasó el 2026-09-05).

## El contrato escrito por otro (`sello_contrato`)

Condición aparte de `harness3.py`, fuera de `all`. El contrato se toma de una corrida
anterior (`--contratos`, normalmente sonnet): la función principal sin cuerpo y, completos,
los helpers que sus cláusulas usan (`contrato.py`, cierre por código, con test). El modelo
recibe ese texto congelado y escribe el cuerpo; si toca el contrato, el juez débil lo
rechaza con fase `contract` y lo cuenta. En `mutantes.py` los helpers congelados no se
mutan. Prerregistrado en el vault: 'El contrato escrito por otro caza lo que haiku deja
pasar'.

    uv run python bench/harness3.py --model haiku --cond sello_contrato \
        --contratos bench/resultados/juez-2026-09-05-0015-sonnet.jsonl

## Mutantes del cuerpo (`mutantes.py`)

Sin modelo. Toma las soluciones aceptadas de corridas del juez, mete un bug pequeño en el
cuerpo de cada una (frontera `<`↔`<=`, aritmética, literal ±1, lógica, ramas, argumentos,
variable por otra del ámbito; nunca en el contrato ni en un `assert`) y pasa cada mutante
por el mismo juez débil y el mismo oráculo. Seis destinos: no compila, muerto por el juez
débil (y de qué: ejemplos, contrato, frontera, probador), equivalente, silencioso, cazado, ruidoso.
Solo clasifica el dominio. Prerregistrado en el vault: 'Los mutantes del cuerpo miden lo
que el ensures caza'. La regla de destinos está en `mutantes.py` y tiene test.

    uv run python bench/mutantes.py bench/resultados/juez-2026-09-02-1814-haiku.jsonl \
        bench/resultados/juez-2026-09-02-1821-sonnet.jsonl \
        bench/resultados/juez-2026-09-02-2237-haiku.jsonl bench/resultados/juez-2026-09-02-2237-sonnet.jsonl
    uv run python bench/mutantes.py bench/resultados/juez-2026-09-02-2237-sonnet.jsonl --only nth   # humo

Si un (problema, condición, modelo) está en varios ficheros manda el último: así `sello`
sale de la cuarta corrida y `python`/`python_asserts` de la primera.

## Ensures solo de cotas (`cotas.py`)

Sin modelo. Sobre la función principal de cada solución aceptada: una cláusula es *cota*
si es una comparación cuyos dos lados se componen solo de `result`, literales, parámetros,
`len(...)` y aritmética; lo demás (`contains`, `forall`, `count`, un helper del fichero) es
*contenido*. Lista también los helpers llamados desde `ensures` y las veces que un modelo
cambió el `ensures` tras un `E201`. Prerregistrado en el vault: 'Un ensures de cotas no
certifica nada'.

    uv run python bench/cotas.py bench/resultados/juez-2026-09-05-0015-haiku.jsonl

## El probador (`probador.py`)

Sin modelo. Pasa por `sello check` (compilador, ejemplos y probador de nivel 2, cada uno en
su proceso) las soluciones aceptadas de corridas del juez y los mutantes de corridas de
mutantes, y responde dos preguntas: cuántas funciones quedan en nivel 2 y por qué no las
demás (Z3 no decide, sin tiempo, sin medida de terminación, recursión mutua), y cuántos de
los mutantes que llegaron a producción (y de los equivalentes en el dominio) mata el
probador en compilación, con qué código. Una solución aceptada que el probador rechaza es
un bug real que el juez débil y el oráculo dejaron pasar: se lista aparte.

    uv run python bench/probador.py \
        --soluciones bench/resultados/juez-2026-09-05-0015-haiku.jsonl \
                     bench/resultados/juez-2026-09-05-0015-sonnet.jsonl \
                     bench/resultados/juez-2026-09-05-1920-haiku-contrato.jsonl \
        --mutantes bench/resultados/mutantes-2026-09-05-1931.jsonl
    uv run python bench/probador.py --soluciones bench/resultados/juez-2026-09-05-0015-sonnet.jsonl --only nth   # humo

## El benchmark de vericoding (`vericoding/`)

Fase 4: las specs Dafny del [benchmark de vericoding](https://github.com/Beneficial-AI-Foundation/vericoding-benchmark)
como contratos de Sello. Tres piezas:

- `bajar.py`: el CSV de metadatos y las 3.029 specs Dafny (`specs/<ID>_specs.dfy`) a
  `vericoding/cache/` (fuera del repo). Solo `raw.githubusercontent.com` pasa el proxy.
- `traducir.py`: Dafny → Sello. Los helpers no recursivos se inlinean en las cláusulas; los
  recursivos quedan congelados como `fn` con `ensures result == <cuerpo>` y ejemplos calculados;
  `==>` es `not a or b`, `|s|` es `len(s)`, `x in s` es `contains(s, x)`, `forall x :: x in s ==> P`
  es `forall x in s: P`, `nat` es `Int` más `>= 0`. Lo que Sello no tiene (índices `s[i]`, tramos,
  cuantificadores sobre enteros, `array`, `real`, `string`, `set`, `map`, datatypes, varios valores
  de retorno) no se traduce y se cuenta por qué: `resultados/vericoding-traduccion-*.md`. Las que
  caben van a `vericoding/tareas/<ID>.json` (con la spec Dafny original). Tiene test.
- `harness4.py`: la condición `sello_contrato` con ese contrato: la principal sin cuerpo ni
  ejemplos y los helpers congelados; el modelo escribe el cuerpo y sus `example` (el benchmark no
  trae casos). Lo que compila pero no se prueba vuelve al modelo con el motivo `unproven`, como en
  el benchmark vuelve el error del verificador. Éxito («el verificador acepta»): la principal y todo
  lo que llama, transitivamente, en nivel 2; los helpers congelados se dan por buenos (su contrato
  es su definición) y se anota cuántos quedan en nivel 1. Segunda columna: nivel 1. Tiene test.

    uv run python bench/vericoding/bajar.py
    uv run python bench/vericoding/traducir.py                       # cobertura + tareas/
    uv run python bench/vericoding/traducir.py DA0001 --ver          # una, con el contrato o los motivos
    uv run python bench/vericoding/harness4.py --model haiku --muestra 50 --semilla 1
    uv run python bench/vericoding/harness4.py --model haiku --only DA0003     # humo
