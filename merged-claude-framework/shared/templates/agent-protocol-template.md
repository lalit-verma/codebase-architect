# Template: `agent-docs/agent-protocol.md`

This file is generated during Phase 3 (Synthesize). It provides
copy-paste-ready instructions for wiring these docs into any coding
agent's context.

```markdown
# Agent Protocol — How to Use These Docs

> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

This file contains ready-to-use instructions for connecting these
architecture docs to your coding agent. Copy the relevant section
into your agent config file.

## For Claude Code

Add this to your repo's `CLAUDE.md` (or `~/.claude/CLAUDE.md`):

---

### Codebase Context — Read Before Every Task

Before starting any task in this repository, follow these steps in
order. Do not skip steps. Do not start writing code until you have
completed the reading.

**Step 1: Load core context (always)**
Read `agent-docs/agent-context.md` fully. This contains the
architecture map, code patterns, conventions, and anti-patterns.
Internalize the patterns and constraints before proceeding.

**Step 2: Load task-relevant subsystem docs**
Identify which subsystem(s) your task touches based on the architecture
map in agent-context.md. If `agent-docs/routing-map.md` exists, use it
to look up the exact subsystem doc and pattern for your task type. Read
the corresponding subsystem doc(s) from `agent-docs/subsystems/`. If
the subsystem has sub-module docs (a subdirectory under subsystems/),
read those too.

**Step 3: Check patterns before creating new files**
Before creating any new file, read `agent-docs/patterns.md` and follow
the established pattern for that file type. Do not invent new patterns
when an established one exists. In your plan, quote the specific
pattern you are following (e.g. "Per patterns.md, this repo uses...").

**Step 4: Check constraints before architectural changes**
If your task involves changing how subsystems interact, adding new
dependencies, or modifying contracts — read `agent-docs/decisions.md`
first to understand existing trade-offs, and `agent-docs/uncertainties.md`
to know where assumptions are weak.

**Step 5: Confirm your understanding**
Before writing code, state which subsystem(s) you are working in,
which patterns you will follow (quote the specific pattern from
patterns.md), and any constraints from decisions.md that apply.
Then proceed.

---

## For Codex

Add this to your repo's `AGENTS.md` (append if it already exists):

---

### Codebase Context — Read Before Every Task

Before starting any task in this repository, follow these steps in
order. Do not skip steps. Do not start writing code until you have
completed the reading.

Step 1: Read `agent-docs/agent-context.md` fully. This is the
architecture map, patterns, conventions, and anti-patterns. Internalize
before proceeding.

Step 2: Based on the architecture map, identify which subsystem your
task touches. Read the corresponding `agent-docs/subsystems/{name}.md`.
If sub-module docs exist in a subdirectory, read those too.

Step 3: Before creating any new file, read `agent-docs/patterns.md`.
Follow the established pattern for that file type. Do not invent new
patterns. Quote the specific pattern you are following.

Step 4: If changing subsystem interactions, dependencies, or contracts,
read `agent-docs/decisions.md` and `agent-docs/uncertainties.md` first.

Step 5: Before writing code, state which subsystem you are working in,
which patterns apply (quote the specific pattern), and any relevant
constraints. Then proceed.

---

## For Cursor

Create `.cursor/rules/architecture-context.mdc` in your repo:

---

```yaml
---
description: Mandatory architecture context loading before coding tasks
alwaysApply: true
---
```

Before starting any coding task in this repository, follow these steps
in order. Do not skip steps. Do not start writing code until you have
completed the reading.

Step 1: Read `agent-docs/agent-context.md` fully. This is the
architecture map, patterns, conventions, and anti-patterns.

Step 2: Identify which subsystem your task touches. Read the relevant
`agent-docs/subsystems/{name}.md`. If sub-module docs exist in a
subdirectory, read those too.

Step 3: Before creating new files, read `agent-docs/patterns.md`.
Follow established patterns. Quote the specific pattern in your plan.

Step 4: If making structural changes, read `agent-docs/decisions.md`
and `agent-docs/uncertainties.md`.

Step 5: State which subsystem, patterns, and constraints apply before
writing code.

---

## Keeping Docs Current

Re-run the analysis phases periodically (after major refactors or
new subsystem additions). The tool supports re-runs that augment
rather than overwrite existing docs. `agent-context.md` and
`patterns.md` are regenerated entirely on re-run because stale
context is worse than no context.
```
