# Phase 3: Synthesize

## Progress

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| 2. Deep Dive | complete |
| **3. Synthesize** | **<-- current** |

---

## First: Read All Docs

Read these before doing anything:

1. `agent-docs/.analysis-state.md`
2. `agent-docs/system-overview.md`
3. Every file in `agent-docs/subsystems/` (including sub-module subdirectories)

If subsystems are still pending, warn the user and ask whether to
continue with incomplete coverage.

If `agent-docs/.analysis-state.md` does not exist, say:
> **Phase 1 has not been run.** Run the Phase 1 prompt first.

---

## Mission

Produce the final documentation set optimized for coding agent
consumption. A coding agent loading these docs should orient itself,
find the right files, follow the right patterns, and avoid
architectural mistakes — without exploring from scratch.

## Constraints

- **Read-only.** Do not modify source code.
- **Base on existing docs.** Do not re-explore the codebase.
- **Factual only.** Observable analysis.
- **Consolidate.** If multiple deep dives noted the same thing, merge.
- **Moderate citations.** Reference docs and file paths.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

---

## Procedure

### 1. Write `agent-docs/index.md`

Navigation hub. Keep under 250 lines. Include: What This Repo Is,
Documentation Scope, Recommended Reading Order, Subsystem Inventory
(with Sub-Modules column), Flow Inventory, Quick Links, Confidence
Summary.

### 2. Write `agent-docs/agent-brief.md`

Most important file. Keep under 150 lines. Include: What This Repo Is,
Classification, Architecture at a Glance, Subsystems That Matter Most,
Flows That Explain the System, Top Patterns to Follow, Common Change
Playbooks (2-3 concrete step-by-step guides for the most frequent
change types), Key Decisions, Known Uncertainties, Reading Path for a
Coding Agent.

### 3. Write `agent-docs/patterns.md`

Consolidate all per-subsystem patterns and system-wide patterns.
Include: Naming Conventions, File Organization, Error Handling, Common
Abstractions, Import/Module Conventions, Test Structure, Fixture/Mock
Patterns, Cross-Subsystem Inconsistencies.

### 4. Write `agent-docs/decisions.md`

Consolidate significant design decisions. 5-8 for medium/large repos,
3-5 for small. Each with: Scope, Chosen pattern, Evidence, Enables,
Costs, Alternatives, Inference, Assessment.

### 5. Write `agent-docs/glossary.md`

Project-specific terms, domain vocabulary, overloaded names.

### 6. Write `agent-docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items with:
Topic, Why Uncertain, Evidence Seen, What Would Resolve It.

### 7. Write Flow Docs (if warranted)

Only for cross-cutting flows spanning multiple subsystems. Write to
`agent-docs/flows/{name}.md`. Skip for simple repos.

### 8. Write `agent-docs/agent-protocol.md`

Copy-paste-ready instructions for wiring these docs into Claude Code
(`CLAUDE.md`), Codex (`AGENTS.md`), and Cursor (`.cursor/rules/`).

### 9. Update State

Set `phase_completed: 3` in `agent-docs/.analysis-state.md`. Record all
generated file paths.

### 10. Report Completion

> **Phase 3 of 3 complete. Documentation set is ready.**
>
> Generated:
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/agent-brief.md` — compact context for coding agents
> - `agent-docs/patterns.md` — code and test conventions
> - `agent-docs/decisions.md` — architectural trade-offs
> - `agent-docs/glossary.md` — project terms
> - `agent-docs/uncertainties.md` — unresolved questions
> - `agent-docs/agent-protocol.md` — agent wiring instructions
>
> **Usage:**
> - Coding agents: load `agent-docs/agent-brief.md` first
> - New team members: start with `agent-docs/index.md`
> - Before changes: check `decisions.md` and `uncertainties.md`
>
> **To wire into your agent:** Follow `agent-docs/agent-protocol.md`
> **To update:** Re-run any phase. It augments existing docs.

---

## Re-run Behavior

If synthesis docs exist, read first, update changed sections, remove
entries for deleted subsystems, preserve accurate entries.
