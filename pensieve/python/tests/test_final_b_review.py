"""Regression tests for final Phase B review findings.

Finding 1: Validator completeness — signature, Parameter.name, Import.alias
Finding 2: Graph deduplication — no duplicate import/test edges from aliased specifiers
"""

from __future__ import annotations

import pytest

from pensieve.schema import (
    Export,
    FileExtraction,
    Import,
    Parameter,
    SchemaError,
    Symbol,
    CallEdge,
    validate_extraction,
)
from pensieve.graph import build_graph


def _make(**overrides):
    defaults = dict(
        file_path="test.py", language="python", sha256="abc",
        file_size_bytes=10, line_count=1,
    )
    defaults.update(overrides)
    return FileExtraction(**defaults)


def _sym(name="foo", **kw):
    defaults = dict(
        kind="function", line_start=1, line_end=5,
        signature=f"def {name}():", visibility="public",
    )
    defaults.update(kw)
    return Symbol(name=name, **defaults)


# ---------------------------------------------------------------------------
# Finding 1: Validator completeness (systematic sweep)
# ---------------------------------------------------------------------------


class TestValidatorSweep:
    """Every schema field that can be malformed is now validated."""

    def test_empty_signature_rejected(self):
        ext = _make(symbols=[Symbol(
            name="foo", kind="function", line_start=1, line_end=5,
            signature="", visibility="public",
        )])
        with pytest.raises(SchemaError, match="signature is empty"):
            validate_extraction(ext)

    def test_empty_parameter_name_rejected(self):
        ext = _make(symbols=[Symbol(
            name="foo", kind="function", line_start=1, line_end=5,
            signature="def foo():", visibility="public",
            parameters=[Parameter(name="")],
        )])
        with pytest.raises(SchemaError, match="parameters.*name is empty"):
            validate_extraction(ext)

    def test_empty_string_alias_rejected(self):
        """Import.alias="" should be rejected (use None instead)."""
        ext = _make(imports=[Import(module="os", alias="", line=1, kind="import")])
        with pytest.raises(SchemaError, match="alias is empty string"):
            validate_extraction(ext)

    def test_none_alias_accepted(self):
        """Import.alias=None is valid (no alias)."""
        ext = _make(imports=[Import(module="os", alias=None, line=1, kind="import")])
        validate_extraction(ext)  # should not raise

    def test_valid_signature_passes(self):
        ext = _make(symbols=[_sym()])
        validate_extraction(ext)

    def test_valid_parameter_passes(self):
        ext = _make(symbols=[_sym(parameters=[Parameter(name="x")])])
        validate_extraction(ext)

    # Exhaustive: verify we didn't miss anything by constructing a fully
    # populated valid extraction and confirming it passes.
    def test_fully_populated_extraction_passes(self):
        from pensieve.schema import RationaleComment
        ext = _make(
            symbols=[Symbol(
                name="Foo", kind="class", line_start=1, line_end=20,
                signature="class Foo:", visibility="public",
                parameters=[],
            ), Symbol(
                name="bar", kind="method", line_start=5, line_end=10,
                signature="def bar(self, x: int) -> str:", visibility="private",
                parent="Foo",
                parameters=[Parameter(name="self"), Parameter(name="x", type="int")],
                return_type="str",
                docstring="A method.",
            )],
            imports=[
                Import(module="os", line=1, kind="import"),
                Import(module="utils", names=["helper"], alias="h", line=2, kind="from_import"),
            ],
            exports=[Export(name="Foo", kind="default", line=1)],
            call_edges=[CallEdge(caller="bar", callee="helper", line=7, confidence=1.0)],
            rationale_comments=[RationaleComment(tag="WHY", text="reason", line=8, context="bar")],
        )
        validate_extraction(ext)


# ---------------------------------------------------------------------------
# Finding 2: Graph deduplication
# ---------------------------------------------------------------------------


class TestGraphDeduplication:

    def test_aliased_import_no_duplicate_edges(self):
        """import { x, helper as h } from './utils' should produce
        ONE import edge, not two."""
        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[
                    Import(module="./utils.js", names=["x"], line=1, kind="import"),
                    Import(module="./utils.js", names=["helper"], alias="h", line=1, kind="import"),
                ],
                symbols=[_sym("main")],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[_sym("x"), _sym("helper")],
            ),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1  # deduplicated

    def test_aliased_import_no_duplicate_test_edges(self):
        """test_main.js importing { x, helper as h } from './utils.js'
        should produce ONE test edge, not two."""
        exts = [
            FileExtraction(
                file_path="test_main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[
                    Import(module="./utils.js", names=["x"], line=1, kind="import"),
                    Import(module="./utils.js", names=["helper"], alias="h", line=1, kind="import"),
                ],
                symbols=[_sym("test_main")],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[_sym("helper")],
            ),
        ]
        graph = build_graph(exts)
        test_edges = [e for e in graph["edges"] if e["kind"] == "tests"]
        assert len(test_edges) == 1

    def test_import_count_reflects_unique_modules(self):
        """import_count should count unique modules, not Import records."""
        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[
                    Import(module="./utils.js", names=["x"], line=1, kind="import"),
                    Import(module="./utils.js", names=["helper"], alias="h", line=1, kind="import"),
                    Import(module="./other.js", names=["foo"], line=2, kind="import"),
                ],
                symbols=[],
            ),
        ]
        graph = build_graph(exts)
        node = graph["nodes"][0]
        assert node["import_count"] == 2  # utils.js + other.js, not 3 records

    def test_distinct_call_edges_preserved(self):
        """Multiple different calls from one file to the same target
        should ALL be preserved — they carry distinct caller/callee info."""
        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=10,
                imports=[
                    Import(module="./utils.js", names=["a", "b"], line=1, kind="import"),
                ],
                call_edges=[
                    CallEdge(caller="f1", callee="a", line=3),
                    CallEdge(caller="f2", callee="b", line=7),
                ],
                symbols=[
                    Symbol(name="f1", kind="function", line_start=2, line_end=5,
                           signature="function f1()", visibility="public"),
                    Symbol(name="f2", kind="function", line_start=6, line_end=9,
                           signature="function f2()", visibility="public"),
                ],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=5,
                symbols=[
                    Symbol(name="a", kind="function", line_start=1, line_end=2,
                           signature="function a()", visibility="public"),
                    Symbol(name="b", kind="function", line_start=3, line_end=4,
                           signature="function b()", visibility="public"),
                ],
            ),
        ]
        graph = build_graph(exts)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        # BOTH call edges should be present
        assert len(call_edges) == 2
        details = {e["detail"] for e in call_edges}
        assert any("f1" in d and "a" in d for d in details)
        assert any("f2" in d and "b" in d for d in details)

    def test_aliased_import_still_deduped(self):
        """import { x, helper as h } from './utils' should still produce
        only ONE import edge (dedup for imports is correct)."""
        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[
                    Import(module="./utils.js", names=["x"], line=1, kind="import"),
                    Import(module="./utils.js", names=["helper"], alias="h", line=1, kind="import"),
                ],
                symbols=[],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=3,
                symbols=[],
            ),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 1  # still deduped for imports

    def test_different_targets_not_deduped(self):
        """Edges to different targets should NOT be deduped."""
        exts = [
            FileExtraction(
                file_path="main.js", language="javascript",
                sha256="a", file_size_bytes=10, line_count=5,
                imports=[
                    Import(module="./utils.js", names=["x"], line=1, kind="import"),
                    Import(module="./other.js", names=["y"], line=2, kind="import"),
                ],
                symbols=[],
            ),
            FileExtraction(
                file_path="utils.js", language="javascript",
                sha256="b", file_size_bytes=10, line_count=1, symbols=[],
            ),
            FileExtraction(
                file_path="other.js", language="javascript",
                sha256="c", file_size_bytes=10, line_count=1, symbols=[],
            ),
        ]
        graph = build_graph(exts)
        import_edges = [e for e in graph["edges"] if e["kind"] == "imports"]
        assert len(import_edges) == 2  # two different targets
