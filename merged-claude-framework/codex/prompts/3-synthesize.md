# Phase 3: Synthesize

## Progress

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| 2. Deep Dive | complete |
| **3. Synthesize** | **<-- current** |

---

## First: Read All Docs

Read before doing anything:
1. `agent-docs/.analysis-state.md`
2. `agent-docs/system-overview.md`
3. Every file in `agent-docs/subsystems/` (including recursive children)

If subsystems still pending, warn and ask whether to continue.

If `agent-docs/.analysis-state.md` does not exist:
> **Phase 1 has not been run.** Run the Phase 1 prompt first.

---

## Mission

Synthesize all analysis into a complete documentation set. Generate
`agent-context.md` FIRST — it is the primary deliverable, a compact
file coding agents load at session start.

## Constraints

- **Read-only.** Do not modify source code.
- **Base on existing docs.** Do not re-explore the codebase.
- **Factual only.** Observable analysis.
- **Consolidate.** Merge duplicate observations.
- **Moderate citations.** Reference docs and file paths.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

---

## Procedure

### 1. Write `agent-docs/agent-context.md` — PRIMARY OUTPUT

**Hard rules:**
- Under 120 lines total
- Every line actionable for a coding agent
- Concrete file paths, not abstract descriptions
- Flat markdown: `##` headings, `- ` bullets, `` `code refs` ``
- NO tables, NO confidence labels
- Standalone: agent reading only this file should navigate the repo

**Structure:**
```markdown
# {Repo Name} — Agent Context

> Load this file at session start for full codebase context.
> Generated on {date}. Re-run analysis to update.

## What this repo is
{2-3 sentences: what it does, archetype, language, execution model.}

## Architecture map
- `{path}/` — {purpose}
{8-20 entries by importance}

## Key patterns
### To add a new {thing}
1. {step with file path}
{2-6 patterns}

## Conventions
- {convention} (see `{file}`)
{4-10 entries}

## Do NOT
- {anti-pattern} — {reason}
{3-8 entries}

## Key contracts
- `{file:line}` — {what it defines, who implements}
{3-8 entries}

## For deeper context
- `agent-docs/agent-brief.md` — architecture overview
- `agent-docs/patterns.md` — all code patterns
- `agent-docs/decisions.md` — trade-offs to respect
- `agent-docs/uncertainties.md` — check before assuming
```

### 2. Write `agent-docs/patterns.md`

Consolidate all patterns from Phase 2. **Present to user first:**

> **Detected patterns for confirmation:**
> 1. {pattern} — {example file}, {N} files
> 2. ...
> **Confirm? Edit or remove any?**

After confirmation, write with: example file, file count, steps to add
new instance, conventions, anti-patterns.

### 3. Write `agent-docs/agent-brief.md`

Compact architecture. Under 100 lines. File-path-heavy.

### 4. Write `agent-docs/index.md`

Navigation hub. Under 250 lines. Subsystem inventory, flow inventory,
quick links, confidence summary.

### 5. Write `agent-docs/decisions.md`

5-8 decisions for medium/large, 3-5 for small. Per decision: scope,
chosen, evidence, enables, costs, alternatives, inference, assessment.

### 6. Write `agent-docs/glossary.md`

Project-specific terms. Prioritize cross-subsystem and domain-specific.

### 7. Write `agent-docs/uncertainties.md`

All `UNCERTAIN:` and `NEEDS CLARIFICATION:` items consolidated.

### 8. Write Flow Docs (if warranted)

Only cross-cutting flows spanning multiple subsystems. Write to
`agent-docs/flows/{name}.md`. Skip for simple repos.

### 9. Update State

Set `phase_completed: 3` in `agent-docs/.analysis-state.md`.

### 10. Report Completion

> **Phase 3 of 3 complete. Documentation set ready.**
>
> Generated:
> - `agent-docs/agent-context.md` — **primary: compact agent context**
> - `agent-docs/patterns.md` — code patterns
> - `agent-docs/agent-brief.md` — compact architecture
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/decisions.md` — trade-offs
> - `agent-docs/glossary.md` — terms
> - `agent-docs/uncertainties.md` — gaps
>
> ---
>
> **IMPORTANT: Wire agent-docs into your coding agent.**
>
> Add this block to your agent config file (`CLAUDE.md` for Claude Code,
> `.cursorrules` for Cursor, `AGENTS.md` for Codex). Create the file if
> it doesn't exist.
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
> **To update:** Re-run any phase. It augments existing `agent-docs/`.

---

## Re-run Behavior

If synthesis docs exist: regenerate `agent-context.md` and `patterns.md`
entirely (stale context is harmful). Update other docs selectively.
Remove entries for deleted subsystems. Preserve accurate entries.
