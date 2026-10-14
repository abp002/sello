# Prueba de literales 2026-10-15-0025

Por problema: rechaza lo correcto (E201, de 25) · `requires` fuera (E300) · admite lo incorrecto (de los casos válidos). `-`: sin contrato que compile. Prerregistrado en el vault: 'El contrato se puede escribir sin el cuerpo'.

| Problema | humo-contratos-2026-10-15-0021-sonnet.jsonl | humo-contratos-2026-10-15-0022-sonnet-py.jsonl |
|---|---|---|
| balance | - | - |
| binary_search | 0 · 0 · 0/24 | 0 · 0 · 0/24 |
| collatz_steps | - | - |
| count_divisors | - | - |
| count_greater | - | - |
| count_pairs_sum | - | - |
| digit_sum | - | - |
| evens_first | - | - |
| fib | - | - |
| first_missing | - | - |
| interleave | - | - |
| is_prime | - | - |
| is_sorted | - | - |
| kth_smallest | - | - |
| last_index_of | - | - |
| majority | - | - |
| max_gap | - | - |
| median_odd | - | - |
| min_index | - | - |
| prefix_sums | - | - |
| range_list | - | - |
| remove_all | - | - |
| replace_all | - | - |
| take_while_pos | - | - |

| | humo-contratos-2026-10-15-0021-sonnet.jsonl | humo-contratos-2026-10-15-0022-sonnet-py.jsonl |
|---|---|---|
| contratos que compilan | 1/24 | 1/24 |
| **rechazan lo correcto** (algún E201) | **0** | **0** |
| casos correctos rechazados (E201) | 0 | 0 |
| contratos con `requires` fuera del dominio (E300) | 0 | 0 |
| admiten lo incorrecto (casos) | 0 % | 0 % |
| **flojos** (admiten el 60 % o más) | **0** | **0** |
| solo cotas (forma, `cotas.py`; Sello) | 0 | 0 |
| ambiguas rechazadas (declarado) | 4/4 | 4/4 |
