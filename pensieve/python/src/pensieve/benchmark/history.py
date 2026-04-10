"""Benchmark history generator (milestone A11).

Appends a one-run summary to `benchmark-history.md` so successive
re-runs show trends over time. Maintains a valid markdown table:

  - Creates the file with header + table on first run.
  - On subsequent runs, finds the table and appends a row at the end.
  - If the file exists but has no table header, inserts the header
    before the first row.
  - Ensures trailing newline before appending to prevent line fusion.

Never overwrites non-table content (prose notes above the table are
preserved).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pensieve.benchmark.metrics import BenchmarkReport


_TABLE_HEADER_LINE = "| Date | Verdict | Cost Δ | Lenient Δ | Quality Δ | Tokens Δ | Time Δ | Tasks |"
_TABLE_SEPARATOR = "|------|---------|--------|-----------|-----------|----------|--------|-------|"

_FULL_HEADER = f"""\
# Benchmark History

Successive benchmark runs on this repo. Each row is one run of
`pensieve benchmark run`. Trends show whether framework changes
improve or regress performance.

{_TABLE_HEADER_LINE}
{_TABLE_SEPARATOR}
"""


def _format_row(report: BenchmarkReport, timestamp: str | None = None) -> str:
    """Format a single BenchmarkReport as a markdown table row."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    d = report.deltas
    task_count = max(
        report.with_framework.task_count,
        report.baseline.task_count,
    )

    def _fmt_pct(val: float) -> str:
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.1f}%"

    def _fmt_pp(val: float) -> str:
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.1f}pp"

    def _fmt_diff(val: float) -> str:
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.2f}"

    return (
        f"| {timestamp} "
        f"| **{report.verdict}** "
        f"| {_fmt_pct(d.cost_pct)} "
        f"| {_fmt_pp(d.lenient_pass_pp)} "
        f"| {_fmt_diff(d.quality_diff)} "
        f"| {_fmt_pct(d.tokens_pct)} "
        f"| {_fmt_pct(d.time_pct)} "
        f"| {task_count} |"
    )


def append_to_history(
    report: BenchmarkReport,
    history_path: Path,
    timestamp: str | None = None,
) -> Path:
    """Append a benchmark run summary to benchmark-history.md.

    Maintains a valid markdown table:
      - Creates the file with header if it doesn't exist.
      - If the file exists but has no table header, appends the
        header + separator before the first row.
      - Ensures a trailing newline before appending the new row.
      - Appends the row after the last table row (pipe-prefixed line).

    Returns the path written to.
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)

    row = _format_row(report, timestamp)

    if not history_path.exists():
        # First run: create file with full header + first row
        history_path.write_text(_FULL_HEADER + row + "\n", encoding="utf-8")
        return history_path

    # File exists — read, find the table, append the row
    content = history_path.read_text(encoding="utf-8")

    # Ensure trailing newline to prevent line fusion
    if content and not content.endswith("\n"):
        content += "\n"

    # Check if the table header exists
    has_table = _TABLE_HEADER_LINE in content

    if has_table:
        # Find the last table row (last line starting with |) and
        # insert after it. This preserves any prose after the table.
        lines = content.split("\n")
        last_table_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("|"):
                last_table_idx = i

        if last_table_idx >= 0:
            # Insert the new row after the last table line
            lines.insert(last_table_idx + 1, row)
            content = "\n".join(lines)
            if not content.endswith("\n"):
                content += "\n"
        else:
            # Header found but no rows yet — append after content
            content += row + "\n"
    else:
        # No table header — add header + separator + row
        content += "\n" + _TABLE_HEADER_LINE + "\n" + _TABLE_SEPARATOR + "\n" + row + "\n"

    history_path.write_text(content, encoding="utf-8")
    return history_path
