# Vericoding en Sello 2026-09-06-1446 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DA0003 | apps | solve | 2 (1) |  |
| DA0008 | apps | solve | 1 (1) | mutual recursion: termination not checked |
| DD0042 | dafnybench | Abs | 2 (1) |  |

| | apps | dafnybench | total |
|---|---|---|---|
| tareas | 2 | 1 | 3 |
| **probadas (nivel 2)** | **1/2 (50 %)** | **1/1 (100 %)** | **2/3 (67 %)** |
| · a la primera | 1 | 1 | 2 |
| · media de intentos hasta probar | 1.00 | 1.00 | 1.00 |
| principal en nivel 2 | 2/2 (100 %) | 1/1 (100 %) | 3/3 (100 %) |
| aceptadas (nivel 1) | 2/2 (100 %) | 1/1 (100 %) | 3/3 (100 %) |
| · media de intentos hasta aceptar | 1.00 | 1.00 | 1.00 |
| tareas con helpers congelados | 1 | 0 | 1 |
| · con alguno sin probar | 0 | 0 | 0 |
| tokens de salida | 85776 | 1839 | 87615 |
| de ellos, razonamiento | 78879 | 1717 | 80596 |
| tokens de entrada | 27458 | 3119 | 30577 |
| coste USD | 0.477 | 0.012 | 0.489 |
| tiempo total (s) | 727 | 20 | 747 |

Rechazos por causa (todos los intentos):

- `unproven`: 4
- `E300`: 1

Por qué no se prueban las aceptadas (último intento):

- mutual recursion: 1
