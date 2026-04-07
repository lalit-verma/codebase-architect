# Codebase Analysis Framework

Evidence-first architecture analysis for any repository. Produces
documentation optimized for **coding agent efficiency** — enabling
Claude Code, Codex, and Cursor to gain deep codebase context at session
start and write higher-quality code than a cold start.

## What It Produces

The primary output is `agent-docs/agent-context.md` — a compact file
(under 120 lines) that a coding agent loads at session start. It
contains the architecture map, code patterns to follow, conventions,
anti-patterns, and key contracts. No prose, every line actionable.

Full output written to `agent-docs/` in your target repo:

```
agent-docs/
  agent-context.md       ** PRIMARY: compact context for coding agents **
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
into your coding agent so it loads context at session start. This is
the critical step — without it, the agent won't know the docs exist.

The wiring uses a **tiered loading strategy**: always load the compact
context file, then selectively load deeper docs based on the task. This
prevents burning the agent's context window on files irrelevant to the
current task.

---

### Claude Code

Add this block to your `CLAUDE.md` (create it at repo root if it
doesn't exist):

```markdown
## Codebase Context

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.
```

---

### Cursor

Add this block to your `.cursorrules` (create it at repo root if it
doesn't exist):

```markdown
## Codebase Context

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.
```

---

### Codex

Add this block to your `AGENTS.md` (create it at repo root if it
doesn't exist, or append to existing):

```markdown
## Codebase Context

Read `agent-docs/agent-context.md` once at session start — it has the
architecture map, key patterns, and conventions.

For non-trivial work, also consult the relevant
`agent-docs/subsystems/{name}.md` and `agent-docs/patterns.md` before
creating new files of an established type. Skip both for small or
self-contained edits.
```

---

### Why this structure works

**Lean by default.** Earlier versions of this framework prescribed a
five-step ritual ("Step 1...Step 5, do not skip steps, quote the
specific pattern, state your understanding"). Benchmark runs showed
the ritual was the dominant cost driver: it pushed agents off cheaper
models onto reasoning-heavy ones for tasks that did not need it,
inflated cost without improving pass rates, and added overhead on
trivial edits where the docs were not relevant. The current wiring
loads the compact context once and trusts the agent to pull deeper
docs only when the task warrants it.

**Tiered loading prevents context window waste.** `agent-context.md`
(~120 lines) is the only thing always read. Subsystem docs and
`patterns.md` are conditional — the agent reads them only when the
task touches a non-trivial subsystem or creates a new file of an
established type. A bug fix in the storage layer doesn't need the UI
subsystem doc.

**Patterns help most where they apply.** `patterns.md` is most useful
when you're about to create a new file of an established type
(handler, migration, test, etc.). For small or one-off edits, forcing
a pattern lookup is overhead with no payoff — and on tasks where the
right answer is "this case is different," it can actively constrain
the agent away from the correct solution.

## Re-running

All phases support re-runs on repos with existing `agent-docs/`. The
tool reads existing state and augments rather than overwrites.
`agent-context.md` and `patterns.md` are regenerated entirely on re-run
because stale context is worse than no context.

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
    pattern-detection-guide.md      pattern detection method
    validation-rules.md             self-check criteria per phase
    scope-selection-rules.md        monorepo scope selection
  templates/                        output document templates
    agent-context-template.md
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
