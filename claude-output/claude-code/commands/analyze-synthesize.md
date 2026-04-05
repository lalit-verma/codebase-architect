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

1. `docs/.analysis-state.md` — analysis state and subsystem map
2. `docs/system-overview.md` — top-level architecture
3. Every file in `docs/subsystems/` — all deep-dive documents

If the analysis state shows subsystems still pending deep dive, warn
the user:

> **Warning:** These subsystems have not been deep-dived yet: {list}.
> The synthesis will be incomplete for those areas. Continue anyway?

If `docs/.analysis-state.md` does not exist, tell the user:

> **Phase 1 has not been run yet.** Run `/project:analyze-discover {description}` first.

Then stop.

---

## Mission

Synthesize all analysis into a complete, navigable documentation set.
This is the final phase. Your output must be structured for efficient
consumption by both humans and future AI agents working in this repo.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Base everything on the docs you just read — do not re-explore the codebase.
- **Factual only.** Limit to observable analysis.
- **Moderate citations.** Reference specific docs and file paths where claims originate.
- **Consolidate, don't repeat.** If multiple deep dives noted the same pattern, consolidate rather than repeating.
- Use labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

---

## Procedure

### Step 1: Produce `docs/index.md`

This is the navigation hub. A new person or agent opens this first.

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture documentation. Review uncertain sections
> before relying as ground truth.

## What This Repo Is

{1 paragraph: what the repository is, its runtime shape, and the scope
these docs cover.}

## Documentation Scope

- Coverage: {whole repo / top-level monorepo architecture / specific app or package}
- Evidence quality: {high/medium/mixed} with brief reason
- Generated on: {date}

## Recommended Reading Order

1. Start with `agent-brief.md` for a compact architecture map.
2. Then `system-overview.md` for the full system shape.
3. Then subsystem and flow docs relevant to your task.
4. Read `decisions.md` for key trade-offs.
5. Check `uncertainties.md` before making risky assumptions.

## Subsystem Inventory

| Subsystem | Role | Why It Exists | Confidence | Doc |
|-----------|------|---------------|------------|-----|
| {name} | {tag} | {1 sentence} | {level} | `subsystems/{name}.md` |

## Flow Inventory

| Flow | Trigger | Handoffs | Why Read It | Doc |
|------|---------|----------|-------------|-----|
| {flow} | {trigger} | {A -> B -> C} | {1 sentence} | {doc path or "see system-overview.md"} |

## Quick Links

- `agent-brief.md` — compact context for AI agents
- `system-overview.md` — top-level architecture
- `decisions.md` — key architectural trade-offs
- `glossary.md` — project-specific terms
- `uncertainties.md` — unresolved questions

## Confidence Summary

- High confidence: {areas}
- Medium confidence: {areas}
- `UNCERTAIN:` {areas that need care}
```

Keep under 250 lines.

### Step 2: Produce `docs/agent-brief.md`

This is the compact context-loading file for future AI agents. It
should be the single file an agent reads to become oriented.

```markdown
# {Repo Name} Agent Brief

> Compact context file for AI agents. Read this first, then load
> specific docs as needed.

## What This Repo Is

{2-4 sentences: what the repo does, its archetype, and the key
architectural shape.}

## Classification

| Field | Value |
|-------|-------|
| Archetype | {application/library/SDK/framework/monorepo/hybrid} |
| Primary language | {language} |
| Execution model | {model} |
| Scale | {size tier} |

## Architecture at a Glance

- Main entrypoints: {paths}
- Central subsystems: {names}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most

| Subsystem | Why It Matters | Read Next |
|-----------|----------------|-----------|
| {name} | {1 sentence} | `subsystems/{name}.md` |

## Flows That Explain the System

| Flow | Why It Matters | Read Next |
|------|----------------|-----------|
| {flow} | {1 sentence} | {doc path} |

## Key Decisions

- {decision with short rationale}
- {decision with short rationale}
- {decision with short rationale}

## Known Uncertainties

- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}

## Reading Path for a New Agent

1. You are here (`agent-brief.md`)
2. Read `system-overview.md` for full architecture
3. Read the subsystem doc most relevant to your task
4. Read `decisions.md` before proposing changes
5. Check `uncertainties.md` before making risky assumptions
```

Keep under 150 lines. Optimize for signal density.

### Step 3: Produce `docs/decisions.md`

Consolidate the most significant design decisions from across all
subsystem analyses.

```markdown
# Architectural Decisions

> Separates code facts from inferred rationale. Treat `Inference:`
> sections as architectural reading, not ground truth from authors.

## {Decision Title}

- **Scope:** {which subsystems it affects}
- **What was chosen:** {pattern/approach}
- **Evidence:** `{file path}`, `{file path}`
- **What it enables:** {benefits}
- **What it costs:** {downsides}
- **Alternative approaches:** {credible options}
- `Inference:` {likely reason this trade-off was accepted}
- **Assessment:** {factual observation on whether it fits the system}
```

Include only decisions that shape multiple parts of the system. Aim for
5-8 decisions for medium/large repos, 3-5 for small repos.

### Step 4: Produce `docs/glossary.md`

Extract recurring terms, abstractions, and project-specific vocabulary
from across all docs.

```markdown
# Glossary

| Term | Meaning | Where Used | Related Docs |
|------|---------|------------|--------------|
| {term} | {definition} | {subsystems/files} | `{doc paths}` |
```

Prioritize terms that:
- Are used across multiple subsystems
- Are domain-specific (not generic programming terms)
- Could confuse a new engineer or agent (overloaded names, internal jargon)

### Step 5: Produce `docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items from
across all docs into one file.

```markdown
# Uncertainties and Open Questions

| Topic | Why Uncertain | Evidence Seen | What Would Resolve It |
|-------|---------------|---------------|-----------------------|
| {topic} | {reason} | `{files}` | {human answer / runtime observation / scoped analysis} |
```

This file prevents false confidence from contaminating the rest of the docs.

### Step 6: Produce Flow Docs (if warranted)

If the system overview identified cross-cutting flows that span multiple
subsystems and are architecturally significant, write them to
`docs/flows/{flow-name}.md`:

```markdown
# {Flow Name}

## Why This Flow Matters
{1 paragraph: what architectural question this flow answers.}

## Trigger
- Initiator: {user/system/job/event}
- Entrypoint: `{file path}`

## Sequence
1. `{file path}` receives {input}
2. `{file path}` transforms/validates/routes
3. `{file path}` coordinates downstream work
4. `{file path}` returns/emits/persists outcome

## Side Effects
- {state changes, events emitted, outputs written}

## Failure Handling
- {error sources and propagation}
- {retry/fallback behavior}

## Trade-off Notes
- `Confirmed:` {evidenced property}
- `Inference:` {likely rationale}
```

Only write flow docs for flows that teach something not already covered
in subsystem docs. Skip this step for simple repos.

### Step 7: Update Analysis State

Update `docs/.analysis-state.md`:
- Set `phase_completed: 3`
- Record all generated files

### Step 8: Report Completion

Tell the user:

> **Phase 3 of 3 complete. Documentation set is ready.**
>
> Generated:
> - `docs/index.md` — navigation hub
> - `docs/agent-brief.md` — compact context for AI agents
> - `docs/decisions.md` — key architectural trade-offs
> - `docs/glossary.md` — project-specific terms
> - `docs/uncertainties.md` — unresolved questions
> {- `docs/flows/{name}.md` — if any were generated}
>
> **How to use these docs:**
> - New team members: start with `docs/index.md`
> - AI agents (Claude/Codex): load `docs/agent-brief.md` first
> - Before making changes: check `docs/decisions.md` and `docs/uncertainties.md`
>
> **To re-run or update:** Run any phase again. It will augment existing docs rather than overwrite.

---

## Re-run Behavior

If synthesis docs already exist:

1. Read all existing docs first
2. Compare against current subsystem docs
3. Update sections that have new information
4. Remove entries for subsystems that no longer exist
5. Preserve entries that are still accurate
6. Add a note: `> Updated on {date}.`
