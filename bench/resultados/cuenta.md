# Contar y sumar con condición (issue #5)

Prerregistrado en el vault: 'Contar y sumar con condición cierra los contratos de cotas'. T es S′: el brazo S del issue #3 con la spec nueva.

| | S·a | S·b | T·a | T·b | P·a | P·b |
|---|---|---|---|---|---|---|
| entregadas | 36/36 | 36/36 | 36/36 | 36/36 | 36/36 | 36/36 |
| contratos que usan `count` o `sum` | 0 | 0 | 11 | 10 | 0 | 0 |
| **casos incorrectos que admite el contrato** | **151/791** | **149/791** | **40/791** | **79/791** | **22/791** | **0/791** |
| contratos flojos (≥ 60 %) | 6 | 7 | 2 | 3 | 1 | 0 |
| contratos que rechazan lo correcto | 0 | 0 | 0 | 0 | 0 | 0 |
| **silencio: dominio + mutantes** | **0 + 6** | **0 + 1** | **0 + 0** | **0 + 2** | **0 + 0** | **0 + 0** |
| ruidosos en el dominio | 0 | 0 | 0 | 0 | 0 | 0 |
| escapes | 4 | 3 | 2 | 7 | 3 | 4 |
| principales con nivel ≥ 2 | 26/36 | 24/36 | 23/36 | 26/36 | - | - |
| contratos unique / ambiguous / unknown | 17/11/8 | 16/10/10 | 22/5/9 | 20/5/11 | 0/1/35 | 0/0/36 |
| intentos hasta aceptar | 1.28 | 1.25 | 1.22 | 1.22 | 1.00 | 1.00 |
| coste USD | 0.12 | 0.09 | 0.12 | 0.09 | 0.02 | 0.01 |

## Regla

1. Casos incorrectos admitidos, S [151, 149] frente a T [40, 79], margen 39: sí.
2. Silencio, S [6, 1] frente a T [0, 2]: sí.
3. Ruidosos, S [0, 0] frente a T [0, 0]: sí.
4. Nivel ≥ 2, S [26, 24] frente a T [23, 26], margen 3: sí.

**ENTRA**.
