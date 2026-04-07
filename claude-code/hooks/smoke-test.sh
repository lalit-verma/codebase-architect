#!/bin/bash
# Smoke test for the PreToolUse hook.
#
# Verifies that pensieve-pretooluse.sh:
#   1. Outputs nothing when agent-docs/agent-context-nano.md is absent
#   2. Outputs JSON when the file is present
#   3. The JSON has the expected hookSpecificOutput structure
#   4. The additionalContext field contains the load-bearing reminder
#
# Run from the repo root or anywhere:
#   bash claude-code/hooks/smoke-test.sh
#
# Exits 0 if all tests pass, 1 if any fail.
#
# This is a UNIT smoke test of the script's output. It does NOT verify
# that Claude Code's harness actually injects the additionalContext into
# the agent's working context — that requires manual verification by
# running a real Claude Code session in a target repo. See the "Manual
# verification" section at the end of this script's output.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SCRIPT="$SCRIPT_DIR/pensieve-pretooluse.sh"

if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "FAIL: hook script not found at $HOOK_SCRIPT"
  exit 1
fi

PASS=0
FAIL=0
TEST_DIR=$(mktemp -d)
ORIG_DIR=$(pwd)
cleanup() { cd "$ORIG_DIR"; rm -rf "$TEST_DIR"; }
trap cleanup EXIT

run_test() {
  local name="$1"
  local result="$2"
  local detail="${3:-}"
  if [ "$result" = "pass" ]; then
    echo "  PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $name${detail:+ — $detail}"
    FAIL=$((FAIL + 1))
  fi
}

echo "PreToolUse hook smoke test"
echo "=========================="
echo "Hook script: $HOOK_SCRIPT"
echo "Test dir:    $TEST_DIR"
echo

# ----------------------------------------------------------------------
# Test 1: hook is silent when agent-docs/agent-context-nano.md is absent
# ----------------------------------------------------------------------
echo "Test 1: hook silent when agent-docs/agent-context-nano.md absent"
cd "$TEST_DIR"
OUTPUT=$(bash "$HOOK_SCRIPT" 2>&1)
EXIT_CODE=$?

if [ -z "$OUTPUT" ]; then
  run_test "produces no stdout" "pass"
else
  run_test "produces no stdout" "fail" "got: $OUTPUT"
fi

if [ "$EXIT_CODE" = "0" ]; then
  run_test "exits 0" "pass"
else
  run_test "exits 0" "fail" "got exit=$EXIT_CODE"
fi
echo

# ----------------------------------------------------------------------
# Test 2: hook outputs JSON when nano file is present
# ----------------------------------------------------------------------
echo "Test 2: hook outputs JSON when agent-docs/agent-context-nano.md present"
mkdir -p "$TEST_DIR/agent-docs"
cat > "$TEST_DIR/agent-docs/agent-context-nano.md" <<'NANO'
# Test Repo — Quick Context

> Inlined nano-context for coding agents.

## What this is
A test fixture for the smoke test.
NANO
cd "$TEST_DIR"
OUTPUT=$(bash "$HOOK_SCRIPT" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" = "0" ]; then
  run_test "exits 0" "pass"
else
  run_test "exits 0" "fail" "got exit=$EXIT_CODE"
fi

if [ -n "$OUTPUT" ]; then
  run_test "produces output" "pass"
else
  run_test "produces output" "fail" "got empty"
fi

# Validate JSON shape via grep (works without jq)
if echo "$OUTPUT" | grep -q '"hookSpecificOutput"'; then
  run_test "contains hookSpecificOutput field" "pass"
else
  run_test "contains hookSpecificOutput field" "fail"
fi

if echo "$OUTPUT" | grep -q '"hookEventName":"PreToolUse"'; then
  run_test "hookEventName is PreToolUse" "pass"
else
  run_test "hookEventName is PreToolUse" "fail"
fi

if echo "$OUTPUT" | grep -q '"permissionDecision":"allow"'; then
  run_test "permissionDecision is allow" "pass"
else
  run_test "permissionDecision is allow" "fail"
fi

if echo "$OUTPUT" | grep -q '"additionalContext"'; then
  run_test "additionalContext field present" "pass"
else
  run_test "additionalContext field present" "fail"
fi

# Stricter validation if jq is available
if command -v jq >/dev/null 2>&1; then
  if echo "$OUTPUT" | jq -e '.hookSpecificOutput.additionalContext' >/dev/null 2>&1; then
    run_test "JSON parses with jq, additionalContext extractable" "pass"
  else
    run_test "JSON parses with jq, additionalContext extractable" "fail"
  fi

  CONTEXT=$(echo "$OUTPUT" | jq -r '.hookSpecificOutput.additionalContext' 2>/dev/null || echo "")

  if echo "$CONTEXT" | grep -q "nano-digest"; then
    run_test "additionalContext mentions nano-digest" "pass"
  else
    run_test "additionalContext mentions nano-digest" "fail"
  fi

  if echo "$CONTEXT" | grep -q "Explore subagent"; then
    run_test "additionalContext mentions Explore subagent" "pass"
  else
    run_test "additionalContext mentions Explore subagent" "fail"
  fi

  if echo "$CONTEXT" | grep -q "Never read agent-docs/ from main thread"; then
    run_test "additionalContext contains the prohibition" "pass"
  else
    run_test "additionalContext contains the prohibition" "fail"
  fi

  if echo "$CONTEXT" | grep -q "long-context fallback"; then
    run_test "additionalContext contains the cost rationale" "pass"
  else
    run_test "additionalContext contains the cost rationale" "fail"
  fi
else
  echo "  SKIP: jq not installed, skipping strict JSON parsing checks"
fi
echo

# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------
echo "=========================="
echo "Results: $PASS passed, $FAIL failed"
echo

if [ "$FAIL" = "0" ]; then
  echo "All unit-level smoke tests passed."
  echo
  echo "NEXT: Manual agent-side verification (cannot be automated)"
  echo "==========================================================="
  echo
  echo "The smoke test above verifies the hook script outputs the"
  echo "correct JSON when invoked. It does NOT verify that Claude"
  echo "Code's harness actually injects the additionalContext into"
  echo "the live agent's working context."
  echo
  echo "To verify end-to-end:"
  echo
  echo "  1. Pick a test repo (or create a temp one):"
  echo "       mkdir /tmp/hook-verify && cd /tmp/hook-verify"
  echo "       git init && touch README.md"
  echo
  echo "  2. Install the hook into the test repo:"
  echo "       mkdir -p .claude/hooks"
  echo "       cp $HOOK_SCRIPT .claude/hooks/"
  echo "       chmod +x .claude/hooks/pensieve-pretooluse.sh"
  echo "       cp $SCRIPT_DIR/settings-snippet.json .claude/settings.json"
  echo
  echo "  3. Create a fake agent-context-nano.md so the hook fires:"
  echo "       mkdir -p agent-docs"
  echo "       echo '# Test Quick Context' > agent-docs/agent-context-nano.md"
  echo
  echo "  4. Open Claude Code in this directory and ask any question"
  echo "     that triggers a Glob or Grep, e.g.:"
  echo "       'find all markdown files in this repo'"
  echo
  echo "  5. The agent's response should reference the codebase context"
  echo "     reminder (mention the nano-digest, Explore, or the"
  echo "     prohibition on main-thread reads of agent-docs/)."
  echo
  echo "If the agent does NOT reference the reminder after a Glob/Grep,"
  echo "the hook is firing but the additionalContext is not reaching the"
  echo "agent. Possible causes:"
  echo "  - Claude Code version doesn't honor hookSpecificOutput.additionalContext"
  echo "  - settings.json isn't being picked up (check it's in the right path)"
  echo "  - Hook script isn't executable (chmod +x)"
  exit 0
else
  echo "Some tests failed. Hook is not wired correctly. Investigate"
  echo "before installing into a target repo or running benchmarks."
  exit 1
fi
