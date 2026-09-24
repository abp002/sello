# Reprobar 2026-09-24-1819 (base-main)

Los programas aceptados de cada corrida, recomprobados con el probador de este commit. Sin modelo.

| Corrida | probadas antes | probadas ahora | principal antes | principal ahora | ganadas | perdidas |
|---|---|---|---|---|---|---|
| vericoding-2026-09-06-1502-sonnet-muestra50-semilla1 | 46/50 | **47/50** | 47/50 | 49/50 | 2 | 1 |
| vericoding-2026-09-06-1807-haiku-muestra50-semilla1 | 44/50 | **43/50** | 46/50 | 46/50 | 1 | 2 |
| vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1 | 29/50 | **28/50** | 41/50 | 41/50 | 0 | 1 |
| vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1 | 22/50 | **20/50** | 37/50 | 37/50 | 0 | 2 |

## Cambios

- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DA0023 `solve` (intento 4)
- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 2)
- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **perdida** DB0020 `ModExpPow2_int`: undecided (undecided: `ensures (result == (Exp_int(x, y) % z))`)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 4)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DD0435 `q`: termination (termination: no argument decreases at every recursive call)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DH0127 `next_odd_collatz_iter`: undecided (undecided: `ensures ((result % 2) == 1)`)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **perdida** DD0767 `ElementWiseDivide`: undecided (undecided: `ensures forall i in 0..len(result): (result[i] == (a[i] / b[i]))`)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **perdida** DD0767 `ElementWiseDivide`: undecided (undecided: `ensures forall i in 0..len(result): (result[i] == (a[i] / b[i]))`)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **perdida** DV0157 `ModifyArrayElement`: undecided (undecided: `ensures forall j in 0..len(arr[index1]): ((not (j != index2)) or (result[index1][j] == arr[index1][j]))`)
