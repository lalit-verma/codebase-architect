"""Benchmark task template schema (milestone A6).

Defines the data format for benchmark task templates. Each template
describes a simulated coding task that can be run against a target
repo to measure framework effectiveness.

Templates are repo-agnostic: they contain instruction templates with
placeholders (e.g., `{most_common_pattern}`, `{file_path}`) that get
filled at runtime from the repo's `structure.json`.

Design:
  - Each template has both a strict and lenient checker specification.
  - Strict = exact structural match (file created, function present, etc.)
  - Lenient = LLM-judged behavioral match (does the output look right?)
  - Templates are categorized by difficulty (easy, medium, hard) and
    by task type (add_handler, add_test, bug_fix, find_owner, navigation).

Serialization: JSON via dataclasses.asdict → json.dumps.
Validation: validate_template() raises TemplateError on invalid data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Difficulty = Literal["easy", "medium", "hard"]
TaskType = Literal[
    "add_handler",
    "add_test",
    "bug_fix",
    "find_owner",
    "navigation",
    "cross_subsystem",
    "refactor",
]
CheckerType = Literal[
    "file_exists",       # strict: check that a specific file was created
    "symbol_exists",     # strict: check that a function/class exists in output
    "pattern_followed",  # strict: check output matches a pattern from patterns.md
    "content_contains",  # strict: check output contains a specific string
    "llm_judge",         # lenient: LLM evaluates the output against criteria
]

VALID_DIFFICULTIES: frozenset[str] = frozenset(Difficulty.__args__)  # type: ignore[attr-defined]
VALID_TASK_TYPES: frozenset[str] = frozenset(TaskType.__args__)  # type: ignore[attr-defined]
VALID_CHECKER_TYPES: frozenset[str] = frozenset(CheckerType.__args__)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Checker specification
# ---------------------------------------------------------------------------


@dataclass
class CheckerSpec:
    """Specification for how to check a task's output.

    Each task has both a strict and lenient checker. The strict checker
    uses deterministic checks (file existence, string matching). The
    lenient checker uses LLM judgment.
    """

    checker_type: CheckerType
    criteria: str  # human-readable description of what constitutes a pass
    target_file: str | None = None  # for file_exists / symbol_exists
    target_symbol: str | None = None  # for symbol_exists
    target_string: str | None = None  # for content_contains
    llm_prompt: str | None = None  # for llm_judge: the evaluation prompt


# ---------------------------------------------------------------------------
# Task template
# ---------------------------------------------------------------------------


@dataclass
class TaskTemplate:
    """A benchmark task template.

    Templates are repo-agnostic. Placeholders in `instruction` are
    filled at runtime from the repo's structure.json.

    Common placeholders:
      {most_common_pattern}  — name of the most-used code pattern
      {pattern_example_file} — example file for that pattern
      {file_path}            — a specific file to operate on
      {function_name}        — a specific function to modify
      {subsystem_name}       — a subsystem name from the architecture map
    """

    name: str  # unique identifier, e.g., "add_handler"
    task_type: TaskType
    difficulty: Difficulty
    description: str  # human-readable description of what the task tests
    instruction: str  # the prompt given to the agent (with placeholders)

    strict_checker: CheckerSpec  # deterministic pass/fail check
    lenient_checker: CheckerSpec  # LLM-judged pass/fail check

    # Optional: modifications to the repo before running the task
    # (e.g., plant a bug, remove a file). List of dicts with
    # {"action": "write_file"|"delete_file"|"modify_file",
    #  "path": "...", "content": "..."}
    setup_actions: list[dict] = field(default_factory=list)

    # Tags for filtering/grouping
    tags: list[str] = field(default_factory=list)

    # --- Serialization ---

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> TaskTemplate:
        strict = CheckerSpec(**d["strict_checker"]) if isinstance(d.get("strict_checker"), dict) else d.get("strict_checker")
        lenient = CheckerSpec(**d["lenient_checker"]) if isinstance(d.get("lenient_checker"), dict) else d.get("lenient_checker")
        return cls(
            name=d["name"],
            task_type=d["task_type"],
            difficulty=d["difficulty"],
            description=d["description"],
            instruction=d["instruction"],
            strict_checker=strict,
            lenient_checker=lenient,
            setup_actions=d.get("setup_actions", []),
            tags=d.get("tags", []),
        )

    @classmethod
    def from_json(cls, s: str) -> TaskTemplate:
        return cls.from_dict(json.loads(s))

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> TaskTemplate:
        return cls.from_json(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TemplateError(Exception):
    """Raised when a TaskTemplate fails validation."""


def validate_template(template: TaskTemplate) -> None:
    """Validate a TaskTemplate instance.

    Raises TemplateError if any required field is missing or invalid.
    """
    errors: list[str] = []

    if not template.name:
        errors.append("name is empty")

    if template.task_type not in VALID_TASK_TYPES:
        errors.append(
            f"task_type '{template.task_type}' not in {sorted(VALID_TASK_TYPES)}"
        )

    if template.difficulty not in VALID_DIFFICULTIES:
        errors.append(
            f"difficulty '{template.difficulty}' not in {sorted(VALID_DIFFICULTIES)}"
        )

    if not template.description:
        errors.append("description is empty")

    if not template.instruction:
        errors.append("instruction is empty")

    # Validate checkers
    for label, checker in [
        ("strict_checker", template.strict_checker),
        ("lenient_checker", template.lenient_checker),
    ]:
        if checker is None:
            errors.append(f"{label} is None")
            continue
        if checker.checker_type not in VALID_CHECKER_TYPES:
            errors.append(
                f"{label}.checker_type '{checker.checker_type}' not in "
                f"{sorted(VALID_CHECKER_TYPES)}"
            )
        if not checker.criteria:
            errors.append(f"{label}.criteria is empty")

        # Type-specific validation
        if checker.checker_type == "file_exists" and not checker.target_file:
            errors.append(f"{label}: file_exists checker requires target_file")
        if checker.checker_type == "symbol_exists" and not checker.target_symbol:
            errors.append(f"{label}: symbol_exists checker requires target_symbol")
        if checker.checker_type == "content_contains" and not checker.target_string:
            errors.append(f"{label}: content_contains checker requires target_string")
        if checker.checker_type == "llm_judge" and not checker.llm_prompt:
            errors.append(f"{label}: llm_judge checker requires llm_prompt")

    # Validate setup_actions
    valid_actions = {"write_file", "delete_file", "modify_file"}
    for i, action in enumerate(template.setup_actions):
        if not isinstance(action, dict):
            errors.append(f"setup_actions[{i}] is not a dict")
            continue
        if action.get("action") not in valid_actions:
            errors.append(
                f"setup_actions[{i}].action '{action.get('action')}' "
                f"not in {sorted(valid_actions)}"
            )
        if not action.get("path"):
            errors.append(f"setup_actions[{i}].path is empty")
        # write_file and modify_file require content; delete_file does not
        act = action.get("action")
        if act in ("write_file", "modify_file") and not action.get("content"):
            errors.append(
                f"setup_actions[{i}]: {act} requires content"
            )

    if errors:
        raise TemplateError(
            f"TaskTemplate '{template.name}' has {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
