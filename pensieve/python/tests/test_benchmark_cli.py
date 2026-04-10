"""Tests for the benchmark CLI subcommand (A13 rework).

Covers:
  - Parser wiring: benchmark generate/run recognized, flags parsed
  - benchmark generate: produces generated-tasks.json
  - benchmark run: generates then runs by default, or loads from file
  - --dev mode limits tasks
  - --judge flag
  - Error handling: nonexistent repo, no structure.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

from pensieve.cli import main


@pytest.fixture(autouse=True)
def _mock_judge(monkeypatch):
    """Prevent CLI tests from making real Claude Code calls for judging."""
    from pensieve.benchmark import judge as judge_mod

    def _fake_judge(llm_prompt, agent_response, model="sonnet", timeout_seconds=60):
        return judge_mod.JudgeResult(
            lenient_pass=False,
            quality_score=5.0,
            reasoning="mocked",
        )

    monkeypatch.setattr(judge_mod, "judge_task", _fake_judge)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo_with_context(tmp_path):
    """Create a repo with structure.json + graph.json for benchmark tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    agent_docs = repo / "agent-docs"
    agent_docs.mkdir()

    # Create source files for pattern detection and task generation
    src = repo / "src" / "handlers"
    src.mkdir(parents=True)
    for name in ("users.py", "posts.py", "comments.py"):
        (src / name).write_text(
            f"def get_{name.replace('.py', '')}():\n"
            f"    x = 1\n"
            f"    if x <= 10:\n"
            f"        return True\n"
            f"    return False\n"
            f"\n"
            f"def create_{name.replace('.py', '')}():\n"
            f"    pass\n"
        )

    utils = repo / "src" / "utils"
    utils.mkdir(parents=True)
    (utils / "auth.py").write_text("def verify():\n    pass\n")
    (utils / "helpers.py").write_text("def paginate():\n    pass\n")

    files_data = [
        {
            "file_path": f"src/handlers/{name}",
            "language": "python",
            "symbols": [
                {"name": f"get_{name.replace('.py', '')}", "kind": "function",
                 "line_start": 1, "line_end": 5,
                 "signature": f"def get_{name.replace('.py', '')}():",
                 "visibility": "public", "parent": None,
                 "docstring": None, "parameters": [], "return_type": None},
                {"name": f"create_{name.replace('.py', '')}", "kind": "function",
                 "line_start": 7, "line_end": 8,
                 "signature": f"def create_{name.replace('.py', '')}():",
                 "visibility": "public", "parent": None,
                 "docstring": None, "parameters": [], "return_type": None},
            ],
            "imports": [], "exports": [], "call_edges": [], "comments": [],
        }
        for name in ("users.py", "posts.py", "comments.py")
    ] + [
        {
            "file_path": f"src/utils/{name}",
            "language": "python",
            "symbols": [
                {"name": name.replace(".py", ""), "kind": "function",
                 "line_start": 1, "line_end": 2,
                 "signature": f"def {name.replace('.py', '')}():",
                 "visibility": "public", "parent": None,
                 "docstring": None, "parameters": [], "return_type": None},
            ],
            "imports": [], "exports": [], "call_edges": [], "comments": [],
        }
        for name in ("auth.py", "helpers.py")
    ]

    structure = {
        "repo_root": str(repo),
        "files": files_data,
        "errors": [],
        "extractor_version": "test",
    }
    (agent_docs / "structure.json").write_text(json.dumps(structure))

    edges = [
        {"source": "src/handlers/users.py", "target": "src/utils/auth.py",
         "kind": "imports", "detail": "", "line": 1, "confidence": 1.0},
        {"source": "src/handlers/posts.py", "target": "src/utils/auth.py",
         "kind": "imports", "detail": "", "line": 1, "confidence": 1.0},
        {"source": "src/handlers/comments.py", "target": "src/utils/auth.py",
         "kind": "imports", "detail": "", "line": 1, "confidence": 1.0},
    ]
    graph = {"nodes": [], "edges": edges, "external_imports": []}
    (agent_docs / "graph.json").write_text(json.dumps(graph))

    return repo


class _MockExecutor:
    def execute(self, instruction, repo_root, mode):
        return {
            "response": "done",
            "tokens": 500,
            "cost_usd": 0.05,
            "time_seconds": 1.0,
        }


# ---------------------------------------------------------------------------
# Parser wiring
# ---------------------------------------------------------------------------


class TestBenchmarkParser:

    def test_benchmark_no_action_exits_nonzero(self, capsys):
        result = main(["benchmark"])
        assert result == 1
        captured = capsys.readouterr()
        assert "specify" in captured.err.lower()

    def test_benchmark_generate_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["benchmark", "generate", "--help"])
        assert exc_info.value.code == 0

    def test_benchmark_run_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["benchmark", "run", "--help"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# benchmark generate
# ---------------------------------------------------------------------------


class TestBenchmarkGenerate:

    def test_generates_tasks_file(self, tmp_path):
        repo = _make_repo_with_context(tmp_path)
        result = main(["benchmark", "generate", "--repo", str(repo)])
        assert result == 0
        tasks_file = repo / "agent-docs" / "generated-tasks.json"
        assert tasks_file.exists()
        data = json.loads(tasks_file.read_text())
        assert data["task_count"] > 0
        assert "tasks" in data

    def test_custom_output_path(self, tmp_path):
        repo = _make_repo_with_context(tmp_path)
        out = tmp_path / "custom" / "tasks.json"
        result = main([
            "benchmark", "generate",
            "--repo", str(repo),
            "--output", str(out),
        ])
        assert result == 0
        assert out.exists()

    def test_max_limits(self, tmp_path):
        repo = _make_repo_with_context(tmp_path)
        result = main([
            "benchmark", "generate",
            "--repo", str(repo),
            "--max-easy", "1", "--max-medium", "0", "--max-hard", "0",
        ])
        assert result == 0
        tasks_file = repo / "agent-docs" / "generated-tasks.json"
        data = json.loads(tasks_file.read_text())
        assert data["task_count"] <= 1

    def test_no_structure_json_fails(self, capsys, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        result = main(["benchmark", "generate", "--repo", str(repo)])
        assert result == 1
        captured = capsys.readouterr()
        assert "structure.json" in captured.err

    def test_nonexistent_repo_fails(self, capsys, tmp_path):
        bad = str(tmp_path / "nope")
        result = main(["benchmark", "generate", "--repo", bad])
        assert result == 1
        assert "not a directory" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# benchmark run
# ---------------------------------------------------------------------------


class TestBenchmarkRun:

    def _run_with_mock(self, tmp_path, extra_args=None):
        repo = _make_repo_with_context(tmp_path)
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        argv = ["benchmark", "run", "--repo", str(repo)]
        if extra_args:
            argv.extend(extra_args)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main(argv)

        return result, repo

    def test_run_generates_and_executes(self, tmp_path):
        result, repo = self._run_with_mock(tmp_path)
        assert result == 0
        # Should have generated tasks
        assert (repo / "agent-docs" / "generated-tasks.json").exists()
        # Should have run and produced benchmark.json
        assert (repo / "agent-docs" / "benchmark.json").exists()
        assert (repo / "agent-docs" / "benchmark-history.md").exists()

    def test_dev_mode_limits_tasks(self, capsys, tmp_path):
        result, repo = self._run_with_mock(tmp_path, ["--dev"])
        assert result == 0
        captured = capsys.readouterr()
        # Dev mode: 1 easy task
        assert "easy=1" in captured.out

    def test_run_from_tasks_file(self, tmp_path):
        repo = _make_repo_with_context(tmp_path)
        # First generate
        main(["benchmark", "generate", "--repo", str(repo), "--max-easy", "1", "--max-medium", "0", "--max-hard", "0"])
        tasks_file = repo / "agent-docs" / "generated-tasks.json"
        assert tasks_file.exists()

        # Then run from file
        mock_executor = _MockExecutor()
        mock_module = mock.MagicMock()
        mock_module.create_executor = mock.MagicMock(return_value=mock_executor)

        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": mock_module}):
            result = main([
                "benchmark", "run",
                "--repo", str(repo),
                "--tasks-file", str(tasks_file),
            ])
        assert result == 0

    def test_no_executor_gives_clear_error(self, capsys, tmp_path):
        repo = _make_repo_with_context(tmp_path)
        with mock.patch.dict(sys.modules, {"pensieve.benchmark.executor": None}):
            result = main(["benchmark", "run", "--repo", str(repo)])
        assert result == 1
        assert "no executor" in capsys.readouterr().err.lower()

    def test_summary_printed(self, capsys, tmp_path):
        result, _ = self._run_with_mock(tmp_path)
        assert result == 0
        captured = capsys.readouterr()
        assert "Verdict:" in captured.out
        assert "Cost:" in captured.out

    def test_judge_off_by_default(self, capsys, tmp_path):
        """Judge should not run unless --judge is passed."""
        result, repo = self._run_with_mock(tmp_path)
        assert result == 0
        # Check benchmark.json — quality should be 0.0 (no judge)
        data = json.loads((repo / "agent-docs" / "benchmark.json").read_text())
        # Without judge, quality_avg should be 0.0
        assert data["with_framework"]["quality_avg"] == 0.0
