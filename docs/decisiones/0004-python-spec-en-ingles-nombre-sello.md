# 0004 — Anfitrión Python, spec en inglés, nombre "Sello"

**Fecha:** 2026-09-01. **Estado:** aceptada.

## Anfitrión: Python 3.12+

Por `z3-solver` (ADR 0003) y porque el objetivo es aprender del lenguaje, no del
anfitrión. Rust añade fricción que no aporta. Se descarta TypeScript por la binding de Z3.
Sin frameworks: `uv`, `pytest` y poco más.

## La spec, en inglés

La especificación es el **prompt** que lee el modelo. En inglés rinde mejor porque es lo
que el modelo ha visto. Todo lo demás del repo, en español, porque el proceso se
documenta para personas.

## Nombre: Sello

Cada función lleva su sello: el certificado de verificación guardado junto al hash. Corto,
español, se pronuncia bien en inglés. Descartados: Acta, Certo (demasiado cerca de Vera).
