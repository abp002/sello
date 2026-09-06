# Vericoding en Sello 2026-09-06-1459 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos.

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
| DD0109 | dafnybench | mroot1 | 1 (1) | mutual recursion: termination not checked |
| DD0159 | dafnybench | Comb | 2 (1) |  |
| DD0225 | dafnybench | ComputePower | 2 (1) |  |
| DD0342 | dafnybench | calcR | 2 (1) |  |
| DD0429 | dafnybench | gcdI | 2 (1) |  |
| DD0435 | dafnybench | q | ✗ (5) |  |
| DD0682 | dafnybench | CubeVolume | 2 (1) |  |
| DD0722 | dafnybench | LastDigit | 2 (1) |  |
| DD0730 | dafnybench | MinLengthSublist | ✗ (5) |  |
| DD0740 | dafnybench | DifferenceSumCubesAndSumNumbers | ✗ (5) |  |
| DD0752 | dafnybench | SquarePyramidSurfaceArea | ✗ (5) |  |
| DD0791 | dafnybench | IsMonthWith30Days | ✗ (5) |  |
| DD0826 | dafnybench | ClimbStairs | ✗ (5) |  |
| DD0848 | dafnybench | HoareTripleReqEns | ✗ (5) |  |
| DH0048 | humaneval | fib4 | ✗ (5) |  |
| DH0065 | humaneval | fibfib | ✗ (5) |  |
| DH0127 | humaneval | next_odd_collatz_iter | ✗ (5) |  |
| DH0140 | humaneval | is_equal_to_sum_even | ✗ (5) |  |
| DJ0147 | verified_cogen | IntegerSquareRoot | ✗ (5) |  |
| DV0057 | verina | NthUglyNumber | ✗ (5) |  |
| DV0088 | verina | MyMin | ✗ (5) |  |
| DV0106 | verina | IsEven | ✗ (5) |  |
| DV0145 | verina | SquareRoot | ✗ (5) |  |
| DV0178 | verina | Triple | ✗ (5) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | bignum | total |
|---|---|---|---|---|---|---|---|
| tareas | 21 | 18 | 4 | 5 | 1 | 1 | 50 |
| **probadas (nivel 2)** | **16/21 (76 %)** | **10/18 (56 %)** | **0/4 (0 %)** | **0/5 (0 %)** | **0/1 (0 %)** | **1/1 (100 %)** | **27/50 (54 %)** |
| · a la primera | 14 | 10 | 0 | 0 | 0 | 0 | 24 |
| · media de intentos hasta probar | 1.44 | 1.00 | 0.00 | 0.00 | 0.00 | 2.00 | 1.30 |
| principal en nivel 2 | 18/21 (86 %) | 11/18 (61 %) | 0/4 (0 %) | 0/5 (0 %) | 0/1 (0 %) | 1/1 (100 %) | 30/50 (60 %) |
| aceptadas (nivel 1) | 21/21 (100 %) | 11/18 (61 %) | 0/4 (0 %) | 0/5 (0 %) | 0/1 (0 %) | 1/1 (100 %) | 33/50 (66 %) |
| · media de intentos hasta aceptar | 1.14 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.09 |
| tareas con helpers congelados | 7 | 5 | 3 | 0 | 0 | 1 | 16 |
| · con alguno sin probar | 2 | 1 | 0 | 0 | 0 | 0 | 3 |
| tokens de salida | 598993 | 114079 | 0 | 0 | 0 | 27671 | 740743 |
| de ellos, razonamiento | 555328 | 109386 | 0 | 0 | 0 | 26767 | 691481 |
| tokens de entrada | 206382 | 49013 | 0 | 0 | 0 | 7410 | 262805 |
| coste USD | 3.299 | 0.619 | 0.000 | 0.000 | 0.000 | 0.146 | 4.064 |
| tiempo total (s) | 5108 | 1054 | 30 | 40 | 8 | 232 | 6472 |

Rechazos por causa (todos los intentos):

- `E000`: 88
- `unproven`: 21
- `E300`: 4
- `E102`: 3
- `E200`: 3
- `E201`: 1
- `contract`: 1
- `E500`: 1
- `E100`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 2
- timeout: 2
- termination: 1
- mutual recursion: 1
