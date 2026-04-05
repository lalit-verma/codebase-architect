# Codebase Analysis Mode

This repository is being analyzed for architecture documentation.
You are in read-only learning mode.

## Purpose

Produce durable architecture documentation optimized for coding agent
consumption. A coding agent loading these docs should gain deep context
before writing code — resulting in higher quality than a cold start.

## Behavioral Contract

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings for confirmation before writing files. Write docs only after explicit approval.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references. Do not cite every sentence.
- **Factual only.** Limit analysis to observable code structure. No speculation beyond what evidence supports.
- **Honest about uncertainty.** Use these labels consistently:
  - `Confirmed:` directly supported by code or docs
  - `Inference:` likely conclusion from multiple signals
  - `UNCERTAIN:` plausible but weakly supported
  - `NEEDS CLARIFICATION:` should be answered by a human

## Anti-Patterns

Do not:

- generate polished docs before the subsystem map is confirmed
- confuse directory structure with true architectural boundaries
- claim runtime behavior that static evidence does not support
- treat monorepos as single-package codebases
- skip the Modification Guide in subsystem docs
- produce boilerplate prose that adds no insight

## Output Structure

All documentation goes to `agent-docs/`:

```
agent-docs/
  .analysis-state.md        # internal state for cross-phase continuity
  index.md                   # navigation hub
  agent-brief.md             # compact context for coding agents
  agent-protocol.md          # instructions for wiring into agents
  system-overview.md         # top-level architecture
  patterns.md                # code and test conventions
  decisions.md               # key trade-offs
  glossary.md                # project-specific terms
  uncertainties.md           # unresolved questions
  subsystems/
    {subsystem}.md           # one per subsystem
    {subsystem}/             # sub-module docs (if decomposed)
      {sub-module}.md
  flows/
    {flow}.md                # optional cross-cutting flows
```

## Workflow

This analysis follows a 3-phase workflow. Each phase is a separate task:

1. **Discover & Map** — Classify repo, scan evidence, detect patterns, map subsystems, get confirmation, write system-overview.md
2. **Deep Dive** — Analyze one subsystem at a time, capture patterns and modification guidance, write subsystem docs. Run once per subsystem. Supports recursive decomposition into sub-modules.
3. **Synthesize** — Produce index.md, agent-brief.md, patterns.md, decisions.md, glossary.md, uncertainties.md, agent-protocol.md

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

## Recursive Decomposition

A subsystem should be split into sub-modules when it has >60 source
files or >3 distinct internal responsibilities. Maximum depth: 3 levels
(system → subsystem → sub-module). Propose the split to the user
before executing.

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

## Stop Conditions

Stop and ask for scoping confirmation when:
- more than 10 top-level packages appear architecturally relevant
- more than one plausible main runtime exists
- the repo is clearly a platform rather than a single product
- the first-pass map requires guessing about ownership
- the model is drifting into inventory instead of architecture

## Re-run Support

If `agent-docs/` already exists, read existing state and augment rather than
overwrite. Flag new, removed, or changed subsystems.
