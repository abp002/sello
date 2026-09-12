# Traducción Dafny -> Sello 2026-09-12-0923

Qué cabe en Sello tal cual de las specs Dafny del benchmark de vericoding (sin `qa-issue`). Una tarea cabe si su método tiene un valor de retorno y `ensures`, todo es `int`/`nat`/`bool`/`seq`, y las cláusulas (con los helpers inlineados) se dicen con el vocabulario de contratos de Sello.

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | numpy_simple | bignum | total |
|---|---|---|---|---|---|---|---|---|---|
| specs | 677 | 443 | 162 | 157 | 172 | 603 | 58 | 62 | 2334 |
| **caben** | **150** (22 %) | **86** (19 %) | **47** (29 %) | **39** (25 %) | **14** (8 %) | **13** (2 %) | **3** (5 %) | **3** (5 %) | **355** (15 %) |
| · con helpers recursivos congelados | 30 | 20 | 15 | 1 | 2 | 3 | 0 | 3 | 74 |
| · nota `as int` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| · nota `cláusula `true` eliminada` | 0 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 5 |
| · nota `div` | 33 | 13 | 6 | 2 | 4 | 2 | 1 | 3 | 64 |
| · nota `función supuesta: abs` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| · nota `función supuesta: max` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| · nota `función supuesta: min` | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| · nota `lema ignorado` | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| · nota `método del preámbulo ignorado` | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 1 | 5 |
| · nota `nat` | 3 | 20 | 11 | 12 | 2 | 6 | 0 | 3 | 57 |
| · nota `requires vacío` | 4 | 19 | 16 | 20 | 6 | 4 | 1 | 0 | 70 |
| longitud mediana del contrato (caracteres) | 485 | 276 | 416 | 266 | 310 | 476 | 240 | 644 | 370 |
| longitud máxima | 4201 | 1473 | 2082 | 1620 | 622 | 1163 | 451 | 644 | 4201 |

## Por qué no caben las demás

1979 specs. Cada una puede tener varios motivos: `en alguna` cuenta la spec si el motivo aparece; `el primero` solo el primero que encuentra el traductor (cabecera antes que cláusulas).

| motivo | en alguna | el primero |
|---|---|---|
| tipo no soportado | 1696 | 1460 |
| literal real/texto/carácter | 801 | 1 |
| miembro .x | 603 | 0 |
| tramo s[i..j] | 435 | 6 |
| helper recursivo con vocabulario de contrato | 427 | 71 |
| tipo desconocido | 231 | 31 |
| función sin definir | 218 | 17 |
| cuantificador sin dominio | 122 | 11 |
| modifies | 115 | 114 |
| sin valor de retorno | 111 | 12 |
| varios valores de retorno | 101 | 98 |
| cuantificador sobre enteros sin cotas | 89 | 25 |
| comprensión set/map/seq | 82 | 0 |
| tupla | 78 | 2 |
| multiset(...) | 72 | 15 |
| conversión as real | 65 | 0 |
| sin ensures | 54 | 32 |
| seq(...) | 49 | 7 |
| nombre sin definir | 41 | 1 |
| old | 40 | 0 |
| genéricos | 38 | 29 |
| función sin cuerpo | 37 | 3 |
| conversión as char | 36 | 0 |
| null | 31 | 0 |
| sintaxis Dafny no cubierta | 30 | 30 |
| match | 20 | 1 |
| var con patrón | 19 | 1 |
| sin método | 9 | 9 |
| índice múltiple | 8 | 0 |
| fresh | 7 | 0 |
| actualización s[i := v] | 5 | 0 |
| var :| (elección) | 4 | 0 |
| sin ejemplo para un helper | 2 | 2 |
| lambda | 2 | 1 |
| conversión as Float | 2 | 0 |
| comparación de secuencias | 1 | 0 |
| llamada a una expresión | 1 | 0 |
| conversión as bv | 1 | 0 |
| conversión as Real | 1 | 0 |
| is | 1 | 0 |

Tipos no soportados (specs en las que aparece):

- tipo: string: 569
- tipo: array: 536
- tipo: real: 411
- tipo: char: 382
- tipo: datatype u otro: 225
- tipo: tuple: 62
- tipo: fn: 11
- tipo: bv: 9
- tipo: set: 7
- tipo: map: 4
- tipo: multiset: 4
