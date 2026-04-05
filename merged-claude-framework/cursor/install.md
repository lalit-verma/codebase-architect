# Cursor Setup

Cursor does not have a slash command system. Use the paste-able prompts
from the `codex/prompts/` directory.

## Running the Analysis

1. Open Cursor in your target repository.

2. Open Composer (Cmd+I / Ctrl+I).

3. Paste the contents of `codex/prompts/1-discover.md` as your first
   message. Replace `{USER_DESCRIPTION}` with 2-3 lines about what
   your repo does.

4. Follow the on-screen instructions. Each phase tells you which prompt
   to paste next.

5. For Phase 2, paste `codex/prompts/2-deep-dive.md` once per
   subsystem, replacing `{SUBSYSTEM_NAME}` each time.

6. For Phase 3, paste `codex/prompts/3-synthesize.md`.

## Wiring the Output

After Phase 3 completes, add this line to your `.cursorrules` file
(create it at repo root if it doesn't exist):

```
Read agent-docs/agent-context.md at the start of every session for full codebase context.
```

This ensures Cursor loads the generated context at the start of every
session, giving it deep understanding of the codebase.

## What Gets Generated

The tool writes all output to `agent-docs/` in your repo:

- `agent-context.md` — primary context file (compact, under 120 lines)
- `patterns.md` — code patterns and conventions
- `agent-brief.md` — compact architecture map
- `system-overview.md` — top-level architecture
- `subsystems/*.md` — per-subsystem deep dives
- `decisions.md`, `glossary.md`, `uncertainties.md`

## Re-running

Re-run any phase to update existing `agent-docs/`. The tool reads
existing state and augments rather than overwrites.
