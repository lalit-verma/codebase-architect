"""Rust structural extractor (milestone B9).

Rust-specific handling:
  - `impl_item` blocks: methods live inside `impl Type { ... }` or
    `impl Trait for Type { ... }`. Parent is the impl target type.
  - `trait_item`: trait definitions with `function_signature_item`
    (abstract method signatures without bodies).
  - `struct_item`, `enum_item`, `type_item` (type alias), `const_item`.
  - `pub` visibility modifier. No modifier = private (crate-private).
    `pub(crate)` = package-level.
  - `///` doc comments: `line_comment` nodes with `outer_doc_comment_marker`.
  - `use_declaration`: simple, nested (`{A, B}`), and glob (`*`).
  - Parameters via `parameters` node with `parameter` + `self_parameter`.
  - Return type after `-> ` between parameters and block.

Pass 1: top-level declarations (functions, impl methods, structs, traits,
         enums, type aliases, constants, imports)
Pass 2: call edges within function/method bodies
Pass 3: rationale comments
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_rust as tsrust
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import RATIONALE_TAGS, extract_rationale_comments, is_rust_doc
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

_LANGUAGE = Language(tsrust.language())


def _make_parser() -> Parser:
    return Parser(_LANGUAGE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

    # _COMMENT_TAGS moved to shared _comments.py module


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _first_line(node: Node, source: bytes) -> str:
    return _node_text(node, source).split("\n")[0].rstrip()


def _rust_visibility(node: Node, source: bytes) -> str:
    """Extract Rust visibility from a node's children."""
    for child in node.children:
        if child.type == "visibility_modifier":
            text = _node_text(child, source).strip()
            if text == "pub":
                return "public"
            elif text.startswith("pub("):
                return "package"  # pub(crate), pub(super), etc.
    return "private"


def _get_rust_doc(node: Node, source: bytes) -> str | None:
    """Extract /// doc comments from preceding siblings.

    Rust doc comments are `line_comment` nodes that contain an
    `outer_doc_comment_marker` (the third `/`). We collect consecutive
    doc-comment lines before the declaration.
    """
    comments: list[str] = []
    prev = node.prev_named_sibling
    while prev and prev.type == "line_comment":
        text = _node_text(prev, source)
        # Check if this is a doc comment (///) vs regular (//)
        is_doc = any(
            child.type == "outer_doc_comment_marker" for child in prev.children
        )
        if is_doc:
            # Extract the doc_comment content
            for child in prev.children:
                if child.type == "doc_comment":
                    comments.insert(0, _node_text(child, source).strip())
                    break
        else:
            # Regular comment — not a doc comment, stop looking
            # But first check if it's a rationale tag (those appear before doc comments sometimes)
            stripped = text.lstrip("/ ").strip()
            tag_match = any(
                stripped.upper().startswith(tag + ":")
                for tag in RATIONALE_TAGS
            )
            if tag_match:
                prev = prev.prev_named_sibling
                continue
            break
        prev = prev.prev_named_sibling

    return " ".join(comments).strip() if comments else None


def _extract_rust_params(params_node: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from Rust `parameters` node."""
    if params_node is None:
        return []

    results: list[Parameter] = []
    for child in params_node.children:
        if child.type == "self_parameter":
            results.append(Parameter(name=_node_text(child, source)))

        elif child.type == "parameter":
            name: str | None = None
            type_str: str | None = None

            pattern = child.child_by_field_name("pattern")
            type_node = child.child_by_field_name("type")

            if pattern:
                name = _node_text(pattern, source)
            if type_node:
                type_str = _node_text(type_node, source)

            if name:
                results.append(Parameter(name=name, type=type_str))

    return results


def _extract_return_type(node: Node, source: bytes) -> str | None:
    """Extract return type from a function_item.

    In Rust, the return type comes after `->` between parameters and block.
    """
    ret = node.child_by_field_name("return_type")
    if ret:
        return _node_text(ret, source)

    # Fallback: scan for `->` then capture the next type node
    found_arrow = False
    for child in node.children:
        if _node_text(child, source) == "->":
            found_arrow = True
        elif found_arrow and child.type == "block":
            break
        elif found_arrow and child.type not in ("->", "line_comment"):
            return _node_text(child, source)

    return None


def _get_impl_type(node: Node, source: bytes) -> str | None:
    """Extract the target type name from an impl_item.

    `impl Type { ... }` → "Type"
    `impl Trait for Type { ... }` → "Type" (the concrete type after `for`)
    """
    # If there's a `for` keyword, the type is after it
    has_for = False
    for child in node.children:
        if child.type == "for":
            has_for = True
        elif has_for and child.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
            text = _node_text(child, source)
            # Strip generics: InMemoryRepo<T> → InMemoryRepo
            if "<" in text:
                text = text[:text.index("<")]
            return text

    # No `for` → inherent impl, type is the first type after `impl`
    found_impl = False
    for child in node.children:
        if child.type == "impl":
            found_impl = True
        elif found_impl and child.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
            text = _node_text(child, source)
            if "<" in text:
                text = text[:text.index("<")]
            return text
        elif found_impl and child.type == "declaration_list":
            break

    return None


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_function(node: Node, source: bytes, parent: str | None = None) -> Symbol:
    """Extract from function_item."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method" if parent else "function",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
        parent=parent,
        docstring=_get_rust_doc(node, source),
        parameters=_extract_rust_params(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_trait_method(node: Node, source: bytes, trait_name: str) -> Symbol:
    """Extract from function_signature_item inside a trait."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility="public",  # trait methods are always public
        parent=trait_name,
        parameters=_extract_rust_params(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_struct(node: Node, source: bytes) -> Symbol:
    """Extract from struct_item."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="struct",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
        docstring=_get_rust_doc(node, source),
    )


def _extract_trait(node: Node, source: bytes) -> tuple[Symbol, list[Symbol]]:
    """Extract from trait_item, including method signatures."""
    name_node = node.child_by_field_name("name")
    trait_name = _node_text(name_node, source) if name_node else "<anonymous>"
    body = node.child_by_field_name("body")

    trait_sym = Symbol(
        name=trait_name,
        kind="trait",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
        docstring=_get_rust_doc(node, source),
    )

    methods: list[Symbol] = []
    if body:
        for child in body.children:
            if child.type == "function_signature_item":
                methods.append(_extract_trait_method(child, source, trait_name))
            elif child.type == "function_item":
                # Default implementation in trait
                methods.append(_extract_function(child, source, parent=trait_name))

    return trait_sym, methods


def _extract_enum(node: Node, source: bytes) -> Symbol:
    """Extract from enum_item."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="enum",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
        docstring=_get_rust_doc(node, source),
    )


def _extract_type_alias(node: Node, source: bytes) -> Symbol:
    """Extract from type_item."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="type_alias",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
        docstring=_get_rust_doc(node, source),
    )


def _extract_const(node: Node, source: bytes) -> Symbol:
    """Extract from const_item."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    return Symbol(
        name=name,
        kind="constant",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_rust_visibility(node, source),
    )


def _extract_impl(node: Node, source: bytes) -> list[Symbol]:
    """Extract methods from an impl_item block."""
    impl_type = _get_impl_type(node, source)
    body = node.child_by_field_name("body")

    methods: list[Symbol] = []
    if body:
        for child in body.children:
            if child.type == "function_item":
                methods.append(_extract_function(child, source, parent=impl_type))

    return methods


def _extract_use(node: Node, source: bytes) -> list[Import]:
    """Extract from use_declaration.

    Handles:
    - Simple: `use std::collections::HashMap;`
    - Nested: `use std::io::{self, Read, Write};`
    - Glob: `use std::io::*;`
    """
    results: list[Import] = []
    line = node.start_point[0] + 1

    for child in node.children:
        if child.type == "use_as_clause":
            # Aliased: use std::collections::HashMap as Map
            scoped = None
            alias_name = None
            for sub in child.children:
                if sub.type == "scoped_identifier":
                    scoped = _node_text(sub, source)
                elif sub.type == "identifier":
                    alias_name = _node_text(sub, source)
            if scoped:
                parts = scoped.rsplit("::", 1)
                if len(parts) == 2:
                    mod, name = parts
                else:
                    mod, name = scoped, ""
                results.append(Import(
                    module=mod,
                    names=[name] if name else [],
                    alias=alias_name,
                    line=line,
                    kind="use",
                ))

        elif child.type == "scoped_identifier":
            # Simple: use std::collections::HashMap
            full_path = _node_text(child, source)
            parts = full_path.rsplit("::", 1)
            if len(parts) == 2:
                mod, name = parts
            else:
                mod, name = full_path, ""
            results.append(Import(
                module=mod,
                names=[name] if name else [],
                line=line,
                kind="use",
            ))

        elif child.type == "scoped_use_list":
            # Nested: use std::io::{self, Read, Write, Read as IoRead}
            module = ""
            plain_names: list[str] = []
            aliased_items: list[tuple[str, str]] = []  # (original, alias)

            for sub in child.children:
                if sub.type == "scoped_identifier":
                    module = _node_text(sub, source)
                elif sub.type == "use_list":
                    for item in sub.children:
                        if item.type == "identifier":
                            plain_names.append(_node_text(item, source))
                        elif item.type == "self":
                            plain_names.append("self")
                        elif item.type == "scoped_identifier":
                            plain_names.append(_node_text(item, source))
                        elif item.type == "use_as_clause":
                            # Read as IoRead inside grouped use
                            original_name = None
                            alias_name = None
                            for inner in item.children:
                                if inner.type in ("identifier", "scoped_identifier"):
                                    if original_name is None:
                                        original_name = _node_text(inner, source)
                                    else:
                                        alias_name = _node_text(inner, source)
                            if original_name:
                                aliased_items.append((original_name, alias_name or original_name))

            # Plain names in one Import
            if plain_names:
                results.append(Import(
                    module=module,
                    names=plain_names,
                    line=line,
                    kind="use",
                ))

            # Each aliased item gets its own Import (same pattern as JS/TS)
            for original, alias in aliased_items:
                results.append(Import(
                    module=module,
                    names=[original],
                    alias=alias,
                    line=line,
                    kind="use",
                ))

        elif child.type == "use_wildcard":
            # Glob: use std::io::*
            text = _node_text(child, source)
            module = text.rsplit("::*", 1)[0] if "::*" in text else text
            results.append(Import(
                module=module,
                names=["*"],
                line=line,
                kind="use",
            ))

    return results


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
                # Strip self.: self.store.get → store.get
                if callee.startswith("self."):
                    callee = callee[5:]
                edges.append(CallEdge(
                    caller=caller,
                    callee=callee,
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))
        # Don't recurse into closures or nested functions
        if node.type not in ("closure_expression", "function_item"):
            stack.extend(node.children)

    return edges


    # Pass 3 (rationale comments) uses the shared module from _comments.py


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract_rust(path: Path) -> FileExtraction:
    """Extract structural data from a Rust source file."""
    source = path.read_bytes()
    sha256 = hashlib.sha256(source).hexdigest()
    lines_list = source.split(b"\n")
    line_count = len(lines_list)
    if lines_list and lines_list[-1] == b"":
        line_count -= 1

    parser = _make_parser()
    tree = parser.parse(source)
    root = tree.root_node

    symbols: list[Symbol] = []
    imports: list[Import] = []
    errors: list[str] = []

    for child in root.children:
        try:
            if child.type == "function_item":
                symbols.append(_extract_function(child, source))

            elif child.type == "struct_item":
                symbols.append(_extract_struct(child, source))

            elif child.type == "trait_item":
                trait_sym, methods = _extract_trait(child, source)
                symbols.append(trait_sym)
                symbols.extend(methods)

            elif child.type == "enum_item":
                symbols.append(_extract_enum(child, source))

            elif child.type == "type_item":
                symbols.append(_extract_type_alias(child, source))

            elif child.type == "const_item":
                symbols.append(_extract_const(child, source))

            elif child.type == "impl_item":
                symbols.extend(_extract_impl(child, source))

            elif child.type == "use_declaration":
                imports.extend(_extract_use(child, source))

        except Exception as e:
            errors.append(f"Error at line {child.start_point[0]+1}: {e}")

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
        comment_node_types=frozenset({"line_comment"}),
        is_doc_comment=is_rust_doc,
    )

    return FileExtraction(
        file_path=str(path),
        language="rust",
        sha256=sha256,
        file_size_bytes=len(source),
        line_count=line_count,
        symbols=symbols,
        imports=imports,
        exports=[],  # Rust uses pub visibility, not export statements
        call_edges=call_edges,
        rationale_comments=rationale_comments,
        extraction_errors=errors,
    )


def _find_function_node(
    root: Node, source: bytes, name: str, parent: str | None,
) -> Node | None:
    """Re-find a function_item node for call-edge extraction.

    Searches both impl_item blocks AND trait_item blocks (for default
    method implementations that have bodies).
    """
    if parent:
        for child in root.children:
            if child.type == "impl_item":
                impl_type = _get_impl_type(child, source)
                if impl_type == parent:
                    body = child.child_by_field_name("body")
                    if body:
                        for member in body.children:
                            if member.type == "function_item":
                                nn = member.child_by_field_name("name")
                                if nn and _node_text(nn, source) == name:
                                    return member
            elif child.type == "trait_item":
                # Trait default methods: function_item inside trait body
                name_node = child.child_by_field_name("name")
                if name_node and _node_text(name_node, source) == parent:
                    body = child.child_by_field_name("body")
                    if body:
                        for member in body.children:
                            if member.type == "function_item":
                                nn = member.child_by_field_name("name")
                                if nn and _node_text(nn, source) == name:
                                    return member
    else:
        for child in root.children:
            if child.type == "function_item":
                nn = child.child_by_field_name("name")
                if nn and _node_text(nn, source) == name:
                    return child
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".rs"], extract_rust)
