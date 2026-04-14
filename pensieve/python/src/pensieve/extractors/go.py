"""Go structural extractor (milestone B7).

Go has a fundamentally different structure from JS/TS/Python:
  - No classes. Structs + methods with receivers.
  - Visibility by capitalization: Uppercase = exported/public,
    lowercase = unexported/private.
  - Interfaces defined via `type X interface { ... }`.
  - Constants via `const` declarations.
  - Multiple return values.
  - Doc comments as `//` comments preceding a declaration.

Pass 1: top-level declarations (functions, methods, structs, interfaces,
         constants, imports)
Pass 2: call edges within function/method bodies
Pass 3: rationale comments
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_go as tsgo
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import RATIONALE_TAGS, extract_rationale_comments
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

_LANGUAGE = Language(tsgo.language())


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


def _go_visibility(name: str) -> str:
    """Go visibility: uppercase first letter = public, lowercase = private."""
    if name and name[0].isupper():
        return "public"
    return "private"


def _get_go_doc(node: Node, source: bytes) -> str | None:
    """Extract Go doc comment from preceding comment siblings.

    Go convention: one or more `//` comment lines immediately before a
    declaration. We collect all consecutive preceding comments.
    """
    comments: list[str] = []
    prev = node.prev_named_sibling
    while prev and prev.type == "comment":
        text = _node_text(prev, source)
        # Strip // prefix
        if text.startswith("//"):
            text = text[2:].strip()
        comments.insert(0, text)
        prev = prev.prev_named_sibling

    if not comments:
        return None

    # Filter out rationale tags — those are not docstrings
    doc_lines = []
    for line in comments:
        is_tag = any(
            tag.lower() in line.lower().split(":")[0]
            for tag in RATIONALE_TAGS
        ) if ":" in line else False
        if not is_tag:
            doc_lines.append(line)

    return " ".join(doc_lines).strip() if doc_lines else None


def _extract_go_params(param_list: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from a Go parameter_list.

    Go params can share types: `username, password string` → two params
    both of type `string`.
    """
    if param_list is None:
        return []

    results: list[Parameter] = []
    for child in param_list.children:
        if child.type == "parameter_declaration":
            # Collect all identifier children (names) and the type
            names: list[str] = []
            type_str: str | None = None

            for sub in child.children:
                if sub.type == "identifier":
                    names.append(_node_text(sub, source))
                elif sub.type in (
                    "type_identifier", "pointer_type", "slice_type",
                    "array_type", "map_type", "channel_type",
                    "qualified_type", "interface_type", "struct_type",
                    "function_type",
                ):
                    type_str = _node_text(sub, source)

            if names:
                for name in names:
                    results.append(Parameter(name=name, type=type_str))
            elif type_str:
                # Unnamed parameter (common in return types): just a type
                results.append(Parameter(name=type_str, type=type_str))

        elif child.type == "variadic_parameter_declaration":
            text = _node_text(child, source)
            results.append(Parameter(name=text))

    return results


def _extract_return_type(node: Node, source: bytes) -> str | None:
    """Extract return type from a Go function/method declaration.

    Go can have:
    - No return: `func foo() { ... }`
    - Single unnamed: `func foo() string { ... }`
    - Multiple unnamed: `func foo() (string, error) { ... }`
    - Named returns: `func foo() (result string, err error) { ... }`

    We capture the text of the return type expression.
    """
    # For function_declaration: children are func, name, params, [return_type...], block
    # For method_declaration: children are func, receiver, name, params, [return_type...], block
    # The return types are between the params and the block.

    found_params = False
    param_count = 0
    is_method = node.type == "method_declaration"

    for child in node.children:
        if child.type == "parameter_list":
            param_count += 1
            if found_params:
                # Already past the params → this is the return type list
                return _node_text(child, source)
            elif is_method and param_count >= 2:
                found_params = True
            elif not is_method and param_count >= 1:
                found_params = True
        elif found_params and child.type == "block":
            break
        elif found_params and child.type in (
            "type_identifier", "pointer_type", "slice_type",
            "array_type", "map_type", "qualified_type",
        ):
            return _node_text(child, source)

    return None


def _get_receiver_type(node: Node, source: bytes) -> str | None:
    """Extract the receiver type from a method_declaration.

    `func (s *Service) Authenticate(...)` → "Service"
    `func (s Service) String()` → "Service"
    """
    if node.type != "method_declaration":
        return None

    # First parameter_list is the receiver
    for child in node.children:
        if child.type == "parameter_list":
            for param in child.children:
                if param.type == "parameter_declaration":
                    # Find the type in the parameter
                    for sub in param.children:
                        if sub.type == "pointer_type":
                            # *Service → get the identifier inside
                            for inner in sub.children:
                                if inner.type == "type_identifier":
                                    return _node_text(inner, source)
                        elif sub.type == "type_identifier":
                            return _node_text(sub, source)
            return None  # found receiver param_list but no type
    return None


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_function(node: Node, source: bytes) -> Symbol:
    """Extract from function_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"

    # Parameters: first (and only) parameter_list
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="function",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_go_visibility(name),
        docstring=_get_go_doc(node, source),
        parameters=_extract_go_params(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_method(node: Node, source: bytes) -> Symbol:
    """Extract from method_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    receiver_type = _get_receiver_type(node, source)

    # Parameters: second parameter_list (first is receiver)
    param_lists = [c for c in node.children if c.type == "parameter_list"]
    params_node = param_lists[1] if len(param_lists) >= 2 else None

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_go_visibility(name),
        parent=receiver_type,
        docstring=_get_go_doc(node, source),
        parameters=_extract_go_params(params_node, source),
        return_type=_extract_return_type(node, source),
    )


def _extract_type_decl(node: Node, source: bytes) -> list[Symbol]:
    """Extract from type_declaration (struct or interface).

    Handles grouped `type (...)` blocks with multiple type_spec children.
    Returns a list of symbols (one per type_spec).
    """
    results: list[Symbol] = []
    for child in node.children:
        if child.type == "type_spec":
            name_node = child.child_by_field_name("name")
            name = _node_text(name_node, source) if name_node else "<anonymous>"

            # Determine kind from the type body
            kind: str | None = None
            for sub in child.children:
                if sub.type == "struct_type":
                    kind = "struct"
                elif sub.type == "interface_type":
                    kind = "interface"

            if kind:
                # Doc comment: check type_spec first (grouped block),
                # then type_declaration (non-grouped single type)
                doc = _get_go_doc(child, source) or _get_go_doc(node, source)
                results.append(Symbol(
                    name=name,
                    kind=kind,
                    line_start=child.start_point[0] + 1,
                    line_end=child.end_point[0] + 1,
                    signature=_first_line(child, source),
                    visibility=_go_visibility(name),
                    docstring=doc,
                ))
    return results


def _extract_const(node: Node, source: bytes) -> list[Symbol]:
    """Extract from const_declaration (can have multiple const_spec).

    Handles both grouped `const (A = 1; B = 2)` and multi-name
    `const A, B = 1, 2` (where one const_spec has multiple identifiers).
    """
    results: list[Symbol] = []
    for child in node.children:
        if child.type == "const_spec":
            # Collect ALL identifiers in this const_spec (handles
            # `const A, B = 1, 2` where one spec has multiple names)
            for sub in child.children:
                if sub.type == "identifier":
                    name = _node_text(sub, source)
                    results.append(Symbol(
                        name=name,
                        kind="constant",
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=_first_line(child, source),
                        visibility=_go_visibility(name),
                    ))
    return results


def _extract_imports(node: Node, source: bytes) -> list[Import]:
    """Extract from import_declaration."""
    results: list[Import] = []
    line = node.start_point[0] + 1

    for child in node.children:
        if child.type == "import_spec_list":
            for spec in child.children:
                if spec.type == "import_spec":
                    imp = _parse_import_spec(spec, source)
                    if imp:
                        results.append(imp)
        elif child.type == "import_spec":
            # Single import: `import "fmt"`
            imp = _parse_import_spec(child, source)
            if imp:
                results.append(imp)

    return results


def _parse_import_spec(node: Node, source: bytes) -> Import | None:
    """Parse a single import_spec node."""
    line = node.start_point[0] + 1
    module = ""
    alias = None

    for child in node.children:
        if child.type == "interpreted_string_literal":
            module = _node_text(child, source).strip('"')
        elif child.type == "package_identifier" or child.type == "identifier":
            alias = _node_text(child, source)
        elif child.type == "blank_identifier":
            alias = "_"
        elif child.type == "dot":
            alias = "."

    if module:
        return Import(module=module, alias=alias, line=line, kind="import")
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
                # Strip receiver: s.repo.FindByID → repo.FindByID
                # But keep package calls: fmt.Errorf → fmt.Errorf
                edges.append(CallEdge(
                    caller=caller,
                    callee=callee,
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))
        # Don't recurse into nested functions (func literals)
        if node.type not in ("func_literal",):
            stack.extend(node.children)

    return edges


    # Pass 3 (rationale comments) uses the shared module from _comments.py


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract_go(path: Path) -> FileExtraction:
    """Extract structural data from a Go source file."""
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
            if child.type == "function_declaration":
                symbols.append(_extract_function(child, source))

            elif child.type == "method_declaration":
                symbols.append(_extract_method(child, source))

            elif child.type == "type_declaration":
                symbols.extend(_extract_type_decl(child, source))

            elif child.type == "const_declaration":
                symbols.extend(_extract_const(child, source))

            elif child.type == "import_declaration":
                imports.extend(_extract_imports(child, source))

        except Exception as e:
            errors.append(f"Error at line {child.start_point[0]+1}: {e}")

    # --- Pass 2: call edges ---
    call_edges: list[CallEdge] = []
    for sym in symbols:
        if sym.kind in ("function", "method"):
            func_node = _find_function_node(root, source, sym.name, sym.kind, sym.parent)
            if func_node:
                body = func_node.child_by_field_name("body")
                call_edges.extend(_collect_calls(body, source, sym.name))

    # --- Pass 3: rationale comments (shared module) ---
    symbol_ranges = [(s.name, s.line_start, s.line_end) for s in symbols]
    rationale_comments = extract_rationale_comments(
        root, source, symbol_ranges,
        comment_node_types=frozenset({"comment"}),
        is_doc_comment=None,  # Go doc comments are regular // comments; tag matching handles the distinction
    )

    return FileExtraction(
        file_path=str(path),
        language="go",
        sha256=sha256,
        file_size_bytes=len(source),
        line_count=line_count,
        symbols=symbols,
        imports=imports,
        exports=[],  # Go uses capitalization, not export statements
        call_edges=call_edges,
        rationale_comments=rationale_comments,
        extraction_errors=errors,
    )


def _find_function_node(
    root: Node, source: bytes, name: str, kind: str, parent: str | None,
) -> Node | None:
    """Re-find a function/method node for call-edge extraction."""
    for child in root.children:
        if kind == "function" and child.type == "function_declaration":
            nn = child.child_by_field_name("name")
            if nn and _node_text(nn, source) == name:
                return child
        elif kind == "method" and child.type == "method_declaration":
            nn = child.child_by_field_name("name")
            receiver = _get_receiver_type(child, source)
            if nn and _node_text(nn, source) == name and receiver == parent:
                return child
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".go"], extract_go)
