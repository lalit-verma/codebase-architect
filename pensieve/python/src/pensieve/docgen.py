"""Phase B Layer 2: v1 prompts + Layer 1 evidence, programmatic execution.

Uses the actual v1 prompt files from claude-code/commands/ as the
generation prompts, injected with structural data from Layer 1
(structure.json + graph.json). Orchestrated programmatically via
`claude -p` with checkpointing, parallelism, and error handling.

v1 prompts handle: what to write, what structure, what quality bar.
Layer 1 handles: evidence (symbols, imports, call edges, graph).
This module handles: orchestration, file I/O, error recovery.

Pipeline:
  Stage 2: analyze-discover prompt + structural data → subsystem map +
           system-overview.md + .analysis-state.md
  Stage 4: analyze-deep-dive prompt + structural data → subsystems/*.md
  Stage 5: analyze-synthesize prompt → all top-level artifacts
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pensieve.context import (
    SubsystemProposal,
    FileSelection,
    RepoProfile,
    SubsystemMap,
    build_subsystem_brief,
)


# ---------------------------------------------------------------------------
# Locate v1 prompt files
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    """Find the codebase-analysis-skill repo root (where v1 prompts live)."""
    # Walk up from this file to find the repo root
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "claude-code" / "commands").is_dir():
            return parent
    # Fallback: try common locations
    for candidate in [
        Path.home() / "Desktop" / "tinkering" / "codebase-analysis-skill",
    ]:
        if (candidate / "claude-code" / "commands").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find codebase-analysis-skill repo root with "
        "claude-code/commands/. V1 prompts are required."
    )


def _read_v1_prompt(name: str) -> str:
    """Read a v1 prompt file from claude-code/commands/."""
    repo_root = _find_repo_root()
    path = repo_root / "claude-code" / "commands" / name
    if not path.exists():
        raise FileNotFoundError(f"V1 prompt not found: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Shared LLM call
# ---------------------------------------------------------------------------


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "sonnet",
    timeout_seconds: int = 300,
    cwd: str | None = None,
    allow_tools: bool = False,
) -> tuple[str, str | None]:
    """Call Claude Code in text mode. Returns (output, error_or_none).

    Args:
        allow_tools: If True, enable bounded tool access
            (Read, Write, Glob, Grep only — no Bash, no broad auto).
    """
    cmd = [
        "claude", "-p",
        "--output-format", "text",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", system_prompt,
    ]
    if allow_tools:
        cmd.extend([
            "--allowedTools", "Read,Write,Glob,Grep",
            "--dangerously-skip-permissions",
        ])
    cmd.append(user_prompt)
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
    }
    if cwd:
        kwargs["cwd"] = cwd

    try:
        result = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        return ("", f"Timed out after {timeout_seconds}s")
    except FileNotFoundError:
        return ("", "Claude Code CLI not found")

    if result.returncode != 0:
        return ("", f"Exit code {result.returncode}. stderr: {result.stderr[:200]}")

    output = result.stdout.strip()
    if not output:
        return ("", f"Empty output. stderr: {result.stderr[:200]}")

    return (output, None)


# ---------------------------------------------------------------------------
# Stage 2: Discover (v1 analyze-discover prompt)
# ---------------------------------------------------------------------------


@dataclass
class DiscoverResult:
    """Output of the discover stage."""
    system_overview: str = ""
    analysis_state: str = ""
    raw_output: str = ""  # full LLM response for parsing
    error: str | None = None


def run_discover(
    repo_root: Path,
    structural_context: str,
    subsystem_map: SubsystemMap | None = None,
    repo_description: str = "",
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> DiscoverResult:
    """Run the v1 analyze-discover prompt with structural evidence.

    The v1 prompt is used as the system prompt. The structural data
    from Layer 1 is injected as additional context in the user message.

    If subsystem_map is provided, it is the authoritative subsystem
    mapping (from Python's propose_subsystems). The discover prompt
    uses it as the confirmed subsystem map rather than proposing its own.
    """
    try:
        v1_prompt = _read_v1_prompt("analyze-discover.md")
    except FileNotFoundError as e:
        return DiscoverResult(error=str(e))

    # Adapt for programmatic use: inject structural data and skip
    # interactive confirmation
    system_prompt = (
        v1_prompt.replace("$ARGUMENTS", repo_description or "Analyze this repository.") +
        "\n\n## IMPORTANT: Programmatic Execution Mode\n"
        "You are running in non-interactive mode via `claude -p`. "
        "Do NOT wait for user confirmation. Do NOT ask questions. "
        "Execute all steps and write the output directly. "
        "Skip Step 2 (Adaptive Questions) and Step 7 (Ask for Confirmation). "
        "Write the system-overview.md and .analysis-state.md content "
        "directly in your response, clearly separated by markers:\n"
        "---FILE: system-overview.md---\n"
        "---FILE: .analysis-state.md---\n"
    )

    # Build subsystem map context if provided
    smap_context = ""
    if subsystem_map and subsystem_map.subsystems:
        smap_lines = ["## Authoritative Subsystem Map (from structural analysis)\n",
                       "Use this as the confirmed subsystem mapping. Do NOT propose "
                       "a different map — this is pre-confirmed.\n"]
        for s in subsystem_map.subsystems:
            smap_lines.append(f"- **{s.name}**: {', '.join(s.directories)} — {s.role}")
        if subsystem_map.excluded:
            smap_lines.append("\nExcluded directories:")
            for e in subsystem_map.excluded:
                smap_lines.append(f"- {e['directory']}: {e['reason']}")
        smap_context = "\n".join(smap_lines) + "\n\n"

    user_prompt = (
        f"## Layer 1 Structural Evidence\n\n"
        f"The repository has been scanned by pensieve. The following "
        f"structural data is available in agent-docs/structure.json and "
        f"agent-docs/graph.json. Use this evidence for architecture "
        f"mapping — it is more complete than manual file exploration.\n\n"
        f"{structural_context}\n\n"
        f"{smap_context}"
        f"Produce the Phase 1 outputs (system-overview.md and .analysis-state.md)."
    )

    output, err = _call_llm(
        system_prompt, user_prompt,
        model=model, timeout_seconds=timeout_seconds,
        cwd=str(repo_root), allow_tools=True,
    )

    if err:
        return DiscoverResult(error=err)

    # Parse file markers from output
    system_overview = ""
    analysis_state = ""

    if "---FILE: system-overview.md---" in output:
        parts = output.split("---FILE: system-overview.md---")
        if len(parts) > 1:
            rest = parts[1]
            if "---FILE:" in rest:
                system_overview = rest[:rest.index("---FILE:")].strip()
            else:
                system_overview = rest.strip()

    if "---FILE: .analysis-state.md---" in output:
        parts = output.split("---FILE: .analysis-state.md---")
        if len(parts) > 1:
            analysis_state = parts[1].strip()

    # If markers weren't used, treat the whole output as system-overview
    if not system_overview and not analysis_state:
        system_overview = output

    return DiscoverResult(
        system_overview=system_overview,
        analysis_state=analysis_state,
        raw_output=output,
    )


# ---------------------------------------------------------------------------
# Stage 4: Per-subsystem deep-dive (v1 analyze-deep-dive prompt)
# ---------------------------------------------------------------------------


@dataclass
class SubsystemDoc:
    """Generated subsystem document."""
    subsystem_name: str
    markdown: str
    files_read: list[str]
    error: str | None = None


def generate_subsystem_doc(
    subsystem: SubsystemProposal,
    structure_path: Path,
    file_selection: FileSelection,
    repo_root: Path,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> SubsystemDoc:
    """Generate a subsystem doc using the v1 deep-dive prompt + structural evidence."""
    try:
        v1_prompt = _read_v1_prompt("analyze-deep-dive.md")
    except FileNotFoundError as e:
        return SubsystemDoc(
            subsystem_name=subsystem.name, markdown="",
            files_read=[], error=str(e),
        )

    # Build structural brief for this subsystem
    brief = build_subsystem_brief(subsystem, structure_path)

    # Read selected files
    file_contents: list[str] = []
    files_read: list[str] = []
    for entry in file_selection.files:
        fp = entry["file_path"]
        full_path = repo_root / fp
        if not full_path.exists():
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 15000:
                content = content[:15000] + "\n[TRUNCATED]\n"
            file_contents.append(f"### {fp}\n```\n{content}\n```\n")
            files_read.append(fp)
        except OSError:
            continue

    # Read analysis-state and system-overview if they exist —
    # inject into prompt so the model doesn't need to Read them itself
    prior_context = ""
    for doc_name in (".analysis-state.md", "system-overview.md"):
        doc_path = repo_root / "agent-docs" / doc_name
        if doc_path.exists():
            try:
                doc_content = doc_path.read_text(encoding="utf-8", errors="replace")
                if len(doc_content) > 5000:
                    doc_content = doc_content[:5000] + "\n[TRUNCATED]\n"
                prior_context += f"### {doc_name}\n```\n{doc_content}\n```\n\n"
            except OSError:
                pass

    # Adapt v1 prompt for programmatic use
    system_prompt = (
        v1_prompt.replace("$ARGUMENTS", subsystem.name) +
        "\n\n## IMPORTANT: Programmatic Execution Mode\n"
        "You are running in non-interactive mode. "
        "Do NOT wait for user confirmation for recursion. "
        "Proceed with a single flat document. "
        "Output ONLY the subsystem document markdown. "
        "Do NOT include the analysis-state update. "
        "Keep the document under 150 lines. "
        "The analysis state and system overview are provided below — "
        "do NOT try to Read them yourself."
    )

    user_prompt = (
        f"## Prior analysis (from Phase 1)\n\n"
        f"{prior_context}"
        f"## Layer 1 Structural Evidence for '{subsystem.name}'\n\n"
        f"Directories: {', '.join(subsystem.directories)}\n"
        f"Role: {subsystem.role}\n\n"
        f"### Structural skeleton (all files in this subsystem)\n\n"
        f"{brief}\n\n"
        f"### Full source of selected key files\n\n"
        f"{''.join(file_contents)}\n\n"
        f"Write the subsystem document for '{subsystem.name}'. "
        f"Follow the template exactly. Under 150 lines. Cite file paths."
    )

    output, err = _call_llm(
        system_prompt, user_prompt,
        model=model, timeout_seconds=timeout_seconds,
        cwd=str(repo_root), allow_tools=True,
    )

    if err:
        return SubsystemDoc(
            subsystem_name=subsystem.name, markdown="",
            files_read=files_read, error=err,
        )

    return SubsystemDoc(
        subsystem_name=subsystem.name, markdown=output,
        files_read=files_read,
    )


def save_subsystem_doc(doc: SubsystemDoc, output_dir: Path) -> Path:
    """Save a subsystem doc to agent-docs/subsystems/{name}.md."""
    safe_name = doc.subsystem_name.lower().replace(" ", "_").replace("/", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ("_", "-"))

    subsystems_dir = output_dir / "subsystems"
    subsystems_dir.mkdir(parents=True, exist_ok=True)

    path = subsystems_dir / f"{safe_name}.md"
    path.write_text(doc.markdown + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Stage 5: Synthesize (v1 analyze-synthesize prompt)
# ---------------------------------------------------------------------------


@dataclass
class SynthesisResult:
    """All top-level artifacts from the v1 synthesis."""
    raw_output: str = ""
    errors: list[str] = field(default_factory=list)


def run_synthesize(
    repo_root: Path,
    structural_context: str = "",
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> SynthesisResult:
    """Run the v1 analyze-synthesize prompt.

    The v1 prompt reads existing agent-docs/ files (system-overview,
    subsystem docs) and produces the full artifact set. We inject
    structural data as additional evidence.

    For programmatic use: the LLM writes files to agent-docs/ via
    its tool use capabilities since we run with --permission-mode auto.
    Alternatively, we parse the output for file contents.
    """
    try:
        v1_prompt = _read_v1_prompt("analyze-synthesize.md")
    except FileNotFoundError as e:
        return SynthesisResult(errors=[str(e)])

    system_prompt = (
        v1_prompt +
        "\n\n## IMPORTANT: Programmatic Execution Mode\n"
        "You are running in non-interactive mode via `claude -p`. "
        "Do NOT wait for user confirmation for patterns. "
        "Do NOT ask questions. "
        "Execute all steps and write all files directly. "
        "Skip the quality smoke test interactive questions — "
        "perform the self-validation checks silently and fix any issues."
    )

    user_prompt = (
        f"## Additional Layer 1 Evidence\n\n"
        f"The repository has been scanned by pensieve. Structural data "
        f"is available in agent-docs/structure.json and agent-docs/graph.json. "
        f"Use this for additional evidence when generating patterns, "
        f"routing-map, and architecture sections.\n\n"
        f"{structural_context}\n\n"
        f"Run Phase 3 synthesis now. Read existing agent-docs/ and "
        f"generate all output files."
    )

    output, err = _call_llm(
        system_prompt, user_prompt,
        model=model, timeout_seconds=timeout_seconds,
        cwd=str(repo_root), allow_tools=True,
    )

    if err:
        return SynthesisResult(errors=[err])

    return SynthesisResult(raw_output=output)
