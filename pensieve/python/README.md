# code-pensieve (Python package)

> A vessel for codebase memories. The Python core of Code Pensieve.

This is the **Python package** for Code Pensieve. Install with:

```bash
pip install -e ".[dev]"
```

Then verify:

```bash
pensieve --version
python -m pensieve --version
pytest
```

## Status

**Phase A scaffolding (milestone A2 complete).** The CLI is wired but
has no subcommands yet. Subcommands land in subsequent milestones:

| Milestone | Subcommand | What it does |
|---|---|---|
| A3 | `pensieve hook install` / `uninstall` | Install/remove the PreToolUse hook for Claude Code |
| A6–A12 | `pensieve benchmark run` | Auto-benchmark with-framework vs baseline on a calibration repo |
| B12 | `pensieve scan <repo>` | AST extraction → `structure.json` + `graph.json` |
| C11 | `pensieve wire <platform>` | Multi-repo wiring installer |

See [`../../PLAN.md`](../../PLAN.md) for the full build plan and
current status. See [`../../pensieve-context.md`](../../pensieve-context.md)
for the context dump that explains *why* the framework is built this
way.

## Layout

```
pensieve/python/
├── pyproject.toml          package metadata, dependencies, entry point
├── README.md               this file
├── .gitignore              Python build artifacts, venv, cache
├── src/
│   └── pensieve/           importable as `import pensieve`
│       ├── __init__.py     __version__
│       ├── __main__.py     enables `python -m pensieve`
│       └── cli.py          CLI entry point (argparse-based)
└── tests/
    ├── conftest.py         pytest fixtures
    └── test_cli.py         smoke tests for the CLI scaffolding
```

The `src/` layout is intentional. It prevents accidentally importing
from the source tree without installing the package, which catches
packaging errors early.

## Development

```bash
# From pensieve/python/, create a virtualenv and install editable
python3 -m venv .venv
source .venv/bin/activate     # or: .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=pensieve --cov-report=term-missing

# Smoke-check the installed CLI
pensieve --version
python -m pensieve --version
```

## Design notes

- **No runtime dependencies** at A2 by design. Tree-sitter and other
  third-party libraries land in Phase B alongside the AST extractors.
  Keeping the surface small until then makes packaging mistakes
  obvious.
- **Build backend: hatchling.** Modern, simple, no setup.py / setup.cfg
  needed. Auto-installed by pip when building.
- **CLI parser: argparse (stdlib).** No external dependency. We can
  switch to click or typer later if argparse becomes painful, but
  argparse handles subcommands fine for now.
- **Python 3.10+.** Modern type-hint syntax (`list[str] | None`) is
  used throughout.
