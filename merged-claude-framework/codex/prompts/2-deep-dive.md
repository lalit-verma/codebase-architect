# Phase 2: Deep Dive

## Target Subsystem

{SUBSYSTEM_NAME}

> Replace `{SUBSYSTEM_NAME}` above with the subsystem name from your
> Phase 1 checkpoint before pasting this prompt.

---

## First: Read Analysis State

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md`.
Match `{SUBSYSTEM_NAME}` against the subsystem map.

If `agent-docs/.analysis-state.md` does not exist:
> **Phase 1 has not been run.** Run the Phase 1 prompt first.

## Progress

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| **2. Deep Dive** | **<-- current: {subsystem name}** |
| 3. Synthesize | pending |

**Subsystem progress:** {N} of {total} complete. Remaining: {list}.

---

## Mission

Deep architectural analysis of **{subsystem}**. Read-only. Factual.
Produce a durable document that coding agents use to navigate and work
within this part of the codebase.

## Constraints

- **Read-only.** Do not modify source code.
- **Evidence-based.** Cite file paths. Moderate citation density.
- **Factual only.** Observable analysis only.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

## Anti-Patterns

Do not:

- confuse directory structure with architectural boundaries
- claim runtime behavior that static evidence does not support
- produce boilerplate prose that adds no insight
- skip the Modification Guide — it is the most agent-valuable section
- decompose a subsystem that is large but uniform (document the pattern)

## Quality Bar

A subsystem doc is good enough when a coding agent reading it can:
- understand what the subsystem does and where it fits
- find the right files to modify for a given task
- follow the correct patterns when adding new code
- avoid breaking invariants or implicit contracts
- know what areas are uncertain

---

## Procedure

### 1. Read the Subsystem

- List all files in the subsystem directory
- <30 files: read all non-test files, sample tests
- 30+ files: read central files fully, sample leaves. Note what was
  sampled.

### 2. Evaluate Recursion Need

If subsystem has 50+ files OR 3+ internal modules with own contracts:

> This subsystem is large enough to decompose:
> - **{sub-1}** (`{path}`): {responsibility}
> - **{sub-2}** (`{path}`): {responsibility}
> Confirm? Or analyze as single unit?

If confirmed: write parent doc + child docs at
`agent-docs/subsystems/{name}/{child}.md` using a lighter sub-module
template (drop Design Decisions and Configuration sections, target
~60% the length of a full subsystem doc). Max depth 3.

When NOT to decompose: many-files-one-pattern (document pattern instead),
generated files, single responsibility despite many files.

### 3. Analyze

**Boundaries & Role:** what it does, inputs, outputs, state owned

**Internal Structure:** file organization, key units

**Contracts & Types:** exported types/interfaces/traits/classes — where
defined, purpose, creators, consumers

**Flows:** trace entry points. Happy path, error handling, async
boundaries, handoffs to other subsystems.

**Dependencies:**
- Internal: imports and imported-by
- External: third-party packages, which are load-bearing
- Flag circular dependencies

**Configuration:** config values, defaults, env-specific behavior

**Design Decisions (2-4):** chosen, enables, costs, alternatives,
assessment

**Testing:** test files, coverage patterns, utilities, fixtures, gaps

**Edge Cases & Gotchas:** implicit contracts, race conditions, known
limitations, surprises for new contributors

**Modification Guide:** (most agent-valuable section)
- Invariants that must be preserved when modifying this subsystem
- Step-by-step pattern for the most common change type
- Files commonly touched together
- What a coding agent would likely get wrong on the first attempt

**Pattern Detection:** identify repetitive file structures. For each:
name, category, example file (cleanest), file list, registration points.

### 4. Write Document

Write to `agent-docs/subsystems/{subsystem-name}.md`:

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

## Sub-subsystems
{Child docs if recursion applied, or "None"}

## Evidence Anchors
- `{file:line}` — {why it matters}

## Internal Structure
| Unit | Responsibility | Why It Matters |

## Key Contracts and Types
| Contract/Type | Defined In | Purpose | Used By |

## Main Flows
### {Flow}
- Trigger, handoffs, failure handling, async, evidence

## Dependencies
### Internal
| Dependency | Why | Direction |
### External
| Package | Purpose | Load-Bearing? |

## Configuration and State

## Design Decisions and Trade-offs
### {Decision}

## Testing

## Modification Guide
- **Invariants to preserve:** {list}
- **To add a new {common change type}:**
  1. {step}
  2. {step}
  - Best template to copy from: `{file}`
- **Files commonly touched together:** {list}
- **Gotchas:** {list}

## Edge Cases and Gotchas

## Detected Patterns
| Pattern | Category | Example File | File Count |

## Open Questions

## Coverage Notes
```

### 5. Update State

Move subsystem from `subsystems_pending` to `subsystems_completed`
in `agent-docs/.analysis-state.md`. Record detected patterns.

### 6. Report Next Steps

> **Phase 2 — {subsystem} complete.** [{N}/{total}]
> Written: `agent-docs/subsystems/{name}.md`
>
> **Remaining:**
> - {next subsystem} — {reason}
>
> **When all done:** Paste the Phase 3 prompt (`3-synthesize.md`).

---

## Re-run Behavior

If `agent-docs/subsystems/{name}.md` exists, read first, compare
against current code, update changed sections, preserve accurate ones.
