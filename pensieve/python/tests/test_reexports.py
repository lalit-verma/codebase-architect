"""Integration tests for JS/TS re-exports and export aliases.

Tests the full pipeline: real extractors → scan → graph.
Verifies that barrel-file patterns produce correct dependency edges.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import json
import pytest

from pensieve.scan import scan_repo


def _make_repo(tmp_path, files):
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel, content in files.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(dedent(content))
    return repo


def _scan_and_graph(repo):
    result = scan_repo(repo)
    return json.loads(result.graph_path.read_text())


# ---------------------------------------------------------------------------
# JS re-exports
# ---------------------------------------------------------------------------


class TestJSReexports:

    def test_named_reexport_creates_import_edge(self, tmp_path):
        """export { foo } from './bar.js' → import edge to bar.js."""
        repo = _make_repo(tmp_path, {
            "bar.js": "export function foo() { return 1; }\n",
            "index.js": "export { foo } from './bar.js';\n",
        })
        graph = _scan_and_graph(repo)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert any(
            e["source"] == "index.js" and e["target"] == "bar.js"
            for e in import_edges
        )

    def test_star_reexport_creates_import_edge(self, tmp_path):
        """export * from './bar.js' → import edge to bar.js."""
        repo = _make_repo(tmp_path, {
            "bar.js": "export function foo() { return 1; }\n",
            "index.js": "export * from './bar.js';\n",
        })
        graph = _scan_and_graph(repo)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert any(
            e["source"] == "index.js" and e["target"] == "bar.js"
            for e in import_edges
        )

    def test_reexport_not_in_external_imports(self, tmp_path):
        """A re-export from a resolved module should NOT appear in external_imports."""
        repo = _make_repo(tmp_path, {
            "bar.js": "export function foo() { return 1; }\n",
            "index.js": "export { foo } from './bar.js';\n",
        })
        graph = _scan_and_graph(repo)
        external = [e for e in graph["external_imports"] if e["file"] == "index.js"]
        assert len(external) == 0


# ---------------------------------------------------------------------------
# JS export aliases
# ---------------------------------------------------------------------------


class TestJSExportAliases:

    def test_export_alias_uses_public_name(self, tmp_path):
        """export { foo as bar } → export name should be 'bar', not 'foo'."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "test.js"
        p.write_text("function foo() {}\nexport { foo as bar };\n")
        ext = extract_javascript(p)

        named_exports = [e for e in ext.exports if e.kind == "named"]
        assert len(named_exports) == 1
        assert named_exports[0].name == "bar"  # public name, not original

    def test_reexport_alias_uses_public_name(self, tmp_path):
        """export { foo as publicFoo } from './bar' → name is 'publicFoo'."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "index.js"
        p.write_text("export { foo as publicFoo } from './bar.js';\n")
        ext = extract_javascript(p)

        exports = [e for e in ext.exports if e.kind == "re_export"]
        assert len(exports) == 1
        assert exports[0].name == "publicFoo"


# ---------------------------------------------------------------------------
# TS re-exports and type exports
# ---------------------------------------------------------------------------


class TestTSReexports:

    def test_ts_named_reexport(self, tmp_path):
        """TS: export { foo } from './bar' → import edge."""
        repo = _make_repo(tmp_path, {
            "bar.ts": "export function foo(): number { return 1; }\n",
            "index.ts": "export { foo } from './bar';\n",
        })
        graph = _scan_and_graph(repo)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert any(
            e["source"] == "index.ts" and e["target"] == "bar.ts"
            for e in import_edges
        )

    def test_ts_type_reexport_kind(self, tmp_path):
        """TS: export type { Foo } from './types' → export kind is 'type'."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "index.ts"
        p.write_text("export type { Foo } from './types';\n")
        ext = extract_typescript(p)

        type_exports = [e for e in ext.exports if e.kind == "type"]
        assert len(type_exports) == 1
        assert type_exports[0].name == "Foo"

    def test_ts_type_reexport_alias(self, tmp_path):
        """TS: export type { Foo as Bar } from './types' → name is Bar, kind is type."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "index.ts"
        p.write_text("export type { Foo as Bar } from './types';\n")
        ext = extract_typescript(p)

        type_exports = [e for e in ext.exports if e.kind == "type"]
        assert len(type_exports) == 1
        assert type_exports[0].name == "Bar"  # public alias

    def test_ts_type_reexport_creates_import_edge(self, tmp_path):
        """TS: export type { Foo } from './types' → import edge to types.ts."""
        repo = _make_repo(tmp_path, {
            "types.ts": "export interface Foo { id: string; }\n",
            "index.ts": "export type { Foo } from './types';\n",
        })
        graph = _scan_and_graph(repo)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert any(
            e["source"] == "index.ts" and e["target"] == "types.ts"
            for e in import_edges
        )


# ---------------------------------------------------------------------------
# Barrel file (realistic integration)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TS type re-export import kind
# ---------------------------------------------------------------------------


class TestTSTypeReexportImportKind:

    def test_ts_type_reexport_import_kind(self, tmp_path):
        """TS export type { Foo } from './types' → Import(kind='import_type')."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "index.ts"
        p.write_text("export type { Foo } from './types';\n")
        ext = extract_typescript(p)

        type_imports = [i for i in ext.imports if i.kind == "import_type"]
        assert len(type_imports) == 1
        assert type_imports[0].module == "./types"

    def test_ts_regular_reexport_import_kind(self, tmp_path):
        """TS export { foo } from './bar' → Import(kind='import'), not 'import_type'."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "index.ts"
        p.write_text("export { foo } from './bar';\n")
        ext = extract_typescript(p)

        regular_imports = [i for i in ext.imports if i.kind == "import"]
        assert len(regular_imports) == 1


# ---------------------------------------------------------------------------
# export * as ns
# ---------------------------------------------------------------------------


class TestNamespaceReexport:

    def test_js_namespace_reexport_export(self, tmp_path):
        """export * as utils from './bar.js' → Export(name='utils', kind='re_export')."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "index.js"
        p.write_text("export * as utils from './bar.js';\n")
        ext = extract_javascript(p)

        reexports = [e for e in ext.exports if e.kind == "re_export"]
        assert len(reexports) == 1
        assert reexports[0].name == "utils"

    def test_js_namespace_reexport_import(self, tmp_path):
        """export * as utils from './bar.js' → Import for dependency edge."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "index.js"
        p.write_text("export * as utils from './bar.js';\n")
        ext = extract_javascript(p)

        assert len(ext.imports) == 1
        assert ext.imports[0].module == "./bar.js"

    def test_ts_namespace_reexport(self, tmp_path):
        """TS export * as utils from './bar' → Export + Import."""
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "index.ts"
        p.write_text("export * as utils from './bar';\n")
        ext = extract_typescript(p)

        reexports = [e for e in ext.exports if e.kind == "re_export"]
        assert len(reexports) == 1
        assert reexports[0].name == "utils"
        assert len(ext.imports) >= 1

    def test_namespace_reexport_graph_edge(self, tmp_path):
        """Full pipeline: export * as utils from './bar' → import edge in graph."""
        repo = _make_repo(tmp_path, {
            "bar.js": "export function foo() {}\n",
            "index.js": "export * as utils from './bar.js';\n",
        })
        graph = _scan_and_graph(repo)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert any(
            e["source"] == "index.js" and e["target"] == "bar.js"
            for e in import_edges
        )


# ---------------------------------------------------------------------------
# Barrel file (realistic integration)
# ---------------------------------------------------------------------------


class TestBarrelFile:

    def test_barrel_file_graph(self, tmp_path):
        """A realistic barrel file re-exporting from multiple modules
        should produce import edges to all source modules."""
        repo = _make_repo(tmp_path, {
            "models/user.js": "export class User {}\n",
            "models/order.js": "export class Order {}\n",
            "models/index.js": dedent("""\
                export { User } from './user.js';
                export { Order } from './order.js';
            """),
            "main.js": dedent("""\
                import { User, Order } from './models/index.js';
                function run() { new User(); }
            """),
        })
        graph = _scan_and_graph(repo)

        # index.js should have import edges to both user.js and order.js
        index_imports = [
            e for e in graph["edges"]
            if e["source"] == "models/index.js" and e["kind"] == "imports"
        ]
        targets = {e["target"] for e in index_imports}
        assert "models/user.js" in targets
        assert "models/order.js" in targets

        # main.js should have an import edge to index.js
        main_imports = [
            e for e in graph["edges"]
            if e["source"] == "main.js" and e["kind"] == "imports"
        ]
        assert any(e["target"] == "models/index.js" for e in main_imports)
