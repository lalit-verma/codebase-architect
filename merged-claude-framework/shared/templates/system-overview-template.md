# Template: `agent-docs/system-overview.md`

```markdown
# {Repo Name} System Overview

> Auto-generated. Review before relying as ground truth.
> Generated on {date}.

## Purpose

{1 paragraph: what this system does, who interacts with it, why it
exists. Mark inference explicitly.}

## External Boundaries

| Actor / System | Interaction | Evidence |
|----------------|-------------|----------|
| {actor} | {protocol/method} | `{file path}` |

## Architectural Shape

{1 paragraph: layered? modular? event-driven? pipeline? plugin-based?
hybrid? Cite evidence.}

## Major Subsystems

| Subsystem | Role | Key Files | Depends On | Confidence |
|-----------|------|-----------|------------|------------|
| {name} | {tag} | `{paths}` | {names} | {level} |

## Primary Flows

### {Flow Name}

- Trigger: {what starts it}
- Path: {A -> B -> C}
- Why it matters: {1-2 sentences}
- Evidence: `{file paths}`

### {Flow Name}

- Trigger: {what starts it}
- Path: {A -> B -> C}
- Why it matters: {1-2 sentences}
- Evidence: `{file paths}`

## State and Configuration

- State boundaries: {stores, caches, or "stateless"}
- Config sources: {env/files/flags}
- Environment differences: {if known}

## Design Observations

- `Confirmed:` {directly evidenced facts}
- `Inference:` {trade-off or design rationale}
- `UNCERTAIN:` {what static analysis cannot confirm}
```
