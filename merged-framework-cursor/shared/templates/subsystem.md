# Template: `agent-docs/subsystems/{subsystem-name}.md`

```markdown
# {Subsystem Name}

## Why This Subsystem Exists

{1 paragraph: responsibility, role in the system, why it is separated
from adjacent code.}

## Boundaries

| Aspect | Detail |
|--------|--------|
| Path | `{path}` |
| Role | `{entrypoint/orchestration/domain/etc.}` |
| Inputs | {who calls it or what triggers it} |
| Outputs | {what it returns/emits/changes} |
| State | {what it owns, or "none"} |

## Sub-Modules

> Include this section only if this subsystem was decomposed.

| Sub-Module | Path | Responsibility | Doc |
|------------|------|----------------|-----|
| {name} | `{path}` | {1 sentence} | `subsystems/{parent}/{name}.md` |

## Evidence Anchors

- `{file:line}` - {why this file matters}
- `{file:line}` - {why this file matters}

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
- Failure handling: {how errors move}
- Async boundaries: {if any}
- Evidence: `{file:line}`, `{file:line}`

## Dependencies

### Internal

| Dependency | Why | Direction |
|------------|-----|-----------|
| {subsystem} | {1 sentence} | {imports / imported by / bidirectional} |

### External

| Package | Purpose | Load-Bearing? |
|---------|---------|---------------|
| {name} | {1 sentence} | {yes/no} |

## Configuration

- Config inputs: {files/env/flags}
- State owned: {what and where}
- Defaults and lifecycle notes: {if any}

## Code and Test Patterns

Conventions specific to this subsystem. System-wide patterns are in
`patterns.md`; only note subsystem-specific conventions here.

| Pattern | Usage | Example File |
|---------|-------|--------------|
| {naming convention, error style, etc.} | {where/when used} | `{file}` |

### Test Conventions

- Test framework: {jest/vitest/pytest/go test/etc.}
- Test location: {colocated / separate `__tests__` / `*_test.go` / etc.}
- Structure: {describe/it, table-driven, BDD, snapshot, etc.}
- Fixtures/mocks: {patterns used, shared utilities}
- Coverage: {full / sampled / notable gaps}

## Modification Guide

> What a coding agent (or developer) should know before changing this
> subsystem.

- **Invariants to preserve:** {contracts, ordering guarantees, state
  assumptions that must not be broken}
- **Pattern to follow when adding new code:**
  - To add a new {handler/endpoint/adapter/etc.}: {steps, files to
    touch, pattern to copy from}
- **Files commonly touched together:** {list}
- **Gotchas:** {implicit contracts, race conditions, ordering
  requirements, surprising coupling}

## Design Decisions and Trade-offs

### {Decision Title}

- What was chosen: {pattern}
- What it enables: {benefit}
- What it costs: {cost}
- Alternative: {credible alternative}
- Assessment: {factual observation}

## Edge Cases and Gotchas

- {item}

## Open Questions

- `UNCERTAIN:` {questions left by static analysis}
- `NEEDS CLARIFICATION:` {what a human should clarify}

## Coverage Notes

- Read fully: {files}
- Sampled: {files}
- Skipped: {files, with reason}
```
