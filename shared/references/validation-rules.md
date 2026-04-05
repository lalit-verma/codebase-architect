# Output Validation Rules

Self-check criteria for each phase. The analyzing agent runs these
checks against its own output BEFORE reporting completion. Every
criterion is pass/fail. If any criterion fails, fix the output
before proceeding.

## Phase 1: Discover & Map — Self-Validation

Run after preparing the checkpoint, before presenting to user.

1. Checkpoint has all 8 sections (Classification, Understanding,
   Subsystems, Flows, Patterns, Coverage, Questions, Doc Plan)
2. Subsystem table has all required columns (Subsystem, Path, Role,
   Responsibility, Evidence Anchors, Dependencies, Confidence,
   Recursion)
3. Every subsystem row has >= 2 evidence anchors (concrete file paths)
4. system-overview.md has all required sections: Purpose, External
   Boundaries, Architectural Shape, Major Subsystems, Primary Flows,
   State and Configuration, Design Observations
5. .analysis-state.md has all required YAML fields: phase_completed,
   generated_on, output_root, subsystems_pending, subsystems_completed,
   recursion_candidates, preliminary_patterns
6. If monorepo or very-large: scope selection was presented and
   selected_scope is recorded in state

## Phase 2: Deep Dive — Self-Validation

Run after writing subsystem doc, before updating state.

1. Document has all required sections: Why This Subsystem Exists,
   Boundaries, Evidence Anchors, Internal Structure, Key Contracts,
   Main Flows, Dependencies, Configuration, Design Decisions, Testing,
   Modification Guide, Edge Cases, Detected Patterns, Open Questions,
   Coverage Notes
2. Modification Guide is non-empty and contains: invariants,
   step-by-step for most common change type, files commonly touched
   together, gotchas
3. At least one flow is traced with file references at each handoff
4. Evidence Anchors section has >= 2 concrete file:line references
5. Coverage Notes section is non-empty (states what was read fully,
   sampled, and skipped)

## Phase 3: Synthesize — Self-Validation

Run after generating agent-context.md, before generating remaining
docs.

1. agent-context.md is under 120 lines (count them)
2. agent-context.md contains no markdown tables (no `|` characters
   used as column separators outside of code blocks)
3. agent-context.md contains no confidence labels (no "Confirmed:",
   "Inference:", "UNCERTAIN:", "NEEDS CLARIFICATION:")
4. agent-context.md has all 7 required sections: What this repo is,
   Architecture map, Key patterns, Conventions, Do NOT, Key contracts,
   For deeper context
5. Every Architecture map entry has a concrete file path in backticks
6. Every Key patterns entry has numbered steps with file paths
7. Every Key contracts entry has a file:line reference

## Phase 3: Quality Smoke Test

Run after ALL docs are generated, before reporting completion. Read
agent-context.md and attempt to answer these 5 questions using ONLY
that file's content. Replace bracketed placeholders with actual values
from the analyzed repository.

**Question 1:** "Where would I create a new [most common entity type
from preliminary patterns]?"
- PASS: answer yields a concrete file path from the Key patterns section
- FAIL: no pattern covers this entity, or path is vague

**Question 2:** "What pattern should I follow for [most common entity
type]?"
- PASS: Key patterns section has numbered steps for this entity type
- FAIL: no matching pattern, or steps are abstract without file paths

**Question 3:** "What should I NOT do in this codebase?"
- PASS: Do NOT section has >= 3 entries with specific reasons
- FAIL: section is missing, empty, or contains only generic advice

**Question 4:** "Which subsystem handles [primary flow identified in
Phase 1]?"
- PASS: Architecture map has an entry that clearly maps to this flow
- FAIL: the primary flow cannot be located from agent-context.md alone

**Question 5:** "What are the key interfaces or contracts?"
- PASS: Key contracts section has >= 2 entries with file:line references
- FAIL: section is missing or entries lack file references

If any question FAILS: identify the gap, fix agent-context.md, and
re-run the failing check. Do not proceed to Report Completion until
all 5 pass.
