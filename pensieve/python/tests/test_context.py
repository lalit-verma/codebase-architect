"""Tests for the directory profiler (B14a).

Covers:
  - Basic profiling: file counts, languages, symbols
  - Edge analysis: internal density, outgoing/incoming targets
  - Directory collapsing: single-child collapse, multi-child expansion
  - Auto-generated and test directory detection
  - min_files filtering
  - LLM format output
  - Real repo validation (socrates calibration repo)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unittest import mock

from pensieve.context import (
    DirectoryProfile,
    RepoProfile,
    profile_directories,
    format_structural_profiles,
    format_subsystem_brief,
    validate_structural_profile,
    validate_subsystem_brief,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_structure(tmp_path: Path, files: list[dict]) -> Path:
    path = tmp_path / "structure.json"
    path.write_text(json.dumps({
        "repo_root": str(tmp_path),
        "files": files,
        "errors": [],
        "extractor_version": "test",
    }))
    return path


def _write_graph(tmp_path: Path, edges: list[dict]) -> Path:
    path = tmp_path / "graph.json"
    nodes = []  # not needed for profiling
    path.write_text(json.dumps({
        "nodes": nodes,
        "edges": edges,
        "external_imports": [],
    }))
    return path


def _file(path: str, language: str = "python", symbols: list | None = None):
    return {
        "file_path": path,
        "language": language,
        "symbols": symbols or [],
        "imports": [],
        "exports": [],
        "call_edges": [],
        "comments": [],
    }


def _edge(source: str, target: str, kind: str = "imports", detail: str = ""):
    return {
        "source": source,
        "target": target,
        "kind": kind,
        "detail": detail,
        "line": 1,
        "confidence": 1.0,
    }


def _sym(name: str, kind: str = "function"):
    return {"name": name, "kind": kind, "signature": f"def {name}():" if kind == "function" else f"class {name}:", "visibility": "public", "parent": None, "line_start": 1, "line_end": 5}


# ---------------------------------------------------------------------------
# Basic profiling
# ---------------------------------------------------------------------------


class TestBasicProfiling:

    def test_file_count_per_directory(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
            _file("lib/e.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        dirs = {d.path: d for d in profile.directories}
        assert "src" in dirs
        assert "lib" in dirs
        assert dirs["src"].file_count == 2
        assert dirs["lib"].file_count == 3

    def test_language_breakdown(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", "python"),
            _file("src/b.ts", "typescript"),
            _file("src/c.py", "python"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        d = profile.directories[0]
        assert d.languages == {"python": 2, "typescript": 1}

    def test_symbol_count(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo"), _sym("bar")]),
            _file("src/b.py", symbols=[_sym("baz")]),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        assert profile.directories[0].symbol_count == 3

    def test_min_files_filter(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("big/a.py"),
            _file("big/b.py"),
            _file("big/c.py"),
            _file("tiny/x.py"),  # only 1 file
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        paths = [d.path for d in profile.directories]
        assert "big" in paths
        assert "tiny" not in paths


# ---------------------------------------------------------------------------
# Edge analysis
# ---------------------------------------------------------------------------


class TestEdgeAnalysis:

    def test_internal_edges(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/a.py", "src/b.py"),  # internal to src
            _edge("lib/c.py", "lib/d.py"),  # internal to lib
        ])
        profile = profile_directories(sp, gp, min_files=2)

        dirs = {d.path: d for d in profile.directories}
        assert dirs["src"].internal_edges == 1
        assert dirs["lib"].internal_edges == 1

    def test_outgoing_edges(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/a.py", "lib/c.py"),  # src → lib
            _edge("src/b.py", "lib/d.py"),  # src → lib
        ])
        profile = profile_directories(sp, gp, min_files=2)

        dirs = {d.path: d for d in profile.directories}
        assert dirs["src"].outgoing_edges == 2
        assert dirs["lib"].incoming_edges == 2
        assert dirs["src"].top_outgoing_targets[0] == ("lib", 2)

    def test_edge_density(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/a.py", "src/b.py"),  # 1 internal
            _edge("src/a.py", "lib/c.py"),  # 1 outgoing
        ])
        profile = profile_directories(sp, gp, min_files=2)

        dirs = {d.path: d for d in profile.directories}
        # density = 1 internal / (1 internal + 1 outgoing) = 0.5
        assert dirs["src"].edge_density == 0.5

    def test_zero_edges_density(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        assert profile.directories[0].edge_density == 0.0


# ---------------------------------------------------------------------------
# Directory collapsing
# ---------------------------------------------------------------------------


class TestDirectoryCollapsing:

    def test_single_child_collapse(self, tmp_path):
        """backend/ → backend/app/ should collapse to backend/app/."""
        sp = _write_structure(tmp_path, [
            _file("backend/app/a.py"),
            _file("backend/app/b.py"),
            _file("backend/app/c.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        paths = [d.path for d in profile.directories]
        assert "backend/app" in paths
        assert "backend" not in paths

    def test_multi_child_expansion(self, tmp_path):
        """src/ with routers/ and models/ should profile at child level."""
        sp = _write_structure(tmp_path, [
            _file("src/routers/a.py"),
            _file("src/routers/b.py"),
            _file("src/models/c.py"),
            _file("src/models/d.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        paths = [d.path for d in profile.directories]
        assert "src/routers" in paths
        assert "src/models" in paths


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------


class TestFlags:

    def test_auto_generated_detection(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("migrations/001.py"),
            _file("migrations/002.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        assert profile.directories[0].is_auto_generated is True

    def test_test_directory_detection(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("tests/test_a.py"),
            _file("tests/test_b.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        assert profile.directories[0].is_test is True

    def test_normal_directory_no_flags(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("routers/a.py"),
            _file("routers/b.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        assert profile.directories[0].is_test is False
        assert profile.directories[0].is_auto_generated is False


# ---------------------------------------------------------------------------
# LLM format
# ---------------------------------------------------------------------------


class TestSerialization:

    def test_to_dict_roundtrip(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        d = profile.to_dict()
        assert d["total_files"] == 2
        assert len(d["directories"]) == 1
        assert d["directories"][0]["path"] == "src"

    def test_to_json(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        j = profile.to_json()
        data = json.loads(j)
        assert data["total_files"] == 2


# ---------------------------------------------------------------------------
# B14b: Subsystem proposal
# ---------------------------------------------------------------------------


def _make_llm_response(subsystems=None, excluded=None, is_error=False, error_msg=""):
    """Build a mock Claude Code JSON response with structured_output."""
    if subsystems is None:
        subsystems = [
            {
                "name": "API Layer",
                "directories": ["routers"],
                "role": "HTTP request handling",
                "rationale": "All router files share the API responsibility",
            },
            {
                "name": "Data Models",
                "directories": ["models"],
                "role": "Database models and schemas",
                "rationale": "ORM models with shared DB access patterns",
            },
        ]
    if excluded is None:
        excluded = [
            {"directory": "migrations", "reason": "Auto-generated"},
        ]

    return json.dumps({
        "type": "result",
        "is_error": is_error,
        "result": error_msg,
        "total_cost_usd": 0.02,
        "duration_ms": 3000,
        "structured_output": {
            "subsystems": subsystems,
            "excluded": excluded,
        },
    })


def _make_profile():
    """Create a minimal RepoProfile for proposal tests."""
    return RepoProfile(
        repo_root="/tmp/repo",
        total_files=20,
        total_edges=50,
        directories=[
            DirectoryProfile(path="routers", file_count=8, symbol_count=40),
            DirectoryProfile(path="models", file_count=6, symbol_count=30),
            DirectoryProfile(path="migrations", file_count=10, is_auto_generated=True),
        ],
    )



# ---------------------------------------------------------------------------
# LLM-optimized structural profiles (XML format)
# ---------------------------------------------------------------------------


class TestStructuralProfiles:
    """Test the XML-tagged, layered structural profiles format."""

    def _make_repo(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/routers/users.py", symbols=[
                _sym("get_users"), _sym("create_user"),
            ]),
            _file("src/routers/posts.py", symbols=[_sym("get_posts")]),
            _file("src/models/user.py", symbols=[
                _sym("User", kind="class"), _sym("UserModel", kind="class"),
            ]),
            _file("src/models/base.py", symbols=[_sym("Base", kind="class")]),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/routers/users.py", "src/models/user.py"),
            _edge("src/routers/users.py", "src/models/base.py"),
            _edge("src/routers/posts.py", "src/models/user.py"),
            _edge("src/models/user.py", "src/models/base.py"),
        ])
        return sp, gp

    def test_contains_xml_tags(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_structural_profiles(sp, gp)
        assert "<repository" in output
        assert "</repository>" in output
        assert "<architecture>" in output
        assert "</architecture>" in output
        assert "<signatures>" in output
        assert "</signatures>" in output
        assert "<dependencies>" in output
        assert "</dependencies>" in output

    def test_architecture_shows_directories(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_structural_profiles(sp, gp)
        assert "src/routers/" in output
        assert "src/models/" in output

    def test_signatures_show_function_names(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_structural_profiles(sp, gp)
        # Should show actual signatures, not just counts
        assert "get_users" in output or "User" in output

    def test_dependencies_section_present(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_structural_profiles(sp, gp)
        # Dependencies section should exist even if thresholds aren't met
        assert "<dependencies>" in output
        assert "</dependencies>" in output

    def test_no_edge_density_percentages(self, tmp_path):
        """New format should NOT contain old-style density percentages."""
        sp, gp = self._make_repo(tmp_path)
        output = format_structural_profiles(sp, gp)
        assert "Edge density:" not in output


class TestSubsystemBrief:
    """Test the per-subsystem brief format."""

    def _make_repo(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/models/user.py", symbols=[
                _sym("User", kind="class"), _sym("get_user"),
            ]),
            _file("src/models/base.py", symbols=[
                _sym("Base", kind="class"), _sym("get_session"),
            ]),
            _file("src/routers/api.py", symbols=[_sym("router")]),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/models/user.py", "src/models/base.py"),
            _edge("src/routers/api.py", "src/models/user.py"),
        ])
        return sp, gp

    def test_contains_subsystem_brief_tags(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/models"], sp, gp)
        assert "<brief" in output
        assert "</brief>" in output

    def test_shows_all_file_signatures(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/models"], sp, gp)
        assert "User" in output
        assert "Base" in output
        assert "get_session" in output

    def test_shows_internal_dependencies(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/models"], sp, gp)
        assert "<internal_dependencies>" in output

    def test_shows_external_dependants(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/models"], sp, gp)
        # routers/api.py imports from models — should show as external dependant
        assert "src/routers" in output or "Depended on by" in output

    def test_empty_dirs_handled(self, tmp_path):
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["nonexistent"], sp, gp)
        assert "No files found" in output


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class TestValidateStructuralProfile:

    def test_valid_profile_passes(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo")]),
            _file("src/b.py", symbols=[_sym("bar")]),
        ])
        gp = _write_graph(tmp_path, [])
        output = format_structural_profiles(sp, gp)
        errors = validate_structural_profile(output)
        assert errors == []

    def test_missing_repository_tag(self):
        errors = validate_structural_profile("<architecture></architecture>")
        assert any("repository" in e.lower() for e in errors)

    def test_missing_required_section(self):
        errors = validate_structural_profile("<repository>\n</repository>")
        assert any("architecture" in e.lower() for e in errors)
        assert any("signatures" in e.lower() for e in errors)
        assert any("dependencies" in e.lower() for e in errors)

    def test_error_attribute_detected(self):
        errors = validate_structural_profile(
            '<repository error="Failed">\n</repository>'
        )
        assert any("error" in e.lower() for e in errors)


class TestValidateSubsystemBrief:

    def test_valid_brief_passes(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo")]),
        ])
        gp = _write_graph(tmp_path, [])
        output = format_subsystem_brief(["src"], sp, gp)
        errors = validate_subsystem_brief(output)
        assert errors == []

    def test_missing_brief_tag(self):
        errors = validate_subsystem_brief("some random text")
        assert any("brief" in e.lower() for e in errors)

    def test_error_attribute_detected(self):
        errors = validate_subsystem_brief(
            '<brief error="Failed">\n</brief>'
        )
        assert any("error" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Fault tolerance
# ---------------------------------------------------------------------------


class TestFaultTolerance:

    def test_profiles_with_missing_graph(self, tmp_path):
        """format_structural_profiles should work without graph.json."""
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo")]),
        ])
        # No graph.json exists
        fake_graph = tmp_path / "nonexistent_graph.json"
        output = format_structural_profiles(sp, fake_graph)
        assert "<repository" in output
        errors = validate_structural_profile(output)
        assert errors == []

    def test_profiles_with_empty_files(self, tmp_path):
        """Repo with zero files should not crash."""
        sp = _write_structure(tmp_path, [])
        gp = _write_graph(tmp_path, [])
        output = format_structural_profiles(sp, gp)
        assert "<repository" in output
        assert "no files found" in output.lower()

    def test_profiles_with_corrupt_structure(self, tmp_path):
        """Corrupt structure.json should return error, not crash."""
        sp = tmp_path / "structure.json"
        sp.write_text("NOT VALID JSON!!!")
        gp = _write_graph(tmp_path, [])
        output = format_structural_profiles(sp, gp)
        assert "error" in output.lower()

    def test_brief_with_missing_graph(self, tmp_path):
        """format_subsystem_brief should work without graph.json."""
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo")]),
        ])
        fake_graph = tmp_path / "nonexistent.json"
        output = format_subsystem_brief(["src"], sp, fake_graph)
        assert "<brief" in output

    def test_brief_with_corrupt_structure(self, tmp_path):
        """Corrupt structure.json in brief should return error, not crash."""
        sp = tmp_path / "structure.json"
        sp.write_text("{{{corrupt")
        gp = _write_graph(tmp_path, [])
        output = format_subsystem_brief(["src"], sp, gp)
        assert "error" in output.lower()


class TestBriefOutsideRepoRejection:
    """Paths outside the repo root must be rejected at the CLI level."""

    def test_outside_repo_path_rejected(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "structure.json").write_text('{"repo_root":"x","files":[],"errors":[]}')

        result = main(["brief", "../../etc/passwd", "--repo", str(repo)])
        assert result == 1
        captured = capsys.readouterr()
        assert "outside repo root" in captured.err

    def test_absolute_outside_path_rejected(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "structure.json").write_text('{"repo_root":"x","files":[],"errors":[]}')

        result = main(["brief", "/etc/passwd", "--repo", str(repo)])
        assert result == 1
        captured = capsys.readouterr()
        assert "outside repo root" in captured.err

    def test_inside_repo_path_accepted(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "structure.json").write_text(
            '{"repo_root":"x","files":[{"file_path":"src/a.py","language":"python",'
            '"symbols":[],"imports":[],"exports":[],"call_edges":[],"comments":[]}],"errors":[]}'
        )
        (ad / "graph.json").write_text('{"nodes":[],"edges":[],"external_imports":[]}')

        result = main(["brief", "src", "--repo", str(repo)])
        assert result == 0


# ---------------------------------------------------------------------------
# Mixed file/directory brief input
# ---------------------------------------------------------------------------


class TestMixedBriefInput:

    def _make_repo(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/routers/users.py", symbols=[_sym("get_users")]),
            _file("src/routers/posts.py", symbols=[_sym("get_posts")]),
            _file("src/models/user.py", symbols=[_sym("User", kind="class")]),
            _file("src/models/base.py", symbols=[_sym("Base", kind="class")]),
            _file("src/utils/auth.py", symbols=[_sym("verify")]),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/routers/users.py", "src/models/user.py"),
            _edge("src/routers/users.py", "src/utils/auth.py"),
            _edge("src/models/user.py", "src/models/base.py"),
        ])
        return sp, gp

    def test_single_file_path(self, tmp_path):
        """A single file path → brief includes only that file."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/models/user.py"], sp, gp)
        assert "User" in output
        assert "get_users" not in output  # routers file not included
        assert 'files="1"' in output

    def test_single_directory(self, tmp_path):
        """A single directory → existing behavior preserved."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(["src/routers"], sp, gp)
        assert "get_users" in output
        assert "get_posts" in output
        assert 'files="2"' in output

    def test_mixed_file_and_directory(self, tmp_path):
        """Mixed file + directory → union is correct."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(
            ["src/routers", "src/models/base.py"], sp, gp,
        )
        assert "get_users" in output   # from directory
        assert "get_posts" in output   # from directory
        assert "Base" in output        # from file
        assert "User" not in output    # user.py not requested
        assert 'files="3"' in output

    def test_duplicate_paths_deduped(self, tmp_path):
        """Duplicate paths → deduped to correct count."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(
            ["src/routers/users.py", "src/routers"], sp, gp,
        )
        # users.py is both a direct file and inside the directory
        assert 'files="2"' in output  # only 2 unique files in routers

    def test_deterministic_ordering(self, tmp_path):
        """Output should be deterministic regardless of input order."""
        sp, gp = self._make_repo(tmp_path)
        output1 = format_subsystem_brief(
            ["src/models/base.py", "src/routers/users.py"], sp, gp,
        )
        output2 = format_subsystem_brief(
            ["src/routers/users.py", "src/models/base.py"], sp, gp,
        )
        assert output1 == output2

    def test_nonexistent_path_warning(self, tmp_path):
        """Nonexistent path → warning in output, other paths still work."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(
            ["src/routers", "nonexistent/path.py"], sp, gp,
        )
        assert "WARNING" in output
        assert "nonexistent" in output
        assert "get_users" in output  # valid path still included

    def test_all_nonexistent_paths(self, tmp_path):
        """All paths nonexistent → no files found."""
        sp, gp = self._make_repo(tmp_path)
        output = format_subsystem_brief(
            ["nonexistent1", "nonexistent2.py"], sp, gp,
        )
        assert "No files found" in output

    def test_internal_vs_external_for_file_slice(self, tmp_path):
        """Internal edges = both endpoints in the slice."""
        sp, gp = self._make_repo(tmp_path)
        # Only include the two models files
        output = format_subsystem_brief(
            ["src/models/user.py", "src/models/base.py"], sp, gp,
        )
        assert "<internal_dependencies>" in output
        # user.py → base.py should be internal
        assert "Within subsystem" in output or "src/models/base.py" in output
        # routers → user.py should be external in
        assert "Depended on by" in output or "src/routers" in output
