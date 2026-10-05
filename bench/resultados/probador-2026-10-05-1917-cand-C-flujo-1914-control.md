# El probador 2026-10-05-1917

Nivel 2 (Z3) sobre las soluciones que el juez débil ya aceptó y sobre los mutantes que llegaron a producción. Sin modelo: determinista y gratis.

## Soluciones aceptadas

Formato: nivel de la función principal · funciones en nivel 2 / total. `✗ Exxx` = el probador encontró una entrada que rompe el contrato: un bug real en una solución que el juez débil y el oráculo dieron por buena.

| Problema | sello_mcp·haiku |
|---|---|
| clamp | 2 · 1/1 |
| index_of | 2 · 1/1 |
| int_sqrt | 2 · 2/3 |
| longest_run | 1 · 1/2 |
| max_subarray | 1 · 1/3 |
| merge_sorted | 1 · 0/1 |
| most_frequent | 1 · 3/4 |
| nth | 2 · 1/1 |
| power | 1 · 1/2 |
| rotate_left | 2 · 3/3 |
| second_largest | ✗ E201 |
| zip_sum | 2 · 1/1 |

| | sello_mcp·haiku |
|---|---|
| soluciones | 12 |
| **principal en nivel 2** | **6/12 (50 %)** |
| funciones en nivel 2 | 15/22 (68 %) |
| · Z3 no decide | 6 |
| · sin tiempo | 0 |
| · sin medida de terminación | 1 |
| · recursión mutua | 0 |
| · construcción no traducida | 0 |
| · sin intentar (otra función falló) | 0 |
| bugs reales en soluciones aceptadas | 1 |
| fallos de la herramienta | 0 |
| tiempo total (s) | 19 |

Rechazadas:

- second_largest (sello_mcp·haiku): `E201` Postcondition violated: find_in_list([-1], [14]) returned Some(-1), which violates `ensures is_second(original, result)` (input found by the prover: find_in_list([-1], [14]); the examples do not cover it)
