# Vericoding en Sello 2026-09-25-1959 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0002 | apps | solve | 2 (1) |  |
| DA0018 | apps | solve | 2 (2) |  |
| DA0045 | apps | solve | 1 (2) | undecided: `ensures forall k in 0..(3 + 1): (((if ((if (((-x + (90 * r |
| DA0055 | apps | solve | 2 (1) |  |
| DA0070 | apps | solve | 2 (1) |  |
| DA0105 | apps | solve | 2 (1) |  |
| DA0144 | apps | solve | 2 (2) |  |
| DA0195 | apps | solve | ✗ (5) |  |
| DA0205 | apps | solve | 2 (5) |  |
| DA0226 | apps | solve | 1 (3) | undecided: `ensures exists x2 in 1..(M + 1): exists d2 in 1..(D + 1):  |
| DA0244 | apps | solve | 2 (1) |  |
| DA0253 | apps | solve | 2 (4) |  |
| DA0285 | apps | solve | 2 (2) |  |
| DA0384 | apps | solve | 2 (1) |  |
| DA0487 | apps | solve | 2 (2) |  |
| DD0535 | dafnybench | IsPrime | 2 (1) |  |
| DD0644 | dafnybench | IsNonPrime | 2 (1) |  |
| DD0653 | dafnybench | ContainsSequence | 2 (1) |  |
| DD0663 | dafnybench | SmallestListLength | 2 (5) |  |
| DD0703 | dafnybench | ElementAtIndexAfterRotation | 2 (2) |  |
| DD0715 | dafnybench | AnyValueExists | 2 (1) |  |
| DD0750 | dafnybench | Interleave | 2 (5) |  |
| DD0753 | dafnybench | SplitAndAppend | 2 (4) |  |
| DD0763 | dafnybench | IsPrime | 2 (1) |  |
| DD0767 | dafnybench | ElementWiseDivide | 2 (1) |  |
| DH0021 | humaneval | largest_divisor | 2 (1) |  |
| DH0029 | humaneval | is_prime | 2 (1) |  |
| DH0040 | humaneval | decode_cyclic | 1 (5) | undecided: `ensures forall i in (len(s) - (len(s) % 3))..len(s): (resu |
| DH0101 | humaneval | make_a_pile | 2 (1) |  |
| DH0104 | humaneval | UniqueDigits | 1 (1) | undecided: `ensures forall e in xs: contains(result, e)` |
| DH0137 | humaneval | can_arrange | ✗ (5) |  |
| DH0152 | humaneval | x_or_y | 2 (1) |  |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 2 (1) |  |
| DJ0125 | verified_cogen | difference | 1 (3) | undecided: `ensures forall i in 0..len(xs): (contains(ys, xs[i]) or co |
| DJ0151 | verified_cogen | LargestPrimeFactor | 1 (3) | undecided: `ensures ((result == 1) or (forall k in 2..result: ((result |
| DJ0171 | verified_cogen | Transpose | 1 (4) | undecided: `ensures forall i in 0..len(result): forall j in 0..len(res |
| DT0088 | numpy_triple | LeftShift | 2 (3) |  |
| DT0090 | numpy_triple | RightShift | 2 (4) |  |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | z3 internal error: b'out of memory' |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 1 (1) | undecided: `ensures forall i in 0..len(result): (result[i] == (x1[i] a |
| DT0555 | numpy_triple | unique | 1 (3) | undecided: `ensures forall i in 0..len(result): forall j in (i + 1)..l |
| DV0041 | verina | MaxProfit | 1 (3) | undecided: `ensures ((((result == 0) and (len(prices) == 0)) or (exist |
| DV0110 | verina | ElementWiseModulo | 2 (1) |  |
| DV0112 | verina | SwapFirstAndLast | 2 (3) |  |
| DV0136 | verina | Copy | 2 (2) |  |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (4) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **12/15 (80 %)** | **10/10 (100 %)** | **5/8 (62 %)** | **6/7 (86 %)** | **1/4 (25 %)** | **2/6 (33 %)** | **36/50 (72 %)** |
| · a la primera | 6 | 6 | 5 | 3 | 1 | 0 | 21 |
| · media de intentos hasta probar | 1.92 | 2.20 | 1.00 | 2.00 | 1.00 | 3.50 | 1.94 |
| principal en nivel 2 | 12/15 (80 %) | 10/10 (100 %) | 6/8 (75 %) | 6/7 (86 %) | 4/4 (100 %) | 2/6 (33 %) | 40/50 (80 %) |
| aceptadas (nivel 1) | 14/15 (93 %) | 10/10 (100 %) | 7/8 (88 %) | 7/7 (100 %) | 4/4 (100 %) | 5/6 (83 %) | 47/50 (94 %) |
| · media de intentos hasta aceptar | 1.64 | 1.80 | 1.57 | 1.86 | 2.75 | 1.40 | 1.77 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 574265 | 251700 | 326016 | 212729 | 247007 | 412215 | 2023932 |
| de ellos, razonamiento | 542410 | 241773 | 310764 | 199500 | 233837 | 391144 | 1919428 |
| tokens de entrada | 167190 | 85081 | 84793 | 71379 | 86167 | 131394 | 626004 |
| coste USD | 3.131 | 1.370 | 1.762 | 1.182 | 1.359 | 2.263 | 11.067 |
| tiempo total (s) | 4333 | 2120 | 2578 | 1579 | 4386 | 5645 | 20641 |

Rechazos por causa (todos los intentos):

- `unproven`: 36
- `E401`: 30
- `E000`: 12
- `E102`: 9
- `E201`: 6
- `E200`: 3
- `E300`: 3
- `E100`: 2
- `contract`: 2
- `E404`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 10
- z3: 1
