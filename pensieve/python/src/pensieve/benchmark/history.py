"""Benchmark history generator (milestone A11).

Appends a one-run summary to `benchmark-history.md` so successive
re-runs show trends over time. The file is human-readable markdown
with a table of runs.

Creates the file with a header on the first run. Appends a new row
on each subsequent run. Never overwrites existing content.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pensieve.benchmark.metrics import BenchmarkReport


_HEADER = """\
# Benchmark History

Successive benchmark runs on this repo. Each row is one run of
`pensieve benchmark run`. Trends show whether framework changes
improve or regress performance.

| Date | Verdict | Cost Δ | Lenient Δ | Quality Δ | Tokens Δ | Time Δ | Tasks |
|------|---------|--------|-----------|-----------|----------|--------|-------|
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

    Creates the file with a header if it doesn't exist.
    Appends a table row for each call.

    Args:
        report: The BenchmarkReport to record.
        history_path: Path to the benchmark-history.md file.
        timestamp: Optional override for the date column. Defaults
            to current UTC time.

    Returns:
        The path written to.
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)

    row = _format_row(report, timestamp)

    if not history_path.exists():
        history_path.write_text(_HEADER + row + "\n", encoding="utf-8")
    else:
        with history_path.open("a", encoding="utf-8") as f:
            f.write(row + "\n")

    return history_path
