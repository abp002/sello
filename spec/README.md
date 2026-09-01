# Sello language specification

**Status: draft v0.** This document is the prompt a model reads before writing Sello. It
must fit in two pages. Every sentence that does not help a model write correct code is a
sentence to delete.

The spec lives in `SPEC.md`. This file states the constraints the spec itself must obey.

## Constraints on the spec

1. **Two pages.** The whole language, readable in one context window with room to spare.
2. **One way to do each thing.** No sugar, no alternatives, no "you may also".
3. **Every construct has an example.** The model learns from examples, not prose.
4. **Errors are part of the spec.** Every error code the compiler can emit is listed here
   with its fix.
5. **Written for a model.** Imperative, concrete, no motivation. Motivation lives in
   `docs/`.

## How the spec is measured

The spec is correct when a model, given only this document and a problem, produces code
that compiles and passes its contracts in fewer attempts than it needs for Python. The
harness in `bench/` measures exactly that.
