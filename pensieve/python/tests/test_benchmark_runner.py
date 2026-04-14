"""Tests for the benchmark runner (milestone A8).

Covers:
  - PlaceholderFiller: loads structure.json, fills templates
  - Strict checker execution: file_exists, content_contains, symbol_exists
  - run_task: orchestrates fill → execute → check
  - Error cases: missing structure.json, unfillable placeholder, executor failure
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.benchmark.runner import (
    PlaceholderFiller,
    TaskResult,
    run_strict_check,
    run_task,
)
from pensieve.benchmark.template import CheckerSpec, TaskTemplate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo_with_structure(tmp_path, files_data=None):
    """Create a fake repo with structure.json."""
    repo = tmp_path / "repo"
    repo.mkdir()
    agent_docs = repo / "agent-docs"
    agent_docs.mkdir()

    if files_data is None:
        files_data = [
            {
                "file_path": "src/main.py",
                "language": "python",
                "sha256": "abc",
                "file_size_bytes": 100,
                "line_count": 10,
                "symbols": [
                    {"name": "main", "kind": "function", "line_start": 1,
                     "line_end": 5, "signature": "def main():",
                     "visibility": "public", "parent": None,
                     "docstring": None, "parameters": [], "return_type": None},
                    {"name": "helper", "kind": "function", "line_start": 7,
                     "line_end": 10, "signature": "def helper():",
                     "visibility": "public", "parent": None,
                     "docstring": None, "parameters": [], "return_type": None},
                ],
                "imports": [],
                "exports": [],
                "call_edges": [],
                "rationale_comments": [],
                "extraction_errors": [],
                "extractor_version": "test",
            },
            {
                "file_path": "tests/test_main.py",
                "language": "python",
                "sha256": "def",
                "file_size_bytes": 50,
                "line_count": 5,
                "symbols": [
                    {"name": "test_main", "kind": "function", "line_start": 1,
                     "line_end": 3, "signature": "def test_main():",
                     "visibility": "public", "parent": None,
                     "docstring": None, "parameters": [], "return_type": None},
                ],
                "imports": [],
                "exports": [],
                "call_edges": [],
                "rationale_comments": [],
                "extraction_errors": [],
                "extractor_version": "test",
            },
        ]

    structure = {
        "version": "0.0.1",
        "repo_root": str(repo),
        "scan_stats": {"total_files": len(files_data)},
        "files": files_data,
        "errors": [],
    }
    (agent_docs / "structure.json").write_text(json.dumps(structure))
    return repo


class MockExecutor:
    """Mock executor that returns a canned response."""

    def __init__(self, response="I created the file.", tokens=100, cost=0.01):
        self.response = response
        self.tokens = tokens
        self.cost = cost
        self.calls: list[dict] = []

    def execute(self, instruction, repo_root, mode):
        self.calls.append({
            "instruction": instruction,
            "repo_root": repo_root,
            "mode": mode,
        })
        return {
            "response": self.response,
            "tokens": self.tokens,
            "cost_usd": self.cost,
            "time_seconds": 0.5,
        }


class FailingExecutor:
    def execute(self, instruction, repo_root, mode):
        raise RuntimeError("Agent crashed")


# ---------------------------------------------------------------------------
# PlaceholderFiller
# ---------------------------------------------------------------------------


class TestPlaceholderFiller:

    def test_loads_from_structure_json(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        filler = PlaceholderFiller(repo)
        values = filler.values
        assert "file_path" in values
        assert "function_name" in values
        assert "most_common_pattern" in values
        assert "repo_description" in values

    def test_fills_instruction(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        filler = PlaceholderFiller(repo)
        filled = filler.fill("Fix the function '{function_name}' in '{file_path}'")
        assert "{" not in filled  # no unfilled placeholders
        assert "main" in filled or "helper" in filled

    def test_missing_structure_json_raises(self, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        with pytest.raises(FileNotFoundError, match="structure.json"):
            PlaceholderFiller(repo)

    def test_empty_files_raises(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path, files_data=[])
        with pytest.raises(ValueError, match="no files"):
            PlaceholderFiller(repo)

    def test_unfillable_placeholder_raises(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        filler = PlaceholderFiller(repo)
        with pytest.raises(KeyError, match="nonexistent_field"):
            filler.fill("This needs {nonexistent_field}")

    def test_all_documented_placeholders_fillable(self, tmp_path):
        """Every placeholder in DOCUMENTED_PLACEHOLDERS should be fillable."""
        from pensieve.benchmark.tasks import DOCUMENTED_PLACEHOLDERS
        repo = _make_repo_with_structure(tmp_path)
        filler = PlaceholderFiller(repo)
        for ph in DOCUMENTED_PLACEHOLDERS:
            assert ph in filler.values, f"Placeholder '{ph}' not in filler values"

    def test_fill_template(self, tmp_path):
        from pensieve.benchmark.tasks import ADD_HANDLER
        repo = _make_repo_with_structure(tmp_path)
        filler = PlaceholderFiller(repo)
        filled = filler.fill_template(ADD_HANDLER)
        assert "{" not in filled


# ---------------------------------------------------------------------------
# Strict checker execution
# ---------------------------------------------------------------------------


class TestStrictChecker:

    def test_file_exists_pass(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "output.py").write_text("x = 1")

        checker = CheckerSpec(
            checker_type="file_exists",
            criteria="test",
            target_file="output.py",
        )
        assert run_strict_check(checker, repo, "", {}) is True

    def test_file_exists_fail(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()

        checker = CheckerSpec(
            checker_type="file_exists",
            criteria="test",
            target_file="missing.py",
        )
        assert run_strict_check(checker, repo, "", {}) is False

    def test_content_contains_in_response(self, tmp_path):
        checker = CheckerSpec(
            checker_type="content_contains",
            criteria="test",
            target_string="auth_service",
        )
        assert run_strict_check(
            checker, tmp_path, "The auth_service module handles login.", {}
        ) is True

    def test_content_contains_in_file(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "out.py").write_text("def auth_service(): pass")

        checker = CheckerSpec(
            checker_type="content_contains",
            criteria="test",
            target_string="auth_service",
            target_file="out.py",
        )
        assert run_strict_check(checker, repo, "", {}) is True

    def test_content_contains_fail(self, tmp_path):
        checker = CheckerSpec(
            checker_type="content_contains",
            criteria="test",
            target_string="not_found_anywhere",
        )
        assert run_strict_check(checker, tmp_path, "nothing here", {}) is False

    def test_symbol_exists_pass(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("def hello():\n    pass\n")

        checker = CheckerSpec(
            checker_type="symbol_exists",
            criteria="test",
            target_file="main.py",
            target_symbol="hello",
        )
        assert run_strict_check(checker, repo, "", {}) is True

    def test_symbol_exists_fail(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("def other():\n    pass\n")

        checker = CheckerSpec(
            checker_type="symbol_exists",
            criteria="test",
            target_file="main.py",
            target_symbol="hello",
        )
        assert run_strict_check(checker, repo, "", {}) is False

    def test_placeholder_resolution_in_checker(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "handler.py").write_text("x = 1")

        checker = CheckerSpec(
            checker_type="file_exists",
            criteria="test",
            target_file="{output_dir}/handler.py",
        )
        assert run_strict_check(
            checker, repo, "", {"output_dir": "src"}
        ) is True


# ---------------------------------------------------------------------------
# run_task
# ---------------------------------------------------------------------------


class TestRunTask:

    def _make_template(self):
        return TaskTemplate(
            name="test_task",
            task_type="add_handler",
            difficulty="easy",
            description="test",
            instruction="Create a file at '{file_path}'",
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria="test",
                target_string="created",
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria="test",
                llm_prompt="test",
            ),
        )

    def test_successful_run(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        executor = MockExecutor(response="I created the file.")
        template = self._make_template()

        result = run_task(
            template, repo, executor, "baseline",
            placeholder_values=PlaceholderFiller(repo).values,
        )

        assert isinstance(result, TaskResult)
        assert result.template_name == "test_task"
        assert result.mode == "baseline"
        assert result.error is None
        assert result.tokens_used == 100
        assert result.strict_pass is True  # "created" in response
        assert result.agent_response == "I created the file."

    def test_executor_failure_recorded(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        executor = FailingExecutor()
        template = self._make_template()

        result = run_task(
            template, repo, executor, "baseline",
            placeholder_values=PlaceholderFiller(repo).values,
        )

        assert result.error is not None
        assert "crashed" in result.error.lower()

    def test_executor_receives_correct_mode(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        executor = MockExecutor()
        template = self._make_template()

        run_task(
            template, repo, executor, "with_framework",
            placeholder_values=PlaceholderFiller(repo).values,
        )

        assert executor.calls[0]["mode"] == "with_framework"

    def test_filled_instruction_sent_to_executor(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        executor = MockExecutor()
        template = self._make_template()

        run_task(
            template, repo, executor, "baseline",
            placeholder_values=PlaceholderFiller(repo).values,
        )

        sent = executor.calls[0]["instruction"]
        assert "{" not in sent  # no unfilled placeholders

    def test_strict_check_fail_recorded(self, tmp_path):
        repo = _make_repo_with_structure(tmp_path)
        executor = MockExecutor(response="nothing relevant")
        template = self._make_template()

        result = run_task(
            template, repo, executor, "baseline",
            placeholder_values=PlaceholderFiller(repo).values,
        )

        assert result.strict_pass is False


# ---------------------------------------------------------------------------
# Integration with real templates
# ---------------------------------------------------------------------------


class TestIntegrationWithRealTemplates:

    def test_all_templates_fillable_and_runnable(self, tmp_path):
        """All 5 task templates should fill and run without errors
        against a valid repo structure."""
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_repo_with_structure(tmp_path)
        executor = MockExecutor()
        filler = PlaceholderFiller(repo)

        for template in get_all_templates():
            result = run_task(
                template, repo, executor, "baseline",
                placeholder_values=filler.values,
            )
            assert result.error is None, (
                f"Template '{template.name}' failed: {result.error}"
            )
            assert result.agent_response != ""
            assert result.tokens_used > 0
