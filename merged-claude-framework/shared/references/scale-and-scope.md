# Scale and Scope Rules

Use these thresholds to decide how broad the first pass should be, how
aggressively to sample, and when to trigger recursive decomposition.

The numbers are heuristics. If the repo shape clearly demands more or
less depth, say so and adjust.

## Repo Size Tiers

### Small (under 150 source files)

Typical signals:
- Single runtime or package
- Clear entrypoint and shallow directory tree

Default behavior:
- Read all central files
- Usually read all source files in the main package
- Write complete docs if the subsystem map is confirmed

### Medium (150-800 source files)

Typical signals:
- Multiple meaningful subsystems
- One main app or service with supporting packages

Default behavior:
- Read central files fully
- Sample repetitive leaves after pattern is established
- Document only confirmed subsystems
- Note when coverage is sampled rather than exhaustive

### Large (800-2000 source files)

Typical signals:
- Multiple apps, packages, crates, or services
- Generated code or many adapters

Default behavior:
- Map architecture first, not every file
- Focus on entrypoints, contracts, registries, orchestration, config
- Require scope confirmation before subsystem deep dives
- Write overview docs first, deeper docs only for confirmed scope

### Very Large / Complex Monorepo (2000+ source files)

Typical signals:
- Workspace with many apps and packages
- Substantial generated code, plugins, or build graph

Default behavior:
- Produce top-level architecture only
- Identify package/app candidates for deeper analysis
- Ask the user what slice matters next
- Do not write full-repo docs claiming broad completeness

## Sampling Rules

Use these defaults unless the user requests exhaustive analysis:

- Always read manifests and workspace config
- Always read entrypoints and bootstrapping code
- Always read contract-defining files (interfaces, types, protos)
- Always read central orchestration modules
- Sample repetitive leaf handlers, adapters, or tests after a pattern is
  established
- Explicitly mark sampled coverage in the checkpoint and final docs

## Generated Code Rules

If generated code is present:
- Identify it as generated (look for codegen markers, `generated` in path
  or filename, "DO NOT EDIT" comments)
- Do not spend the first pass explaining generated implementation detail
- Trace back to the generator, schema, or registration points
- Note where generated code affects architectural boundaries
- Do not count generated files toward subsystem complexity thresholds

## Recursive Decomposition Thresholds

These thresholds determine when a subsystem should be split into
sub-subsystem docs during Phase 2 deep dive.

### Depth 2 (parent subsystem → sub-subsystems)

Trigger when the subsystem has:
- 50+ non-generated source files, OR
- 3+ internal modules that each have their own contracts or entrypoints

### Depth 3 (sub-subsystem → sub-sub-subsystems)

Trigger when a sub-subsystem at depth 2 has:
- 30+ non-generated source files, OR
- 2+ internal modules with own contracts

### Depth 4 (hard stop)

At depth 4, summarize remaining complexity. Do not decompose further.

### When NOT to decompose

- Many files following one pattern (e.g., 50 similar handlers):
  document the pattern in `patterns.md`, not each file.
- Mechanically generated files.
- Folders that are large but have a single clear responsibility.
- Folders where depth would not produce additional actionable insight.

## Stop Conditions

Stop and ask for scoping confirmation when any of these occur:

- More than 10 top-level packages or apps appear architecturally relevant
- More than one plausible main runtime exists
- The repo is clearly a platform or framework rather than a single product
- The first-pass map requires guessing about package ownership
- The analysis is drifting into file inventory instead of architecture

## Write Eligibility

Do not write durable docs if:
- The subsystem map is still low-confidence
- The repo purpose is unclear
- Monorepo scope is not confirmed
- Central flows have not been identified

If any of those remain unresolved, stay in chat mode and ask clarifying
questions.
