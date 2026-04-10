"""Tests for benchmark history generator (milestone A11).

Covers:
  - First run: creates file with header + first row
  - Subsequent run: appends row, preserves header
  - Row content: verdict, deltas, task count
  - Custom timestamp
  - Parent directory creation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pensieve.benchmark.history import append_to_history, _format_row
from pensieve.benchmark.metrics import BenchmarkReport, Deltas, ModeStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(
    verdict: str = "PASS",
    cost_pct: float = -10.0,
    lenient_pp: float = 6.6,
    quality_diff: float = 0.2,
    tokens_pct: float = -5.0,
    time_pct: float = -10.0,
    task_count: int = 5,
) -> BenchmarkReport:
    return BenchmarkReport(
        repo_root="/tmp/repo",
        with_framework=ModeStats(task_count=task_count),
        baseline=ModeStats(task_count=task_count),
        deltas=Deltas(
            cost_pct=cost_pct,
            lenient_pass_pp=lenient_pp,
            quality_diff=quality_diff,
            tokens_pct=tokens_pct,
            time_pct=time_pct,
        ),
        verdict=verdict,
        task_breakdown=[],
        total_time_seconds=30.0,
    )


# ---------------------------------------------------------------------------
# _format_row
# ---------------------------------------------------------------------------


class TestFormatRow:

    def test_contains_verdict(self):
        row = _format_row(_make_report(verdict="PASS"), timestamp="2026-04-10 14:00")
        assert "**PASS**" in row

    def test_contains_deltas(self):
        row = _format_row(
            _make_report(cost_pct=-10.0, lenient_pp=6.6, quality_diff=0.2),
            timestamp="2026-04-10 14:00",
        )
        assert "-10.0%" in row
        assert "+6.6pp" in row
        assert "+0.20" in row

    def test_contains_task_count(self):
        row = _format_row(_make_report(task_count=5), timestamp="2026-04-10 14:00")
        assert "5" in row

    def test_negative_deltas_show_minus(self):
        row = _format_row(
            _make_report(cost_pct=-15.0, lenient_pp=-3.0, quality_diff=-0.5),
            timestamp="2026-04-10 14:00",
        )
        assert "-15.0%" in row
        assert "-3.0pp" in row
        assert "-0.50" in row

    def test_custom_timestamp(self):
        row = _format_row(_make_report(), timestamp="2026-01-01 00:00")
        assert "2026-01-01 00:00" in row


# ---------------------------------------------------------------------------
# append_to_history
# ---------------------------------------------------------------------------


class TestAppendToHistory:

    def test_first_run_creates_file(self, tmp_path):
        path = tmp_path / "benchmark-history.md"
        assert not path.exists()

        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")

        assert path.exists()
        content = path.read_text()
        assert "# Benchmark History" in content
        assert "**PASS**" in content
        assert "2026-04-10 14:00" in content

    def test_second_run_appends(self, tmp_path):
        path = tmp_path / "benchmark-history.md"

        append_to_history(
            _make_report(verdict="PASS"), path, timestamp="2026-04-10 14:00",
        )
        append_to_history(
            _make_report(verdict="MIXED"), path, timestamp="2026-04-11 10:00",
        )

        content = path.read_text()
        # Header should appear only once
        assert content.count("# Benchmark History") == 1
        # Both rows present
        assert "**PASS**" in content
        assert "**MIXED**" in content
        assert "2026-04-10 14:00" in content
        assert "2026-04-11 10:00" in content

    def test_three_runs_show_trend(self, tmp_path):
        path = tmp_path / "benchmark-history.md"

        for i, (v, cost) in enumerate([
            ("FAIL", 11.0),
            ("MIXED", 2.0),
            ("PASS", -10.0),
        ]):
            append_to_history(
                _make_report(verdict=v, cost_pct=cost),
                path,
                timestamp=f"2026-04-{10+i} 12:00",
            )

        content = path.read_text()
        lines = [l for l in content.split("\n") if l.startswith("|") and "Date" not in l and "---" not in l]
        assert len(lines) == 3
        # Trend: FAIL → MIXED → PASS
        assert "FAIL" in lines[0]
        assert "MIXED" in lines[1]
        assert "PASS" in lines[2]

    def test_creates_parent_directory(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "benchmark-history.md"
        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")
        assert path.exists()

    def test_preserves_existing_content(self, tmp_path):
        path = tmp_path / "benchmark-history.md"

        # Write some pre-existing content with a valid table
        path.write_text(
            "# Benchmark History\n\nSome custom note.\n\n"
            "| Date | Verdict | Cost Δ | Lenient Δ | Quality Δ | Tokens Δ | Time Δ | Tasks |\n"
            "|------|---------|--------|-----------|-----------|----------|--------|-------|\n"
        )

        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")

        content = path.read_text()
        assert "Some custom note." in content
        assert "**PASS**" in content

    def test_returns_path(self, tmp_path):
        path = tmp_path / "benchmark-history.md"
        result = append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")
        assert result == path

    # --- Regression tests for review findings ---

    def test_no_trailing_newline_no_fusion(self, tmp_path):
        """Existing file without trailing newline should not fuse the
        new row onto the previous line."""
        path = tmp_path / "benchmark-history.md"
        path.write_text(
            "# Benchmark History\n\n"
            "| Date | Verdict | Cost Δ | Lenient Δ | Quality Δ | Tokens Δ | Time Δ | Tasks |\n"
            "|------|---------|--------|-----------|-----------|----------|--------|-------|\n"
            "| old row | **PASS** | 0% | 0pp | 0 | 0% | 0% | 0 |"
            # no trailing newline!
        )

        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")

        content = path.read_text()
        lines = content.strip().split("\n")
        # The old row and new row should be separate lines
        pipe_lines = [l for l in lines if l.startswith("|") and "Date" not in l and "---" not in l]
        assert len(pipe_lines) == 2
        # No line fusion
        assert not any("||" in l for l in lines)

    def test_prose_only_file_gets_table_header(self, tmp_path):
        """File with only prose (no table) should get a table header
        inserted before the first row."""
        path = tmp_path / "benchmark-history.md"
        path.write_text("Some custom note only\n")

        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")

        content = path.read_text()
        assert "Some custom note only" in content
        assert "| Date |" in content  # table header added
        assert "|------|" in content  # separator added
        assert "**PASS**" in content  # row added

    def test_prose_after_table_preserved(self, tmp_path):
        """Prose after the table should be preserved, and the new row
        should be inserted inside the table, not after the prose."""
        path = tmp_path / "benchmark-history.md"
        path.write_text(
            "# Benchmark History\n\n"
            "| Date | Verdict | Cost Δ | Lenient Δ | Quality Δ | Tokens Δ | Time Δ | Tasks |\n"
            "|------|---------|--------|-----------|-----------|----------|--------|-------|\n"
            "| old | **MIXED** | 0% | 0pp | 0 | 0% | 0% | 0 |\n"
            "\n"
            "## Notes\n\n"
            "Some notes after the table.\n"
        )

        append_to_history(_make_report(verdict="PASS"), path, timestamp="2026-04-11 10:00")

        content = path.read_text()
        assert "Some notes after the table." in content
        assert "**PASS**" in content

        # The new row should appear BEFORE the notes section
        pass_pos = content.index("**PASS**")
        notes_pos = content.index("## Notes")
        assert pass_pos < notes_pos, "New row should be inside the table, before the notes"

    # --- Regression tests for review round: table-block detection ---

    def test_header_without_separator_not_treated_as_table(self, tmp_path):
        """A file containing the header line but no separator should NOT
        be treated as having a valid table. A new table header+separator
        should be inserted before the row."""
        path = tmp_path / "benchmark-history.md"
        path.write_text(
            "Notes mentioning header text only\n"
            "| Date | Verdict | Cost \u0394 | Lenient \u0394 | Quality \u0394 | Tokens \u0394 | Time \u0394 | Tasks |\n"
        )

        append_to_history(_make_report(), path, timestamp="2026-04-10 14:00")

        content = path.read_text()
        # The old header-only line is preserved as prose
        assert "Notes mentioning header text only" in content
        # A proper separator row should now exist
        assert "|------|" in content
        # The new row is present
        assert "**PASS**" in content
        # The separator should be adjacent to the new header line
        lines = content.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("|------"):
                # Previous line should be the header
                assert "| Date |" in lines[i - 1]
                break
        else:
            pytest.fail("No separator line found")

    def test_pipe_in_prose_after_table_not_confused(self, tmp_path):
        """Pipe-prefixed lines in prose AFTER the table should not
        cause the new row to be inserted there instead of in the table."""
        path = tmp_path / "benchmark-history.md"
        path.write_text(
            "# Benchmark History\n\n"
            "| Date | Verdict | Cost \u0394 | Lenient \u0394 | Quality \u0394 | Tokens \u0394 | Time \u0394 | Tasks |\n"
            "|------|---------|--------|-----------|-----------|----------|--------|-------|\n"
            "| old | **MIXED** | 0% | 0pp | 0 | 0% | 0% | 0 |\n"
            "\n"
            "## Notes\n\n"
            "| not a benchmark row | still prose-ish |\n"
        )

        append_to_history(_make_report(verdict="PASS"), path, timestamp="2026-04-11 10:00")

        content = path.read_text()
        lines = content.split("\n")

        # Find the new PASS row position and the prose pipe line position
        pass_line_idx = None
        prose_pipe_idx = None
        for i, line in enumerate(lines):
            if "**PASS**" in line:
                pass_line_idx = i
            if "not a benchmark row" in line:
                prose_pipe_idx = i

        assert pass_line_idx is not None, "PASS row not found"
        assert prose_pipe_idx is not None, "Prose pipe line not found"
        assert pass_line_idx < prose_pipe_idx, (
            f"New row (line {pass_line_idx}) should be BEFORE the prose "
            f"pipe line (line {prose_pipe_idx})"
        )

    def test_two_tables_only_appends_to_benchmark_table(self, tmp_path):
        """If the file contains two pipe tables, the row should be
        appended to the benchmark table (the one with the known header),
        not the second unrelated table."""
        path = tmp_path / "benchmark-history.md"
        path.write_text(
            "# Benchmark History\n\n"
            "| Date | Verdict | Cost \u0394 | Lenient \u0394 | Quality \u0394 | Tokens \u0394 | Time \u0394 | Tasks |\n"
            "|------|---------|--------|-----------|-----------|----------|--------|-------|\n"
            "| old | **MIXED** | 0% | 0pp | 0 | 0% | 0% | 0 |\n"
            "\n"
            "## Other data\n\n"
            "| Metric | Value |\n"
            "|--------|-------|\n"
            "| foo    | bar   |\n"
        )

        append_to_history(_make_report(verdict="PASS"), path, timestamp="2026-04-11 10:00")

        content = path.read_text()

        # The PASS row should appear in the benchmark table, not the other table
        pass_pos = content.index("**PASS**")
        other_pos = content.index("## Other data")
        assert pass_pos < other_pos, "New row should be in the benchmark table, before the other table"

        # The other table should be unchanged
        assert "| foo    | bar   |" in content
