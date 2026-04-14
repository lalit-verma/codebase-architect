# Code Pensieve

> A vessel for codebase memories. Coding agents draw from the store on
> demand instead of re-experiencing the original event.

This directory is the **v2 build** of the codebase analysis framework.
The v1 framework lives alongside it in `shared/`, `claude-code/`,
`codex/`, and `cursor/` and remains runnable as a fallback during the
v2 rebuild.

For the full vision, design principles, architecture, phased rollout,
proceed criteria, decisions log, and lessons carried in from v1, see
[`../PLAN.md`](../PLAN.md) at the repo root.

## Directory layout

| Path | Purpose |
|---|---|
| `python/` | The Python package (`code-pensieve` on PyPI). AST extraction, hook installer, benchmark runner, MCP server. |
| `commands/` | Slash command files for Claude Code that wrap the Python CLI. Thin orchestration layer over the package. |
| `templates/` | Output document templates (nano-digest, agent-context, patterns, etc.). |
| `references/` | Reference documentation: generation rules, validation rules, scope-selection rules, etc. |
| `examples/` | Quality calibration targets — example outputs at the standard the framework aims for. |
| `worked/` | End-to-end runs on real repos with honest `review.md` files listing what we got right AND wrong. |
| `tests/` | Tests for the Python package and integration tests for the framework as a whole. |

## Status

Phase A scaffolding. See [`../PLAN.md`](../PLAN.md) for the current
build status, phase milestones, and proceed criteria.

## Why this exists alongside the v1 framework

The v1 framework (in `shared/`, `claude-code/`, `codex/`, `cursor/`)
treats the codebase as text to be read by an LLM, with the LLM doing
both extraction and interpretation in the same pass. Benchmark data
showed this approach loses to a baseline of "no agent-docs at all" on
cost and pass rate.

Code Pensieve splits the work: deterministic AST extraction handles
enumeration (functions, classes, imports, calls, rationale comments),
and the LLM handles only interpretation (subsystem naming, recipe
synthesis, decision rationale, prioritization). This is the cost
asymmetry that makes graphify-style tools 70× cheaper for the
extraction layer.

The v1 hybrid wiring (inlined nano-digest + Explore subagent
enrichment) is preserved as the baseline wiring strategy for v2 — it
addresses the long-context-fallback problem that earlier wiring
iterations couldn't fix. v2 augments it with PreToolUse hooks for
harness-enforced wiring on Claude Code.
