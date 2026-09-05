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

## El juez imperfecto (`harness3.py`)

El bucle solo ve el compilador y dos ejemplos visibles del enunciado. Lo aceptado pasa al
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
débil (y de qué: ejemplos, contrato, frontera), equivalente, silencioso, cazado, ruidoso.
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
