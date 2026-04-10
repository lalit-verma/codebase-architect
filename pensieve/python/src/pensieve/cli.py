"""Code Pensieve CLI entry point.

Phase A scaffolding (milestone A2). The CLI is wired with `--version`
and `--help` but has no subcommands yet. Subcommands land in subsequent
milestones:

  - A3:    `pensieve hook install` / `pensieve hook uninstall`
  - A6-A12: `pensieve benchmark run`
  - B12:   `pensieve scan <repo>`
  - C11:   `pensieve wire <platform> [--multi-repo]`
  - D1:    `pensieve serve` (MCP server)

When you add a new subcommand, register it in `_build_parser` and
implement a handler. Keep the dispatch table in `main` flat and
explicit; subcommands should be discoverable by reading this file
top-to-bottom.
"""

from __future__ import annotations

import argparse
import sys

from pensieve import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    Subparsers are registered here as we add subcommands. At A2 there
    are none — `pensieve` with no args prints help, `pensieve --version`
    prints the version.
    """
    parser = argparse.ArgumentParser(
        prog="pensieve",
        description=(
            "Code Pensieve — a vessel for codebase memories. Extracts "
            "structural context from a codebase and wires it into "
            "coding agents (Claude Code, Codex, Cursor) for "
            "cost-measured, harness-enforced context delivery."
        ),
        epilog=(
            "Phase A scaffolding. Subcommands land in upcoming "
            "milestones. See PLAN.md in the project root for the build "
            "plan."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"code-pensieve {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="<command>",
    )

    # --- scan subcommand (B12) ---
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a repository and extract structural data",
        description=(
            "Walk a directory, extract structural data from all "
            "supported source files using tree-sitter AST parsing, "
            "and write the results to agent-docs/structure.json. "
            "Uses SHA256 caching — unchanged files are not re-extracted."
        ),
    )
    scan_parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Path to the repository root (default: current directory)",
    )
    scan_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: <repo>/agent-docs)",
    )

    # --- benchmark subcommand (A12) ---
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Run the auto-benchmark suite",
        description=(
            "Run benchmark task templates against a target repo, "
            "comparing with-framework (agent-docs + hook) against "
            "baseline (no agent-docs). Produces benchmark.json with "
            "metrics and appends a row to benchmark-history.md."
        ),
    )
    bench_sub = bench_parser.add_subparsers(
        dest="bench_action",
        title="actions",
        metavar="<action>",
    )

    run_parser = bench_sub.add_parser("run", help="Run the benchmark")
    run_parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Repository root (default: current directory)",
    )
    run_parser.add_argument(
        "--tasks",
        type=str,
        default="all",
        help=(
            "Comma-separated template names, or 'all' for every "
            "registered template (default: all)"
        ),
    )
    run_parser.add_argument(
        "--baseline",
        action="store_true",
        default=False,
        help=(
            "Explicitly include baseline mode. Both modes run by "
            "default; use --baseline --with-framework together to "
            "be explicit. Single-mode is not supported."
        ),
    )
    run_parser.add_argument(
        "--with-framework",
        action="store_true",
        default=False,
        dest="with_framework",
        help=(
            "Explicitly include with-framework mode. Both modes run "
            "by default; use --baseline --with-framework together to "
            "be explicit. Single-mode is not supported."
        ),
    )
    run_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for benchmark.json (default: <repo>/agent-docs)",
    )

    # --- hook subcommand (A3, A4) ---
    hook_parser = subparsers.add_parser(
        "hook",
        help="Install or uninstall the PreToolUse hook",
        description=(
            "Install or uninstall the Code Pensieve PreToolUse hook "
            "into a target repo's .claude/ directory. The hook fires "
            "before every Glob/Grep call and reminds Claude that "
            "codebase context is available."
        ),
    )
    hook_sub = hook_parser.add_subparsers(
        dest="hook_action",
        title="actions",
        metavar="<action>",
    )

    install_parser = hook_sub.add_parser("install", help="Install the hook")
    install_parser.add_argument(
        "--platform",
        type=str,
        default="claude",
        choices=["claude"],
        help="Target platform (default: claude). Others not yet supported.",
    )
    install_parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Repository root (default: current directory)",
    )

    uninstall_parser = hook_sub.add_parser("uninstall", help="Uninstall the hook")
    uninstall_parser.add_argument(
        "--platform",
        type=str,
        default="claude",
        choices=["claude"],
        help="Target platform (default: claude)",
    )
    uninstall_parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Repository root (default: current directory)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `pensieve` CLI.

    Args:
        argv: Optional list of CLI arguments (excluding the program
            name). When None, argparse reads from sys.argv. Useful for
            testing — pass a list to invoke the CLI without running a
            subprocess.

    Returns:
        Process exit code. 0 on success, non-zero on error. Tests can
        assert against this directly.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # --- Dispatch ---

    if args.command == "scan":
        return _cmd_scan(args)

    if args.command == "benchmark":
        return _cmd_benchmark(args)

    if args.command == "hook":
        return _cmd_hook(args)

    print(f"pensieve: unknown command: {args.command}", file=sys.stderr)
    return 1


def _cmd_benchmark(args) -> int:
    """Handle the `pensieve benchmark run` subcommand."""
    if not hasattr(args, "bench_action") or args.bench_action is None:
        print("pensieve benchmark: specify 'run'", file=sys.stderr)
        return 1

    if args.bench_action != "run":
        print(f"pensieve benchmark: unknown action: {args.bench_action}", file=sys.stderr)
        return 1

    from pathlib import Path

    from pensieve.benchmark.history import append_to_history
    from pensieve.benchmark.metrics import aggregate_metrics, write_benchmark_json
    from pensieve.benchmark.runner import run_benchmark
    from pensieve.benchmark.tasks import get_all_templates, get_template_by_name

    repo_root = Path(args.repo).resolve()
    if not repo_root.is_dir():
        print(f"pensieve benchmark run: not a directory: {repo_root}", file=sys.stderr)
        return 1

    # Resolve templates
    if args.tasks == "all":
        templates = get_all_templates()
    else:
        names = [n.strip() for n in args.tasks.split(",") if n.strip()]
        templates = []
        for name in names:
            t = get_template_by_name(name)
            if t is None:
                available = [t.name for t in get_all_templates()]
                print(
                    f"pensieve benchmark run: unknown template: {name}\n"
                    f"  available: {', '.join(available)}",
                    file=sys.stderr,
                )
                return 1
            templates.append(t)

    if not templates:
        print("pensieve benchmark run: no templates to run", file=sys.stderr)
        return 1

    # Resolve modes — benchmark comparison requires both modes.
    # If neither flag is given, run both (the default).
    # If both flags are given, run both (explicit).
    # If only one flag is given, reject: the output artifacts
    # (benchmark.json, benchmark-history.md) are comparative and
    # produce misleading deltas/verdicts with only one side populated.
    run_bl = args.baseline
    run_fw = args.with_framework
    if not run_bl and not run_fw:
        run_bl = True
        run_fw = True
    elif run_bl != run_fw:
        missing = "--with-framework" if run_bl else "--baseline"
        print(
            f"pensieve benchmark run: comparison requires both modes.\n"
            f"  Add {missing} or omit both flags to run the full comparison.\n"
            f"  Single-mode runs are not supported because benchmark.json\n"
            f"  and benchmark-history.md are comparative artifacts.",
            file=sys.stderr,
        )
        return 1

    # Resolve output directory
    output_dir = Path(args.output_dir) if args.output_dir else repo_root / "agent-docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # We need a real executor for actual benchmark runs.
    # For now, print a clear message if no executor is available.
    # A real executor (calling Claude Code subprocess) will be
    # plugged in when we run on the calibration repo (A13).
    try:
        from pensieve.benchmark.executor import create_executor
        executor = create_executor()
    except ImportError:
        # No real executor yet — provide a stub that explains
        print(
            "pensieve benchmark run: no executor available.\n"
            "  The benchmark runner requires an executor to invoke the\n"
            "  coding agent. A real executor (Claude Code subprocess)\n"
            "  will be implemented in A13.\n"
            "\n"
            "  For testing, use the Python API directly with a mock\n"
            "  executor:\n"
            "    from pensieve.benchmark.runner import run_benchmark",
            file=sys.stderr,
        )
        return 1

    print(f"Running benchmark on {repo_root}")
    print(f"  templates: {len(templates)}  baseline: {run_bl}  framework: {run_fw}")

    result = run_benchmark(
        repo_root=repo_root,
        templates=templates,
        executor=executor,
        run_baseline=run_bl,
        run_framework=run_fw,
    )

    # Aggregate metrics
    report = aggregate_metrics(result)

    # Write benchmark.json
    json_path = write_benchmark_json(report, output_dir / "benchmark.json")
    print(f"  -> {json_path}")

    # Append to benchmark-history.md
    history_path = append_to_history(report, output_dir / "benchmark-history.md")
    print(f"  -> {history_path}")

    # Print summary
    d = report.deltas
    print(f"\n  Verdict: {report.verdict}")
    print(f"  Cost:    {d.cost_pct:+.1f}%")
    print(f"  Lenient: {d.lenient_pass_pp:+.1f}pp")
    print(f"  Quality: {d.quality_diff:+.2f}")
    print(f"  Tokens:  {d.tokens_pct:+.1f}%")
    print(f"  Time:    {d.time_pct:+.1f}%")
    print(f"  Tasks:   {max(report.with_framework.task_count, report.baseline.task_count)}")
    print(f"  Total:   {report.total_time_seconds:.1f}s")

    return 0


def _cmd_scan(args) -> int:
    """Handle the `pensieve scan` subcommand."""
    from pathlib import Path
    from pensieve.scan import scan_repo

    repo_root = Path(args.path).resolve()
    if not repo_root.is_dir():
        print(f"pensieve scan: not a directory: {repo_root}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    result = scan_repo(repo_root, output_dir=output_dir)

    # Print summary
    s = result.stats
    print(f"Scanned {s['total_files']} files in {result.scan_time_seconds}s")
    print(f"  extracted: {s['extracted']}  cached: {s['cached']}  "
          f"failed: {s['failed']}")
    print(f"  → {result.structure_path}")

    return 0 if s["failed"] == 0 else 1


def _cmd_hook(args) -> int:
    """Handle the `pensieve hook install/uninstall` subcommand."""
    from pathlib import Path
    from pensieve.hooks import install_hook, uninstall_hook

    if not hasattr(args, "hook_action") or args.hook_action is None:
        print("pensieve hook: specify 'install' or 'uninstall'", file=sys.stderr)
        return 1

    repo_root = Path(args.repo).resolve()
    if not repo_root.is_dir():
        print(f"pensieve hook: not a directory: {repo_root}", file=sys.stderr)
        return 1

    if args.hook_action == "install":
        result = install_hook(repo_root)
        print(f"Hook script: {result['script']}")
        print(f"Settings:    {result['settings']}")
        if result["script"] == "created":
            print(f"  → {repo_root / '.claude' / 'hooks' / 'pensieve-pretooluse.sh'}")
        return 0

    elif args.hook_action == "uninstall":
        result = uninstall_hook(repo_root)
        print(f"Hook script: {result['script']}")
        print(f"Settings:    {result['settings']}")
        return 0

    print(f"pensieve hook: unknown action: {args.hook_action}", file=sys.stderr)
    return 1
