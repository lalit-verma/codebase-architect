"""PreToolUse hook installer/uninstaller (milestones A3, A4).

Installs the Code Pensieve PreToolUse hook into a target repo's
`.claude/` directory. The hook fires before every Glob/Grep tool call
and injects a reminder into Claude's context via the documented
`hookSpecificOutput.additionalContext` JSON mechanism.

Two artifacts are written:
  1. `.claude/hooks/pensieve-pretooluse.sh` — the hook script
  2. `.claude/settings.json` — the PreToolUse hook registration
     (merged into existing settings if present)

The hook's routing logic is generated from pensieve.route (the canonical
source of truth) — not hand-maintained here. See route.py for details.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

from pensieve.route import render_hook_routing_script

# ---------------------------------------------------------------------------
# Embedded hook content — routing script generated from canonical source
# ---------------------------------------------------------------------------

# Bash boilerplate with %%ROUTING_SCRIPT%% placeholder for the generated
# stdlib-only Python routing script from route.py.
_HOOK_SHELL_TEMPLATE = '''\
#!/bin/bash
# Code Pensieve PreToolUse hook for Claude Code.
# Fires before every Glob/Grep. Provides path-aware hints from
# route-index.json and logs telemetry to hook-telemetry.jsonl.
# Reference: https://code.claude.com/docs/en/hooks
#
# Routing logic generated at install time — do not edit inline.

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

# Path-aware routing (Bx2): self-contained, no pensieve import needed.
# Routing script generated at build time (canonical source: route.py).
ARTIFACT_KIND="fallback"
TARGET_SUBSYSTEM=""
ROUTE_MATCH_TYPE="fallback"
BRIEF_SUGGESTED="false"
BRIEF_MODE="none"

if [ -f agent-docs/route-index.json ] && command -v python3 &>/dev/null; then
  ROUTE_RESULT=$(python3 -c "
%%ROUTING_SCRIPT%%
" "$TOOL_INPUT" 2>/dev/null)

  if [ -n "$ROUTE_RESULT" ]; then
    ROUTED_HINT=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('hint',''))" 2>/dev/null || echo "")
    ROUTED_DOC=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('doc',''))" 2>/dev/null || echo "")
    TARGET_SUBSYSTEM=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('subsystem',''))" 2>/dev/null || echo "")
    ROUTE_MATCH_TYPE=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('match_type','fallback'))" 2>/dev/null || echo "fallback")
    ARTIFACT_KIND=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('artifact_kind','fallback'))" 2>/dev/null || echo "fallback")
    BRIEF_SUGGESTED=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print('true' if json.load(sys.stdin).get('brief_suggested',False) else 'false')" 2>/dev/null || echo "false")
    BRIEF_MODE=$(echo "$ROUTE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('brief_mode','none'))" 2>/dev/null || echo "none")
    if [ -n "$ROUTED_HINT" ]; then
      HINT="$ROUTED_HINT"
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
    'brief_suggested': sys.argv[10] == 'true',
    'brief_mode': sys.argv[11],
}
with open('agent-docs/hook-telemetry.jsonl', 'a') as f:
    f.write(json.dumps(event) + '\\n')
" "$TIMESTAMP" "$TOOL_NAME" "$TOOL_INPUT" "$HINT_TYPE" "$ROUTE_MATCH_TYPE" "$ARTIFACT_KIND" "$TARGET_DOC" "$TARGET_SUBSYSTEM" "$SESSION_ID" "$BRIEF_SUGGESTED" "$BRIEF_MODE" 2>/dev/null

# Output the hook response
cat <<HOOKEOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":"$HINT"}}
HOOKEOF
exit 0
'''

# Assemble the final hook script at import time by injecting the
# canonical routing logic from route.py into the bash template.
HOOK_SCRIPT = _HOOK_SHELL_TEMPLATE.replace(
    '%%ROUTING_SCRIPT%%', render_hook_routing_script(),
)

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
# CLAUDE.md managed sections
# ---------------------------------------------------------------------------

_NANO_START = "<!-- pensieve:nano:start -->"
_NANO_END = "<!-- pensieve:nano:end -->"

_USAGE_START = "<!-- pensieve:usage:start -->"
_USAGE_END = "<!-- pensieve:usage:end -->"

_USAGE_CONTENT = """\
## Pensieve

Pensieve is this repo's structural context tool. Use it to get fast orientation once the relevant path, subsystem, or slice is already known.

### When to use it
- Use `pensieve brief <paths>` when routing, file paths, or your current search already narrowed the work to a subsystem or directory slice.
- Prefer it before repeated broad `Glob` / `Grep` when you need structure, not just one symbol.
- Do not use it for vague repo-wide questions when the relevant area is still unknown.

### What it gives you
`pensieve brief` returns a structural map for the selected slice:
- key files and signatures
- internal dependencies
- entry points / wiring files
- related tests
- important rationale comments (`WHY`, `HACK`, `IMPORTANT`)

### How to use it well
- Start with the routed subsystem or path slice.
- Run `pensieve brief <paths>`.
- Use the brief to choose the next files to open, then continue with targeted reads and edits.
- Prefer this over reading large `agent-docs/` files in the main thread.

Treat Pensieve as the default structural tool once the area of work is known."""


def _upsert_section(content: str, start_marker: str, end_marker: str, section_body: str) -> tuple[str, str]:
    """Insert or replace a marker-delimited section in content.

    Returns (new_content, status) where status is "inserted", "replaced", or "unchanged".
    """
    section = f"{start_marker}\n{section_body}\n{end_marker}"

    if start_marker in content and end_marker in content:
        start_idx = content.index(start_marker)
        end_idx = content.index(end_marker) + len(end_marker)
        if end_idx < len(content) and content[end_idx] == "\n":
            end_idx += 1
        new_content = content[:start_idx] + section + "\n" + content[end_idx:]
        if new_content.strip() == content.strip():
            return content, "unchanged"
        return new_content, "replaced"

    if not content.endswith("\n"):
        content += "\n"
    return content + "\n" + section + "\n", "inserted"


def _remove_section(content: str, start_marker: str, end_marker: str) -> tuple[str, bool]:
    """Remove a marker-delimited section from content.

    Returns (new_content, was_removed).
    """
    if start_marker not in content or end_marker not in content:
        return content, False

    start_idx = content.index(start_marker)
    end_idx = content.index(end_marker) + len(end_marker)
    if end_idx < len(content) and content[end_idx] == "\n":
        end_idx += 1
    if start_idx > 0 and content[start_idx - 1] == "\n":
        start_idx -= 1

    return content[:start_idx] + content[end_idx:], True


def wire_nano_to_claudemd(repo_root: Path) -> dict[str, str]:
    """Inline agent-context-nano.md and Pensieve usage section into CLAUDE.md.

    Manages two pensieve-owned sections:
      1. Repo-specific nano-digest (from agent-docs/agent-context-nano.md)
      2. Generic Pensieve usage guide (static content)

    Both are wrapped in marker comments and updated idempotently.
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

    claudemd_path = repo_root / "CLAUDE.md"

    if not claudemd_path.exists():
        # Create with both sections
        content = (
            f"{_NANO_START}\n{nano_content}\n{_NANO_END}\n\n"
            f"{_USAGE_START}\n{_USAGE_CONTENT}\n{_USAGE_END}\n"
        )
        claudemd_path.write_text(content, encoding="utf-8")
        result["claudemd"] = "created"
        return result

    existing = claudemd_path.read_text(encoding="utf-8")

    # Upsert nano section
    content, nano_status = _upsert_section(existing, _NANO_START, _NANO_END, nano_content)

    # Upsert usage section
    content, usage_status = _upsert_section(content, _USAGE_START, _USAGE_END, _USAGE_CONTENT)

    if nano_status == "unchanged" and usage_status == "unchanged":
        result["claudemd"] = "unchanged"
    else:
        claudemd_path.write_text(content, encoding="utf-8")
        result["claudemd"] = "updated"

    return result


def unwire_nano_from_claudemd(repo_root: Path) -> dict[str, str]:
    """Remove both pensieve-managed sections from CLAUDE.md.

    Removes:
      1. Nano-digest section
      2. Pensieve usage section

    Returns:
        Dict with keys:
          - claudemd: "removed" | "not_found" | "no_section"
    """
    claudemd_path = repo_root / "CLAUDE.md"

    if not claudemd_path.exists():
        return {"claudemd": "not_found"}

    existing = claudemd_path.read_text(encoding="utf-8")

    content, nano_removed = _remove_section(existing, _NANO_START, _NANO_END)
    content, usage_removed = _remove_section(content, _USAGE_START, _USAGE_END)

    if not nano_removed and not usage_removed:
        return {"claudemd": "no_section"}

    claudemd_path.write_text(content, encoding="utf-8")
    return {"claudemd": "removed"}
