"""Code Pensieve — A vessel for codebase memories.

Coding agents draw from the store on demand instead of re-experiencing
the original event.

The Python package is the deterministic core of Code Pensieve. It
handles file detection, tree-sitter AST extraction (Phase B+), the
SHA256 incremental cache, the PreToolUse hook installer, the
auto-benchmark runner, and the MCP server. The LLM orchestration
layer (slash commands, prompts, chat-first checkpoints) lives
separately and calls into this package.

See ../../PLAN.md for the full build plan and ../../pensieve-context.md
for the context dump that explains the design.
"""

__version__ = "0.0.1"

__all__ = ["__version__"]
