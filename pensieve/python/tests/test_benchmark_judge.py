"""Tests for the LLM judge (benchmark task evaluation).

All tests mock subprocess.run — no real Claude Code invocations.
Covers:
  - Successful PASS/FAIL parsing from structured output
  - Quality score extraction and clamping
  - Error handling: timeout, not found, empty output, bad JSON, Claude error
  - Unstructured response fallback
  - JudgeResult dataclass shape
"""

from __future__ import annotations

import json
import subprocess
from unittest import mock

import pytest

from pensieve.benchmark.judge import JudgeResult, judge_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_judge_output(
    verdict: str = "PASS",
    quality: float = 7.5,
    reasoning: str = "Good work",
    is_error: bool = False,
    error_result: str | None = None,
) -> str:
    """Build a realistic Claude Code JSON output with structured_output."""
    data = {
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "result": error_result or "",
        "total_cost_usd": 0.01,
        "duration_ms": 2000,
        "usage": {"input_tokens": 500, "output_tokens": 50},
        "structured_output": {
            "verdict": verdict,
            "quality": quality,
            "reasoning": reasoning,
        },
    }
    if is_error:
        data["structured_output"] = None
        data["result"] = error_result or "error"
    return json.dumps(data)


def _mock_run(output: str):
    return mock.MagicMock(stdout=output, stderr="", returncode=0)


# ---------------------------------------------------------------------------
# Successful evaluation
# ---------------------------------------------------------------------------


class TestSuccessfulJudge:

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_pass_verdict(self, mock_run):
        mock_run.return_value = _mock_run(
            _make_judge_output(verdict="PASS", quality=8.0, reasoning="Solid")
        )
        result = judge_task("Does it work?", "Yes it works")

        assert result.lenient_pass is True
        assert result.quality_score == 8.0
        assert result.reasoning == "Solid"
        assert result.error is None

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_fail_verdict(self, mock_run):
        mock_run.return_value = _mock_run(
            _make_judge_output(verdict="FAIL", quality=2.0, reasoning="Missed the point")
        )
        result = judge_task("Does it work?", "No")

        assert result.lenient_pass is False
        assert result.quality_score == 2.0
        assert result.reasoning == "Missed the point"
        assert result.error is None

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_quality_clamped_to_10(self, mock_run):
        mock_run.return_value = _mock_run(
            _make_judge_output(quality=15.0)
        )
        result = judge_task("test", "test")
        assert result.quality_score == 10.0

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_quality_clamped_to_0(self, mock_run):
        mock_run.return_value = _mock_run(
            _make_judge_output(quality=-5.0)
        )
        result = judge_task("test", "test")
        assert result.quality_score == 0.0

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_model_passed_to_command(self, mock_run):
        mock_run.return_value = _mock_run(_make_judge_output())
        judge_task("test", "test", model="haiku")

        cmd = mock_run.call_args[0][0]
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "haiku"

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_uses_json_schema(self, mock_run):
        mock_run.return_value = _mock_run(_make_judge_output())
        judge_task("test", "test")

        cmd = mock_run.call_args[0][0]
        assert "--json-schema" in cmd

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_uses_bare_mode(self, mock_run):
        """Judge should use --bare to skip hooks and CLAUDE.md."""
        mock_run.return_value = _mock_run(_make_judge_output())
        judge_task("test", "test")

        cmd = mock_run.call_args[0][0]
        assert "--bare" in cmd


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestJudgeErrors:

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=60)
        result = judge_task("test", "test")

        assert result.lenient_pass is False
        assert result.quality_score == 0.0
        assert result.error is not None
        assert "timed out" in result.error.lower()

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_claude_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = judge_task("test", "test")

        assert result.error is not None
        assert "not found" in result.error.lower()

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_empty_stdout(self, mock_run):
        mock_run.return_value = mock.MagicMock(stdout="", stderr="oops", returncode=0)
        result = judge_task("test", "test")

        assert result.error is not None
        assert "empty stdout" in result.error.lower()

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_invalid_json(self, mock_run):
        mock_run.return_value = mock.MagicMock(stdout="not json", stderr="", returncode=0)
        result = judge_task("test", "test")

        assert result.error is not None
        assert "json" in result.error.lower()

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_claude_error_response(self, mock_run):
        mock_run.return_value = _mock_run(
            _make_judge_output(is_error=True, error_result="Rate limited")
        )
        result = judge_task("test", "test")

        assert result.error is not None
        assert "Rate limited" in result.error

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_missing_structured_output(self, mock_run):
        """When structured_output is missing, fall back to result field."""
        data = {
            "type": "result",
            "is_error": False,
            "result": json.dumps({
                "verdict": "PASS",
                "quality": 6.0,
                "reasoning": "ok",
            }),
            "structured_output": None,
        }
        mock_run.return_value = _mock_run(json.dumps(data))
        result = judge_task("test", "test")

        assert result.lenient_pass is True
        assert result.quality_score == 6.0

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_unstructured_string_result(self, mock_run):
        """When result is a plain string, error is reported."""
        data = {
            "type": "result",
            "is_error": False,
            "result": "PASS - looks good",
            "structured_output": None,
        }
        mock_run.return_value = _mock_run(json.dumps(data))
        result = judge_task("test", "test")

        assert result.error is not None
        assert "unstructured" in result.error.lower()

    # --- Regression: review findings ---

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_nonzero_returncode_with_parseable_json(self, mock_run):
        """Non-zero exit code must produce an error even if stdout
        contains valid parseable structured JSON."""
        mock_run.return_value = mock.MagicMock(
            stdout=_make_judge_output(verdict="PASS", quality=9.0),
            stderr="transport error",
            returncode=1,
        )
        result = judge_task("test", "test")

        assert result.lenient_pass is False
        assert result.error is not None
        assert "exited with code 1" in result.error

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_malformed_quality_does_not_raise(self, mock_run):
        """quality='not-a-number' must degrade gracefully, not crash."""
        data = {
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {
                "verdict": "PASS",
                "quality": "not-a-number",
                "reasoning": "ok",
            },
        }
        mock_run.return_value = mock.MagicMock(
            stdout=json.dumps(data), stderr="", returncode=0,
        )
        result = judge_task("test", "test")

        # Should not raise — degrades to quality 0.0
        assert result.quality_score == 0.0
        assert "malformed" in result.reasoning

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_quality_none_does_not_raise(self, mock_run):
        """quality=None must degrade gracefully."""
        data = {
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {
                "verdict": "FAIL",
                "quality": None,
                "reasoning": "bad",
            },
        }
        mock_run.return_value = mock.MagicMock(
            stdout=json.dumps(data), stderr="", returncode=0,
        )
        result = judge_task("test", "test")

        assert result.quality_score == 0.0

    @mock.patch("pensieve.benchmark.judge.subprocess.run")
    def test_structured_output_is_list_not_dict(self, mock_run):
        """structured_output as a list should not crash."""
        data = {
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": ["PASS", 7.0, "ok"],
        }
        mock_run.return_value = mock.MagicMock(
            stdout=json.dumps(data), stderr="", returncode=0,
        )
        result = judge_task("test", "test")

        assert result.error is not None
        assert "not a dict" in result.error


# ---------------------------------------------------------------------------
# JudgeResult shape
# ---------------------------------------------------------------------------


class TestJudgeResultShape:

    def test_dataclass_fields(self):
        r = JudgeResult(
            lenient_pass=True,
            quality_score=7.0,
            reasoning="good",
        )
        assert r.lenient_pass is True
        assert r.quality_score == 7.0
        assert r.reasoning == "good"
        assert r.error is None

    def test_error_result(self):
        r = JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error="something broke",
        )
        assert r.error == "something broke"
