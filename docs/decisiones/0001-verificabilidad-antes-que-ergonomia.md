# 0001 — Verificabilidad antes que ergonomía

**Fecha:** 2026-09-01. **Estado:** aceptada.

## Contexto

Un lenguaje para humanos optimiza brevedad, legibilidad y ergonomía. Cuando el que escribe
es un modelo, generar código es rápido y barato, y el cuello de botella pasa a ser saber si
está bien.

## Decisión

Sello optimiza **verificabilidad**. El lenguaje es el revisor. De ahí:

1. Redundancia deliberada: tipo, contrato y ejemplos obligatorios, y las tres cosas tienen
   que cuadrar. Para la IA la redundancia es un checksum que caza alucinaciones.
2. Razonamiento local: sin estado global, efectos explícitos, imports explícitos.
3. Una sola forma de hacer cada cosa. Sin azúcar sintáctico.
4. Errores como datos estructurados, para agentes, no para personas.
5. Efectos en el tipo.
6. Spec y ejemplos como parte del lenguaje, no ficheros aparte.

## Descartado

Optimizar tokens o sintaxis "bonita". Es de segundo orden y es lo que hacen los otros 40.

## Consecuencias

Se sacrifica todo lo que un humano valora y una IA no. Si la IA escribe y lee, la
verbosidad deja de ser coste y pasa a ser comprobación.
