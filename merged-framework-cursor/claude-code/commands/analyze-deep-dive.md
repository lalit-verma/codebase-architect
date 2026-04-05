You are running Phase 2 of a 3-phase codebase analysis workflow.

## Target Subsystem

$ARGUMENTS

---

## First: Read Analysis State

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md` before
doing anything else. These were produced in Phase 1 and contain the
confirmed subsystem map, repo classification, architecture overview,
and system-wide patterns.

From the analysis state, determine:
- Which subsystem the user is asking about (match `$ARGUMENTS` against the subsystem map)
- What subsystems have already been deep-dived
- What subsystems remain
- Whether this subsystem is flagged for recursive decomposition

If `agent-docs/.analysis-state.md` does not exist, tell the user:

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
subsystem. Read-only. Factual. Output a durable document optimized
for coding agents — they should be able to read this doc and
confidently modify code in this subsystem without making
architecturally wrong decisions.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references.
- **Factual only.** Limit to observable analysis.
- Use labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

## Anti-Patterns

Do not:

- confuse directory structure with architectural boundaries
- claim runtime behavior that static evidence does not support
- produce boilerplate prose that adds no insight
- skip the Modification Guide — it is the most agent-valuable section

## Quality Bar

A subsystem doc is good enough when a coding agent reading it can:

- understand what the subsystem does and where it fits
- find the right files to modify for a given task
- follow the correct patterns when adding new code
- avoid breaking invariants or implicit contracts
- know what areas are uncertain and need human verification

---

## Procedure

### Step 1: Assess Size and Decide on Decomposition

Check whether this subsystem needs recursive decomposition:

1. List all source files in the subsystem directory. Count them.
2. If the subsystem was **flagged for decomposition** in Phase 1, or if
   you discover it has **>60 source files** or **>3 distinct internal
   responsibilities**:
   - Propose sub-modules to the user:

     | Sub-Module | Path | Responsibility | Key Files |
     |------------|------|----------------|-----------|
   
   - Explain how the sub-modules relate.
   - Ask: **"Should I split this into sub-module docs, or document it as one unit?"**
   - If confirmed: proceed with split workflow (Step 6B below).
   - If declined: proceed as a single subsystem doc.

3. If the subsystem is small enough: proceed directly to Step 2.

### Step 2: Read the Subsystem

- **Small subsystem (<30 files):** Read all non-test files, sample tests.
- **Large subsystem (30+ files):** Read central files fully, sample
  repetitive leaves. Note what was sampled.
- Read entry files identified in the analysis state.

### Step 3: Analyze

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

**Design Decisions (2-4):**
1. What was chosen
2. What it enables
3. What it costs
4. Alternative approaches
5. Assessment

**Testing:**
- What test files exist?
- What is covered vs. not?
- What test patterns are used?
- Notable test utilities, mocks, or fixtures?

**Edge Cases & Gotchas:**
- Implicit contracts or ordering requirements
- Race conditions or concurrency concerns
- Known limitations or tech debt
- Behavior that would surprise a new contributor

### Step 4: Capture Patterns

Observe and record code and test conventions **specific to this
subsystem** (beyond the system-wide patterns from Phase 1):

- Naming conventions that differ from or extend the system-wide ones
- Error handling style
- Test structure and fixture patterns
- Any recurring abstractions or internal patterns

### Step 5: Identify Modification Guidance

This is the most agent-valuable part. Determine:

- **Invariants:** What contracts, ordering guarantees, or state
  assumptions must not be broken when modifying this subsystem?
- **"How to add a new X":** For the most common change type in this
  subsystem (new handler, new adapter, new test, etc.), what is the
  step-by-step pattern? Which files get touched? Which existing file
  is the best template to copy from?
- **Files commonly changed together:** Which files are tightly coupled
  and usually modified as a group?
- **Gotchas for modifications:** What would a coding agent likely get
  wrong on the first attempt?

### Step 6A: Write Single Subsystem Document

If NOT splitting into sub-modules, write to
`agent-docs/subsystems/{subsystem-name}.md`:

```markdown
# {Subsystem Name}

## Why This Subsystem Exists
{1 paragraph}

## Boundaries
| Aspect | Detail |
|--------|--------|
| Path | `{path}` |
| Role | `{tag}` |
| Inputs | {description} |
| Outputs | {description} |
| State | {description or "none"} |

## Evidence Anchors
- `{file:line}` - {why it matters}

## Internal Structure
| Unit | Responsibility | Why It Matters |
|------|----------------|----------------|

## Key Contracts and Types
| Contract / Type | Defined In | Purpose | Used By |
|-----------------|------------|---------|---------|

## Main Flows
### {Flow}
- Trigger: {what starts it}
- Handoffs: {A -> B -> C}
- Failure handling: {how errors move}
- Async boundaries: {if any}
- Evidence: `{file:line}`

## Dependencies
### Internal
| Dependency | Why | Direction |
|------------|-----|-----------|

### External
| Package | Purpose | Load-Bearing? |
|---------|---------|---------------|

## Configuration
- Config inputs: {files/env/flags}
- State owned: {what and where}
- Defaults: {if any}

## Code and Test Patterns
| Pattern | Usage | Example File |
|---------|-------|--------------|

### Test Conventions
- Framework: {name}
- Location: {colocated / separate}
- Structure: {describe/it, table-driven, etc.}
- Fixtures/mocks: {patterns}
- Coverage: {full / sampled / gaps}

## Modification Guide
- **Invariants to preserve:** {list}
- **To add a new {common change type}:**
  1. {step}
  2. {step}
  3. {step}
  - Best template to copy from: `{file}`
- **Files commonly touched together:** {list}
- **Gotchas:** {list}

## Design Decisions and Trade-offs
### {Decision}
- Chosen: {pattern}
- Enables: {benefit}
- Costs: {cost}
- Alternative: {option}
- Assessment: {observation}

## Edge Cases and Gotchas
- {item}

## Open Questions
- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}

## Coverage Notes
- Read fully: {files}
- Sampled: {files}
- Skipped: {files, with reason}
```

### Step 6B: Write Split Documents (if decomposing)

If splitting into sub-modules:

**1. Write parent doc** to `agent-docs/subsystems/{subsystem-name}.md`:
- Same template as Step 6A but with an added **Sub-Modules** section:

  | Sub-Module | Path | Responsibility | Doc |
  |------------|------|----------------|-----|

- Design Decisions, Configuration, and system-level patterns go here.
- Modification Guide covers cross-sub-module changes.

**2. Write sub-module docs** to `agent-docs/subsystems/{subsystem-name}/{sub-module}.md`:

```markdown
# {Sub-Module Name}

> Part of [{Parent Subsystem}](../{parent}.md)

## Why This Sub-Module Exists
{1 paragraph}

## Boundaries
| Aspect | Detail |
|--------|--------|

## Evidence Anchors
- `{file:line}` - {why}

## Internal Structure
| Unit | Responsibility |
|------|----------------|

## Key Contracts and Types
| Contract / Type | Defined In | Purpose | Used By |
|-----------------|------------|---------|---------|

## Main Flows
### {Flow}
- Trigger, handoffs, failure handling, evidence

## Dependencies
| Dependency | Why | Direction |
|------------|-----|-----------|

## Code and Test Patterns
| Pattern | Usage | Example File |
|---------|-------|--------------|

## Modification Guide
- **Invariants:** {list}
- **To add new code:** {pattern, files}
- **Gotchas:** {list}

## Edge Cases
- {item}

## Open Questions
- `UNCERTAIN:` / `NEEDS CLARIFICATION:` items

## Coverage Notes
- Read fully / sampled / skipped
```

### Step 7: Update Analysis State

Update `agent-docs/.analysis-state.md`:
- Move this subsystem from `subsystems_pending_deep_dive` to `subsystems_completed`
- If split, record the sub-modules under the subsystem entry

### Step 8: Report Next Steps

After writing, tell the user:

> **Phase 2 — Deep dive on {subsystem} complete.** [{N}/{total} subsystems done]
>
> Written: `agent-docs/subsystems/{subsystem-name}.md`
> {If split: + `agent-docs/subsystems/{subsystem-name}/{sub-module}.md` x {count}}
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

If `agent-docs/subsystems/{subsystem-name}.md` already exists:

1. Read the existing document first
2. Compare against current code state
3. Update sections that have changed
4. Preserve sections that are still accurate
5. Add a note at the top: `> Updated on {date}. Previous analysis preserved where still accurate.`
