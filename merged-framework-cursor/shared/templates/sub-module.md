# Template: `agent-docs/subsystems/{parent}/{sub-module-name}.md`

Lighter than a full subsystem doc. Design decisions and configuration
are captured at the parent level unless this sub-module has its own.

```markdown
# {Sub-Module Name}

> Part of [{Parent Subsystem}](../{parent-subsystem}.md)

## Why This Sub-Module Exists

{1 paragraph: what it does within the parent subsystem and why it is
a distinct unit rather than inlined code.}

## Boundaries

| Aspect | Detail |
|--------|--------|
| Path | `{path}` |
| Role | `{tag}` |
| Inputs | {who calls it — typically the parent or siblings} |
| Outputs | {what it returns/emits/changes} |
| State | {what it owns, or "none — inherited from parent"} |

## Evidence Anchors

- `{file:line}` - {why this file matters}
- `{file:line}` - {why this file matters}

## Internal Structure

| Unit | Responsibility |
|------|----------------|
| `{file}` | {1 sentence} |

## Key Contracts and Types

| Contract / Type | Defined In | Purpose | Used By |
|-----------------|------------|---------|---------|
| {name} | `{file:line}` | {1 sentence} | {callers} |

## Main Flows

### {Flow}

- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors move}
- Evidence: `{file:line}`

## Dependencies

| Dependency | Why | Direction |
|------------|-----|-----------|
| {sibling sub-module or external} | {1 sentence} | {direction} |

## Code and Test Patterns

| Pattern | Usage | Example File |
|---------|-------|--------------|
| {convention specific to this sub-module} | {where} | `{file}` |

## Modification Guide

- **Invariants:** {what must not break}
- **To add new code:** {pattern, files to touch}
- **Gotchas:** {surprises, implicit contracts}

## Edge Cases

- {item}

## Open Questions

- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}

## Coverage Notes

- Read fully: {files}
- Sampled: {files}
```
