# Vericoding en Sello 2026-09-12-1048 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0002 | apps | solve | 2 (1) |  |
| DA0018 | apps | solve | 2 (2) |  |
| DA0045 | apps | solve | 1 (2) | undecided: `ensures forall k in 0..(3 + 1): (((if ((if (((-x + (90 * r |
| DA0055 | apps | solve | 2 (1) |  |
| DA0070 | apps | solve | 2 (1) |  |
| DA0105 | apps | solve | 2 (1) |  |
| DA0144 | apps | solve | 1 (1) | undecided: `ensures ((result == -1) or ((((result % divisor) == 0) and |
| DA0195 | apps | solve | 1 (4) | undecided: `solveHelperWithBound((y + 1), (bound - 1))` may violate `r |
| DA0205 | apps | solve | 1 (1) | undecided: `ensures (((n + (result / m)) - result) <= 0)` |
| DA0226 | apps | solve | ✗ (5) |  |
| DA0244 | apps | solve | 2 (3) |  |
| DA0253 | apps | solve | 1 (3) | undecided: `ensures ((not ((N == 1) and (S == A[0]))) or (result == (i |
| DA0285 | apps | solve | 2 (2) |  |
| DA0384 | apps | solve | 2 (1) |  |
| DA0487 | apps | solve | 2 (1) |  |
| DD0535 | dafnybench | IsPrime | 1 (1) | undecided: `ensures (result == (forall k in start..m: ((m % k) != 0))) |
| DD0644 | dafnybench | IsNonPrime | 1 (1) | undecided: `ensures (result == (exists i in 2..limit: ((n % i) == 0))) |
| DD0653 | dafnybench | ContainsSequence | 2 (3) |  |
| DD0663 | dafnybench | SmallestListLength | 2 (3) |  |
| DD0703 | dafnybench | ElementAtIndexAfterRotation | 1 (3) | undecided: `ensures (result == l[(((index - n) + len(l)) % len(l))])` |
| DD0715 | dafnybench | AnyValueExists | 2 (3) |  |
| DD0750 | dafnybench | Interleave | 2 (3) |  |
| DD0753 | dafnybench | SplitAndAppend | 1 (2) | undecided: `ensures forall j in 0..len(result): (result[j] == rotated_ |
| DD0763 | dafnybench | IsPrime | 1 (1) | undecided: `ensures (result == (forall i in start..end: ((n % i) != 0) |
| DD0767 | dafnybench | ElementWiseDivide | 2 (3) |  |
| DH0021 | humaneval | largest_divisor | 1 (2) | undecided: `ensures (result < n)` |
| DH0029 | humaneval | is_prime | 1 (1) | undecided: `ensures (result == (forall k in d..(max + 1): ((n % k) !=  |
| DH0040 | humaneval | decode_cyclic | 1 (3) | undecided: `ensures forall i in (len(s) - (len(s) % 3))..len(s): (resu |
| DH0101 | humaneval | make_a_pile | 2 (3) |  |
| DH0104 | humaneval | UniqueDigits | 1 (2) | timeout: the solver did not answer |
| DH0137 | humaneval | can_arrange | ✗ (5) |  |
| DH0152 | humaneval | x_or_y | 1 (1) | undecided: `ensures ((not (result == true)) or (forall i in k..n: ((n  |
| DH0160 | humaneval | eat | 2 (1) |  |
| DJ0110 | verified_cogen | PrimeNum | 1 (1) | undecided: `ensures (result == (exists i in start..end: ((n % i) == 0) |
| DJ0125 | verified_cogen | difference | 1 (3) | timeout: the solver did not answer |
| DJ0151 | verified_cogen | LargestPrimeFactor | 1 (1) | undecided: `Helper((m / d), d, d)` may violate `requires ((lastPrime = |
| DJ0171 | verified_cogen | Transpose | ✗ (5) |  |
| DT0088 | numpy_triple | LeftShift | 1 (2) | undecided: `ensures forall i in 0..len(result): ((not ((x1[i] > 0) and |
| DT0090 | numpy_triple | RightShift | 1 (1) | undecided: `ensures forall i in 0..len(result): if (result[i] >= 0) th |
| DT0091 | numpy_triple | numpy_unpackbits | 1 (1) | undecided: division by zero in `(a[i] / pow2((7 - j)))` |
| DT0258 | numpy_triple | NumpyBitwiseOr | ✗ (5) |  |
| DT0276 | numpy_triple | LogicalAnd | 1 (2) | undecided: `ensures forall i in 0..len(result): (result[i] == (x1[i] a |
| DT0555 | numpy_triple | unique | 1 (1) | timeout: the solver did not answer |
| DV0041 | verina | MaxProfit | 1 (2) | timeout: the solver did not answer |
| DV0110 | verina | ElementWiseModulo | 2 (5) |  |
| DV0112 | verina | SwapFirstAndLast | 2 (2) |  |
| DV0136 | verina | Copy | 2 (5) |  |
| DV0138 | verina | DoubleArrayElements | 2 (1) |  |
| DV0157 | verina | ModifyArrayElement | 2 (2) |  |
| DV0162 | verina | RemoveFront | 2 (1) |  |

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | total |
|---|---|---|---|---|---|---|---|
| tareas | 15 | 10 | 8 | 7 | 4 | 6 | 50 |
| **probadas (nivel 2)** | **9/15 (60 %)** | **5/10 (50 %)** | **2/8 (25 %)** | **6/7 (86 %)** | **0/4 (0 %)** | **0/6 (0 %)** | **22/50 (44 %)** |
| · a la primera | 6 | 0 | 1 | 2 | 0 | 0 | 9 |
| · media de intentos hasta probar | 1.44 | 3.00 | 2.00 | 2.67 | 0.00 | 0.00 | 2.18 |
| principal en nivel 2 | 12/15 (80 %) | 10/10 (100 %) | 5/8 (62 %) | 6/7 (86 %) | 3/4 (75 %) | 1/6 (17 %) | 37/50 (74 %) |
| aceptadas (nivel 1) | 14/15 (93 %) | 10/10 (100 %) | 7/8 (88 %) | 7/7 (100 %) | 3/4 (75 %) | 5/6 (83 %) | 46/50 (92 %) |
| · media de intentos hasta aceptar | 1.71 | 1.90 | 1.71 | 2.14 | 1.67 | 1.40 | 1.78 |
| tareas con helpers congelados | 1 | 0 | 1 | 0 | 0 | 3 | 5 |
| · con alguno sin probar | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tokens de salida | 715501 | 508673 | 508911 | 282907 | 323582 | 415892 | 2755466 |
| de ellos, razonamiento | 675073 | 488242 | 487507 | 270071 | 310873 | 393417 | 2625183 |
| tokens de entrada | 191275 | 153361 | 137466 | 83468 | 80363 | 127783 | 773716 |
| coste USD | 4.070 | 2.903 | 2.893 | 1.628 | 1.825 | 2.427 | 15.744 |
| tiempo total (s) | 4989 | 3773 | 3762 | 2193 | 2443 | 3069 | 20227 |

Rechazos por causa (todos los intentos):

- `unproven`: 79
- `E401`: 30
- `E000`: 18
- `E102`: 11
- `E201`: 9
- `E100`: 8
- `E200`: 3
- `E404`: 3
- `contract`: 3
- `E500`: 1
- `E300`: 1

Por qué no se prueban las aceptadas (último intento):

- undecided: 20
- timeout: 4
