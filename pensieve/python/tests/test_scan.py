"""Tests for the repository scanner (milestone B12).

Covers:
  - Normal path: scan a repo with mixed language files
  - Failure case 1: empty repo → empty structure.json
  - Failure case 2: extraction exception → error in errors list, not files
  - Failure case 3: extract_file returns None → recorded as failure
  - Ignore patterns: pruned during walk, not filtered after
  - Cache behavior: hits, misses, path normalization
  - CLI subcommand
  - structure.json format: files are schema-valid, errors are separate
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pensieve.scan import scan_repo, _collect_files, DEFAULT_IGNORE_DIRS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel_path, content in files.items():
        f = repo / rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return repo


# ---------------------------------------------------------------------------
# File detection (with pruning)
# ---------------------------------------------------------------------------


class TestCollectFiles:

    def test_finds_supported_files(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "main.py": "x = 1",
            "lib.js": "const x = 1;",
            "readme.md": "# hello",
        })
        from pensieve.extractors import supported_extensions
        files = _collect_files(repo, supported_extensions(), DEFAULT_IGNORE_DIRS)
        names = {f.name for f in files}
        assert "main.py" in names
        assert "lib.js" in names
        assert "readme.md" not in names

    def test_skips_ignored_directories(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "src/main.py": "x = 1",
            "node_modules/dep/index.js": "module.exports = {}",
            ".git/config": "# git config",
            "__pycache__/mod.py": "cached",
            "vendor/lib.go": "package lib",
        })
        from pensieve.extractors import supported_extensions
        files = _collect_files(repo, supported_extensions(), DEFAULT_IGNORE_DIRS)
        rel_paths = {str(f.relative_to(repo)) for f in files}
        assert "src/main.py" in rel_paths
        assert not any("node_modules" in p for p in rel_paths)
        assert not any("__pycache__" in p for p in rel_paths)
        assert not any("vendor" in p for p in rel_paths)
        assert not any(".git" in p for p in rel_paths)

    def test_empty_directory(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()
        from pensieve.extractors import supported_extensions
        files = _collect_files(repo, supported_extensions(), DEFAULT_IGNORE_DIRS)
        assert files == []

    def test_pruning_prevents_descent_into_ignored_dirs(self, tmp_path):
        """Verify os.walk pruning: os.walk should NOT descend into
        ignored directories. We verify by checking that a deeply nested
        file inside node_modules is never visited."""
        repo = _make_repo(tmp_path, {
            "src/main.py": "x = 1",
            "node_modules/deep/nested/pkg/index.js": "x = 1",
        })

        walked_dirs: list[str] = []
        original_walk = os.walk

        def tracking_walk(*args, **kwargs):
            for dirpath, dirnames, filenames in original_walk(*args, **kwargs):
                walked_dirs.append(dirpath)
                yield dirpath, dirnames, filenames

        from pensieve.extractors import supported_extensions
        with patch("pensieve.scan.os.walk", side_effect=tracking_walk):
            _collect_files(repo, supported_extensions(), DEFAULT_IGNORE_DIRS)

        # os.walk should NOT have entered node_modules
        walked_names = [os.path.basename(d) for d in walked_dirs]
        assert "node_modules" not in walked_names
        assert "deep" not in walked_names


# ---------------------------------------------------------------------------
# Normal scan
# ---------------------------------------------------------------------------


class TestScanRepo:

    def test_scan_mixed_languages(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "main.py": "def hello(): pass\n",
            "lib.js": "function greet() {}\n",
            "util.go": "package util\n\nfunc Add(a, b int) int { return a + b }\n",
        })
        result = scan_repo(repo)
        assert result.stats["total_files"] == 3
        assert result.stats["extracted"] == 3
        assert result.stats["failed"] == 0
        assert len(result.extractions) == 3
        assert len(result.errors) == 0

        paths = {e.file_path for e in result.extractions}
        assert "main.py" in paths
        assert all(not e.file_path.startswith("/") for e in result.extractions)

    def test_structure_json_written(self, tmp_path):
        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})
        result = scan_repo(repo)
        assert result.structure_path.exists()
        data = json.loads(result.structure_path.read_text())
        assert "version" in data
        assert "files" in data
        assert "errors" in data
        assert "scan_stats" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["file_path"] == "main.py"
        assert data["errors"] == []

    def test_structure_json_files_are_schema_valid(self, tmp_path):
        """Every entry in structure.json files[] must pass schema validation."""
        from pensieve.schema import FileExtraction, validate_extraction

        repo = _make_repo(tmp_path, {
            "a.py": "def a(): pass\n",
            "b.js": "function b() {}\n",
        })
        result = scan_repo(repo)
        data = json.loads(result.structure_path.read_text())

        for file_entry in data["files"]:
            ext = FileExtraction.from_dict(file_entry)
            validate_extraction(ext)  # must not raise

    def test_output_dir_created(self, tmp_path):
        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})
        output = repo / "agent-docs"
        assert not output.exists()
        scan_repo(repo)
        assert output.exists()


# ---------------------------------------------------------------------------
# Failure case 1: empty repo
# ---------------------------------------------------------------------------


class TestEmptyRepo:

    def test_no_supported_files(self, tmp_path):
        repo = _make_repo(tmp_path, {"readme.md": "# Hello"})
        result = scan_repo(repo)
        assert result.stats["total_files"] == 0
        assert len(result.extractions) == 0
        data = json.loads(result.structure_path.read_text())
        assert data["files"] == []
        assert data["errors"] == []

    def test_completely_empty_dir(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()
        result = scan_repo(repo)
        assert result.stats["total_files"] == 0


# ---------------------------------------------------------------------------
# Failure case 2: extraction exception → error channel, not files
# ---------------------------------------------------------------------------


class TestExtractionException:

    def test_exception_goes_to_errors_not_files(self, tmp_path):
        """When extract_file raises, the error should appear in
        result.errors and structure.json errors[], NOT in files[]."""
        repo = _make_repo(tmp_path, {
            "good.py": "def hello(): pass\n",
            "bad.py": "also valid python\n",
        })

        original_extract = __import__(
            "pensieve.extractors", fromlist=["extract_file"]
        ).extract_file

        def failing_extract(path):
            if path.name == "bad.py":
                raise RuntimeError("simulated extractor crash")
            return original_extract(path)

        with patch("pensieve.scan.extract_file", side_effect=failing_extract):
            result = scan_repo(repo)

        # good.py should be extracted normally
        assert any(e.file_path == "good.py" for e in result.extractions)

        # bad.py should be in errors, NOT in extractions
        assert not any(e.file_path == "bad.py" for e in result.extractions)
        assert any("bad.py" in err["file_path"] for err in result.errors)
        assert result.stats["failed"] == 1

        # structure.json files[] should contain only schema-valid entries
        data = json.loads(result.structure_path.read_text())
        assert len(data["files"]) == 1  # only good.py
        assert len(data["errors"]) == 1  # bad.py


# ---------------------------------------------------------------------------
# Failure case 3: extract_file returns None → failure, not skip
# ---------------------------------------------------------------------------


class TestInvalidExtractorOutput:

    def test_schema_invalid_extraction_goes_to_errors(self, tmp_path):
        """If extract_file returns a schema-invalid FileExtraction (e.g.,
        language='cobol'), it should go to errors, not files/cache."""
        from pensieve.schema import FileExtraction as FE

        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})

        def bad_extractor(path):
            return FE(
                file_path=str(path),
                language="cobol",  # invalid language
                sha256="abc",
                file_size_bytes=10,
                line_count=1,
            )

        with patch("pensieve.scan.extract_file", side_effect=bad_extractor):
            result = scan_repo(repo)

        assert result.stats["failed"] == 1
        assert result.stats["extracted"] == 0
        assert len(result.extractions) == 0
        assert len(result.errors) == 1
        assert "schema-invalid" in result.errors[0]["error"].lower() or "cobol" in result.errors[0]["error"].lower()

        # structure.json files[] must be empty
        data = json.loads(result.structure_path.read_text())
        assert len(data["files"]) == 0
        assert len(data["errors"]) == 1

    def test_empty_import_module_goes_to_errors(self, tmp_path):
        """An extraction with an empty import module fails validation
        and should go to errors."""
        from pensieve.schema import FileExtraction as FE, Import

        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})

        def bad_extractor(path):
            return FE(
                file_path=str(path),
                language="python",
                sha256="abc",
                file_size_bytes=10,
                line_count=1,
                imports=[Import(module="")],  # empty module fails validation
            )

        with patch("pensieve.scan.extract_file", side_effect=bad_extractor):
            result = scan_repo(repo)

        assert result.stats["failed"] == 1
        assert len(result.extractions) == 0
        assert len(result.errors) == 1

    def test_valid_extraction_still_works(self, tmp_path):
        """Sanity check: valid extractions still go to files[], not errors."""
        repo = _make_repo(tmp_path, {"main.py": "def hello(): pass\n"})
        result = scan_repo(repo)
        assert result.stats["extracted"] == 1
        assert result.stats["failed"] == 0
        assert len(result.extractions) == 1
        assert len(result.errors) == 0


class TestExtractFileNone:

    def test_none_on_supported_file_is_failure(self, tmp_path):
        """extract_file returning None on a .py file means the extractor
        failed to load. This should be recorded as a failure, not silently
        skipped."""
        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})

        with patch("pensieve.scan.extract_file", return_value=None):
            result = scan_repo(repo)

        assert result.stats["failed"] == 1
        assert len(result.errors) == 1
        assert "main.py" in result.errors[0]["file_path"]
        assert "None" in result.errors[0]["error"] or "Extractor" in result.errors[0]["error"]
        assert len(result.extractions) == 0


# ---------------------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------------------


class TestCacheBehavior:

    def test_second_scan_uses_cache(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "main.py": "def hello(): pass\n",
            "lib.py": "def world(): pass\n",
        })
        r1 = scan_repo(repo)
        assert r1.stats["extracted"] == 2
        assert r1.stats["cached"] == 0

        r2 = scan_repo(repo)
        assert r2.stats["extracted"] == 0
        assert r2.stats["cached"] == 2

    def test_modified_file_re_extracted(self, tmp_path):
        repo = _make_repo(tmp_path, {"main.py": "def v1(): pass\n"})
        scan_repo(repo)
        (repo / "main.py").write_text("def v2(): pass\n")
        r2 = scan_repo(repo)
        assert r2.stats["extracted"] == 1
        assert r2.stats["cached"] == 0
        assert any(s.name == "v2" for e in r2.extractions for s in e.symbols)

    def test_cached_entry_path_normalized(self, tmp_path):
        repo = _make_repo(tmp_path, {"src/main.py": "def f(): pass\n"})
        scan_repo(repo)
        r2 = scan_repo(repo)
        assert r2.extractions[0].file_path == "src/main.py"


# ---------------------------------------------------------------------------
# Ignore patterns
# ---------------------------------------------------------------------------


class TestIgnorePatterns:

    def test_default_ignores(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "src/app.py": "app = True\n",
            "node_modules/pkg/index.js": "module.exports = 1",
            ".git/objects/ab": "blob",
            "vendor/dep.go": "package dep\n",
            ".venv/lib/six.py": "x = 6\n",
        })
        result = scan_repo(repo)
        paths = {e.file_path for e in result.extractions}
        assert "src/app.py" in paths
        assert not any("node_modules" in p for p in paths)
        assert not any("vendor" in p for p in paths)
        assert not any(".venv" in p for p in paths)

    def test_agent_docs_not_scanned(self, tmp_path):
        repo = _make_repo(tmp_path, {
            "main.py": "x = 1\n",
            "agent-docs/old.py": "stale = True\n",
        })
        result = scan_repo(repo)
        assert not any("agent-docs" in e.file_path for e in result.extractions)


# ---------------------------------------------------------------------------
# CLI subcommand
# ---------------------------------------------------------------------------


class TestCLI:

    def test_scan_subcommand(self, tmp_path):
        from pensieve.cli import main
        repo = _make_repo(tmp_path, {"main.py": "def f(): pass\n"})
        result = main(["scan", str(repo)])
        assert result == 0
        assert (repo / "agent-docs" / "structure.json").exists()

    def test_scan_nonexistent_path(self, tmp_path, capsys):
        from pensieve.cli import main
        result = main(["scan", str(tmp_path / "nonexistent")])
        assert result == 1
        assert "not a directory" in capsys.readouterr().err

    def test_scan_default_current_dir(self, tmp_path, monkeypatch):
        from pensieve.cli import main
        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})
        monkeypatch.chdir(repo)
        result = main(["scan"])
        assert result == 0

    def test_scan_with_output_dir(self, tmp_path):
        from pensieve.cli import main
        repo = _make_repo(tmp_path, {"main.py": "x = 1\n"})
        output = tmp_path / "custom_output"
        result = main(["scan", str(repo), "--output-dir", str(output)])
        assert result == 0
        assert (output / "structure.json").exists()
