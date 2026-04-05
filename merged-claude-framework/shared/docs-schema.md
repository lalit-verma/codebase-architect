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
  index.md                    # navigation hub
  system-overview.md          # top-level architecture
  decisions.md                # architectural trade-offs
  glossary.md                 # project-specific terms
  uncertainties.md            # unresolved questions
  subsystems/
    {name}.md                 # one per subsystem
    {name}/                   # recursive sub-subsystem docs (if needed)
      {child}.md
  flows/
    {name}.md                 # cross-cutting flows (if warranted)
```

## Priority Order

Generate in this order during Phase 3:

1. `agent-context.md` — primary deliverable, under 120 lines
2. `patterns.md` — semi-automated, user confirms before write
3. `agent-brief.md` — under 100 lines
4. `index.md` — under 250 lines
5. `decisions.md`
6. `glossary.md`
7. `uncertainties.md`
8. `flows/*.md` (if warranted)

`system-overview.md` and `subsystems/*.md` are written during earlier
phases.

## File Purposes

| File | Primary Consumer | Purpose |
|------|-----------------|---------|
| `agent-context.md` | Coding agents | Compact context loaded at session start |
| `patterns.md` | Coding agents | Recipes for common operations |
| `agent-brief.md` | Coding agents | Deeper architecture when needed |
| `system-overview.md` | Both | Top-level architecture reference |
| `subsystems/*.md` | Both | Deep subsystem reference |
| `index.md` | Humans | Navigation and orientation |
| `decisions.md` | Both | Constraints agents must respect |
| `glossary.md` | Both | Term definitions |
| `uncertainties.md` | Both | Known gaps to check |
| `flows/*.md` | Both | Cross-cutting flow traces |

## Template References

Use the concrete templates in `templates/` for document structure.
Each template maps 1:1 to an output file type.
