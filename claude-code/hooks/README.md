# PreToolUse Hook for Claude Code

This directory contains the PreToolUse hook installed into target repos
for **harness-enforced wiring**. It complements the v1 hybrid wiring
(inlined nano-digest in `CLAUDE.md`) by reminding Claude — at the
moment it's about to search the codebase — that the context is already
loaded and main-thread reads of `agent-docs/` should be avoided.

## Files in this directory

| File | Purpose |
|---|---|
| `pensieve-pretooluse.sh` | The hook script. Outputs JSON via the documented `hookSpecificOutput.additionalContext` mechanism when `agent-docs/agent-context-nano.md` exists. Silent (exits 0 with no output) otherwise. |
| `settings-snippet.json` | The JSON snippet to merge into the target repo's `.claude/settings.json` to register the hook on the `Glob\|Grep` matcher. |
| `smoke-test.sh` | Unit smoke test that verifies the hook script produces the expected JSON in both file-present and file-absent cases. Includes a manual verification checklist for end-to-end validation. |
| `README.md` | This file. |

## What the hook does

When the Claude Code agent calls a `Glob` or `Grep` tool, the harness
runs `pensieve-pretooluse.sh` before the tool executes. The script:

1. Checks if `agent-docs/agent-context-nano.md` exists in the current
   working directory.
2. If yes, outputs a JSON object on stdout containing:
   - `permissionDecision: "allow"` — allows the tool call to proceed
   - `additionalContext: "<reminder text>"` — Claude Code's harness
     injects this into the agent's context **before** the tool result
     is returned.
3. If no, exits 0 silently. The tool call proceeds with the user's
   normal permission flow, and no reminder is injected.

The reminder injected when the file is present:

> "Codebase context already loaded in CLAUDE.md (nano-digest). For
> deeper context: Explore subagent on agent-docs/agent-context.md.
> Never read agent-docs/ from main thread (triggers long-context
> fallback)."

## Why this is mechanically stronger than CLAUDE.md instructions alone

CLAUDE.md is loaded once at session start. As the conversation grows,
the agent may forget or deprioritize its CLAUDE.md guidance. The
PreToolUse hook fires at the **exact moment** the agent is about to
search the codebase — when the reminder is most relevant — and it's
injected by the harness, not the agent's compliance layer. The agent
cannot "have forgotten" the guidance because it just received it on
the same turn.

The hybrid wiring works in two layers:

| Layer | Mechanism | When it fires | Strength |
|---|---|---|---|
| **Inlined nano-digest in CLAUDE.md** | System prompt content | Every turn (loaded with system prompt) | Carries the full pattern recipes verbatim. Always present. |
| **PreToolUse hook reminder** | Harness-enforced JSON injection | Before every Glob/Grep tool call | Just-in-time. Reinforces the constraint at the moment it's most likely to be violated. |

Both layers work together. The inlined nano carries the load-bearing
content into the system prompt; the hook fires at search time and
reminds the agent of the constraint. Neither alone is sufficient — v1
benchmarks showed inlined-only wiring still hit cost regressions
because the agent would eventually decide to read `agent-docs/` files
directly in long sessions.

## Why JSON output, not plain echo

For `PreToolUse` hooks specifically, plain stdout from a bash command
is **not** injected into the agent's context. From the
[Claude Code Hooks documentation](https://code.claude.com/docs/en/hooks):

> "Exit 0 means success. Claude Code parses stdout for JSON output
> fields. JSON output is only processed on exit 0. For most events,
> stdout is only shown in verbose mode (Ctrl+O). The exceptions are
> UserPromptSubmit and SessionStart, where stdout is added as context
> that Claude can see and act on."

`PreToolUse` is **not** in the exceptions list. So a hook that simply
echoes a reminder string would only show in verbose mode (`Ctrl+O`)
and never reach the agent. The documented mechanism is to output JSON
with a `hookSpecificOutput.additionalContext` field, which the harness
extracts and injects into the agent's context before the tool call
proceeds.

This is the source of an earlier design error: a previous draft of
this hook used plain `echo`, copied from a similar tool that may also
not be injecting context as intended. The current script uses the
documented JSON output format.

## Installation

### Step 1: Smoke test from this repo first

Always run the unit smoke test before installing into a target repo:

```bash
bash claude-code/hooks/smoke-test.sh
```

The smoke test verifies the script outputs the expected JSON. It
prints next-step instructions for manual end-to-end verification on
success.

### Step 2: Copy the hook into the target repo

```bash
cd /path/to/your-target-repo
mkdir -p .claude/hooks
cp /path/to/codebase-analysis-skill/claude-code/hooks/pensieve-pretooluse.sh .claude/hooks/
chmod +x .claude/hooks/pensieve-pretooluse.sh
```

### Step 3: Merge the settings snippet

If `.claude/settings.json` doesn't exist in the target repo:

```bash
cp /path/to/codebase-analysis-skill/claude-code/hooks/settings-snippet.json .claude/settings.json
```

If it does exist, merge the `hooks.PreToolUse` array entry from
`settings-snippet.json` into the existing file. Be careful not to
overwrite other hooks.

### Step 4: Run Phase 3 of the analysis framework

The hook only fires if `agent-docs/agent-context-nano.md` exists. Run
`/user:analyze-synthesize` (or the equivalent) to generate it.

### Step 5: Manual end-to-end verification

The unit smoke test verifies the hook script outputs valid JSON. It
does **not** verify that Claude Code's harness actually injects the
`additionalContext` into the live agent's context. To verify this
end-to-end:

1. Open Claude Code in your target repo
2. Issue a question that triggers a Glob or Grep call (e.g., "find all
   markdown files in this repo")
3. Check the agent's response for awareness of the reminder. The agent
   should reference the nano-digest, the Explore subagent, or the
   prohibition on main-thread reads of `agent-docs/`.

If the agent does **not** reference the reminder, the hook is
producing JSON but the harness isn't honoring the
`additionalContext` field in your Claude Code version. Open an issue
or fall back to inline-nano-only wiring.

## Limitations

- **Claude Code only.** Codex and Cursor don't have an equivalent
  PreToolUse hook mechanism (as of when this hook was written). For
  those platforms, the v1 hybrid wiring (inlined nano-digest in
  `AGENTS.md` / `.cursorrules` plus the Explore-enrichment line) is
  the best-available wiring.
- **Fires every Glob/Grep, not once per session.** Claude Code's hook
  system doesn't expose per-session deduplication. The reminder is
  short (~32 tokens of additionalContext) so the cost across many
  fires remains small relative to the long-context-fallback cost it
  prevents. At 50 fires per session, the reminder accounts for
  ~1,600 tokens — well under 1% of Haiku's 200K context window.
- **Requires the user's working directory to be the repo root** when
  Claude Code starts. The hook checks for `agent-docs/agent-context-nano.md`
  using a relative path. If Claude Code is started from a subdirectory,
  the hook will not find the file and will be silent.
- **The hook output is bounded to what Claude Code's hook system
  supports.** Mechanism is documented at
  [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks).
