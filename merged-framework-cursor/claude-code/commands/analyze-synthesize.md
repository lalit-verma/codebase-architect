You are running Phase 3 of a 3-phase codebase analysis workflow.

## Progress

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| 2. Deep Dive (per subsystem) | complete |
| **3. Synthesize** | **<-- current** |

---

## First: Read All Existing Docs

Read these files before doing anything else:

1. `agent-docs/.analysis-state.md` — analysis state, subsystem map, patterns
2. `agent-docs/system-overview.md` — top-level architecture
3. Every file in `agent-docs/subsystems/` — all deep-dive documents
   (including sub-module docs in subdirectories)

If the analysis state shows subsystems still pending deep dive, warn:

> **Warning:** These subsystems have not been deep-dived yet: {list}.
> The synthesis will be incomplete for those areas. Continue anyway?

If `agent-docs/.analysis-state.md` does not exist, tell the user:

> **Phase 1 has not been run yet.** Run `/project:analyze-discover {description}` first.

Then stop.

---

## Mission

Synthesize all analysis into a complete, navigable documentation set
optimized for coding agent consumption. This is the final phase. A
coding agent loading these docs should be able to orient itself in
the codebase, find the right files, follow the right patterns, and
avoid architectural mistakes — without needing to explore from scratch.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Base everything on the docs you just read — do not re-explore the codebase.
- **Factual only.** Limit to observable analysis.
- **Moderate citations.** Reference specific docs and file paths where claims originate.
- **Consolidate, don't repeat.** If multiple deep dives noted the same pattern, consolidate.
- Use labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

## Quality Bar

The synthesis is good enough when:

- a coding agent can read `agent-brief.md` and immediately know where
  to look for any task
- `patterns.md` gives enough detail to write code that matches the
  repo's existing style
- the "Common Change Playbooks" in `agent-brief.md` are concrete
  enough to follow step-by-step
- `uncertainties.md` prevents false confidence in shaky areas
- `decisions.md` prevents agents from accidentally reversing
  deliberate architectural choices

---

## Procedure

### Step 1: Produce `agent-docs/index.md`

Navigation hub. Keep under 250 lines.

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture documentation. Review uncertain sections
> before relying as ground truth.

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
4. `patterns.md` — code conventions to follow
5. `decisions.md` — key trade-offs
6. `uncertainties.md` — areas needing care

## Subsystem Inventory
| Subsystem | Role | Why It Exists | Confidence | Doc | Sub-Modules |
|-----------|------|---------------|------------|-----|-------------|

## Flow Inventory
| Flow | Trigger | Handoffs | Why Read It | Doc |
|------|---------|----------|-------------|-----|

## Quick Links
- `agent-brief.md`, `agent-protocol.md`, `system-overview.md`
- `patterns.md`, `decisions.md`, `glossary.md`, `uncertainties.md`

## Confidence Summary
- High: {areas}
- Medium: {areas}
- `UNCERTAIN:` {areas}
```

### Step 2: Produce `agent-docs/agent-brief.md`

This is the most important file in the entire documentation set. A
coding agent reads this FIRST to orient itself. Optimize for signal
density. Keep under 150 lines.

```markdown
# {Repo Name} — Agent Brief

> Load this file before starting any coding task in this repository.
> Then load the specific subsystem doc relevant to your task.

## What This Repo Is
{2-4 sentences: concrete, not vague}

## Classification
| Field | Value |
|-------|-------|

## Architecture at a Glance
- Main entrypoints: `{paths}`
- Central subsystems: {names}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most
| Subsystem | Why It Matters | Read Next |
|-----------|----------------|-----------|

## Flows That Explain the System
| Flow | Why It Matters | Read Next |
|------|----------------|-----------|

## Top Patterns to Follow
| Pattern | Scope | Example |
|---------|-------|---------|

## Common Change Playbooks

### Adding a new {most common change type}
1. {concrete step with file path}
2. {concrete step}
3. {concrete step}
See: `subsystems/{name}.md` → Modification Guide

### Adding a new {second most common change type}
1. {step}
2. {step}
See: `subsystems/{name}.md` → Modification Guide

## Key Decisions
- {decision with short rationale}
- Full analysis: `decisions.md`

## Known Uncertainties
- `UNCERTAIN:` {item}
- Full list: `uncertainties.md`

## Reading Path for a Coding Agent
1. You are here — `agent-brief.md`
2. `system-overview.md` for full architecture
3. The subsystem doc most relevant to your task
4. `patterns.md` before writing new code
5. `decisions.md` before proposing structural changes
6. `uncertainties.md` for assumptions near your change area
```

### Step 3: Produce `agent-docs/patterns.md`

Consolidate all per-subsystem patterns and the system-wide patterns
from Phase 1 into one document. A coding agent reads this before
writing any new code.

```markdown
# {Repo Name} — Code and Test Patterns

> Follow these conventions when adding new code.

## Naming Conventions
| Element | Convention | Example | Scope |
|---------|-----------|---------|-------|

## File Organization
| Convention | Description | Example |
|-----------|-------------|---------|

## Error Handling
| Pattern | Where Used | Example File |
|---------|-----------|--------------|

## Common Abstractions
| Abstraction | Purpose | Interface | Implementations |
|-------------|---------|-----------|-----------------|

## Import and Module Conventions
| Convention | Description | Example |
|-----------|-------------|---------|

## Test Structure and Conventions
| Aspect | Convention | Example File |
|--------|-----------|--------------|

## Fixture and Mock Patterns
| Pattern | Usage | Example File |
|---------|-------|--------------|

## Cross-Subsystem Inconsistencies
| Inconsistency | Subsystem A | Subsystem B | Recommendation |
|--------------|-------------|-------------|----------------|
```

### Step 4: Produce `agent-docs/decisions.md`

Consolidate the most significant design decisions from across all
subsystem analyses.

```markdown
# Architectural Decisions

> Separates code facts from inferred rationale.

## {Decision Title}
- **Scope:** {subsystems affected}
- **Chosen:** {pattern}
- **Evidence:** `{file paths}`
- **Enables:** {benefits}
- **Costs:** {downsides}
- **Alternatives:** {options}
- `Inference:` {likely rationale}
- **Assessment:** {observation}
```

Include 5-8 decisions for medium/large repos, 3-5 for small repos.
Only decisions that shape multiple parts of the system.

### Step 5: Produce `agent-docs/glossary.md`

```markdown
# Glossary

| Term | Meaning | Where Used | Related Docs |
|------|---------|------------|--------------|
```

Prioritize: cross-subsystem terms, domain-specific terms, confusing
or overloaded names.

### Step 6: Produce `agent-docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items.

```markdown
# Uncertainties and Open Questions

> A coding agent should check this before making changes near any
> listed area.

| Topic | Why Uncertain | Evidence Seen | What Would Resolve It |
|-------|---------------|---------------|-----------------------|
```

### Step 7: Produce Flow Docs (if warranted)

Only for cross-cutting flows that span multiple subsystems and teach
something not already covered in subsystem docs. Write to
`agent-docs/flows/{name}.md`. Skip for simple repos.

```markdown
# {Flow Name}

## Why This Flow Matters
{1 paragraph}

## Trigger
- Initiator: {user/system/job/event}
- Entrypoint: `{file}`

## Sequence
1. `{file}` receives {input}
2. `{file}` transforms/validates/routes
3. `{file}` coordinates downstream
4. `{file}` returns/emits/persists outcome

## Side Effects
- {state changes, events, outputs}

## Failure Handling
- {error sources and propagation}

## Trade-off Notes
- `Confirmed:` / `Inference:` / `UNCERTAIN:` items
```

### Step 8: Produce `agent-docs/agent-protocol.md`

Generate the agent loading protocol — copy-paste-ready instructions
for wiring these docs into coding agent context.

```markdown
# Agent Protocol — How to Use These Docs

## For Claude Code

Add this to your repo's `CLAUDE.md`:

> Before starting any coding task:
> 1. Read `agent-docs/agent-brief.md` for architecture context.
> 2. Read the relevant `agent-docs/subsystems/{name}.md`.
> 3. Read `agent-docs/patterns.md` to match code conventions.
> 4. If making structural changes, read `agent-docs/decisions.md`.
> 5. If working near uncertain areas, check `agent-docs/uncertainties.md`.

## For Codex

Add this to your repo's `AGENTS.md`:

> [same instructions adapted for Codex]

## For Cursor

Create `.cursor/rules/architecture-context.mdc`:

> [same instructions as a Cursor rule]
```

### Step 9: Update Analysis State

Update `agent-docs/.analysis-state.md`:
- Set `phase_completed: 3`
- Record all generated files

### Step 10: Report Completion

Tell the user:

> **Phase 3 of 3 complete. Documentation set is ready.**
>
> Generated:
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/agent-brief.md` — compact context for coding agents
> - `agent-docs/patterns.md` — code and test conventions
> - `agent-docs/decisions.md` — key architectural trade-offs
> - `agent-docs/glossary.md` — project-specific terms
> - `agent-docs/uncertainties.md` — unresolved questions
> - `agent-docs/agent-protocol.md` — instructions for wiring into your agent
> {- `agent-docs/flows/{name}.md` — if any were generated}
>
> **How to use these docs:**
> - Coding agents: load `agent-docs/agent-brief.md` first, then relevant subsystem docs
> - New team members: start with `agent-docs/index.md`
> - Before making changes: check `agent-docs/decisions.md` and `agent-docs/uncertainties.md`
>
> **To wire into your agent:** Follow the instructions in `agent-docs/agent-protocol.md`
>
> **To re-run or update:** Run any phase again. It will augment existing docs.

---

## Re-run Behavior

If synthesis docs already exist:

1. Read all existing docs first
2. Compare against current subsystem docs
3. Update sections that have new information
4. Remove entries for subsystems that no longer exist
5. Preserve entries that are still accurate
6. Add a note: `> Updated on {date}.`
