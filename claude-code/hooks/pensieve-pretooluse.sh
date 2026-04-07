#!/bin/bash
# PreToolUse hook for Claude Code — Codebase Analysis Framework (v1).
#
# Fires before every Glob and Grep tool call. If the target repo contains
# agent-docs/agent-context-nano.md, the hook injects a short reminder
# into Claude's context via the documented hookSpecificOutput.additionalContext
# mechanism. The reminder tells the agent:
#
#   1. The codebase context (nano-digest) is already loaded via CLAUDE.md.
#   2. For deeper context, use an Explore subagent on agent-docs/agent-context.md.
#   3. Never read agent-docs/ files from the main thread (triggers
#      long-context fallback to a more expensive model).
#
# Why this is necessary: plain stdout from PreToolUse hooks is NOT
# injected into Claude's context — it's only shown in verbose mode
# (Ctrl+O). The documented way to inject context from a PreToolUse hook
# is to output JSON with a hookSpecificOutput object containing
# permissionDecision and additionalContext fields.
#
# Reference: https://code.claude.com/docs/en/hooks
#
# Install: see claude-code/hooks/README.md.
# Verify:  bash claude-code/hooks/smoke-test.sh

if [ -f agent-docs/agent-context-nano.md ]; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":"Codebase context already loaded in CLAUDE.md (nano-digest). For deeper context: Explore subagent on agent-docs/agent-context.md. Never read agent-docs/ from main thread (triggers long-context fallback)."}}
EOF
fi
exit 0
