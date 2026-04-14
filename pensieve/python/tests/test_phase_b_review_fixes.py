"""Regression tests for Phase B comprehensive review findings.

Finding 1: Validator completeness (exports, line numbers, kinds)
Finding 2: JS/TS named-import aliases
Finding 3: file_path contract (documented, not code-fixed)
Finding 4: Rust use X as Y
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.schema import (
    Export,
    FileExtraction,
    Import,
    SchemaError,
    validate_extraction,
)


# ---------------------------------------------------------------------------
# Finding 1: Validator completeness
# ---------------------------------------------------------------------------


class TestValidatorCompleteness:

    def _make(self, **overrides):
        defaults = dict(
            file_path="test.py", language="python", sha256="abc",
            file_size_bytes=10, line_count=1,
        )
        defaults.update(overrides)
        return FileExtraction(**defaults)

    def test_empty_export_name_rejected(self):
        ext = self._make(exports=[Export(name="", kind="named", line=1)])
        with pytest.raises(SchemaError, match="exports.*name is empty"):
            validate_extraction(ext)

    def test_empty_export_kind_rejected(self):
        ext = self._make(exports=[Export(name="foo", kind="", line=1)])
        with pytest.raises(SchemaError, match="exports.*kind is empty"):
            validate_extraction(ext)

    def test_negative_export_line_rejected(self):
        ext = self._make(exports=[Export(name="foo", kind="named", line=-1)])
        with pytest.raises(SchemaError, match="exports.*line is negative"):
            validate_extraction(ext)

    def test_negative_import_line_rejected(self):
        ext = self._make(imports=[Import(module="os", line=-5, kind="import")])
        with pytest.raises(SchemaError, match="imports.*line is negative"):
            validate_extraction(ext)

    def test_empty_import_kind_rejected(self):
        ext = self._make(imports=[Import(module="os", line=1, kind="")])
        with pytest.raises(SchemaError, match="imports.*kind is empty"):
            validate_extraction(ext)

    def test_negative_call_edge_line_rejected(self):
        from pensieve.schema import CallEdge
        ext = self._make(call_edges=[CallEdge(caller="a", callee="b", line=-1)])
        with pytest.raises(SchemaError, match="call_edges.*line is negative"):
            validate_extraction(ext)

    def test_negative_comment_line_rejected(self):
        from pensieve.schema import RationaleComment
        ext = self._make(rationale_comments=[
            RationaleComment(tag="WHY", text="reason", line=-1)
        ])
        with pytest.raises(SchemaError, match="rationale_comments.*line is negative"):
            validate_extraction(ext)

    def test_valid_export_passes(self):
        ext = self._make(exports=[Export(name="Foo", kind="default", line=1)])
        validate_extraction(ext)  # should not raise

    def test_bogus_import_kind_rejected(self):
        ext = self._make(imports=[Import(module="os", line=1, kind="bogus")])
        with pytest.raises(SchemaError, match="imports.*kind.*not in"):
            validate_extraction(ext)

    def test_bogus_export_kind_rejected(self):
        ext = self._make(exports=[Export(name="Foo", kind="bogus", line=1)])
        with pytest.raises(SchemaError, match="exports.*kind.*not in"):
            validate_extraction(ext)

    def test_all_valid_import_kinds_accepted(self):
        from pensieve.schema import VALID_IMPORT_KINDS
        for kind in VALID_IMPORT_KINDS:
            ext = self._make(imports=[Import(module="os", line=1, kind=kind)])
            validate_extraction(ext)

    def test_all_valid_export_kinds_accepted(self):
        from pensieve.schema import VALID_EXPORT_KINDS
        for kind in VALID_EXPORT_KINDS:
            ext = self._make(exports=[Export(name="X", kind=kind, line=1)])
            validate_extraction(ext)


# ---------------------------------------------------------------------------
# Finding 2: JS/TS named-import aliases
# ---------------------------------------------------------------------------


class TestJSTSNamedImportAliases:

    def test_js_aliased_named_import_preserved(self, tmp_path):
        """import { helper as h } should produce Import with alias='h'."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "test.js"
        p.write_text("import { helper as h, foo as bar } from 'utils';\n")
        ext = extract_javascript(p)

        # Should have 2 aliased imports (one per alias) + possibly 0 plain
        aliased = [i for i in ext.imports if i.alias]
        assert len(aliased) == 2
        aliases = {i.alias for i in aliased}
        assert "h" in aliases
        assert "bar" in aliases
        # Original names preserved
        h_import = next(i for i in aliased if i.alias == "h")
        assert "helper" in h_import.names

    def test_ts_aliased_named_import_preserved(self, tmp_path):
        from pensieve.extractors.typescript import extract_typescript
        p = tmp_path / "test.ts"
        p.write_text("import { helper as h } from './utils';\n")
        ext = extract_typescript(p)

        aliased = [i for i in ext.imports if i.alias]
        assert len(aliased) == 1
        assert aliased[0].alias == "h"
        assert "helper" in aliased[0].names

    def test_js_alias_creates_cross_file_call_edge(self, tmp_path):
        """import { helper as h }; h() → cross-file call edge."""
        from pensieve.graph import build_graph
        from pensieve.schema import CallEdge, Symbol

        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[Import(module="utils", names=["helper"],
                                alias="h", line=1, kind="import")],
                call_edges=[CallEdge(caller="main", callee="h", line=3)],
                symbols=[Symbol(name="main", kind="function", line_start=2,
                               line_end=5, signature="function main()",
                               visibility="public")],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[Symbol(name="helper", kind="function", line_start=1,
                               line_end=3, signature="function helper()",
                               visibility="public")],
            ),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1
        assert any(e["target"] == "utils.js" for e in call_edges)

    def test_js_mixed_plain_and_aliased_imports(self, tmp_path):
        """import { x, helper as h } → x as plain name, h as alias."""
        from pensieve.extractors.javascript import extract_javascript
        p = tmp_path / "test.js"
        p.write_text("import { x, helper as h } from 'utils';\n")
        ext = extract_javascript(p)

        plain = [i for i in ext.imports if not i.alias]
        aliased = [i for i in ext.imports if i.alias]
        assert len(plain) == 1
        assert "x" in plain[0].names
        assert len(aliased) == 1
        assert aliased[0].alias == "h"


# ---------------------------------------------------------------------------
# Finding 4: Rust use X as Y
# ---------------------------------------------------------------------------


class TestRustUseAs:

    def test_use_as_creates_import(self, tmp_path):
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::collections::HashMap as Map;\n")
        ext = extract_rust(p)

        assert len(ext.imports) == 1
        imp = ext.imports[0]
        assert imp.module == "std::collections"
        assert "HashMap" in imp.names
        assert imp.alias == "Map"

    def test_multiple_use_as(self, tmp_path):
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text(dedent('''\
        use std::collections::HashMap as Map;
        use std::io::Read as IoRead;
        '''))
        ext = extract_rust(p)
        assert len(ext.imports) == 2
        aliases = {i.alias for i in ext.imports}
        assert "Map" in aliases
        assert "IoRead" in aliases

    def test_use_as_passes_validation(self, tmp_path):
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::collections::HashMap as Map;\nfn main() {}\n")
        ext = extract_rust(p)
        validate_extraction(ext)

    def test_simple_use_still_works(self, tmp_path):
        """Regression: simple use without alias should still work."""
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::collections::HashMap;\n")
        ext = extract_rust(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].alias is None

    def test_grouped_use_as(self, tmp_path):
        """use std::io::{Read as IoRead, Write} → both extracted."""
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::io::{Read as IoRead, Write};\n")
        ext = extract_rust(p)

        assert len(ext.imports) == 2  # one plain (Write), one aliased (Read as IoRead)
        aliased = [i for i in ext.imports if i.alias]
        plain = [i for i in ext.imports if not i.alias]

        assert len(aliased) == 1
        assert aliased[0].alias == "IoRead"
        assert "Read" in aliased[0].names
        assert aliased[0].module == "std::io"

        assert len(plain) == 1
        assert "Write" in plain[0].names

    def test_grouped_use_as_with_self(self, tmp_path):
        """use std::io::{self, Read as IoRead, Write} → all three."""
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::io::{self, Read as IoRead, Write};\n")
        ext = extract_rust(p)

        # self + Write in one Import, Read as IoRead in another
        aliased = [i for i in ext.imports if i.alias]
        plain = [i for i in ext.imports if not i.alias]

        assert len(aliased) == 1
        assert aliased[0].alias == "IoRead"

        assert len(plain) == 1
        names = plain[0].names
        assert "self" in names
        assert "Write" in names

    def test_grouped_use_as_passes_validation(self, tmp_path):
        from pensieve.extractors.rust import extract_rust
        p = tmp_path / "test.rs"
        p.write_text("use std::io::{Read as IoRead, Write};\nfn main() {}\n")
        ext = extract_rust(p)
        validate_extraction(ext)
