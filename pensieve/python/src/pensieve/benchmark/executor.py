"""Claude Code subprocess executor for benchmark runs.

Invokes Claude Code in non-interactive print mode (`claude -p`) with
JSON output format to get structured results including token counts,
cost, and timing.

The executor is pluggable: `create_executor()` returns an instance
that implements the Executor protocol from `runner.py`. Configuration
is via constructor arguments, not environment variables (explicit
over implicit).

Usage from the CLI:
    from pensieve.benchmark.executor import create_executor
    executor = create_executor()

Usage with custom settings:
    executor = ClaudeCodeExecutor(model="haiku", max_budget_usd=1.0)
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Literal


class ClaudeCodeExecutor:
    """Executor that invokes Claude Code as a subprocess.

    Each call to execute() runs `claude -p --output-format json` in a
    subprocess with cwd set to the target repo. The JSON output is
    parsed for response text, token counts, cost, and timing.
    """

    def __init__(
        self,
        model: str | None = None,
        max_budget_usd: float | None = None,
        permission_mode: str = "auto",
        timeout_seconds: int = 300,
        extra_args: list[str] | None = None,
    ) -> None:
        """Configure the executor.

        Args:
            model: Model to use (e.g., "sonnet", "haiku", "opus").
                None uses Claude Code's default.
            max_budget_usd: Per-task spend cap. None for no limit.
            permission_mode: Permission mode for the subprocess.
                "auto" allows tool use without prompting.
            timeout_seconds: Subprocess timeout per task.
            extra_args: Additional CLI args passed to claude.
        """
        self._model = model
        self._max_budget_usd = max_budget_usd
        self._permission_mode = permission_mode
        self._timeout = timeout_seconds
        self._extra_args = extra_args or []

    def execute(
        self,
        instruction: str,
        repo_root: Path,
        mode: Literal["baseline", "with_framework"],
    ) -> dict:
        """Run an instruction via Claude Code subprocess.

        Args:
            instruction: The task instruction to send.
            repo_root: Working directory for the subprocess.
            mode: Benchmark mode (used for logging, not invocation).

        Returns:
            Dict with: response, tokens, cost_usd, time_seconds.
        """
        cmd = self._build_command(instruction)

        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            return {
                "response": "",
                "tokens": 0,
                "cost_usd": 0.0,
                "time_seconds": round(elapsed, 3),
                "error": f"Subprocess timed out after {self._timeout}s",
            }
        except FileNotFoundError:
            return {
                "response": "",
                "tokens": 0,
                "cost_usd": 0.0,
                "time_seconds": 0.0,
                "error": (
                    "Claude Code CLI not found. Ensure 'claude' is "
                    "installed and on PATH."
                ),
            }

        elapsed = round(time.monotonic() - start, 3)

        # Parse JSON output
        output = result.stdout.strip()
        if not output:
            return {
                "response": result.stderr.strip() or "No output from Claude Code",
                "tokens": 0,
                "cost_usd": 0.0,
                "time_seconds": elapsed,
                "error": f"Empty stdout. Exit code: {result.returncode}",
            }

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return {
                "response": output[:500],
                "tokens": 0,
                "cost_usd": 0.0,
                "time_seconds": elapsed,
                "error": "Failed to parse JSON output from Claude Code",
            }

        # Non-zero exit code = failed invocation, even if JSON is parseable.
        # Preserve whatever data exists but mark as error.
        if result.returncode != 0:
            error_msg = data.get("result", result.stderr.strip() or "Unknown error")
            return {
                "response": error_msg if isinstance(error_msg, str) else str(error_msg),
                "tokens": 0,
                "cost_usd": data.get("total_cost_usd", 0.0),
                "time_seconds": elapsed,
                "error": (
                    f"Claude Code exited with code {result.returncode}. "
                    f"stderr: {result.stderr.strip()[:200]}"
                ),
            }

        # Check for error in Claude Code response
        if data.get("is_error"):
            error_msg = data.get("result", "Unknown error")
            return {
                "response": error_msg if isinstance(error_msg, str) else str(error_msg),
                "tokens": 0,
                "cost_usd": data.get("total_cost_usd", 0.0),
                "time_seconds": elapsed,
                "error": f"Claude Code error: {error_msg}",
            }

        # Extract metrics from JSON output
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_creation = usage.get("cache_creation_input_tokens", 0)
        total_tokens = input_tokens + output_tokens + cache_read + cache_creation

        result_dict = {
            "response": data.get("result", ""),
            "tokens": total_tokens,
            "cost_usd": data.get("total_cost_usd", 0.0),
            "time_seconds": data.get("duration_ms", elapsed * 1000) / 1000,
        }

        # Flag suspicious responses: Claude Code returned "success" but
        # with no tokens and no cost — likely an internal timeout or
        # session limit, not a real completion.
        if total_tokens == 0 and data.get("total_cost_usd", 0.0) == 0.0:
            stop = data.get("stop_reason", "unknown")
            terminal = data.get("terminal_reason", "unknown")
            result_dict["error"] = (
                f"Claude Code returned 0 tokens/0 cost "
                f"(stop_reason={stop}, terminal_reason={terminal})"
            )

        return result_dict

    def _build_command(self, instruction: str) -> list[str]:
        """Build the claude CLI command."""
        cmd = [
            "claude",
            "-p",
            "--output-format", "json",
            "--permission-mode", self._permission_mode,
            "--no-session-persistence",
        ]

        if self._model:
            cmd.extend(["--model", self._model])

        if self._max_budget_usd is not None:
            cmd.extend(["--max-budget-usd", str(self._max_budget_usd)])

        cmd.extend(self._extra_args)
        cmd.append(instruction)

        return cmd


def create_executor(
    model: str | None = None,
    max_budget_usd: float | None = None,
    permission_mode: str = "auto",
    timeout_seconds: int = 300,
    extra_args: list[str] | None = None,
) -> ClaudeCodeExecutor:
    """Factory function for the CLI to import.

    This is the entry point that `cli.py` calls:
        from pensieve.benchmark.executor import create_executor
        executor = create_executor()
    """
    return ClaudeCodeExecutor(
        model=model,
        max_budget_usd=max_budget_usd,
        permission_mode=permission_mode,
        timeout_seconds=timeout_seconds,
        extra_args=extra_args,
    )
