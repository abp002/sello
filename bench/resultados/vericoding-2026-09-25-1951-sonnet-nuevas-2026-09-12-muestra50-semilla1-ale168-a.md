# Vericoding en Sello 2026-09-25-1951 · modelo `sonnet` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0002 | apps | solve | 2 (1) |  |
| DA0018 | apps | solve | 2 (1) |  |
| DA0045 | apps | solve | 2 (1) |  |
| DA0055 | apps | solve | 2 (1) |  |
| DA0070 | apps | solve | 2 (1) |  |
| DA0105 | apps | solve | 2 (1) |  |
| DA0144 | apps | solve | 2 (1) |  |
| DA0195 | apps | solve | 1 (1) | undecided: `ensures forall m in n..result: not ok4(m)` |
| DA0205 | apps | solve | 2 (1) |  |
| DA0226 | apps | solve | 1 (1) | undecided: `ensures forall a in 1..(x + 1): forall e in 1..(D + 1): (( |
| DA0244 | apps | solve | 2 (1) |  |
| DA0253 | apps | solve | 2 (2) |  |
| DA0285 | apps | solve | 2 (1) |  |
| DA0384 | apps | solve | 2 (1) |  |
| DA0487 | apps | solve | 2 (1) |  |
| DD0535 | dafnybench | IsPrime | 2 (1) |  |
| DD0644 | dafnybench | IsNonPrime | 2 (1) |  |
| DD0653 | dafnybench | ContainsSequence | 2 (1) |  |
| DD0663 | dafnybench | SmallestListLength | 2 (1) |  |
| DD0703 | dafnybench | ElementAtIndexAfterRotation | 2 (1) |  |
| DD0715 | dafnybench | AnyValueExists | 2 (1) |  |
| DD0750 | dafnybench | Interleave | 2 (2) |  |
| DD0753 | dafnybench | SplitAndAppend | 2 (1) |  |
| DD0763 | dafnybench | IsPrime | 2 (1) |  |
| DD0767 | dafnybench | ElementWiseDivide | 2 (1) |  |
| DH0021 | humaneval | largest_divisor | 2 (1) |  |
| DH0029 | humaneval | is_prime | 2 (1) |  |
| DH0040 | humaneval | decode_cyclic | 1 (1) | undecided: `ensures forall i in (len(s) - (len(s) % 3))..len(s): (resu |
| DH0101 | humaneval | make_a_pile | 2 (1) |  |
| DH0104 | humaneval | UniqueDigits | 1 (1) | undecided: `ensures forall i in 0..len(result): forall j in (i + 1)..l |
| DH0137 | humaneval | can_arrange | 2 (1) |  |
| DH0152 | humaneval | x_or_y | 2 (1) |  |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 2 (1) |  |
| DJ0125 | verified_cogen | difference | 2 (4) |  |
| DJ0151 | verified_cogen | LargestPrimeFactor | 2 (1) |  |
| DJ0171 | verified_cogen | Transpose | 2 (2) |  |
| DT0088 | numpy_triple | LeftShift | 2 (1) |  |
| DT0090 | numpy_triple | RightShift | 2 (1) |  |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | z3 internal error: b'out of memory' |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 2 (5) |  |
| DT0555 | numpy_triple | unique | 1 (1) | z3 internal error: b'out of memory' |
| DV0041 | verina | MaxProfit | 2 (5) |  |
| DV0110 | verina | ElementWiseModulo | 2 (1) |  |
| DV0112 | verina | SwapFirstAndLast | 2 (2) |  |
| DV0136 | verina | Copy | 2 (1) |  |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (1) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **13/15 (87 %)** | **10/10 (100 %)** | **6/8 (75 %)** | **7/7 (100 %)** | **4/4 (100 %)** | **3/6 (50 %)** | **43/50 (86 %)** |
| · a la primera | 12 | 9 | 6 | 5 | 2 | 2 | 36 |
| · media de intentos hasta probar | 1.08 | 1.10 | 1.00 | 1.71 | 2.00 | 2.33 | 1.35 |
| principal en nivel 2 | 13/15 (87 %) | 10/10 (100 %) | 7/8 (88 %) | 7/7 (100 %) | 4/4 (100 %) | 3/6 (50 %) | 44/50 (88 %) |
| aceptadas (nivel 1) | 15/15 (100 %) | 10/10 (100 %) | 8/8 (100 %) | 7/7 (100 %) | 4/4 (100 %) | 5/6 (83 %) | 49/50 (98 %) |
| · media de intentos hasta aceptar | 1.07 | 1.00 | 1.00 | 1.00 | 1.75 | 1.00 | 1.08 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 50705 | 10593 | 25076 | 20607 | 13483 | 31014 | 151478 |
| de ellos, razonamiento | 26484 | 5983 | 13783 | 11753 | 6763 | 17176 | 81942 |
| tokens de entrada | 127053 | 48988 | 81025 | 58837 | 39608 | 112296 | 467807 |
| coste USD | 1.015 | 0.302 | 0.575 | 0.420 | 0.293 | 0.740 | 3.346 |
| tiempo total (s) | 493 | 132 | 243 | 202 | 124 | 307 | 1500 |

Rechazos por causa (todos los intentos):

- `unproven`: 38
- `E201`: 7
- `E401`: 3
- `E200`: 1
- `E300`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 4
- z3: 2
