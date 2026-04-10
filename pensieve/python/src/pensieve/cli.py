"""Code Pensieve CLI entry point.

Subcommands:
  pensieve scan <repo>           — AST extraction → structure.json + graph.json
  pensieve analyze <repo>        — full Layer 2 pipeline → subsystem docs + synthesis
  pensieve wire --repo <path>    — inline nano into CLAUDE.md + install hook
  pensieve benchmark generate    — generate repo-aware benchmark tasks
  pensieve benchmark run         — run benchmark (generate or load → execute → report)
  pensieve hook install/uninstall — manage PreToolUse hook directly

Dispatch table in `main` is flat and explicit. Subcommands are
discoverable by reading this file top-to-bottom.
"""

from __future__ import annotations

import argparse
import sys

from pensieve import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    """
    parser = argparse.ArgumentParser(
        prog="pensieve",
        description=(
            "Code Pensieve — a vessel for codebase memories. Extracts "
            "structural context from a codebase and wires it into "
            "coding agents (Claude Code, Codex, Cursor) for "
            "cost-measured, harness-enforced context delivery."
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

    # --- analyze subcommand (B14) ---
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Generate agent-docs from repo structure (full pipeline)",
        description=(
            "Run the full analysis pipeline: scan the repo, detect "
            "subsystem boundaries, select key files per subsystem, "
            "generate subsystem documentation, and synthesize "
            "patterns.md, agent-context.md, and agent-context-nano.md. "
            "Writes all output to agent-docs/."
        ),
    )
    analyze_parser.add_argument(
        "path", type=str, nargs="?", default=".",
        help="Path to the repository root (default: current directory)",
    )
    analyze_parser.add_argument(
        "--model", type=str, default="sonnet",
        help="Model for LLM calls (default: sonnet)",
    )
    analyze_parser.add_argument(
        "--proposal-timeout", type=int, default=300,
        help="Timeout in seconds for subsystem proposal LLM call (default: 300)",
    )
    analyze_parser.add_argument(
        "--selection-timeout", type=int, default=300,
        help="Timeout in seconds for per-subsystem file selection LLM call (default: 300)",
    )
    analyze_parser.add_argument(
        "--doc-timeout", type=int, default=300,
        help="Timeout in seconds for per-subsystem doc generation LLM call (default: 300)",
    )
    analyze_parser.add_argument(
        "--synthesis-timeout", type=int, default=300,
        help="Timeout in seconds for each synthesis LLM call (default: 300)",
    )
    analyze_parser.add_argument(
        "--analyze-parallelism", type=int, default=1,
        help=(
            "Number of subsystems to process concurrently in stages 3-4 "
            "(default: 1 = sequential). Does not affect proposal or synthesis."
        ),
    )

    # --- wire subcommand ---
    wire_parser = subparsers.add_parser(
        "wire",
        help="Wire agent-docs into the repo (CLAUDE.md + hook)",
        description=(
            "Inline the nano-digest into CLAUDE.md and install the "
            "PreToolUse hook. Run this after `pensieve analyze` to "
            "make agent-docs visible to coding agents."
        ),
    )
    wire_parser.add_argument(
        "--repo", type=str, default=".",
        help="Repository root (default: current directory)",
    )
    wire_parser.add_argument(
        "--platform", type=str, default="claude", choices=["claude"],
        help="Target platform (default: claude)",
    )
    wire_parser.add_argument(
        "--unwire", action="store_true", default=False,
        help="Remove pensieve wiring (undo wire).",
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
    run_parser.add_argument(
        "--parallelism", type=int, default=1,
        help=(
            "Number of tasks to run concurrently within each mode "
            "(default: 1 = sequential). Timing metrics are only "
            "comparable across runs with the same parallelism."
        ),
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

    if args.command == "analyze":
        return _cmd_analyze(args)

    if args.command == "wire":
        return _cmd_wire(args)

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

    parallelism = args.parallelism
    if parallelism < 1:
        print("pensieve benchmark run: --parallelism must be >= 1", file=sys.stderr)
        return 1

    _log(f"Running benchmark on {repo_root}")
    _log(f"  tasks: {len(instances)} (easy={by_diff['easy']}, medium={by_diff['medium']}, hard={by_diff['hard']})")
    _log(f"  judge: {'on' if args.judge else 'off'}  parallelism: {parallelism}")

    result = run_generated_benchmark(
        repo_root=repo_root,
        instances=instances,
        executor=executor,
        on_progress=_on_progress,
        run_judge=args.judge,
        parallelism=parallelism,
    )

    # Aggregate metrics
    report = aggregate_metrics(result)
    report.parallelism = parallelism

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


def _cmd_analyze(args) -> int:
    """Handle the `pensieve analyze` subcommand — full B14 pipeline."""
    from pathlib import Path
    from pensieve.scan import scan_repo
    from pensieve.context import (
        FileSelection,
        profile_directories,
        propose_subsystems,
        select_files_for_subsystem,
        generate_route_index,
        SubsystemProposal,
        SubsystemMap,
    )
    from pensieve.docgen import (
        SubsystemDoc,
        generate_subsystem_doc,
        save_subsystem_doc,
        run_discover,
        run_synthesize,
    )
    from pensieve.checkpoint import AnalyzeCheckpoint

    def _log(msg: str) -> None:
        print(msg, flush=True)

    repo_root = Path(args.path).resolve()
    if not repo_root.is_dir():
        print(f"pensieve analyze: not a directory: {repo_root}", file=sys.stderr)
        return 1

    model = args.model
    proposal_timeout = args.proposal_timeout
    selection_timeout = args.selection_timeout
    doc_timeout = args.doc_timeout
    synthesis_timeout = args.synthesis_timeout
    analyze_parallelism = args.analyze_parallelism
    if analyze_parallelism < 1:
        print("pensieve analyze: --analyze-parallelism must be >= 1", file=sys.stderr)
        return 1
    output_dir = repo_root / "agent-docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    structure_path = output_dir / "structure.json"
    graph_path = output_dir / "graph.json"

    # --- Stage 1: Scan (if needed) ---
    # Rescan if either structure.json or graph.json is missing.
    # Both are required for profiling and subsystem detection.
    if not structure_path.exists() or not graph_path.exists():
        _log("[1/5] Scanning repo...")
        result = scan_repo(repo_root, output_dir=output_dir)
        s = result.stats
        _log(f"  scanned {s['total_files']} files ({s['extracted']} extracted, {s['cached']} cached)")
    else:
        _log("[1/5] Scan: using existing structure.json + graph.json")

    # Verify both files exist after scan
    if not structure_path.exists():
        print("pensieve analyze: scan failed to produce structure.json", file=sys.stderr)
        return 1
    if not graph_path.exists():
        print("pensieve analyze: scan failed to produce graph.json", file=sys.stderr)
        return 1

    # --- Checkpoint validation ---
    ckpt = AnalyzeCheckpoint(output_dir, model)
    if ckpt.validate(structure_path, graph_path):
        _log("  checkpoints: valid (will reuse completed stages)")
    else:
        _log("  checkpoints: stale or missing (will recompute)")
        ckpt.clear()
        ckpt.save_fingerprint(structure_path, graph_path)

    # --- Stage 2: Profile directories + propose subsystems ---
    _log("[2/5] Profiling directories and proposing subsystems...")
    profile = profile_directories(structure_path, graph_path)
    _log(f"  {len(profile.directories)} directories profiled, {profile.total_edges} edges")

    # Check checkpoint for subsystem map
    cached_map = ckpt.load_subsystem_map() if ckpt.has_subsystem_map() else None
    if cached_map:
        _log("  subsystem map: [reused from checkpoint]")
        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(**s) for s in cached_map.get("subsystems", [])
            ],
            excluded=cached_map.get("excluded", []),
        )
    else:
        smap = propose_subsystems(profile, model=model, timeout_seconds=proposal_timeout)
        if smap.error:
            print(f"pensieve analyze: subsystem proposal failed: {smap.error}", file=sys.stderr)
            return 1
        # Save checkpoint
        ckpt.save_subsystem_map({
            "subsystems": [
                {"name": s.name, "directories": s.directories,
                 "role": s.role, "rationale": s.rationale}
                for s in smap.subsystems
            ],
            "excluded": smap.excluded,
        })
        _log("  subsystem map: [computed]")

    _log(f"  {len(smap.subsystems)} subsystems:")
    for s in smap.subsystems:
        _log(f"    - {s.name} ({', '.join(s.directories)})")
    if smap.excluded:
        _log(f"  {len(smap.excluded)} directories excluded")

    # Run v1 discover prompt for system-overview.md + .analysis-state.md
    from pensieve.context import format_profiles_for_llm
    structural_context = format_profiles_for_llm(profile)
    discover_result = run_discover(
        repo_root, structural_context,
        subsystem_map=smap,
        model=model, timeout_seconds=proposal_timeout,
    )
    if discover_result.error:
        _log(f"  discover prompt: WARNING — {discover_result.error}")
    else:
        if discover_result.system_overview:
            (output_dir / "system-overview.md").write_text(
                discover_result.system_overview + "\n", encoding="utf-8",
            )
            _log(f"  -> {output_dir / 'system-overview.md'}")
        if discover_result.analysis_state:
            (output_dir / ".analysis-state.md").write_text(
                discover_result.analysis_state + "\n", encoding="utf-8",
            )
            _log(f"  -> {output_dir / '.analysis-state.md'}")

    # --- Stage 3: Select files per subsystem ---
    from concurrent.futures import ThreadPoolExecutor, as_completed

    par_label = f"  parallelism: {analyze_parallelism}" if analyze_parallelism > 1 else ""
    _log(f"[3/5] Selecting key files for {len(smap.subsystems)} subsystems...{par_label}")

    def _select_one(idx_sub):
        idx, sub = idx_sub
        # Check checkpoint
        cached = ckpt.load_selection(sub.name) if ckpt.has_selection(sub.name) else None
        if cached:
            sel = FileSelection(
                files=cached.get("files", []),
                error=cached.get("error"),
            )
            return (idx, sub.name, sel, True)  # True = reused
        sel = select_files_for_subsystem(
            sub, structure_path, model=model, timeout_seconds=selection_timeout,
        )
        # Only checkpoint successful selections — transient errors must not
        # be cached and replayed on rerun.
        if not sel.error:
            ckpt.save_selection(sub.name, {
                "files": sel.files,
            })
        return (idx, sub.name, sel, False)  # False = computed

    def _log_selection(idx, name, sel, reused):
        tag = "[reused]" if reused else "[computed]"
        if sel.error:
            _log(f"  {idx+1}. {name}: ERROR — {sel.error} {tag}")
        else:
            _log(f"  {idx+1}. {name}: {len(sel.files)} files selected {tag}")

    selections: dict[str, FileSelection] = {}
    if analyze_parallelism <= 1:
        for i, sub in enumerate(smap.subsystems):
            _, name, sel, reused = _select_one((i, sub))
            selections[name] = sel
            _log_selection(i, name, sel, reused)
    else:
        indexed_sels: list[tuple[int, str, FileSelection]] = []
        with ThreadPoolExecutor(max_workers=analyze_parallelism) as pool:
            futures = {
                pool.submit(_select_one, (i, sub)): i
                for i, sub in enumerate(smap.subsystems)
            }
            for future in as_completed(futures):
                try:
                    idx, name, sel, reused = future.result()
                    indexed_sels.append((idx, name, sel))
                    _log_selection(idx, name, sel, reused)
                except Exception as exc:
                    idx = futures[future]
                    name = smap.subsystems[idx].name
                    _log(f"  {idx+1}. {name}: CRASHED — {exc}")
                    indexed_sels.append((idx, name, FileSelection(files=[], error=str(exc))))
        for _, name, sel in sorted(indexed_sels, key=lambda x: x[0]):
            selections[name] = sel

    # --- Stage 4: Generate subsystem docs ---
    _log(f"[4/5] Generating subsystem documentation...{par_label}")

    def _generate_one(idx_sub_sel):
        idx, sub, sel = idx_sub_sel
        # Check checkpoint
        cached_md = ckpt.load_doc(sub.name) if ckpt.has_doc(sub.name) else None
        if cached_md:
            doc = SubsystemDoc(
                subsystem_name=sub.name,
                markdown=cached_md,
                files_read=[f["file_path"] for f in sel.files],
            )
            return (idx, doc, True)  # reused
        doc = generate_subsystem_doc(
            sub, structure_path, sel, repo_root, model=model,
            timeout_seconds=doc_timeout,
        )
        if not doc.error and doc.markdown:
            ckpt.save_doc(sub.name, doc.markdown)
        return (idx, doc, False)  # computed

    def _log_doc(sub_name, doc, reused):
        tag = "[reused]" if reused else "[computed]"
        if doc.error:
            _log(f"    {sub_name}: ERROR: {doc.error} {tag}")
        else:
            path = save_subsystem_doc(doc, output_dir)
            _log(f"    {sub_name}: -> {path} ({len(doc.markdown)} chars) {tag}")

    docs = [None] * len(smap.subsystems)
    if analyze_parallelism <= 1:
        for i, sub in enumerate(smap.subsystems):
            sel = selections.get(sub.name, FileSelection(files=[]))
            _log(f"  {i+1}/{len(smap.subsystems)} {sub.name}...")
            _, doc, reused = _generate_one((i, sub, sel))
            docs[i] = doc
            _log_doc(sub.name, doc, reused)
    else:
        indexed_docs: list[tuple[int, SubsystemDoc]] = []
        with ThreadPoolExecutor(max_workers=analyze_parallelism) as pool:
            jobs = []
            for i, sub in enumerate(smap.subsystems):
                sel = selections.get(sub.name, FileSelection(files=[]))
                _log(f"  {i+1}/{len(smap.subsystems)} {sub.name}...")
                jobs.append((i, sub, sel))
            futures = {
                pool.submit(_generate_one, job): job[0]
                for job in jobs
            }
            for future in as_completed(futures):
                idx = futures[future]
                sub = smap.subsystems[idx]
                try:
                    _, doc, reused = future.result()
                    indexed_docs.append((idx, doc))
                    _log_doc(sub.name, doc, reused)
                except Exception as exc:
                    _log(f"    {sub.name}: CRASHED: {exc}")
                    indexed_docs.append((idx, SubsystemDoc(
                        subsystem_name=sub.name, markdown="",
                        files_read=[], error=f"Worker crashed: {exc}",
                    )))
        for idx, doc in sorted(indexed_docs, key=lambda x: x[0]):
            docs[idx] = doc

    successful = [d for d in docs if d and not d.error]
    failed = [d for d in docs if d and d.error]
    _log(f"  {len(successful)} docs generated, {len(failed)} failed")

    # --- Stage 5: Synthesize (v1 analyze-synthesize prompt) ---
    if not successful:
        print("pensieve analyze: no subsystem docs generated, cannot synthesize.", file=sys.stderr)
        return 1

    _log(f"[5/5] Running v1 synthesis (agent-context, nano, patterns, etc.)...")
    synth_result = run_synthesize(
        repo_root, structural_context=structural_context,
        model=model, timeout_seconds=synthesis_timeout,
    )
    if synth_result.errors:
        for err in synth_result.errors:
            _log(f"  WARNING: {err}")
    else:
        _log(f"  synthesis complete ({len(synth_result.raw_output)} chars)")

    # --- Route index (Bx1) ---
    route_path = generate_route_index(smap, output_dir)
    _log(f"  -> {route_path}")

    # --- Post-synthesis verification ---
    _REQUIRED_ARTIFACTS = [
        "agent-context.md",
        "agent-context-nano.md",
        "patterns.md",
        "routing-map.md",
        "system-overview.md",
        "agent-brief.md",
        "index.md",
        "agent-protocol.md",
    ]
    missing = [name for name in _REQUIRED_ARTIFACTS if not (output_dir / name).exists()]
    if missing:
        _log(f"\n  SYNTHESIS INCOMPLETE — missing required artifacts:")
        for name in missing:
            _log(f"    - {name}")
        _log(f"  {len(_REQUIRED_ARTIFACTS) - len(missing)}/{len(_REQUIRED_ARTIFACTS)} artifacts present")
    else:
        _log(f"  all {len(_REQUIRED_ARTIFACTS)} required artifacts verified")

    # --- Summary ---
    _log(f"\nAnalysis complete:")
    _log(f"  subsystems: {len(successful)}/{len(smap.subsystems)}")
    _log(f"  output: {output_dir}")
    if missing:
        _log(f"  STATUS: INCOMPLETE — {len(missing)} required artifacts missing")
        return 1

    return 0


def _cmd_wire(args) -> int:
    """Handle `pensieve wire` — inline nano into CLAUDE.md + install hook."""
    from pathlib import Path
    from pensieve.hooks import (
        install_hook, uninstall_hook,
        wire_nano_to_claudemd, unwire_nano_from_claudemd,
    )

    repo_root = Path(args.repo).resolve()
    if not repo_root.is_dir():
        print(f"pensieve wire: not a directory: {repo_root}", file=sys.stderr)
        return 1

    if args.unwire:
        # Undo wiring
        nano_result = unwire_nano_from_claudemd(repo_root)
        hook_result = uninstall_hook(repo_root)
        print(f"Nano:     {nano_result['claudemd']}", flush=True)
        print(f"Hook:     {hook_result.get('settings', 'unknown')}", flush=True)
        return 0

    # Check nano exists BEFORE doing anything — wire is all-or-nothing.
    nano_path = repo_root / "agent-docs" / "agent-context-nano.md"
    if not nano_path.exists():
        print(
            "pensieve wire: agent-docs/agent-context-nano.md not found.\n"
            "  Run `pensieve analyze` first to generate it.\n"
            "  No changes made to the repo.",
            file=sys.stderr,
        )
        return 1

    # Both operations: nano → CLAUDE.md + hook install
    nano_result = wire_nano_to_claudemd(repo_root)
    hook_result = install_hook(repo_root)

    print(f"Nano:     {nano_result['nano']} -> CLAUDE.md {nano_result['claudemd']}", flush=True)
    print(f"Hook:     script={hook_result['script']}, settings={hook_result['settings']}", flush=True)

    return 0


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
