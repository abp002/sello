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
| DA0195 | apps | solve | 1 (1) | undecided: `ensures forall n in (y + 1)..result: not (forall i in 0..l |
| DA0205 | apps | solve | 2 (1) |  |
| DA0226 | apps | solve | 1 (2) | undecided: `ensures exists x in 1..(m + 1): exists d in 1..(D + 1): (( |
| DA0244 | apps | solve | 2 (1) |  |
| DA0253 | apps | solve | 2 (4) |  |
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
| DH0021 | humaneval | largest_divisor | 2 (2) |  |
| DH0029 | humaneval | is_prime | 2 (1) |  |
| DH0040 | humaneval | decode_cyclic | 1 (1) | undecided: `ensures forall i in (len(s) - (len(s) % 3))..len(s): (resu |
| DH0101 | humaneval | make_a_pile | 2 (1) |  |
| DH0104 | humaneval | UniqueDigits | 1 (1) | z3 internal error: b'out of memory' |
| DH0137 | humaneval | can_arrange | 2 (1) |  |
| DH0152 | humaneval | x_or_y | 2 (1) |  |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 2 (1) |  |
| DJ0125 | verified_cogen | difference | 1 (1) | undecided: `prepend_new(h, dedup(t))` may violate `requires not contai |
| DJ0151 | verified_cogen | LargestPrimeFactor | 2 (1) |  |
| DJ0171 | verified_cogen | Transpose | 2 (1) |  |
| DT0088 | numpy_triple | LeftShift | 2 (1) |  |
| DT0090 | numpy_triple | RightShift | 2 (1) |  |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | z3 internal error: b'out of memory' |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 2 (3) |  |
| DT0555 | numpy_triple | unique | 1 (1) | z3 internal error: b'out of memory' |
| DV0041 | verina | MaxProfit | 2 (4) |  |
| DV0110 | verina | ElementWiseModulo | 2 (1) |  |
| DV0112 | verina | SwapFirstAndLast | 2 (2) |  |
| DV0136 | verina | Copy | 2 (3) |  |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (1) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **13/15 (87 %)** | **10/10 (100 %)** | **6/8 (75 %)** | **7/7 (100 %)** | **3/4 (75 %)** | **3/6 (50 %)** | **42/50 (84 %)** |
| · a la primera | 12 | 9 | 5 | 4 | 3 | 2 | 35 |
| · media de intentos hasta probar | 1.23 | 1.10 | 1.17 | 1.86 | 1.00 | 1.67 | 1.31 |
| principal en nivel 2 | 14/15 (93 %) | 10/10 (100 %) | 8/8 (100 %) | 7/7 (100 %) | 4/4 (100 %) | 3/6 (50 %) | 46/50 (92 %) |
| aceptadas (nivel 1) | 15/15 (100 %) | 10/10 (100 %) | 8/8 (100 %) | 7/7 (100 %) | 4/4 (100 %) | 5/6 (83 %) | 49/50 (98 %) |
| · media de intentos hasta aceptar | 1.13 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.04 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 57712 | 9715 | 24456 | 18135 | 11895 | 31432 | 153345 |
| de ellos, razonamiento | 31519 | 5584 | 13148 | 9958 | 7132 | 16445 | 83786 |
| tokens de entrada | 140391 | 49340 | 85911 | 63461 | 38927 | 104542 | 482572 |
| coste USD | 1.139 | 0.294 | 0.588 | 0.435 | 0.275 | 0.709 | 3.440 |
| tiempo total (s) | 562 | 120 | 240 | 176 | 117 | 304 | 1519 |

Rechazos por causa (todos los intentos):

- `unproven`: 45
- `E201`: 5
- `E200`: 3

Por qué no se prueban las aceptadas (último intento):

- undecided: 4
- z3: 3
