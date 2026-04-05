# Output Evaluation Rubric

Evaluate the `agent-docs/` documentation produced by the codebase
analysis framework after running on a real repository. This grades
the output quality, not the framework itself (use `eval-toolkit.md`
for that).

## Prerequisites

You need access to:
1. The `agent-docs/` directory produced by the tool
2. The source repository that was analyzed (for spot-checking
   file references and architectural claims)

## How to Use

### Reading Order

Read the output in this exact order — it mirrors how a coding agent
would consume the docs, and surfaces problems in dependency order:

1. List all files in `agent-docs/` — note which exist and which are
   missing against the expected set
2. Read `agent-docs/agent-context.md` FIRST and fully — this is the
   primary deliverable
3. Read `agent-docs/routing-map.md` — the machine-readable lookup
4. Read `agent-docs/patterns.md` — the pattern recipes
5. Sample 2-3 subsystem docs from `agent-docs/subsystems/` — pick one
   large/central subsystem and one smaller/peripheral one
6. Read `agent-docs/agent-protocol.md` — wiring instructions
7. Skim: `agent-docs/agent-brief.md`, `agent-docs/index.md`,
   `agent-docs/decisions.md`, `agent-docs/uncertainties.md`
8. Read `agent-docs/.analysis-state.md` — internal state

As you read, keep a running list of:
- File references that need spot-checking against the source repo
- Cross-file inconsistencies (names, paths, patterns that don't match)
- Sections that feel thin, vague, or boilerplate

### Evaluation Structure

For each of the 10 dimensions below, produce:

> **Dimension N: {Name}** (weight: {Nx})
>
> **Verdict:** PASS / PARTIAL / FAIL
>
> **Evidence:** Quoted passages from the evaluated files that support
> the verdict. Include file path and line context.
>
> **Gaps:** Specific deficiencies with file path and section where the
> gap exists. For each gap, note whether it's critical (would cause an
> agent to make a wrong decision) or minor (suboptimal but not harmful).
>
> **Spot-checks performed:** List any file:line references you verified
> against the source repo, with results.

### Rules

- Quote actual text from the output files. Do not paraphrase.
- PASS = all criteria in the dimension fully met with evidence.
- PARTIAL = most criteria met but with notable gaps that reduce agent
  effectiveness.
- FAIL = fundamental criteria missing — an agent relying on these docs
  would make wrong decisions or be unable to navigate the repo.
- When spot-checking file references against the source repo, check at
  least the number specified per dimension. Record each check result.
- Be harsh. The purpose is to find gaps, not to validate.

### Critical-Fail Overrides

These conditions automatically cap the overall grade regardless of
other dimension scores. Check these FIRST before scoring dimensions.

**Auto-FAIL D1 (caps overall at "Needs Work" max):**
- agent-context.md exceeds 120 lines
- agent-context.md contains markdown tables
- Standalone test: Q1, Q2, or Q3 all FAIL (agent cannot find where
  to create files, what pattern to follow, or what to avoid — the
  three most basic questions)

**Auto-FAIL D10 (caps overall at "Good" max):**
- Task 1 (most common change) grades FAIL — if the docs can't guide
  the most frequent task type, they're not production-ready

**Auto-FAIL D6 (caps overall at "Needs Work" max):**
- agent-context.md is missing entirely
- More than 3 expected files from the output set are missing

These overrides apply after scoring. If a critical-fail is triggered,
note it in the synthesis and adjust the final grade accordingly.

---

## Expected Output File Set

Before scoring dimensions, verify the complete file set exists:

```
agent-docs/
  .analysis-state.md          # internal state
  agent-context.md            # PRIMARY
  patterns.md                 # pattern recipes
  routing-map.md              # task-to-doc routing
  agent-brief.md              # compact architecture
  agent-protocol.md           # wiring instructions
  index.md                    # navigation hub
  system-overview.md          # top-level architecture
  decisions.md                # trade-offs
  glossary.md                 # terms
  uncertainties.md            # open questions
  subsystems/
    {name}.md                 # one per subsystem
    {name}/                   # sub-module docs (if decomposed)
      {child}.md
  flows/                      # optional
    {name}.md
```

Note any missing files. Note any unexpected files.

---

## Dimension 1: agent-context.md Quality

**Weight: 3x** (this is the single most important file)

This file is loaded by every coding agent at every session start. Every
deficiency here costs efficiency across all future tasks in the repo.

### Structural Checks

1. **Line count.** Count the actual lines in the file. The hard limit
   is 120. If over 120, this is an automatic FAIL for this dimension.
   Record the exact count.

2. **Table scan.** Search for `|` characters that form markdown table
   syntax (exclude `|` inside inline code backticks or code blocks).
   Tables are prohibited. If any table exists, note it.

3. **Confidence label scan.** Search for these exact strings:
   `Confirmed:`, `Inference:`, `UNCERTAIN:`, `NEEDS CLARIFICATION:`.
   None should appear. These belong in analysis docs, not in the
   agent-facing context file.

4. **Section completeness.** Verify all 7 required sections exist, in
   this order:
   - `## What this repo is` (2-3 sentences)
   - `## Architecture map` (bullet list of paths)
   - `## Key patterns` (with `### To add a new {thing}` sub-headings)
   - `## Conventions` (bullet list with file references)
   - `## Do NOT` (bullet list with reasons)
   - `## Key contracts` (bullet list with file:line references)
   - `## For deeper context` (pointers to other agent-docs/ files)

### Content Quality Checks

5. **Architecture map density.** Count entries in the Architecture map
   section. Should be 8-20. Each entry must have a file path in
   backticks. Count entries without backtick paths — each is a defect.

6. **Pattern recipe format.** Each Key patterns entry must have:
   - A `### To add a new {thing}` heading
   - Numbered steps (1. 2. 3.)
   - File paths in at least 2 of the steps
   Count patterns that lack numbered steps or file paths.

7. **Convention specificity.** Each Conventions entry should reference
   a specific file in parentheses: `(see \`{file}\`)`. Count entries
   without file references. Generic conventions like "follow best
   practices" are defects.

8. **Anti-pattern specificity.** Each Do NOT entry should have a
   reason after the em dash: `{what} — {why}`. Count entries without
   reasons. Should be 3-8 entries total.

9. **Contract precision.** Each Key contracts entry should have a
   `file:line` reference (not just a file name). Count entries with
   only file names (no line numbers) — these are partial credit, not
   full defects.

10. **Version header.** Must contain: timestamp, version identifier,
    and source commit. Check format matches:
    `> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}`

### Standalone Test (the critical test)

Close all other files. Read ONLY agent-context.md. Attempt to answer
these 7 questions. For each, record the answer you can derive and
whether it's sufficient.

Note: Q1-Q5 overlap with the tool's built-in smoke test
(`validation-rules.md`). If the tool ran its self-validation correctly,
Q1-Q5 should pass. Q6-Q7 are ADDITIONAL questions the tool does NOT
self-check — these test beyond the tool's own quality gate.

**Q1: "Where would I create a new [most common entity type in this
repo]?"**
- Look in Key patterns for a matching recipe
- PASS: a recipe exists with a concrete file path for where to create
- FAIL: no matching recipe, or the path is vague ("in the handlers
  directory" instead of `src/handlers/{name}.ts`)

**Q2: "What pattern should I follow for [that same entity type]?"**
- Look in Key patterns for numbered steps
- PASS: 3+ numbered steps with file paths, including registration and
  test steps
- FAIL: steps are abstract, missing file paths, or incomplete

**Q3: "What should I NOT do in this codebase?"**
- Look in Do NOT section
- PASS: 3+ specific entries with reasons tied to THIS codebase (not
  generic advice)
- FAIL: fewer than 3, or entries are generic ("don't write bad code")

**Q4: "Which subsystem handles [the primary flow identified in the
Architecture map]?"**
- Trace the primary flow through the Architecture map entries
- PASS: can identify which path/subsystem owns the flow
- FAIL: the flow is not traceable from the map, or subsystem boundaries
  are unclear

**Q5: "What are the key interfaces/contracts I must respect?"**
- Look in Key contracts section
- PASS: 2+ entries with file:line references that name specific
  interfaces, types, or abstractions
- FAIL: section missing, empty, or entries lack file references

**Q6 (beyond self-validation): "Where are tests for [the most common
entity type] and what test pattern do I follow?"**
- Look in Key patterns for a test step, and in Conventions for test
  structure
- PASS: agent-context.md specifies both the test file location
  convention and the test pattern (e.g., "tests use vitest with
  factory helpers")
- FAIL: test location is mentioned but test pattern/style is missing,
  or neither is mentioned

**Q7 (beyond self-validation): "If I encounter an error in this
codebase, how are errors handled?"**
- Look in Conventions for error handling style
- PASS: Conventions section describes the error handling pattern with
  a file reference (e.g., "Error wrapping with `AppError` class (see
  `src/errors.ts`)")
- FAIL: no error handling convention mentioned, or it's generic
  ("handle errors appropriately")

Record each Q as PASS/FAIL with the specific text you used to answer.

---

## Dimension 2: patterns.md Quality

**Weight: 2x**

Patterns prevent convention drift. An agent reading patterns.md should
be able to add a new instance of any documented pattern without looking
at existing code.

### Structural Checks

1. **Pattern count.** Count distinct patterns documented. Should be
   2-6 for a typical repo. If 0 or 1, that's likely a gap. If >10,
   question whether some are theoretical rather than real.

2. **Per-pattern completeness.** For EACH pattern, check:
   - [ ] Name with category tag (e.g., "API Endpoint Handler (endpoint)")
   - [ ] Example file path (cleanest instance)
   - [ ] File count (how many files follow this pattern)
   - [ ] Registration point (where new instances are wired, with
     file:line if applicable)
   - [ ] Recipe steps (numbered, with file paths)
   - [ ] Conventions within this pattern
   - [ ] Anti-patterns (what NOT to do)

   Record which patterns are complete and which are missing elements.

3. **Version header present.**

### Content Quality Checks

4. **Recipe actionability.** Pick the most detailed pattern. Could you
   follow its recipe steps to create a new instance without reading any
   other file? The steps should specify: what file to create (with path
   convention), what to put in it (with example file to copy from),
   where to register it, and what test to write.

5. **User confirmation.** Is there evidence that patterns were confirmed
   by the user? Look for phrases like "Confirmed by user", "User
   approved", or evidence of the semi-automated confirmation flow.

### Spot-Checks (against source repo)

6. **Example file verification.** Pick 2 patterns. For each, check that
   the "example file" path actually exists in the source repo. Record
   result.

7. **File count plausibility.** For those same 2 patterns, search the
   source repo for files matching the pattern's location/naming
   convention. Does the claimed file count seem accurate (within 20%)?

---

## Dimension 3: Subsystem Doc Quality

**Weight: 2x**

Sample 2-3 subsystem docs. Pick one central/large subsystem and one
smaller/peripheral one. Evaluate each separately then combine.

### Per-Doc Structural Checks

For each sampled subsystem doc:

1. **Section completeness.** Check all 16 required sections are present:
   Why This Subsystem Exists, Boundaries, Sub-Modules, Evidence Anchors,
   Internal Structure, Key Contracts, Main Flows, Dependencies (Internal
   + External), Configuration, Design Decisions, Testing, Modification
   Guide, Edge Cases, Detected Patterns, Open Questions, Coverage Notes.

   List any missing sections.

2. **Table check.** Scan for markdown tables. Agent-consumed subsystem
   docs should use bullets, not tables. Count tables found.

3. **Version header present.**

### Per-Doc Content Quality Checks

4. **Modification Guide depth.** This is the most agent-valuable
   section. Check that it contains ALL of:
   - [ ] Invariants to preserve (specific contracts, not vague)
   - [ ] Step-by-step for the most common change type (with file paths)
   - [ ] Best template to copy from (specific file name)
   - [ ] Files commonly touched together (specific list)
   - [ ] Gotchas for modifications (specific to this subsystem)

   If any component is missing or vague, note it. If the entire section
   is missing, that's a critical gap.

5. **Flow tracing quality.** Find the Main Flows section. At least one
   flow should be fully traced with:
   - Trigger (what starts it)
   - Handoffs (A -> B -> C with file references at each step)
   - Failure handling (how errors propagate)
   If flows are described abstractly without file references, that's a
   gap.

6. **Evidence anchor quality.** Count file:line references in the
   Evidence Anchors section. Should be >= 2. References should point to
   architecturally significant files, not random helpers.

7. **Coverage notes honesty.** Check that Coverage Notes explicitly
   states what was read fully, what was sampled, and what was skipped.
   If this section says "all files read" for a subsystem with 100+
   files, that's likely dishonest.

### Spot-Checks (against source repo)

8. **Evidence anchor verification.** Pick 2 file:line references from
   the Evidence Anchors section of each sampled doc. Check that these
   files exist in the source repo and the line references are
   approximately correct (within ~10 lines). Record results.

9. **Modification Guide verification.** Pick the "best template to copy
   from" file referenced in the Modification Guide. Does it exist? Is
   it actually a clean, representative instance of the pattern? Check
   against the source repo.

---

## Dimension 4: routing-map.md Quality

**Weight: 1x**

The routing map enables structured task-to-doc lookups.

### Structural Checks

1. **File exists.** If missing, auto-FAIL.

2. **YAML parseability.** Is the YAML code block well-formed? Could a
   parser extract the data? Check for: proper indentation, quoted
   strings where needed, consistent structure.

3. **subsystem_routing completeness.** Count entries — should match the
   number of subsystem docs in `agent-docs/subsystems/`. Each entry
   should have: name, doc, owns_paths, key_files, key_tests,
   common_tasks. List any entries with missing fields.

4. **pattern_routing completeness.** Count entries — should match the
   number of patterns in patterns.md. Each entry should have: pattern,
   doc, subsystem, template_file, registration, test_template. List
   any entries with missing fields.

5. **Version header present.**

### Cross-File Consistency Checks

6. **Subsystem cross-check.** Pick 2 subsystem_routing entries. For
   each, verify:
   - The `doc` path points to an actual file in `agent-docs/subsystems/`
   - The `owns_paths` match the Boundaries section of that subsystem doc
   - The `common_tasks` match the Modification Guide of that doc

7. **Pattern cross-check.** Pick 2 pattern_routing entries. For each,
   verify:
   - The `template_file` matches the example file in patterns.md
   - The `registration` matches the registration point in patterns.md
   - The `subsystem` field names a subsystem that actually has a doc

---

## Dimension 5: Wiring and Protocol

**Weight: 1x**

After analysis, the user needs clear instructions to wire docs into
their coding agent.

### Checks

1. **agent-protocol.md exists** with instructions for all 3 platforms
   (Claude Code/CLAUDE.md, Codex/AGENTS.md, Cursor/.cursor/rules/).

2. **5-step loading protocol** present in each platform section:
   Step 1 load core context, Step 2 load subsystem docs, Step 3 check
   patterns, Step 4 check constraints, Step 5 confirm understanding.

3. **Comprehension checkpoint.** Step 5 requires the agent to state
   which subsystems, patterns, and constraints apply. Check for the
   quote requirement ("quote the specific pattern you are following").

4. **Routing map mention.** Step 2 should mention routing-map.md as a
   faster alternative to manual subsystem identification.

5. **Version header present.**

---

## Dimension 6: Completeness

**Weight: 1x**

Is the full expected file set present and well-formed?

### Checks

1. **File set.** Compare actual files against the expected set listed
   at the top of this eval. List missing files. List unexpected files.

2. **.analysis-state.md YAML fields.** Check for all required fields:
   phase_completed (should be 3), generated_on, output_root,
   subsystems_pending (should be empty or contain only unselected
   scope), subsystems_completed, recursion_candidates,
   preliminary_patterns, analysis_version, source_commit. List missing
   fields.

3. **Version headers.** Spot-check 5 files for the version header
   (`Generated: {timestamp}`, version identifier, source commit).
   Record which have it and which don't.

4. **Orphan reference scan.** Search all generated docs for references
   to other `agent-docs/` files (e.g., `subsystems/{name}.md`,
   `patterns.md`, `decisions.md`). For each reference, verify the
   target file exists. List any broken references.

5. **Unfilled placeholder scan.** Search for literal placeholder text:
   `{name}`, `{path}`, `{date}`, `{value}`, `{subsystem}`. These
   should all be filled with actual values. List any unfilled
   placeholders.

6. **Template instruction leakage.** Search all generated docs for
   phrases that come from the templates rather than the analyzed repo.
   Common leaks: "1 paragraph: what this system does", "2-3 sentences:",
   "{who calls it or what triggers it}", "1 sentence", "{why it matters}".
   These indicate the analyzing agent copied the template structure but
   failed to fill in sections with actual content. List any leaked
   template instructions found — each is a content gap.

---

## Dimension 7: Token Efficiency

**Weight: 2x**

Every token loaded into an agent's context window displaces tokens
available for the actual task. Bloat is a direct cost.

### Measurable Checks

1. **agent-context.md line count.** Must be under 120. Record exact
   count. Over 120 is an automatic critical finding.

2. **agent-brief.md line count.** Should be under 100. Record exact
   count.

3. **index.md line count.** Should be under 250. Record exact count.

4. **Table scan across agent-consumed docs.** Check these files for
   markdown tables: agent-context.md, all subsystem docs, agent-brief.md,
   patterns.md, routing-map.md. Tables are prohibited in these files
   (they waste tokens). Record any tables found.

### Qualitative Checks

5. **Content duplication.** Compare the Key patterns section of
   agent-context.md against patterns.md. The patterns should appear in
   BRIEF form in agent-context.md (just the recipe steps) and in FULL
   form in patterns.md (with metadata, conventions, anti-patterns). If
   agent-context.md has the full detail, that's duplication waste.
   Similarly check Architecture map vs agent-brief.md.

6. **Prose density.** Pick one subsystem doc. Count:
   - Lines containing a file path in backticks (signal lines)
   - Lines that are pure prose without any file path, code reference,
     or structured data (noise lines)
   Calculate the ratio: signal / (signal + noise). Higher is better.
   Below 30% signal suggests the doc is too prose-heavy for agent
   consumption. Record the ratio.

7. **Section bloat.** In the sampled subsystem doc, are any sections
   disproportionately long compared to their value? For example, a
   20-line "Why This Subsystem Exists" section suggests too much prose
   for a 1-paragraph requirement.

---

## Dimension 8: Evidence Quality

**Weight: 1x**

The docs claim things about the codebase. Are those claims grounded?

### Spot-Checks (against source repo)

1. **File reference verification.** Pick 5 file:line references from
   across the docs (mix of agent-context.md, subsystem docs, and
   patterns.md). For each, check:
   - Does the file exist in the source repo?
   - Is the line number approximately correct (within ~10 lines)?
   - Does the content at that location match what the doc claims?
   Record each check with result.

2. **Architectural claim verification.** Pick 3 architectural claims
   (e.g., "X subsystem orchestrates Y and Z", "errors propagate via
   sentinel values", "config is loaded from env files"). For each,
   verify the cited evidence actually supports the claim. Record
   results.

3. **Confidence label correctness.** In analysis docs (subsystem docs,
   system-overview, decisions), check that confidence labels are used
   correctly:
   - `Confirmed:` items should cite direct code/doc evidence
   - `Inference:` items should acknowledge they're derived
   - `UNCERTAIN:` items should identify what's missing
   - Are any strong claims made without evidence?

4. **Runtime claim check.** Search for claims about runtime behavior
   (e.g., "handles 1000 requests/sec", "retries 3 times", "caches for
   5 minutes"). These should be marked as `Inference:` or `UNCERTAIN:`
   unless backed by configuration values or test assertions. Flag any
   stated as fact without evidence.

---

## Dimension 9: Uncertainty Handling

**Weight: 1x**

False confidence is worse than admitted gaps. The docs should preserve
uncertainty rather than hide it.

### Checks

1. **uncertainties.md exists and is non-empty.** If missing or empty
   for a non-trivial repo, that's suspicious — every repo has unknowns.

2. **Structured entries.** Each uncertainty should have: Topic, Why
   Uncertain, Evidence Seen, What Would Resolve It. Check that entries
   follow this structure (not just a bullet list of questions).

3. **Consolidation from subsystem docs.** Pick 2 subsystem docs. Find
   their Open Questions section. Verify that UNCERTAIN and NEEDS
   CLARIFICATION items from those sections appear (or are consolidated)
   in uncertainties.md. If items were dropped, that's a gap.

4. **Coverage notes honesty.** Check 2-3 subsystem docs' Coverage Notes
   sections. Do they honestly distinguish what was read fully vs sampled
   vs skipped? If a subsystem with 50+ files claims "read fully: all
   files", that's likely false. Cross-check file count against the
   source repo.

5. **Confidence level distribution.** In the subsystem inventory (index.md
   or system-overview.md), count how many subsystems are marked high,
   medium, low confidence. Record the distribution.
   - For repos with 5+ subsystems: at least 1 should be medium or low.
     All-high is likely overconfidence.
   - For repos with 10+ subsystems: at least 20% should be medium or
     low. If 100% are high, treat as a gap — the analyzing agent is
     either not using the labels or has unrealistic confidence.
   - For small repos (2-4 subsystems): all-high is acceptable if the
     repo is simple.

---

## Dimension 10: Simulated Task Test

**Weight: 2x**

The ultimate test: can a coding agent actually use these docs to
complete a real task? Simulate being a coding agent that just loaded
these docs. Four tasks test different scenarios.

**Dimension verdict:** Grade each task individually. The dimension
verdict is the LOWEST grade across all 4 tasks — the weakest link
determines whether agents can rely on these docs.

**Navigation metrics to record per task:**

- **Hop count:** How many files did you read to get from task intent
  to "I know what files to create/modify"? Count: agent-context.md
  (1) + routing-map.md (2, if used) + subsystem doc (3) + patterns.md
  (4, if needed). Ideal: 2-3 hops. If >4 hops needed, the routing is
  too indirect.
- **Wrong-turn risk:** At any point, did the docs lead you toward the
  wrong subsystem or wrong pattern before you corrected course? A
  wrong turn means the Architecture map or routing-map pointed to
  subsystem A, but the task actually belongs to subsystem B. Record
  any wrong turns — each is a defect in the routing layer.
- **Dead-end risk:** Did you hit a point where a referenced doc didn't
  exist, a section was empty, or the Modification Guide had no
  guidance for your task type? Record dead-ends — each means the
  agent would have to fall back to raw code exploration.

### Task 1: Most Common Change

1. Read agent-context.md. Identify the most common change type from
   the Key patterns section (e.g., "add a new endpoint", "add a new
   provider adapter").

2. Using ONLY agent-context.md and routing-map.md, determine:
   - Which subsystem doc should I read? (from routing-map or
     Architecture map)
   - What pattern should I follow? (from Key patterns)
   - What file should I create? (from pattern recipe)
   - Where do I register it? (from pattern recipe)
   - What test should I write? (from pattern recipe)

3. Now read the identified subsystem doc's Modification Guide. Does it
   add useful information beyond what agent-context.md provided?
   Specifically: invariants I must not break, files I must modify
   together, gotchas I should watch for.

4. **Grade:**
   - PASS: Could navigate from task to correct files, patterns, and
     constraints without guessing
   - PARTIAL: Got most of the way but had to guess at one step (e.g.,
     test location, registration point)
   - FAIL: Could not determine which files to create/modify, or would
     have followed a wrong pattern

### Task 2: Different Subsystem

1. Pick a task in a DIFFERENT subsystem than Task 1 (e.g., if Task 1
   was adding an endpoint in the API layer, Task 2 might be modifying
   configuration or adding a migration).

2. Repeat the same navigation: agent-context.md -> routing-map.md ->
   subsystem doc -> Modification Guide.

3. **Grade** using the same criteria.

### Task 3: Edge Case — Structural Change

1. Simulate a structural change: "I need to add a new subsystem" or
   "I need to change how subsystem X talks to subsystem Y."

2. Using the docs, determine:
   - What existing decisions constrain this change? (from decisions.md
     or agent-context.md Do NOT section)
   - What uncertainties exist in this area? (from uncertainties.md)
   - Are there invariants I must preserve? (from subsystem docs)

3. **Grade:**
   - PASS: decisions.md and uncertainties.md provided relevant
     constraints, agent-context.md Do NOT section flagged relevant
     anti-patterns
   - PARTIAL: Some relevant constraints found but significant gaps
   - FAIL: No relevant constraints surfaced — agent would make the
     change blind

### Task 4: Debugging / Tracing

1. Simulate a debugging task: "Users report that [primary flow] is
   returning incorrect results. I need to trace the flow and find
   where the bug might be."

2. Using the docs, determine:
   - Which subsystem(s) does this flow pass through? (from
     agent-context.md Architecture map, system-overview.md, or
     routing-map.md)
   - What is the sequence of handoffs? (from the subsystem doc's Main
     Flows section)
   - What are the error handling patterns? (from the subsystem doc and
     Conventions in agent-context.md)
   - Are there known edge cases or gotchas near this flow? (from the
     subsystem doc's Edge Cases section)

3. **Grade:**
   - PASS: Could trace the flow from entry to exit with file references
     at each step, and the docs surfaced relevant edge cases or gotchas
   - PARTIAL: Could identify the subsystem but flow tracing lacked file
     references, or edge cases section was empty/generic
   - FAIL: Could not trace the flow, or would have looked in the wrong
     subsystem

Record detailed notes for each simulated task.

---

## Cross-File Consistency Checks

After all 10 dimensions, perform these cross-file checks:

1. **Subsystem name consistency.** Do subsystem names in agent-context.md
   Architecture map match the filenames of subsystem docs in
   `agent-docs/subsystems/`? List any mismatches.

2. **Pattern name consistency.** Do pattern names in agent-context.md
   Key patterns match the pattern headings in patterns.md? List any
   mismatches.

3. **Routing map alignment.** Do routing-map.md subsystem_routing
   entries have the same names as subsystem doc files? Do
   pattern_routing entries align with patterns.md headings?

4. **Agent-brief alignment.** Does agent-brief.md's "Subsystems That
   Matter Most" list match the subsystem inventory in index.md and
   system-overview.md?

5. **Version header consistency.** Sample 5 files — do they all have
   the same timestamp and source commit? Mismatched versions suggest
   a partial re-run that didn't update all files.

---

## Scoring

### Per-Dimension Scoring

| Verdict | Score | Criteria |
|---------|-------|----------|
| PASS | 2 | All criteria met, spot-checks passed |
| PARTIAL | 1 | Most criteria met, gaps noted but not critical |
| FAIL | 0 | Fundamental criteria missing, agent would be misled |

### Weighted Aggregate

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| D1: agent-context.md | 3x | /2 | /6 |
| D2: patterns.md | 2x | /2 | /4 |
| D3: Subsystem Docs | 2x | /2 | /4 |
| D4: routing-map.md | 1x | /2 | /2 |
| D5: Wiring/Protocol | 1x | /2 | /2 |
| D6: Completeness | 1x | /2 | /2 |
| D7: Token Efficiency | 2x | /2 | /4 |
| D8: Evidence Quality | 1x | /2 | /2 |
| D9: Uncertainty | 1x | /2 | /2 |
| D10: Simulated Tasks | 2x | /2 | /4 |
| **Total** | | | **/32** |

### Grade Bands

| Score | Grade | Interpretation |
|-------|-------|----------------|
| 28-32 | Excellent | Agent can work confidently from these docs |
| 22-27 | Good | Effective with minor gaps, worth using as-is |
| 16-21 | Needs Work | Usable but agent will hit gaps on many tasks |
| <16 | Significant Gaps | Re-run analysis before relying on these docs |

---

## Synthesis

### Score Card

| Dimension | Weight | Verdict | Key Finding |
|-----------|--------|---------|-------------|
| D1: agent-context.md | 3x | | |
| D2: patterns.md | 2x | | |
| D3: Subsystem Docs | 2x | | |
| D4: routing-map.md | 1x | | |
| D5: Wiring/Protocol | 1x | | |
| D6: Completeness | 1x | | |
| D7: Token Efficiency | 2x | | |
| D8: Evidence Quality | 1x | | |
| D9: Uncertainty | 1x | | |
| D10: Simulated Tasks | 2x | | |

### Aggregate Score: ___/32 — Grade: ___

### Critical Gaps (would cause agent errors)

1. {gap} — D{N} — {file:section} — {impact on agent}
2. ...

### Important Gaps (reduce agent efficiency)

1. {gap} — D{N} — {file:section} — {impact}
2. ...

### Minor Gaps (nice to fix)

1. {gap} — D{N} — {file:section}
2. ...

### Strengths (do not change)

1. {strength} — {evidence}
2. ...

### Cross-File Inconsistencies Found

1. {inconsistency} — {files involved}
2. ...

### Recommendation

Based on the grade:
- **Excellent:** Docs are ready for production use.
- **Good:** Fix critical gaps (if any), then use.
- **Needs Work:** Fix critical + important gaps before relying on docs.
- **Significant Gaps:** Re-run the analysis tool. If re-run produces
  the same grade, the tool itself needs improvement (use eval-toolkit.md
  to diagnose).
