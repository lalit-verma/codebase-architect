"""JavaScript structural extractor (milestone B5).

Follows B4's multi-pass architecture adapted for JavaScript AST:

  Pass 1: top-level declarations — functions, classes + methods, imports
           (ESM + CommonJS require), exports, constants, arrow functions
  Pass 2: call edges within function/method bodies
  Pass 3: rationale comments (// and /* */ styles)

JS-specific handling:
  - Arrow functions (`const fn = (...) => { ... }`) detected as
    variable declarations with an arrow_function value.
  - Exports tracked separately; exported names get visibility="public",
    non-exported get visibility="unknown" (JS has no private keyword
    for functions/classes, only module-level scoping).
  - JSDoc (/** ... */) extracted as docstrings by looking at the
    preceding sibling of a function/class declaration.
  - CommonJS `require('module')` detected alongside ESM `import`.
  - `this.method()` calls stripped to `method` (same as Python's self).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import extract_rationale_comments, is_jsdoc
from pensieve.schema import (
    CallEdge,
    Export,
    FileExtraction,
    Import,
    Parameter,
    RationaleComment,
    Symbol,
)

# ---------------------------------------------------------------------------
# Parser setup
# ---------------------------------------------------------------------------

_LANGUAGE = Language(tsjs.language())


def _make_parser() -> Parser:
    return Parser(_LANGUAGE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONSTANT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _first_line(node: Node, source: bytes) -> str:
    return _node_text(node, source).split("\n")[0].rstrip()


def _get_jsdoc(node: Node, source: bytes) -> str | None:
    """Extract JSDoc from the preceding sibling comment, if any.

    JSDoc comments are `/** ... */` that appear immediately before a
    declaration. tree-sitter represents them as `comment` sibling nodes.
    """
    prev = node.prev_named_sibling
    if prev and prev.type == "comment":
        text = _node_text(prev, source)
        if text.startswith("/**"):
            # Strip /** ... */ and clean up * at line starts
            cleaned = text[3:]  # remove /**
            if cleaned.endswith("*/"):
                cleaned = cleaned[:-2]
            lines = []
            for line in cleaned.split("\n"):
                line = line.strip()
                if line.startswith("*"):
                    line = line[1:].strip()
                if line:
                    lines.append(line)
            return " ".join(lines) if lines else None
    return None


def _extract_params(params_node: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from a formal_parameters node."""
    if params_node is None:
        return []
    results: list[Parameter] = []
    for child in params_node.children:
        if child.type == "identifier":
            results.append(Parameter(name=_node_text(child, source)))
        elif child.type == "assignment_pattern":
            # Default parameter: name = value
            left = child.child_by_field_name("left")
            right = child.child_by_field_name("right")
            results.append(Parameter(
                name=_node_text(left, source) if left else "?",
                default=_node_text(right, source) if right else None,
            ))
        elif child.type == "rest_pattern":
            # ...args
            name = _node_text(child, source)
            results.append(Parameter(name=name))
        elif child.type == "object_pattern":
            # Destructured: { a, b }
            results.append(Parameter(name=_node_text(child, source)))
        elif child.type == "array_pattern":
            # Destructured: [a, b]
            results.append(Parameter(name=_node_text(child, source)))
    return results


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_function_decl(node: Node, source: bytes, parent: str | None = None) -> Symbol:
    """Extract from function_declaration or generator_function_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method" if parent else "function",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="unknown",
        parent=parent,
        docstring=_get_jsdoc(node, source) if not parent else None,
        parameters=_extract_params(params_node, source),
    )


def _extract_method(node: Node, source: bytes, class_name: str) -> Symbol:
    """Extract from a method_definition inside a class body."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    # Check for static keyword
    is_static = any(
        child.type == "static" or _node_text(child, source) == "static"
        for child in node.children
        if child.type != "comment"
    )

    sig = _first_line(node, source)

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=sig,
        visibility="public" if not name.startswith("_") else "private",
        parent=class_name,
        docstring=_get_jsdoc(node, source),
        parameters=_extract_params(params_node, source),
    )


def _extract_class(node: Node, source: bytes) -> tuple[Symbol, list[Symbol]]:
    """Extract a class and its methods."""
    name_node = node.child_by_field_name("name")
    class_name = _node_text(name_node, source) if name_node else "<anonymous>"
    body = node.child_by_field_name("body")

    class_sym = Symbol(
        name=class_name,
        kind="class",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="unknown",
        docstring=_get_jsdoc(node, source),
    )

    methods: list[Symbol] = []
    if body:
        for child in body.children:
            if child.type == "method_definition":
                methods.append(_extract_method(child, source, class_name))

    return class_sym, methods


def _extract_arrow_function(node: Node, source: bytes) -> Symbol | None:
    """Try to extract an arrow function from a lexical_declaration.

    Pattern: `const name = (...) => { ... }`
    The declaration is a `lexical_declaration` containing a
    `variable_declarator` whose value is an `arrow_function`.
    """
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if (
                name_node
                and name_node.type == "identifier"
                and value_node
                and value_node.type == "arrow_function"
            ):
                name = _node_text(name_node, source)
                params_node = value_node.child_by_field_name("parameters")
                # Could also be a single param without parens:
                # `const fn = x => x + 1` — parameter is just an identifier
                params: list[Parameter] = []
                if params_node and params_node.type == "formal_parameters":
                    params = _extract_params(params_node, source)
                elif params_node and params_node.type == "identifier":
                    params = [Parameter(name=_node_text(params_node, source))]

                return Symbol(
                    name=name,
                    kind="function",
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=_first_line(node, source),
                    visibility="unknown",
                    docstring=_get_jsdoc(node, source),
                    parameters=params,
                )
    return None


def _extract_imports(node: Node, source: bytes) -> list[Import]:
    """Extract from an ESM import_statement."""
    results: list[Import] = []
    line = node.start_point[0] + 1

    # Find the source module (the string after `from`)
    source_node = node.child_by_field_name("source")
    module = ""
    if source_node:
        raw = _node_text(source_node, source)
        module = raw.strip("'\"")

    # Find imported names
    names: list[str] = []
    alias: str | None = None
    for child in node.children:
        if child.type == "import_clause":
            for sub in child.children:
                if sub.type == "identifier":
                    # Default import: `import path from 'path'`
                    alias = _node_text(sub, source)
                elif sub.type == "named_imports":
                    for spec in sub.children:
                        if spec.type == "import_specifier":
                            name_n = spec.child_by_field_name("name")
                            if name_n:
                                names.append(_node_text(name_n, source))
                elif sub.type == "namespace_import":
                    # `import * as name from 'module'`
                    # Set names=["*"] to distinguish from default imports
                    # (default: alias set, names empty; namespace: alias set, names=["*"])
                    names.append("*")
                    for ns_child in sub.children:
                        if ns_child.type == "identifier":
                            alias = _node_text(ns_child, source)

    results.append(Import(
        module=module,
        names=names,
        alias=alias,
        line=line,
        kind="import",
    ))
    return results


def _extract_require(node: Node, source: bytes) -> Import | None:
    """Try to extract a CommonJS require from a lexical_declaration.

    Pattern: `const name = require('module')`
    """
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if (
                name_node
                and value_node
                and value_node.type == "call_expression"
            ):
                func_node = value_node.child_by_field_name("function")
                if func_node and _node_text(func_node, source) == "require":
                    args = value_node.child_by_field_name("arguments")
                    module = ""
                    if args:
                        for arg in args.children:
                            if arg.type == "string":
                                module = _node_text(arg, source).strip("'\"")
                                break
                    return Import(
                        module=module,
                        alias=_node_text(name_node, source),
                        line=node.start_point[0] + 1,
                        kind="require",
                    )
    return None


def _extract_exports(node: Node, source: bytes) -> list[Export]:
    """Extract from an export_statement."""
    results: list[Export] = []
    line = node.start_point[0] + 1

    has_default = any(
        child.type == "default" or _node_text(child, source) == "default"
        for child in node.children
    )

    if has_default:
        # `export default X` or `export default function X()` or `export default class X`
        for child in node.children:
            if child.type == "identifier":
                results.append(Export(name=_node_text(child, source), kind="default", line=line))
                break
            elif child.type == "function_declaration":
                name_n = child.child_by_field_name("name")
                if name_n:
                    results.append(Export(name=_node_text(name_n, source), kind="default", line=line))
                break
            elif child.type == "class_declaration":
                name_n = child.child_by_field_name("name")
                if name_n:
                    results.append(Export(name=_node_text(name_n, source), kind="default", line=line))
                break
    else:
        # `export { name1, name2 }` or `export function ...` or `export class ...`
        for child in node.children:
            if child.type == "export_clause":
                for spec in child.children:
                    if spec.type == "export_specifier":
                        name_n = spec.child_by_field_name("name")
                        if name_n:
                            results.append(Export(
                                name=_node_text(name_n, source),
                                kind="named",
                                line=line,
                            ))
            elif child.type == "function_declaration":
                name_n = child.child_by_field_name("name")
                if name_n:
                    results.append(Export(
                        name=_node_text(name_n, source),
                        kind="named",
                        line=line,
                    ))
            elif child.type == "class_declaration":
                name_n = child.child_by_field_name("name")
                if name_n:
                    results.append(Export(
                        name=_node_text(name_n, source),
                        kind="named",
                        line=line,
                    ))
            elif child.type == "lexical_declaration":
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        name_n = decl.child_by_field_name("name")
                        if name_n and name_n.type == "identifier":
                            results.append(Export(
                                name=_node_text(name_n, source),
                                kind="named",
                                line=line,
                            ))

    return results


def _extract_constant(node: Node, source: bytes) -> Symbol | None:
    """Try to extract a constant from a lexical_declaration.

    Pattern: `const ALL_CAPS = value` (not a function/require).
    """
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if (
                name_node
                and name_node.type == "identifier"
                and value_node
                and value_node.type not in ("arrow_function", "function")
            ):
                name = _node_text(name_node, source)
                # Skip require() calls
                if value_node.type == "call_expression":
                    func = value_node.child_by_field_name("function")
                    if func and _node_text(func, source) == "require":
                        return None
                if _CONSTANT_RE.match(name):
                    return Symbol(
                        name=name,
                        kind="constant",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        signature=_first_line(node, source),
                        visibility="unknown",
                    )
    return None


# ---------------------------------------------------------------------------
# Pass 2: Call edges
# ---------------------------------------------------------------------------


def _collect_calls(body: Node | None, source: bytes, caller: str) -> list[CallEdge]:
    if body is None:
        return []

    edges: list[CallEdge] = []
    stack = list(body.children)

    while stack:
        node = stack.pop()
        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = _node_text(func_node, source)
                if "." in callee:
                    parts = callee.split(".")
                    if parts[0] == "this":
                        callee = ".".join(parts[1:])
                edges.append(CallEdge(
                    caller=caller,
                    callee=callee,
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))
        if node.type not in (
            "function_declaration", "arrow_function",
            "class_declaration", "method_definition",
        ):
            stack.extend(node.children)

    return edges


    # Pass 3 (rationale comments) uses the shared module from _comments.py


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract_javascript(path: Path) -> FileExtraction:
    """Extract structural data from a JavaScript source file."""
    source = path.read_bytes()
    sha256 = hashlib.sha256(source).hexdigest()
    lines = source.split(b"\n")
    line_count = len(lines)
    if lines and lines[-1] == b"":
        line_count -= 1

    parser = _make_parser()
    tree = parser.parse(source)
    root = tree.root_node

    # --- Pass 1: top-level declarations ---

    symbols: list[Symbol] = []
    imports: list[Import] = []
    exports: list[Export] = []
    errors: list[str] = []

    for child in root.children:
        try:
            if child.type == "function_declaration":
                symbols.append(_extract_function_decl(child, source))

            elif child.type == "class_declaration":
                cls, methods = _extract_class(child, source)
                symbols.append(cls)
                symbols.extend(methods)

            elif child.type == "import_statement":
                imports.extend(_extract_imports(child, source))

            elif child.type == "export_statement":
                exports.extend(_extract_exports(child, source))
                # Also extract declarations inside exports
                for sub in child.children:
                    if sub.type == "function_declaration":
                        symbols.append(_extract_function_decl(sub, source))
                    elif sub.type == "class_declaration":
                        cls, methods = _extract_class(sub, source)
                        symbols.append(cls)
                        symbols.extend(methods)
                    elif sub.type == "lexical_declaration":
                        arrow = _extract_arrow_function(sub, source)
                        if arrow:
                            symbols.append(arrow)

            elif child.type == "lexical_declaration":
                # Check for arrow function, require, or constant
                arrow = _extract_arrow_function(child, source)
                if arrow:
                    symbols.append(arrow)
                else:
                    req = _extract_require(child, source)
                    if req:
                        imports.append(req)
                    else:
                        const = _extract_constant(child, source)
                        if const:
                            symbols.append(const)

        except Exception as e:
            errors.append(f"Error at line {child.start_point[0]+1}: {e}")

    # Apply export visibility: exported names get "public"
    exported_names = {exp.name for exp in exports}
    for sym in symbols:
        if sym.parent is None and sym.name in exported_names:
            sym.visibility = "public"

    # --- Pass 2: call edges ---

    call_edges: list[CallEdge] = []
    for sym in symbols:
        if sym.kind in ("function", "method"):
            func_node = _find_function_node(root, source, sym.name, sym.parent)
            if func_node:
                body = func_node.child_by_field_name("body")
                call_edges.extend(_collect_calls(body, source, sym.name))

    # --- Pass 3: rationale comments (shared module) ---

    symbol_ranges = [(s.name, s.line_start, s.line_end) for s in symbols]
    rationale_comments = extract_rationale_comments(
        root, source, symbol_ranges,
        comment_node_types=frozenset({"comment"}),
        is_doc_comment=is_jsdoc,
    )

    return FileExtraction(
        file_path=str(path),
        language="javascript",
        sha256=sha256,
        file_size_bytes=len(source),
        line_count=line_count,
        symbols=symbols,
        imports=imports,
        exports=exports,
        call_edges=call_edges,
        rationale_comments=rationale_comments,
        extraction_errors=errors,
    )


def _find_function_node(
    root: Node, source: bytes, name: str, parent: str | None,
) -> Node | None:
    """Re-find a function/method node by name for call-edge extraction."""
    if parent:
        for child in root.children:
            node = child
            # Handle exported classes
            if node.type == "export_statement":
                for sub in node.children:
                    if sub.type == "class_declaration":
                        node = sub
                        break
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node and _node_text(name_node, source) == parent:
                    body = node.child_by_field_name("body")
                    if body:
                        for method in body.children:
                            if method.type == "method_definition":
                                mn = method.child_by_field_name("name")
                                if mn and _node_text(mn, source) == name:
                                    return method
    else:
        for child in root.children:
            if child.type == "function_declaration":
                nn = child.child_by_field_name("name")
                if nn and _node_text(nn, source) == name:
                    return child
            elif child.type == "lexical_declaration":
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        nn = decl.child_by_field_name("name")
                        vn = decl.child_by_field_name("value")
                        if (
                            nn
                            and _node_text(nn, source) == name
                            and vn
                            and vn.type == "arrow_function"
                        ):
                            return vn
            elif child.type == "export_statement":
                for sub in child.children:
                    if sub.type == "function_declaration":
                        nn = sub.child_by_field_name("name")
                        if nn and _node_text(nn, source) == name:
                            return sub
                    elif sub.type == "lexical_declaration":
                        for decl in sub.children:
                            if decl.type == "variable_declarator":
                                nn = decl.child_by_field_name("name")
                                vn = decl.child_by_field_name("value")
                                if (
                                    nn
                                    and _node_text(nn, source) == name
                                    and vn
                                    and vn.type == "arrow_function"
                                ):
                                    return vn
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".js", ".mjs", ".cjs"], extract_javascript)
