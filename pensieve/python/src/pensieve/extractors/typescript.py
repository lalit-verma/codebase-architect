"""TypeScript structural extractor (milestone B6).

Extends the JS extractor pattern for TypeScript-specific constructs:

  - `interface_declaration` → kind="interface"
  - `type_alias_declaration` → kind="type_alias"
  - `enum_declaration` → kind="enum"
  - `accessibility_modifier` → visibility="public"/"private"/"protected"
  - Type annotations on parameters and return types
  - `import type` detection
  - TSX support via `language_tsx()` for `.tsx` files

Reuses stable helpers from the JS extractor (call edge collection,
comment collection, JSDoc extraction) where the logic is identical.
TS-specific parameter and return-type extraction is reimplemented.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_typescript as tsts
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import extract_rationale_comments, is_jsdoc
from pensieve.extractors.javascript import (
    _CONSTANT_RE,
    _collect_calls,
    _extract_exports as _extract_js_exports,
    _extract_require,
    _get_jsdoc,
    _node_text,
    _first_line,
)
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
# Parser setup — two parsers: TS and TSX
# ---------------------------------------------------------------------------

_TS_LANGUAGE = Language(tsts.language_typescript())
_TSX_LANGUAGE = Language(tsts.language_tsx())


def _make_parser(tsx: bool = False) -> Parser:
    return Parser(_TSX_LANGUAGE if tsx else _TS_LANGUAGE)


# ---------------------------------------------------------------------------
# TS-specific helpers
# ---------------------------------------------------------------------------


def _extract_ts_params(params_node: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from a formal_parameters node (TS variant).

    TS uses `required_parameter` and `optional_parameter` with type
    annotations, unlike JS's plain `identifier`.
    """
    if params_node is None:
        return []

    results: list[Parameter] = []
    for child in params_node.children:
        if child.type == "identifier":
            results.append(Parameter(name=_node_text(child, source)))

        elif child.type in ("required_parameter", "optional_parameter"):
            name_node = None
            type_str = None
            default_str = None

            for sub in child.children:
                if sub.type == "identifier":
                    name_node = sub
                elif sub.type == "type_annotation":
                    # Type is everything after the ':'
                    for type_child in sub.children:
                        if type_child.type != ":":
                            type_str = _node_text(type_child, source)
                elif sub.type in (
                    "string", "number", "true", "false", "null",
                    "object", "array", "identifier",
                ):
                    if name_node is not None:
                        default_str = _node_text(sub, source)

            # Check for default value via assignment pattern
            value_node = child.child_by_field_name("value")
            if value_node:
                default_str = _node_text(value_node, source)

            results.append(Parameter(
                name=_node_text(name_node, source) if name_node else "?",
                type=type_str,
                default=default_str,
            ))

        elif child.type == "rest_pattern":
            name = _node_text(child, source)
            results.append(Parameter(name=name))

        elif child.type == "object_pattern":
            results.append(Parameter(name=_node_text(child, source)))

        elif child.type == "array_pattern":
            results.append(Parameter(name=_node_text(child, source)))

    return results


def _extract_return_type(node: Node, source: bytes) -> str | None:
    """Extract the return type annotation from a function/method.

    In TS, the return type is a `type_annotation` child of the function
    node, appearing after the `formal_parameters`.
    """
    ret = node.child_by_field_name("return_type")
    if ret:
        # return_type field gives us the type_annotation node
        for child in ret.children:
            if child.type != ":":
                return _node_text(child, source)

    # Fallback: scan children for type_annotation after formal_parameters
    found_params = False
    for child in node.children:
        if child.type == "formal_parameters":
            found_params = True
        elif found_params and child.type == "type_annotation":
            for sub in child.children:
                if sub.type != ":":
                    return _node_text(sub, source)
            break
        elif found_params and child.type in ("statement_block", "{"):
            break

    return None


def _get_method_visibility(node: Node, source: bytes) -> str:
    """Extract visibility from accessibility_modifier on a method."""
    for child in node.children:
        if child.type == "accessibility_modifier":
            text = _node_text(child, source).strip()
            if text in ("public", "private", "protected"):
                return text
    return "public"  # TS default for class members is public


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_function_decl(node: Node, source: bytes, parent: str | None = None) -> Symbol:
    """Extract from function_declaration."""
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
        parameters=_extract_ts_params(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_method(node: Node, source: bytes, class_name: str) -> Symbol:
    """Extract from method_definition inside a class body."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_get_method_visibility(node, source),
        parent=class_name,
        docstring=_get_jsdoc(node, source),
        parameters=_extract_ts_params(params_node, source),
        return_type=_extract_return_type(node, source),
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


def _extract_interface(node: Node, source: bytes) -> Symbol:
    """Extract from interface_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="interface",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="unknown",
        docstring=_get_jsdoc(node, source),
    )


def _extract_type_alias(node: Node, source: bytes) -> Symbol:
    """Extract from type_alias_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="type_alias",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="unknown",
    )


def _extract_enum(node: Node, source: bytes) -> Symbol:
    """Extract from enum_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="enum",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="unknown",
    )


def _extract_imports(node: Node, source: bytes) -> list[Import]:
    """Extract from an import_statement (handles `import type` too)."""
    results: list[Import] = []
    line = node.start_point[0] + 1

    # Detect `import type` — has a `type` child between `import` and import_clause
    is_type_import = any(
        child.type == "type" for child in node.children
    )

    source_node = node.child_by_field_name("source")
    module = ""
    if source_node:
        raw = _node_text(source_node, source)
        module = raw.strip("'\"")

    plain_names: list[str] = []
    default_alias: str | None = None
    namespace_alias: str | None = None
    aliased_specifiers: list[tuple[str, str]] = []

    for child in node.children:
        if child.type == "import_clause":
            for sub in child.children:
                if sub.type == "identifier":
                    default_alias = _node_text(sub, source)
                elif sub.type == "named_imports":
                    for spec in sub.children:
                        if spec.type == "import_specifier":
                            name_n = spec.child_by_field_name("name")
                            alias_n = spec.child_by_field_name("alias")
                            if name_n:
                                original = _node_text(name_n, source)
                                if alias_n:
                                    aliased_specifiers.append(
                                        (original, _node_text(alias_n, source))
                                    )
                                else:
                                    plain_names.append(original)
                elif sub.type == "namespace_import":
                    plain_names.append("*")
                    for ns_child in sub.children:
                        if ns_child.type == "identifier":
                            namespace_alias = _node_text(ns_child, source)

    kind = "import_type" if is_type_import else "import"

    if plain_names or default_alias or namespace_alias:
        results.append(Import(
            module=module,
            names=plain_names,
            alias=default_alias or namespace_alias,
            line=line,
            kind=kind,
        ))

    for original, local_alias in aliased_specifiers:
        results.append(Import(
            module=module,
            names=[original],
            alias=local_alias,
            line=line,
            kind=kind,
        ))

    return results


def _extract_arrow_function(node: Node, source: bytes) -> Symbol | None:
    """Try to extract arrow function from lexical_declaration (same as JS)."""
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
                params: list[Parameter] = []
                if params_node and params_node.type == "formal_parameters":
                    params = _extract_ts_params(params_node, source)
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
                    return_type=_extract_return_type(value_node, source),
                )
    return None


def _extract_ts_exports(node: Node, source: bytes) -> list[Export]:
    """Extract from export_statement — extends JS version with TS types.

    Handles `export interface X`, `export type X`, `export enum X` in
    addition to everything the JS `_extract_exports` handles.
    """
    results = _extract_js_exports(node, source)
    line = node.start_point[0] + 1

    for child in node.children:
        if child.type == "interface_declaration":
            name_n = child.child_by_field_name("name")
            if name_n:
                results.append(Export(
                    name=_node_text(name_n, source),
                    kind="named",
                    line=line,
                ))
        elif child.type == "type_alias_declaration":
            name_n = child.child_by_field_name("name")
            if name_n:
                results.append(Export(
                    name=_node_text(name_n, source),
                    kind="type",
                    line=line,
                ))
        elif child.type == "enum_declaration":
            name_n = child.child_by_field_name("name")
            if name_n:
                results.append(Export(
                    name=_node_text(name_n, source),
                    kind="named",
                    line=line,
                ))

    return results


def _extract_constant(node: Node, source: bytes) -> Symbol | None:
    """Same logic as JS — const ALL_CAPS = value."""
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
# Main extractor
# ---------------------------------------------------------------------------


def extract_typescript(path: Path) -> FileExtraction:
    """Extract structural data from a TypeScript source file."""
    source = path.read_bytes()
    sha256 = hashlib.sha256(source).hexdigest()
    lines_list = source.split(b"\n")
    line_count = len(lines_list)
    if lines_list and lines_list[-1] == b"":
        line_count -= 1

    is_tsx = path.suffix.lower() == ".tsx"
    parser = _make_parser(tsx=is_tsx)
    tree = parser.parse(source)
    root = tree.root_node

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

            elif child.type == "interface_declaration":
                symbols.append(_extract_interface(child, source))

            elif child.type == "type_alias_declaration":
                symbols.append(_extract_type_alias(child, source))

            elif child.type == "enum_declaration":
                symbols.append(_extract_enum(child, source))

            elif child.type == "import_statement":
                imports.extend(_extract_imports(child, source))

            elif child.type == "export_statement":
                exports.extend(_extract_ts_exports(child, source))
                # Also extract declarations inside exports
                for sub in child.children:
                    if sub.type == "function_declaration":
                        symbols.append(_extract_function_decl(sub, source))
                    elif sub.type == "class_declaration":
                        cls, methods = _extract_class(sub, source)
                        symbols.append(cls)
                        symbols.extend(methods)
                    elif sub.type == "interface_declaration":
                        symbols.append(_extract_interface(sub, source))
                    elif sub.type == "type_alias_declaration":
                        symbols.append(_extract_type_alias(sub, source))
                    elif sub.type == "enum_declaration":
                        symbols.append(_extract_enum(sub, source))
                    elif sub.type == "lexical_declaration":
                        arrow = _extract_arrow_function(sub, source)
                        if arrow:
                            symbols.append(arrow)
                        else:
                            const = _extract_constant(sub, source)
                            if const:
                                symbols.append(const)

            elif child.type == "lexical_declaration":
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

    # Apply export visibility
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
        language="typescript",
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
    """Re-find a function/method node by name."""
    if parent:
        for child in root.children:
            node = child
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
                        if nn and _node_text(nn, source) == name and vn and vn.type == "arrow_function":
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
                                if nn and _node_text(nn, source) == name and vn and vn.type == "arrow_function":
                                    return vn
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".ts", ".tsx"], extract_typescript)
