# Template: `agent-docs/subsystems/{name}.md`

```markdown
# {Subsystem Name}

> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

## Why This Subsystem Exists

{1 paragraph: responsibility, role in the system, why it is separated
from adjacent code.}

## Boundaries

- Path / scope: `{path}`
- Role tag: `{entrypoint/orchestration/domain/etc.}`
- Inputs: {who calls it or what triggers it}
- Outputs: {what it returns/emits/changes}
- State: {what it owns, or "none"}

## Sub-Modules

{If recursive decomposition was applied, list child docs:}
- `agent-docs/subsystems/{name}/{child}.md` — {responsibility}

{If no decomposition: "None — this subsystem is documented as a single unit."}

## Evidence Anchors

- `{file:line}` — {why this file matters}
- `{file:line}` — {why this file matters}
- `{file:line}` — {why this file matters}

## Internal Structure

- `{file or package}` — {responsibility}; {why it matters}

## Key Contracts and Types

- {name} (`{file:line}`) — {purpose}; used by {callers/consumers}

## Main Flows

### {Entry Point or Flow}

- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors propagate}
- Async boundaries: {if any}
- Evidence: `{file:line}`, `{file:line}`

## Dependencies

### Internal

- {subsystem} — {why} ({imports/imported by/bidirectional})

### External

- {name} — {purpose} (load-bearing: {yes/no})

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

## Modification Guide

> What a coding agent (or developer) should know before changing this
> subsystem. This is the most agent-valuable section.

- **Invariants to preserve:** {contracts, ordering guarantees, state
  assumptions that must not be broken}
- **Pattern to follow when adding new code:**
  - To add a new {handler/endpoint/adapter/etc.}: {steps, files to
    touch, pattern to copy from}
  - Best template to copy from: `{cleanest example file}`
- **Files commonly touched together:** {list of files that are tightly
  coupled and usually modified as a group}
- **Gotchas for modifications:** {what a coding agent would likely get
  wrong on the first attempt, implicit contracts, ordering requirements}

## Edge Cases and Gotchas

- {implicit contract or ordering requirement}
- {race condition or concurrency concern}
- {known limitation or tech debt}
- {behavior that would surprise a new contributor}

## Detected Patterns

{Patterns found within this subsystem, accumulated for Phase 3:}

- {name} ({category}) — example: `{path}`, {N} files

{If no patterns: "No recurring patterns detected in this subsystem."}

## Open Questions

- `UNCERTAIN:` {questions left by static analysis}
- `NEEDS CLARIFICATION:` {what a human should clarify}

## Coverage Notes

- Read fully: {files}
- Sampled: {files, with reason}
- Skipped: {files, with reason}
```
