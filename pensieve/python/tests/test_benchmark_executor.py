"""Tests for the Claude Code subprocess executor.

All tests mock subprocess.run — no real Claude Code invocations.
Covers:
  - Command building: flags, model, budget, extra args
  - JSON output parsing: tokens, cost, time, response
  - Error handling: timeout, not found, empty output, bad JSON, Claude error
  - Factory function: create_executor returns correct type
  - Protocol compliance: execute() returns the expected dict shape
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from pensieve.benchmark.executor import ClaudeCodeExecutor, create_executor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_claude_json_output(
    result: str = "Task completed",
    is_error: bool = False,
    total_cost_usd: float = 0.05,
    duration_ms: int = 3000,
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 200,
    cache_creation: int = 0,
) -> str:
    """Build a realistic Claude Code JSON output string."""
    return json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "duration_ms": duration_ms,
        "num_turns": 2,
        "result": result,
        "stop_reason": "end_turn",
        "session_id": "test-session-id",
        "total_cost_usd": total_cost_usd,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
        },
    })


def _mock_run_success(output: str = None, returncode: int = 0):
    """Create a mock subprocess.run result."""
    if output is None:
        output = _make_claude_json_output()
    return mock.MagicMock(
        stdout=output,
        stderr="",
        returncode=returncode,
    )


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestCommandBuilding:

    def test_default_command(self):
        """Default executor builds a valid claude command."""
        ex = ClaudeCodeExecutor()
        cmd = ex._build_command("Do something")
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--output-format" in cmd
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "json"
        assert "--permission-mode" in cmd
        assert "--no-session-persistence" in cmd
        assert cmd[-1] == "Do something"

    def test_model_flag(self):
        ex = ClaudeCodeExecutor(model="sonnet")
        cmd = ex._build_command("test")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "sonnet"

    def test_no_model_flag_when_none(self):
        ex = ClaudeCodeExecutor(model=None)
        cmd = ex._build_command("test")
        assert "--model" not in cmd

    def test_budget_flag(self):
        ex = ClaudeCodeExecutor(max_budget_usd=2.0)
        cmd = ex._build_command("test")
        assert "--max-budget-usd" in cmd
        idx = cmd.index("--max-budget-usd")
        assert cmd[idx + 1] == "2.0"

    def test_no_budget_flag_when_none(self):
        ex = ClaudeCodeExecutor(max_budget_usd=None)
        cmd = ex._build_command("test")
        assert "--max-budget-usd" not in cmd

    def test_extra_args_appended(self):
        ex = ClaudeCodeExecutor(extra_args=["--bare", "--verbose"])
        cmd = ex._build_command("test")
        assert "--bare" in cmd
        assert "--verbose" in cmd
        # Extra args before the instruction
        bare_idx = cmd.index("--bare")
        assert bare_idx < len(cmd) - 1

    def test_permission_mode(self):
        ex = ClaudeCodeExecutor(permission_mode="bypassPermissions")
        cmd = ex._build_command("test")
        idx = cmd.index("--permission-mode")
        assert cmd[idx + 1] == "bypassPermissions"

    def test_instruction_is_last_arg(self):
        """The instruction must be the last argument."""
        ex = ClaudeCodeExecutor(model="haiku", extra_args=["--bare"])
        cmd = ex._build_command("My task instruction")
        assert cmd[-1] == "My task instruction"


# ---------------------------------------------------------------------------
# JSON output parsing
# ---------------------------------------------------------------------------


class TestOutputParsing:

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_successful_parse(self, mock_run):
        mock_run.return_value = _mock_run_success(
            _make_claude_json_output(
                result="I fixed the bug",
                total_cost_usd=0.08,
                duration_ms=5000,
                input_tokens=200,
                output_tokens=100,
                cache_read=300,
                cache_creation=50,
            ),
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("Fix the bug", Path("/tmp/repo"), "baseline")

        assert out["response"] == "I fixed the bug"
        assert out["cost_usd"] == 0.08
        assert out["time_seconds"] == 5.0  # 5000ms -> 5.0s
        assert out["tokens"] == 200 + 100 + 300 + 50  # all token types summed
        assert "error" not in out

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_cwd_set_to_repo_root(self, mock_run):
        mock_run.return_value = _mock_run_success()
        ex = ClaudeCodeExecutor()
        ex.execute("test", Path("/my/repo"), "with_framework")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/my/repo"

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_zero_tokens_when_missing_usage(self, mock_run):
        """If usage fields are missing, tokens should be 0, not crash."""
        data = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "done",
            "total_cost_usd": 0.01,
            "duration_ms": 1000,
            "usage": {},
        })
        mock_run.return_value = _mock_run_success(data)
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert out["tokens"] == 0
        assert out["cost_usd"] == 0.01

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_missing_duration_falls_back_to_wall_clock(self, mock_run):
        """If duration_ms is missing, use wall-clock time."""
        data = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "done",
            "total_cost_usd": 0.0,
            "usage": {},
        })
        mock_run.return_value = _mock_run_success(data)
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        # Wall clock time should be very small in a mocked test
        assert isinstance(out["time_seconds"], float)
        assert out["time_seconds"] >= 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude"], timeout=300,
        )
        ex = ClaudeCodeExecutor(timeout_seconds=300)
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert out["tokens"] == 0
        assert "error" in out
        assert "timed out" in out["error"].lower()

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_claude_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "error" in out
        assert "not found" in out["error"].lower()

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_empty_stdout(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="",
            stderr="Some error message",
            returncode=1,
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "error" in out
        assert "empty stdout" in out["error"].lower()

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_invalid_json(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="This is not JSON at all",
            stderr="",
            returncode=0,
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "error" in out
        assert "json" in out["error"].lower()

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_claude_code_error_response(self, mock_run):
        """When Claude Code returns is_error=true, report it."""
        mock_run.return_value = _mock_run_success(
            _make_claude_json_output(
                result="Not logged in",
                is_error=True,
                total_cost_usd=0.0,
            ),
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "error" in out
        assert "Not logged in" in out["error"]
        assert out["response"] == "Not logged in"

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_stderr_used_when_stdout_empty(self, mock_run):
        """When stdout is empty, stderr content should be in response."""
        mock_run.return_value = mock.MagicMock(
            stdout="",
            stderr="Authentication failed",
            returncode=1,
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert out["response"] == "Authentication failed"


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


class TestFactory:

    def test_create_executor_returns_correct_type(self):
        ex = create_executor()
        assert isinstance(ex, ClaudeCodeExecutor)

    def test_create_executor_passes_args(self):
        ex = create_executor(
            model="haiku",
            max_budget_usd=1.5,
            permission_mode="bypassPermissions",
            timeout_seconds=120,
            extra_args=["--bare"],
        )
        cmd = ex._build_command("test")
        assert "--model" in cmd
        assert "haiku" in cmd
        assert "--max-budget-usd" in cmd
        assert "1.5" in cmd
        assert "--bare" in cmd


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_return_dict_has_required_keys(self, mock_run):
        """The execute() return dict must have the keys the runner expects."""
        mock_run.return_value = _mock_run_success()
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "response" in out
        assert "tokens" in out
        assert "cost_usd" in out
        assert "time_seconds" in out
        assert isinstance(out["response"], str)
        assert isinstance(out["tokens"], int)
        assert isinstance(out["cost_usd"], float)
        assert isinstance(out["time_seconds"], float)

    @mock.patch("pensieve.benchmark.executor.subprocess.run")
    def test_error_dict_still_has_required_keys(self, mock_run):
        """Even error returns must have the base keys so the runner
        doesn't crash on missing dict keys."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude"], timeout=300,
        )
        ex = ClaudeCodeExecutor()
        out = ex.execute("test", Path("/tmp"), "baseline")

        assert "response" in out
        assert "tokens" in out
        assert "cost_usd" in out
        assert "time_seconds" in out
