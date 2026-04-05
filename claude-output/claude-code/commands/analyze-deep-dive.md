You are running Phase 2 of a 3-phase codebase analysis workflow.

## Target Subsystem

$ARGUMENTS

---

## First: Read Analysis State

Read `docs/.analysis-state.md` and `docs/system-overview.md` before
doing anything else. These were produced in Phase 1 and contain the
confirmed subsystem map, repo classification, and architecture overview.

From the analysis state, determine:
- Which subsystem the user is asking about (match `$ARGUMENTS` against the subsystem map)
- What subsystems have already been deep-dived
- What subsystems remain

If `docs/.analysis-state.md` does not exist, tell the user:

> **Phase 1 has not been run yet.** Run `/project:analyze-discover {description}` first.

Then stop.

## Progress

After reading the analysis state, display:

| Phase | Status |
|-------|--------|
| 1. Discover & Map | complete |
| **2. Deep Dive** | **<-- current: {subsystem name}** |
| 3. Synthesize | pending |

**Subsystem progress:** {N} of {total} complete. Remaining: {list}.

---

## Mission

Produce a deep architectural understanding of the **{subsystem}**
subsystem. Read-only. Factual. Output a durable document that later
agents can use to navigate and work within this part of the codebase.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references. Do not cite every sentence.
- **Factual only.** Limit to observable analysis.
- Use labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

---

## Procedure

### Step 1: Locate and Read the Subsystem

Using the path from the analysis state:

1. List all files in the subsystem directory
2. For small subsystems (<30 files): read all non-test files, sample tests
3. For large subsystems (30+ files): read central files fully, sample repetitive leaves. Note what was sampled.
4. Read entry files identified in the analysis state

### Step 2: Analyze

Investigate these aspects:

**Boundaries & Role:**
- What does this subsystem do and why does it exist separately?
- What are its inputs (who calls it, what triggers it)?
- What are its outputs (what it returns, emits, or changes)?
- What state does it own, if any?

**Internal Structure:**
- How are files organized within this subsystem?
- What are the key units and their responsibilities?

**Contracts & Types:**
- What are the key exported types, interfaces, traits, or classes?
- For each: where defined, purpose, who creates it, who consumes it

**Flows:**
- Trace each entry point through the subsystem
- Note the happy path, error handling, and async boundaries
- Note where the subsystem hands off to other subsystems

**Dependencies:**
- Internal: what other subsystems does it import? What imports it?
- External: what third-party packages does it use? Which are load-bearing?
- Flag circular dependencies or surprising coupling

**Configuration:**
- What config values affect this subsystem?
- What defaults are assumed?
- What environment-specific behavior exists?

**Design Decisions:**
For each major design choice (aim for 2-4):
1. What was chosen
2. What it enables
3. What it costs
4. Alternative approaches
5. Assessment

**Testing:**
- What test files exist?
- What is covered vs. not?
- What test patterns are used (table-driven, BDD, snapshot, etc.)?
- Any notable test utilities, mocks, or fixtures?

**Edge Cases & Gotchas:**
- Implicit contracts or ordering requirements
- Race conditions or concurrency concerns
- Known limitations or tech debt (TODO comments, workarounds)
- Behavior that would surprise a new contributor

### Step 3: Write the Subsystem Document

Write to `docs/subsystems/{subsystem-name}.md` using this structure:

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
| {name} | `{file:line}` | {1 sentence} | {callers} |

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

## Design Decisions and Trade-offs

### {Decision Title}
- What was chosen: {pattern}
- What it enables: {benefit}
- What it costs: {cost}
- Alternative: {credible alternative}
- Assessment: {your factual observation}

## Testing

- Coverage mode: {full / sampled}
- Test files: {list}
- Patterns: {table-driven/BDD/snapshot/etc.}
- Notable fixtures or mocks: {if any}

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

### Step 4: Update Analysis State

After writing, update `docs/.analysis-state.md`:
- Move this subsystem from `subsystems_pending_deep_dive` to `subsystems_completed`

### Step 5: Report Next Steps

After writing, tell the user:

> **Phase 2 — Deep dive on {subsystem} complete.** [{N}/{total} subsystems done]
>
> Written: `docs/subsystems/{subsystem-name}.md`
>
> **Remaining subsystems:**
> - `/project:analyze-deep-dive {next-subsystem}` - {reason for order}
> - ...
>
> **When all subsystems are done:** Run `/project:analyze-synthesize`

If this was the last subsystem:

> **All subsystems analyzed.** Run `/project:analyze-synthesize` to produce the final documentation set.

---

## Re-run Behavior

If `docs/subsystems/{subsystem-name}.md` already exists:

1. Read the existing document first
2. Compare against current code state
3. Update sections that have changed
4. Preserve sections that are still accurate
5. Add a note at the top: `> Updated on {date}. Previous analysis preserved where still accurate.`
