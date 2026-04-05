# Template: `agent-docs/agent-protocol.md`

This file is generated during Phase 3 (Synthesize). It provides
copy-paste-ready instructions for wiring these docs into any coding
agent's context.

```markdown
# Agent Protocol — How to Use These Docs

This file contains ready-to-use instructions for connecting these
architecture docs to your coding agent.

## For Claude Code

Add this to your repo's `CLAUDE.md` (or `~/.claude/CLAUDE.md`):

---

### Architecture Context

Before starting any coding task in this repository:

1. Read `agent-docs/agent-brief.md` for a compact architecture map.
2. Identify which subsystem(s) your task involves.
3. Read the relevant `agent-docs/subsystems/{name}.md`.
4. Read `agent-docs/patterns.md` to match existing code conventions.
5. If making structural changes, read `agent-docs/decisions.md`.
6. If working near uncertain areas, check `agent-docs/uncertainties.md`.

These docs are auto-generated architecture analysis. Sections marked
`UNCERTAIN:` or `NEEDS CLARIFICATION:` should be verified before
relying on them.

---

## For Codex

Add this to your repo's `AGENTS.md`:

---

### Architecture Context

This repository has auto-generated architecture docs in `agent-docs/`.
Before making changes:

1. Read `agent-docs/agent-brief.md` first.
2. Then read the subsystem doc for the area you are changing.
3. Follow the patterns in `agent-docs/patterns.md`.
4. Check `agent-docs/decisions.md` before proposing structural changes.
5. Check `agent-docs/uncertainties.md` near your change area.

---

## For Cursor

Add this as a Cursor rule (`.cursor/rules/architecture-context.mdc`):

---

```yaml
---
description: Load architecture docs before coding tasks
alwaysApply: true
---
```

Before starting coding tasks in this repository, read
`agent-docs/agent-brief.md` for architecture context. For the specific
area you are working in, read the relevant subsystem doc in
`agent-docs/subsystems/`. Follow conventions documented in
`agent-docs/patterns.md`. Check `agent-docs/uncertainties.md` for assumptions
near your change area.

---

## Keeping Docs Current

Re-run the analysis phases periodically (after major refactors or
new subsystem additions). The tool supports re-runs that augment
rather than overwrite existing docs.
```
