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

    print(f"pensieve: unknown command: {args.command}", file=sys.stderr)
    return 1


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
