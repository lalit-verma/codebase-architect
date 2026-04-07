# Durable Documentation Schema

Target output directory: `agent-docs/` in the target repository root.

Write these files only after the user confirms the subsystem map and
approves writing.

```
agent-docs/
  .analysis-state.md          # cross-phase state (internal)
  agent-context.md            # compact agent-loadable context (full, ~120 lines)
  agent-context-nano.md       # INLINED NANO-DIGEST (≤40 lines) — load-bearing wiring
  patterns.md                 # detected code patterns and conventions
  agent-brief.md              # compact architecture for agents
  agent-protocol.md           # wiring instructions for agents
  routing-map.md              # task-to-doc routing (machine-readable)
  index.md                    # navigation hub
  system-overview.md          # top-level architecture
  decisions.md                # architectural trade-offs
  glossary.md                 # project-specific terms
  uncertainties.md            # unresolved questions
  subsystems/
    {name}.md                 # one per subsystem
    {name}/                   # recursive sub-module docs (if needed)
      {child}.md
  flows/
    {name}.md                 # cross-cutting flows (if warranted)
```

## Priority Order

Generate in this order during Phase 3:

1. `agent-context.md` — compact context, under 120 lines
1b. `agent-context-nano.md` — strict subset of `agent-context.md`,
    ≤40 lines, designed to be inlined into the user's agent config
2. `patterns.md` — semi-automated, user confirms before write
2b. `routing-map.md` — machine-readable task-to-doc routing
3. `agent-brief.md` — under 100 lines
4. `agent-protocol.md` — wiring instructions (with nano-digest inlined into each platform section)
5. `index.md` — under 250 lines
6. `decisions.md`
7. `glossary.md`
8. `uncertainties.md`
9. `flows/*.md` (if warranted)

`system-overview.md` and `subsystems/*.md` are written during earlier
phases.

## File Purposes

- `agent-context.md` — Explore subagents + humans — Compact codebase context, fetched on demand
- `agent-context-nano.md` — Coding agent main thread — Inlined into the user's agent config; lives in the system prompt; strict subset of `agent-context.md`
- `patterns.md` — Explore subagents + humans — Recipes for common operations
- `agent-brief.md` — Coding agents (via Explore) — Deeper architecture when needed
- `agent-protocol.md` — Humans — Hybrid wiring instructions (nano-digest inlined per platform + Explore-enrichment line)
- `routing-map.md` — Coding agents — Task-to-doc routing (machine-readable YAML)
- `system-overview.md` — Both — Top-level architecture reference
- `subsystems/*.md` — Both — Deep subsystem reference
- `index.md` — Humans — Navigation and orientation
- `decisions.md` — Both — Constraints agents must respect
- `glossary.md` — Both — Term definitions
- `uncertainties.md` — Both — Known gaps to check
- `flows/*.md` — Both — Cross-cutting flow traces

## Hybrid Wiring Strategy

The framework's wiring uses a **two-part hybrid** based on benchmark
findings:

1. **Inline the nano-digest** (`agent-context-nano.md`) directly into
   the user's `CLAUDE.md` / `AGENTS.md` / `.cursorrules`. This puts
   the load-bearing context in the system prompt — no Read calls, no
   accumulation, no long-context fallback. Handles common-case tasks
   (Easy bucket) without any further reads.

2. **Tell Explore subagents** where the deeper docs live. When the
   main thread spawns an Explore subagent for codebase research, the
   subagent uses `agent-docs/agent-context.md` as a starting heuristic
   and can fetch `agent-docs/subsystems/`, `agent-docs/patterns.md`,
   and `agent-docs/decisions.md` as needed. This handles the
   medium/hard cases where the nano-digest is insufficient — without
   polluting main-thread context.

The main thread should never read `agent-docs/` files directly. Doing
so re-introduces the long-context fallback path that the inlined
nano-digest is designed to avoid.

## Template References

Use the concrete templates in `templates/` for document structure.
Each template maps 1:1 to an output file type.
