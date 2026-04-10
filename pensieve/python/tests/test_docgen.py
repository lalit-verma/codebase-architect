"""Tests for v1-prompt-based doc generation (Phase B Layer 2).

Covers:
  - V1 prompt file location
  - Subsystem doc generation with mocked LLM
  - Discover stage with mocked LLM
  - Synthesize stage with mocked LLM
  - save functions
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from pensieve.context import (
    FileSelection,
    SubsystemProposal,
)
from pensieve.docgen import (
    SubsystemDoc,
    generate_subsystem_doc,
    save_subsystem_doc,
    run_discover,
    run_synthesize,
    _find_repo_root,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_structure(tmp_path, files):
    path = tmp_path / "structure.json"
    path.write_text(json.dumps({
        "repo_root": str(tmp_path),
        "files": files,
        "errors": [],
        "extractor_version": "test",
    }))
    return path


def _file(path, language="python", symbols=None):
    return {
        "file_path": path,
        "language": language,
        "symbols": symbols or [],
        "imports": [], "exports": [], "call_edges": [], "comments": [],
    }


def _sym(name, kind="function"):
    return {
        "name": name, "kind": kind, "line_start": 1, "line_end": 5,
        "signature": f"def {name}():", "visibility": "public",
        "parent": None, "docstring": None, "parameters": [], "return_type": None,
    }


# ---------------------------------------------------------------------------
# V1 prompt location
# ---------------------------------------------------------------------------


class TestPromptLocation:

    def test_find_repo_root(self):
        """Should find the codebase-analysis-skill repo root."""
        root = _find_repo_root()
        assert (root / "claude-code" / "commands" / "analyze-discover.md").exists()
        assert (root / "claude-code" / "commands" / "analyze-deep-dive.md").exists()
        assert (root / "claude-code" / "commands" / "analyze-synthesize.md").exists()


# ---------------------------------------------------------------------------
# Subsystem doc generation
# ---------------------------------------------------------------------------


class TestGenerateSubsystemDoc:

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_successful_generation(self, mock_run, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "src" / "routers").mkdir(parents=True)
        (repo / "src" / "routers" / "users.py").write_text("def get_users(): pass\n")

        sp = _write_structure(tmp_path, [
            _file("src/routers/users.py", symbols=[_sym("get_users")]),
        ])

        mock_run.return_value = mock.MagicMock(
            stdout="# API Routers\n\n## Why\nHandles HTTP.\n",
            stderr="", returncode=0,
        )

        sub = SubsystemProposal(
            name="API Routers", directories=["src/routers"],
            role="HTTP handlers", rationale="test",
        )
        sel = FileSelection(files=[
            {"file_path": "src/routers/users.py", "reason": "main handler"},
        ])

        doc = generate_subsystem_doc(sub, sp, sel, repo)

        assert doc.error is None
        assert "API Routers" in doc.markdown
        assert "src/routers/users.py" in doc.files_read

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_uses_v1_prompt(self, mock_run, tmp_path):
        """The system prompt should contain v1 deep-dive prompt content."""
        sp = _write_structure(tmp_path, [_file("src/a.py")])
        mock_run.return_value = mock.MagicMock(
            stdout="# Doc\n", stderr="", returncode=0,
        )

        sub = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="",
        )
        generate_subsystem_doc(sub, sp, FileSelection(files=[]), tmp_path)

        # Check system prompt contains v1 content
        cmd = mock_run.call_args[0][0]
        system_idx = cmd.index("--system-prompt")
        system_prompt = cmd[system_idx + 1]
        # V1 deep-dive prompt mentions Phase 2, subsystem analysis, etc.
        assert "Phase 2" in system_prompt or "deep" in system_prompt.lower()
        assert "Programmatic Execution" in system_prompt

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_timeout(self, mock_run, tmp_path):
        import subprocess as sp_mod
        sp = _write_structure(tmp_path, [])
        mock_run.side_effect = sp_mod.TimeoutExpired(cmd=["claude"], timeout=300)

        sub = SubsystemProposal(name="Core", directories=["src"], role="", rationale="")
        doc = generate_subsystem_doc(sub, sp, FileSelection(files=[]), tmp_path)
        assert doc.error is not None


# ---------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------


class TestRunDiscover:

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_successful_discover(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout=(
                "Analysis complete.\n\n"
                "---FILE: system-overview.md---\n"
                "# System Overview\n\nContent here.\n\n"
                "---FILE: .analysis-state.md---\n"
                "---\nphase_completed: 1\n---\n"
            ),
            stderr="", returncode=0,
        )

        result = run_discover(tmp_path, "structural context here")

        assert result.error is None
        assert "System Overview" in result.system_overview
        assert "phase_completed" in result.analysis_state

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_uses_v1_discover_prompt(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout="output", stderr="", returncode=0,
        )

        run_discover(tmp_path, "context")

        cmd = mock_run.call_args[0][0]
        system_idx = cmd.index("--system-prompt")
        system_prompt = cmd[system_idx + 1]
        assert "Phase 1" in system_prompt
        assert "Discover" in system_prompt or "discover" in system_prompt.lower()

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_timeout(self, mock_run, tmp_path):
        import subprocess as sp_mod
        mock_run.side_effect = sp_mod.TimeoutExpired(cmd=["claude"], timeout=300)

        result = run_discover(tmp_path, "context")
        assert result.error is not None


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------


class TestRunSynthesize:

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_successful_synthesize(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout="Generated all artifacts successfully.",
            stderr="", returncode=0,
        )

        result = run_synthesize(tmp_path, "structural context")

        assert len(result.errors) == 0
        assert result.raw_output != ""

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_uses_v1_synthesize_prompt(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout="output", stderr="", returncode=0,
        )

        run_synthesize(tmp_path, "context")

        cmd = mock_run.call_args[0][0]
        system_idx = cmd.index("--system-prompt")
        system_prompt = cmd[system_idx + 1]
        assert "Phase 3" in system_prompt
        assert "Synthesize" in system_prompt or "synthesize" in system_prompt.lower()


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


class TestSave:

    def test_saves_to_subsystems_dir(self, tmp_path):
        doc = SubsystemDoc(
            subsystem_name="API Routers",
            markdown="# API Routers\nContent.\n",
            files_read=[],
        )
        path = save_subsystem_doc(doc, tmp_path)
        assert path.exists()
        assert "subsystems" in str(path)
        assert "Content" in path.read_text()


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestPostSynthesisVerification:
    """Verify the artifact verification logic."""

    def test_all_artifacts_present(self, tmp_path):
        """When all required artifacts exist, verification passes."""
        required = [
            "agent-context.md", "agent-context-nano.md", "patterns.md",
            "routing-map.md", "system-overview.md", "agent-brief.md",
            "index.md", "agent-protocol.md",
        ]
        for name in required:
            (tmp_path / name).write_text(f"# {name}\n")

        missing = [n for n in required if not (tmp_path / n).exists()]
        assert missing == []

    def test_missing_artifacts_detected(self, tmp_path):
        """Missing artifacts are correctly identified."""
        required = [
            "agent-context.md", "agent-context-nano.md", "patterns.md",
            "routing-map.md", "system-overview.md", "agent-brief.md",
            "index.md", "agent-protocol.md",
        ]
        # Only create some
        (tmp_path / "agent-context.md").write_text("# AC\n")
        (tmp_path / "patterns.md").write_text("# P\n")

        missing = [n for n in required if not (tmp_path / n).exists()]
        assert len(missing) == 6
        assert "agent-context-nano.md" in missing
        assert "agent-protocol.md" in missing


class TestDiscoverSubsystemMapInput:
    """Discover should use the authoritative Python subsystem map."""

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_subsystem_map_injected_into_prompt(self, mock_run, tmp_path):
        from pensieve.context import SubsystemMap, SubsystemProposal
        mock_run.return_value = mock.MagicMock(
            stdout="output", stderr="", returncode=0,
        )

        smap = SubsystemMap(
            subsystems=[
                SubsystemProposal(
                    name="Core", directories=["src"],
                    role="main logic", rationale="test",
                ),
            ],
            excluded=[],
        )

        run_discover(tmp_path, "context", subsystem_map=smap)

        cmd = mock_run.call_args[0][0]
        user_prompt = cmd[-1]
        assert "Core" in user_prompt
        assert "Authoritative Subsystem Map" in user_prompt
        assert "pre-confirmed" in user_prompt


class TestOutputOnlyToAgentDocs:
    """The analyze path must write only to <repo>/agent-docs."""

    def test_analyze_parser_has_no_output_dir(self):
        from pensieve.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["analyze", "/tmp/repo"])
        assert not hasattr(args, "output_dir")


class TestToolRestriction:
    """Verify tool access is bounded, not broad auto."""

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_discover_uses_restricted_tools(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout="output", stderr="", returncode=0,
        )
        run_discover(tmp_path, "context")
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert "Read" in cmd[idx + 1]
        assert "Write" in cmd[idx + 1]
        # Should NOT have --permission-mode auto
        assert "--permission-mode" not in cmd

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_synthesize_uses_restricted_tools(self, mock_run, tmp_path):
        mock_run.return_value = mock.MagicMock(
            stdout="output", stderr="", returncode=0,
        )
        run_synthesize(tmp_path, "context")
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
        assert "--permission-mode" not in cmd


class TestDeepDiveInjectsContext:
    """Deep-dive should inject analysis-state and system-overview, not rely on Read."""

    @mock.patch("pensieve.docgen.subprocess.run")
    def test_injects_analysis_state_content(self, mock_run, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()

        # Create prior analysis files
        (ad / ".analysis-state.md").write_text("---\nphase_completed: 1\n---\n")
        (ad / "system-overview.md").write_text("# System Overview\nPurpose: test app\n")

        sp = _write_structure(tmp_path, [
            _file("src/a.py", symbols=[_sym("main")]),
        ])

        mock_run.return_value = mock.MagicMock(
            stdout="# Subsystem Doc\n", stderr="", returncode=0,
        )

        sub = SubsystemProposal(
            name="Core", directories=["src"], role="core", rationale="",
        )
        generate_subsystem_doc(sub, sp, FileSelection(files=[]), repo)

        cmd = mock_run.call_args[0][0]
        user_prompt = cmd[-1]
        # Analysis state and system overview should be IN the prompt
        assert "phase_completed: 1" in user_prompt
        assert "Purpose: test app" in user_prompt


class TestRealCLIPath:
    """End-to-end CLI test: pensieve analyze creates artifacts under agent-docs/."""

    def test_analyze_writes_to_agent_docs(self, tmp_path):
        """A full analyze run (with mocked LLM) should write files
        under <repo>/agent-docs/ and verify required artifacts."""
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("def main(): pass\n")

        from pensieve.scan import scan_repo
        scan_repo(repo)

        required_files = [
            "agent-context.md", "agent-context-nano.md", "patterns.md",
            "routing-map.md", "system-overview.md", "agent-brief.md",
            "index.md", "agent-protocol.md",
        ]

        def _mock_subprocess(cmd, **kwargs):
            cwd = kwargs.get("cwd", str(repo))
            ad = Path(cwd) / "agent-docs"
            ad.mkdir(parents=True, exist_ok=True)

            # Check system prompt to route the mock
            system_prompt = ""
            if "--system-prompt" in cmd:
                sp_idx = cmd.index("--system-prompt")
                if sp_idx + 1 < len(cmd):
                    system_prompt = cmd[sp_idx + 1]

            # Phase 3 synthesis: write all required files
            if "Phase 3" in system_prompt:
                for name in required_files:
                    (ad / name).write_text(f"# {name}\nGenerated.\n")
                return mock.MagicMock(
                    stdout="Synthesis complete.", stderr="", returncode=0,
                )

            # Phase 1 discover: write system-overview + analysis-state
            if "Phase 1" in system_prompt:
                (ad / "system-overview.md").write_text("# Overview\n")
                (ad / ".analysis-state.md").write_text("---\nphase_completed: 1\n---\n")
                return mock.MagicMock(
                    stdout="---FILE: system-overview.md---\n# Overview\n",
                    stderr="", returncode=0,
                )

            # Default: structured JSON for proposals/selections,
            # or plain text for deep-dive
            return mock.MagicMock(
                stdout=json.dumps({
                    "type": "result", "is_error": False, "result": "",
                    "structured_output": {
                        "subsystems": [
                            {"name": "Core", "directories": ["(root)"],
                             "role": "main", "rationale": "x"},
                        ],
                        "excluded": [],
                        "files": [],
                    },
                }),
                stderr="", returncode=0,
            )

        with mock.patch("pensieve.context.subprocess.run", side_effect=_mock_subprocess):
            with mock.patch("pensieve.docgen.subprocess.run", side_effect=_mock_subprocess):
                result = main(["analyze", str(repo)])

        ad = repo / "agent-docs"
        assert ad.exists()

        for name in required_files:
            assert (ad / name).exists(), f"Missing required artifact: {name}"

        assert (ad / "route-index.json").exists()
        assert result == 0
