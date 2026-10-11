# El probador 2026-10-11-1046

Nivel 2 (Z3) sobre las soluciones que el juez débil ya aceptó y sobre los mutantes que llegaron a producción. Sin modelo: determinista y gratis.

## Soluciones aceptadas

Formato: nivel de la función principal · funciones en nivel 2 / total. `✗ Exxx` = el probador encontró una entrada que rompe el contrato: un bug real en una solución que el juez débil y el oráculo dieron por buena.

| Problema | sello_mcp·haiku |
|---|---|
| clamp | 2 · 1/1 |
| index_of | 2 · 1/1 |
| int_sqrt | 2 · 2/2 |
| longest_run | 1 · 1/2 |
| max_subarray | 1 · 5/6 |
| merge_sorted | 1 · 0/1 |
| most_frequent | ✗ E201 |
| nth | 1 · 1/2 |
| power | 1 · 1/2 |
| rotate_left | 2 · 3/3 |
| second_largest | 2 · 3/4 |
| zip_sum | 2 · 1/1 |

| | sello_mcp·haiku |
|---|---|
| soluciones | 12 |
| **principal en nivel 2** | **6/12 (50 %)** |
| funciones en nivel 2 | 19/25 (76 %) |
| · Z3 no decide | 6 |
| · sin tiempo | 0 |
| · sin medida de terminación | 0 |
| · recursión mutua | 0 |
| · construcción no traducida | 0 |
| · sin intentar (otra función falló) | 0 |
| bugs reales en soluciones aceptadas | 1 |
| fallos de la herramienta | 0 |
| tiempo total (s) | 20 |

Rechazadas:

- most_frequent (sello_mcp·haiku): `E201` Postcondition violated: find_max_by_count([55, 56], 56, []) returned 56, which violates `ensures (contains(xs, result) and (forall y in xs: ((y == result) or (count(xs, y) < count(xs, result)))))` (input found by the prover: find_max_by_count([55, 56], 56, []); the examples do not cover it)
