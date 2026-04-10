"""Tests for benchmark mode setup/teardown and run_benchmark (A9).

Covers:
  - setup_baseline: hides agent-docs, uninstalls hook
  - teardown_baseline: restores agent-docs
  - setup_framework: ensures scan + hook installed
  - run_benchmark: orchestrates both modes
  - Edge cases: no agent-docs, already hidden, hook already absent
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.benchmark.runner import (
    BenchmarkResult,
    PlaceholderFiller,
    setup_baseline,
    setup_framework,
    teardown_baseline,
    run_benchmark,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scanned_repo(tmp_path):
    """Create a repo with real source files and run pensieve scan."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def hello():\n    return 42\n")
    (repo / "utils.py").write_text("def helper():\n    return 1\n")

    from pensieve.scan import scan_repo
    scan_repo(repo)
    return repo


class MockExecutor:
    def __init__(self, response="done"):
        self.response = response
        self.calls = []

    def execute(self, instruction, repo_root, mode):
        self.calls.append({"instruction": instruction, "mode": mode})
        return {"response": self.response, "tokens": 50, "cost_usd": 0.005, "time_seconds": 0.1}


# ---------------------------------------------------------------------------
# setup_baseline
# ---------------------------------------------------------------------------


class TestSetupBaseline:

    def test_hides_agent_docs(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        assert (repo / "agent-docs").exists()

        state = setup_baseline(repo)

        assert not (repo / "agent-docs").exists()
        assert (repo / ".agent-docs-hidden").exists()
        assert state["agent_docs"] == "hidden"

    def test_no_agent_docs_graceful(self, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()

        state = setup_baseline(repo)
        assert state["agent_docs"] == "not_present"

    def test_already_hidden_graceful(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        setup_baseline(repo)  # first hide
        state = setup_baseline(repo)  # second call
        assert state["agent_docs"] == "already_hidden"

    def test_hook_uninstalled(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        from pensieve.hooks import install_hook
        install_hook(repo)
        assert (repo / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()

        setup_baseline(repo)
        assert not (repo / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()


# ---------------------------------------------------------------------------
# teardown_baseline
# ---------------------------------------------------------------------------


class TestTeardownBaseline:

    def test_restores_agent_docs(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        state = setup_baseline(repo)
        assert not (repo / "agent-docs").exists()

        teardown_baseline(repo, state)
        assert (repo / "agent-docs").exists()
        assert not (repo / ".agent-docs-hidden").exists()

    def test_no_op_if_not_hidden(self, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        state = {"agent_docs": "not_present"}
        teardown_baseline(repo, state)  # should not crash


# ---------------------------------------------------------------------------
# setup_framework
# ---------------------------------------------------------------------------


class TestSetupFramework:

    def test_installs_hook(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        state = setup_framework(repo)

        assert (repo / ".claude" / "hooks" / "pensieve-pretooluse.sh").exists()
        assert state["hook"] in ("created", "merged", "already_registered")

    def test_scan_already_done(self, tmp_path):
        repo = _make_scanned_repo(tmp_path)
        state = setup_framework(repo)
        assert state["scan"] == "already_present"

    def test_scan_runs_if_needed(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("def hello(): pass\n")
        # No scan done yet

        state = setup_framework(repo)
        assert state["scan"] == "ran"
        assert (repo / "agent-docs" / "structure.json").exists()


# ---------------------------------------------------------------------------
# run_benchmark
# ---------------------------------------------------------------------------


class TestRunBenchmark:

    def test_runs_both_modes(self, tmp_path):
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()
        templates = get_all_templates()

        result = run_benchmark(repo, templates, executor)

        assert isinstance(result, BenchmarkResult)
        assert len(result.baseline_results) == 5
        assert len(result.framework_results) == 5
        assert all(r.mode == "baseline" for r in result.baseline_results)
        assert all(r.mode == "with_framework" for r in result.framework_results)
        assert result.total_time_seconds > 0

    def test_baseline_only(self, tmp_path):
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()

        result = run_benchmark(
            repo, get_all_templates(), executor,
            run_baseline=True, run_framework=False,
        )
        assert len(result.baseline_results) == 5
        assert len(result.framework_results) == 0

    def test_framework_only(self, tmp_path):
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()

        result = run_benchmark(
            repo, get_all_templates(), executor,
            run_baseline=False, run_framework=True,
        )
        assert len(result.baseline_results) == 0
        assert len(result.framework_results) == 5

    def test_agent_docs_restored_after_baseline(self, tmp_path):
        """After running both modes, agent-docs should be back."""
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()

        run_benchmark(repo, get_all_templates(), executor)

        assert (repo / "agent-docs").exists()
        assert (repo / "agent-docs" / "structure.json").exists()

    def test_no_errors_in_results(self, tmp_path):
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()

        result = run_benchmark(repo, get_all_templates(), executor)

        for r in result.baseline_results + result.framework_results:
            assert r.error is None, f"Task '{r.template_name}' ({r.mode}) error: {r.error}"

    def test_executor_receives_different_modes(self, tmp_path):
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path)
        executor = MockExecutor()

        run_benchmark(repo, get_all_templates(), executor)

        modes = {c["mode"] for c in executor.calls}
        assert "baseline" in modes
        assert "with_framework" in modes

    def test_unsanned_repo_gets_scanned(self, tmp_path):
        """run_benchmark on a repo without structure.json runs scan first."""
        from pensieve.benchmark.tasks import get_all_templates

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("def f(): pass\n")

        executor = MockExecutor()
        result = run_benchmark(repo, get_all_templates(), executor)

        assert (repo / "agent-docs" / "structure.json").exists()
        assert len(result.framework_results) == 5
