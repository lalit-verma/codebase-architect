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

Before proceeding, verify:

1. Count lines — must be under 120
2. No tables (no `|` characters outside code blocks)
3. No confidence labels ("Confirmed:", "Inference:", etc.)
4. All 7 sections present: What this repo is, Architecture map, Key
   patterns, Conventions, Do NOT, Key contracts, For deeper context
5. Every Architecture map entry has a file path in backticks
6. Every Key patterns entry has numbered steps with file paths
7. Every Key contracts entry has a file:line reference

If any check fails, fix agent-context.md before proceeding.

### 1c. Write `agent-docs/agent-context-nano.md` — INLINED NANO-DIGEST

Generate the nano-digest immediately after `agent-context.md`. It is
a strict subset of `agent-context.md` designed to be pasted directly
into the user's `AGENTS.md` so the most-used context lives in the
system prompt — no Read calls, no context accumulation.

**Hard rules:**
- 40 lines maximum (target 25-35), ~1.5-2.5K tokens
- **Strict subset of `agent-context.md`** — introduce no new facts
- **Zero references to `agent-docs/`** anywhere in the file
- No tables, no confidence labels
- 5 sections only: What this is, Where things live (5-8 paths), 2
  patterns (most-used), Do NOT (2-3 highest-blast-radius entries)

**Structure:**
```markdown
# {Repo Name} — Quick Context

> Inlined nano-context for coding agents.
> Generated: {YYYY-MM-DD} | v1 | {short_sha}

## What this is
{1-2 sentences from agent-context.md's "What this repo is"}

## Where things live
- `{path}/` — {purpose}
{5-8 entries — top of agent-context.md's Architecture map by importance}

## How to add a new {most common thing}
1. Create `{path}` following `{example file}`
2. {step with concrete file reference}
3. Register in `{file:line}`
4. Test at `{test path}` following `{test example}`

## How to add a new {second most common thing}
1. Create `{path}` following `{example file}`
2. {step with concrete file reference}
3. Register in `{file:line}`
4. Test at `{test path}` following `{test example}`

## Do NOT
- {anti-pattern} — {1-line reason}
{2-3 entries — highest blast radius from agent-context.md's Do NOT}
```

**Sourcing:** Pull from `agent-context.md` only. Do not re-explore.
- What this is → first 1-2 sentences of `agent-context.md`'s "What this repo is"
- Where things live → top 5-8 paths from `agent-context.md`'s "Architecture map" by navigation centrality
- 2 patterns → the 2 patterns from `agent-context.md`'s "Key patterns" with the highest file count
- Do NOT → 2-3 entries from `agent-context.md`'s "Do NOT" with the highest blast radius

### 1d. Self-Validate agent-context-nano.md

1. Line count ≤ 40
2. Zero `agent-docs/` references in the file
3. No tables, no confidence labels
4. All 5 sections present
5. Each pattern has 3+ numbered steps with file paths
6. Each Do NOT has a 1-line reason
7. Cross-check: every fact also in `agent-context.md`

If any check fails, fix before proceeding.

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

Generate copy-paste-ready wiring instructions for all 3 platforms
using the **hybrid wiring strategy**: inlined nano-digest + Explore
enrichment pointer.

Inline the actual contents of `agent-context-nano.md` into the
generated `agent-protocol.md` (do not reference by path) so the user
has a single self-contained file to copy from.

Each platform section should follow this shape:

```markdown
## For {Platform}
Add to your `{config file}`:

---
### Codebase Context

{actual contents of agent-context-nano.md inlined here}

If you spawn a research subagent for codebase exploration, point it
at `agent-docs/agent-context.md` as a starting heuristic. Deeper docs:
`agent-docs/subsystems/{name}.md`, `agent-docs/patterns.md`,
`agent-docs/decisions.md`. Do not read these from the main thread.
---
```

Critical: do NOT generate any 5-step "before every task" ritual,
"do not skip steps" framing, or "quote the specific pattern"
instruction. The benchmark showed those triggered cost without
quality gains. The hybrid wiring is intentionally minimal.

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
> - `agent-docs/agent-context.md` — compact agent context (full)
> - `agent-docs/agent-context-nano.md` — **inlined nano-digest for
>   AGENTS.md (load-bearing wiring)**
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
> **IMPORTANT: Wire agent-docs into your coding agent (hybrid wiring).**
>
> The wiring has two parts:
>
> 1. **Paste the contents of `agent-docs/agent-context-nano.md`**
>    directly into your `AGENTS.md` (or `CLAUDE.md` for Claude Code,
>    `.cursorrules` for Cursor). Create the file if it does not exist.
>    The nano-digest is meant to live in the system prompt, not be
>    referenced by path.
>
> 2. **Add this single line below the pasted nano-digest:**
>
>    ```
>    If you spawn a research subagent for codebase exploration, point
>    it at `agent-docs/agent-context.md` as a starting heuristic.
>    Deeper docs: `agent-docs/subsystems/{name}.md`,
>    `agent-docs/patterns.md`, `agent-docs/decisions.md`. Do not
>    read these from the main thread.
>    ```
>
> Why this shape: benchmark data showed main-thread Reads of
> `agent-docs/` triggered long-context fallback to larger models,
> inflating cost without a quality gain. Inlining the nano-digest puts
> the load-bearing context in the system prompt while leaving deeper
> docs available to subagents that run in their own context.
>
> The full copy-paste-ready snippets for all 3 platforms (with the
> nano-digest already inlined) are in `agent-docs/agent-protocol.md`.
>
> **To update:** Re-run any phase. It augments existing `agent-docs/`.
> `agent-context-nano.md` is regenerated entirely on re-run; you will
> need to re-paste it into your agent config.

---

## Re-run Behavior

If synthesis docs exist: regenerate `agent-context.md` and `patterns.md`
entirely (stale context is harmful). Update other docs selectively.
Remove entries for deleted subsystems. Preserve accurate entries.
