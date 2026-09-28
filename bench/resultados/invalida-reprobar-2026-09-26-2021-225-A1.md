# Reprobar 2026-09-26-2021 (225-A1)

Los programas aceptados de cada corrida, recomprobados con el probador de este commit. Sin modelo.

| Corrida | probadas antes | probadas ahora | principal antes | principal ahora | ganadas | perdidas |
|---|---|---|---|---|---|---|
| vericoding-2026-09-06-1502-sonnet-muestra50-semilla1 | 46/50 | **48/50** | 47/50 | 49/50 | 2 | 0 |
| vericoding-2026-09-06-1807-haiku-muestra50-semilla1 | 44/50 | **43/50** | 46/50 | 46/50 | 1 | 2 |
| vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1 | 29/50 | **44/50** | 41/50 | 46/50 | 15 | 0 |
| vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1 | 22/50 | **35/50** | 37/50 | 39/50 | 13 | 0 |

Carga de la máquina (load average de 1 min): al empezar 3.4, máximo 12.0, al acabar 8.1; 10 núcleos.

**Aviso: la máquina iba cargada.** El reloj de red del probador pudo decidir resultados: esta pasada no sirve para medir un cambio.
Tareas cuyo motivo final lleva «(wall clock)»: 5.

## Cambios

- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DA0023 `solve` (intento 1)
- vericoding-2026-09-06-1502-sonnet-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 2)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **ganada** DD0730 `MinLengthSublist` (intento 2)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DD0435 `q`: termination (termination: no argument decreases at every recursive call)
- vericoding-2026-09-06-1807-haiku-muestra50-semilla1: **perdida** DH0127 `next_odd_collatz_iter`: undecided (undecided: `ensures ((result % 2) == 1)`)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DA0205 `solve` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0535 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0644 `IsNonPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0763 `IsPrime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0021 `largest_divisor` (intento 4)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0029 `is_prime` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0152 `x_or_y` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0110 `PrimeNum` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0125 `difference` (intento 2)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0151 `LargestPrimeFactor` (intento 4)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0091 `numpy_unpackbits` (intento 4)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0276 `LogicalAnd` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0555 `unique` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DV0041 `MaxProfit` (intento 1)
- vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1: **ganada** DV0110 `ElementWiseModulo` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DA0144 `solve` (intento 3)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0535 `IsPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0644 `IsNonPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0703 `ElementAtIndexAfterRotation` (intento 3)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0753 `SplitAndAppend` (intento 5)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DD0763 `IsPrime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0029 `is_prime` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DH0152 `x_or_y` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0110 `PrimeNum` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DJ0125 `difference` (intento 3)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0090 `RightShift` (intento 1)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0091 `numpy_unpackbits` (intento 3)
- vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1: **ganada** DT0276 `LogicalAnd` (intento 2)
