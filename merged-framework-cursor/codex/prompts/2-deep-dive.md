# Phase 2: Deep Dive

## Target Subsystem

{SUBSYSTEM_NAME}

> Replace `{SUBSYSTEM_NAME}` above with the subsystem name from your
> Phase 1 checkpoint before pasting this prompt.

---

## First: Read Analysis State

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md`. These
contain the confirmed subsystem map, architecture overview, and
system-wide patterns.

Match `{SUBSYSTEM_NAME}` against the subsystem map. If it does not
exist, list available subsystems and ask the user to clarify.

If `agent-docs/.analysis-state.md` does not exist, say:
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

Deep architectural analysis of the **{subsystem}** subsystem.
Read-only. Factual. Produce a durable document optimized for coding
agents — they should be able to read it and confidently modify code
in this subsystem without making architecturally wrong decisions.

## Constraints

- **Read-only.** Do not modify source code.
- **Evidence-based.** Cite file paths. Moderate citation density.
- **Factual only.** Observable analysis only.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`
- Do not skip the Modification Guide — it is the most agent-valuable section.

---

## Procedure

### 1. Assess Size and Decide on Decomposition

Count source files in the subsystem. If flagged for decomposition in
Phase 1, or if >60 files / >3 distinct responsibilities:

- Propose sub-modules with name, path, responsibility, key files
- Explain how they relate
- Ask: **"Split into sub-module docs, or document as one unit?"**
- If confirmed: use split workflow (write parent + sub-module docs)

### 2. Read the Subsystem

- Small (<30 files): read all non-test files, sample tests
- Large (30+): read central files fully, sample leaves. Note what was sampled.

### 3. Analyze

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
- Framework, structure, fixture/mock patterns

**Edge Cases & Gotchas:**
- Implicit contracts, race conditions, known limitations, surprises

### 4. Capture Patterns

Observe code and test conventions specific to this subsystem:
- Naming, error handling, test structure, fixtures
- Any recurring abstractions or internal patterns

### 5. Identify Modification Guidance

Determine:
- **Invariants** that must not be broken
- **"How to add a new X"** — step-by-step for the most common change type, with the best file to copy from
- **Files commonly touched together**
- **Gotchas** a coding agent would likely hit

### 6. Write the Document(s)

**If NOT splitting:** Write to `agent-docs/subsystems/{subsystem-name}.md`
with all sections: Why It Exists, Boundaries, Evidence Anchors,
Internal Structure, Key Contracts, Main Flows, Dependencies,
Configuration, Code and Test Patterns, Modification Guide, Design
Decisions, Edge Cases and Gotchas, Open Questions, Coverage Notes.

**If splitting:** Write parent doc at `agent-docs/subsystems/{name}.md`
(with Sub-Modules table) + sub-module docs at
`agent-docs/subsystems/{name}/{sub-module}.md` (lighter template: Boundaries,
Contracts, Flows, Dependencies, Patterns, Modification Guide, Edge
Cases, Open Questions, Coverage Notes).

### 7. Update State

Update `agent-docs/.analysis-state.md`: move this subsystem from pending to
completed. If split, record sub-modules.

### 8. Report Next Steps

> **Phase 2 — {subsystem} complete.** [{N}/{total} done]
> Written: `agent-docs/subsystems/{name}.md`
>
> **Remaining:**
> - {next subsystem} - {reason for order}
> - ...
>
> **When all done:** Paste the Phase 3 prompt (`3-synthesize.md`).

---

## Re-run Behavior

If `agent-docs/subsystems/{name}.md` exists, read it first, compare against
current code, update changed sections, preserve accurate ones.
