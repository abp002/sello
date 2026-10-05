# El probador 2026-10-05-1936

Nivel 2 (Z3) sobre las soluciones que el juez débil ya aceptó y sobre los mutantes que llegaron a producción. Sin modelo: determinista y gratis.

## Soluciones aceptadas

Formato: nivel de la función principal · funciones en nivel 2 / total. `✗ Exxx` = el probador encontró una entrada que rompe el contrato: un bug real en una solución que el juez débil y el oráculo dieron por buena.

| Problema | sello·haiku | sello·sonnet | sello_contrato·haiku | sello_mcp·haiku |
|---|---|---|---|---|
| clamp | 2 · 1/1 | 2 · 1/1 | 2 · 1/1 | - |
| index_of | 2 · 1/1 | 2 · 1/1 | 2 · 1/1 | - |
| int_sqrt | 2 · 1/3 | 2 · 2/2 | 2 · 2/2 | - |
| longest_run | 1 · 1/2 | 1 · 3/4 | 1 · 1/2 | - |
| max_subarray | 1 · 1/2 | 1 · 2/5 | 1 · 5/7 | - |
| merge_sorted | 1 · 0/1 | 1 · 0/1 | 1 · 0/1 | - |
| most_frequent | ✗ E201 | 2 · 4/5 | 2 · 4/5 | - |
| nth | 2 · 1/1 | 2 · 1/1 | 2 · 1/1 | - |
| power | 2 · 1/1 | 1 · 0/1 | 1 · 0/1 | - |
| rotate_left | 1 · 2/3 | 2 · 3/3 | 2 · 3/3 | - |
| second_largest | 1 · 2/3 | 1 · 6/7 | 1 · 5/6 | - |
| zip_sum | 2 · 1/1 | 2 · 1/1 | 2 · 1/1 | - |

| | sello·haiku | sello·sonnet | sello_contrato·haiku | sello_mcp·haiku |
|---|---|---|---|---|
| soluciones | 12 | 12 | 12 | 0 |
| **principal en nivel 2** | **6/12 (50 %)** | **7/12 (58 %)** | **7/12 (58 %)** | **-** |
| funciones en nivel 2 | 12/19 (63 %) | 24/32 (75 %) | 24/31 (77 %) | - |
| · Z3 no decide | 5 | 8 | 7 | 0 |
| · sin tiempo | 0 | 0 | 0 | 0 |
| · sin medida de terminación | 0 | 0 | 0 | 0 |
| · recursión mutua | 2 | 0 | 0 | 0 |
| · construcción no traducida | 0 | 0 | 0 | 0 |
| · sin intentar (otra función falló) | 0 | 0 | 0 | 0 |
| bugs reales en soluciones aceptadas | 1 | 0 | 0 | 0 |
| fallos de la herramienta | 0 | 0 | 0 | 0 |
| tiempo total (s) | 15 | 23 | 14 | 0 |

Rechazadas:

- most_frequent (sello·haiku): `E201` Postcondition violated: find_max_helper([13], [], None) returned None, which violates `ensures match result { None => (len(original) == 0) Some(x) => (contains(original, x) and (forall y in original: ((y == x) or (count(original, x) > count(original, y))))) }` (input found by the prover: find_max_he

## Mutantes

De los mutantes que llegaron a producción en la corrida de mutantes (pasaron el juez débil y no son equivalentes en el dominio), cuántos mata ahora el probador en compilación. Formato: matados / llegaban · equivalentes matados / equivalentes (un equivalente matado es un bug fuera de los casos del oráculo).

| Problema | sello·haiku | sello·sonnet | sello_contrato·haiku | sello_mcp·haiku |
|---|---|---|---|---|
| clamp | 0/0 · 0/8 | 0/0 · 0/8 | 0/0 · 0/8 | 0/0 · 0/8 |
| index_of | 0/1 · 0/8 | 0/4 · 0/14 | 0/3 · 0/8 | 0/4 · 0/8 |
| int_sqrt | 0/0 · 0/5 | 3/3 · 0/1 | 2/2 · 4/9 | 0/0 · 0/5 |
| longest_run | 30/45 · 0/16 | 11/14 · 0/21 | 0/2 · 0/14 | 0/2 · 0/23 |
| max_subarray | 40/66 · 7/53 | 0/0 · 12/59 | 6/29 · 1/25 | 0/24 · 0/31 |
| merge_sorted | 0/0 · 0/12 | 0/0 · 0/12 | 0/0 · 0/12 | 0/0 · 0/12 |
| most_frequent | 0/0 · 9/18 | 4/4 · 16/43 | 0/0 · 0/23 | 0/0 · 1/24 |
| nth | - | 0/0 · 0/2 | - | - |
| second_largest | 3/3 · 0/4 | 1/1 · 0/12 | 4/4 · 0/9 | 0/22 · 0/14 |
| zip_sum | 0/0 · 0/4 | 0/0 · 0/19 | 0/0 · 0/5 | 0/0 · 0/4 |

| | sello·haiku | sello·sonnet | sello_contrato·haiku | sello_mcp·haiku |
|---|---|---|---|---|
| llegaban a producción | 115 | 26 | 40 | 52 |
| **matados por el probador / llegaban** | **73/115 (63 %)** | **19/26 (73 %)** | **12/40 (30 %)** | **0/52 (0 %)** |
| · de los cazados en producción (E201) | 19/20 (95 %) | 10/13 (77 %) | 10/36 (28 %) | 0/23 (0 %) |
| · de los ruidosos (E300 / E500) | 0/1 (0 %) | 7/7 (100 %) | 2/4 (50 %) | 0/29 (0 %) |
| · de los silenciosos | 54/94 (57 %) | 2/6 (33 %) | - | - |
| equivalentes en el dominio matados (bug fuera del oráculo) | 16/128 (12 %) | 28/191 (15 %) | 5/113 (4 %) | 1/129 (1 %) |
| · matados con E201 | 77 | 32 | 16 | 1 |
| · matados con E300 | 12 | 15 | 1 | 0 |
| · matados con E500 | 0 | 0 | 0 | 0 |
| fallos de la herramienta | 0 | 0 | 0 | 0 |
| tiempo total (s) | 203 | 314 | 303 | 715 |
