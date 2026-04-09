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
# Fires before every Glob/Grep. Injects a reminder via
# hookSpecificOutput.additionalContext when agent-docs exists.
# Reference: https://code.claude.com/docs/en/hooks

if [ -f agent-docs/agent-context-nano.md ]; then
  cat <<'HOOKEOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":"Codebase context already loaded in CLAUDE.md (nano-digest). For deeper context: Explore subagent on agent-docs/agent-context.md. Never read agent-docs/ from main thread (triggers long-context fallback)."}}
HOOKEOF
fi
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
