You are running Phase 2 of a 3-phase codebase analysis workflow.
The primary goal is to produce documentation that helps coding agents
gain deep codebase context.

## Target Subsystem

$ARGUMENTS

---

## Shared Resources

Look for shared reference files at `~/.claude/codebase-analysis/`.
If available, load on demand:
- `references/scale-and-scope.md` — reading depth and recursion thresholds
- `references/subsystem-mapping-rubric.md` — for recursive decomposition
- `references/pattern-detection-guide.md` — pattern identification
- `references/validation-rules.md` — self-check criteria
- `templates/subsystem-template.md` — output structure for subsystems
- `templates/sub-module-template.md` — lighter output structure for sub-modules

---

## First: Read Analysis State

Read `agent-docs/.analysis-state.md` and `agent-docs/system-overview.md`
before doing anything else. These were produced in Phase 1.

From the analysis state, determine:
- Which subsystem the user is asking about (match `$ARGUMENTS`)
- What subsystems have already been deep-dived
- What subsystems remain
- Whether this subsystem is flagged as a recursion candidate

If `agent-docs/.analysis-state.md` does not exist, tell the user:

> **Phase 1 has not been run yet.** Run
> `/user:analyze-discover {description}` first.

Then stop.

If `$ARGUMENTS` does not match any subsystem in the map, list the
available subsystems and ask the user to clarify.

If `selected_scope` is present in the analysis state and the target
subsystem is NOT in the selected scope, warn the user:

> **{subsystem} is not in the selected scope.** Selected subsystems:
> {list}. To add it, re-run `/user:analyze-discover` to update scope.
> Or say "analyze anyway" to proceed.

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

Produce a deep architectural understanding of the **{subsystem}**
subsystem. Read-only. Factual. Output a durable document that coding
agents use to navigate and work within this part of the codebase.

## Hard Constraints

- **Read-only.** Do not modify any source code.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references.
- **Factual only.** Limit to observable analysis.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

## Anti-Patterns

Do not:

- confuse directory structure with architectural boundaries
- claim runtime behavior that static evidence does not support
- produce boilerplate prose that adds no insight
- skip the Modification Guide — it is the most agent-valuable section
- decompose a subsystem that is large but uniform (document the pattern
  instead)

## Quality Bar

A subsystem doc is good enough when a coding agent reading it can:

- understand what the subsystem does and where it fits
- find the right files to modify for a given task
- follow the correct patterns when adding new code
- avoid breaking invariants or implicit contracts
- know what areas are uncertain and need human verification

A subsystem doc is not good enough if it:

- reads like boilerplate architecture prose
- hides uncertainty or overstates confidence
- confuses code organization with architectural responsibility
- lacks a Modification Guide

---

## Procedure

### Step 1: Read the Subsystem

Using the path from the analysis state:

1. List all files in the subsystem directory
2. For small subsystems (<30 files): read all non-test files, sample
   tests
3. For large subsystems (30+ files): read central files fully, sample
   repetitive leaves. Note what was sampled.

### Step 2: Evaluate Recursion Need

Check whether this subsystem should be decomposed:

**Trigger conditions** (either one):
- 50+ non-generated source files in this subsystem
- 3+ internal modules that each have their own contracts or entrypoints

**If triggered:**
Present the decomposition proposal in chat:

> This subsystem is large enough to decompose into sub-modules:
> - **{sub-1}** (`{path}`): {responsibility} ({N} files)
> - **{sub-2}** (`{path}`): {responsibility} ({N} files)
> - **{sub-3}** (`{path}`): {responsibility} ({N} files)
>
> I'll write a parent overview doc plus individual sub-module docs.
> **Confirm? Or should I analyze as a single unit?**

Wait for user confirmation before proceeding.

**If confirmed for recursion:**
- Write parent doc at `agent-docs/subsystems/{name}.md` covering:
  overview, internal map, cross-cutting concerns, how sub-modules
  connect
- Deep-dive each sub-module, writing to
  `agent-docs/subsystems/{name}/{child}.md`
- Apply the same analysis procedure to each child
- Recursion applies up to depth 3. At depth 3: summarize, don't
  decompose further.

**If NOT triggered or user declines:**
Proceed with a single flat document.

**When NOT to decompose** (even if thresholds are met):
- Many files following one pattern (50 similar handlers): document the
  pattern, not each file.
- Mechanically generated files.
- Single clear responsibility despite many files.

### Step 3: Analyze

Investigate these dimensions for the subsystem (or each sub-module
if recursive):

**a) Boundaries & Role**
- What does it do and why does it exist separately?
- What are its inputs (who calls it, what triggers it)?
- What are its outputs (what it returns, emits, or changes)?
- What state does it own, if any?

**b) Internal Structure**
- How are files organized?
- What are the key units and their responsibilities?

**c) Contracts & Types**
- Key exported types, interfaces, traits, or classes
- For each: where defined, purpose, who creates it, who consumes it

**d) Flows**
- Trace each entry point through the subsystem
- Note happy path, error handling, async boundaries
- Note handoffs to other subsystems

**e) Dependencies**
- Internal: what other subsystems does it import? What imports it?
- External: what third-party packages? Which are load-bearing?
- Flag circular dependencies or surprising coupling

**f) Configuration**
- Config values that affect this subsystem
- Defaults assumed
- Environment-specific behavior

**g) Design Decisions (2-4)**
- What was chosen, what it enables, what it costs
- Alternative approaches
- Assessment

**h) Testing**
- What test files exist
- What is covered vs. not
- Test patterns (table-driven, BDD, snapshot, integration, etc.)
- Notable test utilities, mocks, or fixtures

**i) Edge Cases & Gotchas**
- Implicit contracts or ordering requirements
- Race conditions or concurrency concerns
- Known limitations, tech debt (TODO comments, workarounds)
- Behavior that would surprise a new contributor

**j) Modification Guide** (most agent-valuable section)
- What invariants must be preserved when modifying this subsystem?
- For the most common change type: what is the step-by-step pattern?
  Which files get touched? Which existing file is the best template?
- Which files are tightly coupled and usually modified together?
- What would a coding agent likely get wrong on the first attempt?

**k) Pattern Detection**
- Identify repetitive file structures within this subsystem
- For each pattern: name, category, example file (cleanest instance),
  file list, registration/wiring points
- Record these for Phase 3's `patterns.md` consolidation

### Step 4: Write Subsystem Document

Write to `agent-docs/subsystems/{subsystem-name}.md`.

If `~/.claude/codebase-analysis/templates/subsystem-template.md` exists,
use its structure. Otherwise use this structure:

```markdown
# {Subsystem Name}

## Why This Subsystem Exists
{1 paragraph}

## Boundaries
| Aspect | Detail |
|--------|--------|
| Path | `{path}` |
| Role | `{tag}` |
| Inputs | {who calls it} |
| Outputs | {what it returns/emits} |
| State | {what it owns, or "none"} |

## Sub-subsystems
{List child docs if recursion applied, or "None"}

## Evidence Anchors
- `{file:line}` — {why it matters}

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

## Configuration and State
- Config inputs, state owned, defaults

## Design Decisions and Trade-offs
### {Decision}
- Chosen, enables, costs, alternative, assessment

## Testing
- Coverage mode, test files, patterns, fixtures, gaps

## Modification Guide
- **Invariants to preserve:** {list}
- **To add a new {common change type}:**
  1. {step}
  2. {step}
  - Best template to copy from: `{file}`
- **Files commonly touched together:** {list}
- **Gotchas:** {list}

## Edge Cases and Gotchas
- {items}

## Detected Patterns
| Pattern | Category | Example File | File Count |
|---------|----------|--------------|------------|

## Open Questions
- `UNCERTAIN:` ...
- `NEEDS CLARIFICATION:` ...

## Coverage Notes
- Read fully / sampled / skipped
```

If recursion was applied, also write child docs at
`agent-docs/subsystems/{name}/{child}.md` using the lighter
sub-module template (`sub-module-template.md`). Sub-module docs
drop standalone Design Decisions and Configuration sections (those
are captured at the parent level) and target ~60% the length of a
full subsystem doc.

### Step 4b: Self-Validate Subsystem Document

Before updating state, verify the document you just wrote:

If `~/.claude/codebase-analysis/references/validation-rules.md` exists,
load it and run the Phase 2 checks. Otherwise use these inline checks:

1. Document has all required sections (check for: Modification Guide,
   Evidence Anchors, Main Flows, Coverage Notes — the most commonly
   missed)
2. Modification Guide is non-empty with invariants and step-by-step
3. At least one flow traced with file references
4. Evidence Anchors has >= 2 file:line references
5. Coverage Notes states what was read/sampled/skipped

If any check fails, fix the document before proceeding.

### Step 5: Update Analysis State

Update `agent-docs/.analysis-state.md`:
- Move this subsystem from `subsystems_pending` to
  `subsystems_completed`
- Record detected patterns
- If recursion was applied, record the sub-module structure

### Step 6: Report Next Steps

After writing, tell the user:

> **Phase 2 — Deep dive on {subsystem} complete.**
> [{N}/{total} subsystems done]
>
> Written: `agent-docs/subsystems/{subsystem-name}.md`
> {If recursion: Also written: `agent-docs/subsystems/{name}/{children}`}
>
> **Remaining subsystems:**
> - `/user:analyze-deep-dive {next}` — {reason for order}
> - ...
>
> **When all subsystems are done:** Run `/user:analyze-synthesize`

If this was the last subsystem:

> **All subsystems analyzed.** Run `/user:analyze-synthesize` to
> produce the final documentation set including `agent-context.md`.

---

## Re-run Behavior

If `agent-docs/subsystems/{subsystem-name}.md` already exists:

1. Read the existing document first
2. Compare against current code state
3. Update sections that have changed
4. Preserve sections that are still accurate
5. Add note: `> Updated on {date}. Previous analysis preserved where
   still accurate.`
6. If subsystem was previously flat but now qualifies for recursion,
   propose decomposition. Keep existing doc as starting point for parent.
