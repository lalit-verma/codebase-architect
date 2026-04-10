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

    # --- benchmark generate ---
    gen_parser = bench_sub.add_parser(
        "generate",
        help="Generate benchmark tasks from repo context",
    )
    gen_parser.add_argument(
        "--repo", type=str, default=".",
        help="Repository root (default: current directory)",
    )
    gen_parser.add_argument(
        "--output", type=str, default=None,
        help="Output path for generated-tasks.json (default: <repo>/agent-docs/generated-tasks.json)",
    )
    gen_parser.add_argument(
        "--max-easy", type=int, default=3,
        help="Maximum easy tasks (default: 3)",
    )
    gen_parser.add_argument(
        "--max-medium", type=int, default=2,
        help="Maximum medium tasks (default: 2)",
    )
    gen_parser.add_argument(
        "--max-hard", type=int, default=2,
        help="Maximum hard tasks (default: 2)",
    )
    gen_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    # --- benchmark run ---
    run_parser = bench_sub.add_parser(
        "run",
        help="Generate and run benchmark (or run from existing generated-tasks.json)",
    )
    run_parser.add_argument(
        "--repo", type=str, default=".",
        help="Repository root (default: current directory)",
    )
    run_parser.add_argument(
        "--tasks-file", type=str, default=None,
        help=(
            "Path to generated-tasks.json to run. If not specified, "
            "tasks are generated fresh from repo context."
        ),
    )
    run_parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for benchmark.json (default: <repo>/agent-docs)",
    )
    run_parser.add_argument(
        "--max-easy", type=int, default=3,
        help="Maximum easy tasks to generate (default: 3)",
    )
    run_parser.add_argument(
        "--max-medium", type=int, default=2,
        help="Maximum medium tasks to generate (default: 2)",
    )
    run_parser.add_argument(
        "--max-hard", type=int, default=2,
        help="Maximum hard tasks to generate (default: 2)",
    )
    run_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for task generation (default: 42)",
    )
    run_parser.add_argument(
        "--judge", action="store_true", default=False,
        help="Run the LLM judge for lenient/quality scoring (adds cost).",
    )
    run_parser.add_argument(
        "--dev", action="store_true", default=False,
        help="Dev mode: generate 1 easy task only.",
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
    """Handle `pensieve benchmark generate` and `pensieve benchmark run`."""
    if not hasattr(args, "bench_action") or args.bench_action is None:
        print("pensieve benchmark: specify 'generate' or 'run'", file=sys.stderr)
        return 1

    if args.bench_action == "generate":
        return _cmd_benchmark_generate(args)
    elif args.bench_action == "run":
        return _cmd_benchmark_run(args)
    else:
        print(f"pensieve benchmark: unknown action: {args.bench_action}", file=sys.stderr)
        return 1


def _cmd_benchmark_generate(args) -> int:
    """Generate benchmark tasks from repo context."""
    from pathlib import Path
    from pensieve.benchmark.generate import (
        audit_tasks, build_repo_context, generate_tasks, save_generated_tasks,
    )

    repo_root = Path(args.repo).resolve()
    if not repo_root.is_dir():
        print(f"pensieve benchmark generate: not a directory: {repo_root}", file=sys.stderr)
        return 1

    structure_path = repo_root / "agent-docs" / "structure.json"
    graph_path = repo_root / "agent-docs" / "graph.json"

    if not structure_path.exists():
        print(
            f"pensieve benchmark generate: no structure.json found.\n"
            f"  Run `pensieve scan {repo_root}` first.",
            file=sys.stderr,
        )
        return 1

    ctx = build_repo_context(
        structure_path, graph_path if graph_path.exists() else None,
        repo_root=repo_root,
    )

    tasks = generate_tasks(
        ctx,
        max_easy=args.max_easy,
        max_medium=args.max_medium,
        max_hard=args.max_hard,
        seed=args.seed,
    )

    if not tasks:
        print("pensieve benchmark generate: no tasks could be generated from this repo.", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else repo_root / "agent-docs" / "generated-tasks.json"
    save_generated_tasks(tasks, output_path)

    # Print audit report
    print(audit_tasks(tasks), flush=True)
    print(f"  -> {output_path}", flush=True)
    return 0


def _cmd_benchmark_run(args) -> int:
    """Generate (or load) and run benchmark tasks."""
    from pathlib import Path
    import json as json_mod

    from pensieve.benchmark.generate import (
        build_repo_context, generate_tasks, save_generated_tasks, TaskInstance,
    )
    from pensieve.benchmark.history import append_to_history
    from pensieve.benchmark.metrics import aggregate_metrics, write_benchmark_json
    from pensieve.benchmark.runner import run_generated_benchmark

    repo_root = Path(args.repo).resolve()
    if not repo_root.is_dir():
        print(f"pensieve benchmark run: not a directory: {repo_root}", file=sys.stderr)
        return 1

    # Load executor
    try:
        from pensieve.benchmark.executor import create_executor
        executor = create_executor()
    except ImportError:
        print(
            "pensieve benchmark run: no executor available.\n"
            "  The executor module (pensieve.benchmark.executor) is required.",
            file=sys.stderr,
        )
        return 1

    # Load or generate tasks
    if args.tasks_file:
        # Load from existing generated-tasks.json
        tasks_path = Path(args.tasks_file)
        if not tasks_path.exists():
            print(f"pensieve benchmark run: file not found: {tasks_path}", file=sys.stderr)
            return 1
        data = json_mod.loads(tasks_path.read_text(encoding="utf-8"))
        from pensieve.benchmark.template import CheckerSpec
        instances = []
        for td in data.get("tasks", []):
            instances.append(TaskInstance(
                template_family=td["template_family"],
                instance_id=td["instance_id"],
                difficulty=td["difficulty"],
                instruction=td["instruction"],
                strict_checker=CheckerSpec(**td["strict_checker"]),
                lenient_checker=CheckerSpec(**td["lenient_checker"]),
                setup_actions=td.get("setup_actions", []),
                source_context=td.get("source_context", ""),
                tags=td.get("tags", []),
            ))
    else:
        # Generate fresh from repo context
        structure_path = repo_root / "agent-docs" / "structure.json"
        graph_path = repo_root / "agent-docs" / "graph.json"

        if not structure_path.exists():
            print(
                f"pensieve benchmark run: no structure.json found.\n"
                f"  Run `pensieve scan {repo_root}` first.",
                file=sys.stderr,
            )
            return 1

        max_easy = 1 if args.dev else args.max_easy
        max_medium = 0 if args.dev else args.max_medium
        max_hard = 0 if args.dev else args.max_hard

        ctx = build_repo_context(
            structure_path, graph_path if graph_path.exists() else None,
            repo_root=repo_root,
        )
        instances = generate_tasks(
            ctx,
            max_easy=max_easy,
            max_medium=max_medium,
            max_hard=max_hard,
            seed=args.seed,
        )

        if not instances:
            print("pensieve benchmark run: no tasks could be generated.", file=sys.stderr)
            return 1

        # Save generated tasks for auditability
        output_dir = Path(args.output_dir) if args.output_dir else repo_root / "agent-docs"
        output_dir.mkdir(parents=True, exist_ok=True)
        save_generated_tasks(instances, output_dir / "generated-tasks.json")

    output_dir = Path(args.output_dir) if args.output_dir else repo_root / "agent-docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    def _on_progress(mode, name, idx, total, task_result):
        if task_result is None:
            _log(f"  [{mode}] {idx}/{total} {name} ...")
        else:
            status = "ok" if not task_result.error else f"ERR: {task_result.error[:60]}"
            cost = f"${task_result.cost_usd:.3f}"
            _log(f"  [{mode}] {idx}/{total} {name} -> {status} ({cost}, {task_result.time_seconds:.1f}s)")

    by_diff = {"easy": 0, "medium": 0, "hard": 0}
    for inst in instances:
        by_diff[inst.difficulty] = by_diff.get(inst.difficulty, 0) + 1

    _log(f"Running benchmark on {repo_root}")
    _log(f"  tasks: {len(instances)} (easy={by_diff['easy']}, medium={by_diff['medium']}, hard={by_diff['hard']})")
    _log(f"  judge: {'on' if args.judge else 'off'}")

    result = run_generated_benchmark(
        repo_root=repo_root,
        instances=instances,
        executor=executor,
        on_progress=_on_progress,
        run_judge=args.judge,
    )

    # Aggregate metrics
    report = aggregate_metrics(result)

    # Write benchmark.json
    json_path = write_benchmark_json(report, output_dir / "benchmark.json")
    _log(f"  -> {json_path}")

    # Append to benchmark-history.md
    history_path = append_to_history(report, output_dir / "benchmark-history.md")
    _log(f"  -> {history_path}")

    # Print summary
    d = report.deltas
    _log(f"\n  Verdict: {report.verdict}")
    _log(f"  Cost:    {d.cost_pct:+.1f}%")
    _log(f"  Lenient: {d.lenient_pass_pp:+.1f}pp")
    _log(f"  Quality: {d.quality_diff:+.2f}")
    _log(f"  Tokens:  {d.tokens_pct:+.1f}%")
    _log(f"  Time:    {d.time_pct:+.1f}%")
    _log(f"  Tasks:   {max(report.with_framework.task_count, report.baseline.task_count)}")
    _log(f"  Total:   {report.total_time_seconds:.1f}s")

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
