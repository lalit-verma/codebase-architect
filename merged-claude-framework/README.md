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
## Codebase Context — Read Before Every Task

Before starting any task in this repository, follow these steps in
order. Do not skip steps. Do not start writing code until you have
completed the reading.

### Step 1: Load core context (always)
Read `agent-docs/agent-context.md` fully. This contains the
architecture map, code patterns, conventions, and anti-patterns.
Internalize the patterns and constraints before proceeding.

### Step 2: Load task-relevant subsystem docs (based on your task)
Identify which subsystem(s) your task touches based on the architecture
map in agent-context.md. Read the corresponding subsystem doc(s) from
`agent-docs/subsystems/`. If the subsystem has sub-module docs
(a subdirectory under subsystems/), read those too.

### Step 3: Check patterns before creating new files
Before creating any new file, read `agent-docs/patterns.md` and follow
the established pattern for that file type. Do not invent new patterns
when an established one exists. In your plan, quote the specific pattern
you are following (e.g. "Per patterns.md, this repo uses...").

### Step 4: Check constraints before architectural changes
If your task involves changing how subsystems interact, adding new
dependencies, or modifying contracts — read `agent-docs/decisions.md`
first to understand existing trade-offs, and `agent-docs/uncertainties.md`
to know where assumptions are weak.

### Step 5: Confirm your understanding
Before writing code, state which subsystem(s) you're working in, which
patterns you'll follow (quote the specific pattern from patterns.md),
and any constraints from decisions.md that apply. Then proceed.
```

---

### Cursor

Add this block to your `.cursorrules` (create it at repo root if it
doesn't exist):

```markdown
## Codebase Context — Read Before Every Task

Before starting any task in this repository, follow these steps in
order. Do not skip steps. Do not start writing code until you have
completed the reading.

Step 1: Read `agent-docs/agent-context.md` fully. This is the
architecture map, patterns, conventions, and anti-patterns. Internalize
before proceeding.

Step 2: Based on the architecture map, identify which subsystem your
task touches. Read the corresponding `agent-docs/subsystems/{name}.md`.
If sub-module docs exist in a subdirectory, read those too.

Step 3: Before creating any new file, read `agent-docs/patterns.md`.
Follow the established pattern for that file type. Do not invent new
patterns. Quote the specific pattern you are following.

Step 4: If changing subsystem interactions, dependencies, or contracts,
read `agent-docs/decisions.md` and `agent-docs/uncertainties.md` first.

Step 5: Before writing code, state which subsystem you're working in,
which patterns apply (quote the specific pattern from patterns.md),
and any relevant constraints. Then proceed.
```

---

### Codex

Add this block to your `AGENTS.md` (create it at repo root if it
doesn't exist, or append to existing):

```markdown
## Codebase Context — Read Before Every Task

Before starting any task in this repository, follow these steps in
order. Do not skip steps. Do not start writing code until you have
completed the reading.

Step 1: Read `agent-docs/agent-context.md` fully. This is the
architecture map, patterns, conventions, and anti-patterns. Internalize
before proceeding.

Step 2: Based on the architecture map, identify which subsystem your
task touches. Read the corresponding `agent-docs/subsystems/{name}.md`.
If sub-module docs exist in a subdirectory, read those too.

Step 3: Before creating any new file, read `agent-docs/patterns.md`.
Follow the established pattern for that file type. Do not invent new
patterns. Quote the specific pattern you are following.

Step 4: If changing subsystem interactions, dependencies, or contracts,
read `agent-docs/decisions.md` and `agent-docs/uncertainties.md` first.

Step 5: Before writing code, state which subsystem you're working in,
which patterns apply (quote the specific pattern from patterns.md),
and any relevant constraints. Then proceed.
```

---

### Why this structure works

**Tiered loading prevents context window waste.** Step 1 (~120 lines)
is always loaded. Steps 2-4 are conditional — the agent reads only
what's relevant to the current task. A bug fix in the storage layer
doesn't need the UI subsystem doc.

**"Do not skip steps" forces sequential reading.** Without this, agents
tend to skim or jump ahead to code generation. The explicit ordering
ensures the agent processes architecture before acting.

**Step 5 forces comprehension.** Requiring the agent to state its
understanding before writing code is the closest you can get to
ensuring depth. If the agent's summary is wrong, it reveals a
misunderstanding before code is written.

**Step 3 prevents pattern drift.** Agents default to generating code
from their training data. Explicitly requiring pattern lookup before
file creation ensures they follow project conventions, not generic
patterns.

## Re-running

All phases support re-runs on repos with existing `agent-docs/`. The
tool reads existing state and augments rather than overwrites.
`agent-context.md` and `patterns.md` are regenerated entirely on re-run
because stale context is worse than no context.

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
merged-claude-framework/
  README.md                         (this file)
  PLAN.md                           (implementation plan)
  shared/
    protocol.md                     canonical behavioral spec
    docs-schema.md                  output directory structure
    references/                     operational playbooks
      ecosystem-playbook.md         per-language exploration
      scale-and-scope.md            reading depth, recursion thresholds
      subsystem-mapping-rubric.md   subsystem identification
      checkpoint-template.md        mandatory checkpoint format
      agent-context-rules.md        agent-context generation rules
      pattern-detection-guide.md    pattern detection method
    templates/                      output document templates
      agent-context-template.md
      agent-protocol-template.md
      patterns-template.md
      subsystem-template.md
      sub-module-template.md
      index-template.md
      agent-brief-template.md
      system-overview-template.md
      flow-template.md
      decisions-template.md
      glossary-template.md
      uncertainties-template.md
    examples/                       quality calibration
      checkpoint-example.md
      agent-context-example.md
  claude-code/
    commands/                       Claude Code slash commands
      analyze-discover.md
      analyze-deep-dive.md
      analyze-synthesize.md
  codex/
    AGENTS.md                       behavioral contract
    prompts/                        paste-able prompts
      1-discover.md
      2-deep-dive.md
      3-synthesize.md
  cursor/
    SKILL.md                        Cursor skill with auto-trigger
```
