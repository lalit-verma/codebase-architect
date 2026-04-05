# Codebase Analysis Mode

This repository is being analyzed for architecture documentation.
You are in read-only learning mode.

## Behavioral Contract

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings for confirmation before writing files. Write docs only after explicit approval.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references. Do not attach citations to every sentence.
- **Factual only.** Limit analysis to observable code structure. No speculation beyond what evidence supports.
- **Honest about uncertainty.** Use these labels consistently:
  - `Confirmed:` directly supported by code or docs
  - `Inference:` likely conclusion from multiple signals
  - `UNCERTAIN:` plausible but weakly supported
  - `NEEDS CLARIFICATION:` should be answered by a human

## Output Structure

All documentation goes to `docs/`:

```
docs/
  .analysis-state.md        # internal state for cross-phase continuity
  index.md                   # navigation hub
  agent-brief.md             # compact context for future AI agents
  system-overview.md         # top-level architecture
  decisions.md               # key trade-offs
  glossary.md                # project-specific terms
  uncertainties.md           # unresolved questions
  subsystems/
    {subsystem}.md           # one per subsystem
  flows/
    {flow}.md                # optional cross-cutting flows
```

## Workflow

This analysis follows a 3-phase workflow. Each phase is a separate task:

1. **Discover & Map** — Classify repo, scan evidence, map subsystems, get confirmation, write system-overview.md
2. **Deep Dive** — Analyze one subsystem at a time, write subsystem docs. Run once per subsystem.
3. **Synthesize** — Produce index.md, agent-brief.md, decisions.md, glossary.md, uncertainties.md

Do not skip phases. Do not write durable docs before the subsystem map
is confirmed.

## Subsystem Rules

A folder is a subsystem only if it satisfies at least 2 of:
- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Is referenced across multiple parts of the system

Not subsystems: utility folders, test helpers, DTO-only folders,
generated code directories (unless unusually central).

## Repo-Type Priorities

- **Applications:** entrypoints, request/event flows, state, orchestration, config
- **Libraries/SDKs:** public API surface, abstractions, extension points, error model, packaging
- **Frameworks:** lifecycle hooks, inversion points, plugin systems, conventions, extension surfaces
- **Monorepos:** workspace layout first, then ask which slice to deepen

## Reading Depth

- Small repos (<150 files): read most source files
- Medium repos (150-800): read central files fully, sample leaves
- Large repos (800+): focus on entrypoints, contracts, orchestration, config
- Very large / monorepo: top-level architecture only, ask which slice to deepen

Note what was read fully vs. sampled vs. skipped.

## Re-run Support

If `docs/` already exists, read existing state and augment rather than
overwrite. Flag new, removed, or changed subsystems.
