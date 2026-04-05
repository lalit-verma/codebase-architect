You are running Phase 3 of a 3-phase codebase analysis workflow.
This is the final phase. The primary output is `agent-context.md` —
a compact file that coding agents load at session start for deep
codebase context.

## Progress

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| 2. Deep Dive (per subsystem) | complete |
| **3. Synthesize** | **<-- current** |

---

## Shared Resources

Look for shared reference files at `~/.claude/codebase-analysis/`.
If available, load on demand:
- `references/agent-context-rules.md` — agent-context generation rules
- `references/pattern-detection-guide.md` — pattern consolidation
- `templates/` — all output templates
- `examples/agent-context-example.md` — quality calibration target

---

## First: Read All Existing Docs

Read these files before doing anything else:

1. `agent-docs/.analysis-state.md` — analysis state
2. `agent-docs/system-overview.md` — top-level architecture
3. Every file in `agent-docs/subsystems/` — all deep-dive documents
   (including any recursive sub-subsystem docs)

If the analysis state shows subsystems still pending, warn the user:

> **Warning:** These subsystems have not been deep-dived yet: {list}.
> The synthesis will be incomplete for those areas. Continue anyway?

If `agent-docs/.analysis-state.md` does not exist, tell the user:

> **Phase 1 has not been run yet.** Run
> `/user:analyze-discover {description}` first.

Then stop.

---

## Mission

Synthesize all analysis into a complete documentation set optimized for
coding agent consumption. Generate `agent-context.md` FIRST — it is
the primary deliverable.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Base everything on the docs you just read — do
  not re-explore the codebase.
- **Factual only.** Limit to observable analysis.
- **Moderate citations.** Reference docs and file paths where claims
  originate.
- **Consolidate, don't repeat.** Merge duplicate observations.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

---

## Procedure

### Step 1: Generate `agent-docs/agent-context.md` — PRIMARY OUTPUT

This is the most important file produced by the entire analysis.

If `~/.claude/codebase-analysis/references/agent-context-rules.md`
exists, load and follow it strictly. If
`~/.claude/codebase-analysis/examples/agent-context-example.md` exists,
use it as a quality calibration target.

**Hard rules for agent-context.md:**
- Under 120 lines total
- Every line must be actionable for a coding agent
- Use concrete file paths, not abstract descriptions
- Use flat markdown: `##` headings, `- ` bullets, `` `code refs` ``
- Do NOT use tables (they waste tokens for agents)
- Do NOT use confidence labels (this is output for agents, not analysis)
- Must be standalone: agent reading only this file should know where
  everything is and what patterns to follow

**Structure:**

```markdown
# {Repo Name} — Agent Context

> Load this file at session start for full codebase context.
> Generated on {date}. Re-run analysis to update.

## What this repo is
{2-3 sentences: what it does, archetype, language, execution model.}

## Architecture map
- `{path}/` — {one-line purpose}
{8-20 entries, ordered by importance}

## Key patterns
### To add a new {thing}
1. {step with file path}
2. {step with file path}
{2-6 patterns, most important first}

## Conventions
- {convention} (see `{file}`)
{4-10 entries}

## Do NOT
- {anti-pattern} — {reason}
{3-8 entries}

## Key contracts
- `{file:line}` — {what it defines, who implements it}
{3-8 entries}

## For deeper context
- `agent-docs/agent-brief.md` — full architecture overview
- `agent-docs/patterns.md` — all detected code patterns
- `agent-docs/subsystems/{name}.md` — {when to read}
- `agent-docs/decisions.md` — trade-offs to respect
- `agent-docs/uncertainties.md` — check before assuming
```

**Content sourcing:**

| Section | Source from existing docs |
|---------|--------------------------|
| What this repo is | `system-overview.md` purpose section |
| Architecture map | All subsystem docs — extract key paths |
| Key patterns | Detected patterns from subsystem deep dives |
| Conventions | Design decisions + observed consistency |
| Do NOT | Edge cases, gotchas, anti-patterns from subsystem docs |
| Key contracts | Contracts and types from subsystem docs |
| For deeper context | Fixed pointers to other agent-docs/ files |

### Step 2: Generate `agent-docs/patterns.md`

Consolidate all patterns detected during Phase 2 deep dives.

**Semi-automated confirmation:** Before writing, present the full
pattern list in chat:

> **Detected patterns for confirmation:**
>
> 1. **{Pattern name}** ({category})
>    - Example: `{file path}`
>    - {N} files follow this pattern
>    - Steps: create at {path}, register at {file}, test at {path}
>
> 2. **{Pattern name}** ({category})
>    - ...
>
> **Confirm these patterns? Edit or remove any before I write
> `agent-docs/patterns.md`.**

After user confirms, write using the patterns template:

```markdown
# Code Patterns and Conventions

> Detected patterns for common operations. Confirmed by user.
> Generated on {date}.

## {Pattern Name} ({category})
- Example file: `{path}` (cleanest instance)
- Files following this pattern: {count} files in `{directory}/`
- Registration point: `{file:line}`

### To add a new instance
1. Create `{path convention}` following `{example file}`
2. {step with file reference}
3. Register in `{registration file:line}`
4. Add test at `{test path}` following `{test example}`

### Conventions within this pattern
- {naming rule}
- {structural rule}

### Anti-patterns
- {what NOT to do}
```

### Step 3: Generate `agent-docs/agent-brief.md`

Compact architecture map. Under 100 lines. More file-path-heavy than
prose-heavy.

```markdown
# {Repo Name} Agent Brief

> For the minimal version, read `agent-context.md` instead.

## What This Repo Is
{2-4 sentences}

## Classification
| Field | Value |
|-------|-------|
| Archetype | {value} |
| Primary language | {value} |
| Execution model | {value} |
| Scale | {value} |

## Architecture at a Glance
- Main entrypoints: `{paths}`
- Central subsystems: {names with paths}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most
| Subsystem | Why | Doc |
|-----------|-----|-----|
| {name} | {1 sentence} | `subsystems/{name}.md` |

## Flows That Explain the System
| Flow | Why | Doc |
|------|-----|-----|
| {flow} | {1 sentence} | `{path}` |

## Key Decisions
- {decision} (see `decisions.md`)

## Known Uncertainties
- `UNCERTAIN:` {item}

## Reading Path
1. `agent-context.md` (if not already loaded)
2. `system-overview.md`
3. Relevant subsystem doc
4. `patterns.md` before creating new files
5. `decisions.md` before proposing changes
6. `uncertainties.md` before risky assumptions
```

### Step 4: Generate `agent-docs/index.md`

Navigation hub. Under 250 lines.

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture documentation. Generated on {date}.

## What This Repo Is
{1 paragraph}

## Documentation Scope
- Coverage: {scope}
- Evidence quality: {level}
- Generated on: {date}

## Recommended Reading Order
1. **Coding agents:** Load `agent-context.md` at session start.
2. `agent-brief.md` — compact architecture.
3. `system-overview.md` — full system shape.
4. Subsystem docs relevant to your task.
5. `patterns.md` — conventions to follow.
6. `decisions.md` — trade-offs.
7. `uncertainties.md` — known gaps.

## Subsystem Inventory
| Subsystem | Role | Why It Exists | Confidence | Doc |
|-----------|------|---------------|------------|-----|

## Flow Inventory
| Flow | Trigger | Handoffs | Why | Doc |
|------|---------|----------|-----|-----|

## Quick Links
- `agent-context.md` — primary agent context file
- `patterns.md` — code patterns and conventions
- `agent-brief.md` — compact architecture
- `system-overview.md` — top-level architecture
- `decisions.md` — trade-offs
- `glossary.md` — terms
- `uncertainties.md` — gaps

## Confidence Summary
- High: {areas}
- Medium: {areas}
- `UNCERTAIN:` {areas}
```

### Step 5: Generate `agent-docs/decisions.md`

Consolidate significant design decisions from all analyses. 5-8 for
medium/large repos, 3-5 for small.

```markdown
# Architectural Decisions

> Separates code facts from inferred rationale. Generated on {date}.

## {Decision Title}
- **Scope:** {subsystems affected}
- **What was chosen:** {pattern/approach}
- **Evidence:** `{file paths}`
- **What it enables:** {benefits}
- **What it costs:** {downsides}
- **Alternative approaches:** {options}
- `Inference:` {likely rationale}
- **Assessment:** {factual observation}
```

### Step 6: Generate `agent-docs/glossary.md`

Project-specific terms, abstractions, domain vocabulary.

```markdown
# Glossary

> Project-specific terms. Generated on {date}.

| Term | Meaning | Where Used | Related Docs |
|------|---------|------------|--------------|
```

Prioritize: cross-subsystem terms, domain-specific terms, confusing
or overloaded names.

### Step 7: Generate `agent-docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items.

```markdown
# Uncertainties and Open Questions

> Check before making risky assumptions. Generated on {date}.

| Topic | Why Uncertain | Evidence Seen | What Would Resolve It |
|-------|---------------|---------------|-----------------------|
```

### Step 8: Generate Flow Docs (if warranted)

Only for cross-cutting flows that span multiple subsystems and teach
something not covered in subsystem docs. Write to
`agent-docs/flows/{name}.md`. Skip for simple repos.

```markdown
# {Flow Name}

## Why This Flow Matters
{1 paragraph}

## Trigger
- Initiator: {user/system/job/event}
- Entrypoint: `{file:line}`

## Sequence
1. `{file:line}` receives {input}
2. `{file:line}` transforms/routes
3. `{file:line}` coordinates downstream
4. `{file:line}` returns/persists outcome

## Side Effects
- {state changes}

## Failure Handling
- {error propagation}

## Notes
- `Confirmed:` {fact}
- `Inference:` {rationale}
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
> - `agent-docs/agent-context.md` — **primary: compact context for
>   coding agents**
> - `agent-docs/patterns.md` — code patterns and conventions
> - `agent-docs/agent-brief.md` — compact architecture
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/decisions.md` — architectural trade-offs
> - `agent-docs/glossary.md` — project terms
> - `agent-docs/uncertainties.md` — unresolved questions
> {- `agent-docs/flows/{name}.md` — if generated}
>
> ---
>
> ---
>
> **IMPORTANT: Wire agent-docs into your coding agent.**
>
> Add the following block to your agent config file (`CLAUDE.md` for
> Claude Code, `.cursorrules` for Cursor, `AGENTS.md` for Codex).
> Create the file if it doesn't exist.
>
> ```
> ## Codebase Context — Read Before Every Task
>
> Before starting any task in this repository, follow these steps in
> order. Do not skip steps. Do not start writing code until you have
> completed the reading.
>
> ### Step 1: Load core context (always)
> Read `agent-docs/agent-context.md` fully. This contains the
> architecture map, code patterns, conventions, and anti-patterns.
> Internalize the patterns and constraints before proceeding.
>
> ### Step 2: Load task-relevant subsystem docs
> Identify which subsystem(s) your task touches based on the
> architecture map. Read the corresponding
> `agent-docs/subsystems/{name}.md`. If sub-subsystem docs exist
> in a subdirectory, read those too.
>
> ### Step 3: Check patterns before creating new files
> Before creating any new file, read `agent-docs/patterns.md` and
> follow the established pattern for that file type.
>
> ### Step 4: Check constraints before architectural changes
> If changing subsystem interactions, dependencies, or contracts —
> read `agent-docs/decisions.md` and
> `agent-docs/uncertainties.md` first.
>
> ### Step 5: Confirm your understanding
> Before writing code, briefly state which subsystem(s) you are
> working in, which patterns you will follow, and any constraints
> that apply. Then proceed.
> ```
>
> ---
>
> **To update:** Re-run any phase. It augments existing `agent-docs/`.

---

## Re-run Behavior

If synthesis docs already exist:

1. Read all existing `agent-docs/` first
2. Compare against current subsystem docs
3. **Regenerate `agent-context.md` entirely** — it's compact enough to
   rewrite, and stale context is harmful
4. **Regenerate `patterns.md`** — re-present patterns to user for
   confirmation
5. Update changed sections in other files
6. Remove entries for subsystems that no longer exist
7. Preserve entries that are still accurate
8. Add update timestamp to modified files
