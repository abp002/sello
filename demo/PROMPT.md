You have access to Sello, a programming language whose user is an AI, only through the `sello_*`
MCP tools. You have no other tools: no files, no shell.

1. Read the language specification with `sello_spec`.
2. List what is already in the store with `sello_names`. Some of it may be useful: read only the
   signature and contract (`sello_sig`), never the body.
3. Write `intersect(xs: List[Int], ys: List[Int]) -> List[Int]`: the elements of `xs` that also
   appear in `ys`, in the order of `xs`, keeping repetitions. Reuse a function from the store if
   one fits. Give it a contract strong enough that a wrong body would break it, and examples.
4. Run `sello_check` until it is accepted. Aim for level 2 (proved), and if the prover cannot
   close an obligation, say which one and why.
5. Store it with `sello_add`, then show its certificate with `sello_sig` and who it depends on
   with `sello_deps`.

End with a short report: what you wrote, how many `sello_check` calls it took, which errors you
hit, and the certificate level you got.
