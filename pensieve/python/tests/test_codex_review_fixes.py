"""Regression tests for Codex review findings.

These tests verify the fixes for bugs found by Codex's review of B1-B5.
Each test is named after the finding it validates.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


# ---------------------------------------------------------------------------
# Finding 1: Lazy extractor loading (one broken module doesn't break others)
# ---------------------------------------------------------------------------


class TestLazyLoading:

    def test_extract_file_works_for_python(self):
        """extract_file dispatches to the Python extractor correctly."""
        from pensieve.extractors import extract_file
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def hello(): pass\n")
            f.flush()
            ext = extract_file(Path(f.name))
        os.unlink(f.name)

        assert ext is not None
        assert ext.language == "python"
        assert any(s.name == "hello" for s in ext.symbols)

    def test_extract_file_returns_none_for_unknown_extension(self):
        from pensieve.extractors import extract_file
        assert extract_file(Path("test.xyz")) is None

    def test_supported_extensions_includes_all_languages(self):
        from pensieve.extractors import supported_extensions
        exts = supported_extensions()
        assert ".py" in exts
        assert ".js" in exts
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".go" in exts
        assert ".java" in exts
        assert ".rs" in exts

    def test_python_extractor_importable_independently(self):
        """Each extractor should be importable without pulling in all others."""
        from pensieve.extractors.python import extract_python
        assert callable(extract_python)

    def test_javascript_extractor_importable_independently(self):
        from pensieve.extractors.javascript import extract_javascript
        assert callable(extract_javascript)


# ---------------------------------------------------------------------------
# Finding 3: Python relative imports
# ---------------------------------------------------------------------------


class TestPythonRelativeImports:

    def _write_py(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "test.py"
        p.write_text(dedent(content))
        return p

    def test_from_dot_import(self, tmp_path):
        """from . import foo → module should be '.', not empty."""
        from pensieve.extractors.python import extract_python
        p = self._write_py(tmp_path, "from . import foo\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "."
        assert "foo" in ext.imports[0].names

    def test_from_dotdot_import(self, tmp_path):
        """from ..bar import baz → module should be '..bar'."""
        from pensieve.extractors.python import extract_python
        p = self._write_py(tmp_path, "from ..bar import baz\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "..bar"
        assert "baz" in ext.imports[0].names

    def test_from_dot_utils_import(self, tmp_path):
        """from .utils import helper → module should be '.utils'."""
        from pensieve.extractors.python import extract_python
        p = self._write_py(tmp_path, "from .utils import helper\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == ".utils"

    def test_relative_import_passes_validation(self, tmp_path):
        """Relative imports should not produce empty module (which fails validation)."""
        from pensieve.extractors.python import extract_python
        from pensieve.schema import validate_extraction
        p = self._write_py(tmp_path, "from . import foo\nfrom ..bar import baz\n")
        ext = extract_python(p)
        validate_extraction(ext)  # should not raise


# ---------------------------------------------------------------------------
# Finding 4: JS inline default-export declarations
# ---------------------------------------------------------------------------


class TestJSInlineDefaultExport:

    def _write_js(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "test.js"
        p.write_text(dedent(content))
        return p

    def test_export_default_function(self, tmp_path):
        """export default function helper() {} should create a default export."""
        from pensieve.extractors.javascript import extract_javascript
        p = self._write_js(tmp_path, '''\
        export default function helper() {
          return 42;
        }
        ''')
        ext = extract_javascript(p)
        # Should have both the symbol AND the export
        assert any(s.name == "helper" and s.kind == "function" for s in ext.symbols)
        assert any(e.name == "helper" and e.kind == "default" for e in ext.exports)
        # The symbol should get public visibility from the export
        helper = next(s for s in ext.symbols if s.name == "helper")
        assert helper.visibility == "public"

    def test_export_default_class(self, tmp_path):
        """export default class Foo {} should create a default export."""
        from pensieve.extractors.javascript import extract_javascript
        p = self._write_js(tmp_path, '''\
        export default class Foo {
          bar() { return 1; }
        }
        ''')
        ext = extract_javascript(p)
        assert any(s.name == "Foo" and s.kind == "class" for s in ext.symbols)
        assert any(e.name == "Foo" and e.kind == "default" for e in ext.exports)
        foo = next(s for s in ext.symbols if s.name == "Foo")
        assert foo.visibility == "public"

    def test_export_default_identifier_still_works(self, tmp_path):
        """export default X (identifier) should still work after the fix."""
        from pensieve.extractors.javascript import extract_javascript
        p = self._write_js(tmp_path, '''\
        class Foo {}
        export default Foo;
        ''')
        ext = extract_javascript(p)
        assert any(e.name == "Foo" and e.kind == "default" for e in ext.exports)
