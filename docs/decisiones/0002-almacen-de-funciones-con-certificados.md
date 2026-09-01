# 0002 — Almacén de funciones con certificados, no texto en ficheros

**Fecha:** 2026-09-01. **Estado:** aceptada. Es la decisión que define el proyecto.

## Contexto

Dos modelos posibles: texto en ficheros (todo el tooling existe, la IA lo domina) o un
almacén de funciones direccionado por contenido al estilo Unison (todo el tooling hay que
hacerlo, pero sin conflictos de merge, con dependencias exactas y con control de qué ve la
IA).

## Decisión

El almacén es la verdad; el texto es una vista.

- Cada función se identifica por el **hash de su AST normalizado**. Los nombres son alias.
- Cada función lleva contrato obligatorio.
- **El resultado de verificar el contrato se guarda junto al hash.** Verificada una vez,
  verificada para siempre. El coste de verificar crece con lo nuevo, no con el programa.
- El texto es la **sintaxis de escritura**. La **sintaxis de lectura es una API**: firma y
  contrato de X, dependientes de Y, verificar Z. La IA nunca lee cuerpos que no pidió.

## Descartado

- Solo texto: el compilador no controla qué ve la IA y la verificación se repite siempre.
- Solo almacén sin texto (Unison puro): arranque demasiado caro y la IA de hoy escribe
  ficheros. Se puede quitar el texto más adelante sin tocar el núcleo.

## Consecuencias

- Resuelve la tensión entre redundancia (ADR 0001) y ventana de contexto: se escribe la
  versión redundante, se lee solo la firma con certificado.
- Riesgo: construir infraestructura y nunca el lenguaje. Mitigación: la fase 1 es un
  intérprete sobre ficheros y ya se mide; el almacén llega en fase 2 y se mide contra ella.
- Esto no lo hace nadie del catálogo. Unison tiene almacén sin contratos; Vera tiene
  contratos sin almacén.
