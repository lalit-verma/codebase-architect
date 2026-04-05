# Template: `agent-docs/subsystems/{name}.md`

```markdown
# {Subsystem Name}

## Why This Subsystem Exists

{1 paragraph: responsibility, role in the system, why it is separated
from adjacent code.}

## Boundaries

| Aspect | Detail |
|--------|--------|
| Path / scope | `{path}` |
| Role tag | `{entrypoint/orchestration/domain/etc.}` |
| Inputs | {who calls it or what triggers it} |
| Outputs | {what it returns/emits/changes} |
| State | {what it owns, or "none"} |

## Sub-subsystems

{If recursive decomposition was applied, list child docs:}
- `agent-docs/subsystems/{name}/{child}.md` — {responsibility}

{If no decomposition: "None — this subsystem is documented as a single unit."}

## Evidence Anchors

- `{file:line}` — {why this file matters}
- `{file:line}` — {why this file matters}
- `{file:line}` — {why this file matters}

## Internal Structure

| Unit | Responsibility | Why It Matters |
|------|----------------|----------------|
| `{file or package}` | {1 sentence} | {1 sentence} |

## Key Contracts and Types

| Contract / Type | Defined In | Purpose | Used By |
|-----------------|------------|---------|---------|
| {name} | `{file:line}` | {1 sentence} | {callers/consumers} |

## Main Flows

### {Entry Point or Flow}

- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors propagate}
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

## Configuration and State

- Config inputs: {files/env/flags}
- State owned: {what and where}
- Defaults and lifecycle notes: {if any}

## Design Decisions and Trade-offs

### {Decision Title}

- What was chosen: {pattern}
- What it enables: {benefit}
- What it costs: {cost}
- Alternative: {credible alternative}
- Assessment: {factual observation}

## Testing

- Coverage mode: {full read / sampled}
- Test files: {key test files}
- Test patterns: {table-driven/BDD/snapshot/integration/etc.}
- Notable fixtures or mocks: {if any}
- Gaps: {what is not tested}

## Edge Cases and Gotchas

- {implicit contract or ordering requirement}
- {race condition or concurrency concern}
- {known limitation or tech debt}
- {behavior that would surprise a new contributor}

## Detected Patterns

{Patterns found within this subsystem, accumulated for Phase 3:}

| Pattern | Category | Example File | File Count |
|---------|----------|--------------|------------|
| {name} | {category} | `{path}` | {N} |

{If no patterns: "No recurring patterns detected in this subsystem."}

## Open Questions

- `UNCERTAIN:` {questions left by static analysis}
- `NEEDS CLARIFICATION:` {what a human should clarify}

## Coverage Notes

- Read fully: {files}
- Sampled: {files, with reason}
- Skipped: {files, with reason}
```
