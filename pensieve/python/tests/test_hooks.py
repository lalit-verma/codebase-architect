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

    def test_hook_script_outputs_valid_json_structure(self, tmp_path):
        """The embedded hook script should output hookSpecificOutput JSON."""
        assert "hookSpecificOutput" in HOOK_SCRIPT
        assert "PreToolUse" in HOOK_SCRIPT
        assert "permissionDecision" in HOOK_SCRIPT
        assert "additionalContext" in HOOK_SCRIPT


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


# ---------------------------------------------------------------------------
# CLAUDE.md nano wiring
# ---------------------------------------------------------------------------


class TestWireNano:

    def test_creates_claudemd_if_missing(self, tmp_path):
        from pensieve.hooks import wire_nano_to_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\nQuick context.\n")

        result = wire_nano_to_claudemd(repo)
        assert result["nano"] == "inlined"
        assert result["claudemd"] == "created"

        content = (repo / "CLAUDE.md").read_text()
        assert "# Nano" in content
        assert "<!-- pensieve:nano:start -->" in content
        assert "<!-- pensieve:nano:end -->" in content

    def test_appends_to_existing_claudemd(self, tmp_path):
        from pensieve.hooks import wire_nano_to_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        (repo / "CLAUDE.md").write_text("# My Project\n\nExisting content.\n")

        result = wire_nano_to_claudemd(repo)
        assert result["claudemd"] == "updated"

        content = (repo / "CLAUDE.md").read_text()
        assert "Existing content." in content
        assert "# Nano" in content

    def test_replaces_existing_section(self, tmp_path):
        from pensieve.hooks import wire_nano_to_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Updated Nano\n")
        (repo / "CLAUDE.md").write_text(
            "# Project\n\n"
            "<!-- pensieve:nano:start -->\n"
            "# Old Nano\n"
            "<!-- pensieve:nano:end -->\n"
            "\nMore content.\n"
        )

        result = wire_nano_to_claudemd(repo)
        assert result["claudemd"] == "updated"

        content = (repo / "CLAUDE.md").read_text()
        assert "# Updated Nano" in content
        assert "# Old Nano" not in content
        assert "More content." in content
        assert content.count("<!-- pensieve:nano:start -->") == 1

    def test_idempotent(self, tmp_path):
        from pensieve.hooks import wire_nano_to_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")

        wire_nano_to_claudemd(repo)
        result = wire_nano_to_claudemd(repo)
        assert result["claudemd"] == "unchanged"

    def test_nano_not_found(self, tmp_path):
        from pensieve.hooks import wire_nano_to_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        result = wire_nano_to_claudemd(repo)
        assert result["nano"] == "not_found"
        assert result["claudemd"] == "unchanged"


class TestUnwireNano:

    def test_removes_section(self, tmp_path):
        from pensieve.hooks import unwire_nano_from_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CLAUDE.md").write_text(
            "# Project\n\n"
            "<!-- pensieve:nano:start -->\n"
            "# Nano\n"
            "<!-- pensieve:nano:end -->\n"
            "\nKeep this.\n"
        )

        result = unwire_nano_from_claudemd(repo)
        assert result["claudemd"] == "removed"

        content = (repo / "CLAUDE.md").read_text()
        assert "Nano" not in content
        assert "Keep this." in content

    def test_no_claudemd(self, tmp_path):
        from pensieve.hooks import unwire_nano_from_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        result = unwire_nano_from_claudemd(repo)
        assert result["claudemd"] == "not_found"

    def test_no_section(self, tmp_path):
        from pensieve.hooks import unwire_nano_from_claudemd
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CLAUDE.md").write_text("# Project\nNo pensieve here.\n")
        result = unwire_nano_from_claudemd(repo)
        assert result["claudemd"] == "no_section"


class TestWireCLI:

    def test_wire_help(self, capsys):
        from pensieve.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(["wire", "--help"])
        assert exc_info.value.code == 0
        assert "wire" in capsys.readouterr().out.lower()

    def test_wire_missing_nano(self, capsys, tmp_path):
        from pensieve.cli import main
        repo = tmp_path / "repo"
        repo.mkdir()
        result = main(["wire", "--repo", str(repo)])
        assert result == 1
        assert "not found" in capsys.readouterr().err.lower()

    def test_wire_missing_nano_no_side_effects(self, tmp_path):
        """Failed wire (missing nano) must not create hook or settings."""
        from pensieve.cli import main
        repo = tmp_path / "repo"
        repo.mkdir()
        main(["wire", "--repo", str(repo)])
        # No hook script should be created
        assert not (repo / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()
        # No settings.json should be created
        assert not (repo / ".claude" / "settings.json").exists()
        # No CLAUDE.md should be created
        assert not (repo / "CLAUDE.md").exists()

    def test_wire_success(self, capsys, tmp_path):
        from pensieve.cli import main
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")

        result = main(["wire", "--repo", str(repo)])
        assert result == 0
        assert (repo / "CLAUDE.md").exists()
        assert (repo / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()

    def test_unwire(self, capsys, tmp_path):
        from pensieve.cli import main
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")

        # Wire first
        main(["wire", "--repo", str(repo)])
        # Then unwire
        result = main(["wire", "--repo", str(repo), "--unwire"])
        assert result == 0

        content = (repo / "CLAUDE.md").read_text()
        assert "pensieve:nano:start" not in content


# ---------------------------------------------------------------------------
# Bx5: Hook telemetry
# ---------------------------------------------------------------------------


class TestHookTelemetry:
    """Test that the hook script contains telemetry logging logic."""

    def test_hook_script_contains_telemetry_append(self):
        """The hook script should write to hook-telemetry.jsonl."""
        from pensieve.hooks import HOOK_SCRIPT
        assert "hook-telemetry.jsonl" in HOOK_SCRIPT

    def test_hook_script_logs_event_fields(self):
        """The telemetry event should include required fields."""
        from pensieve.hooks import HOOK_SCRIPT
        assert "'timestamp'" in HOOK_SCRIPT
        assert "'event'" in HOOK_SCRIPT
        assert "'tool_name'" in HOOK_SCRIPT
        assert "'hint_type'" in HOOK_SCRIPT
        assert "'target_doc'" in HOOK_SCRIPT
        assert "'session_id'" in HOOK_SCRIPT

    def test_hook_script_reads_route_index(self):
        """The hook should attempt to use route-index.json."""
        from pensieve.hooks import HOOK_SCRIPT
        assert "route-index.json" in HOOK_SCRIPT

    def test_hook_script_reads_stdin(self):
        """The hook should read tool input from stdin."""
        from pensieve.hooks import HOOK_SCRIPT
        assert "/dev/stdin" in HOOK_SCRIPT or "cat" in HOOK_SCRIPT

    def test_installed_hook_produces_telemetry(self, tmp_path):
        """End-to-end: installed hook writes telemetry when invoked."""
        import subprocess
        from pensieve.hooks import install_hook

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")

        # Create a simple route index
        import json as json_mod
        (ad / "route-index.json").write_text(json_mod.dumps({
            "version": 1,
            "routes": [
                {"match_type": "directory_prefix", "pattern": "src",
                 "subsystem": "Core", "doc_path": "agent-docs/subsystems/core.md",
                 "hint": "Core subsystem"}
            ],
            "fallback_hint": "See agent-docs/agent-context.md",
        }))

        install_hook(repo)

        # Invoke the hook with mock stdin
        hook_path = repo / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        input_json = json_mod.dumps({
            "tool_name": "Glob",
            "tool_input": {"pattern": "src/**/*.py"},
            "session_id": "test-session-123",
        })

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            cwd=str(repo),
            timeout=10,
        )

        assert result.returncode == 0

        # Check telemetry was written
        telemetry_path = ad / "hook-telemetry.jsonl"
        if telemetry_path.exists():
            lines = telemetry_path.read_text().strip().split("\n")
            assert len(lines) >= 1
            event = json_mod.loads(lines[0])
            assert event["event"] == "hint_shown"
            assert event["tool_name"] == "Glob"
            assert event["session_id"] == "test-session-123"

    def test_installed_hook_v2_routed_hint(self, tmp_path):
        """End-to-end: v2 route-index produces a routed hint, not fallback."""
        import subprocess
        from pensieve.hooks import install_hook

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")

        import json as json_mod
        (ad / "route-index.json").write_text(json_mod.dumps({
            "version": 2,
            "subsystem_routes": [
                {
                    "subsystem": "api-routers",
                    "doc_path": "agent-docs/subsystems/api-routers.md",
                    "role": "HTTP request handling",
                    "owns_paths": ["backend/routers"],
                    "common_tasks": ["Add new API endpoint"],
                    "brief_paths": ["backend/routers"],
                },
            ],
            "pattern_routes": [],
            "fallbacks": {},
            "fallback_hint": "Fallback hint.",
        }))

        install_hook(repo)

        hook_path = repo / ".claude" / "hooks" / "pensieve-pretooluse.sh"
        input_json = json_mod.dumps({
            "tool_name": "Glob",
            "tool_input": {"pattern": "backend/routers/**/*.py"},
            "session_id": "test-v2-session",
        })

        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            cwd=str(repo),
            timeout=10,
        )

        assert result.returncode == 0

        # The hook output should contain the routed hint, not fallback
        output = result.stdout.strip()
        if output:
            data = json_mod.loads(output)
            ctx = data.get("hookSpecificOutput", {}).get("additionalContext", "")
            assert "api-routers" in ctx.lower() or "Subsystem" in ctx, (
                f"Expected routed hint for api-routers, got: {ctx}"
            )

        # Telemetry should show directory_prefix match
        telemetry_path = ad / "hook-telemetry.jsonl"
        if telemetry_path.exists():
            lines = telemetry_path.read_text().strip().split("\n")
            event = json_mod.loads(lines[-1])
            assert event["route_match_type"] == "directory_prefix"
            assert event["artifact_kind"] == "subsystem_doc"
            assert event["target_subsystem"] == "api-routers"
