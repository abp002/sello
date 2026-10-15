# Experimento decisivo (SEL-9)

Prerregistrado en el vault: 'Sello frente a Python con el contrato escrito aparte'.

| | S·a | S·b | A·a | A·b | P·a | P·b |
|---|---|---|---|---|---|---|
| entregadas | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| **silenciosos en el dominio (llamadas)** | **0** | **0** | **0** | **0** | **0** | **0** |
| **tareas con algún silencioso** | **0** | **0** | **0** | **0** | **0** | **0** |
| ruidosos en el dominio (llamadas) | 25 | 25 | 25 | 25 | 0 | 0 |
| cazados por el contrato (llamadas) | 0 | 0 | 0 | 0 | 0 | 0 |
| intentos hasta aceptar (cuerpo) | 1.17 | 1.17 | 1.17 | 1.33 | 1.00 | 1.00 |
| coste USD (contrato + cuerpo) | 0.87 | 0.34 | 0.34 | 0.34 | 0.18 | 0.08 |
| contratos que compilan | 24 | 24 | 24 | 24 | 24 | 24 |
| contratos que admiten lo incorrecto (casos) | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| contratos flojos (≥ 60 %) | 0 | 0 | 0 | 0 | 0 | 0 |
| contratos que rechazan lo correcto | 0 | 0 | 0 | 0 | 0 | 0 |
| mutantes: silenciosos / llegan | 0/1 | 0/3 | 0/1 | 0/4 | 0/2 | 0/2 |
| mutantes: cazados / llegan | 1/1 | 3/3 | 1/1 | 4/4 | 2/2 | 2/2 |
| mutantes: silenciosos / generados | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| avisos de ambigüedad | 0 | 0 | 0 | 0 | - | - |
| contratos finales unique / ambiguous / unknown | 16/0/8 | 14/0/10 | 15/0/9 | 15/0/9 | - | - |

## Regla de decisión

- Silenciosos en el dominio, S − P por repetición: [0, 0]; ruido entre repeticiones: S 0, P 0. **EMPATE (dentro del ruido)**.
- Coste: S 1.21 USD frente a P 0.26 USD (4.7×; si Sello gana con más de 2×, la regla no le da la victoria).
- Aviso (A frente a S): silenciosos [0, 0] frente a [0, 0]; admite lo incorrecto [0, 0] frente a [0, 0]; ruidosos [25, 25] frente a [25, 25]. **NO ENTRA**.

## Corrección del oráculo (issue #2)

El oráculo de Sello corría los 25 casos con 60 s para el lote y el de Python con 3 s por caso: un caso
lento tumbaba los demás. Con 3 s por caso en los dos (`reoraculo.py`, sin modelo, sobre los mismos
cuerpos; ficheros `juez-*-sel9-*-reoraculo.jsonl`) solo cambia `fib`:

| | S·a | S·b | A·a | A·b | P·a | P·b |
|---|---|---|---|---|---|---|
| ruidosos en el dominio (llamadas) | 17 | 7 | 5 | 8 | 0 | 0 |
| silenciosos en el dominio (llamadas) | 0 | 0 | 0 | 0 | 0 | 0 |

La regla no cambia: EMPATE.
