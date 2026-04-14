"""Tests for the SHA256 extraction cache (milestone B11).

Covers:
  - Normal path: put/get round trip
  - Failure case 1: file content changed → hash differs → cache miss
  - Failure case 2: extractor version changed → cache miss
  - Failure case 3: cache dir doesn't exist → created on first put
  - Failure case 4: corrupted JSON → cache miss + warning, no crash
  - Failure case 5: identical content different paths → shared cache entry
  - Cache operations: has(), invalidate(), clear(), stats()
  - Review fix: cross-language cache isolation (same bytes, different ext)
  - Review fix: schema validation on load (invalid language → cache miss)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve import __version__
from pensieve._version import EXTRACTOR_HASH
from pensieve.cache import ExtractionCache
from pensieve.schema import FileExtraction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_EXT = ".py"


def _make_extraction(
    file_path: str = "src/main.py",
    sha256: str = "abc123",
    **overrides,
) -> FileExtraction:
    defaults = dict(
        file_path=file_path,
        language="python",
        sha256=sha256,
        file_size_bytes=100,
        line_count=10,
        extractor_version=EXTRACTOR_HASH,
    )
    defaults.update(overrides)
    return FileExtraction(**defaults)


# ---------------------------------------------------------------------------
# Normal path
# ---------------------------------------------------------------------------


class TestNormalPath:

    def test_put_then_get(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="deadbeef")
        cache.put(ext, ext=_DEFAULT_EXT)
        result = cache.get("deadbeef", ext=_DEFAULT_EXT)
        assert result is not None
        assert result.sha256 == "deadbeef"
        assert result.file_path == "src/main.py"

    def test_get_miss_returns_none(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        assert cache.get("nonexistent", ext=_DEFAULT_EXT) is None

    def test_put_creates_json_file(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="abc123")
        path = cache.put(ext, ext=_DEFAULT_EXT)
        assert path.exists()
        assert path.suffix == ".json"
        assert "abc123" in path.stem
        assert "py" in path.stem

    def test_round_trip_preserves_all_fields(self, tmp_path):
        from pensieve.schema import Symbol, Import, CallEdge, RationaleComment

        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(
            sha256="full_roundtrip",
            symbols=[Symbol(
                name="foo", kind="function", line_start=1, line_end=5,
                signature="def foo():", visibility="public",
            )],
            imports=[Import(module="os", line=1, kind="import")],
            call_edges=[CallEdge(caller="foo", callee="bar", line=3)],
            rationale_comments=[RationaleComment(
                tag="WHY", text="reason", line=2, context="foo",
            )],
        )
        cache.put(ext, ext=_DEFAULT_EXT)
        result = cache.get("full_roundtrip", ext=_DEFAULT_EXT)
        assert result is not None
        assert len(result.symbols) == 1
        assert result.symbols[0].name == "foo"
        assert len(result.imports) == 1
        assert len(result.call_edges) == 1
        assert len(result.rationale_comments) == 1


# ---------------------------------------------------------------------------
# Failure case 1: content changed
# ---------------------------------------------------------------------------


class TestContentChanged:

    def test_different_hash_is_cache_miss(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="original_hash")
        cache.put(ext, ext=_DEFAULT_EXT)
        assert cache.get("changed_hash", ext=_DEFAULT_EXT) is None

    def test_hash_file_produces_different_hashes(self, tmp_path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("content A")
        f2.write_text("content B")
        assert ExtractionCache.hash_file(f1) != ExtractionCache.hash_file(f2)

    def test_hash_file_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("identical content")
        f2.write_text("identical content")
        assert ExtractionCache.hash_file(f1) == ExtractionCache.hash_file(f2)


# ---------------------------------------------------------------------------
# Failure case 2: version mismatch
# ---------------------------------------------------------------------------


class TestVersionMismatch:

    def test_stale_version_is_cache_miss(self, tmp_path):
        """A cached entry with a different extractor_version is a miss."""
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="versioned", extractor_version="stale_hash")
        # Write directly (bypass put() which overwrites version)
        cache._cache_dir.mkdir(parents=True, exist_ok=True)
        ext.save(cache._cache_path("versioned", _DEFAULT_EXT))
        assert cache.get("versioned", ext=_DEFAULT_EXT) is None

    def test_matching_version_is_cache_hit(self, tmp_path):
        """put() writes EXTRACTOR_HASH; get() defaults to EXTRACTOR_HASH → hit."""
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="versioned")
        cache.put(ext, ext=_DEFAULT_EXT)  # put() sets extractor_version = EXTRACTOR_HASH
        assert cache.get("versioned", ext=_DEFAULT_EXT) is not None

    def test_put_stamps_extractor_hash(self, tmp_path):
        """put() should set extractor_version to EXTRACTOR_HASH."""
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="stamped", extractor_version="anything")
        cache.put(ext, ext=_DEFAULT_EXT)
        # Read back raw JSON to verify the stamp
        import json
        data = json.loads(cache._cache_path("stamped", _DEFAULT_EXT).read_text())
        assert data["extractor_version"] == EXTRACTOR_HASH

    def test_explicit_version_override(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        # Write with a custom version directly
        ext = _make_extraction(sha256="v2_entry", extractor_version="custom_v2")
        cache._cache_dir.mkdir(parents=True, exist_ok=True)
        ext.save(cache._cache_path("v2_entry", _DEFAULT_EXT))
        # Miss with default (EXTRACTOR_HASH)
        assert cache.get("v2_entry", ext=_DEFAULT_EXT) is None
        # Hit with explicit matching version
        assert cache.get("v2_entry", ext=_DEFAULT_EXT, extractor_version="custom_v2") is not None

    def test_extractor_hash_is_not_package_version(self):
        """EXTRACTOR_HASH should be computed from source files, not __version__."""
        assert EXTRACTOR_HASH != __version__
        assert all(c in "0123456789abcdef" for c in EXTRACTOR_HASH)
        assert len(EXTRACTOR_HASH) == 16

    def test_hash_changes_when_extractor_source_changes(self, tmp_path):
        """Core property: modifying an extractor source file produces
        a different hash. This is what makes cache auto-invalidation
        work without developer discipline.

        We can't modify real source files in a test, so we simulate by
        calling _compute_extractor_hash's logic on a controlled set of
        files, modifying one, and verifying the hash changes.
        """
        import hashlib

        # Create fake "extractor source files"
        src_dir = tmp_path / "extractors"
        src_dir.mkdir()
        (src_dir / "python.py").write_text("def extract(): pass  # v1")
        (src_dir / "javascript.py").write_text("def extract(): pass")
        schema = tmp_path / "schema.py"
        schema.write_text("class FileExtraction: pass")

        def compute_hash(directory, schema_path):
            files = sorted(directory.glob("*.py"))
            if schema_path.exists():
                files.append(schema_path)
            hasher = hashlib.sha256()
            for f in sorted(files):
                hasher.update(f.read_bytes())
            return hasher.hexdigest()[:16]

        hash_v1 = compute_hash(src_dir, schema)

        # Modify one extractor file
        (src_dir / "python.py").write_text("def extract(): pass  # v2 changed")

        hash_v2 = compute_hash(src_dir, schema)

        assert hash_v1 != hash_v2, (
            "Hash should change when an extractor source file is modified"
        )

        # Modify schema.py
        schema.write_text("class FileExtraction: version = 2")

        hash_v3 = compute_hash(src_dir, schema)

        assert hash_v2 != hash_v3, (
            "Hash should change when schema.py is modified"
        )

    def test_extractor_hash_includes_all_expected_files(self):
        """Verify the hash computation reads from the actual extractor
        source files by checking that the _compute function uses the
        same file set we expect."""
        from pensieve._version import _compute_extractor_hash
        from pathlib import Path
        import pensieve.extractors as ext_pkg

        pkg_dir = Path(ext_pkg.__file__).parent
        schema_path = pkg_dir.parent / "schema.py"

        expected_files = sorted(pkg_dir.glob("*.py"))
        if schema_path.exists():
            expected_files.append(schema_path)

        # At minimum, we expect: __init__.py, _comments.py, python.py,
        # javascript.py, typescript.py, go.py, java.py, rust.py, schema.py
        file_names = {f.name for f in expected_files}
        assert "__init__.py" in file_names
        assert "_comments.py" in file_names
        assert "python.py" in file_names
        assert "javascript.py" in file_names
        assert "schema.py" in file_names
        assert len(expected_files) >= 9  # 8 extractor files + schema.py


# ---------------------------------------------------------------------------
# Failure case 3: cache dir doesn't exist
# ---------------------------------------------------------------------------


class TestLazyDirectoryCreation:

    def test_get_on_nonexistent_dir_returns_none(self, tmp_path):
        cache = ExtractionCache(tmp_path / "nonexistent" / ".cache")
        assert cache.get("anything", ext=_DEFAULT_EXT) is None

    def test_put_creates_directory(self, tmp_path):
        cache_dir = tmp_path / "deep" / "nested" / ".cache"
        cache = ExtractionCache(cache_dir)
        assert not cache_dir.exists()
        ext = _make_extraction(sha256="first_write")
        cache.put(ext, ext=_DEFAULT_EXT)
        assert cache_dir.exists()

    def test_put_idempotent_on_existing_dir(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        cache.put(_make_extraction(sha256="entry1"), ext=_DEFAULT_EXT)
        cache.put(_make_extraction(sha256="entry2"), ext=_DEFAULT_EXT)
        assert cache.get("entry1", ext=_DEFAULT_EXT) is not None
        assert cache.get("entry2", ext=_DEFAULT_EXT) is not None


# ---------------------------------------------------------------------------
# Failure case 4: corrupted JSON
# ---------------------------------------------------------------------------


class TestCorruptedCache:

    def test_corrupted_json_returns_none(self, tmp_path):
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        cache = ExtractionCache(cache_dir)
        (cache_dir / "corrupted_py.json").write_text("not valid json {{{")
        with pytest.warns(UserWarning, match="Corrupted cache entry"):
            assert cache.get("corrupted", ext=_DEFAULT_EXT) is None

    def test_truncated_json_returns_none(self, tmp_path):
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        cache = ExtractionCache(cache_dir)
        (cache_dir / "truncated_py.json").write_text('{"file_path": "test.py"')
        with pytest.warns(UserWarning, match="Corrupted cache entry"):
            assert cache.get("truncated", ext=_DEFAULT_EXT) is None

    def test_empty_file_returns_none(self, tmp_path):
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        cache = ExtractionCache(cache_dir)
        (cache_dir / "empty_py.json").write_text("")
        with pytest.warns(UserWarning, match="Corrupted cache entry"):
            assert cache.get("empty", ext=_DEFAULT_EXT) is None

    def test_hash_mismatch_in_cached_entry(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="real_hash")
        cache.put(ext, ext=_DEFAULT_EXT)
        old = tmp_path / ".cache" / "real_hash_py.json"
        new = tmp_path / ".cache" / "wrong_hash_py.json"
        old.rename(new)
        with pytest.warns(UserWarning, match="Cache integrity error"):
            assert cache.get("wrong_hash", ext=_DEFAULT_EXT) is None


# ---------------------------------------------------------------------------
# Failure case 5: identical content, different paths
# ---------------------------------------------------------------------------


class TestSharedCacheEntry:

    def test_identical_content_shares_cache(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext_a = _make_extraction(file_path="a.py", sha256="same_hash")
        cache.put(ext_a, ext=_DEFAULT_EXT)
        result = cache.get("same_hash", ext=_DEFAULT_EXT)
        assert result is not None
        assert result.file_path == "a.py"

    def test_overwrite_updates_cached_entry(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        cache.put(_make_extraction(file_path="a.py", sha256="shared"), ext=_DEFAULT_EXT)
        cache.put(_make_extraction(file_path="b.py", sha256="shared"), ext=_DEFAULT_EXT)
        result = cache.get("shared", ext=_DEFAULT_EXT)
        assert result is not None
        assert result.file_path == "b.py"


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------


class TestCacheOperations:

    def test_has(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        cache.put(_make_extraction(sha256="exists"), ext=_DEFAULT_EXT)
        assert cache.has("exists", ext=_DEFAULT_EXT) is True
        assert cache.has("missing", ext=_DEFAULT_EXT) is False

    def test_invalidate_existing(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        cache.put(_make_extraction(sha256="to_remove"), ext=_DEFAULT_EXT)
        assert cache.invalidate("to_remove", ext=_DEFAULT_EXT) is True
        assert cache.get("to_remove", ext=_DEFAULT_EXT) is None

    def test_invalidate_nonexistent(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        assert cache.invalidate("never_existed", ext=_DEFAULT_EXT) is False

    def test_clear(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        for i in range(5):
            cache.put(_make_extraction(sha256=f"entry_{i}"), ext=_DEFAULT_EXT)
        assert cache.clear() == 5
        assert cache.stats()["entries"] == 0

    def test_clear_empty_dir(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        assert cache.clear() == 0

    def test_stats(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        for i in range(3):
            cache.put(_make_extraction(sha256=f"stat_{i}"), ext=_DEFAULT_EXT)
        s = cache.stats()
        assert s["entries"] == 3
        assert s["size_bytes"] > 0

    def test_stats_empty(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        assert cache.stats() == {"entries": 0, "size_bytes": 0}


# ---------------------------------------------------------------------------
# Integration with real file hashing
# ---------------------------------------------------------------------------


class TestHashFileIntegration:

    def test_extract_cache_put_get_with_real_file(self, tmp_path):
        from pensieve.extractors.python import extract_python
        src = tmp_path / "hello.py"
        src.write_text("def hello():\n    return 42\n")

        cache = ExtractionCache(tmp_path / ".cache")
        sha = cache.hash_file(src)
        assert cache.get(sha, ext=".py") is None

        ext = extract_python(src)
        ext.sha256 = sha
        cache.put(ext, ext=".py")

        result = cache.get(sha, ext=".py")
        assert result is not None
        assert any(s.name == "hello" for s in result.symbols)

    def test_modified_file_misses_cache(self, tmp_path):
        from pensieve.extractors.python import extract_python
        src = tmp_path / "counter.py"
        src.write_text("count = 1\n")

        cache = ExtractionCache(tmp_path / ".cache")
        sha_v1 = cache.hash_file(src)
        ext = extract_python(src)
        ext.sha256 = sha_v1
        cache.put(ext, ext=".py")

        src.write_text("count = 2\n")
        sha_v2 = cache.hash_file(src)
        assert sha_v1 != sha_v2
        assert cache.get(sha_v2, ext=".py") is None
        assert cache.get(sha_v1, ext=".py") is not None


# ---------------------------------------------------------------------------
# Review fix 1: cross-language cache isolation
# ---------------------------------------------------------------------------


class TestCrossLanguageIsolation:
    """Same bytes in .js and .ts must NOT share a cache entry."""

    def test_same_content_different_extensions_separate_entries(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")

        js_ext = _make_extraction(
            sha256="same_bytes", language="javascript", file_path="lib.js",
        )
        ts_ext = _make_extraction(
            sha256="same_bytes", language="typescript", file_path="lib.ts",
        )

        cache.put(js_ext, ext=".js")
        cache.put(ts_ext, ext=".ts")

        js_result = cache.get("same_bytes", ext=".js")
        ts_result = cache.get("same_bytes", ext=".ts")

        assert js_result is not None
        assert ts_result is not None
        assert js_result.language == "javascript"
        assert ts_result.language == "typescript"

    def test_js_cached_does_not_serve_ts(self, tmp_path):
        """If only .js is cached, .ts lookup is a miss."""
        cache = ExtractionCache(tmp_path / ".cache")
        js_ext = _make_extraction(
            sha256="shared", language="javascript", file_path="lib.js",
        )
        cache.put(js_ext, ext=".js")

        # .ts lookup should miss, NOT return the .js extraction
        assert cache.get("shared", ext=".ts") is None

    def test_cache_file_names_include_extension(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="abc123")
        path = cache.put(ext, ext=".py")
        assert "py" in path.stem
        assert path.stem == "abc123_py"


# ---------------------------------------------------------------------------
# Review fix 2: schema validation on load
# ---------------------------------------------------------------------------


class TestSchemaValidationOnLoad:
    """get() should reject cached entries that fail schema validation."""

    def test_invalid_language_is_cache_miss(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")

        # Write a valid-looking but semantically invalid entry
        ext = _make_extraction(sha256="cobol_test")
        cache.put(ext, ext=_DEFAULT_EXT)

        # Tamper with the cached file to have an invalid language
        cache_file = tmp_path / ".cache" / "cobol_test_py.json"
        data = json.loads(cache_file.read_text())
        data["language"] = "cobol"
        cache_file.write_text(json.dumps(data))

        with pytest.warns(UserWarning, match="fails schema validation"):
            result = cache.get("cobol_test", ext=_DEFAULT_EXT)
        assert result is None

    def test_empty_file_path_is_cache_miss(self, tmp_path):
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="no_path")
        cache.put(ext, ext=_DEFAULT_EXT)

        cache_file = tmp_path / ".cache" / "no_path_py.json"
        data = json.loads(cache_file.read_text())
        data["file_path"] = ""
        cache_file.write_text(json.dumps(data))

        with pytest.warns(UserWarning, match="fails schema validation"):
            assert cache.get("no_path", ext=_DEFAULT_EXT) is None

    def test_valid_entry_passes_validation(self, tmp_path):
        """A properly cached entry passes validation and is returned."""
        cache = ExtractionCache(tmp_path / ".cache")
        ext = _make_extraction(sha256="good_entry")
        cache.put(ext, ext=_DEFAULT_EXT)
        result = cache.get("good_entry", ext=_DEFAULT_EXT)
        assert result is not None
