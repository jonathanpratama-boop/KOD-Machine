# Historical identifiers

`ID_MAP.jsonl` is an append-only schema-v1 registry. It is intentionally empty:
this release renames no historical experiment, detector, import, artifact or profile.

If a later release adds a public alias, append one record with `schema_version: 1`,
`old`, `new`, `kind`, `since`, `commit` and `reason`. `old` is the original canonical
identifier, `new` is its additional alias, `since` is an explicit UTC instant, and
`commit` is an already-existing full commit that establishes the naming decision.
Do not use a future/self-referential commit hash. Names cannot be rebound or chained.

`kod.ids.resolve(name, at=<cutoff>, kind=<kind>)` returns the original name when
an alias was effective by that cutoff. Unknown names remain unchanged; resolution
is not evidence that a record exists. Path aliases resolve to original paths for
verification only. They never instruct a move, rewrite or hash recomputation.

Original readers continue to accept their historical names and schemas. Introduce
alias resolution at a reader's input boundary when that reader adopts an actual
alias; do not rewrite signed payloads or canonical historical identifiers.
