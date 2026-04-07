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

### Codebase Context

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.

---

## For Codex

Add this to your repo's `AGENTS.md` (append if it already exists):

---

### Codebase Context

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.

---

## For Cursor

Create `.cursor/rules/architecture-context.mdc` in your repo:

---

```yaml
---
description: Load architecture context for non-trivial coding tasks
alwaysApply: true
---
```

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.

---

## Keeping Docs Current

Re-run the analysis phases periodically (after major refactors or
new subsystem additions). The tool supports re-runs that augment
rather than overwrite existing docs. `agent-context.md` and
`patterns.md` are regenerated entirely on re-run because stale
context is worse than no context.
```
