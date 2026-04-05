# Phase 2: Deep Dive

## Target Subsystem

{SUBSYSTEM_NAME}

> Replace `{SUBSYSTEM_NAME}` above with the subsystem name from your
> Phase 1 checkpoint before pasting this prompt.

---

## First: Read Analysis State

Read `docs/.analysis-state.md` and `docs/system-overview.md`. These
contain the confirmed subsystem map and architecture overview.

Match `{SUBSYSTEM_NAME}` against the subsystem map. If it does not
exist, list available subsystems and ask the user to clarify.

If `docs/.analysis-state.md` does not exist, say:
> **Phase 1 has not been run.** Run the Phase 1 prompt first.

## Progress

After reading state, display:

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| **2. Deep Dive** | **<-- current: {subsystem name}** |
| 3. Synthesize | pending |

**Subsystem progress:** {N} of {total} complete. Remaining: {list}.

---

## Mission

Deep architectural analysis of the **{subsystem}** subsystem. Read-only.
Factual. Produce a durable document for later agents and humans.

## Constraints

- **Read-only.** Do not modify source code.
- **Evidence-based.** Cite file paths. Moderate citation density.
- **Factual only.** Observable analysis only.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

---

## Procedure

### 1. Read the Subsystem

- List all files in the subsystem directory
- Small (<30 files): read all non-test files, sample tests
- Large (30+): read central files fully, sample leaves. Note what was sampled.

### 2. Analyze

**Boundaries & Role:**
- What does it do? Why does it exist separately?
- Inputs, outputs, state owned

**Internal Structure:**
- File organization, key units and responsibilities

**Contracts & Types:**
- Key exported types/interfaces/traits/classes
- Where defined, purpose, creators, consumers

**Flows:**
- Trace each entry point. Happy path, error handling, async boundaries.
- Note handoffs to other subsystems.

**Dependencies:**
- Internal: imports and imported-by
- External: third-party packages, which are load-bearing
- Flag circular dependencies

**Configuration:**
- Config values, defaults, environment-specific behavior

**Design Decisions (2-4):**
- What was chosen, what it enables, what it costs, alternatives, assessment

**Testing:**
- Test files, coverage patterns, test utilities

**Edge Cases & Gotchas:**
- Implicit contracts, race conditions, known limitations, surprises

### 3. Write the Document

Write to `docs/subsystems/{subsystem-name}.md`:

```markdown
# {Subsystem Name}

## Why This Subsystem Exists
{1 paragraph}

## Boundaries
| Aspect | Detail |
|--------|--------|
| Path | `{path}` |
| Role | `{tag}` |
| Inputs | ... |
| Outputs | ... |
| State | ... |

## Evidence Anchors
- `{file:line}` - {why it matters}

## Internal Structure
| Unit | Responsibility | Why It Matters |
|------|----------------|----------------|

## Key Contracts and Types
| Contract/Type | Defined In | Purpose | Used By |
|---------------|------------|---------|---------|

## Main Flows
### {Flow}
- Trigger, handoffs, failure handling, async boundaries, evidence

## Dependencies
### Internal
| Dependency | Why | Direction |

### External
| Package | Purpose | Load-Bearing? |

## Configuration
- Config inputs, state, defaults

## Design Decisions
### {Decision}
- Chosen, enables, costs, alternative, assessment

## Testing
- Coverage mode, test files, patterns, fixtures

## Edge Cases and Gotchas
- {items}

## Open Questions
- `UNCERTAIN:` ...
- `NEEDS CLARIFICATION:` ...

## Coverage Notes
- Read fully / sampled / skipped
```

### 4. Update State

Update `docs/.analysis-state.md`: move this subsystem from pending to
completed.

### 5. Report Next Steps

> **Phase 2 — {subsystem} complete.** [{N}/{total} done]
> Written: `docs/subsystems/{name}.md`
>
> **Remaining:**
> - {next subsystem} - {reason for order}
> - ...
>
> **When all done:** Paste the Phase 3 prompt (`3-synthesize.md`).

---

## Re-run Behavior

If `docs/subsystems/{name}.md` exists, read it first, compare against
current code, update changed sections, preserve accurate ones.
