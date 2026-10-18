# El helper de referencia (issue #6)

Prerregistrado en el vault: 'Una frase en la spec no basta para que el contrato fije el resultado'. U es T con la spec que guía el helper de referencia.

| | T·a | T·b | U·a | U·b | P·a | P·b |
|---|---|---|---|---|---|---|
| entregadas | 36/36 | 36/36 | 36/36 | 36/36 | 36/36 | 36/36 |
| principales con `ensures result == helper(...)` | 4 | 2 | 3 | 6 | 0 | 0 |
| contratos que usan `count` o `sum` | 11 | 10 | 9 | 10 | 0 | 0 |
| **casos incorrectos que admite el contrato** | **40/791** | **79/791** | **99/791** | **64/791** | **22/791** | **0/791** |
| contratos flojos (≥ 60 %) | 2 | 3 | 5 | 3 | 1 | 0 |
| contratos que rechazan lo correcto | 0 | 0 | 0 | 0 | 0 | 0 |
| **silencio: dominio + mutantes** | **0 + 0** | **0 + 2** | **0 + 1** | **0 + 0** | **0 + 0** | **0 + 0** |
| ruidosos en el dominio | 0 | 0 | 0 | 0 | 0 | 0 |
| escapes | 2 | 7 | 0 | 8 | 3 | 4 |
| principales con nivel ≥ 2 | 23/36 | 26/36 | 27/36 | 25/36 | - | - |
| contratos unique / ambiguous / unknown | 22/5/9 | 20/5/11 | 20/6/10 | 22/3/11 | 0/1/35 | 0/0/36 |
| intentos hasta aceptar | 1.22 | 1.22 | 1.33 | 1.22 | 1.00 | 1.00 |
| coste USD | 0.12 | 0.09 | 0.12 | 0.10 | 0.02 | 0.01 |

## Regla

1. Casos incorrectos admitidos, T [40, 79] frente a U [99, 64], margen 39: no.
2. Silencio, T [0, 2] frente a U [1, 0]: sí.
3. Ruidosos, T [0, 0] frente a U [0, 0]: sí.
4. Nivel ≥ 2, T [23, 26] frente a U [27, 25], margen 3: sí.

**NO ENTRA**.
