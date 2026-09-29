# Prueba de literales 2026-09-29-2314

Por problema: rechaza lo correcto (E201, de 25) · `requires` fuera (E300) · admite lo incorrecto (de los casos válidos). `-`: sin contrato que compile. Prerregistrado en el vault: 'El contrato se puede escribir sin el cuerpo'.

| Problema | juez-2026-09-05-0015-sonnet.jsonl |
|---|---|
| clamp | 0 · 0 · 0/24 · cotas |
| index_of | 0 · 0 · 0/21 |
| int_sqrt | 0 · 0 · 0/24 · cotas |
| longest_run | 0 · 0 · 18/23 |
| max_subarray | 0 · 0 · 0/25 |
| merge_sorted | 0 · 0 · 0/25 |
| most_frequent | 0 · 0 · 0/19 |
| nth | 0 · 0 · 2/19 |
| power | 17 · 0 · 0/25 |
| rotate_left | 0 · 0 · 0/25 |
| second_largest | 0 · 0 · 0/24 |
| zip_sum | 0 · 0 · 0/25 |

| | juez-2026-09-05-0015-sonnet.jsonl |
|---|---|
| contratos que compilan | 12/12 |
| **rechazan lo correcto** (algún E201) | **1** |
| casos correctos rechazados (E201) | 17 |
| contratos con `requires` fuera del dominio (E300) | 0 |
| admiten lo incorrecto (casos) | 7 % |
| **flojos** (admiten el 60 % o más) | **1** |
| solo cotas (forma, `cotas.py`) | 2 |
| ambiguas rechazadas (declarado) | 44/45 |
