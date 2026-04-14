"""Regression tests for A8/A9 review findings.

Finding 1: PLAN.md contract (documentation fix, not tested here)
Finding 2: Mode isolation — framework mutations don't leak into baseline
Finding 3: Test-dir exclusion from placeholder heuristics
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.benchmark.runner import (
    PlaceholderFiller,
    run_benchmark,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scanned_repo(tmp_path, files_dict):
    """Create a repo with given files and run pensieve scan."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel_path, content in files_dict.items():
        f = repo / rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    from pensieve.scan import scan_repo
    scan_repo(repo)
    return repo


class MutatingExecutor:
    """Executor that writes a file to the repo during execution,
    simulating an agent that modifies the working tree."""

    def __init__(self):
        self.calls = []

    def execute(self, instruction, repo_root, mode):
        self.calls.append({"mode": mode, "repo_root": str(repo_root)})
        # Mutate the repo
        marker = repo_root / f"mutated_by_{mode}.txt"
        marker.write_text(f"Written during {mode} run")
        return {"response": "done", "tokens": 50, "cost_usd": 0.005, "time_seconds": 0.1}


class CleanExecutor:
    def execute(self, instruction, repo_root, mode):
        return {"response": "done", "tokens": 50, "cost_usd": 0.005, "time_seconds": 0.1}


# ---------------------------------------------------------------------------
# Finding 2: Mode isolation
# ---------------------------------------------------------------------------


class TestModeIsolation:

    def test_framework_mutations_not_in_baseline(self, tmp_path):
        """Files created during framework mode should NOT exist during
        baseline mode. Each mode runs on a fresh copy."""
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path, {
            "main.py": "def hello(): pass\n",
        })

        executor = MutatingExecutor()
        result = run_benchmark(repo, get_all_templates()[:1], executor)

        # Both modes should have run
        assert len(result.framework_results) == 1
        assert len(result.baseline_results) == 1

        # The executor was called in both modes
        modes = [c["mode"] for c in executor.calls]
        assert "with_framework" in modes
        assert "baseline" in modes

        # Crucially: each call should have used a DIFFERENT repo path
        paths = [c["repo_root"] for c in executor.calls]
        assert paths[0] != paths[1], (
            "Both modes used the same repo path — no isolation"
        )

    def test_original_repo_not_modified(self, tmp_path):
        """The original repo should be untouched after the benchmark."""
        from pensieve.benchmark.tasks import get_all_templates

        repo = _make_scanned_repo(tmp_path, {
            "main.py": "def hello(): pass\n",
        })

        # Record original state
        original_files = set()
        for f in repo.rglob("*"):
            if f.is_file():
                original_files.add(str(f.relative_to(repo)))

        executor = MutatingExecutor()
        run_benchmark(repo, get_all_templates()[:1], executor)

        # Check no new files in the original repo
        current_files = set()
        for f in repo.rglob("*"):
            if f.is_file():
                current_files.add(str(f.relative_to(repo)))

        # agent-docs/ may have been created by auto-scan, that's expected
        new_files = current_files - original_files
        mutation_files = {f for f in new_files if "mutated_by" in f}
        assert len(mutation_files) == 0, (
            f"Original repo was modified: {mutation_files}"
        )


# ---------------------------------------------------------------------------
# Finding 3: Test-dir exclusion from heuristics
# ---------------------------------------------------------------------------


class TestTestDirExclusion:

    def test_test_heavy_repo_picks_source_dir(self, tmp_path):
        """A repo with more test files than source files should still
        pick a source directory for pattern/subsystem, not tests/."""
        repo = _make_scanned_repo(tmp_path, {
            "src/main.py": "def main(): pass\n",
            "tests/test_a.py": "def test_a(): pass\n",
            "tests/test_b.py": "def test_b(): pass\n",
            "tests/test_c.py": "def test_c(): pass\n",
        })

        filler = PlaceholderFiller(repo)
        values = filler.values

        # Pattern directory should be src, not tests
        assert "test" not in values["pattern_directory"].lower(), (
            f"pattern_directory is '{values['pattern_directory']}' — should be a source dir"
        )
        assert "test" not in values["subsystem_name"].lower(), (
            f"subsystem_name is '{values['subsystem_name']}' — should be a source dir"
        )

    def test_all_test_repo_fallback(self, tmp_path):
        """If ALL files are in test dirs, fallback to using them."""
        repo = _make_scanned_repo(tmp_path, {
            "tests/test_a.py": "def test_a(): pass\n",
            "tests/test_b.py": "def test_b(): pass\n",
        })

        filler = PlaceholderFiller(repo)
        # Should not crash — falls back to test dirs
        assert filler.values["pattern_directory"] is not None

    def test_root_source_files_preferred(self, tmp_path):
        """Source files at repo root should be preferred over test dirs."""
        repo = _make_scanned_repo(tmp_path, {
            "main.py": "def main(): pass\n",
            "utils.py": "def helper(): pass\n",
            "tests/test_main.py": "def test_main(): pass\n",
        })

        filler = PlaceholderFiller(repo)
        assert "test" not in filler.values["pattern_directory"].lower()
