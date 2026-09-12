# Vericoding en Sello 2026-09-12-0937 · modelo `sonnet` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0002 | apps | solve | 2 (1) |  |
| DA0018 | apps | solve | 2 (1) |  |
| DA0045 | apps | solve | 2 (1) |  |
| DA0055 | apps | solve | 2 (1) |  |
| DA0070 | apps | solve | 2 (1) |  |
| DA0105 | apps | solve | 2 (1) |  |
| DA0144 | apps | solve | 1 (1) | undecided: `ensures ((result == -1) or (((result > 0) and ((result % m |
| DA0195 | apps | solve | 1 (2) | undecided: `ensures (result == (forall i in 0..len(xs): forall j in (i |
| DA0205 | apps | solve | 1 (1) | timeout |
| DA0226 | apps | solve | 1 (1) | undecided: `ensures forall x in 1..(M + 1): forall d in 1..(D + 1): (( |
| DA0244 | apps | solve | 2 (1) |  |
| DA0253 | apps | solve | 2 (2) |  |
| DA0285 | apps | solve | 2 (3) |  |
| DA0384 | apps | solve | 2 (1) |  |
| DA0487 | apps | solve | 2 (1) |  |
| DD0535 | dafnybench | IsPrime | 1 (1) | undecided: `ensures (result == ((m > 1) and (forall j in 2..m: ((m % j |
| DD0644 | dafnybench | IsNonPrime | 1 (1) | undecided: `ensures (result == (forall j in 2..k: ((n % j) != 0)))` |
| DD0653 | dafnybench | ContainsSequence | 2 (1) |  |
| DD0663 | dafnybench | SmallestListLength | 2 (2) |  |
| DD0703 | dafnybench | ElementAtIndexAfterRotation | 2 (2) |  |
| DD0715 | dafnybench | AnyValueExists | 2 (2) |  |
| DD0750 | dafnybench | Interleave | 2 (2) |  |
| DD0753 | dafnybench | SplitAndAppend | 1 (1) | undecided: `ensures forall i in 0..len(l): (result[i] == l[((i + n) %  |
| DD0763 | dafnybench | IsPrime | 1 (1) | undecided: `ensures (result == (forall j in k..n: ((n % j) != 0)))` |
| DD0767 | dafnybench | ElementWiseDivide | 2 (1) |  |
| DH0021 | humaneval | largest_divisor | 1 (1) | undecided: `ensures ((n % result) == 0)` |
| DH0029 | humaneval | is_prime | 1 (1) | undecided: `ensures (result == ((n >= 2) and (forall k in 2..n: ((n %  |
| DH0040 | humaneval | decode_cyclic | 2 (4) |  |
| DH0101 | humaneval | make_a_pile | 2 (1) |  |
| DH0104 | humaneval | UniqueDigits | 1 (1) | timeout: the solver did not answer |
| DH0137 | humaneval | can_arrange | 2 (3) |  |
| DH0152 | humaneval | x_or_y | 1 (1) | undecided: `ensures (result == (forall i in j..k: ((n % i) != 0)))` |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 1 (1) | undecided: `ensures (result == (forall i in k..n: not ((n % i) == 0))) |
| DJ0125 | verified_cogen | difference | 1 (2) | timeout: the prover did not answer |
| DJ0151 | verified_cogen | LargestPrimeFactor | 1 (1) | undecided: `ensures ((x % result) == 0)` |
| DJ0171 | verified_cogen | Transpose | 2 (4) |  |
| DT0088 | numpy_triple | LeftShift | 2 (1) |  |
| DT0090 | numpy_triple | RightShift | 2 (1) |  |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | undecided: `ensures forall i in 0..len(a): forall j in 0..8: (result[( |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 1 (1) | undecided: `ensures forall i in 0..len(result): (result[i] == (x1[i] a |
| DT0555 | numpy_triple | unique | 1 (1) | timeout: the solver did not answer |
| DV0041 | verina | MaxProfit | 1 (1) | undecided: `scan(all, t, true, if (h <= curMin) then h else curMin, if |
| DV0110 | verina | ElementWiseModulo | 1 (1) | undecided: `ensures forall i in 0..len(result): (result[i] == (a[i] %  |
| DV0112 | verina | SwapFirstAndLast | 2 (3) |  |
| DV0136 | verina | Copy | 2 (2) |  |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (1) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **11/15 (73 %)** | **6/10 (60 %)** | **4/8 (50 %)** | **5/7 (71 %)** | **1/4 (25 %)** | **2/6 (33 %)** | **29/50 (58 %)** |
| · a la primera | 9 | 2 | 2 | 3 | 0 | 2 | 18 |
| · media de intentos hasta probar | 1.27 | 1.67 | 2.25 | 1.60 | 4.00 | 1.00 | 1.62 |
| principal en nivel 2 | 13/15 (87 %) | 9/10 (90 %) | 7/8 (88 %) | 6/7 (86 %) | 3/4 (75 %) | 3/6 (50 %) | 41/50 (82 %) |
| aceptadas (nivel 1) | 15/15 (100 %) | 10/10 (100 %) | 8/8 (100 %) | 7/7 (100 %) | 4/4 (100 %) | 5/6 (83 %) | 49/50 (98 %) |
| · media de intentos hasta aceptar | 1.27 | 1.20 | 1.00 | 1.29 | 2.00 | 1.00 | 1.24 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 330633 | 167085 | 332552 | 188406 | 207713 | 239412 | 1465801 |
| de ellos, razonamiento | 303347 | 154520 | 312721 | 173852 | 192493 | 224225 | 1361158 |
| tokens de entrada | 174528 | 139776 | 144737 | 89563 | 97155 | 111296 | 757055 |
| coste USD | 4.090 | 2.339 | 4.035 | 2.323 | 2.553 | 2.903 | 18.244 |
| tiempo total (s) | 3367 | 1779 | 3426 | 1926 | 2093 | 2467 | 15058 |

Rechazos por causa (todos los intentos):

- `unproven`: 91
- `E401`: 22
- `E201`: 3
- `E200`: 2
- `contract`: 2
- `E300`: 1
- `E500`: 1
- `E100`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 16
- timeout: 4
