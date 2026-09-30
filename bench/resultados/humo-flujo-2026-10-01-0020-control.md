# Flujo contrato→cuerpo por el MCP 2026-10-01-0020 · control

Prerregistrado en el vault: 'Un hueco se rellena por el MCP igual que en el banco'. Programas: llamadas a `sello_check` y `sello_add` con fuente. Oráculo: silenciosos dominio+ambigua · cazados.

| Problema | contrato | cuerpo | E103 (tras check) | lee view/sig | nivel | oráculo |
|---|---|---|---|---|---|---|
| clamp | cargado (contratos-2026-09-29-2317-sonnet.jsonl) | rellena en 2/2 | 1 (0) | 1/1 | 2/2 | 0+0 · 0 |

- Cuerpos: rellenados 1/1 (corridos 1); programas hasta rellenar 2.00; programas por sesión 2.00.
- E103: 1 en 1 problemas; tras un check aceptado, 0. Leen el contrato con view en 1, solo con sig en 0.
- E201 en el bucle: 0 problemas. Nombres propios fuera del hueco: 0.
- Certificados: nivel 2 en 1, nivel 1 en 0.
- Oráculo: **silenciosos 0** (dominio 0, ambigua 0); ruidosos en el dominio 0; cazados 0.
- Sesiones de haiku que no acaban en success: 0 (-). Carga máxima: 5.0.
- Modelos: claude-haiku-4-5-20251001.

# Juez imperfecto 2026-10-01-0020 · modelo `haiku`

Errores silenciosos que llegaron a producción tras pasar el juez débil (`-` = el juez débil no aceptó ninguna solución). Formato: silenciosos dominio+ambigua · cazados por el contrato.

| Problema | sello_mcp |
|---|---|
| clamp | 0+0 · 0 |

| | sello_mcp |
|---|---|
| aceptadas por el juez débil | 1/1 |
| media de intentos hasta aceptar | 2.00 |
| **silenciosos (total)** | **0** |
| silenciosos en el dominio | 0 |
| silenciosos en la zona ambigua | 0 |
| problemas sin ningún silencioso | 1/1 |
| ruidosos en el dominio (rechazo indebido) | 0 |
| declarados en la zona ambigua | 4 |
| cazados por el contrato (E201 / assert) | 0 |
| llamadas del oráculo | 29 |
| tokens de salida | 1676 |
| de ellos, razonamiento | 616 |
| coste USD | 0.045 |
| tiempo total (s) | 19 |
