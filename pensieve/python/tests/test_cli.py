"""Smoke tests for the pensieve CLI scaffolding (milestone A2).

These tests verify the CLI is wired correctly: --version prints the
version, --help prints usage, no-args prints help, and the package is
invokable both as `pensieve` (console script) and `python -m pensieve`.

As subcommands land in A3+, this file will get split into per-command
test modules.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pensieve import __version__
from pensieve.cli import main


class TestVersion:
    """Verify version handling."""

    def test_version_constant_set(self):
        """The package version constant exists and is a non-empty string."""
        assert __version__
        assert isinstance(__version__, str)
        # Version should look like SemVer-ish (digits and dots)
        assert all(part.isdigit() for part in __version__.split("."))

    def test_version_flag_exits_zero(self, capsys):
        """`pensieve --version` prints version and exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # argparse prints --version output to stdout
        assert __version__ in captured.out
        assert "code-pensieve" in captured.out


class TestHelp:
    """Verify help output."""

    def test_no_args_prints_help_and_exits_zero(self, capsys):
        """Running `pensieve` with no args prints help and exits 0."""
        result = main([])
        assert result == 0

        captured = capsys.readouterr()
        assert "pensieve" in captured.out.lower()
        assert "usage" in captured.out.lower()

    def test_help_flag_exits_zero(self, capsys):
        """`pensieve --help` exits 0 and shows usage."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()
        assert "code pensieve" in captured.out.lower()

    def test_help_lists_subcommands(self, capsys):
        """Help should list the main subcommands."""
        with pytest.raises(SystemExit):
            main(["--help"])

        captured = capsys.readouterr()
        assert "scan" in captured.out.lower()
        assert "analyze" in captured.out.lower()
        assert "wire" in captured.out.lower()
        assert "benchmark" in captured.out.lower()


class TestUnknownCommand:
    """Verify unknown subcommand handling."""

    def test_unknown_command_exits_nonzero(self, capsys):
        """An unknown subcommand exits non-zero with an error message.

        argparse rejects unknown subcommands at parse time with exit 2,
        which is the expected behavior. We don't need to assert the
        exact code — just that it's not 0.
        """
        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent-subcommand"])
        assert exc_info.value.code != 0


class TestEntryPoint:
    """Verify the package is invokable via the installed entry point.

    These tests require the package to be installed (via `pip install
    -e .`) so that `python -m pensieve` and the `pensieve` console
    script resolve. They run as subprocesses to exercise the real
    entry-point wiring.
    """

    def test_python_dash_m_invocation(self):
        """`python -m pensieve --version` works."""
        result = subprocess.run(
            [sys.executable, "-m", "pensieve", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"python -m pensieve --version failed: {result.stderr}"
        )
        assert __version__ in result.stdout

    def test_python_dash_m_help(self):
        """`python -m pensieve` with no args prints help and exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "pensieve"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Analyze command (B14)
# ---------------------------------------------------------------------------


class TestAnalyzeCommand:

    def test_analyze_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["analyze", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "analyze" in captured.out.lower()

    def test_analyze_listed_in_top_help(self, capsys):
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "analyze" in captured.out.lower()

    def test_nonexistent_repo_fails(self, capsys, tmp_path):
        bad = str(tmp_path / "nope")
        result = main(["analyze", bad])
        assert result == 1
        assert "not a directory" in capsys.readouterr().err

    def test_structure_without_graph_rescans(self, capsys, tmp_path):
        """If structure.json exists but graph.json is missing, analyze
        should rescan instead of crashing with FileNotFoundError."""
        import json as json_mod
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        # Create structure.json but NOT graph.json
        (ad / "structure.json").write_text(json_mod.dumps({
            "repo_root": str(repo), "files": [], "errors": [],
            "extractor_version": "test",
        }))
        # Create a source file so scan has something to find
        (repo / "main.py").write_text("def main(): pass\n")

        # This should NOT crash — it should rescan and then fail
        # at the proposal step (no LLM available in tests), but
        # the point is it doesn't raise FileNotFoundError.
        # We just verify it gets past stage 1 without crashing.
        # It will fail at stage 2 (proposal needs LLM) — that's fine.
        result = main(["analyze", str(repo)])
        # Should have rescanned (graph was missing)
        captured = capsys.readouterr()
        assert "Scanning repo" in captured.out
