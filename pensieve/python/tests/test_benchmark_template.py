"""Tests for the benchmark task template schema (milestone A6).

Covers:
  - Construction with all fields
  - JSON round-trip serialization
  - File I/O (save/load)
  - Validation: required fields, valid enums, checker-specific requirements
  - Setup actions validation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pensieve.benchmark.template import (
    CheckerSpec,
    TaskTemplate,
    TemplateError,
    validate_template,
    VALID_DIFFICULTIES,
    VALID_TASK_TYPES,
    VALID_CHECKER_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_checker(checker_type="llm_judge", **kw):
    defaults = dict(
        criteria="Output should be correct",
        llm_prompt="Is this output correct? Answer PASS or FAIL.",
    )
    defaults.update(kw)
    return CheckerSpec(checker_type=checker_type, **defaults)


def _make_template(**overrides):
    defaults = dict(
        name="test_task",
        task_type="add_handler",
        difficulty="easy",
        description="Test adding a handler",
        instruction="Create a new handler at {file_path}",
        strict_checker=CheckerSpec(
            checker_type="file_exists",
            criteria="File should exist",
            target_file="src/handlers/new.py",
        ),
        lenient_checker=_make_checker(),
    )
    defaults.update(overrides)
    return TaskTemplate(**defaults)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:

    def test_minimal_template(self):
        t = _make_template()
        assert t.name == "test_task"
        assert t.task_type == "add_handler"
        assert t.difficulty == "easy"
        assert t.setup_actions == []
        assert t.tags == []

    def test_with_setup_actions(self):
        t = _make_template(setup_actions=[
            {"action": "write_file", "path": "src/bug.py", "content": "x = 1/0"},
        ])
        assert len(t.setup_actions) == 1

    def test_with_tags(self):
        t = _make_template(tags=["pattern", "python"])
        assert t.tags == ["pattern", "python"]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:

    def test_to_dict(self):
        t = _make_template()
        d = t.to_dict()
        assert d["name"] == "test_task"
        assert d["strict_checker"]["checker_type"] == "file_exists"
        assert d["lenient_checker"]["checker_type"] == "llm_judge"

    def test_to_json_and_back(self):
        t = _make_template()
        j = t.to_json()
        restored = TaskTemplate.from_json(j)
        assert restored.name == t.name
        assert restored.task_type == t.task_type
        assert restored.strict_checker.checker_type == "file_exists"
        assert restored.lenient_checker.checker_type == "llm_judge"

    def test_round_trip_preserves_all_fields(self):
        t = _make_template(
            setup_actions=[{"action": "write_file", "path": "x.py", "content": "y"}],
            tags=["test"],
        )
        j = t.to_json()
        restored = TaskTemplate.from_json(j)
        assert restored.setup_actions == t.setup_actions
        assert restored.tags == t.tags
        assert restored.strict_checker.target_file == "src/handlers/new.py"

    def test_save_and_load(self, tmp_path):
        t = _make_template()
        path = tmp_path / "template.json"
        t.save(path)
        loaded = TaskTemplate.load(path)
        assert loaded.name == t.name
        assert loaded.strict_checker.checker_type == t.strict_checker.checker_type


# ---------------------------------------------------------------------------
# Validation — valid cases
# ---------------------------------------------------------------------------


class TestValidationValid:

    def test_minimal_valid_template(self):
        t = _make_template()
        validate_template(t)  # should not raise

    def test_all_task_types_accepted(self):
        for tt in VALID_TASK_TYPES:
            t = _make_template(task_type=tt)
            validate_template(t)

    def test_all_difficulties_accepted(self):
        for d in VALID_DIFFICULTIES:
            t = _make_template(difficulty=d)
            validate_template(t)

    def test_all_checker_types_accepted(self):
        for ct in VALID_CHECKER_TYPES:
            kw = {"criteria": "test"}
            if ct == "file_exists":
                kw["target_file"] = "x.py"
            elif ct == "symbol_exists":
                kw["target_symbol"] = "foo"
            elif ct == "content_contains":
                kw["target_string"] = "hello"
            elif ct == "llm_judge":
                kw["llm_prompt"] = "Is this correct?"
            checker = CheckerSpec(checker_type=ct, **kw)
            t = _make_template(strict_checker=checker)
            validate_template(t)


# ---------------------------------------------------------------------------
# Validation — invalid cases
# ---------------------------------------------------------------------------


class TestValidationInvalid:

    def test_empty_name(self):
        t = _make_template(name="")
        with pytest.raises(TemplateError, match="name is empty"):
            validate_template(t)

    def test_invalid_task_type(self):
        t = _make_template(task_type="bogus")
        with pytest.raises(TemplateError, match="task_type.*not in"):
            validate_template(t)

    def test_invalid_difficulty(self):
        t = _make_template(difficulty="extreme")
        with pytest.raises(TemplateError, match="difficulty.*not in"):
            validate_template(t)

    def test_empty_description(self):
        t = _make_template(description="")
        with pytest.raises(TemplateError, match="description is empty"):
            validate_template(t)

    def test_empty_instruction(self):
        t = _make_template(instruction="")
        with pytest.raises(TemplateError, match="instruction is empty"):
            validate_template(t)

    def test_invalid_checker_type(self):
        bad_checker = CheckerSpec(checker_type="bogus", criteria="test")
        t = _make_template(strict_checker=bad_checker)
        with pytest.raises(TemplateError, match="checker_type.*not in"):
            validate_template(t)

    def test_empty_checker_criteria(self):
        bad_checker = CheckerSpec(checker_type="llm_judge", criteria="", llm_prompt="test")
        t = _make_template(lenient_checker=bad_checker)
        with pytest.raises(TemplateError, match="criteria is empty"):
            validate_template(t)

    def test_file_exists_without_target_file(self):
        bad_checker = CheckerSpec(checker_type="file_exists", criteria="test")
        t = _make_template(strict_checker=bad_checker)
        with pytest.raises(TemplateError, match="file_exists.*requires target_file"):
            validate_template(t)

    def test_symbol_exists_without_target_symbol(self):
        bad_checker = CheckerSpec(checker_type="symbol_exists", criteria="test")
        t = _make_template(strict_checker=bad_checker)
        with pytest.raises(TemplateError, match="symbol_exists.*requires target_symbol"):
            validate_template(t)

    def test_content_contains_without_target_string(self):
        bad_checker = CheckerSpec(checker_type="content_contains", criteria="test")
        t = _make_template(strict_checker=bad_checker)
        with pytest.raises(TemplateError, match="content_contains.*requires target_string"):
            validate_template(t)

    def test_llm_judge_without_llm_prompt(self):
        bad_checker = CheckerSpec(checker_type="llm_judge", criteria="test")
        t = _make_template(lenient_checker=bad_checker)
        with pytest.raises(TemplateError, match="llm_judge.*requires llm_prompt"):
            validate_template(t)

    def test_invalid_setup_action(self):
        t = _make_template(setup_actions=[
            {"action": "destroy_everything", "path": "x.py"},
        ])
        with pytest.raises(TemplateError, match="setup_actions.*action.*not in"):
            validate_template(t)

    def test_setup_action_missing_path(self):
        t = _make_template(setup_actions=[
            {"action": "write_file"},
        ])
        with pytest.raises(TemplateError, match="setup_actions.*path is empty"):
            validate_template(t)

    def test_multiple_errors_reported(self):
        t = _make_template(name="", description="", instruction="")
        with pytest.raises(TemplateError, match="3 error"):
            validate_template(t)


# ---------------------------------------------------------------------------
# Enum sets
# ---------------------------------------------------------------------------


class TestEnumSets:

    def test_all_expected_task_types(self):
        expected = {"add_handler", "add_test", "bug_fix", "find_owner",
                    "navigation", "cross_subsystem", "refactor"}
        assert VALID_TASK_TYPES == expected

    def test_all_expected_difficulties(self):
        assert VALID_DIFFICULTIES == {"easy", "medium", "hard"}

    def test_all_expected_checker_types(self):
        expected = {"file_exists", "symbol_exists", "pattern_followed",
                    "content_contains", "llm_judge"}
        assert VALID_CHECKER_TYPES == expected
