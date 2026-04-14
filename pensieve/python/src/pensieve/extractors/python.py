"""Python structural extractor (milestone B4 — reference implementation).

Parses a `.py` file with tree-sitter, walks the AST, and returns a
`FileExtraction` containing all structural landmarks: functions,
classes, methods, imports, constants, call edges within functions, and
rationale comments (# WHY:, # NOTE:, etc.).

This is the REFERENCE extractor. B5-B9 (JS, TS, Go, Java, Rust) follow
the same architecture: parse → walk top-level → walk class bodies →
collect call edges → collect comments → assemble FileExtraction.

Design decisions documented here apply to all extractors:

- **One pass per concern, not one recursive walk.** Simpler to reason
  about and debug. Pass 1: top-level declarations. Pass 2: class
  methods. Pass 3: call edges. Pass 4: rationale comments.
- **Signature = first line of the declaration.** Good enough for pattern
  matching. Multi-line signatures get truncated to the first line.
- **Visibility by convention:** `_name` = private, `name` = public.
  Python has no language-level visibility keywords.
- **Constants = top-level ALL_CAPS assignments.** Heuristic but matches
  the universal Python convention.
- **Nested functions and lambdas are skipped.** They're not structural
  landmarks at the file level.
- **Decorated functions are unwrapped.** `decorated_definition` wraps a
  `function_definition` or `class_definition`; we extract the inner
  definition.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import extract_rationale_comments
from pensieve.schema import (
    CallEdge,
    FileExtraction,
    Import,
    Parameter,
    RationaleComment,
    Symbol,
)

# ---------------------------------------------------------------------------
# Parser setup
# ---------------------------------------------------------------------------

_LANGUAGE = Language(tspython.language())


def _make_parser() -> Parser:
    return Parser(_LANGUAGE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONSTANT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _node_text(node: Node, source: bytes) -> str:
    """Extract the text content of a node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _first_line(node: Node, source: bytes) -> str:
    """Extract the first line of a node's text (for signatures)."""
    text = _node_text(node, source)
    return text.split("\n")[0].rstrip()


def _get_docstring(body_node: Node | None, source: bytes) -> str | None:
    """Extract the docstring from a function/class body, if present.

    The docstring is the first statement in the body that is an
    expression_statement containing a string literal.
    """
    if body_node is None:
        return None
    for child in body_node.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    raw = _node_text(sub, source)
                    # Strip surrounding quotes (""", ''', ", ')
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q) and raw.endswith(q):
                            return raw[len(q):-len(q)].strip()
                    return raw
            break  # only check the FIRST expression_statement
        elif child.type == "comment":
            continue  # skip leading comments before docstring
        else:
            break  # first non-comment, non-expression node → no docstring
    return None


def _visibility(name: str) -> str:
    """Determine Python visibility by naming convention."""
    if name.startswith("__") and name.endswith("__"):
        return "public"  # dunder methods are public API
    if name.startswith("__"):
        return "private"  # name-mangled
    if name.startswith("_"):
        return "private"  # convention-private
    return "public"


def _unwrap_decorated(node: Node) -> Node:
    """Unwrap a `decorated_definition` to get the inner definition."""
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return child
    return node


def _extract_parameters(params_node: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from a `parameters` node."""
    if params_node is None:
        return []

    results: list[Parameter] = []
    for child in params_node.children:
        if child.type == "identifier":
            results.append(Parameter(name=_node_text(child, source)))

        elif child.type == "typed_parameter":
            name_node = child.child_by_field_name("name") or child.children[0]
            type_node = child.child_by_field_name("type")
            results.append(Parameter(
                name=_node_text(name_node, source),
                type=_node_text(type_node, source) if type_node else None,
            ))

        elif child.type == "default_parameter":
            name_node = child.child_by_field_name("name") or child.children[0]
            value_node = child.child_by_field_name("value")
            results.append(Parameter(
                name=_node_text(name_node, source),
                default=_node_text(value_node, source) if value_node else None,
            ))

        elif child.type == "typed_default_parameter":
            name_node = child.child_by_field_name("name") or child.children[0]
            type_node = child.child_by_field_name("type")
            value_node = child.child_by_field_name("value")
            results.append(Parameter(
                name=_node_text(name_node, source),
                type=_node_text(type_node, source) if type_node else None,
                default=_node_text(value_node, source) if value_node else None,
            ))

        elif child.type == "list_splat_pattern":
            name = _node_text(child, source).lstrip("*")
            results.append(Parameter(name=f"*{name}"))

        elif child.type == "dictionary_splat_pattern":
            name = _node_text(child, source).lstrip("*")
            results.append(Parameter(name=f"**{name}"))

    return results


def _extract_return_type(func_node: Node, source: bytes) -> str | None:
    """Extract the return type annotation from a function_definition."""
    ret = func_node.child_by_field_name("return_type")
    if ret is None:
        return None
    return _node_text(ret, source)


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_function(node: Node, source: bytes, parent: str | None = None) -> Symbol:
    """Extract a function/method Symbol from a function_definition node."""
    raw_node = node
    node = _unwrap_decorated(node)

    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    params_node = node.child_by_field_name("parameters")
    body_node = node.child_by_field_name("body")

    return Symbol(
        name=name,
        kind="method" if parent else "function",
        line_start=raw_node.start_point[0] + 1,  # 1-indexed
        line_end=raw_node.end_point[0] + 1,
        signature=_first_line(raw_node, source),
        visibility=_visibility(name),
        parent=parent,
        docstring=_get_docstring(body_node, source),
        parameters=_extract_parameters(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_class(node: Node, source: bytes) -> tuple[Symbol, list[Symbol]]:
    """Extract a class Symbol and its method Symbols."""
    raw_node = node
    node = _unwrap_decorated(node)

    name_node = node.child_by_field_name("name")
    class_name = _node_text(name_node, source) if name_node else "<anonymous>"
    body_node = node.child_by_field_name("body")

    class_symbol = Symbol(
        name=class_name,
        kind="class",
        line_start=raw_node.start_point[0] + 1,
        line_end=raw_node.end_point[0] + 1,
        signature=_first_line(raw_node, source),
        visibility=_visibility(class_name),
        docstring=_get_docstring(body_node, source),
    )

    methods: list[Symbol] = []
    if body_node:
        for child in body_node.children:
            actual = _unwrap_decorated(child)
            if actual.type == "function_definition":
                methods.append(_extract_function(child, source, parent=class_name))

    return class_symbol, methods


def _extract_import(node: Node, source: bytes) -> list[Import]:
    """Extract Import entries from an import or import_from statement."""
    results: list[Import] = []
    line = node.start_point[0] + 1

    if node.type == "import_statement":
        # `import os`, `import os.path`, `import numpy as np`
        for child in node.children:
            if child.type == "dotted_name":
                results.append(Import(
                    module=_node_text(child, source),
                    line=line,
                    kind="import",
                ))
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                module = _node_text(name_node, source) if name_node else ""
                alias = _node_text(alias_node, source) if alias_node else None
                results.append(Import(
                    module=module,
                    alias=alias,
                    line=line,
                    kind="import",
                ))

    elif node.type == "import_from_statement":
        # `from pathlib import Path`, `from typing import Optional, List`
        # Also handles relative imports: `from . import foo`, `from ..bar import baz`
        module_node = node.child_by_field_name("module_name")
        module = ""
        if module_node:
            if module_node.type == "relative_import":
                # Relative import: from . import X, from ..bar import X
                module = _node_text(module_node, source)  # e.g., ".", "..bar", ".utils"
            else:
                module = _node_text(module_node, source)

        # Collect imported names
        names: list[str] = []
        alias = None
        for child in node.children:
            if child.type == "dotted_name" and child != module_node:
                names.append(_node_text(child, source))
            elif child.type == "aliased_import":
                name_n = child.child_by_field_name("name")
                alias_n = child.child_by_field_name("alias")
                if name_n:
                    names.append(_node_text(name_n, source))
                if alias_n:
                    alias = _node_text(alias_n, source)

        results.append(Import(
            module=module,
            names=names,
            alias=alias,
            line=line,
            kind="from_import",
        ))

    return results


def _extract_constant(node: Node, source: bytes) -> Symbol | None:
    """Try to extract a top-level constant from an expression_statement.

    Returns a Symbol if the statement is a simple assignment to an
    ALL_CAPS identifier, otherwise None.
    """
    if node.type != "expression_statement":
        return None

    for child in node.children:
        if child.type == "assignment":
            lhs = child.child_by_field_name("left")
            if lhs and lhs.type == "identifier":
                name = _node_text(lhs, source)
                if _CONSTANT_RE.match(name):
                    return Symbol(
                        name=name,
                        kind="constant",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        signature=_first_line(node, source),
                        visibility=_visibility(name),
                    )
    return None


# ---------------------------------------------------------------------------
# Pass 2: Call edges
# ---------------------------------------------------------------------------


def _collect_calls(
    body_node: Node | None,
    source: bytes,
    caller_name: str,
) -> list[CallEdge]:
    """Collect all function/method calls inside a function body."""
    if body_node is None:
        return []

    edges: list[CallEdge] = []
    stack = list(body_node.children)

    while stack:
        node = stack.pop()
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = _node_text(func_node, source)
                # Simplify attribute calls: `self.method()` → `method`,
                # `os.path.exists()` → `os.path.exists`
                if "." in callee:
                    parts = callee.split(".")
                    if parts[0] == "self":
                        callee = ".".join(parts[1:])
                edges.append(CallEdge(
                    caller=caller_name,
                    callee=callee,
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))
        # Don't recurse into nested function definitions — those are
        # separate scopes we skip by design.
        if node.type not in ("function_definition", "class_definition"):
            stack.extend(node.children)

    return edges


    # Pass 3 (rationale comments) uses the shared module from _comments.py


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract_python(path: Path) -> FileExtraction:
    """Extract structural data from a Python source file.

    This is the reference implementation for all language extractors.
    The architecture is:

    1. Read file, compute hash, create parser
    2. Pass 1: walk top-level nodes → functions, classes, imports, constants
    3. Pass 2: for each function/method body, collect call edges
    4. Pass 3: collect all rationale-tagged comments with context
    5. Assemble and return FileExtraction
    """
    source = path.read_bytes()
    sha256 = hashlib.sha256(source).hexdigest()
    lines = source.split(b"\n")
    line_count = len(lines)
    if lines and lines[-1] == b"":
        line_count -= 1  # don't count trailing empty line

    parser = _make_parser()
    tree = parser.parse(source)
    root = tree.root_node

    # --- Pass 1: top-level declarations ---

    symbols: list[Symbol] = []
    imports: list[Import] = []
    errors: list[str] = []

    for child in root.children:
        actual = _unwrap_decorated(child)

        if actual.type == "function_definition":
            symbols.append(_extract_function(child, source))

        elif actual.type == "class_definition":
            try:
                class_sym, methods = _extract_class(child, source)
                symbols.append(class_sym)
                symbols.extend(methods)
            except Exception as e:
                errors.append(f"Error extracting class at line {child.start_point[0]+1}: {e}")

        elif child.type in ("import_statement", "import_from_statement"):
            try:
                imports.extend(_extract_import(child, source))
            except Exception as e:
                errors.append(f"Error extracting import at line {child.start_point[0]+1}: {e}")

        elif child.type == "expression_statement":
            const = _extract_constant(child, source)
            if const:
                symbols.append(const)

    # --- Pass 2: call edges ---

    call_edges: list[CallEdge] = []
    for sym in symbols:
        if sym.kind in ("function", "method"):
            # Re-find the AST node for this symbol to get its body
            func_node = _find_function_node(root, source, sym.name, sym.parent)
            if func_node:
                body = func_node.child_by_field_name("body")
                call_edges.extend(_collect_calls(body, source, sym.name))

    # --- Pass 3: rationale comments (shared module) ---

    symbol_ranges = [
        (s.name, s.line_start, s.line_end) for s in symbols
    ]
    rationale_comments = extract_rationale_comments(
        root, source, symbol_ranges,
        comment_node_types=frozenset({"comment"}),
        is_doc_comment=None,  # Python docstrings are string literals, not comments
    )

    return FileExtraction(
        file_path=str(path),
        language="python",
        sha256=sha256,
        file_size_bytes=len(source),
        line_count=line_count,
        symbols=symbols,
        imports=imports,
        exports=[],  # Python doesn't have explicit export statements
        call_edges=call_edges,
        rationale_comments=rationale_comments,
        extraction_errors=errors,
    )


def _find_function_node(
    root: Node,
    source: bytes,
    name: str,
    parent: str | None,
) -> Node | None:
    """Re-find a function_definition node by name and parent.

    Used in Pass 2 to locate function bodies for call-edge extraction.
    """
    if parent:
        # Find the class first, then the method inside it
        for child in root.children:
            actual = _unwrap_decorated(child)
            if actual.type == "class_definition":
                name_node = actual.child_by_field_name("name")
                if name_node and _node_text(name_node, source) == parent:
                    body = actual.child_by_field_name("body")
                    if body:
                        for method_child in body.children:
                            m_actual = _unwrap_decorated(method_child)
                            if m_actual.type == "function_definition":
                                m_name = m_actual.child_by_field_name("name")
                                if m_name and _node_text(m_name, source) == name:
                                    return m_actual
    else:
        for child in root.children:
            actual = _unwrap_decorated(child)
            if actual.type == "function_definition":
                name_node = actual.child_by_field_name("name")
                if name_node and _node_text(name_node, source) == name:
                    return actual
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".py"], extract_python)
