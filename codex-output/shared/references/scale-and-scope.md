# Scale And Scope Rules

Use these thresholds to decide how broad the first pass should be and
how aggressively to sample.

The numbers are heuristics. If the repo shape clearly demands more or
less depth, say so and adjust.

## Repo Size Tiers

### Small

Typical signals:

- under 150 source files
- single runtime or package
- clear entrypoint and shallow directory tree

Default behavior:

- read all central files
- usually read all source files in the main package
- write complete docs if the subsystem map is confirmed

### Medium

Typical signals:

- 150 to 800 source files
- multiple meaningful subsystems
- one main app or service with supporting packages

Default behavior:

- read central files fully
- sample repetitive leaves
- document only confirmed subsystems
- avoid pretending that every helper module was examined

### Large

Typical signals:

- over 800 source files
- multiple apps/packages/crates/services
- generated code or many adapters

Default behavior:

- map architecture first, not every file
- focus on entrypoints, contracts, registries, orchestration, config
- require scope confirmation before subsystem deep dives
- write overview docs first, deeper docs only for confirmed scope

### Very Large / Complex Monorepo

Typical signals:

- over 2000 source files
- workspace with many apps/packages
- substantial generated code, plugins, or build graph

Default behavior:

- produce top-level architecture only
- identify package/app candidates for deeper analysis
- ask the user what slice matters next
- do not write full-repo durable docs claiming broad completeness

## Sampling Rules

Use these defaults unless the user requests exhaustive analysis:

- always read manifests and workspace config
- always read entrypoints and bootstrapping
- always read contract-defining files
- always read central orchestration modules
- sample repetitive leaf handlers, adapters, or tests after a pattern is
  established
- explicitly mark sampled coverage in the checkpoint and final docs

## Generated Code Rules

If generated code is present:

- identify it as generated
- do not spend the first pass explaining generated implementation in
  depth
- trace back to the generator, schema, or registration points when
  possible
- note where generated code still affects architecture

## Stop Conditions

Stop and ask for scoping confirmation when any of these occur:

- more than 10 top-level packages/apps appear architecturally relevant
- more than one plausible main runtime exists
- the repo is clearly a platform/framework rather than a single product
- the first-pass map requires guessing about package ownership
- the model is drifting into inventory instead of architecture

## Write Eligibility

Do not write durable docs yet if:

- the subsystem map is still low-confidence
- the repo purpose is unclear
- monorepo scope is not confirmed
- central flows have not been identified

If any of those remain unresolved, stay in chat mode.
