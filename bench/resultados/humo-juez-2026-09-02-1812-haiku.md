# Juez imperfecto 2026-09-02-1812 · modelo `haiku`

Errores silenciosos que llegaron a producción tras pasar el juez débil (`-` = el juez débil no aceptó ninguna solución). Formato: silenciosos dominio+ambigua · cazados por el contrato.

| Problema | python | python_asserts | sello |
|---|---|---|---|
| nth | 0+2 · 0 | 0+0 · 4 | 0+0 · 0 |

| | python | python_asserts | sello |
|---|---|---|---|
| aceptadas por el juez débil | 1/1 | 1/1 | 1/1 |
| media de intentos hasta aceptar | 1.00 | 1.00 | 2.00 |
| **silenciosos (total)** | **2** | **0** | **0** |
| silenciosos en el dominio | 0 | 0 | 0 |
| silenciosos en la zona ambigua | 2 | 0 | 0 |
| problemas sin ningún silencioso | 0/1 | 1/1 | 1/1 |
| ruidosos en el dominio (rechazo indebido) | 0 | 0 | 0 |
| declarados en la zona ambigua | 2 | 4 | 4 |
| cazados por el contrato (E201 / assert) | 0 | 4 | 0 |
| llamadas del oráculo | 29 | 29 | 29 |
| tokens de salida | 378 | 4160 | 10790 |
| de ellos, razonamiento | 329 | 4013 | 10231 |
| coste USD | 0.003 | 0.022 | 0.064 |
| tiempo total (s) | 5 | 36 | 97 |
