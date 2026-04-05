# Codebase Analysis Skill

Generic, evidence-first architecture analysis for any repository.
Produces durable documentation optimized for both human readers and
subsequent AI agents acting as copilots.

Works across applications, libraries, SDKs, frameworks, and monorepos.

## Two Wrappers, One Protocol

| Wrapper | Location | How It Works |
|---------|----------|--------------|
| Claude Code | `claude-code/commands/` | Slash commands (`/project:analyze-*`) |
| Codex | `codex/` | AGENTS.md + paste-able prompt files |

Both follow the same 3-phase workflow and produce identical output
structure in `docs/`.

## The 3-Phase Workflow

| Phase | Command / Prompt | Runs | Output |
|-------|-----------------|------|--------|
| 1. Discover & Map | `analyze-discover` | Once | `docs/system-overview.md`, `docs/.analysis-state.md` |
| 2. Deep Dive | `analyze-deep-dive` | Once per subsystem | `docs/subsystems/{name}.md` |
| 3. Synthesize | `analyze-synthesize` | Once | `docs/index.md`, `docs/agent-brief.md`, `docs/decisions.md`, `docs/glossary.md`, `docs/uncertainties.md` |

Phase 2 runs multiple times — once for each subsystem identified in
Phase 1. Each phase tells you what step you are on, what is complete,
and what comes next.

## Output Structure

```
docs/
  .analysis-state.md        # internal state (consumed by phases 2-3)
  index.md                   # navigation hub for humans and agents
  agent-brief.md             # compact context loader for future agents
  system-overview.md         # top-level architecture
  decisions.md               # key trade-offs and design choices
  glossary.md                # project-specific terms
  uncertainties.md           # unresolved questions
  subsystems/
    {subsystem-name}.md      # one per subsystem
  flows/
    {flow-name}.md           # optional, for cross-cutting flows
```

`index.md` and `agent-brief.md` are the primary entry points for any
agent that needs to onboard to the codebase.

## Re-running

All phases support re-runs. If `docs/` already exists, the skill reads
existing state and augments rather than overwrites. New subsystems are
added, removed ones are flagged, and changed areas are updated.

---

## Setup: Claude Code

1. Copy the `commands/` folder into your target repo:

   ```bash
   cp -r claude-code/commands/ /path/to/your-repo/.claude/commands/
   ```

   Or for user-level availability across all repos:

   ```bash
   cp -r claude-code/commands/ ~/.claude/commands/
   ```

2. Open Claude Code in your target repo.

3. Run the workflow:

   ```
   /project:analyze-discover This is a Go payment processing service that handles transactions via gRPC
   ```

   Follow the on-screen instructions. Each phase tells you the next
   command to run.

## Setup: Codex

1. Copy `codex/AGENTS.md` into your target repo root:

   ```bash
   cp codex/AGENTS.md /path/to/your-repo/AGENTS.md
   ```

2. Open Codex in your target repo.

3. Paste the contents of `codex/prompts/1-discover.md` as your first
   task. Replace `{USER_DESCRIPTION}` with your 2-3 line repo
   description.

4. Follow the instructions at the end of each phase for the next
   prompt to paste.

---

## Design Principles

- **Read-only.** Never modifies source code.
- **Chat-first.** Presents findings for confirmation before writing files.
- **Evidence-based.** Cites file paths. Uses `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:` labels.
- **Moderate citations.** Anchors each major section in 1-3 references. Does not cite every sentence.
- **Factual.** Limits analysis to observable code structure. No speculation about intent beyond what evidence supports.
- **Durable.** Output is structured for long-term reuse by humans and AI agents, not for single-session consumption.
- **Augmentable.** Supports re-runs that update rather than replace existing docs.
