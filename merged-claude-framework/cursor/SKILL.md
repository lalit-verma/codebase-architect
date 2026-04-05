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
agent consumption. The primary output is `agent-docs/agent-context.md`
— a compact file (under 120 lines) that a coding agent loads at session
start. Agent understanding is the primary goal; human readability is
secondary.

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

## Shared Resources

If available, load these files from the shared resources directory on
demand during analysis:

- `shared/references/ecosystem-playbook.md` — per-language exploration
- `shared/references/scale-and-scope.md` — reading depth, recursion
- `shared/references/subsystem-mapping-rubric.md` — subsystem qualification
- `shared/references/checkpoint-template.md` — checkpoint format
- `shared/references/agent-context-rules.md` — agent-context generation
- `shared/references/pattern-detection-guide.md` — pattern detection
- `shared/references/validation-rules.md` — self-check criteria per phase
- `shared/references/scope-selection-rules.md` — monorepo scope selection
- `shared/templates/` — output document templates
- `shared/examples/` — quality calibration targets

## Workflow

Execute these phases in order. Do not skip phases.

### Phase 1: Discover & Map

**Steps:**

1. **Classify the repository** — archetype, language, execution model, scale
2. **Detect ecosystem** — check root for markers (go.mod, package.json, Cargo.toml, pyproject.toml, pom.xml, *.csproj, etc.) and use ecosystem-appropriate exploration
3. **Evidence scan** — manifests, entrypoints, contracts, registries, config, tests, docs. Scale reading depth to repo size.
4. **Detect system-wide patterns** — naming, file organization, error handling, test conventions, common abstractions
5. **Map subsystems** — at least 2 of: owns responsibility, exposes contract, coordinates modules, encapsulates state, distinct dependency pattern, cross-referenced. Tag with role. Flag any with >60 files or >3 distinct responsibilities for recursive decomposition.
6. **Present checkpoint** — classification, working understanding, subsystem table (with Decomposition column), flows, patterns, coverage notes, open questions, proposed doc plan
6b. **Self-validate checkpoint** — verify 8 sections present, subsystem table has all columns, every subsystem has 2+ evidence anchors. Fix before presenting.
6c. **Scope selection (monorepo/very-large only)** — present scope table with package, path, est. files, centrality (core/supporting/peripheral), recommended priority. Record `selected_scope` in state. Skip for small/medium repos.
7. **Ask for confirmation** before writing anything.
8. **Write files** — `agent-docs/.analysis-state.md` (state + patterns + decomposition flags) and `agent-docs/system-overview.md`
9. **Report next steps** — list subsystems in recommended deep-dive order

### Phase 2: Deep Dive (run once per subsystem)

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md` first.

**Steps:**

1. **Assess size and scope** — if `selected_scope` exists in state and target subsystem is not in it, warn user and ask whether to proceed. If flagged for decomposition or >60 files / >3 responsibilities, propose sub-module split and get confirmation.
2. **Read the subsystem** — scale reading to size. Note what was sampled.
3. **Analyze** — boundaries, internal structure, contracts, flows, dependencies, configuration, design decisions, testing, edge cases
4. **Capture patterns** — code and test conventions specific to this subsystem
5. **Identify modification guidance** — invariants, "how to add a new X", files touched together, gotchas. This is the most agent-valuable section.
6. **Write document(s)** — single doc at `agent-docs/subsystems/{name}.md`, or parent + sub-module docs at `agent-docs/subsystems/{name}/{sub-module}.md` if decomposing. Use templates from `shared/templates/subsystem-template.md` and `shared/templates/sub-module-template.md`.
6b. **Self-validate subsystem doc** — verify Modification Guide non-empty, at least 1 flow traced with file refs, 2+ evidence anchors, Coverage Notes present. Fix before updating state.
7. **Update state** — move from pending to completed in `.analysis-state.md`
8. **Report next steps** — remaining subsystems, recommended order

### Phase 3: Synthesize

Read all existing docs first.

**Steps:**

1. **Write `agent-docs/agent-context.md`** — PRIMARY OUTPUT. Under 120 lines. No tables. No prose. Every line actionable. Use `shared/references/agent-context-rules.md` and `shared/examples/agent-context-example.md` for quality calibration.
1b. **Self-validate agent-context.md** — under 120 lines, no tables, no confidence labels, all 7 sections, file paths in every map/pattern/contract entry. Fix before continuing.
2. **Write `agent-docs/patterns.md`** — consolidated code and test conventions. Present to user for confirmation before writing.
3. **Write `agent-docs/agent-brief.md`** — compact architecture (<100 lines). Include Common Change Playbooks.
4. **Write `agent-docs/index.md`** — navigation hub (<250 lines).
5. **Write `agent-docs/decisions.md`** — 5-8 key decisions.
6. **Write `agent-docs/glossary.md`** — project terms.
7. **Write `agent-docs/uncertainties.md`** — all unresolved questions.
8. **Write flow docs** — only if cross-cutting flows warrant it.
9. **Write `agent-docs/agent-protocol.md`** — wiring instructions for Claude Code, Codex, Cursor.
9b. **Quality smoke test** — read agent-context.md and answer 5 diagnostic questions (where to create new entity, what pattern to follow, what not to do, which subsystem handles primary flow, key contracts). If any answer cannot be found in agent-context.md alone, fix the doc.
10. **Update state** — set phase_completed: 3, record all generated files
11. **Report completion** — list all generated files, usage instructions

## Output Structure

```
agent-docs/
  .analysis-state.md
  agent-context.md         ** PRIMARY: compact context for coding agents **
  patterns.md              ** code patterns — "how to add a new X" **
  agent-brief.md              compact architecture map
  agent-protocol.md           wiring instructions for agents
  index.md                    navigation hub
  system-overview.md          top-level architecture
  decisions.md                architectural trade-offs
  glossary.md                 project-specific terms
  uncertainties.md            unresolved questions
  subsystems/
    {subsystem}.md
    {subsystem}/
      {sub-module}.md
  flows/
    {flow}.md
```

## Recursive Decomposition

Maximum 3 levels: system -> subsystem -> sub-module. Triggered when
subsystem has >60 files or >3 distinct responsibilities. Proposed to
user, not automatic. Sub-module docs use a lighter template (~60% of
subsystem docs). See `shared/references/scale-and-scope.md` for rules.

## Quality Bar

Good enough when a coding agent reading the docs can:
- understand what the system is and how it is organized
- find the right files to modify for a given task
- follow the correct patterns when adding new code
- avoid breaking invariants or implicit contracts
- know what areas are uncertain

## Re-run Support

All phases support re-runs. If `agent-docs/` already exists, read existing
state and augment rather than overwrite. `agent-context.md` and `patterns.md`
are regenerated entirely on re-run (stale context is harmful).
