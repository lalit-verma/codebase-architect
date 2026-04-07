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

### 0. Capture Version Info

Run: `git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown"`

Record as `{short_sha}`. Record current UTC time. Apply this version
header to ALL generated files:
`> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}`

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
> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

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

### 1b. Self-Validate agent-context.md

Before proceeding to patterns.md, verify:

1. Count lines — must be under 120
2. No tables (no `|` characters outside code blocks)
3. No confidence labels ("Confirmed:", "Inference:", etc.)
4. All 7 sections present: What this repo is, Architecture map, Key
   patterns, Conventions, Do NOT, Key contracts, For deeper context
5. Every Architecture map entry has a file path in backticks
6. Every Key patterns entry has numbered steps with file paths
7. Every Key contracts entry has a file:line reference

If any check fails, fix agent-context.md before proceeding.

### 2. Write `agent-docs/patterns.md`

Consolidate all patterns from Phase 2. **Present to user first:**

> **Detected patterns for confirmation:**
> 1. {pattern} — {example file}, {N} files
> 2. ...
> **Confirm? Edit or remove any?**

After confirmation, write with: example file, file count, steps to add
new instance, conventions, anti-patterns.

### 2b. Write `agent-docs/routing-map.md`

Build a machine-readable YAML-in-markdown routing map. Two sections:
- `subsystem_routing`: per-subsystem (owns_paths, key_files, key_tests,
  common_tasks from Modification Guide)
- `pattern_routing`: per-pattern (template_file, registration,
  test_template from patterns.md)

Structured lookup table only. Do not duplicate agent-context.md content.

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

### 9. Write `agent-docs/agent-protocol.md`

Generate copy-paste-ready wiring instructions for Claude Code (`CLAUDE.md`),
Codex (`AGENTS.md`), and Cursor (`.cursor/rules/architecture-context.mdc`).
Each section should include the 5-step loading protocol with the quote
requirement for patterns.

### 9b. Quality Smoke Test

Read `agent-docs/agent-context.md` and answer these 5 questions using
ONLY that file's content:

1. "Where would I create a new [most common entity type]?"
   PASS: answer yields a concrete file path from Key patterns
2. "What pattern should I follow for [most common entity type]?"
   PASS: Key patterns has numbered steps for this entity type
3. "What should I NOT do in this codebase?"
   PASS: Do NOT section has >= 3 specific entries
4. "Which subsystem handles [primary flow from Phase 1]?"
   PASS: Architecture map clearly maps to this flow
5. "What are the key interfaces/contracts?"
   PASS: Key contracts has >= 2 entries with file:line refs

If any question fails, fix agent-context.md and re-check before
proceeding.

### 10. Update State

Set `phase_completed: 3` in `agent-docs/.analysis-state.md`.

### 11. Report Completion

> **Phase 3 of 3 complete. Documentation set ready.**
>
> Generated:
> - `agent-docs/agent-context.md` — **primary: compact agent context**
> - `agent-docs/patterns.md` — code patterns
> - `agent-docs/routing-map.md` — task-to-doc routing
> - `agent-docs/agent-brief.md` — compact architecture
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/decisions.md` — trade-offs
> - `agent-docs/glossary.md` — terms
> - `agent-docs/uncertainties.md` — gaps
> - `agent-docs/agent-protocol.md` — wiring instructions for agents
>
> ---
>
> **IMPORTANT: Wire agent-docs into your coding agent.**
>
> Follow the instructions in `agent-docs/agent-protocol.md` — it has
> copy-paste-ready snippets for Claude Code, Codex, and Cursor.
>
> Or add this block to your agent config file (`CLAUDE.md` for Claude Code,
> `.cursorrules` for Cursor, `AGENTS.md` for Codex). Create the file if
> it doesn't exist.
>
> ```
> ## Codebase Context
>
> Read `agent-docs/agent-context.md` once at session start — it has
> the architecture map, key patterns, and conventions.
>
> For non-trivial work, also consult the relevant
> `agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md`
> before creating new files of an established type. Skip both for
> small or self-contained edits.
> ```
>
> **To update:** Re-run any phase. It augments existing `agent-docs/`.

---

## Re-run Behavior

If synthesis docs exist: regenerate `agent-context.md` and `patterns.md`
entirely (stale context is harmful). Update other docs selectively.
Remove entries for deleted subsystems. Preserve accurate entries.
