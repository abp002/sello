# bench — el experimento

Aquí vive la métrica. Antes que el compilador.

## Tres harness, tres preguntas

| Harness | Batería | Pregunta |
|---|---|---|
| `harness.py` | `problemas/`, `dificiles/` | ¿Cuántos intentos hasta compilar y pasar casos ocultos completos? Mide facilidad de generación. |
| `harness2.py` | `problemas2/` | ¿Leer solo `sig` (sin cuerpos) baja los aciertos? |
| `harness3.py` | `ambiguos/` | **¿Cuánto error silencioso llega a producción tras pasar un juez débil?** La métrica principal desde el 2026-09-02. |

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
