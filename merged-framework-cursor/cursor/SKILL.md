---
name: codebase-analysis
description: >
  Deep, evidence-first architecture analysis for any codebase.
  Produces durable documentation optimized for coding agent context —
  so that future Cursor, Claude Code, or Codex sessions gain deep
  understanding before writing code.
  Use this skill whenever the user wants to understand, learn from,
  document, or map a repository — even casual requests like "help me
  understand this repo", "what does this codebase do", "walk me through
  the architecture", "I'm new to this repo", or "how is this project
  structured". Also trigger for "analyze this codebase" or "generate
  architecture docs".
  This skill is for learning and understanding — not for modifying,
  refactoring, or contributing code.
---

# Codebase Architecture Analysis

Produces thorough architecture documentation optimized for coding
agent consumption. Agent understanding is the primary goal; human
readability is secondary.

## Hard Constraints

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings for confirmation. Write files only after approval.
- **Evidence-based.** Cite file paths. Moderate citation density.
- **Factual only.** Label anything beyond direct evidence.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

## Anti-Patterns

- Do not generate polished docs before the subsystem map is confirmed
- Do not confuse directory structure with architectural boundaries
- Do not claim runtime behavior without static evidence
- Do not skip the Modification Guide in subsystem docs
- Do not produce boilerplate prose

## Workflow

Execute these phases in order. Do not skip phases.

### Phase 1: Discover & Map

Read `shared/references/ecosystem-playbook.md` for per-language
detection logic and commands. Read `shared/references/scale-and-scope.md`
for reading depth rules. Read `shared/references/subsystem-mapping-rubric.md`
for subsystem qualification.

**Steps:**

1. **Classify the repository** — archetype, language, execution model, scale
2. **Detect ecosystem** — check root for markers (go.mod, package.json, Cargo.toml, pyproject.toml, pom.xml, *.csproj, etc.) and use ecosystem-appropriate exploration
3. **Evidence scan** — manifests, entrypoints, contracts, registries, config, tests, docs. Scale reading depth to repo size.
4. **Detect system-wide patterns** — naming, file organization, error handling, test conventions, common abstractions
5. **Map subsystems** — at least 2 of: owns responsibility, exposes contract, coordinates modules, encapsulates state, distinct dependency pattern, cross-referenced. Tag with role. Flag any with >60 files or >3 distinct responsibilities for recursive decomposition.
6. **Present checkpoint** — classification, working understanding, subsystem table (with Decomposition column), flows, patterns, coverage notes, open questions, proposed doc plan. Use `shared/references/checkpoint-example.md` as quality target.
7. **Ask for confirmation** before writing anything.
8. **Write files** — `agent-docs/.analysis-state.md` (state + patterns + decomposition flags) and `agent-docs/system-overview.md`
9. **Report next steps** — list subsystems in recommended deep-dive order

### Phase 2: Deep Dive (run once per subsystem)

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md` first.

**Steps:**

1. **Assess size** — if flagged for decomposition or >60 files / >3 responsibilities, propose sub-module split and get confirmation
2. **Read the subsystem** — scale reading to size. Note what was sampled.
3. **Analyze** — boundaries, internal structure, contracts, flows, dependencies, configuration, design decisions, testing, edge cases
4. **Capture patterns** — code and test conventions specific to this subsystem
5. **Identify modification guidance** — invariants, "how to add a new X", files touched together, gotchas. This is the most agent-valuable section.
6. **Write document(s)** — single doc at `agent-docs/subsystems/{name}.md`, or parent + sub-module docs at `agent-docs/subsystems/{name}/{sub-module}.md` if decomposing. Use templates from `shared/templates/subsystem.md` and `shared/templates/sub-module.md`.
7. **Update state** — move from pending to completed in `.analysis-state.md`
8. **Report next steps** — remaining subsystems, recommended order

### Phase 3: Synthesize

Read all existing docs first.

**Steps:**

1. **Write `agent-docs/index.md`** — navigation hub (<250 lines). Use `shared/templates/index.md`.
2. **Write `agent-docs/agent-brief.md`** — compact context for agents (<150 lines). Include Common Change Playbooks. Use `shared/templates/agent-brief.md`.
3. **Write `agent-docs/patterns.md`** — consolidated code and test conventions. Use `shared/templates/patterns.md`.
4. **Write `agent-docs/decisions.md`** — 5-8 key decisions. Use `shared/templates/decisions.md`.
5. **Write `agent-docs/glossary.md`** — project terms. Use `shared/templates/glossary.md`.
6. **Write `agent-docs/uncertainties.md`** — all unresolved questions. Use `shared/templates/uncertainties.md`.
7. **Write flow docs** — only if cross-cutting flows warrant it. Use `shared/templates/flow.md`.
8. **Write `agent-docs/agent-protocol.md`** — wiring instructions for Claude Code, Codex, Cursor. Use `shared/templates/agent-protocol.md`.
9. **Update state** — set phase_completed: 3, record all generated files
10. **Report completion** — list all generated files, usage instructions

## Output Structure

```
agent-docs/
  .analysis-state.md
  index.md
  agent-brief.md
  agent-protocol.md
  system-overview.md
  patterns.md
  decisions.md
  glossary.md
  uncertainties.md
  subsystems/
    {subsystem}.md
    {subsystem}/
      {sub-module}.md
  flows/
    {flow}.md
```

## Recursive Decomposition

Maximum 3 levels: system → subsystem → sub-module. Triggered when
subsystem has >60 files or >3 distinct responsibilities. Proposed to
user, not automatic. Sub-module docs are lighter (~60% of subsystem
docs). See `shared/references/scale-and-scope.md` for rules.

## Quality Bar

Good enough when a coding agent reading the docs can:
- understand what the system is and how it is organized
- find the right files to modify for a given task
- follow the correct patterns when adding new code
- avoid breaking invariants or implicit contracts
- know what areas are uncertain

## Re-run Support

All phases support re-runs. If `agent-docs/` already exists, read existing
state and augment rather than overwrite.
