# Vericoding en Sello 2026-09-25-1959 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0002 | apps | solve | 2 (1) |  |
| DA0018 | apps | solve | 2 (1) |  |
| DA0045 | apps | solve | 1 (1) | undecided: `ensures forall k in 0..(3 + 1): (((if ((if (((-x + (90 * r |
| DA0055 | apps | solve | 2 (2) |  |
| DA0070 | apps | solve | 2 (1) |  |
| DA0105 | apps | solve | 2 (1) |  |
| DA0144 | apps | solve | 2 (2) |  |
| DA0195 | apps | solve | 1 (3) | termination: no argument decreases at every recursive call |
| DA0205 | apps | solve | 1 (2) | timeout |
| DA0226 | apps | solve | ✗ (5) |  |
| DA0244 | apps | solve | 2 (1) |  |
| DA0253 | apps | solve | 2 (4) |  |
| DA0285 | apps | solve | 2 (1) |  |
| DA0384 | apps | solve | 2 (1) |  |
| DA0487 | apps | solve | 2 (1) |  |
| DD0535 | dafnybench | IsPrime | 2 (1) |  |
| DD0644 | dafnybench | IsNonPrime | 2 (2) |  |
| DD0653 | dafnybench | ContainsSequence | 2 (1) |  |
| DD0663 | dafnybench | SmallestListLength | 2 (2) |  |
| DD0703 | dafnybench | ElementAtIndexAfterRotation | 2 (1) |  |
| DD0715 | dafnybench | AnyValueExists | 2 (1) |  |
| DD0750 | dafnybench | Interleave | 2 (1) |  |
| DD0753 | dafnybench | SplitAndAppend | 2 (1) |  |
| DD0763 | dafnybench | IsPrime | 2 (1) |  |
| DD0767 | dafnybench | ElementWiseDivide | 2 (1) |  |
| DH0021 | humaneval | largest_divisor | 2 (4) |  |
| DH0029 | humaneval | is_prime | 2 (1) |  |
| DH0040 | humaneval | decode_cyclic | 1 (5) | undecided: `ensures forall i in (len(s) - (len(s) % 3))..len(s): (resu |
| DH0101 | humaneval | make_a_pile | 2 (1) |  |
| DH0104 | humaneval | UniqueDigits | 1 (1) | undecided: `ensures forall e in xs: ((not HasNoEvenDigit(e)) or contai |
| DH0137 | humaneval | can_arrange | ✗ (5) |  |
| DH0152 | humaneval | x_or_y | 2 (1) |  |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 2 (1) |  |
| DJ0125 | verified_cogen | difference | 1 (2) | undecided: `ensures forall i in 0..len(arr2): ((not (not contains(arr1 |
| DJ0151 | verified_cogen | LargestPrimeFactor | 1 (2) | undecided: `trialDivision((n / d), d)` may violate `requires forall i  |
| DJ0171 | verified_cogen | Transpose | 2 (2) |  |
| DT0088 | numpy_triple | LeftShift | 2 (5) |  |
| DT0090 | numpy_triple | RightShift | 2 (3) |  |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | z3 internal error: b'out of memory' |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 1 (1) | undecided: `ensures forall i in 0..n: (result[i] == (x1[i] and x2[i])) |
| DT0555 | numpy_triple | unique | 1 (1) | undecided: `cons_sorted(h, insert_sorted(x, t))` may violate `requires |
| DV0041 | verina | MaxProfit | 1 (2) | undecided: `ensures ((((result == 0) and (len(prices) == 0)) or (exist |
| DV0110 | verina | ElementWiseModulo | 2 (2) |  |
| DV0112 | verina | SwapFirstAndLast | 2 (2) |  |
| DV0136 | verina | Copy | 1 (2) | undecided: `ensures forall i in 0..remaining: (result[(d_start + i)] = |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (2) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **11/15 (73 %)** | **10/10 (100 %)** | **5/8 (62 %)** | **5/7 (71 %)** | **2/4 (50 %)** | **2/6 (33 %)** | **35/50 (70 %)** |
| · a la primera | 8 | 8 | 4 | 2 | 1 | 0 | 23 |
| · media de intentos hasta probar | 1.45 | 1.20 | 1.60 | 1.60 | 1.50 | 4.00 | 1.57 |
| principal en nivel 2 | 13/15 (87 %) | 10/10 (100 %) | 6/8 (75 %) | 6/7 (86 %) | 3/4 (75 %) | 3/6 (50 %) | 41/50 (82 %) |
| aceptadas (nivel 1) | 14/15 (93 %) | 10/10 (100 %) | 7/8 (88 %) | 7/7 (100 %) | 4/4 (100 %) | 5/6 (83 %) | 47/50 (94 %) |
| · media de intentos hasta aceptar | 1.43 | 1.20 | 1.71 | 1.57 | 1.75 | 1.00 | 1.43 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 649938 | 124860 | 418658 | 265744 | 221640 | 405656 | 2086496 |
| de ellos, razonamiento | 617953 | 120924 | 398289 | 253750 | 213001 | 385567 | 1989484 |
| tokens de entrada | 171045 | 42978 | 104353 | 73818 | 76049 | 128487 | 596730 |
| coste USD | 3.533 | 0.667 | 2.261 | 1.451 | 1.201 | 2.239 | 11.353 |
| tiempo total (s) | 5194 | 1047 | 3311 | 1896 | 5423 | 4425 | 21297 |

Rechazos por causa (todos los intentos):

- `unproven`: 46
- `E201`: 14
- `E000`: 9
- `E300`: 8
- `E100`: 4
- `E401`: 3
- `E500`: 3
- `contract`: 3
- `E102`: 2
- `E403`: 1
- `E200`: 1
- `E404`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 9
- termination: 1
- timeout: 1
- z3: 1
