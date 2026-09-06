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
| `sello/` | El compilador, el probador (Z3) y el almacén, en Python |
| `tests/` | Tests de la lógica: parser, hash, verificador |
| `bench/` | El experimento: harness, problemas y resultados de cada medición |

## Estado

**Fase 2 hecha y métrica cambiada** (3 de septiembre de 2026): núcleo, almacén con
certificados, API de consulta, y el *juez imperfecto* como métrica principal (errores
silenciosos que llegan a producción, `bench/harness3.py`). Tres cambios medidos en un
día llevaron a Sello de 7/5 silenciosos (haiku/sonnet) a 1/0, igualando a Python con
asserts: vocabulario de listas en contratos, `requires` como sitio de lo que el enunciado
permite suponer, y `E102` para el contrato trivial. El porqué de cada decisión, la
bitácora y el estado del arte viven en el vault de notas del autor, no en el repo. Aquí
hay código, spec y este README.

**Mutantes del cuerpo y la fuerza del `ensures`** (5 de septiembre de 2026): un mutador
sin modelo (`bench/mutantes.py`) mide cuántos bugs de cuerpo caza el contrato. Donde el
`ensures` habla del contenido no hay silenciosos; donde solo acota un número, casi todo
pasa. Tres frases en la spec sobre eso llevan a sonnet de 6/12 a 2/12 funciones con
`ensures` de cotas y de 30 % a 0 % de mutantes silenciosos; haiku no cambia un contrato.

**Nivel 2: el probador** (6 de septiembre de 2026): Z3 intenta demostrar cada `ensures` a
partir de `requires` y de los contratos de las funciones llamadas (`sello/prover.py`:
verificación modular al estilo Dafny, hipótesis de inducción y medida de terminación). Un
contraejemplo solo se reporta si el intérprete lo reproduce, así que el probador nunca
rechaza por su cuenta: adelanta a compilación errores que existían para alguna entrada.
Primera medición sin modelo (`bench/probador.py`) sobre lo aceptado el 5 de septiembre:
prueba 46/89 funciones (la principal en 18/36 soluciones), encuentra un bug real en una
solución que el juez débil y 345 llamadas del oráculo dieron por buena (`int_sqrt` de haiku
con contrato de sonnet: `search(0, 1, 1)`), y mata en compilación 25/48 mutantes que llegaban
a producción, entre ellos 11/19 de los silenciosos de haiku. También encontró que `div` de
`ejemplos/basicos.sello` violaba su `ensures` con divisor negativo desde el primer día. Por
la tarde, dos hechos sobre secuencias que Z3 no deriva solo (la cola elemento a elemento y
`++` por tramos) suben a 49/89 y 27/48; los patrones de instanciación explícitos, medidos,
no entran. `sello mcp` sirve la misma API por MCP.

**Fase 4: el benchmark de vericoding** (6 de septiembre de 2026, tarde): las 2.334 specs Dafny
sin `qa-issue` del [benchmark de vericoding](https://github.com/Beneficial-AI-Foundation/vericoding-benchmark)
pasan por un traductor a contratos de Sello (`bench/vericoding/traducir.py`): los helpers no
recursivos se inlinean, los recursivos quedan congelados con su definición en el `ensures`, y
lo que Sello no tiene se cuenta. Caben tal cual 199 (9 %); lo que más bloquea, después de los
tipos que no existen (`string`, `array`, `real`), es el cuantificador sobre un rango de enteros:
es la única traba en 179 specs más, y con el índice `s[i]` serían 219. Sobre una muestra de 50,
la condición `sello_contrato` (el contrato lo pone el benchmark, el modelo escribe el cuerpo y
sus ejemplos, y el éxito es el certificado de nivel 2 de todo lo que la principal llama) está
corriendo con haiku y con sonnet; los números van a la bitácora y a `bench/resultados/vericoding-*`.

    uv sync --extra dev
    uv run sello check ejemplos/basicos.sello     # parse, tipos, ejemplos, probador (nivel 2)
    uv run sello add ejemplos/basicos.sello       # al almacén, con certificado
    uv run sello sig max_of                       # firma + contrato + certificado
    uv run sello users contains_in                # quién la llama
    uv run sello eval 'max_of([factorial(3), div(9, 2)])'
    uv run sello mcp                              # la misma API por MCP (stdio) para agentes

## Hoja de ruta

0. ~~**Cimientos**: repo, decisiones, spec v0, harness de medición vacío.~~
1. ~~**Núcleo**: lexer, parser e intérprete con contratos. Nivel de verificación 1: los
   ejemplos se ejecutan. Errores en JSON. Primera medición.~~
2. ~~**Almacén**: hash del AST normalizado, nombres como alias, certificado por hash, API
   de consulta. Segunda medición: leer por API no baja los aciertos.~~
   ~~**Juez imperfecto**: métrica de silenciosos; vocabulario de listas, `requires` como
   dominio y `E102`. Sello pasa de 7/5 a 1/0 e iguala a Python con asserts.~~
3. **Solver**: ~~Z3 sobre los contratos (nivel 2): verificación modular, contraejemplos
   confirmados por el intérprete, medida de terminación. Primera medición: 52 % de las
   funciones probadas, 52 % de los mutantes que llegaban a producción muertos en compilación.
   Hechos de cons y concat para la teoría de secuencias: 55 %.~~ ~~Servidor MCP (`sello mcp`)
   para que los agentes consulten el almacén.~~ Pendiente: otra codificación de las listas
   para lo que Z3 no decide (cuantificadores sobre secuencias), guardas en tiempo de ejecución
   para lo no probado (nivel 3).
4. **Benchmark**: ~~contra el conjunto público de vericoding: traductor Dafny → Sello, 199 de
   2.334 specs caben tal cual, primera corrida en condición `sello_contrato`.~~ Pendiente, y
   solo si la medición lo justifica: cuantificadores sobre rangos de enteros e índices `s[i]`
   en los contratos (desbloquearían 219 specs más), y una medida de terminación entre funciones
   para la recursión mutua.
5. **El almacén como dataset**: afinar un modelo abierto con código Sello generado y
   filtrado por el compilador. Solo con Z3 hecho y la sintaxis congelada. Objetivo: que el
   coste de razonamiento baje de 10x a 1x manteniendo aciertos.

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
