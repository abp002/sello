# Reprobar 2026-09-24-1827 (fase-u)

Los programas aceptados de cada corrida, recomprobados con el probador de este commit. Sin modelo.

| Corrida | probadas antes | probadas ahora | principal antes | principal ahora | ganadas | perdidas |
|---|---|---|---|---|---|---|
| vericoding-2026-09-06-1502-sonnet-muestra50-semilla1 | 46/50 | **48/50** | 47/50 | 49/50 | 2 | 0 |
| vericoding-2026-09-06-1807-haiku-muestra50-semilla1 | 44/50 | **44/50** | 46/50 | 47/50 | 1 | 1 |
| vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1 | 29/50 | **35/50** | 41/50 | 44/50 | 9 | 3 |
| vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1 | 22/50 | **29/50** | 37/50 | 37/50 | 8 | 1 |

## Cambios

- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DA0023 `solve` (intento 1)
- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 2)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 4)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DD0435 `q`: termination (termination: no argument decreases at every recursive call)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0535 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0644 `IsNonPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0753 `SplitAndAppend` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0763 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0021 `largest_divisor` (intento 4)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0029 `is_prime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0152 `x_or_y` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0110 `PrimeNum` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DV0110 `ElementWiseModulo` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DA0045 `solve`: undecided (undecided: `ensures forall k in 0..(3 + 1): (((if ((if (((-x + (90 * result)) % 360) < 0) then (((-x + (90 * result)) % )
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DJ0171 `Transpose`: timeout (timeout)
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
