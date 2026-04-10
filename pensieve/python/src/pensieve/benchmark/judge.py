"""LLM judge for benchmark task evaluation.

Calls Claude Code to evaluate whether the agent's output satisfies
the lenient checker criteria. Returns a pass/fail verdict and a
quality score (0-10).

Uses `claude -p --output-format json --json-schema` for structured
output parsing. Defaults to sonnet model for cost efficiency — the
judge doesn't need the most capable model.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


_JUDGE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["PASS", "FAIL"],
            "description": "Whether the agent's output satisfies the criteria.",
        },
        "quality": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": (
                "Quality score from 0 (completely wrong) to 10 (perfect). "
                "5 = minimally acceptable. 7 = good. 9+ = excellent."
            ),
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the verdict and score.",
        },
    },
    "required": ["verdict", "quality", "reasoning"],
})


@dataclass
class JudgeResult:
    """Result of an LLM judge evaluation."""

    lenient_pass: bool
    quality_score: float  # 0.0 - 10.0
    reasoning: str
    error: str | None = None


def judge_task(
    llm_prompt: str,
    agent_response: str,
    model: str = "sonnet",
    timeout_seconds: int = 60,
) -> JudgeResult:
    """Evaluate a task result using Claude as a judge.

    Args:
        llm_prompt: The filled evaluation prompt from the checker spec.
        agent_response: The agent's text response to evaluate.
        model: Model to use for judging (default: sonnet for cost).
        timeout_seconds: Subprocess timeout.

    Returns:
        JudgeResult with pass/fail, quality score, and reasoning.
    """
    system_prompt = (
        "You are a benchmark evaluator for a coding agent. "
        "Evaluate the agent's output against the criteria below. "
        "Be fair but rigorous. A PASS means the agent meaningfully "
        "addressed the task. Minor imperfections are acceptable for PASS. "
        "A FAIL means the agent missed the core requirement."
    )

    user_prompt = (
        f"## Evaluation criteria\n\n{llm_prompt}\n\n"
        f"## Agent's response\n\n{agent_response}\n\n"
        f"Evaluate the response against the criteria."
    )

    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", system_prompt,
        "--json-schema", _JUDGE_SCHEMA,
        user_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=f"Judge timed out after {timeout_seconds}s",
        )
    except FileNotFoundError:
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error="Claude Code CLI not found",
        )

    output = result.stdout.strip()
    if not output:
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=f"Empty stdout from judge. stderr: {result.stderr[:200]}",
        )

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=f"Failed to parse judge JSON: {output[:200]}",
        )

    # Non-zero exit code = failed invocation, even if JSON is parseable.
    if result.returncode != 0:
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=(
                f"Judge exited with code {result.returncode}. "
                f"stderr: {result.stderr.strip()[:200]}"
            ),
        )

    if data.get("is_error"):
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=f"Judge error: {data.get('result', 'unknown')}",
        )

    # Extract structured output
    structured = data.get("structured_output") or data.get("result", {})
    if isinstance(structured, str):
        # result field is a string, not structured — try parsing it
        try:
            structured = json.loads(structured)
        except (json.JSONDecodeError, TypeError):
            return JudgeResult(
                lenient_pass=False,
                quality_score=0.0,
                reasoning=structured[:200] if structured else "",
                error="Judge returned unstructured response",
            )

    if not isinstance(structured, dict):
        return JudgeResult(
            lenient_pass=False,
            quality_score=0.0,
            reasoning="",
            error=f"Judge structured output is not a dict: {type(structured).__name__}",
        )

    verdict = structured.get("verdict", "FAIL")
    reasoning = structured.get("reasoning", "")

    # Safely coerce quality to float — malformed values degrade, not crash
    raw_quality = structured.get("quality", 0.0)
    try:
        quality = max(0.0, min(10.0, float(raw_quality)))
    except (TypeError, ValueError):
        quality = 0.0
        reasoning = f"[judge quality malformed: {raw_quality!r}] {reasoning}"

    return JudgeResult(
        lenient_pass=(verdict == "PASS"),
        quality_score=quality,
        reasoning=reasoning,
    )
