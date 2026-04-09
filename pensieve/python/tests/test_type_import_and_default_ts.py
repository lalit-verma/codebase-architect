"""Tests for type-only import call suppression and TS default interface/enum.

Fix 1: import type { Foo } should create import edge but NOT call edge.
Fix 3: export default interface Foo / export default enum Foo should
       produce Export(kind="default").
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import json
import pytest

from pensieve.graph import build_graph
from pensieve.schema import (
    CallEdge,
    Export,
    FileExtraction,
    Import,
    Symbol,
)


def _sym(name="foo", **kw):
    defaults = dict(
        kind="function", line_start=1, line_end=5,
        signature=f"def {name}():", visibility="public",
    )
    defaults.update(kw)
    return Symbol(name=name, **defaults)


# ---------------------------------------------------------------------------
# Fix 1 + 2: type-only imports suppress call edges
# ---------------------------------------------------------------------------


class TestTypeImportNoCallEdge:

    def test_import_type_named_no_call_edge(self):
        """import type { Foo } from './types'; Foo() → import edge, no call edge."""
        exts = [
            FileExtraction(
                file_path="main.ts", language="typescript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[Import(module="./types.ts", names=["Foo"],
                                line=1, kind="import_type")],
                call_edges=[CallEdge(caller="run", callee="Foo", line=3)],
                symbols=[_sym("run")],
            ),
            FileExtraction(
                file_path="types.ts", language="typescript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[_sym("Foo")],
            ),
        ]
        graph = build_graph(exts)

        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1  # import edge exists

        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0  # no call edge for type import

    def test_import_type_aliased_no_call_edge(self):
        """import type { Foo as Bar } from './types'; Bar() → no call edge."""
        exts = [
            FileExtraction(
                file_path="main.ts", language="typescript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[Import(module="./types.ts", names=["Foo"],
                                alias="Bar", line=1, kind="import_type")],
                call_edges=[CallEdge(caller="run", callee="Bar", line=3)],
                symbols=[_sym("run")],
            ),
            FileExtraction(
                file_path="types.ts", language="typescript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[_sym("Foo")],
            ),
        ]
        graph = build_graph(exts)

        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1

        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0

    def test_regular_import_still_creates_call_edge(self):
        """Regression: import { Foo } (not type) should still create call edge."""
        exts = [
            FileExtraction(
                file_path="main.ts", language="typescript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[Import(module="./utils.ts", names=["helper"],
                                line=1, kind="import")],
                call_edges=[CallEdge(caller="run", callee="helper", line=3)],
                symbols=[_sym("run")],
            ),
            FileExtraction(
                file_path="utils.ts", language="typescript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[_sym("helper")],
            ),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 1

    def test_type_import_integration(self, tmp_path):
        """Full pipeline: import type { Foo } → no call edge in graph.json."""
        from pensieve.scan import scan_repo

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "types.ts").write_text("export interface Foo { id: string; }\n")
        (repo / "main.ts").write_text(dedent("""\
            import type { Foo } from './types';
            function run(): void { const x: Foo = { id: '1' }; }
        """))

        result = scan_repo(repo)
        graph = json.loads(result.graph_path.read_text())

        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) >= 1  # dependency edge exists

        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0  # no runtime call edge


# ---------------------------------------------------------------------------
# Fix 3 + 4: TS default interface/enum exports
# ---------------------------------------------------------------------------


class TestTSDefaultInterfaceEnum:

    def test_export_default_interface(self, tmp_path):
        """export default interface Foo {} → Export(kind='default')."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "types.ts"
        p.write_text("export default interface Foo { id: string; }\n")
        ext = extract_typescript(p)

        defaults = [e for e in ext.exports if e.kind == "default"]
        assert len(defaults) == 1
        assert defaults[0].name == "Foo"

        # Interface should also be in symbols
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert any(s.name == "Foo" for s in ifaces)

    def test_export_default_enum(self, tmp_path):
        """export default enum Status { A, B } → Export(kind='default')."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "types.ts"
        p.write_text("export default enum Status { A, B }\n")
        ext = extract_typescript(p)

        defaults = [e for e in ext.exports if e.kind == "default"]
        assert len(defaults) == 1
        assert defaults[0].name == "Status"

        # Enum should also be in symbols
        enums = [s for s in ext.symbols if s.kind == "enum"]
        assert any(s.name == "Status" for s in enums)

    def test_non_default_interface_still_named(self, tmp_path):
        """Regression: export interface Foo {} (not default) → kind='named'."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "types.ts"
        p.write_text("export interface Foo { id: string; }\n")
        ext = extract_typescript(p)

        named = [e for e in ext.exports if e.kind == "named"]
        assert any(e.name == "Foo" for e in named)
        assert not any(e.kind == "default" for e in ext.exports)

    def test_non_default_enum_still_named(self, tmp_path):
        """Regression: export enum Status {} (not default) → kind='named'."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "types.ts"
        p.write_text("export enum Status { A, B }\n")
        ext = extract_typescript(p)

        named = [e for e in ext.exports if e.kind == "named"]
        assert any(e.name == "Status" for e in named)
        assert not any(e.kind == "default" for e in ext.exports)
