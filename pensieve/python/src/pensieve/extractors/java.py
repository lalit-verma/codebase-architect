"""Java structural extractor (milestone B8).

Java-specific handling:
  - Access modifiers: `public`/`private`/`protected` in `modifiers` node.
    No modifier = package-private ("package" visibility).
  - Classes, interfaces, enums as top-level declarations.
  - Methods + constructors inside class bodies.
  - Javadoc (`/** ... */`) as preceding `block_comment` sibling.
  - `import_declaration` with `scoped_identifier`.
  - Constants: `static final` fields (typically ALL_CAPS).
  - Annotations (`@Override`, `@Inject`) noted in signatures.
  - `method_invocation` for call edges (not `call_expression` like JS).

Pass 1: top-level declarations
Pass 2: call edges within method/constructor bodies
Pass 3: rationale comments
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser

from pensieve.extractors import register
from pensieve.extractors._comments import extract_rationale_comments, is_jsdoc
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

_LANGUAGE = Language(tsjava.language())


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


def _get_javadoc(node: Node, source: bytes) -> str | None:
    """Extract Javadoc from the preceding sibling block_comment."""
    prev = node.prev_named_sibling
    if prev and prev.type == "block_comment":
        text = _node_text(prev, source)
        if text.startswith("/**"):
            cleaned = text[3:]
            if cleaned.endswith("*/"):
                cleaned = cleaned[:-2]
            lines = []
            for line in cleaned.split("\n"):
                line = line.strip()
                if line.startswith("*"):
                    line = line[1:].strip()
                # Skip @param, @return, @throws tags
                if line.startswith("@"):
                    continue
                if line:
                    lines.append(line)
            return " ".join(lines) if lines else None
    return None


def _get_visibility(node: Node, source: bytes) -> str:
    """Extract Java visibility from modifiers node."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                text = _node_text(mod, source)
                if text == "public":
                    return "public"
                elif text == "private":
                    return "private"
                elif text == "protected":
                    return "protected"
    return "package"  # Java default: package-private


def _has_modifier(node: Node, source: bytes, modifier: str) -> bool:
    """Check if a node's modifiers contain a specific keyword."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                if _node_text(mod, source) == modifier:
                    return True
    return False


def _extract_java_params(params_node: Node | None, source: bytes) -> list[Parameter]:
    """Extract parameters from formal_parameters."""
    if params_node is None:
        return []

    results: list[Parameter] = []
    for child in params_node.children:
        if child.type == "formal_parameter":
            name: str | None = None
            type_str: str | None = None

            for sub in child.children:
                if sub.type == "identifier":
                    name = _node_text(sub, source)
                elif sub.type in (
                    "type_identifier", "generic_type", "array_type",
                    "integral_type", "floating_point_type", "boolean_type",
                    "scoped_type_identifier", "void_type",
                ):
                    type_str = _node_text(sub, source)

            if name:
                results.append(Parameter(name=name, type=type_str))

        elif child.type == "spread_parameter":
            # varargs: String... args
            text = _node_text(child, source)
            results.append(Parameter(name=text))

    return results


def _extract_method_return_type(node: Node, source: bytes) -> str | None:
    """Extract the return type from a method_declaration.

    The return type is a type child appearing before the method name.
    Could be: type_identifier, generic_type, void_type, array_type,
    integral_type, etc.
    """
    # In tree-sitter-java, the type is a named child before the name identifier
    type_node = node.child_by_field_name("type")
    if type_node:
        return _node_text(type_node, source)

    # Fallback: scan children for a type before the name
    for child in node.children:
        if child.type == "identifier":
            break  # hit the name without finding a type
        if child.type in (
            "type_identifier", "generic_type", "void_type",
            "array_type", "integral_type", "floating_point_type",
            "boolean_type", "scoped_type_identifier",
        ):
            return _node_text(child, source)

    return None


# ---------------------------------------------------------------------------
# Pass 1: Top-level declarations
# ---------------------------------------------------------------------------


def _extract_class(node: Node, source: bytes) -> tuple[Symbol, list[Symbol]]:
    """Extract a class and its methods/constructors."""
    name_node = node.child_by_field_name("name")
    class_name = _node_text(name_node, source) if name_node else "<anonymous>"
    body = node.child_by_field_name("body")

    class_sym = Symbol(
        name=class_name,
        kind="class",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_get_visibility(node, source),
        docstring=_get_javadoc(node, source),
    )

    members: list[Symbol] = []
    if body:
        for child in body.children:
            if child.type == "method_declaration":
                members.append(_extract_method(child, source, class_name))
            elif child.type == "constructor_declaration":
                members.append(_extract_constructor(child, source, class_name))
            elif child.type == "field_declaration":
                const = _extract_field_constant(child, source, class_name)
                if const:
                    members.append(const)

    return class_sym, members


def _extract_method(node: Node, source: bytes, parent: str | None = None) -> Symbol:
    """Extract from method_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_get_visibility(node, source),
        parent=parent,
        docstring=_get_javadoc(node, source),
        parameters=_extract_java_params(params_node, source),
        return_type=_extract_method_return_type(node, source),
    )


def _extract_constructor(node: Node, source: bytes, class_name: str) -> Symbol:
    """Extract from constructor_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else class_name
    params_node = node.child_by_field_name("parameters")

    return Symbol(
        name=name,
        kind="method",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_get_visibility(node, source),
        parent=class_name,
        docstring=_get_javadoc(node, source),
        parameters=_extract_java_params(params_node, source),
    )


def _extract_interface(node: Node, source: bytes) -> tuple[Symbol, list[Symbol]]:
    """Extract from interface_declaration."""
    name_node = node.child_by_field_name("name")
    name = _node_text(name_node, source) if name_node else "<anonymous>"
    body = node.child_by_field_name("body")

    iface_sym = Symbol(
        name=name,
        kind="interface",
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=_first_line(node, source),
        visibility=_get_visibility(node, source),
        docstring=_get_javadoc(node, source),
    )

    # Interface methods (abstract, no body)
    methods: list[Symbol] = []
    if body:
        for child in body.children:
            if child.type == "method_declaration":
                methods.append(_extract_method(child, source, name))

    return iface_sym, methods


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
        visibility=_get_visibility(node, source),
        docstring=_get_javadoc(node, source),
    )


def _extract_field_constant(
    node: Node, source: bytes, class_name: str,
) -> Symbol | None:
    """Try to extract a constant from a field_declaration.

    Java constants are `static final` fields, typically ALL_CAPS.
    """
    is_static = _has_modifier(node, source, "static")
    is_final = _has_modifier(node, source, "final")

    if not (is_static and is_final):
        return None

    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source)
                if _CONSTANT_RE.match(name):
                    return Symbol(
                        name=name,
                        kind="constant",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        signature=_first_line(node, source),
                        visibility=_get_visibility(node, source),
                        parent=class_name,
                    )
    return None


def _extract_imports(node: Node, source: bytes) -> Import:
    """Extract from import_declaration.

    Handles:
    - Regular: `import java.util.List;` → module=java.util, names=[List]
    - Wildcard: `import java.util.*;` → module=java.util, names=[*]
    - Static: `import static java.util.Collections.sort;`
    - Static wildcard: `import static java.util.Collections.*;`
    """
    line = node.start_point[0] + 1

    # Collect the scoped identifier (the path before any wildcard)
    module = ""
    for child in node.children:
        if child.type in ("scoped_identifier", "identifier"):
            module = _node_text(child, source)

    # Check for wildcard (asterisk child)
    is_wildcard = any(child.type == "asterisk" for child in node.children)

    # Check for static import
    is_static = any(
        _node_text(c, source) == "static" for c in node.children
    )

    if is_wildcard:
        # `import java.util.*;` → module=java.util, names=["*"]
        # The scoped_identifier is already the module path (java.util)
        return Import(
            module=module,
            names=["*"],
            line=line,
            kind="static_import" if is_static else "import",
        )
    else:
        # `import java.util.List;` → module=java.util, names=[List]
        parts = module.rsplit(".", 1)
        if len(parts) == 2:
            mod, name = parts
        else:
            mod, name = module, ""

        return Import(
            module=mod,
            names=[name] if name else [],
            line=line,
            kind="static_import" if is_static else "import",
        )


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
        if node.type == "method_invocation":
            # method_invocation has: object.method(args) or method(args)
            name_node = node.child_by_field_name("name")
            obj_node = node.child_by_field_name("object")

            if name_node:
                callee_name = _node_text(name_node, source)
                if obj_node:
                    obj_text = _node_text(obj_node, source)
                    if obj_text == "this":
                        callee = callee_name
                    else:
                        callee = f"{obj_text}.{callee_name}"
                else:
                    callee = callee_name

                edges.append(CallEdge(
                    caller=caller,
                    callee=callee,
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))

        elif node.type == "object_creation_expression":
            # `new Foo(args)` — treat as a call to the constructor
            type_node = node.child_by_field_name("type")
            if type_node:
                edges.append(CallEdge(
                    caller=caller,
                    callee=f"new {_node_text(type_node, source)}",
                    line=node.start_point[0] + 1,
                    confidence=1.0,
                ))

        # Don't recurse into nested classes or lambdas
        if node.type not in (
            "class_declaration", "lambda_expression",
            "anonymous_class_body",
        ):
            stack.extend(node.children)

    return edges


    # Pass 3 (rationale comments) uses the shared module from _comments.py


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract_java(path: Path) -> FileExtraction:
    """Extract structural data from a Java source file."""
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
            if child.type == "class_declaration":
                cls, members = _extract_class(child, source)
                symbols.append(cls)
                symbols.extend(members)

            elif child.type == "interface_declaration":
                iface, methods = _extract_interface(child, source)
                symbols.append(iface)
                symbols.extend(methods)

            elif child.type == "enum_declaration":
                symbols.append(_extract_enum(child, source))

            elif child.type == "import_declaration":
                imports.append(_extract_imports(child, source))

            elif child.type == "local_variable_declaration":
                # Top-level `public static final` constant
                is_static = _has_modifier(child, source, "static")
                is_final = _has_modifier(child, source, "final")
                if is_static and is_final:
                    for sub in child.children:
                        if sub.type == "variable_declarator":
                            name_node = sub.child_by_field_name("name")
                            if name_node:
                                name = _node_text(name_node, source)
                                if _CONSTANT_RE.match(name):
                                    symbols.append(Symbol(
                                        name=name,
                                        kind="constant",
                                        line_start=child.start_point[0] + 1,
                                        line_end=child.end_point[0] + 1,
                                        signature=_first_line(child, source),
                                        visibility=_get_visibility(child, source),
                                    ))

        except Exception as e:
            errors.append(f"Error at line {child.start_point[0]+1}: {e}")

    # --- Pass 2: call edges ---
    call_edges: list[CallEdge] = []
    for sym in symbols:
        if sym.kind == "method" and sym.parent:
            func_node = _find_method_node(
                root, source, sym.name, sym.parent, sym.line_start,
            )
            if func_node:
                body = func_node.child_by_field_name("body")
                call_edges.extend(_collect_calls(body, source, sym.name))

    # --- Pass 3: rationale comments (shared module) ---
    symbol_ranges = [(s.name, s.line_start, s.line_end) for s in symbols]
    rationale_comments = extract_rationale_comments(
        root, source, symbol_ranges,
        comment_node_types=frozenset({"line_comment", "block_comment"}),
        is_doc_comment=is_jsdoc,  # Javadoc uses same /** */ syntax as JSDoc
    )

    return FileExtraction(
        file_path=str(path),
        language="java",
        sha256=sha256,
        file_size_bytes=len(source),
        line_count=line_count,
        symbols=symbols,
        imports=imports,
        exports=[],  # Java uses access modifiers, not export statements
        call_edges=call_edges,
        rationale_comments=rationale_comments,
        extraction_errors=errors,
    )


def _find_method_node(
    root: Node, source: bytes, name: str, parent: str, line_start: int,
) -> Node | None:
    """Re-find a method/constructor node for call-edge extraction.

    Uses line_start to disambiguate overloaded methods (multiple methods
    with the same name in the same class). Without this, the first
    overload wins and the rest get no call edges.
    """
    for child in root.children:
        if child.type in ("class_declaration", "interface_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node and _node_text(name_node, source) == parent:
                body = child.child_by_field_name("body")
                if body:
                    for member in body.children:
                        if member.type in ("method_declaration", "constructor_declaration"):
                            mn = member.child_by_field_name("name")
                            if (
                                mn
                                and _node_text(mn, source) == name
                                and member.start_point[0] + 1 == line_start
                            ):
                                return member
    return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register([".java"], extract_java)
