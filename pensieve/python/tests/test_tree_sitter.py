"""Smoke tests for tree-sitter integration (milestone B1).

Verifies tree-sitter is installed, the Python grammar loads, and we
can parse source code into an AST and walk it. This is the foundation
for the per-language extractors in B4–B9.
"""

from __future__ import annotations

import tree_sitter_python as tspython
from tree_sitter import Language, Parser


def _make_python_parser() -> Parser:
    """Create a tree-sitter parser for Python."""
    language = Language(tspython.language())
    return Parser(language)


class TestTreeSitterImport:
    """Verify the packages are importable and the API surface exists."""

    def test_tree_sitter_importable(self):
        from tree_sitter import Language, Parser  # noqa: F811
        assert Language is not None
        assert Parser is not None

    def test_tree_sitter_python_importable(self):
        import tree_sitter_python as ts  # noqa: F811
        assert hasattr(ts, "language")


class TestPythonParsing:
    """Verify we can parse Python source into an AST."""

    def test_parse_simple_function(self):
        parser = _make_python_parser()
        source = b"def hello():\n    return 42\n"
        tree = parser.parse(source)
        root = tree.root_node

        assert root.type == "module"
        assert root.child_count > 0

    def test_extract_function_name(self):
        parser = _make_python_parser()
        source = b"def greet(name: str) -> str:\n    return f'hello {name}'\n"
        tree = parser.parse(source)
        root = tree.root_node

        # Find the function_definition node
        func_node = root.children[0]
        assert func_node.type == "function_definition"

        # The function name is the first `identifier` child
        name_node = func_node.child_by_field_name("name")
        assert name_node is not None
        assert name_node.type == "identifier"
        assert source[name_node.start_byte:name_node.end_byte] == b"greet"

    def test_extract_class_and_methods(self):
        parser = _make_python_parser()
        source = b"""\
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
"""
        tree = parser.parse(source)
        root = tree.root_node

        # Find class
        class_node = root.children[0]
        assert class_node.type == "class_definition"

        class_name = class_node.child_by_field_name("name")
        assert source[class_name.start_byte:class_name.end_byte] == b"Calculator"

        # Find methods inside the class body
        body = class_node.child_by_field_name("body")
        methods = [
            child for child in body.children
            if child.type == "function_definition"
        ]
        assert len(methods) == 2

        method_names = []
        for m in methods:
            name_node = m.child_by_field_name("name")
            method_names.append(
                source[name_node.start_byte:name_node.end_byte].decode()
            )
        assert method_names == ["add", "subtract"]

    def test_extract_imports(self):
        parser = _make_python_parser()
        source = b"""\
import os
from pathlib import Path
from typing import Optional, List
"""
        tree = parser.parse(source)
        root = tree.root_node

        import_nodes = [
            child for child in root.children
            if child.type in ("import_statement", "import_from_statement")
        ]
        assert len(import_nodes) == 3

    def test_parse_empty_source(self):
        parser = _make_python_parser()
        tree = parser.parse(b"")
        root = tree.root_node

        assert root.type == "module"
        assert root.child_count == 0

    def test_parse_syntax_error_still_produces_tree(self):
        """tree-sitter is error-tolerant — it always produces a tree,
        even for invalid syntax. This is important for extracting
        partial information from broken files."""
        parser = _make_python_parser()
        source = b"def broken(:\n    return\n"
        tree = parser.parse(source)
        root = tree.root_node

        assert root.type == "module"
        # The tree should contain an ERROR node somewhere
        assert root.has_error

    def test_node_line_numbers(self):
        """Verify we can extract line/column positions from nodes,
        which we need for file:line references in the output."""
        parser = _make_python_parser()
        source = b"x = 1\n\ndef foo():\n    pass\n"
        tree = parser.parse(source)
        root = tree.root_node

        func_node = [
            c for c in root.children if c.type == "function_definition"
        ][0]
        # Function starts on line 3 (0-indexed: line 2)
        assert func_node.start_point[0] == 2
        # Column 0
        assert func_node.start_point[1] == 0
