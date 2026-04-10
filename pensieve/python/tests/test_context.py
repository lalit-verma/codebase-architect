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
    FileSelection,
    RepoProfile,
    SubsystemDoc,
    SubsystemMap,
    SubsystemProposal,
    SynthesisResult,
    build_subsystem_brief,
    generate_subsystem_doc,
    profile_directories,
    format_profiles_for_llm,
    propose_subsystems,
    format_subsystem_map,
    save_subsystem_doc,
    generate_route_index,
    save_synthesis,
    synthesize_docs,
    select_files_for_subsystem,
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


# ---------------------------------------------------------------------------
# B14c: Subsystem brief + file selection
# ---------------------------------------------------------------------------


class TestBuildSubsystemBrief:

    def test_brief_contains_file_names(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("foo")]),
            _file("src/b.py", symbols=[_sym("bar")]),
        ])
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        brief = build_subsystem_brief(subsystem, sp)
        assert "src/a.py" in brief
        assert "src/b.py" in brief

    def test_brief_contains_symbols(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("my_function")]),
        ])
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        brief = build_subsystem_brief(subsystem, sp)
        assert "my_function" in brief

    def test_brief_empty_directories(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("other/a.py"),
        ])
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        brief = build_subsystem_brief(subsystem, sp)
        assert "No files found" in brief

    def test_brief_matches_subdirectories(self, tmp_path):
        """Files in subdirectories of a listed directory should be included."""
        sp = _write_structure(tmp_path, [
            _file("retrieval/web/google.py", symbols=[_sym("search_google")]),
            _file("retrieval/web/bing.py", symbols=[_sym("search_bing")]),
            _file("retrieval/vector/chroma.py", symbols=[_sym("ChromaDB")]),
        ])
        subsystem = SubsystemProposal(
            name="Retrieval",
            directories=["retrieval/web", "retrieval/vector"],
            role="RAG", rationale="test",
        )
        brief = build_subsystem_brief(subsystem, sp)
        assert "search_google" in brief
        assert "ChromaDB" in brief

    def test_brief_includes_subsystem_name_and_role(self, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/a.py"),
        ])
        subsystem = SubsystemProposal(
            name="API Layer", directories=["src"],
            role="HTTP request handling", rationale="test",
        )
        brief = build_subsystem_brief(subsystem, sp)
        assert "API Layer" in brief
        assert "HTTP request handling" in brief


class TestSelectFilesForSubsystem:

    def _make_llm_file_response(self, files=None):
        if files is None:
            files = [
                {"file_path": "src/main.py", "reason": "Entry point"},
                {"file_path": "src/config.py", "reason": "Configuration hub"},
            ]
        return json.dumps({
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {"files": files},
        })

    @mock.patch("pensieve.context.subprocess.run")
    def test_successful_selection(self, mock_run, tmp_path):
        sp = _write_structure(tmp_path, [
            _file("src/main.py", symbols=[_sym("main")]),
            _file("src/config.py", symbols=[_sym("Config")]),
        ])
        mock_run.return_value = mock.MagicMock(
            stdout=self._make_llm_file_response(),
            stderr="", returncode=0,
        )
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        result = select_files_for_subsystem(subsystem, sp)

        assert result.error is None
        assert len(result.files) == 2
        assert result.files[0]["file_path"] == "src/main.py"
        assert result.files[1]["reason"] == "Configuration hub"

    @mock.patch("pensieve.context.subprocess.run")
    def test_timeout_returns_error(self, mock_run, tmp_path):
        import subprocess as sp_mod
        sp = _write_structure(tmp_path, [_file("src/a.py")])
        mock_run.side_effect = sp_mod.TimeoutExpired(cmd=["claude"], timeout=120)

        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        result = select_files_for_subsystem(subsystem, sp)

        assert result.error is not None
        assert "timed out" in result.error.lower()

    @mock.patch("pensieve.context.subprocess.run")
    def test_nonzero_returncode(self, mock_run, tmp_path):
        sp = _write_structure(tmp_path, [_file("src/a.py")])
        mock_run.return_value = mock.MagicMock(
            stdout=self._make_llm_file_response(),
            stderr="auth error", returncode=1,
        )
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        result = select_files_for_subsystem(subsystem, sp)

        assert result.error is not None
        assert "exited with code 1" in result.error

    @mock.patch("pensieve.context.subprocess.run")
    def test_malformed_entry_skipped(self, mock_run, tmp_path):
        sp = _write_structure(tmp_path, [_file("src/a.py")])
        resp = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "",
            "structured_output": {
                "files": [
                    {"file_path": "src/good.py", "reason": "good"},
                    None,
                    {"file_path": "src/also_good.py", "reason": "also good"},
                ],
            },
        })
        mock_run.return_value = mock.MagicMock(
            stdout=resp, stderr="", returncode=0,
        )
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        result = select_files_for_subsystem(subsystem, sp)

        assert result.error is None
        assert len(result.files) == 2

    @mock.patch("pensieve.context.subprocess.run")
    def test_uses_json_schema(self, mock_run, tmp_path):
        sp = _write_structure(tmp_path, [_file("src/a.py")])
        mock_run.return_value = mock.MagicMock(
            stdout=self._make_llm_file_response(),
            stderr="", returncode=0,
        )
        subsystem = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="test",
        )
        select_files_for_subsystem(subsystem, sp)
        cmd = mock_run.call_args[0][0]
        assert "--json-schema" in cmd


# ---------------------------------------------------------------------------
# B14d: Deep-dive documentation generation
# ---------------------------------------------------------------------------


class TestGenerateSubsystemDoc:

    def _make_repo_with_files(self, tmp_path):
        """Create a repo with structure.json and actual source files."""
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()

        src = repo / "src" / "handlers"
        src.mkdir(parents=True)
        (src / "users.py").write_text(
            "def get_users():\n    return []\n\n"
            "def create_user(name):\n    pass\n"
        )
        (src / "posts.py").write_text(
            "def get_posts():\n    return []\n"
        )

        sp = ad / "structure.json"
        sp.write_text(json.dumps({
            "repo_root": str(repo),
            "files": [
                _file("src/handlers/users.py", symbols=[_sym("get_users"), _sym("create_user")]),
                _file("src/handlers/posts.py", symbols=[_sym("get_posts")]),
            ],
            "errors": [],
            "extractor_version": "test",
        }))

        return repo, sp

    @mock.patch("pensieve.context.subprocess.run")
    def test_successful_generation(self, mock_run, tmp_path):
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="# Handlers\n\n## Why This Subsystem Exists\nHandles HTTP requests.\n",
            stderr="",
            returncode=0,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[
            {"file_path": "src/handlers/users.py", "reason": "main handler"},
        ])

        doc = generate_subsystem_doc(subsystem, sp, selection, repo)

        assert doc.error is None
        assert "Handlers" in doc.markdown
        assert doc.subsystem_name == "Handlers"
        assert "src/handlers/users.py" in doc.files_read

    @mock.patch("pensieve.context.subprocess.run")
    def test_prompt_contains_structural_brief(self, mock_run, tmp_path):
        """The prompt should include the structural brief with all file symbols."""
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="doc content", stderr="", returncode=0,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[
            {"file_path": "src/handlers/users.py", "reason": "main"},
        ])

        generate_subsystem_doc(subsystem, sp, selection, repo)

        # Check the prompt passed to claude
        cmd = mock_run.call_args[0][0]
        prompt = cmd[-1]  # instruction is last arg
        assert "get_users" in prompt  # from structural brief
        assert "def get_users" in prompt  # from file content

    @mock.patch("pensieve.context.subprocess.run")
    def test_prompt_contains_file_content(self, mock_run, tmp_path):
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="doc content", stderr="", returncode=0,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[
            {"file_path": "src/handlers/users.py", "reason": "main"},
        ])

        generate_subsystem_doc(subsystem, sp, selection, repo)

        cmd = mock_run.call_args[0][0]
        prompt = cmd[-1]
        # Full file content should be in the prompt
        assert "return []" in prompt

    @mock.patch("pensieve.context.subprocess.run")
    def test_uses_text_output_not_json(self, mock_run, tmp_path):
        """Deep-dive should use --output-format text, not json."""
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="doc content", stderr="", returncode=0,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[])

        generate_subsystem_doc(subsystem, sp, selection, repo)

        cmd = mock_run.call_args[0][0]
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "text"

    @mock.patch("pensieve.context.subprocess.run")
    def test_timeout_returns_error(self, mock_run, tmp_path):
        import subprocess as sp_mod
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.side_effect = sp_mod.TimeoutExpired(cmd=["claude"], timeout=300)

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[])

        doc = generate_subsystem_doc(subsystem, sp, selection, repo)

        assert doc.error is not None
        assert "timed out" in doc.error.lower()

    @mock.patch("pensieve.context.subprocess.run")
    def test_nonzero_returncode(self, mock_run, tmp_path):
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="", stderr="auth error", returncode=1,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[])

        doc = generate_subsystem_doc(subsystem, sp, selection, repo)

        assert doc.error is not None
        assert "exited with code 1" in doc.error

    @mock.patch("pensieve.context.subprocess.run")
    def test_missing_file_handled(self, mock_run, tmp_path):
        """Selected file that doesn't exist should not crash."""
        repo, sp = self._make_repo_with_files(tmp_path)
        mock_run.return_value = mock.MagicMock(
            stdout="doc content", stderr="", returncode=0,
        )

        subsystem = SubsystemProposal(
            name="Handlers", directories=["src/handlers"],
            role="HTTP handlers", rationale="test",
        )
        selection = FileSelection(files=[
            {"file_path": "src/handlers/nonexistent.py", "reason": "test"},
            {"file_path": "src/handlers/users.py", "reason": "exists"},
        ])

        doc = generate_subsystem_doc(subsystem, sp, selection, repo)

        assert doc.error is None
        assert "src/handlers/users.py" in doc.files_read
        assert "src/handlers/nonexistent.py" not in doc.files_read


class TestSaveSubsystemDoc:

    def test_saves_to_subsystems_dir(self, tmp_path):
        doc = SubsystemDoc(
            subsystem_name="API Routers",
            markdown="# API Routers\n\nContent here.\n",
            files_read=["src/routers/users.py"],
        )
        path = save_subsystem_doc(doc, tmp_path)

        assert path.exists()
        assert "subsystems" in str(path)
        assert path.name == "api_routers.md"
        assert "Content here" in path.read_text()

    def test_creates_subsystems_dir(self, tmp_path):
        doc = SubsystemDoc(
            subsystem_name="Core",
            markdown="# Core\n",
            files_read=[],
        )
        output_dir = tmp_path / "deep" / "nested"
        path = save_subsystem_doc(doc, output_dir)
        assert path.exists()

    def test_sanitizes_name(self, tmp_path):
        doc = SubsystemDoc(
            subsystem_name="Shared Utilities & Access Control",
            markdown="# Content\n",
            files_read=[],
        )
        path = save_subsystem_doc(doc, tmp_path)
        assert "/" not in path.name
        assert "&" not in path.name
        assert " " not in path.name


# ---------------------------------------------------------------------------
# B14e: Synthesis
# ---------------------------------------------------------------------------


def _make_subsystem_docs():
    """Create mock SubsystemDoc objects for synthesis tests."""
    return [
        SubsystemDoc(
            subsystem_name="API Routers",
            markdown=(
                "# API Routers\n\n"
                "## Why This Subsystem Exists\n"
                "Handles all HTTP endpoints.\n\n"
                "## Modification Guide\n"
                "To add a new router: create in routers/, register in main.py.\n"
                "Best template: routers/users.py\n\n"
                "## Detected Patterns\n"
                "Router pattern — example: routers/users.py, 5 files\n"
            ),
            files_read=["src/routers/users.py"],
        ),
        SubsystemDoc(
            subsystem_name="Data Models",
            markdown=(
                "# Data Models\n\n"
                "## Why This Subsystem Exists\n"
                "SQLAlchemy ORM models.\n\n"
                "## Modification Guide\n"
                "To add a new model: create in models/, inherit Base.\n\n"
                "## Detected Patterns\n"
                "Model pattern — example: models/user.py, 8 files\n"
            ),
            files_read=["src/models/user.py"],
        ),
    ]


def _make_simple_profile():
    return RepoProfile(
        repo_root="/tmp/repo",
        total_files=20,
        total_edges=50,
        directories=[
            DirectoryProfile(path="src/routers", file_count=5),
            DirectoryProfile(path="src/models", file_count=8),
        ],
    )


class TestSynthesizeDocs:

    @mock.patch("pensieve.context._call_llm_text")
    def test_produces_three_artifacts(self, mock_call):
        mock_call.side_effect = [
            ("# Patterns\n\nRouter pattern...", None),
            ("# Agent Context\n\nWhat this repo is...", None),
            ("# Nano\n\nQuick context...", None),
        ]

        result = synthesize_docs(_make_subsystem_docs(), _make_simple_profile())

        assert result.patterns_md != ""
        assert result.agent_context_md != ""
        assert result.agent_context_nano_md != ""
        assert len(result.errors) == 0
        assert mock_call.call_count == 3

    @mock.patch("pensieve.context._call_llm_text")
    def test_one_failure_does_not_block_others(self, mock_call):
        mock_call.side_effect = [
            ("", "patterns.md timed out"),  # patterns fails
            ("# Agent Context\n\nContent.", None),  # context succeeds
            ("# Nano\n\nContent.", None),  # nano succeeds
        ]

        result = synthesize_docs(_make_subsystem_docs(), _make_simple_profile())

        assert result.patterns_md == ""
        assert result.agent_context_md != ""
        assert result.agent_context_nano_md != ""
        assert len(result.errors) == 1
        assert "patterns.md" in result.errors[0]

    @mock.patch("pensieve.context._call_llm_text")
    def test_passes_subsystem_summaries(self, mock_call):
        mock_call.return_value = ("output", None)

        synthesize_docs(_make_subsystem_docs(), _make_simple_profile())

        # All three calls should include subsystem content
        for call in mock_call.call_args_list:
            user_prompt = call[1].get("user_prompt") or call[0][1]
            assert "API Routers" in user_prompt
            assert "Data Models" in user_prompt

    @mock.patch("pensieve.context._call_llm_text")
    def test_passes_directory_profile(self, mock_call):
        mock_call.return_value = ("output", None)

        synthesize_docs(_make_subsystem_docs(), _make_simple_profile())

        for call in mock_call.call_args_list:
            user_prompt = call[1].get("user_prompt") or call[0][1]
            assert "src/routers" in user_prompt


class TestSaveSynthesis:

    def test_saves_all_three_files(self, tmp_path):
        result = SynthesisResult(
            patterns_md="# Patterns\nContent.\n",
            agent_context_md="# Agent Context\nContent.\n",
            agent_context_nano_md="# Nano\nContent.\n",
        )
        paths = save_synthesis(result, tmp_path)

        assert len(paths) == 3
        names = {p.name for p in paths}
        assert "patterns.md" in names
        assert "agent-context.md" in names
        assert "agent-context-nano.md" in names

        for p in paths:
            assert p.exists()
            assert "Content" in p.read_text()

    def test_skips_empty_artifacts(self, tmp_path):
        result = SynthesisResult(
            patterns_md="# Patterns\n",
            agent_context_md="",  # empty — should be skipped
            agent_context_nano_md="# Nano\n",
        )
        paths = save_synthesis(result, tmp_path)

        assert len(paths) == 2
        names = {p.name for p in paths}
        assert "agent-context.md" not in names

    def test_creates_output_dir(self, tmp_path):
        result = SynthesisResult(
            patterns_md="# P\n",
            agent_context_md="# A\n",
            agent_context_nano_md="# N\n",
        )
        nested = tmp_path / "deep" / "nested"
        paths = save_synthesis(result, nested)
        assert len(paths) == 3
        assert nested.exists()


# ---------------------------------------------------------------------------
# Analyze parallelism equivalence tests
# ---------------------------------------------------------------------------


class TestAnalyzeParallelEquivalence:
    """Verify that parallel stage 3/4 produce same results as sequential."""

    def _make_subsystems(self):
        return [
            SubsystemProposal(
                name="Routers", directories=["src/routers"],
                role="HTTP handlers", rationale="test",
            ),
            SubsystemProposal(
                name="Models", directories=["src/models"],
                role="Data layer", rationale="test",
            ),
            SubsystemProposal(
                name="Utils", directories=["src/utils"],
                role="Shared utilities", rationale="test",
            ),
        ]

    @mock.patch("pensieve.context.subprocess.run")
    def test_stage3_sequential_and_parallel_equivalent(self, mock_run, tmp_path):
        """File selection results must be identical regardless of parallelism."""
        sp = _write_structure(tmp_path, [
            _file("src/routers/a.py", symbols=[_sym("handler")]),
            _file("src/models/b.py", symbols=[_sym("Model")]),
            _file("src/utils/c.py", symbols=[_sym("helper")]),
        ])

        # Mock returns a deterministic response based on subsystem name
        def _mock_select(cmd, **kwargs):
            prompt = cmd[-1]
            if "Routers" in prompt:
                files = [{"file_path": "src/routers/a.py", "reason": "handler"}]
            elif "Models" in prompt:
                files = [{"file_path": "src/models/b.py", "reason": "model"}]
            else:
                files = [{"file_path": "src/utils/c.py", "reason": "util"}]
            return mock.MagicMock(
                stdout=json.dumps({
                    "type": "result", "is_error": False, "result": "",
                    "structured_output": {"files": files},
                }),
                stderr="", returncode=0,
            )
        mock_run.side_effect = _mock_select

        subsystems = self._make_subsystems()

        # Sequential
        seq_results = {}
        for sub in subsystems:
            sel = select_files_for_subsystem(sub, sp)
            seq_results[sub.name] = sel

        # Reset mock call count
        mock_run.reset_mock()
        mock_run.side_effect = _mock_select

        # Parallel (via ThreadPoolExecutor directly)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        par_results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(select_files_for_subsystem, sub, sp): sub.name
                for sub in subsystems
            }
            for future in as_completed(futures):
                name = futures[future]
                par_results[name] = future.result()

        # Compare
        for name in seq_results:
            seq = seq_results[name]
            par = par_results[name]
            assert seq.error == par.error, f"{name}: error mismatch"
            assert len(seq.files) == len(par.files), f"{name}: file count mismatch"
            for sf, pf in zip(seq.files, par.files):
                assert sf["file_path"] == pf["file_path"], f"{name}: file path mismatch"

    @mock.patch("pensieve.context.subprocess.run")
    def test_stage4_output_ordering_stable(self, mock_run, tmp_path):
        """Doc generation must produce results in subsystem order regardless
        of completion order."""
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        for name in ("a.py", "b.py", "c.py"):
            d = repo / "src" / name.replace(".py", "")
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(f"def {name[0]}(): pass\n")

        sp = ad / "structure.json"
        sp.write_text(json.dumps({
            "repo_root": str(repo),
            "files": [
                _file(f"src/{n.replace('.py','')}/{n}", symbols=[_sym(n[0])])
                for n in ("a.py", "b.py", "c.py")
            ],
            "errors": [], "extractor_version": "test",
        }))

        import time as time_mod
        call_count = [0]

        def _mock_doc(cmd, **kwargs):
            call_count[0] += 1
            prompt = cmd[-1]
            # Extract subsystem name from prompt
            for name in ("First", "Second", "Third"):
                if name in prompt:
                    return mock.MagicMock(
                        stdout=f"# {name} doc\n", stderr="", returncode=0,
                    )
            return mock.MagicMock(stdout="# Unknown\n", stderr="", returncode=0)

        mock_run.side_effect = _mock_doc

        subsystems = [
            SubsystemProposal(name="First", directories=["src/a"], role="a", rationale=""),
            SubsystemProposal(name="Second", directories=["src/b"], role="b", rationale=""),
            SubsystemProposal(name="Third", directories=["src/c"], role="c", rationale=""),
        ]

        from concurrent.futures import ThreadPoolExecutor, as_completed
        indexed = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(
                    generate_subsystem_doc,
                    sub, sp, FileSelection(files=[]), repo,
                ): i
                for i, sub in enumerate(subsystems)
            }
            for future in as_completed(futures):
                idx = futures[future]
                doc = future.result()
                indexed.append((idx, doc))

        indexed.sort(key=lambda x: x[0])
        names = [doc.subsystem_name for _, doc in indexed]
        assert names == ["First", "Second", "Third"]

    @mock.patch("pensieve.context.subprocess.run")
    def test_one_subsystem_failure_does_not_abort_others(self, mock_run, tmp_path):
        """A failing subsystem in parallel mode should not stop others."""
        sp = _write_structure(tmp_path, [
            _file("src/good/a.py", symbols=[_sym("a")]),
            _file("src/bad/b.py", symbols=[_sym("b")]),
            _file("src/also_good/c.py", symbols=[_sym("c")]),
        ])

        call_count = [0]

        def _mock_with_failure(cmd, **kwargs):
            call_count[0] += 1
            prompt = cmd[-1]
            if "Bad" in prompt:
                raise RuntimeError("Deliberate failure")
            return mock.MagicMock(
                stdout=json.dumps({
                    "type": "result", "is_error": False, "result": "",
                    "structured_output": {"files": [{"file_path": "x.py", "reason": "ok"}]},
                }),
                stderr="", returncode=0,
            )

        mock_run.side_effect = _mock_with_failure

        subsystems = [
            SubsystemProposal(name="Good", directories=["src/good"], role="a", rationale=""),
            SubsystemProposal(name="Bad", directories=["src/bad"], role="b", rationale=""),
            SubsystemProposal(name="AlsoGood", directories=["src/also_good"], role="c", rationale=""),
        ]

        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(select_files_for_subsystem, sub, sp): sub.name
                for sub in subsystems
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = FileSelection(files=[], error=str(exc))

        assert results["Good"].error is None
        assert results["AlsoGood"].error is None
        # Bad should have an error (either from the mock or caught)
        assert results["Bad"].error is not None or len(results["Bad"].files) == 0


# ---------------------------------------------------------------------------
# Bx1: Route index
# ---------------------------------------------------------------------------


class TestRouteIndex:

    def test_generates_route_index(self, tmp_path):
        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(
                    name="API Routers",
                    directories=["src/routers"],
                    role="HTTP handlers",
                    rationale="test",
                ),
                SubsystemProposal(
                    name="Data Models",
                    directories=["src/models", "src/db"],
                    role="ORM layer",
                    rationale="test",
                ),
            ],
            excluded=[],
        )
        path = generate_route_index(smap, tmp_path)

        assert path.exists()
        assert path.name == "route-index.json"

        data = json.loads(path.read_text())
        assert data["version"] == 1
        assert len(data["routes"]) == 3  # 1 for routers + 2 for models
        assert "fallback_hint" in data

    def test_route_entries_have_required_fields(self, tmp_path):
        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(
                    name="Core", directories=["src"],
                    role="core logic", rationale="test",
                ),
            ],
            excluded=[],
        )
        generate_route_index(smap, tmp_path)
        data = json.loads((tmp_path / "route-index.json").read_text())

        route = data["routes"][0]
        assert route["match_type"] == "directory_prefix"
        assert route["pattern"] == "src"
        assert route["subsystem"] == "Core"
        assert route["doc_path"].startswith("agent-docs/subsystems/")
        assert route["hint"] != ""

    def test_directory_trailing_slash_stripped(self, tmp_path):
        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(
                    name="Utils", directories=["src/utils/"],
                    role="shared", rationale="test",
                ),
            ],
            excluded=[],
        )
        generate_route_index(smap, tmp_path)
        data = json.loads((tmp_path / "route-index.json").read_text())

        assert data["routes"][0]["pattern"] == "src/utils"

    def test_empty_subsystem_map(self, tmp_path):
        smap = SubsystemMap(subsystems=[], excluded=[])
        path = generate_route_index(smap, tmp_path)
        data = json.loads(path.read_text())
        assert data["routes"] == []
        assert "fallback_hint" in data
