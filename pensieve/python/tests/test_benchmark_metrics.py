"""Tests for benchmark metrics aggregation (milestone A10).

Covers:
  - ModeStats computation from TaskResults
  - Deltas between framework and baseline
  - Verdict logic: PASS, MIXED, FAIL
  - benchmark.json output format
  - Edge cases: empty results, all errors, zero baseline
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.benchmark.metrics import (
    BenchmarkReport,
    Deltas,
    ModeStats,
    aggregate_metrics,
    compute_deltas,
    compute_mode_stats,
    compute_verdict,
    write_benchmark_json,
)
from pensieve.benchmark.runner import BenchmarkResult, TaskResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(
    name: str = "test",
    mode: str = "baseline",
    tokens: int = 1000,
    cost: float = 0.10,
    time: float = 2.0,
    strict: bool = True,
    lenient: bool = True,
    quality: float = 7.0,
    error: str | None = None,
) -> TaskResult:
    return TaskResult(
        template_name=name,
        mode=mode,
        instruction="test instruction",
        agent_response="test response",
        tokens_used=tokens,
        cost_usd=cost,
        time_seconds=time,
        strict_pass=strict,
        lenient_pass=lenient,
        quality_score=quality,
        error=error,
    )


# ---------------------------------------------------------------------------
# ModeStats
# ---------------------------------------------------------------------------


class TestComputeModeStats:

    def test_basic_stats(self):
        results = [
            _result(tokens=1000, cost=0.10, time=2.0, quality=7.0),
            _result(tokens=2000, cost=0.20, time=3.0, quality=8.0),
        ]
        stats = compute_mode_stats(results)
        assert stats.task_count == 2
        assert stats.avg_tokens == 1500.0
        assert abs(stats.avg_cost_usd - 0.15) < 1e-10
        assert stats.avg_time_seconds == 2.5
        assert stats.quality_avg == 7.5
        assert stats.error_count == 0

    def test_pass_rates(self):
        results = [
            _result(strict=True, lenient=True),
            _result(strict=False, lenient=True),
            _result(strict=False, lenient=False),
            _result(strict=True, lenient=False),
        ]
        stats = compute_mode_stats(results)
        assert stats.strict_pass_rate == 0.5
        assert stats.lenient_pass_rate == 0.5

    def test_empty_results(self):
        stats = compute_mode_stats([])
        assert stats.task_count == 0
        assert stats.avg_tokens == 0.0
        assert stats.error_count == 0

    def test_error_tasks_excluded_from_averages(self):
        results = [
            _result(tokens=1000, cost=0.10, quality=7.0),
            _result(tokens=0, cost=0.0, quality=0.0, error="failed"),
        ]
        stats = compute_mode_stats(results)
        assert stats.task_count == 2
        assert stats.error_count == 1
        # Averages should only reflect the valid task
        assert stats.avg_tokens == 1000.0
        assert stats.quality_avg == 7.0


# ---------------------------------------------------------------------------
# Deltas
# ---------------------------------------------------------------------------


class TestComputeDeltas:

    def test_framework_cheaper(self):
        fw = ModeStats(avg_cost_usd=0.08)
        bl = ModeStats(avg_cost_usd=0.10)
        deltas = compute_deltas(fw, bl)
        assert deltas.cost_pct < 0  # framework is cheaper

    def test_framework_more_expensive(self):
        fw = ModeStats(avg_cost_usd=0.12)
        bl = ModeStats(avg_cost_usd=0.10)
        deltas = compute_deltas(fw, bl)
        assert deltas.cost_pct > 0

    def test_lenient_pass_improvement(self):
        fw = ModeStats(lenient_pass_rate=0.60)
        bl = ModeStats(lenient_pass_rate=0.50)
        deltas = compute_deltas(fw, bl)
        assert deltas.lenient_pass_pp == 10.0

    def test_zero_baseline_no_crash(self):
        fw = ModeStats(avg_tokens=100)
        bl = ModeStats(avg_tokens=0)
        deltas = compute_deltas(fw, bl)
        assert deltas.tokens_pct == 0.0  # no division by zero


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


class TestComputeVerdict:

    def test_pass_verdict(self):
        fw = ModeStats(avg_cost_usd=0.09, lenient_pass_rate=0.60, quality_avg=7.5)
        bl = ModeStats(avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0)
        deltas = compute_deltas(fw, bl)
        assert compute_verdict(fw, bl, deltas) == "PASS"

    def test_fail_verdict(self):
        fw = ModeStats(avg_cost_usd=0.12, lenient_pass_rate=0.40, quality_avg=6.0)
        bl = ModeStats(avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0)
        deltas = compute_deltas(fw, bl)
        assert compute_verdict(fw, bl, deltas) == "FAIL"

    def test_mixed_verdict_cost_up_quality_up(self):
        fw = ModeStats(avg_cost_usd=0.12, lenient_pass_rate=0.60, quality_avg=8.0)
        bl = ModeStats(avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0)
        deltas = compute_deltas(fw, bl)
        assert compute_verdict(fw, bl, deltas) == "MIXED"

    def test_mixed_verdict_cost_down_quality_down(self):
        fw = ModeStats(avg_cost_usd=0.08, lenient_pass_rate=0.60, quality_avg=6.0)
        bl = ModeStats(avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0)
        deltas = compute_deltas(fw, bl)
        assert compute_verdict(fw, bl, deltas) == "MIXED"

    def test_pass_requires_lenient_5pp_margin(self):
        """PASS needs lenient_pass ≥ baseline + 5pp, not just ≥ baseline."""
        fw = ModeStats(avg_cost_usd=0.09, lenient_pass_rate=0.52, quality_avg=7.5)
        bl = ModeStats(avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0)
        deltas = compute_deltas(fw, bl)
        # +2pp is not enough for PASS
        assert compute_verdict(fw, bl, deltas) == "MIXED"


# ---------------------------------------------------------------------------
# aggregate_metrics
# ---------------------------------------------------------------------------


class TestAggregateMetrics:

    def test_basic_aggregation(self):
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[
                _result("t1", "baseline", tokens=1000, cost=0.10, quality=7.0, lenient=True),
                _result("t2", "baseline", tokens=2000, cost=0.20, quality=6.0, lenient=False),
            ],
            framework_results=[
                _result("t1", "with_framework", tokens=800, cost=0.08, quality=8.0, lenient=True),
                _result("t2", "with_framework", tokens=1500, cost=0.15, quality=7.5, lenient=True),
            ],
            total_time_seconds=10.0,
        )
        report = aggregate_metrics(br)

        assert isinstance(report, BenchmarkReport)
        assert report.baseline.task_count == 2
        assert report.with_framework.task_count == 2
        assert report.deltas.cost_pct < 0  # framework cheaper
        assert report.deltas.lenient_pass_pp > 0  # framework better pass rate
        assert len(report.task_breakdown) == 2

    def test_task_breakdown_has_both_modes(self):
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[_result("t1", "baseline")],
            framework_results=[_result("t1", "with_framework")],
        )
        report = aggregate_metrics(br)
        assert len(report.task_breakdown) == 1
        entry = report.task_breakdown[0]
        assert "baseline" in entry
        assert "with_framework" in entry

    def test_empty_results(self):
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[],
            framework_results=[],
        )
        report = aggregate_metrics(br)
        assert report.baseline.task_count == 0
        assert report.with_framework.task_count == 0
        assert report.verdict == "MIXED"  # no data → not PASS, not FAIL

    # --- Regression: one-side-empty produces misleading deltas ---

    def test_framework_only_raises(self):
        """aggregate_metrics rejects framework-only results because
        comparative metrics are meaningless with one side empty."""
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[],
            framework_results=[
                _result("t1", "with_framework", tokens=800, cost=0.08),
            ],
        )
        with pytest.raises(ValueError, match="baseline is empty"):
            aggregate_metrics(br)

    def test_baseline_only_raises(self):
        """aggregate_metrics rejects baseline-only results."""
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[
                _result("t1", "baseline", tokens=1000, cost=0.10),
            ],
            framework_results=[],
        )
        with pytest.raises(ValueError, match="framework is empty"):
            aggregate_metrics(br)


# ---------------------------------------------------------------------------
# write_benchmark_json
# ---------------------------------------------------------------------------


class TestWriteBenchmarkJson:

    def test_writes_valid_json(self, tmp_path):
        report = BenchmarkReport(
            repo_root="/tmp/repo",
            with_framework=ModeStats(task_count=2, avg_tokens=800),
            baseline=ModeStats(task_count=2, avg_tokens=1000),
            deltas=Deltas(tokens_pct=-20.0, cost_pct=-10.0),
            verdict="PASS",
            task_breakdown=[{"template": "t1"}],
            total_time_seconds=5.0,
        )
        path = tmp_path / "benchmark.json"
        write_benchmark_json(report, path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["verdict"] == "PASS"
        assert data["with_framework"]["task_count"] == 2
        assert data["baseline"]["avg_tokens"] == 1000
        assert data["deltas"]["tokens_pct"] == -20.0
        assert len(data["task_breakdown"]) == 1

    def test_creates_parent_directory(self, tmp_path):
        report = BenchmarkReport(
            repo_root="/tmp/repo",
            with_framework=ModeStats(),
            baseline=ModeStats(),
            deltas=Deltas(),
            verdict="MIXED",
            task_breakdown=[],
        )
        path = tmp_path / "deep" / "nested" / "benchmark.json"
        write_benchmark_json(report, path)
        assert path.exists()


# ---------------------------------------------------------------------------
# Integration: aggregate from run_benchmark output shape
# ---------------------------------------------------------------------------


class TestIntegration:

    def test_full_pipeline_shape(self):
        """Simulate a run_benchmark result and verify the full
        aggregation pipeline produces a valid report."""
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[
                _result("add_handler", "baseline", tokens=1500, cost=0.15,
                        quality=7.0, strict=True, lenient=True),
                _result("add_test", "baseline", tokens=1200, cost=0.12,
                        quality=6.5, strict=True, lenient=False),
                _result("bug_fix", "baseline", tokens=800, cost=0.08,
                        quality=7.5, strict=False, lenient=True),
            ],
            framework_results=[
                _result("add_handler", "with_framework", tokens=1000, cost=0.10,
                        quality=8.0, strict=True, lenient=True),
                _result("add_test", "with_framework", tokens=900, cost=0.09,
                        quality=7.5, strict=True, lenient=True),
                _result("bug_fix", "with_framework", tokens=600, cost=0.06,
                        quality=8.0, strict=True, lenient=True),
            ],
            total_time_seconds=30.0,
        )
        report = aggregate_metrics(br)

        # Framework should win: lower cost, higher pass rate, higher quality
        assert report.deltas.cost_pct < 0
        assert report.deltas.lenient_pass_pp > 0
        assert report.deltas.quality_diff > 0
        assert report.verdict == "PASS"

        # Task breakdown should have 3 entries
        assert len(report.task_breakdown) == 3
        names = {e["template"] for e in report.task_breakdown}
        assert names == {"add_handler", "add_test", "bug_fix"}


# ---------------------------------------------------------------------------
# Review fix: duplicate template names preserved
# ---------------------------------------------------------------------------


class TestDuplicateTemplateNames:

    def test_repeated_template_name_not_collapsed(self):
        """Two results with the same template_name should both appear
        in the breakdown, not collapse into one."""
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[
                _result("add_handler", "baseline", tokens=1000),
                _result("add_handler", "baseline", tokens=2000),
            ],
            framework_results=[
                _result("add_handler", "with_framework", tokens=800),
                _result("add_handler", "with_framework", tokens=1500),
            ],
        )
        report = aggregate_metrics(br)
        assert len(report.task_breakdown) == 2  # both preserved

    def test_breakdown_preserves_order(self):
        br = BenchmarkResult(
            repo_root=Path("/tmp/repo"),
            baseline_results=[
                _result("t1", "baseline", tokens=100),
                _result("t2", "baseline", tokens=200),
                _result("t1", "baseline", tokens=300),
            ],
            framework_results=[
                _result("t1", "with_framework", tokens=80),
                _result("t2", "with_framework", tokens=150),
                _result("t1", "with_framework", tokens=250),
            ],
        )
        report = aggregate_metrics(br)
        assert len(report.task_breakdown) == 3
        templates = [e["template"] for e in report.task_breakdown]
        assert templates == ["t1", "t2", "t1"]


# ---------------------------------------------------------------------------
# Review fix: error-aware verdict
# ---------------------------------------------------------------------------


class TestErrorAwareVerdict:

    def test_framework_errors_prevent_pass(self):
        """Framework with execution errors should not get PASS even if
        surviving tasks beat baseline."""
        fw = ModeStats(
            avg_cost_usd=0.05, lenient_pass_rate=0.80, quality_avg=9.0,
            error_count=1,
        )
        bl = ModeStats(
            avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0,
            error_count=0,
        )
        deltas = compute_deltas(fw, bl)
        verdict = compute_verdict(fw, bl, deltas)
        assert verdict == "MIXED"  # not PASS, because framework had errors

    def test_baseline_errors_prevent_pass(self):
        """Baseline with errors also prevents PASS."""
        fw = ModeStats(
            avg_cost_usd=0.09, lenient_pass_rate=0.60, quality_avg=7.5,
            error_count=0,
        )
        bl = ModeStats(
            avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0,
            error_count=1,
        )
        deltas = compute_deltas(fw, bl)
        verdict = compute_verdict(fw, bl, deltas)
        assert verdict == "MIXED"

    def test_no_errors_allows_pass(self):
        """Zero errors in both modes allows PASS (regression)."""
        fw = ModeStats(
            avg_cost_usd=0.09, lenient_pass_rate=0.60, quality_avg=7.5,
            error_count=0,
        )
        bl = ModeStats(
            avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0,
            error_count=0,
        )
        deltas = compute_deltas(fw, bl)
        verdict = compute_verdict(fw, bl, deltas)
        assert verdict == "PASS"

    def test_errors_dont_prevent_fail(self):
        """FAIL verdict should still be possible with errors — errors
        make it worse, not better."""
        fw = ModeStats(
            avg_cost_usd=0.15, lenient_pass_rate=0.30, quality_avg=5.0,
            error_count=2,
        )
        bl = ModeStats(
            avg_cost_usd=0.10, lenient_pass_rate=0.50, quality_avg=7.0,
            error_count=0,
        )
        deltas = compute_deltas(fw, bl)
        verdict = compute_verdict(fw, bl, deltas)
        assert verdict == "FAIL"
