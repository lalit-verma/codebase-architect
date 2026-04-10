"""Tests for cross-file edge aggregation (milestone B13).

Covers:
  - Import edges: module name → file path resolution
  - External imports: stdlib/third-party → not in edges, in external_imports
  - Cross-file call edges: imported function calls resolved to source file
  - Test→source mapping: test files detected and linked to source files
  - Circular imports: both edges present
  - Relative imports: resolved against importer's directory
  - graph.json written by scan_repo()
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.graph import (
    build_graph,
    _build_module_index,
    _is_test_file,
    _resolve_module,
)
from pensieve.schema import (
    CallEdge,
    FileExtraction,
    Import,
    Symbol,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ext(
    path: str,
    language: str = "python",
    symbols: list | None = None,
    imports: list | None = None,
    call_edges: list | None = None,
) -> FileExtraction:
    return FileExtraction(
        file_path=path,
        language=language,
        sha256="fake",
        file_size_bytes=100,
        line_count=10,
        symbols=symbols or [],
        imports=imports or [],
        call_edges=call_edges or [],
    )


def _sym(name: str, kind: str = "function", parent: str | None = None) -> Symbol:
    return Symbol(
        name=name, kind=kind, line_start=1, line_end=5,
        signature=f"def {name}():", visibility="public", parent=parent,
    )


def _imp(module: str, names: list[str] | None = None, line: int = 1) -> Import:
    return Import(module=module, names=names or [], line=line, kind="import")


def _call(caller: str, callee: str, line: int = 1) -> CallEdge:
    return CallEdge(caller=caller, callee=callee, line=line)


# ---------------------------------------------------------------------------
# Module index
# ---------------------------------------------------------------------------


class TestModuleIndex:

    def test_simple_file(self):
        idx = _build_module_index([_ext("utils.py")])
        assert "utils" in idx
        assert idx["utils"] == "utils.py"

    def test_nested_file(self):
        idx = _build_module_index([_ext("src/utils.py")])
        assert "utils" in idx
        assert "src.utils" in idx

    def test_init_file(self):
        idx = _build_module_index([_ext("models/__init__.py")])
        assert "models" in idx

    # --- Regression: Python package root detection ---

    def test_package_root_dotted_import(self):
        """Files under a directory containing __init__.py should be
        indexable with dotted paths relative to the package's parent.
        e.g., backend/open_webui/env.py with backend/open_webui/__init__.py
        should be findable as 'open_webui.env'."""
        idx = _build_module_index([
            _ext("backend/open_webui/__init__.py"),
            _ext("backend/open_webui/env.py"),
            _ext("backend/open_webui/utils/redis.py"),
            _ext("backend/open_webui/utils/__init__.py"),
        ])
        # Package-relative dotted paths
        assert idx.get("open_webui.env") == "backend/open_webui/env.py"
        assert idx.get("open_webui.utils.redis") == "backend/open_webui/utils/redis.py"
        # Repo-root dotted paths still work
        assert idx.get("backend.open_webui.env") == "backend/open_webui/env.py"

    def test_package_root_import_resolution(self):
        """Imports like 'open_webui.env' should resolve to
        backend/open_webui/env.py when __init__.py exists."""
        exts = [
            _ext("backend/open_webui/__init__.py"),
            _ext("backend/open_webui/env.py", symbols=[_sym("DEBUG")]),
            _ext("backend/open_webui/config.py",
                 imports=[_imp("open_webui.env", ["DEBUG"])]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["source"] == "backend/open_webui/config.py"
        assert import_edges[0]["target"] == "backend/open_webui/env.py"


# ---------------------------------------------------------------------------
# Import edges
# ---------------------------------------------------------------------------


class TestImportEdges:

    def test_simple_import_creates_edge(self):
        exts = [
            _ext("main.py", imports=[_imp("utils", ["helper"])]),
            _ext("utils.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["source"] == "main.py"
        assert import_edges[0]["target"] == "utils.py"

    def test_no_self_import_edge(self):
        """A file importing from itself should not create an edge."""
        exts = [_ext("utils.py", imports=[_imp("utils")])]
        graph = build_graph(exts)
        assert len(graph["edges"]) == 0

    def test_stdlib_import_is_external(self):
        exts = [_ext("main.py", imports=[_imp("os"), _imp("json")])]
        graph = build_graph(exts)
        assert len(graph["edges"]) == 0
        assert len(graph["external_imports"]) == 2
        modules = {e["module"] for e in graph["external_imports"]}
        assert "os" in modules
        assert "json" in modules

    def test_circular_imports_both_edges(self):
        exts = [
            _ext("a.py", imports=[_imp("b")]),
            _ext("b.py", imports=[_imp("a")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 2
        sources = {(e["source"], e["target"]) for e in import_edges}
        assert ("a.py", "b.py") in sources
        assert ("b.py", "a.py") in sources


# ---------------------------------------------------------------------------
# Cross-file call edges
# ---------------------------------------------------------------------------


class TestCrossFileCallEdges:

    def test_imported_function_call_creates_cross_file_edge(self):
        exts = [
            _ext("main.py",
                 imports=[_imp("utils", ["helper"])],
                 call_edges=[_call("main", "helper")],
                 symbols=[_sym("main")]),
            _ext("utils.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 1
        assert call_edges[0]["source"] == "main.py"
        assert call_edges[0]["target"] == "utils.py"
        assert "helper" in call_edges[0]["detail"]

    def test_local_call_not_cross_file(self):
        """A call to a function defined in the same file should NOT
        produce a cross-file edge."""
        exts = [
            _ext("main.py",
                 symbols=[_sym("foo"), _sym("bar")],
                 call_edges=[_call("foo", "bar")]),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0

    def test_unresolved_call_not_in_edges(self):
        """A call to a function that wasn't imported should not create
        a cross-file edge."""
        exts = [
            _ext("main.py",
                 call_edges=[_call("main", "unknown_func")],
                 symbols=[_sym("main")]),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0

    def test_imported_name_not_in_target_symbols(self):
        """If the imported name doesn't exist as a symbol in the target
        file, no cross-file call edge should be created."""
        exts = [
            _ext("main.py",
                 imports=[_imp("utils", ["ghost"])],
                 call_edges=[_call("main", "ghost")],
                 symbols=[_sym("main")]),
            _ext("utils.py", symbols=[_sym("helper")]),  # no "ghost"
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0


# ---------------------------------------------------------------------------
# Test→source mapping
# ---------------------------------------------------------------------------


class TestTestMapping:

    def test_test_file_detected(self):
        assert _is_test_file("test_main.py")
        assert _is_test_file("main_test.py")
        assert _is_test_file("tests/test_utils.py")
        assert _is_test_file("test/helpers.py")

    def test_non_test_file(self):
        assert not _is_test_file("main.py")
        assert not _is_test_file("utils.py")
        assert not _is_test_file("src/models.py")

    def test_test_file_creates_tests_edge(self):
        exts = [
            _ext("test_main.py", imports=[_imp("main")]),
            _ext("main.py", symbols=[_sym("run")]),
        ]
        graph = build_graph(exts)
        test_edges = [e for e in graph["edges"] if e["kind"] == "tests"]
        assert len(test_edges) == 1
        assert test_edges[0]["source"] == "test_main.py"
        assert test_edges[0]["target"] == "main.py"

    def test_test_file_importing_multiple_sources(self):
        exts = [
            _ext("test_all.py", imports=[_imp("main"), _imp("utils")]),
            _ext("main.py"),
            _ext("utils.py"),
        ]
        graph = build_graph(exts)
        test_edges = [e for e in graph["edges"] if e["kind"] == "tests"]
        assert len(test_edges) == 2
        targets = {e["target"] for e in test_edges}
        assert "main.py" in targets
        assert "utils.py" in targets

    def test_test_importing_test_not_linked(self):
        """A test file importing another test file should NOT create
        a tests edge (test→test is not a source relationship)."""
        exts = [
            _ext("test_main.py", imports=[_imp("test_helpers")]),
            _ext("test_helpers.py", symbols=[_sym("setup")]),
        ]
        graph = build_graph(exts)
        test_edges = [e for e in graph["edges"] if e["kind"] == "tests"]
        assert len(test_edges) == 0


# ---------------------------------------------------------------------------
# Relative imports
# ---------------------------------------------------------------------------


class TestRelativeImports:

    def test_dot_import(self):
        idx = _build_module_index([_ext("pkg/utils.py"), _ext("pkg/main.py")])
        resolved = _resolve_module(".utils", idx, "pkg/main.py")
        assert resolved == "pkg/utils.py"

    def test_unresolvable_relative_is_none(self):
        idx = _build_module_index([_ext("main.py")])
        assert _resolve_module(".nonexistent", idx, "main.py") is None

    def test_dotted_relative_import(self):
        """from .sub.mod import X → resolves to pkg/sub/mod.py"""
        idx = _build_module_index([
            _ext("pkg/main.py"),
            _ext("pkg/sub/mod.py"),
        ])
        resolved = _resolve_module(".sub.mod", idx, "pkg/main.py")
        assert resolved == "pkg/sub/mod.py"

    def test_js_path_relative_import(self):
        """import { X } from './utils' → resolves to src/utils.js"""
        idx = _build_module_index([
            _ext("src/main.js", language="javascript"),
            _ext("src/utils.js", language="javascript"),
        ])
        resolved = _resolve_module("./utils", idx, "src/main.js")
        assert resolved == "src/utils.js"

    def test_js_path_relative_with_extension(self):
        """import { X } from './utils.js' → resolves to src/utils.js"""
        idx = _build_module_index([
            _ext("src/main.js", language="javascript"),
            _ext("src/utils.js", language="javascript"),
        ])
        resolved = _resolve_module("./utils.js", idx, "src/main.js")
        assert resolved == "src/utils.js"

    def test_js_parent_relative_import(self):
        """import { X } from '../lib/helpers' → resolves to lib/helpers.ts"""
        idx = _build_module_index([
            _ext("src/main.ts", language="typescript"),
            _ext("lib/helpers.ts", language="typescript"),
        ])
        resolved = _resolve_module("../lib/helpers", idx, "src/main.ts")
        assert resolved == "lib/helpers.ts"

    def test_dotted_relative_creates_import_edge(self):
        """Full integration: from .sub.mod import helper → import edge."""
        exts = [
            _ext("pkg/main.py", imports=[_imp(".sub.mod", ["helper"])]),
            _ext("pkg/sub/mod.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["source"] == "pkg/main.py"
        assert import_edges[0]["target"] == "pkg/sub/mod.py"


# ---------------------------------------------------------------------------
# Review fix: no false-positive fallback
# ---------------------------------------------------------------------------


class TestNoFalsePositiveFallback:

    def test_dotted_import_no_last_segment_fallback(self):
        """pkg.bar should NOT resolve to other/bar.py — that's a
        false positive from last-segment matching."""
        exts = [
            _ext("main.py", imports=[_imp("pkg.bar")]),
            _ext("other/bar.py", symbols=[_sym("bar_func")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 0  # should be external, not matched
        assert len(graph["external_imports"]) == 1
        assert graph["external_imports"][0]["module"] == "pkg.bar"

    def test_unresolved_dotted_import_is_external(self):
        exts = [
            _ext("main.py", imports=[_imp("some.unknown.module")]),
        ]
        graph = build_graph(exts)
        assert len(graph["edges"]) == 0
        assert len(graph["external_imports"]) == 1

    def test_ambiguous_stem_produces_no_edge(self):
        """Two files with same stem (pkg1/utils.py, pkg2/utils.py):
        `import utils` must NOT resolve to either — it's ambiguous."""
        exts = [
            _ext("main.py", imports=[_imp("utils", ["helper"])]),
            _ext("pkg1/utils.py", symbols=[_sym("helper")]),
            _ext("pkg2/utils.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 0  # ambiguous → no edge
        assert len(graph["external_imports"]) == 1  # treated as external

    def test_dotted_path_disambiguates_stem(self):
        """pkg1.utils and pkg2.utils should resolve unambiguously even
        though the bare stem 'utils' is ambiguous."""
        exts = [
            _ext("main.py", imports=[_imp("pkg1.utils", ["helper"])]),
            _ext("pkg1/utils.py", symbols=[_sym("helper")]),
            _ext("pkg2/utils.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["target"] == "pkg1/utils.py"


# ---------------------------------------------------------------------------
# Review fix: relative import fallback false positive
# ---------------------------------------------------------------------------


class TestRelativeFallbackFalsePositive:

    def test_relative_import_no_global_fallback(self):
        """from .nonexistent import x in pkg/main.py must NOT resolve to
        other/nonexistent.py — that's a false positive via global stem match."""
        exts = [
            _ext("pkg/main.py", imports=[_imp(".nonexistent", ["x"])]),
            _ext("other/nonexistent.py", symbols=[_sym("x")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 0  # should be unresolved
        assert len(graph["external_imports"]) == 1


# ---------------------------------------------------------------------------
# Review fix: aliased imports for call resolution
# ---------------------------------------------------------------------------


class TestAliasedCallResolution:

    def test_aliased_import_creates_call_edge(self):
        """from utils import helper as h; h() → cross-file call edge."""
        exts = [
            _ext("main.py",
                 imports=[Import(module="utils", names=["helper"],
                                 alias="h", line=1, kind="from_import")],
                 call_edges=[_call("main", "h")],
                 symbols=[_sym("main")]),
            _ext("utils.py", symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        # "h" is the alias; it should resolve to utils.py
        # Note: the callee in the edge detail will be "h" (the local name),
        # and the target is utils.py. The alias tracking resolves h → utils.py.
        assert len(call_edges) >= 1
        assert any(e["target"] == "utils.py" for e in call_edges)

    def test_default_import_alias_creates_call_edge(self):
        """import foo from './utils.js'; foo() → cross-file call edge
        ONLY when utils.js has a default export."""
        from pensieve.schema import Export

        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=[],
                                 alias="foo", line=1, kind="import")],
                 call_edges=[_call("handler", "foo")],
                 symbols=[_sym("handler")]),
        ]
        # utils.js WITH a default export → call edge should exist
        utils_with_default = FileExtraction(
            file_path="utils.js", language="javascript",
            sha256="fake", file_size_bytes=100, line_count=10,
            symbols=[_sym("helper")],
            exports=[Export(name="helper", kind="default", line=1)],
        )
        graph = build_graph(exts + [utils_with_default])

        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["target"] == "utils.js"

        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 1
        assert call_edges[0]["source"] == "main.js"
        assert call_edges[0]["target"] == "utils.js"
        assert call_edges[0]["confidence"] < 1.0

    def test_namespace_import_no_false_positive_call_edge(self):
        """import * as utils from './utils.js'; utils() → NO call edge.
        Namespace imports should not be treated as default imports.
        The extractor now sets names=["*"] for namespace imports,
        distinguishing them from default imports (names=[])."""
        from pensieve.schema import Export

        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=["*"],
                                 alias="utils", line=1, kind="import")],
                 call_edges=[_call("main", "utils")],
                 symbols=[_sym("main")]),
        ]
        utils_with_default = FileExtraction(
            file_path="utils.js", language="javascript",
            sha256="fake", file_size_bytes=100, line_count=10,
            symbols=[_sym("helper")],
            exports=[Export(name="helper", kind="default", line=1)],
        )
        graph = build_graph(exts + [utils_with_default])

        # Import edge should exist (the import statement is real)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1

        # NO call edge — this is a namespace import, not a default import
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0

    def test_class_default_export_no_call_edge(self):
        """export default class Foo {}; import foo; foo() → NO call edge.
        A class is not a callable function in dependency-graph terms."""
        from pensieve.schema import Export

        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=[],
                                 alias="foo", line=1, kind="import")],
                 call_edges=[_call("handler", "foo")],
                 symbols=[_sym("handler")]),
        ]
        utils = FileExtraction(
            file_path="utils.js", language="javascript",
            sha256="fake", file_size_bytes=100, line_count=10,
            symbols=[Symbol(name="Foo", kind="class", line_start=1, line_end=5,
                           signature="class Foo {}", visibility="public")],
            exports=[Export(name="Foo", kind="default", line=1)],
        )
        graph = build_graph(exts + [utils])
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0  # class is not callable

    def test_constant_default_export_no_call_edge(self):
        """export default 42; import foo; foo() → NO call edge.
        A constant is not callable."""
        from pensieve.schema import Export

        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=[],
                                 alias="foo", line=1, kind="import")],
                 call_edges=[_call("handler", "foo")],
                 symbols=[_sym("handler")]),
        ]
        utils = FileExtraction(
            file_path="utils.js", language="javascript",
            sha256="fake", file_size_bytes=100, line_count=10,
            symbols=[Symbol(name="VALUE", kind="constant", line_start=1, line_end=1,
                           signature="const VALUE = 42", visibility="public")],
            exports=[Export(name="VALUE", kind="default", line=1)],
        )
        graph = build_graph(exts + [utils])
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0  # constant is not callable

    def test_function_default_export_still_creates_call_edge(self):
        """Regression: export default function helper(); import foo; foo()
        → call edge SHOULD still exist."""
        from pensieve.schema import Export

        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=[],
                                 alias="foo", line=1, kind="import")],
                 call_edges=[_call("handler", "foo")],
                 symbols=[_sym("handler")]),
        ]
        utils = FileExtraction(
            file_path="utils.js", language="javascript",
            sha256="fake", file_size_bytes=100, line_count=10,
            symbols=[_sym("helper")],  # kind="function" by default
            exports=[Export(name="helper", kind="default", line=1)],
        )
        graph = build_graph(exts + [utils])
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 1
        assert call_edges[0]["target"] == "utils.js"

    def test_default_import_no_call_edge_without_default_export(self):
        """import foo from './utils.js'; foo() → NO call edge when
        utils.js has only named exports (no default export)."""
        exts = [
            _ext("main.js",
                 language="javascript",
                 imports=[Import(module="./utils.js", names=[],
                                 alias="foo", line=1, kind="import")],
                 call_edges=[_call("handler", "foo")],
                 symbols=[_sym("handler")]),
            _ext("utils.js",
                 language="javascript",
                 symbols=[_sym("helper")]),  # no exports → no default export
        ]
        graph = build_graph(exts)

        # Import edge should still exist (the import statement is real)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1

        # But NO call edge — target has no default export
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0


# ---------------------------------------------------------------------------
# Review fix: extension priority ambiguity
# ---------------------------------------------------------------------------


class TestExtensionAmbiguity:

    def test_ts_importing_utils_prefers_ts_over_js(self):
        """main.ts importing ./utils should prefer utils.ts when both
        utils.js and utils.ts exist."""
        idx = _build_module_index([
            _ext("src/main.ts", language="typescript"),
            _ext("src/utils.js", language="javascript"),
            _ext("src/utils.ts", language="typescript"),
        ])
        resolved = _resolve_module("./utils", idx, "src/main.ts")
        assert resolved == "src/utils.ts"

    def test_js_importing_utils_prefers_js_over_ts(self):
        """main.js importing ./utils should prefer utils.js."""
        idx = _build_module_index([
            _ext("src/main.js", language="javascript"),
            _ext("src/utils.js", language="javascript"),
            _ext("src/utils.ts", language="typescript"),
        ])
        resolved = _resolve_module("./utils", idx, "src/main.js")
        assert resolved == "src/utils.js"

    def test_unresolvable_ambiguity_returns_none(self):
        """If main.py imports ./utils and both utils.js and utils.ts exist
        (but no utils.py), it's ambiguous → None."""
        idx = _build_module_index([
            _ext("src/main.py", language="python"),
            _ext("src/utils.js", language="javascript"),
            _ext("src/utils.ts", language="typescript"),
        ])
        resolved = _resolve_module("./utils", idx, "src/main.py")
        assert resolved is None

    def test_single_match_still_works(self):
        """When only one extension matches, resolve as before."""
        idx = _build_module_index([
            _ext("src/main.ts", language="typescript"),
            _ext("src/utils.ts", language="typescript"),
        ])
        resolved = _resolve_module("./utils", idx, "src/main.ts")
        assert resolved == "src/utils.ts"

    def test_extension_ambiguity_in_full_graph(self):
        """Full integration: main.ts + utils.ts + utils.js → import edge
        should point to utils.ts, not utils.js."""
        exts = [
            _ext("main.ts",
                 language="typescript",
                 imports=[Import(module="./utils", names=["helper"],
                                 line=1, kind="import")],
                 symbols=[_sym("main")]),
            _ext("utils.ts",
                 language="typescript",
                 symbols=[_sym("helper")]),
            _ext("utils.js",
                 language="javascript",
                 symbols=[_sym("helper")]),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1
        assert import_edges[0]["target"] == "utils.ts"  # not utils.js


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


class TestNodes:

    def test_nodes_contain_all_files(self):
        exts = [_ext("a.py"), _ext("b.py"), _ext("c.py")]
        graph = build_graph(exts)
        assert len(graph["nodes"]) == 3
        paths = {n["file_path"] for n in graph["nodes"]}
        assert paths == {"a.py", "b.py", "c.py"}

    def test_node_has_expected_fields(self):
        exts = [_ext("main.py", symbols=[_sym("foo"), _sym("bar")])]
        graph = build_graph(exts)
        node = graph["nodes"][0]
        assert node["file_path"] == "main.py"
        assert node["symbol_count"] == 2
        assert node["is_test"] is False

    def test_test_node_flagged(self):
        exts = [_ext("test_main.py")]
        graph = build_graph(exts)
        assert graph["nodes"][0]["is_test"] is True


# ---------------------------------------------------------------------------
# Integration: graph.json written by scan_repo
# ---------------------------------------------------------------------------


class TestGraphJsonIntegration:

    def _make_repo(self, tmp_path, files):
        repo = tmp_path / "repo"
        repo.mkdir()
        for path, content in files.items():
            f = repo / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        return repo

    def test_scan_produces_graph_json(self, tmp_path):
        from pensieve.scan import scan_repo

        repo = self._make_repo(tmp_path, {
            "main.py": "from utils import helper\ndef main():\n    helper()\n",
            "utils.py": "def helper():\n    return 42\n",
            "test_main.py": "from main import main\ndef test_main():\n    pass\n",
        })
        result = scan_repo(repo)

        assert result.graph_path.exists()
        data = json.loads(result.graph_path.read_text())

        assert "nodes" in data
        assert "edges" in data
        assert "external_imports" in data

        assert len(data["nodes"]) == 3

        # Should have import edges, cross-file call edges, and test edges
        edge_kinds = {e["kind"] for e in data["edges"]}
        assert "imports" in edge_kinds
        assert "tests" in edge_kinds

    def test_scan_graph_has_cross_file_call(self, tmp_path):
        from pensieve.scan import scan_repo

        repo = self._make_repo(tmp_path, {
            "main.py": "from utils import helper\ndef run():\n    helper()\n",
            "utils.py": "def helper():\n    return 1\n",
        })
        result = scan_repo(repo)
        data = json.loads(result.graph_path.read_text())

        call_edges = [e for e in data["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1
        assert call_edges[0]["source"] == "main.py"
        assert call_edges[0]["target"] == "utils.py"
