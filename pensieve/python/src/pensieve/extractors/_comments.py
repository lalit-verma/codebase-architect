"""Shared rationale comment extraction (milestone B10).

Consolidates comment-tag detection from all 6 language extractors into
one module. Each extractor delegates to `extract_rationale_comments()`
instead of maintaining its own `_collect_comments` + `_COMMENT_TAGS`.

Adding a new tag (e.g., PERF:, SECURITY:) is a one-line change in
`RATIONALE_TAGS` below.

Supported comment styles:
  # WHY: text          (Python)
  // NOTE: text        (JS, TS, Go, Java, Rust)
  /* HACK: text */     (JS, TS, Java)
  * TODO: text         (inside block comments)
"""

from __future__ import annotations

import re
from collections.abc import Callable

from tree_sitter import Node

from pensieve.schema import RationaleComment

# ---------------------------------------------------------------------------
# Canonical tag list — single source of truth
# ---------------------------------------------------------------------------

RATIONALE_TAGS: tuple[str, ...] = (
    "WHY",
    "NOTE",
    "IMPORTANT",
    "HACK",
    "TODO",
    "FIXME",
)

# Universal pattern matching any comment prefix + any tag.
# Handles: # TAG:, // TAG:, /* TAG:, * TAG: (inside block comments)
# Group 1 = tag name, Group 2 = text after tag
_TAG_PATTERN = re.compile(
    r"(?:#|//|/\*|\*)\s*("
    + "|".join(RATIONALE_TAGS)
    + r")\s*:\s*(.+?)(?:\*/)?$",
    re.IGNORECASE,
)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_context(
    line: int,
    symbol_ranges: list[tuple[str, int, int]],
) -> str | None:
    """Find the containing symbol for a given line number.

    Returns the name of the innermost symbol whose range contains the
    line. If multiple symbols contain the line (e.g., a method inside a
    class), the last match wins — since symbol_ranges is ordered by
    appearance, the last match is the most specific.
    """
    context = None
    for sym_name, sym_start, sym_end in symbol_ranges:
        if sym_start <= line <= sym_end:
            context = sym_name
    return context


def extract_rationale_comments(
    root: Node,
    source: bytes,
    symbol_ranges: list[tuple[str, int, int]],
    comment_node_types: frozenset[str],
    is_doc_comment: Callable[[Node, bytes], bool] | None = None,
) -> list[RationaleComment]:
    """Extract rationale-tagged comments from an AST.

    Walks all nodes, finds comments matching `comment_node_types`,
    skips doc comments (via `is_doc_comment` filter), and matches
    against the canonical tag list.

    Args:
        root: The AST root node.
        source: The raw source bytes.
        symbol_ranges: List of (name, line_start, line_end) tuples
            for determining which symbol a comment is inside.
        comment_node_types: Set of AST node types that represent
            comments. E.g., {"comment"} for Python/JS, {"line_comment",
            "block_comment"} for Java.
        is_doc_comment: Optional callable that returns True if a comment
            node is a doc comment (and should be SKIPPED). E.g., for
            JS/Java: check if text starts with "/**". For Rust: check
            for outer_doc_comment_marker child.

    Returns:
        List of RationaleComment instances with tag, text, line, and
        context (containing symbol name).
    """
    results: list[RationaleComment] = []
    stack = [root]

    while stack:
        node = stack.pop()

        if node.type in comment_node_types:
            # Skip doc comments if a filter is provided
            if is_doc_comment and is_doc_comment(node, source):
                stack.extend(node.children)
                continue

            text = _node_text(node, source)
            base_line = node.start_point[0] + 1

            # Process each line of the comment (handles multi-line block comments)
            for i, comment_line in enumerate(text.split("\n")):
                comment_line = comment_line.strip()

                # Try matching the raw line first
                m = _TAG_PATTERN.match(comment_line)

                # If no match, try stripping block-comment prefixes
                if not m and comment_line.startswith("*"):
                    cleaned = comment_line.lstrip("*").strip()
                    m = _TAG_PATTERN.match(f"// {cleaned}")

                if m:
                    tag = m.group(1).upper()
                    tag_text = m.group(2).strip()
                    line = base_line + i

                    results.append(RationaleComment(
                        tag=tag,  # type: ignore[arg-type]
                        text=tag_text,
                        line=line,
                        context=_find_context(line, symbol_ranges),
                    ))

        stack.extend(node.children)

    return results


# ---------------------------------------------------------------------------
# Pre-built doc-comment filters for each language family
# ---------------------------------------------------------------------------


def is_jsdoc(node: Node, source: bytes) -> bool:
    """Filter for JS/TS/Java: skip `/** ... */` Javadoc/JSDoc comments."""
    text = _node_text(node, source)
    return text.startswith("/**")


def is_rust_doc(node: Node, source: bytes) -> bool:
    """Filter for Rust: skip `///` doc comments (outer_doc_comment_marker)."""
    return any(
        child.type == "outer_doc_comment_marker"
        for child in node.children
    )


# No filter needed for Python (docstrings are string literals, not comments)
# No filter needed for Go (doc comments are regular // comments; we don't
# skip them — the tag matching itself distinguishes rationale from docs)
