"""Regression tests for Phase A review findings.

Finding 1: Hook identity — exact command match, not substring
Finding 2: Setup action content validation
Finding 3: Fresh install status reporting
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.hooks import install_hook, uninstall_hook


# ---------------------------------------------------------------------------
# Finding 1: Hook identity — exact match, not substring
# ---------------------------------------------------------------------------


class TestHookIdentity:

    def _seed_settings(self, tmp_path, hooks_list):
        """Pre-seed .claude/settings.json with given PreToolUse hooks."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings = {"hooks": {"PreToolUse": hooks_list}}
        (claude_dir / "settings.json").write_text(json.dumps(settings))

    def test_unrelated_hook_with_pensieve_substring_not_treated_as_ours(self, tmp_path):
        """A hook whose command contains 'pensieve' as a substring but
        is NOT our exact command should NOT be treated as already installed."""
        unrelated = {
            "matcher": "Glob|Grep",
            "hooks": [{"type": "command", "command": "bash .claude/hooks/not-pensieve.sh --use-pensieve-cache"}],
        }
        self._seed_settings(tmp_path, [unrelated])

        result = install_hook(tmp_path)
        # Should NOT say already_registered — the unrelated hook is not ours
        assert result["settings"] != "already_registered"
        assert result["settings"] == "merged"

        # Both hooks should be present
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["PreToolUse"]) == 2

    def test_uninstall_preserves_unrelated_hook_with_pensieve_substring(self, tmp_path):
        """Uninstall should NOT remove an unrelated hook that happens to
        contain 'pensieve' in its command string."""
        unrelated = {
            "matcher": "Glob|Grep",
            "hooks": [{"type": "command", "command": "bash check-pensieve-cache.sh"}],
        }
        self._seed_settings(tmp_path, [unrelated])

        # Install ours
        install_hook(tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(data["hooks"]["PreToolUse"]) == 2

        # Uninstall ours
        uninstall_hook(tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        # The unrelated hook should still be there
        assert len(data["hooks"]["PreToolUse"]) == 1
        remaining = data["hooks"]["PreToolUse"][0]
        assert "check-pensieve-cache" in remaining["hooks"][0]["command"]

    def test_our_exact_hook_is_detected_as_already_registered(self, tmp_path):
        """Our exact command string should be detected as already registered."""
        install_hook(tmp_path)
        result = install_hook(tmp_path)
        assert result["settings"] == "already_registered"

    def test_our_exact_hook_is_removed_by_uninstall(self, tmp_path):
        """Our exact command string should be removed by uninstall."""
        install_hook(tmp_path)
        result = uninstall_hook(tmp_path)
        assert result["settings"] == "removed"


# ---------------------------------------------------------------------------
# Finding 2: Setup action content validation
# ---------------------------------------------------------------------------


class TestSetupActionContentValidation:

    def _make_template(self, setup_actions):
        from pensieve.benchmark.template import TaskTemplate, CheckerSpec
        return TaskTemplate(
            name="test", task_type="bug_fix", difficulty="easy",
            description="test", instruction="test",
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria="test", target_string="x",
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria="test", llm_prompt="test",
            ),
            setup_actions=setup_actions,
        )

    def test_write_file_without_content_rejected(self):
        from pensieve.benchmark.template import validate_template, TemplateError
        t = self._make_template([{"action": "write_file", "path": "x.py"}])
        with pytest.raises(TemplateError, match="write_file requires content"):
            validate_template(t)

    def test_modify_file_without_content_rejected(self):
        from pensieve.benchmark.template import validate_template, TemplateError
        t = self._make_template([{"action": "modify_file", "path": "x.py"}])
        with pytest.raises(TemplateError, match="modify_file requires content"):
            validate_template(t)

    def test_delete_file_without_content_accepted(self):
        from pensieve.benchmark.template import validate_template
        t = self._make_template([{"action": "delete_file", "path": "x.py"}])
        validate_template(t)  # should not raise

    def test_write_file_with_content_accepted(self):
        from pensieve.benchmark.template import validate_template
        t = self._make_template([
            {"action": "write_file", "path": "x.py", "content": "x = 1"}
        ])
        validate_template(t)

    def test_modify_file_with_content_accepted(self):
        from pensieve.benchmark.template import validate_template
        t = self._make_template([
            {"action": "modify_file", "path": "x.py", "content": "x = 2"}
        ])
        validate_template(t)


