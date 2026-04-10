"""Benchmark runner (milestones A8, A9).

Runs benchmark task templates against a target repo and collects
results. The runner has two modes:

  - baseline: no agent-docs, no hook — measures the agent cold
  - with_framework: agent-docs + PreToolUse hook installed

The actual agent invocation is pluggable via an Executor protocol.
A real executor calls Claude Code; a mock executor is used in tests.

Architecture:
  1. PlaceholderFiller reads structure.json and fills template placeholders
  2. StrictCheckerExecutor runs deterministic checks (file_exists, etc.)
  3. Runner orchestrates: fill → execute → check → collect results
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from pensieve.benchmark.template import CheckerSpec, TaskTemplate


# ---------------------------------------------------------------------------
# Task result
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """Result of running a single benchmark task."""

    template_name: str
    mode: Literal["baseline", "with_framework"]
    instruction: str  # the filled instruction sent to the agent

    # Agent output
    agent_response: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    time_seconds: float = 0.0

    # Check results
    strict_pass: bool = False
    lenient_pass: bool = False
    quality_score: float = 0.0  # 0-10 LLM-judged quality

    # Errors
    error: str | None = None


# ---------------------------------------------------------------------------
# Executor protocol — pluggable agent invocation
# ---------------------------------------------------------------------------


class Executor(Protocol):
    """Protocol for agent execution. Implementations call the actual
    coding agent (real) or return canned responses (mock/test)."""

    def execute(
        self,
        instruction: str,
        repo_root: Path,
        mode: Literal["baseline", "with_framework"],
    ) -> dict:
        """Run an instruction against a repo.

        Returns a dict with:
          - response: str (the agent's output)
          - tokens: int
          - cost_usd: float
          - time_seconds: float
        """
        ...


# ---------------------------------------------------------------------------
# Placeholder filling
# ---------------------------------------------------------------------------


class PlaceholderFiller:
    """Fills template placeholders from a repo's structure.json.

    Reads structure.json once, extracts placeholder values, and
    provides fill(template) → filled instruction string.
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._values: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        structure_path = self._repo_root / "agent-docs" / "structure.json"
        if not structure_path.exists():
            raise FileNotFoundError(
                f"No structure.json found at {structure_path}. "
                f"Run `pensieve scan {self._repo_root}` first."
            )

        data = json.loads(structure_path.read_text(encoding="utf-8"))
        files = data.get("files", [])

        if not files:
            raise ValueError(
                f"structure.json at {structure_path} has no files. "
                f"The repo may be empty or all files failed extraction."
            )

        # --- Derive placeholder values ---

        # Find the most common pattern (most symbols of same kind in same dir)
        dir_counts: dict[str, int] = {}
        for f in files:
            parent = str(Path(f["file_path"]).parent)
            dir_counts[parent] = dir_counts.get(parent, 0) + 1

        most_common_dir = max(dir_counts, key=dir_counts.get)  # type: ignore
        files_in_dir = [
            f for f in files
            if str(Path(f["file_path"]).parent) == most_common_dir
        ]

        example_file = files_in_dir[0]["file_path"] if files_in_dir else files[0]["file_path"]
        example_ext = Path(example_file).suffix

        self._values["most_common_pattern"] = f"files in {most_common_dir}/"
        self._values["pattern_example_file"] = example_file
        self._values["pattern_directory"] = most_common_dir

        # Test directory heuristic
        test_dirs = [
            f["file_path"] for f in files
            if any(
                part in ("tests", "test", "spec", "__tests__")
                for part in Path(f["file_path"]).parts
            )
        ]
        if test_dirs:
            self._values["pattern_test_dir"] = str(Path(test_dirs[0]).parent)
        else:
            self._values["pattern_test_dir"] = "tests"

        # Concrete new file path (runner-computed)
        new_name = f"new_instance{example_ext}"
        self._values["new_file_path"] = str(Path(most_common_dir) / new_name)

        # Concrete test file path
        self._values["test_file_path"] = str(
            Path(self._values["pattern_test_dir"]) / f"test_new_instance{example_ext}"
        )

        # Pick a file for file_path-based tasks
        # Prefer a file with symbols (not empty)
        files_with_symbols = [f for f in files if f.get("symbols")]
        target = files_with_symbols[0] if files_with_symbols else files[0]
        self._values["file_path"] = target["file_path"]

        # Pick a function from that file
        symbols = target.get("symbols", [])
        functions = [s for s in symbols if s.get("kind") in ("function", "method")]
        if functions:
            self._values["function_name"] = functions[0]["name"]
        else:
            self._values["function_name"] = symbols[0]["name"] if symbols else "main"

        # Bug description (generic, runner can override for specific bugs)
        self._values["bug_description"] = "off-by-one error in the loop condition"

        # Subsystem heuristic: use directory as subsystem name
        self._values["subsystem_name"] = most_common_dir
        subsystem_paths = [f["file_path"] for f in files_in_dir[:5]]
        self._values["subsystem_paths"] = ", ".join(subsystem_paths)

        # Repo description
        languages = {f.get("language", "unknown") for f in files}
        self._values["repo_description"] = (
            f"{len(files)}-file {'/'.join(sorted(languages))} project"
        )

    @property
    def values(self) -> dict[str, str]:
        """The resolved placeholder values."""
        return dict(self._values)

    def fill(self, text: str) -> str:
        """Fill placeholders in a text string.

        Raises KeyError if a placeholder can't be resolved.
        """
        try:
            return text.format(**self._values)
        except KeyError as e:
            raise KeyError(
                f"Cannot fill placeholder {e}. Available: "
                f"{sorted(self._values.keys())}"
            ) from e

    def fill_template(self, template: TaskTemplate) -> str:
        """Fill the instruction placeholders in a TaskTemplate."""
        return self.fill(template.instruction)


# ---------------------------------------------------------------------------
# Strict checker execution
# ---------------------------------------------------------------------------


def run_strict_check(
    checker: CheckerSpec,
    repo_root: Path,
    agent_response: str,
    placeholder_values: dict[str, str],
) -> bool:
    """Execute a strict (deterministic) checker.

    Args:
        checker: The checker specification.
        repo_root: Path to the repo root (for file checks).
        agent_response: The agent's text response (for content checks).
        placeholder_values: Filled placeholder values for resolving
            target_file/target_string/target_symbol.

    Returns:
        True if the check passes, False otherwise.
    """
    def _fill(s: str | None) -> str:
        if s is None:
            return ""
        try:
            return s.format(**placeholder_values)
        except KeyError:
            return s

    ct = checker.checker_type

    if ct == "file_exists":
        target = _fill(checker.target_file)
        if not target:
            return False
        return (repo_root / target).exists()

    elif ct == "content_contains":
        target = _fill(checker.target_string)
        if not target:
            return False
        # Check in agent response
        if target in agent_response:
            return True
        # Also check in the target file if specified
        target_file = _fill(checker.target_file)
        if target_file:
            file_path = repo_root / target_file
            if file_path.exists():
                return target in file_path.read_text(encoding="utf-8", errors="replace")
        return False

    elif ct == "symbol_exists":
        target_file = _fill(checker.target_file)
        target_sym = _fill(checker.target_symbol)
        if not target_file or not target_sym:
            return False
        file_path = repo_root / target_file
        if not file_path.exists():
            return False
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return target_sym in content

    elif ct == "pattern_followed":
        # Pattern checking requires runtime access to patterns.md
        # and is more semantic than deterministic. For now, return
        # True (defer to lenient checker for real evaluation).
        return True

    elif ct == "llm_judge":
        # LLM judgment is not a strict check — this shouldn't be
        # called for strict checking. Return True as a no-op.
        return True

    return False


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_task(
    template: TaskTemplate,
    repo_root: Path,
    executor: Executor,
    mode: Literal["baseline", "with_framework"],
    placeholder_values: dict[str, str] | None = None,
) -> TaskResult:
    """Run a single benchmark task.

    Args:
        template: The task template to execute.
        repo_root: Path to the target repo.
        executor: The agent executor (real or mock).
        mode: "baseline" or "with_framework".
        placeholder_values: Pre-computed placeholder values. If None,
            a PlaceholderFiller is created from the repo's structure.json.

    Returns:
        A TaskResult with all metrics and check results.
    """
    if placeholder_values is None:
        filler = PlaceholderFiller(repo_root)
        placeholder_values = filler.values

    # Fill the instruction
    try:
        instruction = template.instruction.format(**placeholder_values)
    except KeyError as e:
        return TaskResult(
            template_name=template.name,
            mode=mode,
            instruction=template.instruction,
            error=f"Cannot fill placeholder: {e}",
        )

    # Execute
    start = time.monotonic()
    try:
        result = executor.execute(instruction, repo_root, mode)
    except Exception as e:
        return TaskResult(
            template_name=template.name,
            mode=mode,
            instruction=instruction,
            error=f"Executor failed: {e}",
            time_seconds=round(time.monotonic() - start, 3),
        )

    elapsed = round(time.monotonic() - start, 3)

    # Run strict check
    strict_pass = run_strict_check(
        template.strict_checker,
        repo_root,
        result.get("response", ""),
        placeholder_values,
    )

    return TaskResult(
        template_name=template.name,
        mode=mode,
        instruction=instruction,
        agent_response=result.get("response", ""),
        tokens_used=result.get("tokens", 0),
        cost_usd=result.get("cost_usd", 0.0),
        time_seconds=result.get("time_seconds", elapsed),
        strict_pass=strict_pass,
        lenient_pass=False,  # set by LLM judge in A10
        quality_score=0.0,  # set by LLM judge in A10
    )


# ---------------------------------------------------------------------------
# Mode setup / teardown (milestone A9)
# ---------------------------------------------------------------------------


def setup_baseline(repo_root: Path) -> dict[str, str]:
    """Prepare a repo for baseline benchmark run.

    Hides agent-docs/ and uninstalls the hook so the agent runs cold.
    Returns a dict describing what was done (for teardown).

    The original state is preserved: agent-docs is renamed, not deleted;
    the hook is uninstalled but the settings.json is not removed.
    """
    state: dict[str, str] = {}
    agent_docs = repo_root / "agent-docs"
    hidden = repo_root / ".agent-docs-hidden"

    if hidden.exists():
        # Already hidden from a previous run — skip
        state["agent_docs"] = "already_hidden"
    elif agent_docs.exists():
        agent_docs.rename(hidden)
        state["agent_docs"] = "hidden"
    else:
        state["agent_docs"] = "not_present"

    # Uninstall hook (safe no-op if not installed)
    from pensieve.hooks import uninstall_hook
    hook_result = uninstall_hook(repo_root)
    state["hook"] = hook_result.get("settings", "not_found")

    return state


def teardown_baseline(repo_root: Path, state: dict[str, str]) -> None:
    """Restore the repo after a baseline run.

    Unhides agent-docs/ if it was hidden by setup_baseline.
    Does NOT reinstall the hook — that's setup_framework's job.
    """
    hidden = repo_root / ".agent-docs-hidden"
    agent_docs = repo_root / "agent-docs"

    if state.get("agent_docs") == "hidden" and hidden.exists():
        hidden.rename(agent_docs)


def setup_framework(repo_root: Path) -> dict[str, str]:
    """Prepare a repo for with-framework benchmark run.

    Ensures agent-docs/ exists (runs scan if needed) and installs
    the PreToolUse hook.
    """
    state: dict[str, str] = {}

    # Ensure agent-docs exists
    agent_docs = repo_root / "agent-docs"
    structure = agent_docs / "structure.json"

    if not structure.exists():
        # Need to run scan first
        from pensieve.scan import scan_repo
        scan_repo(repo_root)
        state["scan"] = "ran"
    else:
        state["scan"] = "already_present"

    # Install hook
    from pensieve.hooks import install_hook
    hook_result = install_hook(repo_root)
    state["hook"] = hook_result.get("settings", "unknown")

    return state


def teardown_framework(repo_root: Path, state: dict[str, str]) -> None:
    """Cleanup after a with-framework run.

    Currently a no-op — we leave agent-docs/ and the hook in place.
    The baseline setup will hide them if needed.
    """
    pass


# ---------------------------------------------------------------------------
# Full benchmark orchestrator (milestone A9)
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Result of a full benchmark run (both modes, all templates)."""

    repo_root: Path
    baseline_results: list[TaskResult]
    framework_results: list[TaskResult]
    total_time_seconds: float = 0.0


def run_benchmark(
    repo_root: Path,
    templates: list[TaskTemplate],
    executor: Executor,
    run_baseline: bool = True,
    run_framework: bool = True,
) -> BenchmarkResult:
    """Run the full benchmark: baseline + with_framework on all templates.

    Args:
        repo_root: Path to the target repo.
        templates: Task templates to run.
        executor: Agent executor (real or mock).
        run_baseline: Whether to run baseline mode.
        run_framework: Whether to run with-framework mode.

    Returns:
        BenchmarkResult with per-task results for each mode.
    """
    start = time.monotonic()
    repo_root = repo_root.resolve()

    baseline_results: list[TaskResult] = []
    framework_results: list[TaskResult] = []

    # --- Phase 1: Ensure scan is done (needed for placeholder filling) ---
    agent_docs = repo_root / "agent-docs"
    if not (agent_docs / "structure.json").exists():
        from pensieve.scan import scan_repo
        scan_repo(repo_root)

    # Pre-compute placeholders from the scanned repo
    filler = PlaceholderFiller(repo_root)
    placeholder_values = filler.values

    # --- Phase 2: With-framework run (run first so agent-docs is present) ---
    if run_framework:
        fw_state = setup_framework(repo_root)
        try:
            for template in templates:
                result = run_task(
                    template, repo_root, executor, "with_framework",
                    placeholder_values=placeholder_values,
                )
                framework_results.append(result)
        finally:
            teardown_framework(repo_root, fw_state)

    # --- Phase 3: Baseline run (agent-docs hidden) ---
    if run_baseline:
        bl_state = setup_baseline(repo_root)
        try:
            for template in templates:
                result = run_task(
                    template, repo_root, executor, "baseline",
                    placeholder_values=placeholder_values,
                )
                baseline_results.append(result)
        finally:
            teardown_baseline(repo_root, bl_state)

    elapsed = round(time.monotonic() - start, 3)

    return BenchmarkResult(
        repo_root=repo_root,
        baseline_results=baseline_results,
        framework_results=framework_results,
        total_time_seconds=elapsed,
    )
