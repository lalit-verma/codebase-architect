# Template: `agent-docs/agent-protocol.md`

This file is generated during Phase 3 (Synthesize). It provides
copy-paste-ready instructions for wiring the analysis into any coding
agent's context using the **hybrid wiring strategy**:

1. **Inline a nano-digest** into the agent's config file (`CLAUDE.md`,
   `AGENTS.md`, or `.cursorrules`) so the most-used context lives in
   the system prompt — no Read calls, no context accumulation, no
   long-context fallback.
2. **Tell Explore subagents** where the deeper docs live so they can
   enrich research without polluting main-thread context.

This split is the result of benchmark findings: main-thread Reads of
the deeper `agent-docs/` files inflated cost via long-context fallback,
while pushing reads entirely into subagents lost the pattern fidelity
that the writer needed. Inlining a nano-digest gives the writer enough
context for common tasks without triggering either failure mode.

```markdown
# Agent Protocol — How to Use These Docs

> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

This file contains ready-to-use instructions for connecting these
architecture docs to your coding agent. The wiring has two parts:
an inlined nano-digest, and a separate Explore-enrichment instruction.

## For Claude Code

Claude Code uses **two-part wiring**: an inlined nano-digest in
`CLAUDE.md` (always-loaded layer) plus a `PreToolUse` hook in
`.claude/settings.json` (harness-enforced layer that fires before
every Glob/Grep). Both work together — the inline nano carries the
load-bearing patterns into the system prompt, and the hook reminds
the agent at search time not to read `agent-docs/` from the main
thread.

### Part 1: Inline the nano-digest into `CLAUDE.md`

Add this to your repo's `CLAUDE.md` (create the file if it does not
exist):

---

### Codebase Context

{PASTE THE CONTENTS OF `agent-docs/agent-context-nano.md` HERE — the
nano-digest is meant to live directly in this file, not be referenced
by path.}

For deeper context, use an Explore subagent on
`agent-docs/agent-context.md`. Never read `agent-docs/` files from
the main thread (triggers long-context fallback).

---

### Part 2: Install the PreToolUse hook

The hook fires before every Glob or Grep call and injects a reminder
into Claude's context if `agent-docs/agent-context-nano.md` exists.
This is mechanically stronger than relying on `CLAUDE.md` alone
because the harness fires it just-in-time, not at session start.

1. Copy the hook script into your target repo:

   ```bash
   mkdir -p .claude/hooks
   cp /path/to/codebase-analysis-skill/claude-code/hooks/pensieve-pretooluse.sh .claude/hooks/
   chmod +x .claude/hooks/pensieve-pretooluse.sh
   ```

2. Merge the settings snippet into `.claude/settings.json`:

   ```bash
   # If .claude/settings.json doesn't exist:
   cp /path/to/codebase-analysis-skill/claude-code/hooks/settings-snippet.json .claude/settings.json

   # If it does exist, merge the hooks.PreToolUse array entry from
   # settings-snippet.json into the existing file.
   ```

3. Verify the hook script outputs the expected JSON:

   ```bash
   bash /path/to/codebase-analysis-skill/claude-code/hooks/smoke-test.sh
   ```

4. **Manual end-to-end verification (do this once):** open Claude Code
   in your target repo, ask any question that triggers a Glob or Grep,
   and check the agent's response for awareness of the codebase context
   reminder. If absent, see `claude-code/hooks/README.md` for
   troubleshooting.

See `claude-code/hooks/README.md` for the full mechanism explanation.

---

## For Codex

Add this to your repo's `AGENTS.md` (append if it already exists).

---

### Codebase Context

{PASTE THE CONTENTS OF `agent-docs/agent-context-nano.md` HERE.}

If you spawn a research subagent for codebase exploration, point it
at `agent-docs/agent-context.md` as a starting heuristic. Deeper docs:
`agent-docs/subsystems/{name}.md`, `agent-docs/patterns.md`,
`agent-docs/decisions.md`. Do not read these from the main thread.

---

## For Cursor

Create `.cursor/rules/architecture-context.mdc` in your repo.

---

```yaml
---
description: Inlined codebase nano-context plus subagent enrichment
alwaysApply: true
---
```

{PASTE THE CONTENTS OF `agent-docs/agent-context-nano.md` HERE.}

If you spawn a research subagent for codebase exploration, point it
at `agent-docs/agent-context.md` as a starting heuristic. Deeper docs:
`agent-docs/subsystems/{name}.md`, `agent-docs/patterns.md`,
`agent-docs/decisions.md`. Do not read these from the main thread.

---

## Keeping Docs Current

Re-run the analysis phases periodically (after major refactors or
new subsystem additions). The tool supports re-runs that augment
rather than overwrite existing docs. `agent-context.md` and
`patterns.md` are regenerated entirely on re-run because stale
context is worse than no context.
```
