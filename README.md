# Sello

**Un lenguaje de programación cuyo usuario es la IA, no una persona.**

Sello no es un lenguaje de texto en ficheros. Es un **almacén de funciones con
certificados**: cada función se identifica por el hash de su árbol sintáctico, lleva un
contrato obligatorio (precondiciones, postcondiciones, efectos y ejemplos), y el resultado
de verificar ese contrato se guarda junto al hash. Verificada una vez, verificada para
siempre. De ahí el nombre: cada función lleva su sello.

El texto es solo la sintaxis de escritura. La sintaxis de lectura es una API que la IA
consulta: *dame la firma y el contrato de X*, *quién usa Y*, *verifica Z*.

## La hipótesis

> Un lenguaje para humanos optimiza brevedad y ergonomía. Un lenguaje para IA optimiza
> **verificabilidad**. La IA genera código rápido y barato; el cuello de botella es saber
> si está bien. Así que el lenguaje debe ser el revisor.

Es una hipótesis falsable y se mide desde el día uno: se le da a un modelo la
especificación (dos páginas) y un problema, y se cuenta **cuántos intentos necesita
hasta que compila y pasa los contratos**, comparado con Python sobre el mismo problema.
Si el número baja, Sello funciona. Si no baja, cada intento fallido deja un error
estructurado que dice qué decisión de diseño está fallando.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `spec/` | La especificación del lenguaje. En inglés, porque es el prompt que lee el modelo |
| `sello/` | El compilador y el almacén, en Python |
| `tests/` | Tests de la lógica: parser, hash, verificador |
| `bench/` | El experimento: harness de medición contra Python |

## Estado

**Fase 1** (septiembre de 2026). El porqué de cada decisión, la bitácora y el estado
del arte viven en el vault de notas del autor, no en el repo. Aquí hay código, spec y
este README.

## Hoja de ruta

0. **Cimientos** (ahora): repo, decisiones, spec v0, harness de medición vacío.
1. **Núcleo**: lexer, parser e intérprete de un lenguaje mínimo con contratos. Nivel de
   verificación 1: los ejemplos se ejecutan. Errores en JSON. Primera medición.
2. **Almacén**: hash del AST normalizado, nombres como alias, certificado por hash, API de
   consulta. Segunda medición: ¿leer por API en vez de por fichero baja los intentos?
3. **Solver**: Z3 sobre los contratos decidibles (nivel 2), guardas en tiempo de ejecución
   para el resto (nivel 3). Servidor MCP para que los agentes consulten el almacén.
4. **Benchmark**: contra el conjunto público de vericoding.

Cada fase termina con una medición y una entrada en la bitácora. Si una fase no mejora la
métrica, se documenta por qué antes de seguir.

## De dónde viene

Sello roba sin vergüenza: los contratos triples y el formato de errores de
[Vera](https://github.com/aallan/vera); el almacén por contenido y la API de consulta de
[Unison](https://www.unison-lang.org/); la elección de solver automático del
[benchmark de vericoding](https://arxiv.org/abs/2509.22908). Lo que no hace nadie es
juntarlo y guardar el certificado junto al hash.

## Licencia

MIT.
