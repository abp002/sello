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

**Para una visión de conjunto, lee [docs/v0.1.md](docs/v0.1.md)**: qué se ha medido, qué ha fallado y
cómo reproducir la demo de un agente que usa Sello por MCP. Lo de abajo es el detalle, fase a fase.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `spec/` | La especificación del lenguaje. En inglés, porque es el prompt que lee el modelo |
| `sello/` | El compilador, el probador (Z3) y el almacén, en Python |
| `tests/` | Tests de la lógica: parser, hash, verificador |
| `bench/` | El experimento: harness, problemas y resultados de cada medición |
| `demo/` | Un agente de Claude Code que solo tiene el MCP de Sello; guion y transcripciones |

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
no entran. `sello mcp` sirve la misma API por MCP. Por la noche, el bug de solidez que destapó el
benchmark (fase 4) deja la hipótesis de inducción como una implicación por llamada, y la misma
medición sube a 61/82 y 28/48, con dos bugs reales más (`most_frequent` de haiku). El 23 de
septiembre, con el probador aislado por función (un Z3 roto ya no tumba a las siguientes), 61/82 y 29/48.

**Fase 4: el benchmark de vericoding** (6 de septiembre de 2026, tarde): las 2.334 specs Dafny
sin `qa-issue` del [benchmark de vericoding](https://github.com/Beneficial-AI-Foundation/vericoding-benchmark)
pasan por un traductor a contratos de Sello (`bench/vericoding/traducir.py`): los helpers no
recursivos se inlinean, los recursivos quedan congelados con su definición en el `ensures`, y
lo que Sello no tiene se cuenta. Caben tal cual 199 (9 %); lo que más bloquea, después de los
tipos que no existen (`string`, `array`, `real`), es el cuantificador sobre un rango de enteros:
es la única traba en 179 specs más, y con el índice `s[i]` serían 219. Sobre una muestra de 50,
en la condición `sello_contrato` (el contrato lo pone el benchmark, el modelo escribe el cuerpo y
sus ejemplos, y el éxito es el certificado de nivel 2 de todo lo que la principal llama), sonnet
prueba 46/50 (92 %; 38 a la primera, 0,14 USD por tarea probada) y haiku 44/50 (88 %; 39 a la
primera, 0,11 USD). Una de las
de haiku era falsa: DD0435 es una spec insatisfacible del propio benchmark (`q(1, 4)` no tiene
solución) que sonnet se estrelló cinco veces contra el contraejemplo del probador y que haiku
«probó» con una recursión que no termina, porque el contrato de la propia función entraba en Z3
como axioma `forall` y una spec falsa en un punto lo hace inconsistente en bloque. Arreglado (la
hipótesis de inducción solo en cada llamada recursiva, bajo su camino, y la terminación probada
sin ella) y recomprobados los 100 programas: sonnet 46/50 y haiku 43/50. Lo que queda sin probar
son límites del probador (división por un producto de variables, helpers recursivos congelados
que hay que desplegar, un `timeout` que oscila) y la spec falsa. El artículo da un 82 % en Dafny
con modelos de serie sobre todo el benchmark; aquí es el 9 % que cabe, así que lo que dice la
comparación es que el cuello de botella de la fase 4 es la cobertura del traductor, no el modelo.
Números en `bench/resultados/vericoding-*`.

**Fase 4, segunda tanda: el cuantificador acotado y el índice** (12 de septiembre de 2026): en
los contratos, `forall i in a..b: P` (rango de enteros, `a` incluido y `b` excluido) y `xs[i]`,
que traducen 1:1 el `forall i :: 0 <= i < |s| ==> P(s[i])` de Dafny. El probador los codifica en
Z3 con la obligación de que el índice esté en rango, y el traductor saca las cotas de las
premisas (con varias variables, cada rango puede usar las anteriores: `0 <= i < j < |s|`).
Remedida la traducción sin modelo: caben **355 de 2.334 (15 %)**, 156 más y ninguna menos. La
predicción era 220: las 64 que faltan las tapaba el cuantificador y ahora se ven (20 son
cuantificadores sin cotas sobre todos los enteros, 29 helpers recursivos que indexan en el
cuerpo, que Sello prohíbe por diseño, y tramos `s[i..j]`). La corrida con modelo sobre 50 de las
156 specs nuevas (misma condición, semilla 1, 5 intentos): **sonnet 29/50 (58 %) y haiku 22/50
(44 %)** en nivel 2 completo, con 1,62 y 2,18 intentos de media; la principal sola queda en 41/50
y 37/50, y en nivel 1 aceptan 49/50 y 46/50. El criterio prerregistrado (sonnet ≥ 80 % y ≤ 1,5
intentos) no se cumple, pero no por el índice: de las 21 tareas de sonnet sin probar, 12 son
aritmética no lineal (`forall j in 2..n: n % j != 0`, la primalidad que el rango dejó entrar y Z3
no decide), 4 son índices puros, 4 `timeout` y 12 tienen la principal probada y falla un helper
del modelo. Fricción nueva: 22 rechazos `E401` en sonnet y 30 en haiku (1 y 1 en la corrida
vieja) por escribir `xs[i]` y `len(xs)` en el cuerpo. Las 199 specs viejas no cambian.

**`/` y `%` con divisor variable** (24 de septiembre de 2026): el probador traduce `a % b` como
`a - b * (a / b)`, un producto de dos variables que Z3 no decide y que, dentro de un
cuantificador, le hace abandonar pruebas que no lo necesitan (la primalidad por recursión solo
necesita partir el rango). Una fase nueva, al final y solo para lo que las exactas no deciden,
los trata como funciones no interpretadas con axiomas lineales verdaderos
(`sello/prover.py`, `divmod_uf`). Recomprobando sin modelo los intentos aceptados
(`bench/vericoding/reprobar.py`): segunda tanda, sonnet de 28/50 a **34/50** y haiku de 20/50 a
**29/50**; la primera, 47 → 48 y 43 → 43. El criterio prerregistrado (ninguna perdida) no se
cumplió con la primera versión: construir el traductor nuevo antes de decidir cambiaba el
E-matching de las fases exactas y perdía una prueba; las tres que siguen apareciendo como
perdidas oscilan igual en `main`. Números en `bench/resultados/reprobar-2026-09-24-*`.

**El probador decide por trabajo, no por reloj** (24 de septiembre de 2026): todos los límites
eran de reloj de pared, así que el mismo programa salía en nivel 1 o 2 según la carga (4 de 200
tareas oscilaban entre pasadas). Ahora cada consulta, función y programa tiene un tope de trabajo
de Z3 (`rlimit`), calibrado sobre 10.376 consultas; el reloj queda de red y, si corta él, el
motivo lo dice (`wall clock`). Midiéndolo apareció otra fuente de ruido y de coste: `confirm`
ejecutaba el contraejemplo candidato sin límite y un `ensures` recursivo de coste 2^n colgaba el
probador hasta su reloj; ahora corre con combustible. Resultado: 162 probadas frente a 154-156, 5,5
minutos por pasada frente a 8, 0 cambios entre pasadas con la misma carga y 2 (marcados) con otra.
Los dos criterios prerregistrados no se cumplieron del todo (coste en el primero, determinismo con
otra carga en el segundo); están en `bench/resultados/reprobar-2026-09-24-19*` y `-2*`.

**El índice se queda fuera del cuerpo** (25 de septiembre de 2026): `E401` por escribir `xs[i]` o
`len(xs)` en un cuerpo era el error nuevo dominante. Experimento prerregistrado con dos brazos
sobre las mismas 50 tareas, corridos a la vez: A, el lenguaje de siempre con un `E401` que enseña
a recorrer con `match`; B, A más `xs[i]` y `len` permitidos en el cuerpo (el probador ya comprueba
cada índice contra `len`). Probadas: sonnet 43 (A) y 42 (B), haiku 36 y 35; B quita los rechazos
por índice (haiku, de 26 a 0) y baja los intentos de haiku de 1,77 a 1,43, pero cuesta lo mismo y
no prueba más. El criterio prerregistrado (B no puede probar menos en la suma) no se cumple, así
que B no entra. Las cuatro tareas que cambian: dos no usan el índice en ningún brazo y las dos que
sí se compensan. El mensaje nuevo tampoco enseña a haiku, que repite el error igual que antes. Los
resultados están en `bench/resultados/*ale168*` (`bench/vericoding/palabras_contrato.py` los
resume).

**Los relojes se quedan; el ruido era la carga** (26 de septiembre de 2026): el reloj de red del
probador seguía decidiendo algunas tareas, y el ritmo de Z3 varía 30 veces entre consultas (de 146
a unas 4.700 unidades de trabajo por ms). Experimento prerregistrado: subir los relojes de 10/20/60
s a 60/120/300 s. Con la máquina libre, las cuatro pasadas (una con los relojes de siempre, tres
con los altos) dan las mismas 163 tareas, en el mismo intento. Los relojes altos no ganan ninguna
prueba, van de 2 a 3 veces más lentos y no eliminan los cortes: Z3 llegó a pasarse 60 s sin gastar
su tope de trabajo. El criterio (ningún corte) no se cumple, así que no entran. Lo que sí movía
los resultados era la carga: con una compilación ajena en marcha, 50 cortes y 3 tareas menos.
`reprobar.py` anota ahora la carga de la máquina y avisa si iba cargada. Por el camino, la
terminación dejó de decir «no argument decreases» cuando Z3 solo no llegaba a decidir. Resultados
en `bench/resultados/*188*`.

**`dedupe` no llega a nivel 2, y no por su contrato** (26 de septiembre de 2026): el error interno
de Z3 que la dejaba en nivel 1 ya no aparece (el tope de trabajo corta antes de que Z3 se quede sin
memoria). Tenía, eso sí, el contrato incompleto: pedía que el resultado contuviera todo lo de `xs`,
pero no que solo tuviera cosas de `xs`, así que `dedupe([42]) == [42, 43]` lo cumplía y la prueba
modular de `distinct` era imposible. Arreglado. Aun así no se prueba, porque la teoría de
secuencias de Z3 no cierra con `seq.nth` una deducción de dos pasos que con arrays es inmediata
(`bench/seq_nth.py`: timeout frente a 0,00 s, en todas las versiones de Z3 desde la 4.12). Siguiente
paso, prerregistrado aparte: codificar el índice como función no interpretada, como hace Dafny
(ALE-225).

**El índice va a Z3 como función opaca, y `dedupe` llega a nivel 2** (28 de septiembre de 2026):
`xs[i]`, y todo lo que se traducía con `seq.nth` (`contains`, `sorted`, `distinct`, los
cuantificadores sobre listas, la cabeza de `[h, ..t]` y `count`), pasa a ser una función no
interpretada `at(xs, i)`, como `Seq#Index` en Dafny, con dos axiomas por tipo de elemento: el de la
lista de un elemento y el de la concatenación por tramos. Las listas siguen siendo secuencias de Z3
para la longitud, `++` y la igualdad. Sin modelo, las mismas 200 tareas pasan de 163 a **173**
probadas (dos pasadas idénticas tarea a tarea, 3 min 30 s cada una), `dedupe` llega a nivel 2 y un
cuerpo que mete elementos de fuera sale E201 con la entrada que lo rompe, cosa que antes no cazaba
nada. El prerregistro no se cumple por una tarea: `DD0753` (`drop(l, n) ++ take(l, n)` con el
índice `(i + n) % len(l)`) se probaba siempre y ahora nunca. El cambio se queda, y esa pérdida
tiene issue propio (ALE-249). `intersect` con `count` (ALE-172) sigue sin decidirse. Resultados en
`bench/resultados/*225*`.

**`DD0753` vuelve con el resto a una vuelta del rango** (28 de septiembre de 2026): la pérdida de
ALE-225 la explicaba la aritmética, no los patrones. `(i + n) % len(l)` con divisor variable es no
lineal: con `seq.nth`, MBQI la cerraba dentro de su tope; con `at`, el mismo cálculo toma otro
camino y no cierra. Los patrones sí forman un bucle de instanciación, y el axioma global de `at`
sobre `++` casa además con las concatenaciones que crea la teoría de secuencias al descomponer cada
lista (ALE-253), pero quitarlos no basta. La fase `u` sabía que `a % b == a` si `0 <= a < b`, pero
no cuánto vale el resto a una vuelta del rango, que es lo que usa una rotación. Con dos axiomas
lineales más (`b <= a < 2b` y `-b <= a < 0`), la prueba sale con 4.071 de trabajo. Sin modelo,
**174** de 200 (dos pasadas idénticas tarea a tarea, ninguna perdida: prerregistro cumplido).
`bench/patrones.py` enseña cuántas veces se instancia cada cuantificador y con qué patrones trabaja
Z3. Resultados en `bench/resultados/*249*`.

**El axioma de la concatenación solo casa con lo que escribe el programa** (28 de septiembre de
2026): el `++` de Sello va a Z3 como `cat!(a, b)`, una función no interpretada igual a `seq.++` por
axioma, y el axioma de `at` por tramos se engancha a `cat!`. Antes se enganchaba a `seq.++`, y como
la teoría de secuencias descompone cada lista por su cuenta, se disparaba sobre cualquier índice: en
`DD0753`, 5.071 instancias; ahora, 467. Un test de propiedad contrasta los tres axiomas globales de
las listas con la semántica de Sello. Sin modelo: gana `DH0104` en las dos pasadas (**175**). El
prerregistro no se cumple, porque la segunda pasada pierde `DH0021`, una tarea sin listas que decide
el reloj con la máquina cargada (el probador de antes la pierde igual). El cambio se queda.
Resultados en `bench/resultados/*253*`.

**El certificado dice en qué se apoya** (29 de septiembre de 2026): el nivel 2 es modular, se prueba
con los contratos de lo que la función llama, y nada decía si esos contratos estaban probados.
`sig`, `add` y `verify` dan ahora `closure_level`, el nivel más bajo de todo lo que la función
alcanza por sus llamadas, y `rests_on`, lo de ese cierre que no llega a 2, como `#print axioms` en
Lean. Se calcula al leer, porque el certificado de una dependencia puede subir. Por el camino salió
un bug de `add`: certificaba en el orden del fichero, así que un llamador que iba delante se quedaba
con nombre y nivel 2 aunque su llamado fallara después. Ahora certifica en orden de dependencias y
cada ciclo entero. Es el paso previo a guardar contratos sin cuerpo.

**El almacén guarda contratos sin cuerpo** (29 de septiembre de 2026): un cuerpo `{ sorry }` guarda
un contrato que espera implementación, un hueco, en nivel 0. Su hash es el de su contrato, y lo
rellena la función que, con el cuerpo cambiado por `sorry`, da ese mismo hash: firma, cláusulas,
ejemplos y los helpers que llaman, idénticos. El contrato es de quien lo escribe (`add --author`, o
el autor con el que se lanza `sello mcp`): otro autor no puede cambiárselo al nombre (`E103`), ni
antes ni después de rellenarlo, así que quien implementa no puede debilitar el `ensures` para salir
de un `E201`. Quien llama a un hueco se prueba con su contrato, sus ejemplos que llegan al hueco
quedan pendientes y su cierre lo lista, como un `sorry` en `#print axioms`. Es la consecuencia de
diseño de que el contrato escrito por otro caza lo que haiku deja pasar.

**El contrato se puede escribir sin el cuerpo** (29 de septiembre de 2026, prerregistrado el 5):
sonnet escribe solo el contrato de los 12 problemas del juez imperfecto, con `{ sorry }` por
cuerpo (`bench/contratar.py`), y haiku escribe el cuerpo contra él. Medido como un juez, con la
respuesta correcta y otra incorrecta por cuerpo (`bench/literales.py`): ningún contrato a ciegas
rechaza lo correcto ni admite lo incorrecto; los escritos con el cuerpo delante admiten el 2 %
(hoy) y el 7 % (los de la quinta corrida). Haiku entrega 12 de 12 sin un silencioso, y de 530
mutantes de su cuerpo llegan a producción 2, que el contrato caza. Dos controles separan la spec
nueva del hecho de escribir a ciegas. La regla de decisión confirma; los denominadores de los
mutantes son pequeños.

**Un hueco se rellena por el MCP igual que en el banco** (1 de octubre de 2026, prerregistrado el
mismo día). El flujo contrato→cuerpo pasa por el producto (`bench/flujo.py`). Por problema hay un
almacén y dos agentes de Claude Code sin más herramientas que `sello mcp`. Sonnet, con
`--author sonnet`, guarda el contrato como hueco; haiku, con `--author haiku`, lo rellena, y su
única guarda es `E103`. Sonnet guarda los 12 al primer intento, y sus contratos pasan la prueba de
literales como los del banco. Haiku rellena 12 de 12 sin un silencioso. La medición destapó dos
fallos del almacén:
- `sig` no enseñaba los ejemplos, que son contrato, y haiku chocaba con `E103` en los 12
  problemas.
- Un hueco podía quedarse sin forma de rellenarse. Bastaba con que quien implementa guardara sus
  propios helpers con los nombres de los del contrato. Desde ahí, el contrato copiado tal cual de
  `view` daba otro hash.

Ahora `sig` enseña los ejemplos, y los nombres que llama el contrato de un hueco solo los mueve su
autor. Remedido, `E103` cae de 12 problemas a 1 y a 0; ese 1 es la guarda nueva. Una de las cuatro
predicciones, la media de intentos, no se cumple en una columna: dos sesiones largas, con
tropiezos del cuerpo. Queda abierto un tercer fallo. Con los helpers enlazados desde el almacén,
el probador no refuta lo que sí refuta con ellos en el mismo fichero.

**Un candidato que no se reproduce no cierra la búsqueda** (5 de octubre de 2026, prerregistrado el
mismo día). El tercer fallo del 1 de octubre no era del almacén. Con los helpers en el fichero o
enlazados, el probador fallaba en la misma consulta. Z3 dejaba un modelo parcial, y que fuera el bug
(`find_in_list([-1], [14])`) o una entrada correcta lo decidían los nombres de las funciones. El
probador se quedaba con ese primer candidato. Ahora, lo que queda sin decidir pide hasta tres
candidatos más, sin las entradas ya ejecutadas, y solo puede refutar: con entradas excluidas, un
`unsat` no prueba nada. Medido contra el probador anterior, no cambia ninguna prueba: las mismas 175
tareas de vericoding y los mismos niveles en 877 programas. De 794 mutantes que llegaban a
producción, mata 13 más en compilación (7 distintos), a cambio de un 20 % más de tiempo en reprobar.
Una primera versión además «probaba» una tarea más sin probar nada nuevo. Guardaba nodos de Z3
durante las fases normales, y eso basta para cambiar el orden del E-matching. La versión de `main`
apunta las entradas como valores del intérprete y construye las exclusiones al final.

**El oráculo del flujo juzga lo que el almacén ejecuta** (5 de octubre de 2026, prerregistrado el
mismo día). El oráculo de `flujo.py` volvía a cargar cada solución como fichero, y esa carga pasa
el probador. Por el almacén, a producción llega lo que `eval` ejecuta, y `eval` no prueba nada.
El probador no ve lo mismo en el fichero que en el almacén. Una solución que el almacén había
aceptado podía no cargar, y entonces todas sus llamadas contaban como rechazadas: un bug del
dominio habría salido ruidoso en vez de silencioso. Ahora el oráculo juzga en ejecución, con los
contratos y sin probador. Se rejuzgaron sin modelo las 47 soluciones del 1 de octubre, y cambia
una sola: los 25 ruidosos de `second_largest` pasan a correctos. No aparece ni desaparece ningún
silencioso.

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
   ~~El cierre del certificado (`closure_level`, `rests_on`).~~ ~~Contratos sin cuerpo
   (`{ sorry }`) con autor: el contrato primero, el cuerpo después.~~ Pendiente: al rellenar
   un hueco, poner al día a quien lo llamaba sin tener que volver a añadirlo.
3. **Solver**: ~~Z3 sobre los contratos (nivel 2): verificación modular, contraejemplos
   confirmados por el intérprete, medida de terminación. Primera medición: 52 % de las
   funciones probadas, 52 % de los mutantes que llegaban a producción muertos en compilación.
   Hechos de cons y concat para la teoría de secuencias: 55 %. La hipótesis de inducción como
   implicación por llamada (bug de solidez destapado por vericoding): 74 % y 58 %.~~ ~~Servidor MCP (`sello mcp`)
   para que los agentes consulten el almacén.~~ ~~Enlace del almacén en `check` y `add`: una
   función guardada se llama por su nombre sin copiarla y el probador usa su contrato.~~ ~~El
   índice de las listas como función no interpretada, como `Seq#Index` en Dafny: de 163 a 173
   de 200 sin modelo.~~ ~~El resto de `%` a una vuelta del rango en la fase u: 174.~~ ~~El axioma de `++` solo sobre
   las concatenaciones del programa: 175.~~ Pendiente: lo que Z3 sigue sin decidir sobre secuencias (`count` en
   `intersect`), guardas en tiempo de ejecución para lo no probado (nivel 3).
4. **Benchmark**: ~~contra el conjunto público de vericoding: traductor Dafny → Sello, 199 de
   2.334 specs caben tal cual, primera corrida en condición `sello_contrato`: sonnet 46/50 y
   haiku 44/50 en nivel 2 sobre una muestra de 50.~~ ~~Cuantificadores sobre rangos de enteros
   e índices `s[i]` en los contratos: 355 de 2.334 caben; sobre las nuevas, sonnet 58 % y haiku
   44 % en nivel 2 (aritmética no lineal, no el índice, es lo que no se decide).~~ ~~`%` de
   divisor variable en Z3.~~ ~~Decidir qué hacer con el índice en el cuerpo: se queda fuera,
   porque permitirlo no prueba más.~~ Pendiente: una medida de terminación entre funciones para
   la recursión mutua.
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
