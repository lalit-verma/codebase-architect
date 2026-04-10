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
    SubsystemMap,
    SubsystemProposal,
    profile_directories,
    format_profiles_for_llm,
    propose_subsystems,
    format_subsystem_map,
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


def _sym(name: str):
    return {"name": name, "kind": "function"}


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


class TestLLMFormat:

    def test_format_contains_directory_names(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        text = format_profiles_for_llm(profile)
        assert "src/" in text
        assert "lib/" in text

    def test_format_contains_edge_stats(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
            _file("src/b.py"),
            _file("lib/c.py"),
            _file("lib/d.py"),
        ])
        gp = _write_graph(tmp_path, [
            _edge("src/a.py", "lib/c.py"),
        ])
        profile = profile_directories(sp, gp, min_files=2)

        text = format_profiles_for_llm(profile)
        assert "Edge density" in text
        assert "internal" in text

    def test_format_flags_auto_generated(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("migrations/001.py"),
            _file("migrations/002.py"),
        ])
        gp = _write_graph(tmp_path, [])
        profile = profile_directories(sp, gp, min_files=2)

        text = format_profiles_for_llm(profile)
        assert "AUTO-GENERATED" in text


# ---------------------------------------------------------------------------
# RepoProfile serialization
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


class TestProposeSubsystems:

    @mock.patch("pensieve.context.subprocess.run")
    def test_successful_proposal(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout=_make_llm_response(),
            stderr="",
            returncode=0,
        )
        result = propose_subsystems(_make_profile())

        assert result.error is None
        assert len(result.subsystems) == 2
        assert result.subsystems[0].name == "API Layer"
        assert result.subsystems[0].directories == ["routers"]
        assert result.subsystems[1].name == "Data Models"
        assert len(result.excluded) == 1

    @mock.patch("pensieve.context.subprocess.run")
    def test_proposal_passes_model(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout=_make_llm_response(),
            stderr="",
            returncode=0,
        )
        propose_subsystems(_make_profile(), model="opus")
        cmd = mock_run.call_args[0][0]
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus"

    @mock.patch("pensieve.context.subprocess.run")
    def test_proposal_uses_json_schema(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout=_make_llm_response(),
            stderr="",
            returncode=0,
        )
        propose_subsystems(_make_profile())
        cmd = mock_run.call_args[0][0]
        assert "--json-schema" in cmd

    @mock.patch("pensieve.context.subprocess.run")
    def test_timeout_returns_error(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd=["claude"], timeout=120)
        result = propose_subsystems(_make_profile())

        assert result.error is not None
        assert "timed out" in result.error.lower()
        assert len(result.subsystems) == 0

    @mock.patch("pensieve.context.subprocess.run")
    def test_nonzero_returncode(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout=_make_llm_response(),
            stderr="auth error",
            returncode=1,
        )
        result = propose_subsystems(_make_profile())

        assert result.error is not None
        assert "exited with code 1" in result.error

    @mock.patch("pensieve.context.subprocess.run")
    def test_malformed_subsystem_entry_skipped(self, mock_run):
        """A malformed entry in subsystems array should be skipped,
        not crash the whole proposal."""
        resp = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {
                "subsystems": [
                    {"name": "Good", "directories": ["src"], "role": "ok", "rationale": "ok"},
                    None,  # malformed
                    {"name": "Also Good", "directories": ["lib"], "role": "ok", "rationale": "ok"},
                ],
                "excluded": [],
            },
        })
        mock_run.return_value = mock.MagicMock(
            stdout=resp, stderr="", returncode=0,
        )
        result = propose_subsystems(_make_profile())

        assert result.error is None
        assert len(result.subsystems) == 2
        assert result.subsystems[0].name == "Good"
        assert result.subsystems[1].name == "Also Good"

    @mock.patch("pensieve.context.subprocess.run")
    def test_empty_structured_output(self, mock_run):
        resp = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {},
        })
        mock_run.return_value = mock.MagicMock(
            stdout=resp, stderr="", returncode=0,
        )
        result = propose_subsystems(_make_profile())

        assert result.error is None
        assert len(result.subsystems) == 0


class TestFormatSubsystemMap:

    def test_format_lists_subsystems(self):
        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(
                    name="API Layer",
                    directories=["routers"],
                    role="HTTP handling",
                    rationale="Shared responsibility",
                ),
            ],
            excluded=[{"directory": "migrations", "reason": "Auto-generated"}],
        )
        text = format_subsystem_map(smap)
        assert "API Layer" in text
        assert "routers" in text
        assert "migrations" in text
        assert "Auto-generated" in text

    def test_format_error(self):
        smap = SubsystemMap(
            subsystems=[], excluded=[],
            error="LLM timed out",
        )
        text = format_subsystem_map(smap)
        assert "Error" in text
        assert "timed out" in text


class TestSubsystemDataclasses:

    def test_proposal_fields(self):
        p = SubsystemProposal(
            name="Auth",
            directories=["auth/", "middleware/auth/"],
            role="Authentication and authorization",
            rationale="Tightly coupled",
        )
        assert p.name == "Auth"
        assert len(p.directories) == 2

    def test_map_error_default(self):
        m = SubsystemMap(subsystems=[], excluded=[])
        assert m.error is None
