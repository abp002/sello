# Vericoding en Sello 2026-09-12-0935 · modelo `haiku` · condición `sello_contrato`

El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos · `sin respuesta (k)` = el modelo no contestó al intento k (límite de sesión, red): fuera del recuento.

| tarea | fuente | fn | resultado | último motivo sin probar |
|---|---|---|---|---|
| DD0715 | dafnybench | AnyValueExists | 2 (1) |  |

| | dafnybench | total |
|---|---|---|
| tareas | 1 | 1 |
| **probadas (nivel 2)** | **1/1 (100 %)** | **1/1 (100 %)** |
| · a la primera | 1 | 1 |
| · media de intentos hasta probar | 1.00 | 1.00 |
| principal en nivel 2 | 1/1 (100 %) | 1/1 (100 %) |
| aceptadas (nivel 1) | 1/1 (100 %) | 1/1 (100 %) |
| · media de intentos hasta aceptar | 1.00 | 1.00 |
| tareas con helpers congelados | 0 | 0 |
| · con alguno sin probar | 0 | 0 |
| tokens de salida | 9080 | 9080 |
| de ellos, razonamiento | 8753 | 8753 |
| tokens de entrada | 3370 | 3370 |
| coste USD | 0.053 | 0.053 |
| tiempo total (s) | 82 | 82 |
