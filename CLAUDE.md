# Sello

Lenguaje de programación cuyo usuario es la IA. Almacén de funciones con certificados:
hash del AST como identidad, contrato obligatorio, verificación guardada junto al hash.
Público en `github.com/abp002/sello`. Todo se documenta en abierto, errores incluidos.
Bitácora: Alejandro (team de Linear).

## Cómo se trabaja aquí

- **La documentación del proceso NO va en el repo.** Decisiones, bitácora y estado del
  arte viven en el vault de Obsidian: `~/Desktop/vault/Proyectos/Lenguaje para IA/`
  (una nota por decisión, título como afirmación; la bitácora es `Bitácora de Sello.md`).
  Una decisión que no está escrita allí no está tomada.
- **La bitácora se escribe al cerrar cada sesión de trabajo**, con fecha absoluta: qué se
  hizo, qué se midió, qué falló.
- **La spec (`spec/`) está en inglés** porque es el prompt que lee el modelo. El resto del
  repo, en español.
- **Nada se añade al lenguaje sin medirlo.** Si una feature no baja los intentos hasta
  compilar, no entra, por bonita que sea.
- **Robar es política**: si Vera o Unison ya resolvieron algo, se copia y se cita.

## Stack

Python 3.12+, `uv`, `pytest`, `z3-solver` (fase 3). Sin frameworks.

    uv sync
    uv run pytest

`uv run` reinstala z3-solver en cada arranque (la rueda 5.1.0.0 dice macosx_13_0 en el nombre y
macosx_13_3 en su WHEEL). Con procesos en paralelo (servidores MCP, corridas largas), lanzar con
`.venv/bin/python` o `.venv/bin/sello` y no meter otro `uv run` durante la corrida.

## QA

Nivel: activo. Tests de la lógica que se toque: parser, normalización y hash del AST,
verificador de contratos, almacén. Sin tests de glue ni de la CLI.
Contrato de verificación: `.claude/code/run.sh <verbo>`.
