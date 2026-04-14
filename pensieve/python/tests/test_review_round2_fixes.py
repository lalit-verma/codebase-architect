"""Regression tests for code review round 2 findings.

Finding 1: Java overloaded methods call-edge disambiguation
Finding 2: Java wildcard imports
Finding 3: Go grouped declarations (multi-name const, grouped type blocks)
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.schema import validate_extraction


# ---------------------------------------------------------------------------
# Finding 1: Java overloaded methods
# ---------------------------------------------------------------------------


class TestJavaOverloads:

    def _write(self, tmp_path, content):
        p = tmp_path / "Test.java"
        p.write_text(dedent(content))
        return p

    def test_overloaded_methods_both_get_call_edges(self, tmp_path):
        """Two run() overloads — both should get their own call edges."""
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        public class Service {
            public void run(String name) {
                helperA();
            }
            public void run(String name, int count) {
                helperB();
            }
            private void helperA() {}
            private void helperB() {}
        }
        ''')
        ext = extract_java(p)
        validate_extraction(ext)

        # Both overloads should be extracted as separate symbols
        run_methods = [s for s in ext.symbols if s.name == "run"]
        assert len(run_methods) == 2

        # Each should have its own call edges
        callers = {e.caller for e in ext.call_edges}
        callees = {e.callee for e in ext.call_edges}
        assert "run" in callers
        assert "helperA" in callees
        assert "helperB" in callees

    def test_second_overload_call_edges_not_lost(self, tmp_path):
        """Regression: without line_start disambiguation, _find_method_node
        returns the FIRST overload for both symbols. The second overload's
        body is never walked, so its call edges are silently dropped.

        This test is designed to FAIL if line_start matching is removed:
        the first process() calls nothing, so if _find_method_node always
        returns the first one, processB() never appears in call edges.
        """
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        public class Worker {
            public void process() {
                // first overload — calls nothing
            }
            public void process(String data) {
                // second overload — the only one that calls processB
                processB(data);
            }
            private void processB(String d) {}
        }
        ''')
        ext = extract_java(p)

        # Both overloads extracted
        process_methods = [s for s in ext.symbols if s.name == "process"]
        assert len(process_methods) == 2

        # processB MUST appear as a callee. If _find_method_node
        # matched the first (empty) overload for both symbols,
        # processB would be missing entirely.
        callees = {e.callee for e in ext.call_edges}
        assert "processB" in callees, (
            "processB not found in call edges — _find_method_node likely "
            "returned the first overload (which calls nothing) for both "
            "symbols, dropping the second overload's call edges"
        )

    def test_overloaded_constructors(self, tmp_path):
        """Multiple constructors should each get call edges."""
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        public class Foo {
            public Foo() {
                init();
            }
            public Foo(String name) {
                setup(name);
            }
            private void init() {}
            private void setup(String s) {}
        }
        ''')
        ext = extract_java(p)
        constructors = [s for s in ext.symbols if s.name == "Foo" and s.kind == "method"]
        assert len(constructors) == 2
        callees = {e.callee for e in ext.call_edges}
        assert "init" in callees
        assert "setup" in callees


# ---------------------------------------------------------------------------
# Finding 2: Java wildcard imports
# ---------------------------------------------------------------------------


class TestJavaWildcardImports:

    def _write(self, tmp_path, content):
        p = tmp_path / "Test.java"
        p.write_text(dedent(content))
        return p

    def test_wildcard_import(self, tmp_path):
        """import java.util.* → module=java.util, names=[*]"""
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        import java.util.*;
        public class Foo {}
        ''')
        ext = extract_java(p)
        assert len(ext.imports) == 1
        imp = ext.imports[0]
        assert imp.module == "java.util"
        assert "*" in imp.names

    def test_static_wildcard_import(self, tmp_path):
        """import static java.util.Collections.* → module=java.util.Collections, names=[*]"""
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        import static java.util.Collections.*;
        public class Foo {}
        ''')
        ext = extract_java(p)
        imp = ext.imports[0]
        assert imp.module == "java.util.Collections"
        assert "*" in imp.names
        assert imp.kind == "static_import"

    def test_regular_import_still_works(self, tmp_path):
        """import java.util.List → module=java.util, names=[List]"""
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        import java.util.List;
        public class Foo {}
        ''')
        ext = extract_java(p)
        imp = ext.imports[0]
        assert imp.module == "java.util"
        assert "List" in imp.names

    def test_wildcard_import_passes_validation(self, tmp_path):
        from pensieve.extractors.java import extract_java
        p = self._write(tmp_path, '''\
        import java.util.*;
        import static java.util.Collections.*;
        public class Foo {}
        ''')
        ext = extract_java(p)
        validate_extraction(ext)


# ---------------------------------------------------------------------------
# Finding 3: Go grouped declarations
# ---------------------------------------------------------------------------


class TestGoGroupedDeclarations:

    def _write(self, tmp_path, content):
        p = tmp_path / "test.go"
        p.write_text(dedent(content))
        return p

    def test_multi_name_const(self, tmp_path):
        """const A, B = 1, 2 should yield both A and B."""
        from pensieve.extractors.go import extract_go
        p = self._write(tmp_path, '''\
        package main

        const A, B = 1, 2
        ''')
        ext = extract_go(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        names = {c.name for c in consts}
        assert "A" in names
        assert "B" in names
        assert len(consts) == 2

    def test_grouped_const_block(self, tmp_path):
        """const (...) with multiple specs should yield all constants."""
        from pensieve.extractors.go import extract_go
        p = self._write(tmp_path, '''\
        package main

        const (
        \tA = 1
        \tB = 2
        \tC = 3
        )
        ''')
        ext = extract_go(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 3
        assert {c.name for c in consts} == {"A", "B", "C"}

    def test_grouped_type_block(self, tmp_path):
        """type (...) with multiple type_specs should yield all types."""
        from pensieve.extractors.go import extract_go
        p = self._write(tmp_path, '''\
        package main

        type (
        \tUser struct {
        \t\tName string
        \t}
        \tRepo interface {
        \t\tFind() error
        \t}
        )
        ''')
        ext = extract_go(p)
        structs = [s for s in ext.symbols if s.kind == "struct"]
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(structs) == 1
        assert structs[0].name == "User"
        assert len(ifaces) == 1
        assert ifaces[0].name == "Repo"

    def test_grouped_type_with_three_types(self, tmp_path):
        """Grouped type block with 3 declarations."""
        from pensieve.extractors.go import extract_go
        p = self._write(tmp_path, '''\
        package main

        type (
        \tA struct{}
        \tB struct{}
        \tC interface{ Do() }
        )
        ''')
        ext = extract_go(p)
        type_syms = [s for s in ext.symbols if s.kind in ("struct", "interface")]
        assert len(type_syms) == 3
        assert {s.name for s in type_syms} == {"A", "B", "C"}

    def test_single_type_still_works(self, tmp_path):
        """Non-grouped type should still work (regression check)."""
        from pensieve.extractors.go import extract_go
        p = self._write(tmp_path, '''\
        package main

        type User struct {
        \tName string
        }
        ''')
        ext = extract_go(p)
        assert len([s for s in ext.symbols if s.kind == "struct"]) == 1
