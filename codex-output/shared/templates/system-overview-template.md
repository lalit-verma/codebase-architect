# Template: `docs/system-overview.md`

```markdown
# {Repo Name} System Overview

## Purpose

{1 paragraph describing what the system appears to do and who or what
interacts with it. Mark inference explicitly if needed.}

## External Boundaries

| Actor / System | Interaction | Evidence |
|----------------|-------------|----------|
| {actor} | {REST/gRPC/CLI/import/etc.} | `{file:line}` |

## Architectural Shape

{1 short paragraph describing whether the system is layered, modular,
plugin-based, pipeline-oriented, event-driven, or hybrid.}

## Major Subsystems

| Subsystem | Role | Key Files | Depends On | Confidence |
|-----------|------|-----------|------------|------------|
| {name} | {tag} | `{paths}` | {names} | {level} |

## Primary Flows

### {Flow Name}

- Trigger: {what starts it}
- Path: {A -> B -> C}
- Why it matters: {1-2 sentences}
- Evidence anchors: `{file:line}`, `{file:line}`

Repeat for the most important flows only.

## State And Configuration

- State boundaries: {stores, caches, durable state, or stateless note}
- Configuration sources: {env/config files/flags}
- Environment differences: {if known}

## Design Observations

- `Confirmed:` {directly evidenced architecture fact}
- `Inference:` {trade-off or design rationale}
- `UNCERTAIN:` {what static analysis cannot fully confirm}
```
