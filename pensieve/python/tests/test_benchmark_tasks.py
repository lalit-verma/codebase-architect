"""Tests for benchmark task templates (milestone A7).

Covers:
  - All 5 templates pass validate_template()
  - All templates serialize and deserialize correctly
  - Placeholder inventory: only documented placeholders used
  - Template registry: get_all_templates, get_template_by_name
  - Each template has both strict and lenient checkers
  - Each template's checker type has its required fields
"""

from __future__ import annotations

import re

import pytest

from pensieve.benchmark.tasks import (
    ALL_TEMPLATES,
    DOCUMENTED_PLACEHOLDERS,
    get_all_templates,
    get_template_by_name,
    ADD_HANDLER,
    ADD_TEST,
    BUG_FIX_LOCALIZED,
    FIND_OWNER,
    COLD_NAVIGATION,
)
from pensieve.benchmark.template import validate_template, TaskTemplate


# ---------------------------------------------------------------------------
# All templates valid
# ---------------------------------------------------------------------------


class TestAllTemplatesValid:

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_passes_validation(self, template):
        validate_template(template)

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_has_non_empty_instruction(self, template):
        assert len(template.instruction) > 50

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_has_non_empty_description(self, template):
        assert len(template.description) > 20

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_has_strict_and_lenient_checkers(self, template):
        assert template.strict_checker is not None
        assert template.lenient_checker is not None
        assert template.strict_checker.criteria
        assert template.lenient_checker.criteria


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_json_round_trip(self, template):
        j = template.to_json()
        restored = TaskTemplate.from_json(j)
        assert restored.name == template.name
        assert restored.task_type == template.task_type
        assert restored.difficulty == template.difficulty
        assert restored.strict_checker.checker_type == template.strict_checker.checker_type
        assert restored.lenient_checker.checker_type == template.lenient_checker.checker_type

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_save_and_load(self, template, tmp_path):
        path = tmp_path / f"{template.name}.json"
        template.save(path)
        loaded = TaskTemplate.load(path)
        assert loaded.name == template.name
        validate_template(loaded)


# ---------------------------------------------------------------------------
# Placeholder inventory
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _extract_placeholders(template: TaskTemplate) -> set[str]:
    """Extract all {placeholder} names from a template's text fields."""
    text_fields = [
        template.instruction,
        template.strict_checker.criteria,
        template.strict_checker.target_file or "",
        template.strict_checker.target_string or "",
        template.strict_checker.llm_prompt or "",
        template.lenient_checker.criteria,
        template.lenient_checker.target_file or "",
        template.lenient_checker.target_string or "",
        template.lenient_checker.llm_prompt or "",
    ]
    placeholders: set[str] = set()
    for field in text_fields:
        placeholders.update(_PLACEHOLDER_RE.findall(field))
    return placeholders


class TestPlaceholders:

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.name)
    def test_only_documented_placeholders_used(self, template):
        """Every placeholder in the template must be in DOCUMENTED_PLACEHOLDERS."""
        used = _extract_placeholders(template)
        undocumented = used - DOCUMENTED_PLACEHOLDERS
        assert undocumented == set(), (
            f"Template '{template.name}' uses undocumented placeholders: "
            f"{undocumented}"
        )

    def test_at_least_one_placeholder_per_template(self):
        for t in ALL_TEMPLATES:
            used = _extract_placeholders(t)
            assert len(used) > 0, f"Template '{t.name}' has no placeholders"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:

    def test_get_all_templates_returns_five(self):
        templates = get_all_templates()
        assert len(templates) == 5

    def test_all_names_unique(self):
        names = [t.name for t in get_all_templates()]
        assert len(names) == len(set(names))

    def test_all_task_types_present(self):
        types = {t.task_type for t in get_all_templates()}
        assert "add_handler" in types
        assert "add_test" in types
        assert "bug_fix" in types
        assert "find_owner" in types
        assert "navigation" in types

    def test_get_template_by_name(self):
        assert get_template_by_name("add_handler") is ADD_HANDLER
        assert get_template_by_name("add_test") is ADD_TEST
        assert get_template_by_name("bug_fix_localized") is BUG_FIX_LOCALIZED
        assert get_template_by_name("find_owner") is FIND_OWNER
        assert get_template_by_name("cold_navigation") is COLD_NAVIGATION

    def test_get_template_by_name_missing(self):
        assert get_template_by_name("nonexistent") is None

    def test_difficulty_spread(self):
        difficulties = {t.difficulty for t in get_all_templates()}
        assert "easy" in difficulties
        assert "medium" in difficulties


# ---------------------------------------------------------------------------
# Individual template spot checks
# ---------------------------------------------------------------------------


class TestIndividualTemplates:

    def test_add_handler_uses_pattern_placeholders(self):
        placeholders = _extract_placeholders(ADD_HANDLER)
        assert "most_common_pattern" in placeholders
        assert "pattern_example_file" in placeholders
        assert "new_file_path" in placeholders

    def test_add_test_uses_file_path(self):
        placeholders = _extract_placeholders(ADD_TEST)
        assert "file_path" in placeholders
        assert "test_file_path" in placeholders

    def test_bug_fix_has_setup_action(self):
        assert len(BUG_FIX_LOCALIZED.setup_actions) > 0
        assert BUG_FIX_LOCALIZED.setup_actions[0]["action"] == "modify_file"

    def test_bug_fix_uses_function_name(self):
        placeholders = _extract_placeholders(BUG_FIX_LOCALIZED)
        assert "function_name" in placeholders
        assert "bug_description" in placeholders

    def test_find_owner_uses_subsystem(self):
        placeholders = _extract_placeholders(FIND_OWNER)
        assert "subsystem_name" in placeholders
        assert "file_path" in placeholders

    def test_cold_navigation_uses_repo_description(self):
        placeholders = _extract_placeholders(COLD_NAVIGATION)
        assert "repo_description" in placeholders

    def test_all_lenient_checkers_are_llm_judge(self):
        """All lenient checkers should use LLM judgment."""
        for t in ALL_TEMPLATES:
            assert t.lenient_checker.checker_type == "llm_judge", (
                f"Template '{t.name}' lenient checker is "
                f"'{t.lenient_checker.checker_type}', expected 'llm_judge'"
            )

    def test_strict_criteria_do_not_overclaim(self):
        """Strict checker criteria should honestly describe what the
        deterministic checker can verify, not claim more.
        Check for affirmative overclaiming phrases, not disclaimer text."""
        for t in ALL_TEMPLATES:
            criteria = t.strict_checker.criteria.lower()
            # Affirmative overclaim phrases that a strict checker can't deliver
            overclaim_phrases = [
                "fixes the bug correctly",
                "follows the pattern correctly",
                "correctly identifies",
                "covers the main functions",
                "at least 3 distinct",
            ]
            for phrase in overclaim_phrases:
                assert phrase not in criteria, (
                    f"Template '{t.name}' strict criteria overclaims "
                    f"with '{phrase}': {t.strict_checker.criteria}"
                )

    def test_add_handler_strict_uses_new_file_path(self):
        """ADD_HANDLER strict checker should use the concrete {new_file_path}."""
        assert ADD_HANDLER.strict_checker.target_file == "{new_file_path}"

    def test_add_test_strict_uses_test_file_path(self):
        """ADD_TEST strict checker should use the concrete {test_file_path}."""
        assert ADD_TEST.strict_checker.target_file == "{test_file_path}"

    def test_bug_fix_strict_is_minimal_sanity_check(self):
        """BUG_FIX strict checker should be a sanity check (function exists),
        not a correctness check."""
        assert "sanity check" in BUG_FIX_LOCALIZED.strict_checker.criteria.lower()

    def test_find_owner_strict_matches_actual_check(self):
        """FIND_OWNER strict criteria should only claim to check for the
        subsystem name, not file paths or conventions."""
        criteria = FIND_OWNER.strict_checker.criteria.lower()
        assert "subsystem name" in criteria
        assert "at least one file path" not in criteria

    def test_cold_navigation_strict_matches_actual_check(self):
        """COLD_NAVIGATION strict criteria should say 'at least one',
        not 'at least 3'."""
        criteria = COLD_NAVIGATION.strict_checker.criteria.lower()
        assert "at least one" in criteria
        assert "at least 3" not in criteria
