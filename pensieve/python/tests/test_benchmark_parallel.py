"""Tests for parallel benchmark execution.

Covers:
  - All tasks execute exactly once with parallelism > 1
  - Results are returned in original task order
  - One task failing does not stop others
  - parallelism=1 matches sequential behavior
  - CLI --parallelism flag parsing
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest import mock

import pytest

from pensieve.benchmark.generate import TaskInstance
from pensieve.benchmark.runner import (
    TaskResult,
    _run_mode_tasks,
    run_generated_benchmark,
)
from pensieve.benchmark.template import CheckerSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_instance(name: str, idx: int, setup_actions=None) -> TaskInstance:
    return TaskInstance(
        template_family=name,
        instance_id=f"{name}_{idx}",
        difficulty="easy",
        instruction=f"Do task {name}_{idx}",
        strict_checker=CheckerSpec(
            checker_type="content_contains",
            criteria="response has something",
            target_string="done",
        ),
        lenient_checker=CheckerSpec(
            checker_type="llm_judge",
            criteria="looks good",
            llm_prompt="Is it good?",
        ),
        setup_actions=setup_actions or [],
    )


class _MockExecutor:
    """Executor that records which instructions it received."""

    def __init__(self, delay: float = 0.0):
        self.calls: list[str] = []
        self._delay = delay

    def execute(self, instruction, repo_root, mode):
        self.calls.append(instruction)
        if self._delay:
            time.sleep(self._delay)
        return {
            "response": "done",
            "tokens": 100,
            "cost_usd": 0.01,
            "time_seconds": 1.0,
        }


class _FailingExecutor:
    """Executor that fails on specific instructions."""

    def __init__(self, fail_on: str):
        self._fail_on = fail_on

    def execute(self, instruction, repo_root, mode):
        if self._fail_on in instruction:
            raise RuntimeError(f"Deliberate failure on: {self._fail_on}")
        return {
            "response": "done",
            "tokens": 100,
            "cost_usd": 0.01,
            "time_seconds": 1.0,
        }


def _make_mode_copy(tmp_path: Path) -> Path:
    """Create a minimal mode copy directory."""
    mode_copy = tmp_path / "mode_copy"
    mode_copy.mkdir()
    (mode_copy / "file.py").write_text("x = 1\n")
    return mode_copy


# ---------------------------------------------------------------------------
# _run_mode_tasks tests
# ---------------------------------------------------------------------------


class TestRunModeTasks:

    def test_sequential_executes_all(self, tmp_path):
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(3)]
        executor = _MockExecutor()

        results = _run_mode_tasks(
            mode_copy, instances, executor, "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=1,
        )

        assert len(results) == 3
        assert len(executor.calls) == 3

    def test_parallel_executes_all(self, tmp_path):
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(4)]
        executor = _MockExecutor()

        results = _run_mode_tasks(
            mode_copy, instances, executor, "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=3,
        )

        assert len(results) == 4
        assert len(executor.calls) == 4

    def test_parallel_preserves_order(self, tmp_path):
        """Results must be in original task order, not completion order."""
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(5)]
        executor = _MockExecutor()

        results = _run_mode_tasks(
            mode_copy, instances, executor, "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=3,
        )

        # Each result should match its original instruction
        for i, result in enumerate(results):
            assert f"task_{i}" in result.instruction

    def test_one_failure_does_not_stop_others(self, tmp_path):
        """A failing task should not prevent other tasks from completing."""
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(3)]
        executor = _FailingExecutor(fail_on="task_1")

        results = _run_mode_tasks(
            mode_copy, instances, executor, "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=2,
        )

        assert len(results) == 3
        # Task 0 and 2 should succeed
        assert results[0].error is None
        assert results[2].error is None
        # Task 1 should have an error
        assert results[1].error is not None
        assert "Deliberate failure" in results[1].error

    def test_sequential_and_parallel_same_results(self, tmp_path):
        """Sequential and parallel should produce same result shape."""
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(3)]

        seq_results = _run_mode_tasks(
            mode_copy, instances, _MockExecutor(), "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=1,
        )

        par_results = _run_mode_tasks(
            mode_copy, instances, _MockExecutor(), "baseline",
            on_progress=None, run_judge=False, judge_model="sonnet",
            parallelism=3,
        )

        assert len(seq_results) == len(par_results)
        for s, p in zip(seq_results, par_results):
            assert s.template_name == p.template_name
            assert s.instruction == p.instruction
            assert s.tokens_used == p.tokens_used
            assert s.cost_usd == p.cost_usd

    def test_progress_callback_called(self, tmp_path):
        mode_copy = _make_mode_copy(tmp_path)
        instances = [_make_instance("task", i) for i in range(2)]
        executor = _MockExecutor()
        progress_calls = []

        def on_progress(mode, name, idx, total, result):
            progress_calls.append((mode, name, idx, result is not None))

        _run_mode_tasks(
            mode_copy, instances, executor, "baseline",
            on_progress=on_progress, run_judge=False, judge_model="sonnet",
            parallelism=2,
        )

        # Should have start + complete for each task
        starts = [c for c in progress_calls if not c[3]]
        completions = [c for c in progress_calls if c[3]]
        assert len(starts) == 2
        assert len(completions) == 2


# ---------------------------------------------------------------------------
# CLI --parallelism
# ---------------------------------------------------------------------------


class TestCLIParallelism:

    def test_parallelism_flag_in_help(self, capsys):
        from pensieve.cli import main
        with pytest.raises(SystemExit):
            main(["benchmark", "run", "--help"])
        captured = capsys.readouterr()
        assert "--parallelism" in captured.out

    def test_invalid_parallelism_rejected(self, capsys, tmp_path):
        from pensieve.cli import main
        # Create a repo with structure.json so we get past the arg validation
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "structure.json").write_text(json.dumps({
            "repo_root": str(repo), "files": [
                {"file_path": "a.py", "language": "python", "symbols": [
                    {"name": "f", "kind": "function", "line_start": 1, "line_end": 5,
                     "signature": "def f():", "visibility": "public", "parent": None,
                     "docstring": None, "parameters": [], "return_type": None}
                ], "imports": [], "exports": [], "call_edges": [], "comments": []},
                {"file_path": "b.py", "language": "python", "symbols": [
                    {"name": "g", "kind": "function", "line_start": 1, "line_end": 5,
                     "signature": "def g():", "visibility": "public", "parent": None,
                     "docstring": None, "parameters": [], "return_type": None}
                ], "imports": [], "exports": [], "call_edges": [], "comments": []},
                {"file_path": "c.py", "language": "python", "symbols": [], "imports": [],
                 "exports": [], "call_edges": [], "comments": []},
            ], "errors": [], "extractor_version": "test",
        }))

        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock()

        import sys
        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main([
                "benchmark", "run", "--repo", str(repo),
                "--parallelism", "0",
            ])
        assert result == 1
        captured = capsys.readouterr()
        assert "must be >= 1" in captured.err
