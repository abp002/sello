# Vericoding en Sello 2026-09-06-1502 · modelo `sonnet` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0001 | apps | solve | 2 (2) |  |
| DA0008 | apps | solve | 2 (4) |  |
| DA0023 | apps | solve | 1 (1) | undecided: `ensures ((not (((a - 1) / (m * k)) == ((b - 1) / (m * k))) |
| DA0026 | apps | solve | 2 (1) |  |
| DA0029 | apps | solve | 2 (5) |  |
| DA0069 | apps | solve | 2 (1) |  |
| DA0099 | apps | solve | 2 (2) |  |
| DA0122 | apps | solve | 2 (3) |  |
| DA0140 | apps | MinBacteria | 2 (1) |  |
| DA0190 | apps | solve | 2 (1) |  |
| DA0399 | apps | solve | 2 (1) |  |
| DA0419 | apps | solve | 2 (1) |  |
| DA0455 | apps | SolveCookieDistribution | 2 (1) |  |
| DA0476 | apps | solve | 2 (1) |  |
| DA0478 | apps | solve | 2 (1) |  |
| DA0522 | apps | Solve | 2 (1) |  |
| DA0529 | apps | solve | 2 (1) |  |
| DA0552 | apps | CountTriples | 1 (1) | timeout |
| DA0615 | apps | CalculateBlackSquares | 2 (1) |  |
| DA0656 | apps | solve | 2 (1) |  |
| DA0674 | apps | solve | 2 (1) |  |
| DB0020 | bignum | ModExpPow2_int | 2 (4) |  |
| DD0065 | dafnybench | ComputeIsEven | 2 (1) |  |
| DD0080 | dafnybench | M | 2 (1) |  |
| DD0092 | dafnybench | Triple | 2 (1) |  |
| DD0094 | dafnybench | Triple | 2 (1) |  |
| DD0109 | dafnybench | mroot1 | 2 (1) |  |
| DD0159 | dafnybench | Comb | 2 (1) |  |
| DD0225 | dafnybench | ComputePower | 2 (1) |  |
| DD0342 | dafnybench | calcR | 2 (1) |  |
| DD0429 | dafnybench | gcdI | 2 (1) |  |
| DD0435 | dafnybench | q | ✗ (5) |  |
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
| DH0127 | humaneval | next_odd_collatz_iter | 2 (2) |  |
| DH0140 | humaneval | is_equal_to_sum_even | 2 (1) |  |
| DJ0147 | verified_cogen | IntegerSquareRoot | 2 (2) |  |
| DV0057 | verina | NthUglyNumber | 2 (1) |  |
| DV0088 | verina | MyMin | 2 (1) |  |
| DV0106 | verina | IsEven | 2 (1) |  |
| DV0145 | verina | SquareRoot | 2 (1) |  |
| DV0178 | verina | Triple | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | bignum | total |
|---|---|---|---|---|---|---|---|
| tareas | 21 | 18 | 4 | 5 | 1 | 1 | 50 |
| **probadas (nivel 2)** | **19/21 (90 %)** | **16/18 (89 %)** | **4/4 (100 %)** | **5/5 (100 %)** | **1/1 (100 %)** | **1/1 (100 %)** | **46/50 (92 %)** |
| · a la primera | 14 | 16 | 3 | 5 | 0 | 0 | 38 |
| · media de intentos hasta probar | 1.58 | 1.00 | 1.25 | 1.00 | 2.00 | 4.00 | 1.35 |
| principal en nivel 2 | 20/21 (95 %) | 16/18 (89 %) | 4/4 (100 %) | 5/5 (100 %) | 1/1 (100 %) | 1/1 (100 %) | 47/50 (94 %) |
| aceptadas (nivel 1) | 21/21 (100 %) | 17/18 (94 %) | 4/4 (100 %) | 5/5 (100 %) | 1/1 (100 %) | 1/1 (100 %) | 49/50 (98 %) |
| · media de intentos hasta aceptar | 1.10 | 1.06 | 1.00 | 1.00 | 1.00 | 2.00 | 1.08 |
| tareas con helpers congelados | 7 | 5 | 3 | 0 | 0 | 1 | 16 |
| · con alguno sin probar | 2 | 1 | 0 | 0 | 0 | 0 | 3 |
| tokens de salida | 291962 | 109799 | 6316 | 24359 | 8316 | 51846 | 492598 |
| de ellos, razonamiento | 246141 | 102168 | 3878 | 22655 | 7396 | 48881 | 431119 |
| tokens de entrada | 219647 | 109762 | 21981 | 19943 | 8686 | 19683 | 399702 |
| coste USD | 3.777 | 1.522 | 0.151 | 0.323 | 0.118 | 0.597 | 6.489 |
| tiempo total (s) | 2842 | 1213 | 66 | 254 | 85 | 502 | 4960 |

Rechazos por causa (todos los intentos):

- `unproven`: 26
- `E201`: 5
- `E200`: 3
- `E401`: 1
- `E404`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 2
- timeout: 1
