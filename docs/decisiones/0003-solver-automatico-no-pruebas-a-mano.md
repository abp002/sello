# 0003 — Solver automático, no pruebas a mano

**Fecha:** 2026-09-01. **Estado:** aceptada.

## Contexto

El benchmark de vericoding (arXiv 2509.22908, 12.504 specs) mide cuánto código verificado
generan los LLM: Dafny 82 %, Verus 44 %, Lean 27 %. Añadir lenguaje natural a las specs no
mejora el resultado.

## Decisión

Los contratos se verifican en tres niveles, como Vera:

1. **Ejemplos ejecutados.** Siempre. Es lo que hay en fase 1.
2. **Z3** para lo decidible: aritmética, comparaciones, booleanos. Fase 3.
3. **Guardas en tiempo de ejecución** para lo que Z3 no decide. Fase 3.

Nunca se pide a la IA que escriba una prueba. El certificado dice en qué nivel se verificó
cada contrato: un nivel 3 no es una prueba, es una promesa vigilada.

## Descartado

Pruebas al estilo Lean o Coq. El dato del 27 % lo entierra.

## Consecuencias

Fija el anfitrión (ADR 0004): `z3-solver` en Python es la mejor binding y Vera demostró que
el pipeline entero cabe ahí.
