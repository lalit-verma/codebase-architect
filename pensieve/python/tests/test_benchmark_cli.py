"""Tests for the benchmark CLI subcommand (milestone A12).

Covers:
  - Parser wiring: `benchmark run` recognized, flags parsed
  - No action: `benchmark` alone prints error
  - Unknown template name rejected with available list
  - Nonexistent repo directory rejected
  - Mode flags: neither → both, --baseline → only baseline, --with-framework → only framework
  - No executor: clear error message when executor module missing
  - Full integration with mock executor: benchmark.json + benchmark-history.md written
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

from pensieve.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo_with_structure(tmp_path, files_data=None):
    """Create a fake repo with structure.json for benchmark tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    agent_docs = repo / "agent-docs"
    agent_docs.mkdir()

    if files_data is None:
        files_data = [
            {
                "file_path": "src/main.py",
                "language": "python",
                "sha256": "abc123",
                "file_size_bytes": 100,
                "line_count": 10,
                "symbols": [
                    {
                        "name": "main",
                        "kind": "function",
                        "line_start": 1,
                        "line_end": 5,
                        "signature": "def main():",
                        "visibility": "public",
                        "parent": None,
                        "docstring": None,
                        "parameters": [],
                        "return_type": None,
                    },
                ],
                "imports": [],
                "exports": [],
                "call_edges": [],
                "comments": [],
            },
        ]

    structure = {
        "repo_root": str(repo),
        "files": files_data,
        "errors": [],
        "extractor_version": "test",
    }
    (agent_docs / "structure.json").write_text(
        json.dumps(structure), encoding="utf-8",
    )

    # Create the source file so file_exists checks can pass
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass\n")

    return repo


class _MockExecutor:
    """Mock executor that returns canned responses."""

    def __init__(self, response="done", tokens=500, cost=0.05, time_s=1.0):
        self._response = response
        self._tokens = tokens
        self._cost = cost
        self._time = time_s

    def execute(self, instruction, repo_root, mode):
        return {
            "response": self._response,
            "tokens": self._tokens,
            "cost_usd": self._cost,
            "time_seconds": self._time,
        }


# ---------------------------------------------------------------------------
# Parser wiring
# ---------------------------------------------------------------------------


class TestBenchmarkParser:

    def test_benchmark_no_action_exits_nonzero(self, capsys):
        """'pensieve benchmark' with no action prints error."""
        result = main(["benchmark"])
        assert result == 1
        captured = capsys.readouterr()
        assert "specify" in captured.err.lower()

    def test_benchmark_run_help(self, capsys):
        """'pensieve benchmark run --help' exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["benchmark", "run", "--help"])
        assert exc_info.value.code == 0

    def test_benchmark_listed_in_top_help(self, capsys):
        """'pensieve --help' mentions the benchmark command."""
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "benchmark" in captured.out.lower()


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestBenchmarkArgValidation:

    def test_nonexistent_repo_fails(self, capsys, tmp_path):
        bad_path = str(tmp_path / "nonexistent")
        result = main(["benchmark", "run", "--repo", bad_path])
        assert result == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err

    def test_unknown_template_name_fails(self, capsys, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        # Patch executor import to not fail before template resolution
        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": None}):
            result = main([
                "benchmark", "run",
                "--repo", str(repo),
                "--tasks", "nonexistent_template",
            ])
        assert result == 1
        captured = capsys.readouterr()
        assert "unknown template" in captured.err.lower()
        # Should list available templates
        assert "add_handler" in captured.err

    def test_empty_tasks_after_strip_fails(self, capsys, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": None}):
            result = main([
                "benchmark", "run",
                "--repo", str(repo),
                "--tasks", " , , ",
            ])
        assert result == 1
        captured = capsys.readouterr()
        assert "no templates" in captured.err.lower()


# ---------------------------------------------------------------------------
# No executor
# ---------------------------------------------------------------------------


class TestNoExecutor:

    def test_missing_executor_module_gives_clear_error(self, capsys, tmp_path):
        """When pensieve.benchmark.executor doesn't exist, the CLI
        should print a helpful message, not a traceback."""
        repo = _make_repo_with_structure(tmp_path)
        result = main(["benchmark", "run", "--repo", str(repo)])
        assert result == 1
        captured = capsys.readouterr()
        assert "no executor" in captured.err.lower()
        assert "a13" in captured.err.lower()  # mentions where it'll be built


# ---------------------------------------------------------------------------
# Mode flag logic
# ---------------------------------------------------------------------------


class TestModeFlags:

    def _run_with_mock_executor(self, tmp_path, extra_args=None):
        """Helper: run benchmark with a mock executor and capture the
        run_benchmark call to inspect which modes were requested."""
        repo = _make_repo_with_structure(tmp_path)

        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        captured_kwargs = {}

        original_run = None
        from pensieve.benchmark import runner as runner_mod
        original_run = runner_mod.run_benchmark

        def patched_run(**kwargs):
            captured_kwargs.update(kwargs)
            return original_run(**kwargs)

        argv = ["benchmark", "run", "--repo", str(repo)]
        if extra_args:
            argv.extend(extra_args)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            with mock.patch("pensieve.benchmark.runner.run_benchmark", side_effect=patched_run):
                result = main(argv)

        return result, captured_kwargs

    def test_no_flags_runs_both(self, tmp_path):
        """Neither --baseline nor --with-framework → both modes run."""
        result, kwargs = self._run_with_mock_executor(tmp_path)
        assert result == 0
        assert kwargs["run_baseline"] is True
        assert kwargs["run_framework"] is True

    def test_baseline_only_rejected(self, capsys, tmp_path):
        """--baseline alone is rejected because comparative artifacts
        (benchmark.json, benchmark-history.md) need both modes."""
        repo = _make_repo_with_structure(tmp_path)
        result = main(["benchmark", "run", "--repo", str(repo), "--baseline"])
        assert result == 1
        captured = capsys.readouterr()
        assert "comparison requires both modes" in captured.err.lower()
        assert "--with-framework" in captured.err

    def test_framework_only_rejected(self, capsys, tmp_path):
        """--with-framework alone is rejected for the same reason."""
        repo = _make_repo_with_structure(tmp_path)
        result = main(["benchmark", "run", "--repo", str(repo), "--with-framework"])
        assert result == 1
        captured = capsys.readouterr()
        assert "comparison requires both modes" in captured.err.lower()
        assert "--baseline" in captured.err

    def test_both_flags_explicit(self, tmp_path):
        result, kwargs = self._run_with_mock_executor(
            tmp_path, ["--baseline", "--with-framework"],
        )
        assert result == 0
        assert kwargs["run_baseline"] is True
        assert kwargs["run_framework"] is True


# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------


class TestTemplateSelection:

    def test_all_selects_every_template(self, tmp_path):
        """--tasks all should select all registered templates."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        captured_templates = []

        from pensieve.benchmark import runner as runner_mod
        original_run = runner_mod.run_benchmark

        def patched_run(**kwargs):
            captured_templates.extend(kwargs["templates"])
            return original_run(**kwargs)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            with mock.patch("pensieve.benchmark.runner.run_benchmark", side_effect=patched_run):
                result = main(["benchmark", "run", "--repo", str(repo)])

        assert result == 0
        from pensieve.benchmark.tasks import get_all_templates
        assert len(captured_templates) == len(get_all_templates())

    def test_specific_template_names(self, tmp_path):
        """--tasks add_handler,add_test selects exactly those two."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        captured_templates = []

        from pensieve.benchmark import runner as runner_mod
        original_run = runner_mod.run_benchmark

        def patched_run(**kwargs):
            captured_templates.extend(kwargs["templates"])
            return original_run(**kwargs)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            with mock.patch("pensieve.benchmark.runner.run_benchmark", side_effect=patched_run):
                result = main([
                    "benchmark", "run",
                    "--repo", str(repo),
                    "--tasks", "add_handler,add_test",
                ])

        assert result == 0
        assert len(captured_templates) == 2
        names = [t.name for t in captured_templates]
        assert names == ["add_handler", "add_test"]


# ---------------------------------------------------------------------------
# Full integration: outputs written
# ---------------------------------------------------------------------------


class TestBenchmarkOutputs:

    def test_benchmark_json_written(self, tmp_path):
        """A successful run writes benchmark.json."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main(["benchmark", "run", "--repo", str(repo)])

        assert result == 0
        json_path = repo / "agent-docs" / "benchmark.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "verdict" in data
        assert "deltas" in data
        assert "with_framework" in data
        assert "baseline" in data

    def test_benchmark_history_written(self, tmp_path):
        """A successful run writes benchmark-history.md."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main(["benchmark", "run", "--repo", str(repo)])

        assert result == 0
        history_path = repo / "agent-docs" / "benchmark-history.md"
        assert history_path.exists()
        content = history_path.read_text()
        assert "Benchmark History" in content

    def test_custom_output_dir(self, tmp_path):
        """--output-dir writes outputs to the specified directory."""
        repo = _make_repo_with_structure(tmp_path)
        out_dir = tmp_path / "custom_output"

        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main([
                "benchmark", "run",
                "--repo", str(repo),
                "--output-dir", str(out_dir),
            ])

        assert result == 0
        assert (out_dir / "benchmark.json").exists()
        assert (out_dir / "benchmark-history.md").exists()

    def test_summary_printed(self, capsys, tmp_path):
        """A successful run prints the verdict summary."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main(["benchmark", "run", "--repo", str(repo)])

        assert result == 0
        captured = capsys.readouterr()
        assert "Verdict:" in captured.out
        assert "Cost:" in captured.out
        assert "Lenient:" in captured.out

    def test_second_run_appends_history(self, tmp_path):
        """Running twice appends a second row to benchmark-history.md."""
        repo = _make_repo_with_structure(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        for _ in range(2):
            with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
                result = main(["benchmark", "run", "--repo", str(repo)])
            assert result == 0

        history = (repo / "agent-docs" / "benchmark-history.md").read_text()
        # Header once, two data rows
        assert history.count("Benchmark History") == 1
        pipe_lines = [
            l for l in history.split("\n")
            if l.startswith("|") and "Date" not in l and "---" not in l
        ]
        assert len(pipe_lines) == 2
