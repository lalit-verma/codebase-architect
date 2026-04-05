# Codebase Analysis Framework

Evidence-first architecture analysis for any repository. Produces
durable documentation **optimized for coding agent context** — so that
future Cursor, Claude Code, or Codex sessions gain deep understanding
before writing code, resulting in higher quality than a cold start.

Works across applications, libraries, SDKs, frameworks, and monorepos.

## Three Platforms, One Workflow

| Platform | Location | How It Works |
|----------|----------|--------------|
| Claude Code | `claude-code/commands/` | Slash commands (`/project:analyze-*`) |
| Codex | `codex/` | `AGENTS.md` + paste-able prompt files |
| Cursor | `cursor/` | `SKILL.md` + `shared/` references |

All three follow the same 3-phase workflow and produce identical
output in `agent-docs/`.

## The 3-Phase Workflow

| Phase | Command / Prompt | Runs | Output |
|-------|-----------------|------|--------|
| 1. Discover & Map | `analyze-discover` | Once | `agent-docs/system-overview.md`, `agent-docs/.analysis-state.md` |
| 2. Deep Dive | `analyze-deep-dive` | Once per subsystem | `agent-docs/subsystems/{name}.md` (+ sub-module docs if decomposed) |
| 3. Synthesize | `analyze-synthesize` | Once | `agent-docs/index.md`, `agent-docs/agent-brief.md`, `agent-docs/patterns.md`, `agent-docs/decisions.md`, `agent-docs/glossary.md`, `agent-docs/uncertainties.md`, `agent-docs/agent-protocol.md`, optional `agent-docs/flows/` |

Phase 2 runs multiple times — once per subsystem identified in Phase 1.
Large subsystems may be recursively decomposed into sub-modules (max 3
levels deep).

## Output Structure

```
agent-docs/
  .analysis-state.md        # internal state (consumed by phases 2-3)
  index.md                   # navigation hub
  agent-brief.md             # compact context for coding agents ← START HERE
  agent-protocol.md          # instructions for wiring into your agent
  system-overview.md         # top-level architecture
  patterns.md                # code and test conventions to follow
  decisions.md               # key trade-offs and design choices
  glossary.md                # project-specific terms
  uncertainties.md           # unresolved questions
  subsystems/
    {subsystem}.md           # one per subsystem
    {subsystem}/             # sub-module docs (if decomposed)
      {sub-module}.md
  flows/
    {flow}.md                # optional cross-cutting flows
```

`agent-brief.md` is the primary entry point for coding agents.
`index.md` is the primary entry point for humans.

## What Makes This Agent-First

Unlike conventional architecture docs, this framework prioritizes:

- **Modification Guides** — every subsystem doc tells a coding agent
  exactly how to add new code, what invariants to preserve, and what
  files are commonly changed together
- **Pattern Capture** — `patterns.md` and per-subsystem pattern tables
  let agents match existing code conventions
- **Common Change Playbooks** — `agent-brief.md` includes step-by-step
  guides for the most frequent types of changes
- **Agent Protocol** — `agent-protocol.md` provides copy-paste wiring
  for Claude Code, Codex, and Cursor
- **Confidence Labels** — `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:` throughout, so agents know when to ask

---

## Setup: Claude Code

1. Copy the `commands/` folder into your target repo:

   ```bash
   cp -r claude-code/commands/ /path/to/your-repo/.claude/commands/
   ```

   Or for user-level availability across all repos:

   ```bash
   cp -r claude-code/commands/ ~/.claude/commands/
   ```

2. Open Claude Code in your target repo.

3. Run the workflow:

   ```
   /project:analyze-discover This is a Go payment processing service that handles transactions via gRPC
   ```

4. Follow the on-screen instructions. Each phase tells you the next
   command to run.

## Setup: Codex

1. Copy `codex/AGENTS.md` into your target repo root:

   ```bash
   cp codex/AGENTS.md /path/to/your-repo/AGENTS.md
   ```

2. Open Codex in your target repo.

3. Paste the contents of `codex/prompts/1-discover.md` as your first
   task. Replace `{USER_DESCRIPTION}` with your 2-3 line repo
   description.

4. Follow the instructions at the end of each phase for the next
   prompt to paste.

## Setup: Cursor

1. Install the skill by copying `cursor/SKILL.md` and `shared/` to
   your Cursor skills location.

2. Open Cursor in your target repo.

3. Ask the agent to analyze the codebase — the skill triggers on
   phrases like "analyze this codebase", "help me understand this
   repo", "document this architecture", etc.

## After Generation: Wire Docs Into Your Agent

Once all 3 phases are complete, your `agent-docs/` folder is ready.
The final step is to tell your coding agent to **read these docs before
every coding task**. Phase 3 generates `agent-docs/agent-protocol.md`
with copy-paste-ready snippets, but here is the quick version:

### Claude Code

Add this to your repo's `CLAUDE.md` (create it if it doesn't exist):

```markdown
## Architecture Context — MANDATORY

This repository has architecture documentation in `agent-docs/`.
You MUST follow these steps **sequentially, one at a time** before
writing or proposing any code. Do NOT skip steps. Do NOT start coding
until you have completed all applicable steps.

**Step 1 — Orient.** Read `agent-docs/agent-brief.md` in full. After
reading, write a 2-3 sentence summary of the system architecture to
confirm you have absorbed it.

**Step 2 — Locate.** Identify which subsystem(s) your task touches.
Read each relevant `agent-docs/subsystems/{name}.md` in full — pay
close attention to the "Modification Guide" section. State which
subsystem(s) you read and what invariants apply.

**Step 3 — Match conventions.** Read `agent-docs/patterns.md`. In your
plan or PR description, **quote the specific pattern** you are
following (e.g. "Per patterns.md §Error Handling, this repo uses
sentinel errors, not panics").

**Step 4 — Check constraints.** If your task involves structural
changes, read `agent-docs/decisions.md` to understand existing
trade-offs. If working near uncertain areas, read
`agent-docs/uncertainties.md`.

**Step 5 — Plan, then code.** Only after completing steps 1-4, propose
your implementation plan. Reference specific docs where relevant.

If you are unsure whether a step applies, complete it anyway — it is
cheaper to read a short file than to debug a convention violation.
```

### Codex

Add this to your repo's `AGENTS.md` (append if it already exists):

```markdown
## Architecture Context — MANDATORY

This repository has architecture documentation in `agent-docs/`.
Follow these steps **in order** before writing any code. Complete each
step fully before moving to the next. Do not skip steps.

**Step 1 — Orient.** Read `agent-docs/agent-brief.md` in full.
Summarize the system architecture in 2-3 sentences before proceeding.

**Step 2 — Locate.** Identify the subsystem(s) relevant to your task.
Read the corresponding `agent-docs/subsystems/{name}.md` in full.
Note the invariants and modification guide for each.

**Step 3 — Match conventions.** Read `agent-docs/patterns.md`. When
proposing code, cite the specific convention you are following
(e.g. "Following §Naming Conventions: all service methods use
verbNoun format").

**Step 4 — Check constraints.** Read `agent-docs/decisions.md` before
proposing structural changes. Read `agent-docs/uncertainties.md` if
your change area has open questions.

**Step 5 — Plan, then code.** Propose your approach first. Reference
the docs. Only write code after confirming alignment.

When in doubt, read the doc — it is faster than guessing wrong.
```

### Cursor

Create `.cursor/rules/architecture-context.mdc` in your repo:

```yaml
---
description: Mandatory architecture context loading before coding tasks
alwaysApply: true
---
```

```markdown
# Architecture Context — MANDATORY

This repository has architecture documentation in `agent-docs/`.
You MUST follow these steps **sequentially** before writing any code.
Do NOT skip steps. Do NOT start coding until all applicable steps are
complete.

**Step 1 — Orient.** Read `agent-docs/agent-brief.md` in full. Write
a 2-3 sentence summary of the system architecture to confirm you
absorbed it.

**Step 2 — Locate.** Identify which subsystem(s) your task touches.
Read each relevant `agent-docs/subsystems/{name}.md` in full. Pay
close attention to the Modification Guide section. State which
subsystem(s) you read and what invariants apply to your change.

**Step 3 — Match conventions.** Read `agent-docs/patterns.md`. In
your plan, **quote the specific pattern** you are following.

**Step 4 — Check constraints.** If making structural changes, read
`agent-docs/decisions.md`. If near uncertain areas, read
`agent-docs/uncertainties.md`.

**Step 5 — Plan, then code.** Propose your plan with doc references
before writing code.

When in doubt, read the doc — it is faster than guessing wrong.
```

---

## Shared References (Optional Quality Boosters)

The `shared/` directory contains references and templates that the
Cursor skill uses directly and that the self-contained Claude Code /
Codex prompts inline in condensed form:

- `shared/references/ecosystem-playbook.md` — per-language exploration
  commands and architectural signals
- `shared/references/scale-and-scope.md` — reading depth rules and
  recursive decomposition triggers
- `shared/references/subsystem-mapping-rubric.md` — what counts as a
  subsystem, when to split or merge
- `shared/references/checkpoint-example.md` — concrete example of a
  quality checkpoint
- `shared/templates/` — document templates for all output files

---

## Design Principles

- **Agent-first.** Documentation is structured for coding agent context, not just human readability.
- **Read-only.** Never modifies source code.
- **Chat-first.** Presents findings for confirmation before writing files.
- **Evidence-based.** Cites file paths. Uses confidence labels throughout.
- **Pattern-aware.** Captures code and test conventions agents can follow.
- **Modification-ready.** Every subsystem doc includes a guide for common changes.
- **Durable.** Output is structured for long-term reuse, not single-session consumption.
- **Augmentable.** Supports re-runs that update rather than replace existing docs.
