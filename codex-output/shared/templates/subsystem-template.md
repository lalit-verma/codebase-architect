# Template: `docs/subsystems/<subsystem>.md`

```markdown
# {Subsystem Name}

## Why This Subsystem Exists

{1 paragraph on responsibility, role in the system, and why it appears
to have been separated from adjacent code.}

## Boundaries

| Aspect | Detail |
|--------|--------|
| Path / scope | `{path}` |
| Role tag | `{entrypoint/orchestration/domain/etc.}` |
| Inputs | {who calls it or what triggers it} |
| Outputs | {what it returns/emits/changes} |
| State | {what it owns, or "none"} |

## Evidence Anchors

- `{file:line}` - {why this file matters}
- `{file:line}` - {why this file matters}
- `{file:line}` - {why this file matters}

## Internal Structure

| Unit | Responsibility | Why It Matters |
|------|----------------|----------------|
| `{file or package}` | {1 sentence} | {1 sentence} |

## Key Contracts And Types

| Contract / Type | Defined In | Purpose | Used By |
|-----------------|------------|---------|---------|
| {name} | `{file:line}` | {1 sentence} | {callers/consumers} |

## Main Flows

### {Entry Point Or Flow}

- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors move}
- Async boundaries: {if any}
- Evidence: `{file:line}`, `{file:line}`

## Dependencies

### Internal

| Dependency | Why | Direction |
|------------|-----|-----------|
| {subsystem} | {1 sentence} | {imports/imported by/bidirectional} |

### External

| Package | Purpose | Load-Bearing? |
|---------|---------|---------------|
| {name} | {1 sentence} | {yes/no} |

## Configuration And State

- config inputs: {files/env/flags}
- state owned: {what and where}
- caches or lifecycle notes: {if any}

## Design Decisions And Trade-Offs

### {Decision Title}

- What was chosen: {pattern}
- What it enables: {benefit}
- What it costs: {cost}
- Alternative: {credible alternative}
- Assessment: {your view}

## Coverage And Gaps

- Coverage mode: {full read / central read plus sampling}
- Areas sampled: {paths}
- `UNCERTAIN:` {questions left by static analysis}
```
