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
- `references/nano-context-rules.md` — nano-digest generation rules
- `references/pattern-detection-guide.md` — pattern consolidation
- `references/validation-rules.md` — self-check criteria and smoke test
- `templates/` — all output templates (including `agent-context-nano-template.md`)
- `examples/agent-context-example.md` — quality calibration target

---

## First: Read All Existing Docs

Read these files before doing anything else:

1. `agent-docs/.analysis-state.md` — analysis state
2. `agent-docs/system-overview.md` — top-level architecture
3. Every file in `agent-docs/subsystems/` — all deep-dive documents
   (including any recursive sub-module docs)

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

### Step 0: Capture Version Info

Run: `git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown"`

Record the result as `{short_sha}`. Record the current UTC time as
`{YYYY-MM-DD HH:MM UTC}`. Apply this version header to ALL generated
files:

```
> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}
```

For `agent-context.md` only (120-line budget), use the compact
single-line variant:
```
> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}
```

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
> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

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

- **What this repo is** — `system-overview.md` purpose section
- **Architecture map** — all subsystem docs, extract key paths
- **Key patterns** — detected patterns from subsystem deep dives
- **Conventions** — design decisions + observed consistency
- **Do NOT** — edge cases, gotchas, anti-patterns from subsystem docs
- **Key contracts** — contracts and types from subsystem docs
- **For deeper context** — fixed pointers to other agent-docs/ files

### Step 1b: Self-Validate agent-context.md

Before proceeding to patterns.md, verify the file you just generated:

If `~/.claude/codebase-analysis/references/validation-rules.md` exists,
load it and run the Phase 3 self-validation checks. Otherwise:

1. Count lines — must be under 120
2. Scan for `|` characters outside code blocks — no tables allowed
3. Scan for "Confirmed:", "Inference:", "UNCERTAIN:", "NEEDS
   CLARIFICATION:" — none allowed
4. Verify all 7 sections present: What this repo is, Architecture map,
   Key patterns, Conventions, Do NOT, Key contracts, For deeper context
5. Every Architecture map entry has a file path in backticks
6. Every Key patterns entry has numbered steps with file paths
7. Every Key contracts entry has a file:line reference

If any check fails, fix agent-context.md before proceeding.

### Step 1c: Generate `agent-docs/agent-context-nano.md` — INLINED NANO-DIGEST

Generate the nano-digest immediately after `agent-context.md`. The
nano-digest is a strict subset of `agent-context.md` designed to be
pasted directly into the user's `CLAUDE.md` so it lives in the
system prompt. This is the load-bearing wiring fix for cost: by
inlining the nano-digest, the main thread does not need to Read
`agent-docs/` files for common tasks.

If `~/.claude/codebase-analysis/references/nano-context-rules.md`
exists, load and follow it strictly. If
`~/.claude/codebase-analysis/templates/agent-context-nano-template.md`
exists, use its structure.

**Hard rules for agent-context-nano.md:**
- 40 lines maximum (target 25-35)
- ~1.5-2.5K tokens
- **Strict subset of `agent-context.md`** — no new facts
- **Zero references to `agent-docs/`** anywhere in the file
- No tables, no confidence labels
- 5 sections only: What this is, Where things live (5-8 paths), 2
  patterns (most-used), Do NOT (2-3 entries)

**Structure:**

```markdown
# {Repo Name} — Quick Context

> Inlined nano-context for coding agents.
> Generated: {YYYY-MM-DD} | v1 | {short_sha}

## What this is
{1-2 sentences from agent-context.md's "What this repo is", trimmed}

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
- {anti-pattern} — {1-line reason}
{2-3 entries — highest blast radius from agent-context.md's Do NOT}
```

**Content sourcing (do not re-explore):**
- **What this is** — first 1-2 sentences of `agent-context.md`'s "What this repo is"
- **Where things live** — top 5-8 entries of `agent-context.md`'s "Architecture map" by navigation centrality (entrypoints, primary subsystems, registration points)
- **2 patterns** — the 2 patterns from `agent-context.md`'s "Key patterns" with the highest file count in the codebase
- **Do NOT** — the 2-3 entries from `agent-context.md`'s "Do NOT" with the highest blast radius

### Step 1d: Self-Validate agent-context-nano.md

Before proceeding to patterns.md, verify the nano-digest:

1. Count lines — must be ≤ 40
2. Grep for `agent-docs/` — must find zero matches
3. Scan for `|` characters outside code blocks — no tables
4. Scan for "Confirmed:", "Inference:", "UNCERTAIN:", "NEEDS CLARIFICATION:" — none allowed
5. Verify all 5 sections present: What this is, Where things live, 2 pattern sections, Do NOT
6. Every "Where things live" entry has a path in backticks
7. Every pattern has at least 3 numbered steps with file paths
8. Every Do NOT entry has a 1-line reason
9. Cross-check: every fact in the nano-digest also appears in `agent-context.md`

If any check fails, fix agent-context-nano.md before proceeding.

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
> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

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

### Step 2b: Generate `agent-docs/routing-map.md`

Build a machine-readable routing map from the subsystem docs and
patterns.md. This is a YAML-in-markdown lookup table, NOT narrative.

If `~/.claude/codebase-analysis/templates/routing-map-template.md`
exists, use its structure. Otherwise:

The file has two YAML sections inside a code block:
- `subsystem_routing`: one entry per completed subsystem. Pull
  `owns_paths` from subsystem Boundaries, `key_files` from Evidence
  Anchors, `key_tests` from Testing, `common_tasks` from Modification
  Guide.
- `pattern_routing`: one entry per confirmed pattern from patterns.md.
  Pull `template_file` from the example file, `registration` from
  the registration point, `test_template` from the test step.

Do NOT duplicate narrative from agent-context.md. This is a structured
lookup table only.

### Step 3: Generate `agent-docs/agent-brief.md`

Compact architecture map. Under 100 lines. More file-path-heavy than
prose-heavy.

```markdown
# {Repo Name} Agent Brief

> For the minimal version, read `agent-context.md` instead.

## What This Repo Is
{2-4 sentences}

## Classification
- Archetype: {value}
- Primary language: {value}
- Execution model: {value}
- Scale: {value}

## Architecture at a Glance
- Main entrypoints: `{paths}`
- Central subsystems: {names with paths}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most
- {name} — {why} (`subsystems/{name}.md`)

## Flows That Explain the System
- {flow} — {why} (`{doc path}`)

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

> Auto-generated architecture documentation. Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

## What This Repo Is
{1 paragraph}

## Documentation Scope
- Coverage: {scope}
- Evidence quality: {level}
- Generated: {YYYY-MM-DD HH:MM UTC}

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

> Separates code facts from inferred rationale. Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

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

> Project-specific terms. Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

| Term | Meaning | Where Used | Related Docs |
|------|---------|------------|--------------|
```

Prioritize: cross-subsystem terms, domain-specific terms, confusing
or overloaded names.

### Step 7: Generate `agent-docs/uncertainties.md`

Consolidate all `UNCERTAIN:` and `NEEDS CLARIFICATION:` items.

```markdown
# Uncertainties and Open Questions

> Check before making risky assumptions. Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

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

### Step 9: Generate `agent-docs/agent-protocol.md`

Generate copy-paste-ready wiring instructions for all 3 platforms
using the **hybrid wiring strategy**: inlined nano-digest + Explore
enrichment pointer + PreToolUse hook (Claude Code only).

If `~/.claude/codebase-analysis/templates/agent-protocol-template.md`
exists, use its structure. The Claude Code section is two-part:
(1) inline the nano-digest into `CLAUDE.md`, (2) install the
PreToolUse hook from `claude-code/hooks/pensieve-pretooluse.sh` into
`.claude/hooks/` and the settings snippet into `.claude/settings.json`.
Codex and Cursor sections remain one-part (inline nano + Explore
enrichment line) because those platforms don't have an equivalent
PreToolUse hook mechanism as of when this was written.

Inline the actual nano-digest contents into the generated
`agent-protocol.md` (do not reference by path) so the user has a
single self-contained file to copy from. For Claude Code, also
include the hook installation steps with concrete shell commands
(see `claude-code/hooks/README.md` for the canonical install
sequence).

Claude Code section structure:

```markdown
## For Claude Code

Two-part wiring: inlined nano in CLAUDE.md plus a PreToolUse hook.

### Part 1: Inline the nano-digest into CLAUDE.md
---
### Codebase Context

{actual contents of agent-context-nano.md inlined here}

For deeper context, use an Explore subagent on
`agent-docs/agent-context.md`. Never read `agent-docs/` files from
the main thread (triggers long-context fallback).
---

### Part 2: Install the PreToolUse hook
1. mkdir -p .claude/hooks && cp .../pensieve-pretooluse.sh .claude/hooks/
2. chmod +x .claude/hooks/pensieve-pretooluse.sh
3. Merge .../settings-snippet.json into .claude/settings.json
4. Verify with: bash .../smoke-test.sh
5. Manual end-to-end check: trigger a Glob/Grep in Claude Code and
   verify the agent's response references the codebase context
```

Codex and Cursor sections (one-part each):

```markdown
## For {Codex|Cursor}
Add to your `{AGENTS.md|.cursorrules}`:

---
### Codebase Context

{actual contents of agent-context-nano.md inlined here}

For deeper context, use an Explore subagent on
`agent-docs/agent-context.md`. Never read `agent-docs/` files from
the main thread (triggers long-context fallback).
---
```

Critical: do NOT generate any 5-step "before every task" ritual,
"do not skip steps" framing, or "quote the specific pattern"
instruction. The benchmark showed those triggered cost without
quality gains. The hybrid wiring is intentionally minimal.

### Step 9b: Quality Smoke Test

Read `agent-docs/agent-context.md` and attempt to answer these 5
questions using ONLY that file's content. Replace bracketed placeholders
with actual values from the analyzed repository.

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

If any question cannot be answered from agent-context.md alone, the
doc has a gap. Fix agent-context.md and re-check the failing question
before proceeding.

### Step 10: Update Analysis State

Update `agent-docs/.analysis-state.md`:
- Set `phase_completed: 3`
- Record all generated files

### Step 11: Report Completion

Tell the user:

> **Phase 3 of 3 complete. Documentation set is ready.**
>
> Generated:
> - `agent-docs/agent-context.md` — compact agent context (full)
> - `agent-docs/agent-context-nano.md` — **inlined nano-digest for
>   CLAUDE.md (load-bearing wiring)**
> - `agent-docs/patterns.md` — code patterns and conventions
> - `agent-docs/routing-map.md` — task-to-doc routing (machine-readable)
> - `agent-docs/agent-brief.md` — compact architecture
> - `agent-docs/index.md` — navigation hub
> - `agent-docs/decisions.md` — architectural trade-offs
> - `agent-docs/glossary.md` — project terms
> - `agent-docs/uncertainties.md` — unresolved questions
> - `agent-docs/agent-protocol.md` — wiring instructions for agents
> {- `agent-docs/flows/{name}.md` — if generated}
>
> ---
>
> **IMPORTANT: Wire agent-docs into your coding agent (hybrid wiring).**
>
> ### For Claude Code (three steps — TWO-PART WIRING)
>
> 1. **Paste the contents of `agent-docs/agent-context-nano.md`**
>    directly into your `CLAUDE.md`. Create the file if it does not
>    exist. The nano-digest is meant to live in the system prompt, not
>    be referenced by path.
>
> 2. **Add this line below the pasted nano-digest:**
>
>    ```
>    For deeper context, use an Explore subagent on
>    agent-docs/agent-context.md. Never read agent-docs/ files
>    from the main thread (triggers long-context fallback).
>    ```
>
> 3. **Install the PreToolUse hook** for harness-enforced wiring on
>    Glob/Grep tool calls:
>
>    ```bash
>    mkdir -p .claude/hooks
>    cp /path/to/codebase-analysis-skill/claude-code/hooks/pensieve-pretooluse.sh .claude/hooks/
>    chmod +x .claude/hooks/pensieve-pretooluse.sh
>    # Merge claude-code/hooks/settings-snippet.json into .claude/settings.json
>    ```
>
>    Verify the hook produces the expected JSON:
>    ```bash
>    bash /path/to/codebase-analysis-skill/claude-code/hooks/smoke-test.sh
>    ```
>
>    Manual end-to-end check: in your target repo, ask Claude any
>    question that triggers a Glob or Grep, and verify the agent's
>    response references the codebase context reminder.
>
> ### For Codex / Cursor (two steps — ONE-PART WIRING)
>
> 1. **Paste `agent-docs/agent-context-nano.md`** into `AGENTS.md`
>    (Codex) or `.cursorrules` (Cursor)
> 2. **Add this line below it:**
>    ```
>    For deeper context, use an Explore subagent on
>    agent-docs/agent-context.md. Never read agent-docs/ files
>    from the main thread (triggers long-context fallback).
>    ```
>
> Codex and Cursor don't have a PreToolUse-equivalent hook mechanism,
> so the inlined nano + Explore guidance is the best-available wiring
> for those platforms.
>
> ### Why this shape
>
> Benchmark data showed that main-thread reads of `agent-docs/`
> triggered long-context fallback to larger models, inflating cost
> without a quality gain. Inlining the nano-digest puts load-bearing
> context in the system prompt (no Reads, no accumulation) while the
> Explore subagent handles deeper questions in its own context. The
> Claude Code PreToolUse hook adds harness-enforced reinforcement at
> the moment the agent is most likely to violate the rule.
>
> The full copy-paste-ready snippets for all 3 platforms (with the
> nano-digest already inlined) are in `agent-docs/agent-protocol.md`.
> The hook script and settings snippet are in
> `claude-code/hooks/` (in this repo).
>
> ---
>
> **To update:** Re-run any phase. It augments existing `agent-docs/`.
> `agent-context-nano.md` is regenerated entirely on re-run; you will
> need to re-paste it into your agent config. The PreToolUse hook does
> NOT need to be reinstalled on re-runs — it picks up the new nano
> automatically the next time it fires.

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
