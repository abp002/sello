# bench — el experimento

Aquí vive la métrica. Antes que el compilador.

**Qué mide:** intentos que necesita un modelo hasta que su programa compila y pasa los
contratos, dado solo `spec/SPEC.md` y el enunciado. Se compara con Python sobre los mismos
problemas.

**Condiciones:** mismo modelo, misma temperatura, mismos problemas. Se registra también el
tiempo de agente y los tokens, no solo intentos.

**Problemas:** batería pequeña y variada (aritmética, listas, recursión, opción). Cuando
haya solver, los del benchmark público de vericoding.

Vacío por ahora. Es lo primero que se construye en la fase 1.
