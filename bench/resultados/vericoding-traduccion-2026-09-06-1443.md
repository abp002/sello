# Traducción Dafny -> Sello 2026-09-06-1443

Qué cabe en Sello tal cual de las specs Dafny del benchmark de vericoding (sin `qa-issue`). Una tarea cabe si su método tiene un valor de retorno y `ensures`, todo es `int`/`nat`/`bool`/`seq`, y las cláusulas (con los helpers inlineados) se dicen con el vocabulario de contratos de Sello.

| | apps | dafnybench | humaneval | verina | verified_cogen | numpy_triple | numpy_simple | bignum | total |
|---|---|---|---|---|---|---|---|---|---|
| specs | 677 | 443 | 162 | 157 | 172 | 603 | 58 | 62 | 2334 |
| **caben** | **99** (15 %) | **57** (13 %) | **16** (10 %) | **18** (11 %) | **4** (2 %) | **1** (0 %) | **1** (2 %) | **3** (5 %) | **199** (9 %) |
| · con helpers recursivos congelados | 24 | 19 | 10 | 1 | 1 | 0 | 0 | 3 | 58 |
| · nota `as int` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| · nota `cláusula `true` eliminada` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| · nota `div` | 23 | 3 | 1 | 0 | 0 | 0 | 1 | 3 | 31 |
| · nota `función supuesta: abs` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| · nota `función supuesta: max` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| · nota `función supuesta: min` | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| · nota `lema ignorado` | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| · nota `método del preámbulo ignorado` | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 3 |
| · nota `nat` | 3 | 19 | 5 | 4 | 1 | 1 | 0 | 3 | 36 |
| · nota `requires vacío` | 1 | 14 | 2 | 13 | 1 | 0 | 0 | 0 | 31 |
| longitud mediana del contrato (caracteres) | 430 | 261 | 519 | 223 | 255 | 379 | 240 | 644 | 345 |
| longitud máxima | 2606 | 1473 | 2082 | 1214 | 622 | 379 | 240 | 644 | 2606 |

## Por qué no caben las demás

2135 specs. Cada una puede tener varios motivos: `en alguna` cuenta la spec si el motivo aparece; `el primero` solo el primero que encuentra el traductor (cabecera antes que cláusulas).

| motivo | en alguna | el primero |
|---|---|---|
| tipo no soportado | 1696 | 1460 |
| cuantificador sobre enteros | 1579 | 275 |
| índice s[i] | 682 | 27 |
| literal real/texto/carácter | 537 | 0 |
| miembro .x | 487 | 0 |
| tramo s[i..j] | 321 | 1 |
| helper recursivo con vocabulario de contrato | 283 | 10 |
| tipo desconocido | 171 | 14 |
| función sin definir | 155 | 8 |
| modifies | 115 | 114 |
| sin valor de retorno | 111 | 12 |
| varios valores de retorno | 101 | 98 |
| cuantificador sin dominio | 91 | 4 |
| multiset(...) | 72 | 2 |
| comprensión set/map/seq | 67 | 0 |
| sin ensures | 54 | 32 |
| tupla | 49 | 1 |
| genéricos | 37 | 29 |
| seq(...) | 32 | 2 |
| sintaxis Dafny no cubierta | 30 | 30 |
| null | 30 | 0 |
| nombre sin definir | 24 | 0 |
| old | 21 | 0 |
| conversión as real | 20 | 0 |
| conversión as char | 18 | 0 |
| función sin cuerpo | 17 | 2 |
| match | 17 | 1 |
| var con patrón | 11 | 1 |
| sin método | 9 | 9 |
| fresh | 7 | 0 |
| actualización s[i := v] | 4 | 0 |
| índice múltiple | 3 | 0 |
| sin ejemplo para un helper | 2 | 2 |
| var :| (elección) | 2 | 0 |
| conversión as Float | 2 | 0 |
| comparación de secuencias | 1 | 0 |
| lambda | 1 | 1 |
| conversión as Real | 1 | 0 |

Tipos no soportados (specs en las que aparece):

- tipo: string: 567
- tipo: array: 536
- tipo: real: 385
- tipo: char: 257
- tipo: datatype u otro: 221
- tipo: tuple: 62
- tipo: fn: 10
- tipo: bv: 7
- tipo: set: 7
- tipo: map: 4
- tipo: multiset: 4
