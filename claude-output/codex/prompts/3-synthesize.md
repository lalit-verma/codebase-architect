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

1. `docs/.analysis-state.md`
2. `docs/system-overview.md`
3. Every file in `docs/subsystems/`

If subsystems are still pending, warn the user and ask whether to
continue with incomplete coverage.

If `docs/.analysis-state.md` does not exist, say:
> **Phase 1 has not been run.** Run the Phase 1 prompt first.

---

## Mission

Produce the final documentation set. Structure everything for efficient
consumption by both humans and future AI agents.

## Constraints

- **Read-only.** Do not modify source code.
- **Base on existing docs.** Do not re-explore the codebase.
- **Factual only.** Observable analysis.
- **Consolidate.** If multiple deep dives noted the same thing, merge.
- **Moderate citations.** Reference docs and file paths where claims originate.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

---

## Procedure

### 1. Write `docs/index.md`

Navigation hub. Keep under 250 lines.

```markdown
# {Repo Name} Documentation Index

> Auto-generated. Review uncertain sections before relying as ground truth.

## What This Repo Is
{1 paragraph}

## Documentation Scope
- Coverage: {scope}
- Evidence quality: {level}
- Generated on: {date}

## Recommended Reading Order
1. `agent-brief.md` — compact architecture map
2. `system-overview.md` — full system shape
3. Subsystem docs relevant to your task
4. `decisions.md` — key trade-offs
5. `uncertainties.md` — unresolved assumptions

## Subsystem Inventory
| Subsystem | Role | Why It Exists | Confidence | Doc |
|-----------|------|---------------|------------|-----|

## Flow Inventory
| Flow | Trigger | Handoffs | Why Read It | Doc |
|------|---------|----------|-------------|-----|

## Quick Links
- `agent-brief.md`, `system-overview.md`, `decisions.md`, `glossary.md`, `uncertainties.md`

## Confidence Summary
- High: {areas}
- Medium: {areas}
- `UNCERTAIN:` {areas}
```

### 2. Write `docs/agent-brief.md`

Compact context file for AI agents. Keep under 150 lines.

```markdown
# {Repo Name} Agent Brief

> Read this first to orient. Load specific docs as needed.

## What This Repo Is
{2-4 sentences}

## Classification
| Field | Value |
|-------|-------|

## Architecture at a Glance
- Entrypoints, subsystems, flows, state, config

## Subsystems That Matter Most
| Subsystem | Why | Read Next |
|-----------|-----|-----------|

## Flows That Explain the System
| Flow | Why | Read Next |
|------|-----|-----------|

## Key Decisions
- {bullet list}

## Known Uncertainties
- {bullet list}

## Reading Path for a New Agent
1. You are here
2. system-overview.md
3. Relevant subsystem doc
4. decisions.md
5. uncertainties.md
```

### 3. Write `docs/decisions.md`

Key architectural decisions from across all analyses. 5-8 for
medium/large repos, 3-5 for small.

```markdown
# Architectural Decisions

> Separates code facts from inferred rationale.

## {Decision Title}
- Scope: {subsystems affected}
- Chosen: {pattern}
- Evidence: {file paths}
- Enables: {benefits}
- Costs: {downsides}
- Alternatives: {options}
- `Inference:` {likely rationale}
- Assessment: {factual observation}
```

### 4. Write `docs/glossary.md`

Project-specific terms, abstractions, domain vocabulary.

```markdown
# Glossary
| Term | Meaning | Where Used | Related Docs |
|------|---------|------------|--------------|
```

Prioritize: cross-subsystem terms, domain-specific terms, confusing
or overloaded names.

### 5. Write `docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items.

```markdown
# Uncertainties and Open Questions
| Topic | Why Uncertain | Evidence Seen | What Would Resolve It |
|-------|---------------|---------------|-----------------------|
```

### 6. Write Flow Docs (if warranted)

Only for cross-cutting flows that span multiple subsystems and teach
something not already covered in subsystem docs. Write to
`docs/flows/{name}.md`. Skip for simple repos.

### 7. Update State

Set `phase_completed: 3` in `docs/.analysis-state.md`.

### 8. Report Completion

> **Phase 3 of 3 complete. Documentation set is ready.**
>
> Generated:
> - `docs/index.md` — navigation hub
> - `docs/agent-brief.md` — compact context for agents
> - `docs/decisions.md` — architectural trade-offs
> - `docs/glossary.md` — project terms
> - `docs/uncertainties.md` — unresolved questions
>
> **Usage:**
> - New team members: start with `docs/index.md`
> - AI agents: load `docs/agent-brief.md` first
> - Before changes: check `decisions.md` and `uncertainties.md`
>
> **To update:** Re-run any phase. It augments existing docs.

---

## Re-run Behavior

If synthesis docs exist, read first, update changed sections, remove
entries for deleted subsystems, preserve accurate entries.
