# Template: `agent-docs/system-overview.md`

```markdown
# {Repo Name} System Overview

> Auto-generated. Review before relying as ground truth. Generated {date}.

## Purpose

{1 paragraph: what this system does, who interacts with it, why it
exists. Mark inference explicitly.}

## External Boundaries

| Actor / System | Interaction | Evidence |
|----------------|-------------|----------|
| {actor} | {REST/gRPC/CLI/import/etc.} | `{file:line}` |

## Architectural Shape

{1 paragraph: layered? modular? event-driven? pipeline? plugin-based?
hybrid? Cite the structural evidence.}

## Major Subsystems

| Subsystem | Role | Key Files | Depends On | Confidence | Has Sub-Modules |
|-----------|------|-----------|------------|------------|-----------------|
| {name} | {tag} | `{paths}` | {names} | {level} | {yes/no} |

## Primary Flows

### {Flow Name}

- Trigger: {what starts it}
- Path: {A -> B -> C}
- Why it matters: {1-2 sentences}
- Evidence anchors: `{file:line}`, `{file:line}`

Repeat for the 3-5 most important flows only.

## State and Configuration

- State boundaries: {stores, caches, durable state, or "stateless"}
- Configuration sources: {env/config files/flags}
- Environment differences: {if known}

## Patterns at a Glance

Top code conventions observed system-wide. Detailed per-subsystem
patterns are in `patterns.md` and individual subsystem docs.

| Pattern | Where Observed | Example |
|---------|---------------|---------|
| {pattern} | {subsystems/scope} | `{file}` |

## Design Observations

- `Confirmed:` {directly evidenced architecture fact}
- `Inference:` {trade-off or design rationale}
- `UNCERTAIN:` {what static analysis cannot fully confirm}
- `NEEDS CLARIFICATION:` {what a human should answer}
```
