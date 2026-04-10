"""Benchmark metrics aggregation (milestone A10).

Takes raw TaskResult lists from run_benchmark and computes:
  - Per-mode aggregate stats (avg tokens, cost, time, pass rates, quality)
  - Deltas between with_framework and baseline
  - Verdict: PASS / MIXED / FAIL

Writes benchmark.json to the output directory.

Verdict logic:
  PASS  = cost ≤ baseline AND lenient_pass ≥ baseline + 5pp AND quality ≥ baseline
  FAIL  = cost > 105% of baseline AND lenient_pass < baseline
  MIXED = everything else (some axes improved, some regressed)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pensieve.benchmark.runner import BenchmarkResult, TaskResult


# ---------------------------------------------------------------------------
# Aggregate stats
# ---------------------------------------------------------------------------


@dataclass
class ModeStats:
    """Aggregate statistics for one benchmark mode."""

    task_count: int = 0
    avg_tokens: float = 0.0
    avg_cost_usd: float = 0.0
    avg_time_seconds: float = 0.0
    strict_pass_rate: float = 0.0  # 0.0 - 1.0
    lenient_pass_rate: float = 0.0  # 0.0 - 1.0
    quality_avg: float = 0.0  # 0.0 - 10.0
    error_count: int = 0


def compute_mode_stats(results: list[TaskResult]) -> ModeStats:
    """Compute aggregate stats from a list of TaskResults."""
    if not results:
        return ModeStats()

    valid = [r for r in results if r.error is None]
    n = len(valid) if valid else 1  # avoid division by zero

    return ModeStats(
        task_count=len(results),
        avg_tokens=sum(r.tokens_used for r in valid) / n,
        avg_cost_usd=sum(r.cost_usd for r in valid) / n,
        avg_time_seconds=sum(r.time_seconds for r in valid) / n,
        strict_pass_rate=sum(1 for r in valid if r.strict_pass) / n,
        lenient_pass_rate=sum(1 for r in valid if r.lenient_pass) / n,
        quality_avg=sum(r.quality_score for r in valid) / n,
        error_count=sum(1 for r in results if r.error is not None),
    )


# ---------------------------------------------------------------------------
# Deltas
# ---------------------------------------------------------------------------


@dataclass
class Deltas:
    """Difference between with_framework and baseline stats."""

    tokens_pct: float = 0.0  # negative = framework uses fewer tokens
    cost_pct: float = 0.0  # negative = framework is cheaper
    time_pct: float = 0.0  # negative = framework is faster
    strict_pass_pp: float = 0.0  # percentage points difference
    lenient_pass_pp: float = 0.0  # percentage points difference
    quality_diff: float = 0.0  # absolute difference


def compute_deltas(framework: ModeStats, baseline: ModeStats) -> Deltas:
    """Compute deltas between framework and baseline stats."""

    def _pct(fw: float, bl: float) -> float:
        if bl == 0:
            return 0.0
        return round((fw - bl) / bl * 100, 2)

    def _pp(fw: float, bl: float) -> float:
        return round((fw - bl) * 100, 2)

    return Deltas(
        tokens_pct=_pct(framework.avg_tokens, baseline.avg_tokens),
        cost_pct=_pct(framework.avg_cost_usd, baseline.avg_cost_usd),
        time_pct=_pct(framework.avg_time_seconds, baseline.avg_time_seconds),
        strict_pass_pp=_pp(framework.strict_pass_rate, baseline.strict_pass_rate),
        lenient_pass_pp=_pp(framework.lenient_pass_rate, baseline.lenient_pass_rate),
        quality_diff=round(framework.quality_avg - baseline.quality_avg, 2),
    )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


Verdict = Literal["PASS", "MIXED", "FAIL"]


def compute_verdict(
    framework: ModeStats,
    baseline: ModeStats,
    deltas: Deltas,
) -> Verdict:
    """Compute the benchmark verdict.

    PASS  = cost ≤ baseline AND lenient_pass ≥ baseline + 5pp AND quality ≥ baseline
            AND no execution errors in either mode
    FAIL  = cost > 105% of baseline AND lenient_pass < baseline
    MIXED = everything else (including any mode with execution errors)
    """
    # Execution errors in either mode prevent PASS
    has_errors = framework.error_count > 0 or baseline.error_count > 0

    cost_ok = deltas.cost_pct <= 0
    lenient_good = deltas.lenient_pass_pp >= 5.0
    quality_ok = deltas.quality_diff >= 0

    cost_bad = deltas.cost_pct > 5.0
    lenient_bad = deltas.lenient_pass_pp < 0

    if cost_bad and lenient_bad:
        return "FAIL"
    elif cost_ok and lenient_good and quality_ok and not has_errors:
        return "PASS"
    else:
        return "MIXED"


# ---------------------------------------------------------------------------
# benchmark.json output
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkReport:
    """Complete benchmark report, written to benchmark.json."""

    repo_root: str
    with_framework: ModeStats
    baseline: ModeStats
    deltas: Deltas
    verdict: Verdict
    task_breakdown: list[dict]
    total_time_seconds: float = 0.0


def aggregate_metrics(result: BenchmarkResult) -> BenchmarkReport:
    """Aggregate a BenchmarkResult into a BenchmarkReport.

    Raises ValueError if exactly one side is empty — comparative
    metrics (deltas, verdict) are meaningless without both modes.
    Both-empty is allowed (produces zero deltas and MIXED verdict).
    """
    has_fw = len(result.framework_results) > 0
    has_bl = len(result.baseline_results) > 0
    if has_fw != has_bl:
        populated = "framework" if has_fw else "baseline"
        empty = "baseline" if has_fw else "framework"
        raise ValueError(
            f"Cannot compute comparative metrics: {populated} has results "
            f"but {empty} is empty. Run both modes for a valid comparison."
        )

    fw_stats = compute_mode_stats(result.framework_results)
    bl_stats = compute_mode_stats(result.baseline_results)
    deltas = compute_deltas(fw_stats, bl_stats)
    verdict = compute_verdict(fw_stats, bl_stats, deltas)

    # Per-task breakdown: pair framework and baseline results by INDEX,
    # not by template name. This preserves all instances when the same
    # template is run multiple times (e.g., different parameterizations).
    breakdown: list[dict] = []
    max_len = max(
        len(result.framework_results),
        len(result.baseline_results),
        1,  # avoid empty range
    )

    def _task_dict(r: TaskResult) -> dict:
        return {
            "tokens": r.tokens_used,
            "cost_usd": r.cost_usd,
            "time_seconds": r.time_seconds,
            "strict_pass": r.strict_pass,
            "lenient_pass": r.lenient_pass,
            "quality": r.quality_score,
            "error": r.error,
        }

    for i in range(max_len):
        entry: dict = {"index": i}
        if i < len(result.framework_results):
            fw = result.framework_results[i]
            entry["template"] = fw.template_name
            entry["with_framework"] = _task_dict(fw)
        if i < len(result.baseline_results):
            bl = result.baseline_results[i]
            entry.setdefault("template", bl.template_name)
            entry["baseline"] = _task_dict(bl)
        breakdown.append(entry)

    return BenchmarkReport(
        repo_root=str(result.repo_root),
        with_framework=fw_stats,
        baseline=bl_stats,
        deltas=deltas,
        verdict=verdict,
        task_breakdown=breakdown,
        total_time_seconds=result.total_time_seconds,
    )


def write_benchmark_json(
    report: BenchmarkReport,
    output_path: Path,
) -> Path:
    """Write a BenchmarkReport to benchmark.json.

    Returns the path written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "repo_root": report.repo_root,
        "with_framework": asdict(report.with_framework),
        "baseline": asdict(report.baseline),
        "deltas": asdict(report.deltas),
        "verdict": report.verdict,
        "task_breakdown": report.task_breakdown,
        "total_time_seconds": report.total_time_seconds,
    }

    output_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
