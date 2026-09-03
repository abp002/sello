# bench — el experimento

Aquí vive la métrica. Antes que el compilador.

## Tres harness, tres preguntas

| Harness | Batería | Pregunta |
|---|---|---|
| `harness.py` | `problemas/`, `dificiles/` | ¿Cuántos intentos hasta compilar y pasar casos ocultos completos? Mide facilidad de generación. |
| `harness2.py` | `problemas2/` | ¿Leer solo `sig` (sin cuerpos) baja los aciertos? |
| `harness3.py` | `ambiguos/` | **¿Cuánto error silencioso llega a producción tras pasar un juez débil?** La métrica principal desde el 2026-09-02. |
| `mutantes.py` | soluciones de `resultados/juez-*.jsonl` | De los bugs de cuerpo que el juez débil deja pasar, ¿cuántos caza el contrato? Sin modelo. |

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
