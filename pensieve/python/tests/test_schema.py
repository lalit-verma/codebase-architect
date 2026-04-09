"""Tests for the per-file structural extraction schema (milestone B3).

Covers: construction, serialization, deserialization, round-tripping,
validation (both valid and invalid cases), and edge cases.
"""

from __future__ import annotations

import json

import pytest

from pensieve.schema import (
    CallEdge,
    Export,
    FileExtraction,
    Import,
    Parameter,
    RationaleComment,
    SchemaError,
    Symbol,
    validate_extraction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_minimal_extraction(**overrides) -> FileExtraction:
    """Create a minimal valid FileExtraction with optional overrides."""
    defaults = dict(
        file_path="src/main.py",
        language="python",
        sha256="abc123def456",
        file_size_bytes=1024,
        line_count=42,
    )
    defaults.update(overrides)
    return FileExtraction(**defaults)


def _make_full_extraction() -> FileExtraction:
    """Create a fully populated FileExtraction for round-trip testing."""
    return FileExtraction(
        file_path="src/calculator.py",
        language="python",
        sha256="e3b0c44298fc1c149afbf4c8996fb924",
        file_size_bytes=2048,
        line_count=85,
        symbols=[
            Symbol(
                name="Calculator",
                kind="class",
                line_start=10,
                line_end=80,
                signature="class Calculator:",
                visibility="public",
                docstring="A simple calculator.",
            ),
            Symbol(
                name="add",
                kind="method",
                line_start=15,
                line_end=20,
                signature="def add(self, a: int, b: int) -> int:",
                visibility="public",
                parent="Calculator",
                parameters=[
                    Parameter(name="self"),
                    Parameter(name="a", type="int"),
                    Parameter(name="b", type="int", default=None),
                ],
                return_type="int",
            ),
            Symbol(
                name="PI",
                kind="constant",
                line_start=1,
                line_end=1,
                signature="PI = 3.14159",
                visibility="public",
            ),
        ],
        imports=[
            Import(module="math", names=["sqrt", "pi"], line=1, kind="from_import"),
            Import(module="os", line=2, kind="import"),
            Import(module="typing", names=["Optional"], alias=None, line=3, kind="from_import"),
        ],
        exports=[],
        call_edges=[
            CallEdge(caller="add", callee="sqrt", line=18, confidence=1.0),
            CallEdge(caller="add", callee="validate", line=16, confidence=0.7),
        ],
        rationale_comments=[
            RationaleComment(
                tag="WHY",
                text="Using sqrt here for distance calculation",
                line=18,
                context="add",
            ),
            RationaleComment(
                tag="HACK",
                text="Temporary workaround for float precision",
                line=25,
                context="Calculator",
            ),
        ],
        extraction_errors=[],
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_minimal_extraction(self):
        ext = _make_minimal_extraction()
        assert ext.file_path == "src/main.py"
        assert ext.language == "python"
        assert ext.symbols == []
        assert ext.imports == []
        assert ext.exports == []
        assert ext.call_edges == []
        assert ext.rationale_comments == []

    def test_full_extraction(self):
        ext = _make_full_extraction()
        assert len(ext.symbols) == 3
        assert len(ext.imports) == 3
        assert len(ext.call_edges) == 2
        assert len(ext.rationale_comments) == 2

    def test_symbol_with_parameters(self):
        ext = _make_full_extraction()
        method = ext.symbols[1]
        assert method.name == "add"
        assert method.parent == "Calculator"
        assert len(method.parameters) == 3
        assert method.parameters[1].name == "a"
        assert method.parameters[1].type == "int"

    def test_extractor_version_auto_populated(self):
        ext = _make_minimal_extraction()
        assert ext.extractor_version  # non-empty
        assert len(ext.extractor_version) > 0
        # extractor_version is now EXTRACTOR_HASH (hex string), not a
        # dotted version. It should be a hex string or a version string
        # (fallback case).
        assert isinstance(ext.extractor_version, str)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_dict(self):
        ext = _make_minimal_extraction()
        d = ext.to_dict()
        assert isinstance(d, dict)
        assert d["file_path"] == "src/main.py"
        assert d["language"] == "python"
        assert d["symbols"] == []

    def test_to_json(self):
        ext = _make_minimal_extraction()
        j = ext.to_json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["file_path"] == "src/main.py"

    def test_full_extraction_to_json(self):
        ext = _make_full_extraction()
        j = ext.to_json()
        parsed = json.loads(j)
        assert len(parsed["symbols"]) == 3
        assert parsed["symbols"][1]["parameters"][1]["type"] == "int"

    def test_to_dict_preserves_nested_parameters(self):
        ext = _make_full_extraction()
        d = ext.to_dict()
        method_dict = d["symbols"][1]
        assert isinstance(method_dict["parameters"], list)
        assert method_dict["parameters"][1]["name"] == "a"
        assert method_dict["parameters"][1]["type"] == "int"


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------


class TestDeserialization:
    def test_from_dict_minimal(self):
        original = _make_minimal_extraction()
        d = original.to_dict()
        restored = FileExtraction.from_dict(d)
        assert restored.file_path == original.file_path
        assert restored.language == original.language
        assert restored.sha256 == original.sha256

    def test_from_json_minimal(self):
        original = _make_minimal_extraction()
        j = original.to_json()
        restored = FileExtraction.from_json(j)
        assert restored.file_path == original.file_path

    def test_from_dict_full(self):
        original = _make_full_extraction()
        d = original.to_dict()
        restored = FileExtraction.from_dict(d)
        assert len(restored.symbols) == 3
        assert restored.symbols[1].name == "add"
        assert restored.symbols[1].parent == "Calculator"
        assert len(restored.symbols[1].parameters) == 3
        assert restored.symbols[1].parameters[1].type == "int"

    def test_round_trip_json(self):
        """Full round trip: construction → JSON → back to dataclass."""
        original = _make_full_extraction()
        j = original.to_json()
        restored = FileExtraction.from_json(j)

        assert restored.file_path == original.file_path
        assert restored.language == original.language
        assert len(restored.symbols) == len(original.symbols)
        assert len(restored.imports) == len(original.imports)
        assert len(restored.call_edges) == len(original.call_edges)
        assert len(restored.rationale_comments) == len(original.rationale_comments)

        # Deep check on a method's parameters
        orig_method = original.symbols[1]
        rest_method = restored.symbols[1]
        assert rest_method.name == orig_method.name
        assert rest_method.parent == orig_method.parent
        assert rest_method.return_type == orig_method.return_type
        assert len(rest_method.parameters) == len(orig_method.parameters)
        for op, rp in zip(orig_method.parameters, rest_method.parameters):
            assert rp.name == op.name
            assert rp.type == op.type

    def test_from_dict_with_missing_optional_fields(self):
        """Deserialization handles missing optional fields gracefully."""
        d = {
            "file_path": "test.py",
            "language": "python",
            "sha256": "abc",
            "file_size_bytes": 100,
            "line_count": 5,
        }
        ext = FileExtraction.from_dict(d)
        assert ext.symbols == []
        assert ext.imports == []
        assert ext.extractor_version == "unknown"

    def test_round_trip_preserves_call_edge_confidence(self):
        ext = _make_full_extraction()
        j = ext.to_json()
        restored = FileExtraction.from_json(j)
        assert restored.call_edges[0].confidence == 1.0
        assert restored.call_edges[1].confidence == 0.7

    def test_round_trip_preserves_rationale_comments(self):
        ext = _make_full_extraction()
        j = ext.to_json()
        restored = FileExtraction.from_json(j)
        assert restored.rationale_comments[0].tag == "WHY"
        assert restored.rationale_comments[0].context == "add"
        assert restored.rationale_comments[1].tag == "HACK"


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


class TestFileIO:
    def test_save_and_load(self, tmp_path):
        original = _make_full_extraction()
        filepath = tmp_path / "extraction.json"
        original.save(filepath)

        assert filepath.exists()
        loaded = FileExtraction.load(filepath)
        assert loaded.file_path == original.file_path
        assert len(loaded.symbols) == len(original.symbols)

    def test_saved_file_is_valid_json(self, tmp_path):
        ext = _make_full_extraction()
        filepath = tmp_path / "extraction.json"
        ext.save(filepath)

        raw = filepath.read_text()
        parsed = json.loads(raw)
        assert "file_path" in parsed
        assert "symbols" in parsed


# ---------------------------------------------------------------------------
# Validation — valid cases
# ---------------------------------------------------------------------------


class TestValidationValid:
    def test_minimal_valid(self):
        ext = _make_minimal_extraction()
        errors = validate_extraction(ext)  # should not raise
        assert errors == []

    def test_full_valid(self):
        ext = _make_full_extraction()
        errors = validate_extraction(ext)
        assert errors == []


# ---------------------------------------------------------------------------
# Validation — invalid cases
# ---------------------------------------------------------------------------


class TestValidationInvalid:
    def test_empty_file_path(self):
        ext = _make_minimal_extraction(file_path="")
        with pytest.raises(SchemaError, match="file_path is empty"):
            validate_extraction(ext)

    def test_invalid_language(self):
        ext = _make_minimal_extraction(language="cobol")  # type: ignore[arg-type]
        with pytest.raises(SchemaError, match="language.*not in"):
            validate_extraction(ext)

    def test_empty_sha256(self):
        ext = _make_minimal_extraction(sha256="")
        with pytest.raises(SchemaError, match="sha256 is empty"):
            validate_extraction(ext)

    def test_negative_file_size(self):
        ext = _make_minimal_extraction(file_size_bytes=-1)
        with pytest.raises(SchemaError, match="file_size_bytes is negative"):
            validate_extraction(ext)

    def test_negative_line_count(self):
        ext = _make_minimal_extraction(line_count=-1)
        with pytest.raises(SchemaError, match="line_count is negative"):
            validate_extraction(ext)

    def test_invalid_symbol_kind(self):
        ext = _make_minimal_extraction(
            symbols=[
                Symbol(
                    name="foo",
                    kind="widget",  # type: ignore[arg-type]
                    line_start=1,
                    line_end=5,
                    signature="def foo():",
                )
            ]
        )
        with pytest.raises(SchemaError, match="kind.*not in"):
            validate_extraction(ext)

    def test_empty_symbol_name(self):
        ext = _make_minimal_extraction(
            symbols=[
                Symbol(name="", kind="function", line_start=1, line_end=5, signature="def ():")
            ]
        )
        with pytest.raises(SchemaError, match="name is empty"):
            validate_extraction(ext)

    def test_line_end_before_start(self):
        ext = _make_minimal_extraction(
            symbols=[
                Symbol(name="foo", kind="function", line_start=10, line_end=5, signature="def foo():")
            ]
        )
        with pytest.raises(SchemaError, match="line_end.*< line_start"):
            validate_extraction(ext)

    def test_empty_import_module(self):
        ext = _make_minimal_extraction(imports=[Import(module="")])
        with pytest.raises(SchemaError, match="module is empty"):
            validate_extraction(ext)

    def test_call_edge_confidence_out_of_range(self):
        ext = _make_minimal_extraction(
            call_edges=[CallEdge(caller="a", callee="b", confidence=1.5)]
        )
        with pytest.raises(SchemaError, match="confidence.*not in"):
            validate_extraction(ext)

    def test_call_edge_empty_caller(self):
        ext = _make_minimal_extraction(
            call_edges=[CallEdge(caller="", callee="b")]
        )
        with pytest.raises(SchemaError, match="caller is empty"):
            validate_extraction(ext)

    def test_invalid_rationale_tag(self):
        ext = _make_minimal_extraction(
            rationale_comments=[
                RationaleComment(tag="YOLO", text="whatever", line=1)  # type: ignore[arg-type]
            ]
        )
        with pytest.raises(SchemaError, match="tag.*not in"):
            validate_extraction(ext)

    def test_empty_rationale_text(self):
        ext = _make_minimal_extraction(
            rationale_comments=[
                RationaleComment(tag="WHY", text="", line=1)
            ]
        )
        with pytest.raises(SchemaError, match="text is empty"):
            validate_extraction(ext)

    def test_multiple_errors_reported(self):
        ext = _make_minimal_extraction(
            file_path="",
            sha256="",
            language="unknown",  # type: ignore[arg-type]
        )
        with pytest.raises(SchemaError) as exc_info:
            validate_extraction(ext)
        error_text = str(exc_info.value)
        assert "3 error(s)" in error_text
        assert "file_path" in error_text
        assert "sha256" in error_text
        assert "language" in error_text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_zero_byte_file(self):
        ext = _make_minimal_extraction(file_size_bytes=0, line_count=0)
        validate_extraction(ext)  # should not raise

    def test_symbol_on_single_line(self):
        ext = _make_minimal_extraction(
            symbols=[
                Symbol(
                    name="PI",
                    kind="constant",
                    line_start=1,
                    line_end=1,
                    signature="PI = 3.14",
                )
            ]
        )
        validate_extraction(ext)

    def test_all_languages_accepted(self):
        for lang in ["python", "javascript", "typescript", "go", "java", "rust"]:
            ext = _make_minimal_extraction(language=lang)  # type: ignore[arg-type]
            validate_extraction(ext)

    def test_all_symbol_kinds_accepted(self):
        for kind in [
            "function", "class", "method", "interface", "trait",
            "struct", "enum", "type_alias", "constant",
        ]:
            ext = _make_minimal_extraction(
                symbols=[
                    Symbol(name="x", kind=kind, line_start=1, line_end=1, signature="x")  # type: ignore[arg-type]
                ]
            )
            validate_extraction(ext)

    def test_all_comment_tags_accepted(self):
        for tag in ["WHY", "NOTE", "IMPORTANT", "HACK", "TODO", "FIXME"]:
            ext = _make_minimal_extraction(
                rationale_comments=[
                    RationaleComment(tag=tag, text="reason", line=1)  # type: ignore[arg-type]
                ]
            )
            validate_extraction(ext)
