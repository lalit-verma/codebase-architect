"""Benchmark task templates (milestone A7).

Five parameterized task templates covering the Phase A benchmark suite.
Each template uses placeholders filled at runtime from a repo's
structure.json.

Documented placeholders (all templates use a subset of these):
  {most_common_pattern}  — name of the most-used code pattern
  {pattern_example_file} — example file for that pattern
  {pattern_directory}    — directory where pattern instances live
  {pattern_test_dir}     — directory where tests for that pattern live
  {file_path}            — a specific file to operate on
  {function_name}        — a specific function to modify/fix
  {bug_description}      — description of the planted bug
  {subsystem_name}       — a subsystem name from the architecture map
  {subsystem_paths}      — key paths belonging to a subsystem
  {repo_description}     — short description of what the repo does
"""

from __future__ import annotations

from pensieve.benchmark.template import CheckerSpec, TaskTemplate

# ---------------------------------------------------------------------------
# Placeholder documentation — used by the runner to validate that all
# placeholders can be filled from structure.json
# ---------------------------------------------------------------------------

DOCUMENTED_PLACEHOLDERS: frozenset[str] = frozenset({
    "most_common_pattern",
    "pattern_example_file",
    "pattern_directory",
    "pattern_test_dir",
    "new_file_path",     # concrete path for the new file (computed by runner)
    "test_file_path",    # concrete path for the test file (computed by runner)
    "file_path",
    "function_name",
    "bug_description",
    "subsystem_name",
    "subsystem_paths",
    "repo_description",
})

# ---------------------------------------------------------------------------
# Task templates
# ---------------------------------------------------------------------------

ADD_HANDLER = TaskTemplate(
    name="add_handler",
    task_type="add_handler",
    difficulty="easy",
    description=(
        "Create a new instance of the most common file pattern in the "
        "repo (e.g., a new handler, endpoint, model, or component). "
        "Tests whether the agent follows established conventions."
    ),
    instruction=(
        "Create a new file following the '{most_common_pattern}' pattern "
        "in this repository. Use '{pattern_example_file}' as a reference. "
        "The new file should be placed at '{new_file_path}' and "
        "follow the same structure, naming conventions, and registration "
        "steps as the example. Include all necessary imports, "
        "boilerplate, and registration."
    ),
    strict_checker=CheckerSpec(
        checker_type="file_exists",
        criteria=(
            "The file '{new_file_path}' exists. This only verifies "
            "creation, not correctness — correctness is checked by "
            "the lenient checker."
        ),
        target_file="{new_file_path}",
    ),
    lenient_checker=CheckerSpec(
        checker_type="llm_judge",
        criteria=(
            "The new file follows the '{most_common_pattern}' pattern: "
            "same structure, imports, boilerplate, and conventions as "
            "'{pattern_example_file}'."
        ),
        llm_prompt=(
            "Compare the newly created file at '{new_file_path}' against "
            "'{pattern_example_file}'. Does it follow the same pattern "
            "(structure, imports, naming, registration)? Answer PASS if "
            "the pattern is followed correctly, FAIL if significant "
            "deviations exist. Minor style differences are acceptable."
        ),
    ),
    tags=["pattern", "convention", "easy"],
)

ADD_TEST = TaskTemplate(
    name="add_test",
    task_type="add_test",
    difficulty="easy",
    description=(
        "Write a test file for an existing source file. Tests whether "
        "the agent follows the repo's test conventions (test framework, "
        "directory structure, naming, assertion style)."
    ),
    instruction=(
        "Write tests for the file '{file_path}'. Place the test file at "
        "'{test_file_path}'. Cover the main exported functions/methods. "
        "Use the same test framework and assertion style as other tests "
        "in this repo."
    ),
    strict_checker=CheckerSpec(
        checker_type="file_exists",
        criteria=(
            "The file '{test_file_path}' exists. This only verifies "
            "creation, not test quality — quality is checked by "
            "the lenient checker."
        ),
        target_file="{test_file_path}",
    ),
    lenient_checker=CheckerSpec(
        checker_type="llm_judge",
        criteria=(
            "The test file covers the main functions/methods in "
            "'{file_path}', uses the repo's test framework, and follows "
            "the repo's test conventions."
        ),
        llm_prompt=(
            "Review the test file at '{test_file_path}' written for "
            "'{file_path}'. Does it: (1) cover the main exported "
            "functions, (2) use the correct test framework for this repo, "
            "(3) follow the repo's naming and structural conventions? "
            "Answer PASS or FAIL with a brief explanation."
        ),
    ),
    tags=["test", "convention", "easy"],
)

BUG_FIX_LOCALIZED = TaskTemplate(
    name="bug_fix_localized",
    task_type="bug_fix",
    difficulty="easy",
    description=(
        "Fix a localized bug in a single function. Tests whether the "
        "agent can read a function, understand the bug, and apply a "
        "correct fix without side effects."
    ),
    instruction=(
        "There is a bug in the function '{function_name}' in file "
        "'{file_path}'. The bug: {bug_description}. Fix the bug. "
        "Do not change the function's signature or any other function "
        "in the file. Only modify what is necessary to fix the "
        "described issue."
    ),
    strict_checker=CheckerSpec(
        checker_type="content_contains",
        criteria=(
            "The file '{file_path}' still contains the function "
            "'{function_name}' (verifies the agent edited the right "
            "file and didn't delete the function). This is a minimal "
            "sanity check — correctness of the fix is verified by the "
            "lenient checker."
        ),
        target_string="{function_name}",
        target_file="{file_path}",
    ),
    lenient_checker=CheckerSpec(
        checker_type="llm_judge",
        criteria=(
            "The bug described as '{bug_description}' in "
            "'{function_name}' has been fixed correctly without "
            "introducing new issues or unnecessary changes."
        ),
        llm_prompt=(
            "The function '{function_name}' in '{file_path}' had this "
            "bug: {bug_description}. Review the diff. Was the bug fixed "
            "correctly? Were any unnecessary changes made? Answer PASS "
            "if the fix is correct and minimal, FAIL otherwise."
        ),
    ),
    setup_actions=[
        {
            "action": "modify_file",
            "path": "{file_path}",
            "content": "# {bug_description} — planted by benchmark runner",
        },
    ],
    tags=["bug_fix", "localized", "easy"],
)

FIND_OWNER = TaskTemplate(
    name="find_owner",
    task_type="find_owner",
    difficulty="medium",
    description=(
        "Identify which subsystem owns a given file and what conventions "
        "apply. Tests whether the agent can navigate the architecture "
        "map and understand subsystem boundaries."
    ),
    instruction=(
        "Answer these questions about the file '{file_path}':\n"
        "1. Which subsystem or module does this file belong to?\n"
        "2. What are the key conventions for this subsystem "
        "(naming, error handling, test structure)?\n"
        "3. If I wanted to add a new file to the same subsystem, what "
        "pattern should I follow?\n"
        "4. What other files in this subsystem are closely related?\n"
        "Be specific — cite file paths and conventions from this repo."
    ),
    strict_checker=CheckerSpec(
        checker_type="content_contains",
        criteria=(
            "The response mentions the subsystem name "
            "'{subsystem_name}'. This is a minimal sanity check — "
            "full correctness (file paths, conventions, guidance) is "
            "verified by the lenient checker."
        ),
        target_string="{subsystem_name}",
    ),
    lenient_checker=CheckerSpec(
        checker_type="llm_judge",
        criteria=(
            "The response correctly identifies the subsystem, cites "
            "relevant file paths and conventions, and provides "
            "actionable guidance for adding new files."
        ),
        llm_prompt=(
            "The file '{file_path}' belongs to the '{subsystem_name}' "
            "subsystem with paths: {subsystem_paths}. Review the agent's "
            "response. Did it: (1) correctly identify the subsystem, "
            "(2) cite real file paths from this repo, (3) describe "
            "real conventions, (4) provide useful guidance for adding "
            "new files? Answer PASS or FAIL."
        ),
    ),
    tags=["navigation", "architecture", "medium"],
)

COLD_NAVIGATION = TaskTemplate(
    name="cold_navigation",
    task_type="navigation",
    difficulty="medium",
    description=(
        "Answer an open-ended question about the repo's architecture "
        "requiring exploration of multiple files. Tests whether the "
        "agent can orient itself and provide a coherent answer."
    ),
    instruction=(
        "This is a {repo_description}. Answer the following:\n"
        "1. What are the main subsystems or modules in this repo?\n"
        "2. How do they communicate with each other (imports, APIs, "
        "shared types)?\n"
        "3. Where would I start if I wanted to understand the main "
        "flow of this application?\n"
        "4. Are there any patterns or conventions that are "
        "consistently followed across the codebase?\n"
        "Be specific — cite file paths, not just abstract descriptions."
    ),
    strict_checker=CheckerSpec(
        checker_type="content_contains",
        criteria=(
            "The response mentions at least one known file path from "
            "the repo ('{file_path}'). This is a minimal sanity check "
            "that the agent looked at the repo — architecture quality "
            "is verified by the lenient checker."
        ),
        target_string="{file_path}",
    ),
    lenient_checker=CheckerSpec(
        checker_type="llm_judge",
        criteria=(
            "The response demonstrates genuine understanding of the "
            "repo's architecture, cites multiple real file paths, and "
            "provides a coherent map of the codebase."
        ),
        llm_prompt=(
            "This repo is a {repo_description}. The agent was asked to "
            "describe its architecture. Review the response. Did it: "
            "(1) identify real subsystems with correct file paths, "
            "(2) describe how they connect, (3) point to a reasonable "
            "starting point for understanding the codebase, (4) cite "
            "actual patterns/conventions? Answer PASS or FAIL."
        ),
    ),
    tags=["navigation", "architecture", "exploration", "medium"],
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_TEMPLATES: list[TaskTemplate] = [
    ADD_HANDLER,
    ADD_TEST,
    BUG_FIX_LOCALIZED,
    FIND_OWNER,
    COLD_NAVIGATION,
]


def get_all_templates() -> list[TaskTemplate]:
    """Return all registered benchmark task templates."""
    return list(ALL_TEMPLATES)


def get_template_by_name(name: str) -> TaskTemplate | None:
    """Look up a template by name."""
    for t in ALL_TEMPLATES:
        if t.name == name:
            return t
    return None
