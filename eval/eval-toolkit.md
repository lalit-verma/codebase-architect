# Toolkit Evaluation Rubric

Evaluate the codebase analysis framework itself — its prompts,
templates, references, and cross-platform consistency. This does NOT
evaluate output produced by the tool; use `eval-output.md` for that.

## How to Use

1. Read every file in the framework (shared/, claude-code/, codex/,
   cursor/, README.md). There are ~35 files.
2. Evaluate each of the 8 dimensions below.
3. For each dimension, produce:
   - **Verdict:** PASS / PARTIAL / FAIL
   - **Evidence:** Quote specific passages that support the verdict.
   - **Gaps:** What is missing or insufficient. Cite file and section.
4. Produce the synthesis section at the end.

## Rules

- Quote, don't paraphrase. Every verdict must cite the actual text.
- PASS means all criteria in the dimension are fully met.
- PARTIAL means most criteria met but with notable gaps.
- FAIL means fundamental criteria are missing.
- Be specific about which file and section each finding comes from.

### Critical-Fail Overrides

These conditions automatically cap the overall grade regardless of
other dimension scores. Check these FIRST.

**Auto-FAIL D1 (caps overall at "Needs Work" max):**
- No dedicated agent-context rules file exists
- No filled-out agent-context example exists
- No line budget is specified anywhere

**Auto-FAIL D4 (caps overall at "Good" max):**
- One of the three platforms (Claude Code, Codex, Cursor) is entirely
  missing or has no functional equivalent of the other two
- Self-validation steps are present in only 1 of 3 platforms

These overrides apply after scoring. If triggered, note in synthesis
and adjust the final grade.

---

## Dimension 1: Primary Deliverable Specification

**Weight: 3x** — this spec governs the file loaded on every agent session.

The primary deliverable is `agent-context.md`. How well is it spec'd?

Check for:

- **Dedicated rules file** (`shared/references/agent-context-rules.md`)
  exists and defines: line budget, no-tables rule, no-confidence-labels
  rule, flat markdown requirement, standalone constraint, regeneration
  on re-run policy
- **Required sections** are enumerated with content guidance for each
  (What this repo is, Architecture map, Key patterns, Conventions,
  Do NOT, Key contracts, For deeper context)
- **Concrete filled-out example** (`shared/examples/agent-context-example.md`)
  exists and demonstrates the target quality — not just a template with
  placeholders, but a realistic completed file
- **Quality checklist** with measurable pass/fail items (not just
  aspirational descriptions)
- **Content sourcing table** mapping each section to its source doc
- **Platform notes** confirming content is identical across Claude Code,
  Codex, and Cursor — only wiring differs
- **Token budget** is explicit (a number, not "keep it short")

---

## Dimension 2: Pattern Detection Pipeline

**Weight: 2x** — patterns directly prevent convention drift at runtime.

Patterns are the highest-impact output. How thorough is the pipeline?

Check for:

- **Dedicated detection guide** (`shared/references/pattern-detection-guide.md`)
  with: definition of what counts as a pattern, minimum instance
  threshold (3+), detection method per phase
- **Pattern categories** defined (endpoint, service, model, etc.) with
  tagging requirement
- **Negative guidance** — explicit list of what is NOT a pattern
  (single-instance files, generic idioms, generated code, framework
  boilerplate)
- **3-phase progression** documented: Phase 1 preliminary detection,
  Phase 2 per-subsystem refinement, Phase 3 consolidation
- **Semi-automated confirmation** — agent proposes, user confirms
  before writing to durable docs. Check that this is in the synthesize
  command, not just the guide.
- **Output format** defined with: recipe steps (not just descriptions),
  example file, file count, registration point, anti-patterns
- **Patterns template** (`shared/templates/patterns-template.md`) with
  the recipe structure

---

## Dimension 3: Subsystem Doc Completeness

**Weight: 2x** — subsystem docs are the second file agents load per-task.

Subsystem docs are the deep reference agents load per-task.

Check for:

- **Subsystem template** (`shared/templates/subsystem-template.md`)
  lists all required sections. Count them — should be 16: Why It Exists,
  Boundaries, Sub-Modules, Evidence Anchors, Internal Structure, Key
  Contracts, Main Flows, Dependencies, Configuration, Design Decisions,
  Testing, Modification Guide, Edge Cases, Detected Patterns, Open
  Questions, Coverage Notes
- **Modification Guide** section is present in the template with:
  invariants, step-by-step for common changes, files touched together,
  gotchas. Check that the deep-dive command explicitly calls this out
  as "most agent-valuable section."
- **Lighter sub-module template** exists for recursive children
  (`shared/templates/sub-module-template.md`), drops Design Decisions
  and Configuration, targets ~60% length
- **Recursive decomposition rules** defined: trigger thresholds,
  depth limit (should be 3), when NOT to decompose
- **Subsystem mapping rubric** defines what counts as a subsystem
  (2-of-6 criteria), split/merge guidance, naming guidance, confidence
  levels, minimum evidence requirements
- **No tables** in the subsystem template (bullet-only format for
  token efficiency)
- **Inline fallback consistency.** The deep-dive commands contain an
  inline template used when `shared/` is not installed. Check that
  the inline template in `claude-code/commands/analyze-deep-dive.md`
  and `codex/prompts/2-deep-dive.md` matches the standalone
  `shared/templates/subsystem-template.md` in format (both should use
  bullets, not tables). If the inline version uses tables while the
  standalone uses bullets, the fallback path produces lower-quality
  output.

---

## Dimension 4: Cross-Platform Parity

**Weight: 2x** — inconsistency across platforms means some users get worse output.

Three platforms must have equivalent capability.

Check for:

- **Claude Code:** 3 command files in `claude-code/commands/`
  (discover, deep-dive, synthesize) with full procedural instructions
- **Codex:** `AGENTS.md` behavioral contract + 3 prompt files in
  `codex/prompts/` mirroring the commands
- **Cursor:** `SKILL.md` with YAML frontmatter, auto-trigger keywords,
  and complete 3-phase workflow inline
- **Self-validation steps** present in ALL 3 platforms (not just one).
  Check: Phase 1 checkpoint validation, Phase 2 subsystem doc
  validation, Phase 3 agent-context validation
- **Quality smoke test** present in Phase 3 across ALL 3 platforms
- **Scope selection** for monorepos present in Phase 1 across ALL 3
- **Inline fallback content** in Claude Code commands for when shared/
  is missing — commands should be self-contained at reduced quality
- **Consistent output** — all platforms produce the same `agent-docs/`
  structure with the same file set

Cross-check: pick one specific feature (e.g., the smoke test) and
verify it appears with equivalent detail in all 3 platform files.

Secondary cross-check: compare the inline subsystem template in the
Claude Code deep-dive command against the Codex deep-dive prompt. Do
they use the same format (tables vs bullets)? Do they have the same
sections? Format divergence between platforms means agents on different
platforms produce structurally different subsystem docs.

---

## Dimension 5: Behavioral Specification

**Weight: 1x**

Is the tool's behavior fully defined in one place?

Check for:

- **Single canonical spec** (`shared/protocol.md`) exists and covers:
  core objectives, hard rules, output root, output priority, 3-phase
  model, state persistence, re-run semantics, confidence labels,
  citation policy
- **Quality bar** defined with both positive criteria ("good enough
  when...") and negative criteria ("not good enough if...")
- **Failure modes** explicitly listed (not just implied by quality bar)
- **Output priority hierarchy** — which file matters most, which is
  secondary
- **Re-run semantics** defined per file type: which files are
  regenerated entirely vs updated selectively
- **Repo-type priorities** — different guidance for applications,
  libraries, frameworks, monorepos

---

## Dimension 6: Self-Validation and Quality Gates

**Weight: 2x** — without self-validation, quality depends entirely on the LLM's judgment.

Does the framework verify its own output?

Check for:

- **Validation rules file** (`shared/references/validation-rules.md`)
  with pass/fail criteria for each phase
- **Phase 1 validation** integrated into discover commands (checkpoint
  completeness, evidence anchor counts)
- **Phase 2 validation** integrated into deep-dive commands (required
  sections, Modification Guide non-empty, flows traced, coverage notes)
- **Phase 3 validation** integrated into synthesize commands
  (agent-context.md line count, no tables, no labels, all sections,
  file path density)
- **Quality smoke test** — 5 diagnostic questions that test whether
  agent-context.md is standalone. Check that the questions are specific
  enough to have clear pass/fail outcomes.
- **Confirmation gates** — at least: Phase 1 subsystem map
  confirmation, Phase 3 pattern confirmation before writing. Are there
  any important docs that get written without any confirmation gate?

---

## Dimension 7: Shared Reference Quality

**Weight: 1x**

The references govern how well the analyzing agent explores any
codebase.

Check for:

- **Ecosystem playbook** (`shared/references/ecosystem-playbook.md`):
  how many languages covered? Are there actual bash commands (not just
  descriptions)? Is there a generic fallback? Count the languages with
  full detection heuristics + exploration commands + architectural
  signals.
- **Scale-and-scope rules** (`shared/references/scale-and-scope.md`):
  4 size tiers defined? Sampling rules explicit? Generated code
  handling? Stop conditions listed? Write eligibility criteria?
  Recursive decomposition thresholds?
- **Subsystem mapping rubric**: 2-of-6 criteria? Split/merge guidance?
  Naming guidance? Confidence levels? Minimum evidence requirements?
  Monorepo-specific rules?
- **Scope selection rules**: trigger conditions for monorepos?
  Structured table format? Centrality categories? State tracking
  fields? Phase 2 scope-awareness? Scope expansion mechanism?
- **Checkpoint template**: all 8 sections defined? Scope selection
  section for monorepos? Mandatory closing question?
- **Checkpoint example**: filled-out example for quality calibration?

---

## Dimension 8: Output Schema and Wiring

**Weight: 1x**

The last mile — connecting generated docs to the coding agent.

Check for:

- **docs-schema.md** defines the full output tree with priority order
  and consumer labels (coding agents vs humans vs both), and
  documents the hybrid wiring strategy (inlined nano-digest +
  Explore-enrichment line)
- **agent-context-nano template** exists at
  `shared/templates/agent-context-nano-template.md` with:
  - Hard ceiling of 40 lines documented
  - 5 required sections (What this is, Where things live, 2 patterns,
    Do NOT)
  - Explicit prohibition on `agent-docs/` references inside the file
  - Sourcing rules tying every nano section back to a section of
    `agent-context.md`
- **nano-context-rules.md** exists at
  `shared/references/nano-context-rules.md` with hard constraints,
  required sections, exclusions table, and quality check list
- **agent-protocol template** provides hybrid wiring for all 3
  platforms with: a placeholder for the inlined nano-digest, the
  Explore-enrichment line (point at `agent-docs/agent-context.md`,
  list deeper docs, prohibit main-thread reads). Must NOT include a
  5-step loading protocol or "quote the specific pattern"
  requirement — those were removed in the hybrid wiring change.
- **routing-map template** defines machine-readable YAML structure
  for task-to-doc routing with: subsystem_routing (owns_paths,
  key_files, key_tests, common_tasks) and pattern_routing
  (template_file, registration, test_template)
- **Version tracking** across all templates: standardized header
  format, git commit capture instruction in synthesize commands,
  version fields in .analysis-state.md schema
- **README.md** includes the hybrid wiring instructions for all 3
  platforms (paste nano-digest into config + add Explore-enrichment
  line) and the rationale section ("Why hybrid wiring") that ties
  the design to the benchmark findings

---

## Synthesis

After evaluating all 8 dimensions, produce:

### Score Card

| Verdict | Score |
|---------|-------|
| PASS | 2 |
| PARTIAL | 1 |
| FAIL | 0 |

| Dimension | Weight | Verdict | Weighted Score | Key Finding |
|-----------|--------|---------|----------------|-------------|
| D1: Primary Deliverable | 3x | | /6 | |
| D2: Pattern Pipeline | 2x | | /4 | |
| D3: Subsystem Docs | 2x | | /4 | |
| D4: Cross-Platform Parity | 2x | | /4 | |
| D5: Behavioral Spec | 1x | | /2 | |
| D6: Self-Validation | 2x | | /4 | |
| D7: Shared References | 1x | | /2 | |
| D8: Schema and Wiring | 1x | | /2 | |
| **Total** | | | **/28** | |

### Grade Bands

| Score | Grade | Interpretation |
|-------|-------|----------------|
| 24-28 | Excellent | Framework is production-ready |
| 18-23 | Good | Usable, fix identified gaps |
| 12-17 | Needs Work | Significant gaps reduce output quality |
| <12 | Fundamental Issues | Major redesign needed |

### Prioritized Gaps

List every gap found. Categorize as **critical** (would cause agents
to produce wrong output), **important** (reduces output quality), or
**minor** (cosmetic or edge-case):

1. {gap} — {severity} — {which dimension} — {specific file and section} — {suggested fix}
2. ...

### Strengths

List the framework's strongest aspects — what should NOT be changed:

1. {strength} — {evidence}
2. ...
