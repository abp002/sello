# Estado del arte (septiembre de 2026)

Hay **41 lenguajes diseñados para que los escriba una IA**, catalogados en
[agentlanguages.dev](https://agentlanguages.dev). Casi todos ocupan el mismo sitio y el
hueco que persigue Sello sigue vacío.

## Las tres corrientes

| Corriente | Idea | Ejemplos |
|---|---|---|
| Sintáctica | Sintaxis más fácil de generar: AST en JSON, SSA como sintaxis, mínimo de tokens | X07, Magpie, ilo, NERD |
| Verificación | Contratos comprobables por máquina. El grupo grande | Vera, Intent, Thermite, Pact, Aver, Hale |
| Orquestación | Reformular como coordinación de agentes | Pel, Quasar, Lumen |

La mayoría son proyectos de una persona. Otra sintaxis no vale nada; el valor está en el
modelo de almacén y verificación.

## Los dos referentes

**[Vera](https://github.com/aallan/vera).** El más maduro: Python + Z3, 2.680 commits,
12.000 tests. Contratos obligatorios `requires` / `ensures` / `effects`, probados con Z3.
Errores JSON con código estable, causa y ejemplo corregido. Sin nombres de variables:
índices De Bruijn tipados (`@Int.0`). Hallazgo del autor: los LLM no fallan en sintaxis,
fallan en coherencia a escala y en nombres. Usa ficheros de texto, sin almacén.

**[Unison 1.0](https://www.unison-lang.org/unison-1-0/)** (nov. 2025). Código
direccionado por contenido y un [servidor MCP](https://www.unison-lang.org/docs/usage-topics/mcp-setup/)
con 16 herramientas para agentes: buscar por nombre y tipo, dependencias, dependientes,
typecheck. Sin contratos, solo tipos.

## Lo que Sello roba y lo que no existe

Roba: contratos triples y formato de errores (Vera), almacén y API de consulta (Unison),
De Bruijn como candidato (Vera, LLMLang).

No existe: almacén por contenido + contratos con solver + **certificado guardado junto al
hash**. Solo un proyecto del catálogo usa almacén en vez de ficheros (Spec, experimento) y
solo uno direcciona por contenido (Tacit, marginal).

## Datos que fijan decisiones

- [Benchmark de vericoding](https://arxiv.org/abs/2509.22908), 12.504 specs: Dafny 82 %,
  Verus 44 %, Lean 27 %. Añadir lenguaje natural a la spec no mejora nada. Por eso solver
  automático y no pruebas a mano. Y por eso la métrica de Sello es la estándar del campo.
- [Intent Formalization](https://arxiv.org/abs/2603.17150) (Lahiri, 2026): la brecha
  entre intención y código; espectro desde tests hasta specs completas.
- [AkitaOnRails, feb. 2026](https://akitaonrails.com/en/2026/02/09/ai-agents-best-programming-language-for-llms/):
  "la historia del diseño de lenguajes es eliminar justo lo que los LLM necesitan".
- [TokDrift](https://arxiv.org/html/2510.14972): la tokenización no respeta la gramática;
  la sintaxis afecta al modelo. De segundo orden, pero real.
