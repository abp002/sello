# Reprobar 2026-09-24-1935 (calibra-1)

Los programas aceptados de cada corrida, recomprobados con el probador de este commit. Sin modelo.

| Corrida | probadas antes | probadas ahora | principal antes | principal ahora | ganadas | perdidas |
|---|---|---|---|---|---|---|
| vericoding-2026-09-06-1502-sonnet-muestra50-semilla1 | 46/50 | **48/50** | 47/50 | 49/50 | 2 | 0 |
| vericoding-2026-09-06-1807-haiku-muestra50-semilla1 | 44/50 | **43/50** | 46/50 | 46/50 | 1 | 2 |
| vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1 | 29/50 | **34/50** | 41/50 | 42/50 | 8 | 3 |
| vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1 | 22/50 | **29/50** | 37/50 | 37/50 | 8 | 1 |

## Cambios

- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DA0023 `solve` (intento 1)
- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 2)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 4)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DD0435 `q`: termination (termination: no argument decreases at every recursive call)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DH0127 `next_odd_collatz_iter`: undecided (undecided: `ensures ((result % 2) == 1)`)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0535 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0644 `IsNonPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0763 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0021 `largest_divisor` (intento 4)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0029 `is_prime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0152 `x_or_y` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0110 `PrimeNum` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DV0110 `ElementWiseModulo` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DT0088 `LeftShift`: undecided (undecided: `LeftShift(t1, t2)` may violate `requires forall i in 0..len(x2): (x2[i] >= 0)` of `LeftShift`)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DT0090 `RightShift`: undecided (undecided: `ensures forall i in 0..len(result): ((not (x2[i] == 0)) or (result[i] == x1[i]))`)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DV0157 `ModifyArrayElement`: undecided (undecided: `ensures forall j in 0..len(arr[index1]): ((not (j != index2)) or (result[index1][j] == arr[index1][j]))`)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0535 `IsPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0644 `IsNonPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0703 `ElementAtIndexAfterRotation` (intento 3)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0753 `SplitAndAppend` (intento 2)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0763 `IsPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0029 `is_prime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0152 `x_or_y` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0110 `PrimeNum` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **perdida** DV0157 `ModifyArrayElement`: undecided (undecided: `ensures forall j in 0..len(arr[index1]): ((not (j != index2)) or (result[index1][j] == arr[index1][j]))`)
