"""Tests for the PreToolUse hook installer/uninstaller (A3, A4).

Covers:
  - Fresh install: no .claude/ dir → creates everything from scratch
  - Existing settings.json with other hooks → merge without overwriting
  - Idempotent re-install → no duplicate entries
  - Uninstall: removes script + settings entry, preserves other hooks
  - Uninstall when not installed → graceful no-op
  - Hook script is executable
  - Hook script content matches expected JSON output pattern
  - CLI dispatch: `pensieve hook install/uninstall`
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from pensieve.hooks import install_hook, uninstall_hook, HOOK_SCRIPT, HOOK_ENTRY


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


class TestInstallHook:

    def test_fresh_install_creates_everything(self, tmp_path):
        """No .claude/ dir → creates dir, script, settings.json."""
        result = install_hook(tmp_path)

        assert result["script"] == "created"
        assert result["settings"] in ("created", "merged")

        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        assert script.exists()
        assert "hookSpecificOutput" in script.read_text()

        settings = tmp_path / ".claude" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]
        assert len(data["hooks"]["PreToolUse"]) == 1

    def test_script_is_executable(self, tmp_path):
        install_hook(tmp_path)
        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        assert os.access(script, os.X_OK)

    def test_merge_with_existing_settings(self, tmp_path):
        """Existing settings.json with other hooks → our entry appended."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"

        existing = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "echo other"}],
                    }
                ]
            },
            "other_setting": True,
        }
        settings_path.write_text(json.dumps(existing))

        result = install_hook(tmp_path)
        assert result["settings"] == "merged"

        data = json.loads(settings_path.read_text())
        # Both hooks should be present
        assert len(data["hooks"]["PreToolUse"]) == 2
        # Other settings preserved
        assert data["other_setting"] is True

    def test_idempotent_reinstall(self, tmp_path):
        """Re-running install does not create duplicate entries."""
        install_hook(tmp_path)
        result = install_hook(tmp_path)

        assert result["script"] == "already_exists"
        assert result["settings"] == "already_registered"

        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["PreToolUse"]) == 1

    def test_corrupted_settings_json(self, tmp_path):
        """Corrupted settings.json → treated as empty, overwritten."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("not valid json {{{")

        result = install_hook(tmp_path)
        assert result["script"] == "created"

        # settings.json should now be valid
        data = json.loads((claude_dir / "settings.json").read_text())
        assert len(data["hooks"]["PreToolUse"]) == 1

    def test_hook_script_outputs_valid_json(self, tmp_path):
        """The embedded hook script should contain valid JSON."""
        # Extract the JSON from the heredoc
        import re
        match = re.search(r"cat <<'HOOKEOF'\n(.+?)\nHOOKEOF", HOOK_SCRIPT, re.DOTALL)
        assert match is not None
        json_str = match.group(1)
        data = json.loads(json_str)
        assert data["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert data["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert "nano-digest" in data["hookSpecificOutput"]["additionalContext"]


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------


class TestUninstallHook:

    def test_uninstall_removes_script_and_settings(self, tmp_path):
        install_hook(tmp_path)
        result = uninstall_hook(tmp_path)

        assert result["script"] == "removed"
        assert result["settings"] == "removed"

        assert not (tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()

        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["PreToolUse"]) == 0

    def test_uninstall_preserves_other_hooks(self, tmp_path):
        """Uninstall removes only our hook, not other PreToolUse hooks."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"

        settings = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo other"}]},
                ]
            }
        }
        settings_path.write_text(json.dumps(settings))

        install_hook(tmp_path)
        uninstall_hook(tmp_path)

        data = json.loads(settings_path.read_text())
        # The other hook should still be there
        assert len(data["hooks"]["PreToolUse"]) == 1
        assert data["hooks"]["PreToolUse"][0]["matcher"] == "Bash"

    def test_uninstall_when_not_installed(self, tmp_path):
        """Uninstall on a repo without the hook → graceful no-op."""
        result = uninstall_hook(tmp_path)
        assert result["script"] == "not_found"
        assert result["settings"] == "not_found"

    def test_uninstall_script_only(self, tmp_path):
        """If settings.json was manually removed but script exists."""
        install_hook(tmp_path)
        (tmp_path / ".claude" / "settings.json").unlink()

        result = uninstall_hook(tmp_path)
        assert result["script"] == "removed"
        assert result["settings"] == "not_found"

    def test_uninstall_settings_only(self, tmp_path):
        """If script was manually removed but settings entry exists."""
        install_hook(tmp_path)
        (tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh").unlink()

        result = uninstall_hook(tmp_path)
        assert result["script"] == "not_found"
        assert result["settings"] == "removed"


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# A5: End-to-end smoke test — run the INSTALLED script via subprocess
# ---------------------------------------------------------------------------


class TestInstalledHookE2E:
    """After pensieve hook install, run the installed .sh script via
    subprocess and verify it produces the expected JSON output."""

    def test_installed_hook_fires_when_nano_exists(self, tmp_path):
        """Install hook → create agent-docs/agent-context-nano.md →
        run the script → should produce JSON with hookSpecificOutput."""
        import subprocess

        install_hook(tmp_path)

        # Create the trigger file
        (tmp_path / "agent-docs").mkdir()
        (tmp_path / "agent-docs" / "agent-context-nano.md").write_text("# Quick Context\n")

        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        assert result.stdout.strip() != ""

        # Parse JSON output
        data = json.loads(result.stdout)
        assert data["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert data["hookSpecificOutput"]["permissionDecision"] == "allow"
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "nano-digest" in ctx
        assert "Explore subagent" in ctx
        assert "Never read agent-docs/" in ctx

    def test_installed_hook_silent_when_no_nano(self, tmp_path):
        """Install hook → no agent-docs/ → run script → empty output."""
        import subprocess

        install_hook(tmp_path)

        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_installed_hook_silent_when_nano_removed(self, tmp_path):
        """Hook fires → remove nano → hook goes silent."""
        import subprocess

        install_hook(tmp_path)
        nano_dir = tmp_path / "agent-docs"
        nano_dir.mkdir()
        nano_file = nano_dir / "agent-context-nano.md"
        nano_file.write_text("# Quick Context\n")

        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"

        # First run: should produce output
        r1 = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert r1.stdout.strip() != ""

        # Remove nano file
        nano_file.unlink()

        # Second run: should be silent
        r2 = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert r2.returncode == 0
        assert r2.stdout.strip() == ""

    def test_full_cycle_install_verify_uninstall(self, tmp_path):
        """Install → verify script works → uninstall → script gone."""
        import subprocess

        # Install
        install_result = install_hook(tmp_path)
        assert install_result["script"] == "created"

        script = tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        assert script.exists()

        # Verify it runs
        (tmp_path / "agent-docs").mkdir()
        (tmp_path / "agent-docs" / "agent-context-nano.md").write_text("# ctx\n")

        r = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert r.returncode == 0
        assert "hookSpecificOutput" in r.stdout

        # Uninstall
        uninstall_result = uninstall_hook(tmp_path)
        assert uninstall_result["script"] == "removed"
        assert not script.exists()


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


class TestCLI:

    def test_hook_install_via_cli(self, tmp_path):
        from pensieve.cli import main
        result = main(["hook", "install", "--repo", str(tmp_path)])
        assert result == 0
        assert (tmp_path / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()
        assert (tmp_path / ".claude" / "settings.json").exists()

    def test_hook_uninstall_via_cli(self, tmp_path):
        from pensieve.cli import main
        main(["hook", "install", "--repo", str(tmp_path)])
        result = main(["hook", "uninstall", "--repo", str(tmp_path)])
        assert result == 0

    def test_hook_no_action_shows_error(self, tmp_path, capsys):
        from pensieve.cli import main
        result = main(["hook"])
        assert result == 1

    def test_hook_install_nonexistent_repo(self, tmp_path, capsys):
        from pensieve.cli import main
        result = main(["hook", "install", "--repo", str(tmp_path / "nope")])
        assert result == 1
        assert "not a directory" in capsys.readouterr().err
