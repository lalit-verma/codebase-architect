"""PreToolUse hook installer/uninstaller (milestones A3, A4).

Installs the Code Pensieve PreToolUse hook into a target repo's
`.claude/` directory. The hook fires before every Glob/Grep tool call
and injects a reminder into Claude's context via the documented
`hookSpecificOutput.additionalContext` JSON mechanism.

Two artifacts are written:
  1. `.claude/hooks/pensieve-pretooluse.sh` — the hook script
  2. `.claude/settings.json` — the PreToolUse hook registration
     (merged into existing settings if present)

The hook content is embedded in this module, not read from external
files, so `pensieve hook install` works from any install location.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedded hook content (proven in claude-code/hooks/)
# ---------------------------------------------------------------------------

HOOK_SCRIPT = '''\
#!/bin/bash
# Code Pensieve PreToolUse hook for Claude Code.
# Fires before every Glob/Grep. Provides path-aware hints from
# route-index.json and logs telemetry to hook-telemetry.jsonl.
# Reference: https://code.claude.com/docs/en/hooks

# Exit early if no agent-docs
if [ ! -f agent-docs/agent-context-nano.md ]; then
  exit 0
fi

# Read stdin (tool input JSON from Claude Code)
INPUT=$(cat /dev/stdin 2>/dev/null || echo "{}")
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); ti=d.get('tool_input',{}); print(ti.get('pattern','') or ti.get('path','') or ti.get('command',''))" 2>/dev/null || echo "")

# Default hint
HINT="Codebase context in CLAUDE.md (nano-digest). For deeper context: Explore subagent on agent-docs/agent-context.md. Never read agent-docs/ from main thread."
HINT_TYPE="fallback"
TARGET_DOC="agent-docs/agent-context.md"

# Try path-aware routing from route-index.json (v2 schema)
ARTIFACT_KIND="fallback"
TARGET_SUBSYSTEM=""
ROUTE_MATCH_TYPE="fallback"

if [ -f agent-docs/route-index.json ] && command -v python3 &>/dev/null; then
  ROUTE_RESULT=$(python3 -c "
import json, sys
try:
    with open('agent-docs/route-index.json') as f:
        idx = json.load(f)
    query = sys.argv[1] if len(sys.argv) > 1 else ''
    v = idx.get('version', 1)
    # v2 schema: subsystem_routes with owns_paths
    if v >= 2:
        for route in idx.get('subsystem_routes', []):
            for p in route.get('owns_paths', []):
                p = p.rstrip('/')
                if query.startswith(p):
                    hint = route.get('role', route['subsystem'])
                    print(json.dumps({
                        'hint': hint,
                        'doc': route.get('doc_path', ''),
                        'subsystem': route['subsystem'],
                        'match_type': 'directory_prefix',
                        'artifact_kind': 'subsystem_doc',
                    }))
                    sys.exit(0)
    # v1 fallback: routes[] with pattern
    else:
        for route in idx.get('routes', []):
            if route.get('match_type') == 'directory_prefix' and query.startswith(route.get('pattern', '')):
                print(json.dumps({
                    'hint': route.get('hint', ''),
                    'doc': route.get('doc_path', ''),
                    'subsystem': route.get('subsystem', ''),
                    'match_type': 'directory_prefix',
                    'artifact_kind': 'subsystem_doc',
                }))
                sys.exit(0)
    # No match — fallback
    fb = idx.get('fallback_hint', '') if v >= 2 else idx.get('fallback_hint', '')
    print(json.dumps({'hint': fb, 'doc': 'agent-docs/agent-context.md', 'subsystem': '', 'match_type': 'fallback', 'artifact_kind': 'fallback'}))
except Exception:
    print(json.dumps({'hint': '', 'doc': '', 'subsystem': '', 'match_type': 'fallback', 'artifact_kind': 'fallback'}))
" "$TOOL_INPUT" 2>/dev/null)

  if [ -n "$ROUTE_RESULT" ]; then
    ROUTED_HINT=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('hint',''))" 2>/dev/null || echo "")
    ROUTED_DOC=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('doc',''))" 2>/dev/null || echo "")
    TARGET_SUBSYSTEM=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('subsystem',''))" 2>/dev/null || echo "")
    ROUTE_MATCH_TYPE=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('match_type','fallback'))" 2>/dev/null || echo "fallback")
    ARTIFACT_KIND=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('artifact_kind','fallback'))" 2>/dev/null || echo "fallback")
    if [ -n "$ROUTED_HINT" ]; then
      HINT="$ROUTED_HINT. See $ROUTED_DOC for details."
      HINT_TYPE="routed"
      TARGET_DOC="$ROUTED_DOC"
    fi
  fi
fi

# Log telemetry event (append-only JSONL, expanded schema Bx5a)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
python3 -c "
import json, sys
event = {
    'timestamp': sys.argv[1],
    'event': 'hint_shown',
    'tool_name': sys.argv[2],
    'query': sys.argv[3][:200],
    'hint_type': sys.argv[4],
    'route_match_type': sys.argv[5],
    'artifact_kind': sys.argv[6],
    'target_doc': sys.argv[7],
    'target_subsystem': sys.argv[8],
    'session_id': sys.argv[9],
}
with open('agent-docs/hook-telemetry.jsonl', 'a') as f:
    f.write(json.dumps(event) + '\\n')
" "$TIMESTAMP" "$TOOL_NAME" "$TOOL_INPUT" "$HINT_TYPE" "$ROUTE_MATCH_TYPE" "$ARTIFACT_KIND" "$TARGET_DOC" "$TARGET_SUBSYSTEM" "$SESSION_ID" 2>/dev/null

# Output the hook response
cat <<HOOKEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":"$HINT"}}
HOOKEOF
exit 0
'''

HOOK_ENTRY = {
    "matcher": "Glob|Grep",
    "hooks": [
        {
            "type": "command",
            "command": "bash .claude/hooks/pensieve-pretooluse.sh",
        }
    ],
}

_HOOK_SCRIPT_NAME = "pensieve-pretooluse.sh"
# The exact command string we write — used for identity matching.
# Must match HOOK_ENTRY["hooks"][0]["command"] exactly.
_OUR_COMMAND = "bash .claude/hooks/pensieve-pretooluse.sh"


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


def install_hook(repo_root: Path) -> dict[str, str]:
    """Install the PreToolUse hook into a repo's .claude/ directory.

    Creates `.claude/hooks/pensieve-pretooluse.sh` and merges the hook
    registration into `.claude/settings.json`.

    Idempotent: re-running does not create duplicate entries.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A dict describing what was done:
          {"script": "created" | "already_exists",
           "settings": "created" | "merged" | "already_registered"}
    """
    claude_dir = repo_root / ".claude"
    hooks_dir = claude_dir / "hooks"
    script_path = hooks_dir / _HOOK_SCRIPT_NAME
    settings_path = claude_dir / "settings.json"

    result: dict[str, str] = {}

    # --- Write hook script ---
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if script_path.exists():
        result["script"] = "already_exists"
    else:
        script_path.write_text(HOOK_SCRIPT)
        # Make executable
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        result["script"] = "created"

    # --- Merge settings entry ---
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    # Check if already registered (idempotent) — exact command match,
    # not substring. An unrelated hook with "pensieve" in its args must
    # NOT be treated as ours.
    already = any(
        isinstance(h, dict)
        and any(
            isinstance(hh, dict) and hh.get("command") == _OUR_COMMAND
            for hh in h.get("hooks", [])
        )
        for h in pre_tool
    )

    if already:
        result["settings"] = "already_registered"
    else:
        # Track whether settings.json existed before we write
        is_new_settings = not settings_path.exists()
        pre_tool.append(HOOK_ENTRY)
        settings_path.write_text(
            json.dumps(settings, indent=2) + "\n",
            encoding="utf-8",
        )
        result["settings"] = "created" if is_new_settings else "merged"

    return result


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------


def uninstall_hook(repo_root: Path) -> dict[str, str]:
    """Remove the PreToolUse hook from a repo's .claude/ directory.

    Removes the hook script and the settings entry. Does not remove
    `.claude/` itself or other hooks/settings.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A dict describing what was done:
          {"script": "removed" | "not_found",
           "settings": "removed" | "not_found" | "not_registered"}
    """
    claude_dir = repo_root / ".claude"
    hooks_dir = claude_dir / "hooks"
    script_path = hooks_dir / _HOOK_SCRIPT_NAME
    settings_path = claude_dir / "settings.json"

    result: dict[str, str] = {}

    # --- Remove hook script ---
    if script_path.exists():
        script_path.unlink()
        result["script"] = "removed"
    else:
        result["script"] = "not_found"

    # --- Remove settings entry ---
    if not settings_path.exists():
        result["settings"] = "not_found"
        return result

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        result["settings"] = "not_found"
        return result

    pre_tool = settings.get("hooks", {}).get("PreToolUse", [])
    original_len = len(pre_tool)

    # Filter out our hook entry — exact command match only
    filtered = [
        h for h in pre_tool
        if not (
            isinstance(h, dict)
            and any(
                isinstance(hh, dict) and hh.get("command") == _OUR_COMMAND
                for hh in h.get("hooks", [])
            )
        )
    ]

    if len(filtered) == original_len:
        result["settings"] = "not_registered"
    else:
        settings["hooks"]["PreToolUse"] = filtered
        settings_path.write_text(
            json.dumps(settings, indent=2) + "\n",
            encoding="utf-8",
        )
        result["settings"] = "removed"

    return result


# ---------------------------------------------------------------------------
# CLAUDE.md nano-digest wiring
# ---------------------------------------------------------------------------

_NANO_START = "<!-- pensieve:nano:start -->"
_NANO_END = "<!-- pensieve:nano:end -->"


def wire_nano_to_claudemd(repo_root: Path) -> dict[str, str]:
    """Inline agent-context-nano.md into CLAUDE.md.

    Reads the nano-digest from agent-docs/agent-context-nano.md and
    inlines it into CLAUDE.md wrapped in section markers. If CLAUDE.md
    already has a pensieve section, it is replaced. If CLAUDE.md doesn't
    exist, it is created.

    User content outside the markers is preserved.

    Returns:
        Dict with keys:
          - nano: "inlined" | "not_found" (nano file missing)
          - claudemd: "created" | "updated" | "unchanged"
    """
    result: dict[str, str] = {}

    nano_path = repo_root / "agent-docs" / "agent-context-nano.md"
    if not nano_path.exists():
        result["nano"] = "not_found"
        result["claudemd"] = "unchanged"
        return result

    nano_content = nano_path.read_text(encoding="utf-8").strip()
    result["nano"] = "inlined"

    section = f"{_NANO_START}\n{nano_content}\n{_NANO_END}"

    claudemd_path = repo_root / "CLAUDE.md"

    if not claudemd_path.exists():
        claudemd_path.write_text(section + "\n", encoding="utf-8")
        result["claudemd"] = "created"
        return result

    existing = claudemd_path.read_text(encoding="utf-8")

    if _NANO_START in existing and _NANO_END in existing:
        start_idx = existing.index(_NANO_START)
        end_idx = existing.index(_NANO_END) + len(_NANO_END)
        if end_idx < len(existing) and existing[end_idx] == "\n":
            end_idx += 1
        new_content = existing[:start_idx] + section + "\n" + existing[end_idx:]

        if new_content.strip() == existing.strip():
            result["claudemd"] = "unchanged"
        else:
            claudemd_path.write_text(new_content, encoding="utf-8")
            result["claudemd"] = "updated"
    else:
        if not existing.endswith("\n"):
            existing += "\n"
        claudemd_path.write_text(
            existing + "\n" + section + "\n",
            encoding="utf-8",
        )
        result["claudemd"] = "updated"

    return result


def unwire_nano_from_claudemd(repo_root: Path) -> dict[str, str]:
    """Remove the pensieve nano section from CLAUDE.md.

    Returns:
        Dict with keys:
          - claudemd: "removed" | "not_found" | "no_section"
    """
    claudemd_path = repo_root / "CLAUDE.md"

    if not claudemd_path.exists():
        return {"claudemd": "not_found"}

    existing = claudemd_path.read_text(encoding="utf-8")

    if _NANO_START not in existing or _NANO_END not in existing:
        return {"claudemd": "no_section"}

    start_idx = existing.index(_NANO_START)
    end_idx = existing.index(_NANO_END) + len(_NANO_END)
    if end_idx < len(existing) and existing[end_idx] == "\n":
        end_idx += 1
    if start_idx > 0 and existing[start_idx - 1] == "\n":
        start_idx -= 1

    new_content = existing[:start_idx] + existing[end_idx:]
    claudemd_path.write_text(new_content, encoding="utf-8")

    return {"claudemd": "removed"}
