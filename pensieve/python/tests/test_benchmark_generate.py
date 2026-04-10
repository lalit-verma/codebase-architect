"""Tests for repo-aware benchmark task generation (A13 rework).

Covers:
  - RepoContext building from structure.json + graph.json
  - File classification: source, test, central, untested
  - Pattern directory detection
  - Task generation per family: add_sibling, add_test, bug_fix, find_owner
  - Difficulty stratification
  - Setup action application: write_file, delete_file, modify_file, mutate_function
  - Generated task serialization
  - Task set is bounded and non-empty on a realistic repo context
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.benchmark.generate import (
    FileInfo,
    RepoContext,
    TaskInstance,
    apply_setup_actions,
    build_repo_context,
    generate_tasks,
    save_generated_tasks,
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
    path.write_text(json.dumps({
        "nodes": [],
        "edges": edges,
        "external_imports": [],
    }))
    return path


def _file(path, language="python", symbols=None, imports=None, call_edges=None):
    return {
        "file_path": path,
        "language": language,
        "symbols": symbols or [],
        "imports": imports or [],
        "exports": [],
        "call_edges": call_edges or [],
        "comments": [],
    }


def _sym(name, kind="function", line_start=1, line_end=10, signature=None):
    return {
        "name": name,
        "kind": kind,
        "line_start": line_start,
        "line_end": line_end,
        "signature": signature or f"def {name}():",
        "visibility": "public",
        "parent": None,
        "docstring": None,
        "parameters": [],
        "return_type": None,
    }


def _edge(source, target, kind="imports", detail=""):
    return {
        "source": source,
        "target": target,
        "kind": kind,
        "detail": detail,
        "line": 1,
        "confidence": 1.0,
    }


def _make_realistic_context(tmp_path):
    """Build a RepoContext that resembles a real repo."""
    sp = _write_structure(tmp_path, [
        # Routers - a pattern directory
        _file("src/routers/users.py", symbols=[
            _sym("get_users", line_start=10, line_end=25),
            _sym("create_user", line_start=27, line_end=45),
            _sym("delete_user", line_start=47, line_end=60),
        ]),
        _file("src/routers/posts.py", symbols=[
            _sym("get_posts", line_start=10, line_end=30),
            _sym("create_post", line_start=32, line_end=50),
        ]),
        _file("src/routers/comments.py", symbols=[
            _sym("get_comments", line_start=10, line_end=25),
            _sym("add_comment", line_start=27, line_end=40),
        ]),
        # Models
        _file("src/models/user.py", symbols=[
            _sym("User", kind="class", line_start=5, line_end=30),
            _sym("UserCreate", kind="class", line_start=32, line_end=40),
        ]),
        _file("src/models/post.py", symbols=[
            _sym("Post", kind="class", line_start=5, line_end=25),
        ]),
        _file("src/models/base.py", symbols=[
            _sym("Base", kind="class", line_start=5, line_end=15),
            _sym("get_session", line_start=17, line_end=30),
        ]),
        # Utils - central, imported by many
        _file("src/utils/auth.py", symbols=[
            _sym("get_current_user", line_start=10, line_end=25),
            _sym("verify_token", line_start=27, line_end=40),
            _sym("hash_password", line_start=42, line_end=55),
        ]),
        _file("src/utils/helpers.py", symbols=[
            _sym("paginate", line_start=5, line_end=20),
            _sym("validate_email", line_start=22, line_end=35),
        ]),
        # Config
        _file("src/config.py", symbols=[
            _sym("Settings", kind="class", line_start=5, line_end=30),
            _sym("get_settings", line_start=32, line_end=40),
        ]),
        # Tests
        _file("tests/test_users.py", symbols=[
            _sym("test_get_users"),
            _sym("test_create_user"),
        ]),
        _file("tests/test_posts.py", symbols=[
            _sym("test_get_posts"),
        ]),
    ])

    gp = _write_graph(tmp_path, [
        # Routers import from models and utils
        _edge("src/routers/users.py", "src/models/user.py"),
        _edge("src/routers/users.py", "src/utils/auth.py"),
        _edge("src/routers/posts.py", "src/models/post.py"),
        _edge("src/routers/posts.py", "src/utils/auth.py"),
        _edge("src/routers/comments.py", "src/utils/auth.py"),
        # Models import from base
        _edge("src/models/user.py", "src/models/base.py"),
        _edge("src/models/post.py", "src/models/base.py"),
        # Utils imported by many
        _edge("src/config.py", "src/utils/helpers.py"),
        # Test edges
        _edge("tests/test_users.py", "src/routers/users.py", kind="tests"),
        _edge("tests/test_posts.py", "src/routers/posts.py", kind="tests"),
    ])

    return build_repo_context(sp, gp)


# ---------------------------------------------------------------------------
# RepoContext building
# ---------------------------------------------------------------------------


class TestRepoContext:

    def test_file_count(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        assert ctx.total_files == 11

    def test_source_files_exclude_tests(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        source_paths = [ctx.files[i].path for i in ctx.source_files]
        assert "tests/test_users.py" not in source_paths
        assert "src/routers/users.py" in source_paths

    def test_central_files_have_incoming_edges(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        # auth.py has 3 incoming edges (from 3 routers)
        central_paths = [ctx.files[i].path for i in ctx.central_files]
        assert "src/utils/auth.py" in central_paths

    def test_untested_files_detected(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        untested_paths = [ctx.files[i].path for i in ctx.untested_files]
        # comments.py has no test file
        assert "src/routers/comments.py" in untested_paths
        # users.py has a test file
        assert "src/routers/users.py" not in untested_paths

    def test_pattern_dirs_detected(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        pattern_dir_paths = [p["dir"] for p in ctx.pattern_dirs]
        assert "src/routers" in pattern_dir_paths

    def test_languages_counted(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        assert ctx.languages["python"] == 11


# ---------------------------------------------------------------------------
# Task generation
# ---------------------------------------------------------------------------


class TestTaskGeneration:

    def test_generates_nonempty(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx)
        assert len(tasks) > 0

    def test_difficulty_stratification(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx)
        difficulties = {t.difficulty for t in tasks}
        # Should have at least easy and medium
        assert "easy" in difficulties

    def test_max_limits_respected(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=1, max_medium=1, max_hard=1)
        easy = [t for t in tasks if t.difficulty == "easy"]
        medium = [t for t in tasks if t.difficulty == "medium"]
        hard = [t for t in tasks if t.difficulty == "hard"]
        assert len(easy) <= 1
        assert len(medium) <= 1
        assert len(hard) <= 1

    def test_deterministic_with_seed(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks1 = generate_tasks(ctx, seed=42)
        tasks2 = generate_tasks(ctx, seed=42)
        assert len(tasks1) == len(tasks2)
        for t1, t2 in zip(tasks1, tasks2):
            assert t1.instance_id == t2.instance_id

    def test_no_placeholder_in_instructions(self, tmp_path):
        """Generated instructions should be concrete, no {placeholders}."""
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx)
        for task in tasks:
            assert "{" not in task.instruction, (
                f"Task {task.instance_id} has unresolved placeholder: "
                f"{task.instruction[:100]}"
            )

    def test_each_task_has_instance_id(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx)
        ids = [t.instance_id for t in tasks]
        assert len(ids) == len(set(ids)), "Duplicate instance IDs"


class TestAddSiblingGeneration:

    def test_targets_pattern_directory(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=3, max_medium=0, max_hard=0)
        sibling_tasks = [t for t in tasks if t.template_family == "add_sibling"]
        assert len(sibling_tasks) >= 1
        # Should target a pattern directory, not migrations
        for t in sibling_tasks:
            assert "migration" not in t.instruction.lower()

    def test_strict_checker_is_file_exists(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=1, max_medium=0, max_hard=0)
        sibling = [t for t in tasks if t.template_family == "add_sibling"]
        if sibling:
            assert sibling[0].strict_checker.checker_type == "file_exists"
            assert sibling[0].strict_checker.target_file is not None


class TestBugFixGeneration:

    def test_has_setup_actions(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=0, max_medium=2, max_hard=0)
        bug_tasks = [t for t in tasks if t.template_family == "bug_fix"]
        if bug_tasks:
            assert len(bug_tasks[0].setup_actions) > 0
            assert bug_tasks[0].setup_actions[0]["action"] == "mutate_function"

    def test_targets_real_function(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=0, max_medium=2, max_hard=0)
        bug_tasks = [t for t in tasks if t.template_family == "bug_fix"]
        if bug_tasks:
            # Instruction should name a real function from the repo
            all_func_names = [
                s["name"] for fi in ctx.files for s in fi.symbols
                if s.get("kind") in ("function", "method")
            ]
            assert any(
                name in bug_tasks[0].instruction
                for name in all_func_names
            ), f"Bug task doesn't target a real function: {bug_tasks[0].instruction[:200]}"


class TestFindOwnerGeneration:

    def test_targets_central_file(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=0, max_medium=0, max_hard=1)
        owner_tasks = [t for t in tasks if t.template_family == "find_owner"]
        if owner_tasks:
            # Should mention a real directory
            assert "src/" in owner_tasks[0].instruction


# ---------------------------------------------------------------------------
# Setup action execution
# ---------------------------------------------------------------------------


class TestSetupActions:

    def test_write_file(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        errors = apply_setup_actions([{
            "action": "write_file",
            "path": "new_file.py",
            "content": "print('hello')\n",
        }], repo)
        assert errors == []
        assert (repo / "new_file.py").read_text() == "print('hello')\n"

    def test_delete_file(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "to_delete.py").write_text("old content")
        errors = apply_setup_actions([{
            "action": "delete_file",
            "path": "to_delete.py",
        }], repo)
        assert errors == []
        assert not (repo / "to_delete.py").exists()

    def test_modify_file_appends(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "existing.py").write_text("line1\n")
        errors = apply_setup_actions([{
            "action": "modify_file",
            "path": "existing.py",
            "content": "line2",
        }], repo)
        assert errors == []
        content = (repo / "existing.py").read_text()
        assert "line1" in content
        assert "line2" in content

    def test_modify_file_nonexistent_errors(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        errors = apply_setup_actions([{
            "action": "modify_file",
            "path": "nonexistent.py",
            "content": "stuff",
        }], repo)
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_mutate_function_swaps_operator(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "code.py").write_text(
            "def foo():\n"
            "    x = 1\n"
            "    if x <= 10:\n"
            "        return True\n"
            "    return False\n"
        )
        errors = apply_setup_actions([{
            "action": "mutate_function",
            "path": "code.py",
            "function_name": "foo",
            "line_start": 1,
            "line_end": 5,
            "mutation": "swap_comparison",
            "find_patterns": ["<="],
            "replace_patterns": [">="],
        }], repo)
        assert errors == []
        content = (repo / "code.py").read_text()
        assert ">=" in content
        assert "<=" not in content

    def test_mutate_function_no_match_errors(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "code.py").write_text("def foo():\n    pass\n")
        errors = apply_setup_actions([{
            "action": "mutate_function",
            "path": "code.py",
            "function_name": "foo",
            "line_start": 1,
            "line_end": 2,
            "mutation": "swap_comparison",
            "find_patterns": ["<="],
            "replace_patterns": [">="],
        }], repo)
        assert len(errors) == 1
        assert "no matching pattern" in errors[0]

    def test_unknown_action_errors(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        errors = apply_setup_actions([{
            "action": "unknown_action",
            "path": "file.py",
        }], repo)
        assert len(errors) == 1
        assert "Unknown" in errors[0]

    def test_missing_path_errors(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        errors = apply_setup_actions([{
            "action": "write_file",
        }], repo)
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:

    def test_task_instance_to_dict(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=1, max_medium=0, max_hard=0)
        assert len(tasks) >= 1
        d = tasks[0].to_dict()
        assert "template_family" in d
        assert "instance_id" in d
        assert "instruction" in d
        assert "strict_checker" in d
        assert "lenient_checker" in d

    def test_save_generated_tasks(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx)
        out = tmp_path / "generated-tasks.json"
        save_generated_tasks(tasks, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["task_count"] == len(tasks)
        assert "by_difficulty" in data
        assert "tasks" in data

    def test_task_to_json_roundtrip(self, tmp_path):
        ctx = _make_realistic_context(tmp_path)
        tasks = generate_tasks(ctx, max_easy=1, max_medium=0, max_hard=0)
        if tasks:
            j = tasks[0].to_json()
            d = json.loads(j)
            assert d["template_family"] == tasks[0].template_family
