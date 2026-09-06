# Vericoding en Sello 2026-09-06-1807 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

32 tareas reutilizadas de `vericoding-2026-09-06-1459-haiku-muestra50-semilla1.jsonl` (todas sus llamadas contestaron); 18 repetidas ahora porque alguna llamada volvió sin respuesta: DD0109, DD0435, DD0730, DD0740, DD0752, DD0791, DD0826, DD0848, DH0048, DH0065, DH0127, DH0140, DJ0147, DV0057, DV0088, DV0106, DV0145, DV0178.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0001 | apps | solve | 2 (1) |  |
| DA0008 | apps | solve | 1 (1) | undecided: `ensures (countLessOrEqualValue(n, m, result) >= k)` |
| DA0023 | apps | solve | 1 (2) | undecided: `ensures ((not (((a - 1) / (m * k)) == ((b - 1) / (m * k))) |
| DA0026 | apps | solve | 2 (1) |  |
| DA0029 | apps | solve | 1 (1) | timeout: the prover did not answer |
| DA0069 | apps | solve | 2 (1) |  |
| DA0099 | apps | solve | 2 (4) |  |
| DA0122 | apps | solve | 1 (1) | timeout: the prover did not answer |
| DA0140 | apps | MinBacteria | 2 (1) |  |
| DA0190 | apps | solve | 2 (1) |  |
| DA0399 | apps | solve | 2 (1) |  |
| DA0419 | apps | solve | 2 (1) |  |
| DA0455 | apps | SolveCookieDistribution | 2 (1) |  |
| DA0476 | apps | solve | 1 (1) | termination: no argument decreases at every recursive call |
| DA0478 | apps | solve | 2 (1) |  |
| DA0522 | apps | Solve | 2 (1) |  |
| DA0529 | apps | solve | 2 (1) |  |
| DA0552 | apps | CountTriples | 2 (5) |  |
| DA0615 | apps | CalculateBlackSquares | 2 (1) |  |
| DA0656 | apps | solve | 2 (1) |  |
| DA0674 | apps | solve | 2 (1) |  |
| DB0020 | bignum | ModExpPow2_int | 2 (2) |  |
| DD0065 | dafnybench | ComputeIsEven | 2 (1) |  |
| DD0080 | dafnybench | M | 2 (1) |  |
| DD0092 | dafnybench | Triple | 2 (1) |  |
| DD0094 | dafnybench | Triple | 2 (1) |  |
| DD0109 | dafnybench | mroot1 | 2 (1) |  |
| DD0159 | dafnybench | Comb | 2 (1) |  |
| DD0225 | dafnybench | ComputePower | 2 (1) |  |
| DD0342 | dafnybench | calcR | 2 (1) |  |
| DD0429 | dafnybench | gcdI | 2 (1) |  |
| DD0435 | dafnybench | q | 2 (2) |  |
| DD0682 | dafnybench | CubeVolume | 2 (1) |  |
| DD0722 | dafnybench | LastDigit | 2 (1) |  |
| DD0730 | dafnybench | MinLengthSublist | 1 (2) | undecided: `ensures contains(s, result)` |
| DD0740 | dafnybench | DifferenceSumCubesAndSumNumbers | 2 (1) |  |
| DD0752 | dafnybench | SquarePyramidSurfaceArea | 2 (1) |  |
| DD0791 | dafnybench | IsMonthWith30Days | 2 (1) |  |
| DD0826 | dafnybench | ClimbStairs | 2 (1) |  |
| DD0848 | dafnybench | HoareTripleReqEns | 2 (1) |  |
| DH0048 | humaneval | fib4 | 2 (1) |  |
| DH0065 | humaneval | fibfib | 2 (1) |  |
| DH0127 | humaneval | next_odd_collatz_iter | 2 (1) |  |
| DH0140 | humaneval | is_equal_to_sum_even | 2 (1) |  |
| DJ0147 | verified_cogen | IntegerSquareRoot | 2 (3) |  |
| DV0057 | verina | NthUglyNumber | 2 (1) |  |
| DV0088 | verina | MyMin | 2 (1) |  |
| DV0106 | verina | IsEven | 2 (1) |  |
| DV0145 | verina | SquareRoot | 2 (1) |  |
| DV0178 | verina | Triple | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | bignum | total |
|---|---|---|---|---|---|---|---|
| tareas | 21 | 18 | 4 | 5 | 1 | 1 | 50 |
| **probadas (nivel 2)** | **16/21 (76 %)** | **17/18 (94 %)** | **4/4 (100 %)** | **5/5 (100 %)** | **1/1 (100 %)** | **1/1 (100 %)** | **44/50 (88 %)** |
| · a la primera | 14 | 16 | 4 | 5 | 0 | 0 | 39 |
| · media de intentos hasta probar | 1.44 | 1.06 | 1.00 | 1.00 | 3.00 | 2.00 | 1.25 |
| principal en nivel 2 | 18/21 (86 %) | 17/18 (94 %) | 4/4 (100 %) | 5/5 (100 %) | 1/1 (100 %) | 1/1 (100 %) | 46/50 (92 %) |
| aceptadas (nivel 1) | 21/21 (100 %) | 18/18 (100 %) | 4/4 (100 %) | 5/5 (100 %) | 1/1 (100 %) | 1/1 (100 %) | 50/50 (100 %) |
| · media de intentos hasta aceptar | 1.14 | 1.11 | 1.00 | 1.00 | 1.00 | 1.00 | 1.10 |
| tareas con helpers congelados | 7 | 5 | 3 | 0 | 0 | 1 | 16 |
| · con alguno sin probar | 2 | 1 | 0 | 0 | 0 | 0 | 3 |
| tokens de salida | 598993 | 177868 | 37023 | 38088 | 35581 | 27671 | 915224 |
| de ellos, razonamiento | 555328 | 171502 | 35551 | 36862 | 34080 | 26767 | 860090 |
| tokens de entrada | 206382 | 76106 | 13458 | 15574 | 10495 | 7410 | 329425 |
| coste USD | 3.299 | 0.965 | 0.199 | 0.206 | 0.188 | 0.146 | 5.003 |
| tiempo total (s) | 5108 | 1618 | 311 | 341 | 301 | 232 | 7911 |

Rechazos por causa (todos los intentos):

- `unproven`: 24
- `E000`: 4
- `E200`: 3
- `E300`: 2
- `E201`: 2
- `E102`: 2
- `contract`: 1
- `E500`: 1
- `E401`: 1
- `E404`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 3
- timeout: 2
- termination: 1
