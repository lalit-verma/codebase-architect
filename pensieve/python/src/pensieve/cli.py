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

    # Subparsers — empty at A2, populated as subcommands ship.
    parser.add_subparsers(
        dest="command",
        title="commands",
        description=(
            "No subcommands implemented yet. Subcommands land in "
            "milestones A3 (hook), A6-A12 (benchmark), B12 (scan), "
            "C11 (wire), D1 (serve)."
        ),
        metavar="<command>",
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
        # No subcommand → print help and exit cleanly. This is the
        # discoverable behavior we want at A2; once subcommands land
        # in A3+, the user will see them listed in --help and pick one.
        parser.print_help()
        return 0

    # Dispatch table for subcommands. Empty at A2 — populated as
    # subcommands ship. The unreachable branch is intentional: if
    # argparse accepted a subcommand we don't know how to handle,
    # something is wrong with the parser registration.
    print(f"pensieve: unknown command: {args.command}", file=sys.stderr)
    return 1
