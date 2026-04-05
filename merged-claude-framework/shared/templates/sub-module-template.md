# Template: `agent-docs/subsystems/{parent}/{sub-module-name}.md`

Lighter than a full subsystem doc. Design decisions and configuration
are captured at the parent level unless this sub-module has its own.
Target ~60% the length of a full subsystem doc.

```markdown
# {Sub-Module Name}

> Part of [{Parent Subsystem}](../{parent-subsystem}.md)

## Why This Sub-Module Exists

{1 paragraph: what it does within the parent subsystem and why it is
a distinct unit rather than inlined code.}

## Boundaries

- Path: `{path}`
- Role: `{tag}`
- Inputs: {who calls it — typically the parent or siblings}
- Outputs: {what it returns/emits/changes}
- State: {what it owns, or "none — inherited from parent"}

## Evidence Anchors

- `{file:line}` - {why this file matters}
- `{file:line}` - {why this file matters}

## Internal Structure

- `{file}` — {responsibility}
- `{file}` — {responsibility}

## Key Contracts and Types

- `{file:line}` — {name}: {purpose}, used by {callers}

## Main Flows

### {Flow}

- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors move}
- Evidence: `{file:line}`

## Dependencies

- {dependency} — {why}, {direction}

## Code and Test Patterns

- {convention specific to this sub-module} — see `{file}`

## Modification Guide

- **Invariants:** {what must not break}
- **To add new code:** {pattern, files to touch}
- **Files commonly touched together:** {list}
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
