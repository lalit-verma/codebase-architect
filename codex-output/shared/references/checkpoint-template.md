# Checkpoint Template

Use this exact structure for the mandatory chat checkpoint before any
durable docs are written.

## 1. Repository Classification

| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|
| Repo archetype | `{application | library | SDK | framework | monorepo | hybrid}` | `{high/medium/low}` | `{files/markers}` |
| Primary language | `{language}` | `{high/medium/low}` | `{files/markers}` |
| Execution model | `{CLI/server/worker/library/plugin/build/mixed}` | `{high/medium/low}` | `{files/markers}` |
| Scale | `{small/medium/large/very large}` | `{high/medium/low}` | `{counts/layout}` |

## 2. Working Understanding Of Repo Purpose

- `Confirmed:` {facts directly supported by code/docs}
- `Inference:` {best current understanding of what the repo exists to do}
- `UNCERTAIN:` {what is still unclear}

## 3. Candidate Subsystems

| Subsystem | Path / Scope | Role Tag | Responsibility | Evidence Anchors | Key Dependencies | Confidence |
|-----------|--------------|----------|----------------|------------------|------------------|------------|
| `{name}` | `{path}` | `{tag}` | `{1-2 sentences}` | `{2-5 references}` | `{names}` | `{high/medium/low}` |

Rules:

- order from most central to least central
- include only real architectural units
- mark generated/shared noise separately rather than inflating the map

## 4. Candidate Flows Worth Documenting

| Flow | Trigger | Main Handoffs | Why It Matters | Confidence |
|------|---------|---------------|----------------|------------|
| `{name}` | `{trigger}` | `{A -> B -> C}` | `{architectural reason}` | `{high/medium/low}` |

## 5. Coverage Notes

- what was read fully
- what was sampled
- what was intentionally skipped
- what appears generated or mechanically repetitive

## 6. Open Questions

- `NEEDS CLARIFICATION:` {question}
- `NEEDS CLARIFICATION:` {question}

Ask only questions that materially affect subsystem boundaries, repo
purpose, or write scope.

## 7. Proposed Documentation Plan

If the user approves writing, propose exactly what will be created:

- `docs/index.md`
- `docs/agent-brief.md`
- `docs/system-overview.md`
- `docs/subsystems/<subset>.md`
- `docs/flows/<subset>.md`
- `docs/decisions.md`
- `docs/glossary.md`
- `docs/uncertainties.md`

Also state:

- write scope
- expected citation density
- unresolved limitations that will remain

## 8. Required Closing Question

End with a direct confirmation request:

"Does this subsystem map and scope look right, and do you want me to
stay in chat mode or write the approved docs to `docs/`?"
