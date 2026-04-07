# Codebase Analysis Framework

Evidence-first architecture analysis for any repository. Produces
documentation optimized for **coding agent efficiency** — enabling
Claude Code, Codex, and Cursor to gain deep codebase context at session
start and write higher-quality code than a cold start.

## What It Produces

The two load-bearing outputs are:

- **`agent-docs/agent-context-nano.md`** — a ≤40 line nano-digest that
  you paste directly into your `CLAUDE.md` / `AGENTS.md` /
  `.cursorrules`. Lives in the agent's system prompt. Handles common
  tasks (Easy bucket) without any tool-call reads. **This is the
  load-bearing wiring fix** — see "Why hybrid wiring" below.
- **`agent-docs/agent-context.md`** — a ~120 line compact context file
  that an Explore subagent uses as a starting heuristic for deeper
  research. Handles medium/hard tasks where the nano-digest is
  insufficient.

Full output written to `agent-docs/` in your target repo:

```
agent-docs/
  agent-context-nano.md  ** INLINED nano-digest (paste into CLAUDE.md) **
  agent-context.md          compact context for Explore subagents
  patterns.md            ** code patterns — "how to add a new X" **
  agent-brief.md            compact architecture map
  agent-protocol.md         wiring instructions for agents
  routing-map.md            task-to-doc routing (machine-readable)
  index.md                  navigation hub
  system-overview.md        top-level architecture
  decisions.md              architectural trade-offs
  glossary.md               project-specific terms
  uncertainties.md          unresolved questions
  subsystems/               per-subsystem deep dives
  flows/                    cross-cutting flows (if warranted)
```

## The 3-Phase Workflow

| Phase | Command | Runs | Output |
|-------|---------|------|--------|
| 1. Discover & Map | `analyze-discover` | Once | `system-overview.md`, `.analysis-state.md` |
| 2. Deep Dive | `analyze-deep-dive` | Once per subsystem | `subsystems/{name}.md` |
| 3. Synthesize | `analyze-synthesize` | Once | `agent-context.md`, `patterns.md`, `agent-protocol.md`, and all remaining docs |

Phase 2 runs multiple times — once per subsystem. Large subsystems
are recursively decomposed (up to depth 3). Each phase tells you what
to run next.

## Setup: Claude Code

1. Copy the command files to your user-level commands directory:

   ```bash
   mkdir -p ~/.claude/commands
   cp claude-code/commands/*.md ~/.claude/commands/
   ```

2. Copy the shared resources:

   ```bash
   mkdir -p ~/.claude/codebase-analysis
   cp -r shared/* ~/.claude/codebase-analysis/
   ```

3. Open Claude Code in any target repo and run:

   ```
   /user:analyze-discover This is a Go payment service using gRPC
   ```

4. Follow the on-screen instructions. Each phase tells you the next
   command.

## Setup: Codex

1. Copy `codex/AGENTS.md` to your target repo root:

   ```bash
   cp codex/AGENTS.md /path/to/your-repo/AGENTS.md
   ```

2. Open Codex in your target repo.

3. Paste the contents of `codex/prompts/1-discover.md` as your first
   task. Replace `{USER_DESCRIPTION}` with a 2-3 line repo description.

4. Follow instructions at the end of each phase for the next prompt.

## Setup: Cursor

1. Copy `cursor/SKILL.md` and the `shared/` directory to your Cursor
   skills location.

2. Open Cursor in your target repo.

3. Ask the agent to analyze the codebase — the skill triggers on
   phrases like "analyze this codebase", "help me understand this
   repo", "document this architecture", etc.

## After Analysis: Wire agent-docs Into Your Coding Agent

After Phase 3 completes, you need to wire the generated documentation
into your coding agent. This is the critical step — without it, the
agent won't know the docs exist.

The wiring uses a **hybrid two-part strategy**:

1. **Paste the nano-digest** (`agent-docs/agent-context-nano.md`)
   directly into your agent config file (`CLAUDE.md`, `AGENTS.md`,
   or `.cursorrules`). Do not reference it by path — paste the actual
   contents. The nano-digest is meant to live in the system prompt.
2. **Add a single Explore-enrichment line** below the nano-digest
   telling subagents where the deeper docs live.

The same wiring works for all three platforms — only the config file
name changes.

---

### Claude Code

Open your `CLAUDE.md` (create it at repo root if it doesn't exist),
then:

1. Paste the entire contents of `agent-docs/agent-context-nano.md`.
2. Below it, add this line:

```
If you spawn an Explore subagent for codebase research, point it at
`agent-docs/agent-context.md` as a starting heuristic. Deeper docs:
`agent-docs/subsystems/{name}.md`, `agent-docs/patterns.md`,
`agent-docs/decisions.md`. Do not read these from the main thread.
```

Done. The full copy-paste-ready snippet (with the nano-digest already
inlined) is also written to `agent-docs/agent-protocol.md` after
Phase 3 completes.

---

### Cursor

Same as Claude Code, but the target file is `.cursorrules` (or
`.cursor/rules/architecture-context.mdc` with `alwaysApply: true`).

---

### Codex

Same as Claude Code, but the target file is `AGENTS.md`.

---

### Why hybrid wiring

The framework went through several wiring iterations, each driven by
benchmark data. The current shape is the result of three findings:

**1. Main-thread Reads of `agent-docs/` inflate cost.** Early versions
of the framework had the agent read `agent-context.md`, plus subsystem
docs, plus `patterns.md` at session start. Benchmarks showed this
triggered long-context fallback to larger models — even though token
counts were similar, the cost was 11% higher because the larger model
costs ~5× more per token. The mechanism is mechanical: once accumulated
context exceeds the smaller model's window, the provider falls back.

**2. Pure subagent routing trades cost for quality.** A later iteration
moved all doc reads into a research subagent. This fixed cost (the
main thread stayed within the cheaper model's window) but tanked
quality on the Medium-difficulty bucket: lenient pass rate fell from
70% to 30%. The reason is **pattern fidelity** — when patterns are
read directly, the writer sees them verbatim and reproduces specifics.
When patterns come back as a subagent summary, the writer reproduces
the gist but loses the details that make strict pass rates work.

**3. The fix is to inline the load-bearing context, not reference it.**
The nano-digest is small enough to live in the system prompt
(~1.5–2.5K tokens) without triggering any context-window threshold,
and it contains the actual pattern recipes verbatim — so the writer
gets full pattern fidelity without doing any Reads. The deeper docs
remain available to Explore subagents when the task genuinely needs
them, which keeps the framework's full architecture map useful for
medium/hard tasks without polluting the main thread.

**How it scales by task difficulty:**

- **Easy tasks** rely entirely on the inlined nano-digest. No subagent
  spawned. No Reads of `agent-docs/`. Stays in the cheaper model.
- **Medium tasks** use the nano-digest as a starting point and spawn
  an Explore subagent to read `agent-context.md` and the relevant
  subsystem doc. Main thread still doesn't accumulate `agent-docs/`
  content; subagent returns a summary plus any verbatim snippets the
  task needs.
- **Hard tasks** lean heavily on the Explore subagent to navigate
  multiple subsystem docs, decisions, and flows. The nano-digest
  still serves as the main thread's anchor for "where am I in this
  codebase."

**What is intentionally absent from the wiring:**

- No "before every task" ritual ("Step 1: read X. Step 2: identify
  subsystem...")
- No "do not skip steps" framing
- No "quote the specific pattern from patterns.md" instruction
- No requirement to "state your understanding before writing code"
- No reference to `agent-docs/` paths *inside* the inlined nano-digest

Each of these was tested and removed because it inflated cost or
added overhead without a corresponding quality gain.

## Re-running

All phases support re-runs on repos with existing `agent-docs/`. The
tool reads existing state and augments rather than overwrites.
`agent-context.md`, `agent-context-nano.md`, and `patterns.md` are
regenerated entirely on re-run because stale context is worse than no
context. After a re-run you must re-paste the new
`agent-docs/agent-context-nano.md` into your `CLAUDE.md` (or
`AGENTS.md` / `.cursorrules`) — Phase 3 will remind you.

## Evaluation

Two evaluation rubrics in `eval/` let you grade the tool and its output:

- **`eval/eval-toolkit.md`** — Evaluates the framework itself (prompts,
  templates, references, cross-platform consistency). 8 dimensions
  scored PASS/PARTIAL/FAIL. Use when evolving the framework or comparing
  against alternatives.

- **`eval/eval-output.md`** — Evaluates the `agent-docs/` produced
  after running the tool on a real repo. 10 weighted dimensions with
  spot-checks against the source repo, cross-file consistency checks,
  and simulated task tests. Scored out of 32 with grade bands
  (Excellent/Good/Needs Work/Significant Gaps). Run this after every
  analysis to verify output quality.

To run either eval: paste the prompt into a coding agent, point it at
the target (framework files for toolkit eval, `agent-docs/` + source
repo for output eval), and it produces a scored report with evidence.

## Design Principles

- **Agent-first.** Primary consumer is a coding agent, not a human.
- **Read-only.** Never modifies source code.
- **Chat-first.** Presents findings for confirmation before writing.
- **Evidence-based.** Cites file paths. Labels uncertainty.
- **Pattern-aware.** Detects recurring code structures and documents
  them as actionable recipes.
- **Recursive.** Large subsystems are decomposed up to depth 3.
- **Durable.** Output structured for long-term reuse. Supports re-runs.

## File Structure

```
README.md                           (this file)
shared/
  protocol.md                       canonical behavioral spec
  docs-schema.md                    output directory structure
  references/                       operational playbooks
    ecosystem-playbook.md           per-language exploration
    scale-and-scope.md              reading depth, recursion thresholds
    subsystem-mapping-rubric.md     subsystem identification
    checkpoint-template.md          mandatory checkpoint format
    agent-context-rules.md          agent-context generation rules
    nano-context-rules.md           nano-digest generation rules
    pattern-detection-guide.md      pattern detection method
    validation-rules.md             self-check criteria per phase
    scope-selection-rules.md        monorepo scope selection
  templates/                        output document templates
    agent-context-template.md
    agent-context-nano-template.md
    agent-protocol-template.md
    patterns-template.md
    routing-map-template.md
    subsystem-template.md
    sub-module-template.md
    index-template.md
    agent-brief-template.md
    system-overview-template.md
    flow-template.md
    decisions-template.md
    glossary-template.md
    uncertainties-template.md
  examples/                         quality calibration
    checkpoint-example.md
    agent-context-example.md
claude-code/
  commands/                         Claude Code slash commands
    analyze-discover.md
    analyze-deep-dive.md
    analyze-synthesize.md
codex/
  AGENTS.md                         behavioral contract
  prompts/                          paste-able prompts
    1-discover.md
    2-deep-dive.md
    3-synthesize.md
cursor/
  SKILL.md                          Cursor skill with auto-trigger
eval/
  README.md                         when to use each eval, known limitations
  eval-toolkit.md                   evaluate the framework itself
  eval-output.md                    evaluate agent-docs/ output quality
```
