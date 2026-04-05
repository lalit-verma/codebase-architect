# Durable Documentation Schema

Target output directory: `agent-docs/` in the target repository root.

Write these files only after the user confirms the subsystem map and
approves writing.

```
agent-docs/
  .analysis-state.md          # cross-phase state (internal)
  agent-context.md            # PRIMARY: compact agent-loadable context
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

1. `agent-context.md` — primary deliverable, under 120 lines
2. `patterns.md` — semi-automated, user confirms before write
2b. `routing-map.md` — machine-readable task-to-doc routing
3. `agent-brief.md` — under 100 lines
4. `agent-protocol.md` — wiring instructions
5. `index.md` — under 250 lines
6. `decisions.md`
7. `glossary.md`
8. `uncertainties.md`
9. `flows/*.md` (if warranted)

`system-overview.md` and `subsystems/*.md` are written during earlier
phases.

## File Purposes

- `agent-context.md` — Coding agents — Compact context loaded at session start
- `patterns.md` — Coding agents — Recipes for common operations
- `agent-brief.md` — Coding agents — Deeper architecture when needed
- `agent-protocol.md` — Humans — Wiring instructions for agent config
- `routing-map.md` — Coding agents — Task-to-doc routing (machine-readable YAML)
- `system-overview.md` — Both — Top-level architecture reference
- `subsystems/*.md` — Both — Deep subsystem reference
- `index.md` — Humans — Navigation and orientation
- `decisions.md` — Both — Constraints agents must respect
- `glossary.md` — Both — Term definitions
- `uncertainties.md` — Both — Known gaps to check
- `flows/*.md` — Both — Cross-cutting flow traces

## Template References

Use the concrete templates in `templates/` for document structure.
Each template maps 1:1 to an output file type.
