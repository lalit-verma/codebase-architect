# Codebase Analysis Mode

This repository is being analyzed for architecture documentation.
You are in read-only learning mode.

The primary deliverable is `agent-docs/agent-context.md` — a compact
file that coding agents load at session start for deep codebase
understanding.

## Behavioral Contract

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings for confirmation before writing files.
  Write to `agent-docs/` only after explicit approval.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references.
- **Factual only.** Limit analysis to observable code structure.
- **Honest about uncertainty.** Use these labels consistently:
  - `Confirmed:` directly supported by code or docs
  - `Inference:` likely conclusion from multiple signals
  - `UNCERTAIN:` plausible but weakly supported
  - `NEEDS CLARIFICATION:` should be answered by a human

## Output Root

All documentation goes to `agent-docs/` (not `docs/`):

```
agent-docs/
  .analysis-state.md        # cross-phase state
  agent-context.md           # PRIMARY: compact agent-loadable context
  patterns.md                # detected code patterns and conventions
  agent-brief.md             # compact architecture for agents
  index.md                   # navigation hub
  system-overview.md         # top-level architecture
  decisions.md               # key trade-offs
  glossary.md                # project-specific terms
  uncertainties.md           # unresolved questions
  subsystems/
    {subsystem}.md           # one per subsystem
    {subsystem}/             # recursive sub-subsystem docs (if needed)
      {child}.md
  flows/
    {flow}.md                # cross-cutting flows (if warranted)
```

## Workflow

3-phase workflow. Each phase is a separate task:

1. **Discover & Map** — Classify repo, scan evidence, map subsystems,
   detect preliminary patterns, get confirmation, write system-overview.
2. **Deep Dive** — Analyze one subsystem at a time. Detect patterns.
   Recursively decompose large subsystems (depth limit 4). Write
   subsystem docs. Run once per subsystem.
3. **Synthesize** — Generate `agent-context.md` FIRST (primary output),
   then `patterns.md` (with user confirmation), then remaining docs.

Do not skip phases. Do not write durable docs before the subsystem map
is confirmed.

## Subsystem Rules

A folder is a subsystem only if it satisfies at least 2 of:
- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Referenced across multiple parts of the system

Not subsystems: utility folders, test helpers, DTO-only folders,
generated code directories (unless unusually central).

## Recursive Decomposition

Large subsystems are decomposed into sub-subsystem docs:
- 50+ files or 3+ internal modules with own contracts → propose depth 2
- 30+ files at depth 2 → propose depth 3
- Depth 4: hard stop, summarize
- Many-files-one-pattern → document the pattern, don't decompose

## Pattern Detection

Detect recurring code structures (3+ similar files). Propose patterns
to user for confirmation before including in final output.

## Repo-Type Priorities

- **Applications:** entrypoints, flows, state, orchestration, config
- **Libraries/SDKs:** API surface, abstractions, extension points
- **Frameworks:** lifecycle hooks, inversion points, plugin systems
- **Monorepos:** workspace layout first, ask which slice to deepen

## Reading Depth

- Small (<150 files): read most source files
- Medium (150-800): read central files fully, sample leaves
- Large (800+): focus on entrypoints, contracts, orchestration, config
- Very large / monorepo: top-level architecture only, ask which slice

Note what was read fully vs. sampled vs. skipped.

## Re-run Support

If `agent-docs/` already exists, read existing state and augment rather
than overwrite. Regenerate `agent-context.md` and `patterns.md`
entirely on re-run (stale context is harmful). Update other docs
selectively.
