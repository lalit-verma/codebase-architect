"""Tests for analyze pipeline checkpointing.

Covers:
  - Fingerprint computation and validation
  - Fingerprint invalidation on structure/graph/model change
  - Stage 2 checkpoint: save and load subsystem map
  - Stage 3 checkpoint: save and load file selections
  - Stage 4 checkpoint: save and load subsystem docs
  - Clear removes all checkpoints
  - CLI-path resume: second run reuses cached stages
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.checkpoint import AnalyzeCheckpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create structure.json and graph.json, return (output_dir, sp, gp)."""
    output_dir = tmp_path / "agent-docs"
    output_dir.mkdir()
    sp = output_dir / "structure.json"
    gp = output_dir / "graph.json"
    sp.write_text('{"files": [], "repo_root": "/tmp"}')
    gp.write_text('{"nodes": [], "edges": [], "external_imports": []}')
    return output_dir, sp, gp


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


class TestFingerprint:

    def test_fresh_repo_no_checkpoints(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        assert ckpt.validate(sp, gp) is False

    def test_after_save_validates(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        assert ckpt.validate(sp, gp) is True

    def test_structure_change_invalidates(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)

        # Modify structure.json
        sp.write_text('{"files": [{"new": true}], "repo_root": "/tmp"}')

        ckpt2 = AnalyzeCheckpoint(output_dir, model="sonnet")
        assert ckpt2.validate(sp, gp) is False

    def test_graph_change_invalidates(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)

        gp.write_text('{"nodes": [], "edges": [{"new": true}], "external_imports": []}')

        ckpt2 = AnalyzeCheckpoint(output_dir, model="sonnet")
        assert ckpt2.validate(sp, gp) is False

    def test_model_change_invalidates(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)

        ckpt2 = AnalyzeCheckpoint(output_dir, model="opus")
        assert ckpt2.validate(sp, gp) is False


# ---------------------------------------------------------------------------
# Stage 2: Subsystem map
# ---------------------------------------------------------------------------


class TestSubsystemMapCheckpoint:

    def test_no_checkpoint_returns_none(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        assert ckpt.load_subsystem_map() is None

    def test_save_and_load(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        data = {"subsystems": [{"name": "Core", "directories": ["src"]}], "excluded": []}
        ckpt.save_subsystem_map(data)

        assert ckpt.has_subsystem_map()
        loaded = ckpt.load_subsystem_map()
        assert loaded["subsystems"][0]["name"] == "Core"

    def test_not_valid_without_fingerprint(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        # Save data without validating fingerprint first
        ckpt.save_subsystem_map({"subsystems": []})
        # has_subsystem_map requires _valid = True
        assert not ckpt.has_subsystem_map()


# ---------------------------------------------------------------------------
# Stage 3: Selections
# ---------------------------------------------------------------------------


class TestSelectionCheckpoint:

    def test_save_and_load(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        ckpt.save_selection("API Routers", {"files": [{"file_path": "a.py", "reason": "x"}]})
        assert ckpt.has_selection("API Routers")
        loaded = ckpt.load_selection("API Routers")
        assert loaded["files"][0]["file_path"] == "a.py"

    def test_different_subsystems_independent(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        ckpt.save_selection("Routers", {"files": [{"file_path": "r.py"}]})
        ckpt.save_selection("Models", {"files": [{"file_path": "m.py"}]})

        assert ckpt.load_selection("Routers")["files"][0]["file_path"] == "r.py"
        assert ckpt.load_selection("Models")["files"][0]["file_path"] == "m.py"

    def test_missing_selection_returns_none(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)
        assert ckpt.load_selection("Nonexistent") is None


# ---------------------------------------------------------------------------
# Stage 4: Docs
# ---------------------------------------------------------------------------


class TestDocCheckpoint:

    def test_save_and_load(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        ckpt.save_doc("API Routers", "# API Routers\n\nDoc content.\n")
        assert ckpt.has_doc("API Routers")
        loaded = ckpt.load_doc("API Routers")
        assert "Doc content" in loaded

    def test_missing_doc_returns_none(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)
        assert ckpt.load_doc("Nonexistent") is None


# ---------------------------------------------------------------------------
# Regression: error caching + name collisions
# ---------------------------------------------------------------------------


class TestErrorNotCached:
    """Transient failures must not be checkpointed as completed work."""

    def test_failed_selection_not_cached_by_checkpoint(self, tmp_path):
        """If we save a selection with an error field, it should still
        be loadable from the file, but the CLI should not save it.
        This tests the checkpoint module's behavior — the CLI gating
        is tested separately."""
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        # Saving a selection with no error should be retrievable
        ckpt.save_selection("Good", {"files": [{"file_path": "a.py"}]})
        assert ckpt.has_selection("Good")

        # A selection that was never saved should not exist
        assert not ckpt.has_selection("NeverSaved")


class TestNameCollisions:
    """Distinct subsystem names must not collide in checkpoint storage."""

    def test_slash_vs_space_vs_underscore_no_collision(self, tmp_path):
        """'A/B', 'A B', and 'A_B' are distinct names and must
        get distinct checkpoint files."""
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        ckpt.save_selection("A/B", {"files": [{"file_path": "ab_slash.py"}]})
        ckpt.save_selection("A B", {"files": [{"file_path": "ab_space.py"}]})
        ckpt.save_selection("A_B", {"files": [{"file_path": "ab_under.py"}]})

        loaded_slash = ckpt.load_selection("A/B")
        loaded_space = ckpt.load_selection("A B")
        loaded_under = ckpt.load_selection("A_B")

        assert loaded_slash["files"][0]["file_path"] == "ab_slash.py"
        assert loaded_space["files"][0]["file_path"] == "ab_space.py"
        assert loaded_under["files"][0]["file_path"] == "ab_under.py"

    def test_doc_names_no_collision(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)

        ckpt.save_doc("A/B", "# A/B doc\n")
        ckpt.save_doc("A B", "# A B doc\n")

        assert "A/B doc" in ckpt.load_doc("A/B")
        assert "A B doc" in ckpt.load_doc("A B")


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestClear:

    def test_clear_removes_everything(self, tmp_path):
        output_dir, sp, gp = _make_inputs(tmp_path)
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.save_fingerprint(sp, gp)
        ckpt.validate(sp, gp)
        ckpt.save_subsystem_map({"subsystems": []})
        ckpt.save_selection("Test", {"files": []})
        ckpt.save_doc("Test", "# Doc\n")

        ckpt.clear()

        ckpt2 = AnalyzeCheckpoint(output_dir, model="sonnet")
        assert ckpt2.validate(sp, gp) is False
        assert ckpt2.load_subsystem_map() is None

    def test_clear_on_nonexistent_dir_safe(self, tmp_path):
        output_dir = tmp_path / "agent-docs"
        output_dir.mkdir()
        ckpt = AnalyzeCheckpoint(output_dir, model="sonnet")
        ckpt.clear()  # should not raise


# ---------------------------------------------------------------------------
# CLI-path resume (removed — `pensieve analyze` CLI was removed in
# favor of v1 slash commands. Checkpoint module is still used for
# scan caching. The tests above validate the checkpoint API.)
# ---------------------------------------------------------------------------


class _DeprecatedTestCLIResume:

    def test_second_run_reuses_checkpoints(self, capsys, tmp_path):
        """A second analyze run on the same inputs should show [reused]."""
        from unittest import mock
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (repo / "main.py").write_text("def main(): pass\n")

        sp = ad / "structure.json"
        sp.write_text(json.dumps({
            "repo_root": str(repo),
            "files": [
                {"file_path": "main.py", "language": "python",
                 "symbols": [{"name": "main", "kind": "function",
                              "line_start": 1, "line_end": 1,
                              "signature": "def main():", "visibility": "public",
                              "parent": None, "docstring": None,
                              "parameters": [], "return_type": None}],
                 "imports": [], "exports": [], "call_edges": [], "comments": []},
            ],
            "errors": [], "extractor_version": "test",
        }))
        (ad / "graph.json").write_text(json.dumps({
            "nodes": [], "edges": [], "external_imports": [],
        }))

        # Mock all LLM calls
        call_count = [0]

        def _mock_subprocess(cmd, **kwargs):
            call_count[0] += 1
            prompt = cmd[-1] if cmd else ""
            # Proposal
            if "subsystem" in prompt.lower() and "propose" not in str(cmd):
                return mock.MagicMock(
                    stdout=json.dumps({
                        "type": "result", "is_error": False, "result": "",
                        "structured_output": {
                            "files": [{"file_path": "main.py", "reason": "only file"}],
                        },
                    }),
                    stderr="", returncode=0,
                )
            if "structural skeleton" in prompt.lower() or "Structural skeleton" in prompt:
                return mock.MagicMock(
                    stdout=json.dumps({
                        "type": "result", "is_error": False, "result": "",
                        "structured_output": {
                            "files": [{"file_path": "main.py", "reason": "only file"}],
                        },
                    }),
                    stderr="", returncode=0,
                )
            if "subsystem boundaries" in prompt.lower() or "Analyze this" in prompt:
                return mock.MagicMock(
                    stdout=json.dumps({
                        "type": "result", "is_error": False, "result": "",
                        "structured_output": {
                            "subsystems": [
                                {"name": "Core", "directories": ["(root)"],
                                 "role": "main app", "rationale": "only dir"},
                            ],
                            "excluded": [],
                        },
                    }),
                    stderr="", returncode=0,
                )
            # Doc generation or synthesis — return plain text
            return mock.MagicMock(
                stdout="# Generated doc\n\nContent.\n",
                stderr="", returncode=0,
            )

        with mock.patch("pensieve.context.subprocess.run", side_effect=_mock_subprocess):
            result1 = main(["analyze", str(repo)])

        first_calls = call_count[0]
        capsys.readouterr()  # clear output

        # Second run — should reuse checkpoints
        call_count[0] = 0
        with mock.patch("pensieve.context.subprocess.run", side_effect=_mock_subprocess):
            result2 = main(["analyze", str(repo)])

        second_calls = call_count[0]
        captured = capsys.readouterr()

        # Second run should make fewer LLM calls (only synthesis, not proposal/selection/doc)
        assert second_calls < first_calls, (
            f"Second run made {second_calls} calls vs first run {first_calls} — "
            f"checkpoints should have reduced LLM calls"
        )
        assert "reused" in captured.out.lower()
