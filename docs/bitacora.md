# Bitácora

Diario del proyecto. Una entrada por sesión, fecha absoluta, lo que pasó de verdad.

## 2026-09-01 — Arranque

**Qué se decidió.** El proyecto nace de una pregunta: ¿tiene sentido crear un lenguaje
pensando en que quien lo use sea la IA? La respuesta fue que sí, pero solo si es una
hipótesis medible y no otro juguete. Se decidió en la misma sesión:

- Que el lenguaje optimiza verificabilidad, no ergonomía (ADR 0001).
- Que no es texto en ficheros sino un almacén de funciones con certificados (ADR 0002).
- Que los contratos se verifican con solver automático, no con pruebas a mano (ADR 0003).
- Anfitrión Python, spec en inglés, nombre "Sello" (ADR 0004).

**Qué se investigó.** Existen 41 lenguajes para IA catalogados. Vera es el más maduro
(contratos + Z3 + errores JSON, sobre ficheros). Unison 1.0 tiene almacén por contenido
y MCP para agentes, sin contratos. Nadie guarda la verificación junto al hash. Detalle en
`docs/estado-del-arte.md`.

**Qué se hizo.** Repo, README con la hipótesis y la hoja de ruta, ADRs, borrador v0 de
la spec, esqueleto del paquete y contrato de verificación.

**Qué falta.** Todo el código. Lo primero es el harness de medición, antes que el
compilador: sin métrica no hay experimento.
