"""Smoke tests for all 6 tree-sitter language parsers (milestone B2).

Each language gets a test class that confirms:
  1. The grammar package is importable
  2. A parser can be created
  3. A minimal source file parses into an AST with the expected root type
  4. A basic construct (function, class, or import) can be extracted

Python parser tests are in test_tree_sitter.py (B1). This file covers
the 5 additional languages: JavaScript, TypeScript, Go, Java, Rust.
"""

from __future__ import annotations

import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parser_for(language_fn) -> Parser:
    """Create a tree-sitter parser from a language function."""
    return Parser(Language(language_fn))


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

class TestJavaScript:

    def _parser(self) -> Parser:
        return _parser_for(tsjs.language())

    def test_import(self):
        assert hasattr(tsjs, "language")

    def test_parse_function(self):
        parser = self._parser()
        source = b"function greet(name) {\n  return `hello ${name}`;\n}\n"
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "program"

        func = root.children[0]
        assert func.type == "function_declaration"
        name = func.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"greet"

    def test_parse_class(self):
        parser = self._parser()
        source = b"""\
class Calculator {
  add(a, b) {
    return a + b;
  }
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        class_node = root.children[0]
        assert class_node.type == "class_declaration"
        name = class_node.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"Calculator"

    def test_parse_imports(self):
        parser = self._parser()
        source = b"import { useState } from 'react';\nimport path from 'path';\n"
        tree = parser.parse(source)
        root = tree.root_node

        imports = [c for c in root.children if c.type == "import_statement"]
        assert len(imports) == 2

    def test_parse_arrow_function(self):
        parser = self._parser()
        source = b"const add = (a, b) => a + b;\n"
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "program"
        assert not root.has_error


# ---------------------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------------------

class TestTypeScript:
    """TypeScript uses `language_typescript()` not `language()`.
    The package also exposes `language_tsx()` for .tsx files."""

    def _parser(self) -> Parser:
        return _parser_for(tsts.language_typescript())

    def _tsx_parser(self) -> Parser:
        return _parser_for(tsts.language_tsx())

    def test_import(self):
        assert hasattr(tsts, "language_typescript")
        assert hasattr(tsts, "language_tsx")

    def test_parse_function_with_types(self):
        parser = self._parser()
        source = b"function greet(name: string): string {\n  return `hello ${name}`;\n}\n"
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "program"

        func = root.children[0]
        assert func.type == "function_declaration"
        name = func.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"greet"

    def test_parse_interface(self):
        parser = self._parser()
        source = b"""\
interface User {
  id: number;
  name: string;
  email?: string;
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        iface = root.children[0]
        assert iface.type == "interface_declaration"
        name = iface.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"User"

    def test_parse_type_export(self):
        parser = self._parser()
        source = b"export type Result<T> = { ok: true; value: T } | { ok: false; error: Error };\n"
        tree = parser.parse(source)
        assert not tree.root_node.has_error

    def test_tsx_parser_handles_jsx(self):
        parser = self._tsx_parser()
        source = b"const App = () => <div>hello</div>;\n"
        tree = parser.parse(source)
        assert tree.root_node.type == "program"
        assert not tree.root_node.has_error


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------

class TestGo:

    def _parser(self) -> Parser:
        return _parser_for(tsgo.language())

    def test_import(self):
        assert hasattr(tsgo, "language")

    def test_parse_function(self):
        parser = self._parser()
        source = b"""\
package main

func add(a int, b int) int {
\treturn a + b
}
"""
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "source_file"

        funcs = [c for c in root.children if c.type == "function_declaration"]
        assert len(funcs) == 1
        name = funcs[0].child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"add"

    def test_parse_method_with_receiver(self):
        parser = self._parser()
        source = b"""\
package main

type Calculator struct{}

func (c *Calculator) Add(a, b int) int {
\treturn a + b
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        methods = [c for c in root.children if c.type == "method_declaration"]
        assert len(methods) == 1
        name = methods[0].child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"Add"

    def test_parse_imports(self):
        parser = self._parser()
        source = b"""\
package main

import (
\t"fmt"
\t"os"
)
"""
        tree = parser.parse(source)
        root = tree.root_node

        imports = [c for c in root.children if c.type == "import_declaration"]
        assert len(imports) == 1  # one import block

    def test_parse_struct(self):
        parser = self._parser()
        source = b"""\
package main

type User struct {
\tID   int
\tName string
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        type_decls = [c for c in root.children if c.type == "type_declaration"]
        assert len(type_decls) == 1


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

class TestJava:

    def _parser(self) -> Parser:
        return _parser_for(tsjava.language())

    def test_import(self):
        assert hasattr(tsjava, "language")

    def test_parse_class_with_method(self):
        parser = self._parser()
        source = b"""\
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "program"

        class_node = root.children[0]
        assert class_node.type == "class_declaration"
        name = class_node.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"Calculator"

    def test_parse_interface(self):
        parser = self._parser()
        source = b"""\
public interface Repository<T> {
    T findById(long id);
    void save(T entity);
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        iface = root.children[0]
        assert iface.type == "interface_declaration"
        name = iface.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"Repository"

    def test_parse_imports(self):
        parser = self._parser()
        source = b"""\
import java.util.List;
import java.util.Optional;

public class Foo {}
"""
        tree = parser.parse(source)
        root = tree.root_node

        imports = [c for c in root.children if c.type == "import_declaration"]
        assert len(imports) == 2

    def test_parse_annotation(self):
        parser = self._parser()
        source = b"""\
@Override
public String toString() {
    return "hello";
}
"""
        tree = parser.parse(source)
        assert not tree.root_node.has_error


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------

class TestRust:

    def _parser(self) -> Parser:
        return _parser_for(tsrust.language())

    def test_import(self):
        assert hasattr(tsrust, "language")

    def test_parse_function(self):
        parser = self._parser()
        source = b"fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n"
        tree = parser.parse(source)
        root = tree.root_node
        assert root.type == "source_file"

        func = root.children[0]
        assert func.type == "function_item"
        name = func.child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"add"

    def test_parse_struct(self):
        parser = self._parser()
        source = b"""\
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: Option<String>,
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        structs = [c for c in root.children if c.type == "struct_item"]
        assert len(structs) == 1
        name = structs[0].child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"User"

    def test_parse_impl_block(self):
        parser = self._parser()
        source = b"""\
impl Calculator {
    pub fn add(&self, a: i32, b: i32) -> i32 {
        a + b
    }

    pub fn subtract(&self, a: i32, b: i32) -> i32 {
        a - b
    }
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        impls = [c for c in root.children if c.type == "impl_item"]
        assert len(impls) == 1

    def test_parse_trait(self):
        parser = self._parser()
        source = b"""\
pub trait Repository<T> {
    fn find_by_id(&self, id: u64) -> Option<T>;
    fn save(&mut self, entity: T);
}
"""
        tree = parser.parse(source)
        root = tree.root_node

        traits = [c for c in root.children if c.type == "trait_item"]
        assert len(traits) == 1
        name = traits[0].child_by_field_name("name")
        assert source[name.start_byte:name.end_byte] == b"Repository"

    def test_parse_use_statement(self):
        parser = self._parser()
        source = b"use std::collections::HashMap;\nuse std::io::{self, Read};\n"
        tree = parser.parse(source)
        root = tree.root_node

        uses = [c for c in root.children if c.type == "use_declaration"]
        assert len(uses) == 2
