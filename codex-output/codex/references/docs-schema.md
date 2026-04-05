# Codex Wrapper Reference: Durable Docs Schema

Use this schema only after the user confirms the subsystem map and
explicitly asks for docs to be written.

When `../shared/templates/` exists, use those templates as the minimum
document shape. This file only summarizes the target docs tree.

```text
docs/
  index.md
  agent-brief.md
  system-overview.md
  decisions.md
  glossary.md
  uncertainties.md
  subsystems/
    <subsystem>.md
  flows/
    <flow>.md
```

## File Purposes

### `docs/index.md`

- navigation hub
- reading order
- subsystem and flow inventory
- confidence summary

### `docs/agent-brief.md`

- compact context-loading file for later agents
- highest-signal summary only

### `docs/system-overview.md`

- top-level architecture
- boundaries, main flows, style, and state model

### `docs/subsystems/<subsystem>.md`

- subsystem role
- dependencies and boundaries
- contracts, flows, trade-offs, and open questions

### `docs/flows/<flow>.md`

- trigger
- handoffs
- side effects
- failure handling

### `docs/decisions.md`

- architectural decisions
- trade-offs
- alternatives

### `docs/glossary.md`

- project-specific terms and overloaded names

### `docs/uncertainties.md`

- unresolved questions
- missing evidence
- what would resolve them
