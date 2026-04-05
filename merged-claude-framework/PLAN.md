# Implementation Plan: Merged Codebase Analysis Framework

## Primary Objective

Build a tool that generates documentation optimized for **coding agent
efficiency** — enabling Claude Code, Codex, and Cursor to gain deep
codebase context at session start and produce higher-quality work than
a cold start.

Secondary objective: the same documentation is human-readable for
onboarding and reference.

---

## Design Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Output folder | `agent-docs/` (not `docs/`) | Avoids collision with repo's own `docs/` |
| Installation model | User-global (`~/.claude/`) | Install once, analyze any repo. Tool is not part of the target repo. |
| Phase model | 3 explicit commands | Multi-session capable, state persisted to disk, user controls progression |
| Target platforms | Claude Code + Codex + Cursor | All three agent platforms supported |
| Primary output | `agent-docs/agent-context.md` | Compact, actionable, designed for agent auto-loading |
| Pattern detection | Semi-automated | Agent proposes, user confirms before final output |
| Subsystem recursion | Adaptive, max depth 3 | Decompose only when single doc would lose actionable detail |
| Re-run behavior | Augment, don't replace | Read existing `agent-docs/`, update changed sections, preserve accurate ones |

---

## Installation Layout (Option B: User-Global)

```
~/.claude/
  commands/                              # Claude Code auto-registers these as /user:* commands
    analyze-discover.md                  # Phase 1 slash command
    analyze-deep-dive.md                 # Phase 2 slash command
    analyze-synthesize.md                # Phase 3 slash command
  codebase-analysis/                     # Shared resources (read on-demand by commands)
    protocol.md                          # Canonical behavioral spec
    docs-schema.md                       # Output directory structure
    references/
      ecosystem-playbook.md              # Per-language exploration commands
      scale-and-scope.md                 # Reading depth, stop conditions, recursion thresholds
      subsystem-mapping-rubric.md        # What qualifies as subsystem, split/merge
      checkpoint-template.md             # Mandatory checkpoint format (8 sections)
      agent-context-rules.md             # NEW: Rules for generating agent-loadable context
      pattern-detection-guide.md         # NEW: How to detect and document code patterns
    templates/
      agent-context-template.md          # NEW: Template for generated agent-context.md
      patterns-template.md               # NEW: Template for patterns.md
      index-template.md
      agent-brief-template.md
      system-overview-template.md
      subsystem-template.md              # Enhanced with testing, edge cases, recursion
      flow-template.md
      decisions-template.md
      glossary-template.md
      uncertainties-template.md
    examples/
      checkpoint-example.md              # Filled checkpoint for quality calibration
      agent-context-example.md           # NEW: Example of generated agent-context.md
  codex/                                 # Codex assets (copied to target repo when needed)
    AGENTS.md                            # Behavioral contract
    prompts/
      1-discover.md
      2-deep-dive.md
      3-synthesize.md
  cursor/
    SKILL.md                             # Cursor skill with auto-trigger
```

**How commands find shared resources:**
Each slash command contains a `SHARED_ROOT` resolution block at the top:

```
Look for shared resources at ~/.claude/codebase-analysis/.
If not found, use the inline fallback content in this command.
```

This means commands work at reduced quality even if shared/ is missing
(self-contained fallback), but at full quality when the bundle is
properly installed.

**Invocation:**

```
# Claude Code (after install)
/user:analyze-discover This is a Go payment service using gRPC
/user:analyze-deep-dive transaction-engine
/user:analyze-synthesize

# Codex
# 1. Copy AGENTS.md to target repo root
# 2. Paste prompt contents into chat

# Cursor
# 1. Paste prompt contents into Composer
# 2. After analysis, wire agent-context.md into .cursorrules
```

---

## Output Layout (Written to Target Repo)

When the tool runs on a target repo, it produces:

```
target-repo/
  agent-docs/
    .analysis-state.md                   # Cross-phase state file (internal)
    agent-context.md                     # PRIMARY OUTPUT: compact agent-loadable context
    patterns.md                          # NEW: detected code patterns and conventions
    agent-brief.md                       # Compact architecture map
    index.md                             # Navigation hub
    system-overview.md                   # Top-level architecture
    decisions.md                         # Architectural trade-offs
    glossary.md                          # Project-specific terms
    uncertainties.md                     # Unresolved questions
    subsystems/
      auth.md                            # Subsystem doc (flat)
      api-layer.md                       # Subsystem doc (flat)
      storage.md                         # Subsystem doc (with recursion below)
      storage/                           # Sub-subsystem docs (depth 2)
        postgres-adapter.md
        cache-layer.md
    flows/
      request-lifecycle.md               # Cross-cutting flow (if warranted)
```

**Priority of outputs (what matters most for Goal #1):**

1. `agent-context.md` — THE primary deliverable. Under 120 lines.
   Designed to be referenced from CLAUDE.md/.cursorrules/AGENTS.md.
2. `patterns.md` — actionable "how to add a new X" recipes.
3. `agent-brief.md` — compact architecture for deeper context loading.
4. `subsystems/*.md` — on-demand deep reference.
5. Everything else — supporting documentation.

---

## The Three Phases

### Phase 1: Discover & Map

**Command:** `/user:analyze-discover {description}`
**Runs:** Once per repo
**Produces:** `agent-docs/.analysis-state.md`, `agent-docs/system-overview.md`

```
Step 1: Classify the repository
         - archetype, language, execution model, scale
         - load ecosystem-playbook.md, use language-specific commands
         - inline fallback if playbook not found

Step 2: Adaptive questions (0-4 questions)
         - ask ONLY if repo purpose, scope, or boundaries are unclear
         - skip entirely if evidence is sufficient
         - themes: purpose, scope, known gaps, special concerns

Step 3: Evidence scan
         - follow ecosystem-playbook exploration commands
         - apply scale-and-scope.md reading depth rules
         - priority: manifests > entrypoints > contracts > routers/DI >
           orchestration > config > tests > existing docs
         - note: read fully / sampled / skipped

Step 4: Map subsystems
         - apply subsystem-mapping-rubric.md (2-of-6 criteria)
         - tag each: entrypoint | orchestration | domain/core |
           integration | storage | configuration | tooling/build |
           ui/presentation | shared | generated
         - flag recursion candidates: subsystems with 50+ files OR
           3+ internal modules with own contracts
         - detect preliminary patterns: note file clusters following
           similar structures (endpoints, handlers, adapters, tests)

Step 5: Present checkpoint
         - use checkpoint-template.md exact structure
         - 8 sections: classification, understanding, subsystems,
           flows, coverage, open questions, preliminary patterns,
           proposed plan
         - subsystem table includes recursion-candidate column
         - patterns section is new: "These file clusters appear to
           follow a common pattern: [list]. Will confirm during
           deep dives."

Step 6: Ask for confirmation
         - "Does this map look right? Should I write
           agent-docs/system-overview.md and save analysis state?"
         - do NOT write files until confirmed

Step 7: Write files (after confirmation)
         - agent-docs/.analysis-state.md:
             phase_completed: 1
             generated_on: {date}
             output_root: agent-docs
             subsystems_pending: [list]
             subsystems_completed: []
             recursion_candidates: [list]
             preliminary_patterns: [list]
         - agent-docs/system-overview.md:
             purpose, boundaries, architectural shape, subsystems,
             flows, state/config, design observations

Step 8: Report next steps
         - "Phase 1 complete. Next: run /user:analyze-deep-dive
           {subsystem} for each subsystem. Recommended order: ..."
         - flag recursion candidates: "These subsystems are large
           and may be decomposed during deep dive: [list]"
```

**Re-run behavior:**
If `agent-docs/.analysis-state.md` exists:
1. Read it first
2. Compare current repo state against recorded subsystem map
3. Flag new, removed, or changed subsystems
4. Augment rather than overwrite — preserve existing confirmations
5. Reset `subsystems_pending` for subsystems that changed significantly
6. Update `agent-docs/system-overview.md` to reflect changes

---

### Phase 2: Deep Dive

**Command:** `/user:analyze-deep-dive {subsystem-name}`
**Runs:** Once per subsystem (and once per sub-module if recursion triggers)
**Produces:** `agent-docs/subsystems/{name}.md` (and optionally `agent-docs/subsystems/{name}/*.md`)

```
Step 0: Read analysis state
         - read agent-docs/.analysis-state.md and
           agent-docs/system-overview.md
         - match $ARGUMENTS against subsystem map
         - if state doesn't exist: halt, tell user to run Phase 1
         - display progress: "{N} of {total} complete. Remaining: ..."

Step 1: Read the subsystem
         - list all files in subsystem directory
         - <30 files: read all non-test, sample tests
         - 30+ files: read central fully, sample leaves, note coverage

Step 2: Evaluate recursion need
         - does this subsystem have 50+ files?
         - does it contain 3+ internal modules with own
           contracts/entrypoints?
         - if YES to either:
             present decomposition proposal in chat:
             "This subsystem is large enough to decompose:
              - {sub-1}: {responsibility} ({N} files)
              - {sub-2}: {responsibility} ({N} files)
              Confirm? Or analyze as single unit?"
         - if user confirms decomposition:
             write parent doc at agent-docs/subsystems/{name}.md
             (overview + internal map + cross-cutting concerns)
             then deep-dive each sub-module, writing to
             agent-docs/subsystems/{name}/{child}.md
         - recursion applies to depth 3 max
         - at depth 3: summarize remaining complexity, don't decompose

Step 3: Analyze
         Investigate these dimensions:

         a) Boundaries & Role
            - what it does, why it exists separately
            - inputs, outputs, state owned

         b) Internal Structure
            - file organization, key units and responsibilities

         c) Contracts & Types
            - exported types/interfaces/traits/classes
            - where defined, purpose, who creates, who consumes

         d) Flows
            - trace each entry point through the subsystem
            - happy path, error handling, async boundaries
            - handoffs to other subsystems

         e) Dependencies
            - internal: imports and imported-by
            - external: third-party packages, which are load-bearing
            - flag circular or surprising coupling

         f) Configuration
            - config values, defaults, env-specific behavior

         g) Design Decisions (2-4)
            - what was chosen, enables, costs, alternatives, assessment

         h) Testing
            - test files, coverage patterns, test utilities, fixtures
            - what is covered vs not

         i) Edge Cases & Gotchas
            - implicit contracts, race conditions, ordering requirements
            - known limitations, tech debt, surprises for new contributors

         j) Pattern Detection
            - identify repetitive file structures within subsystem
            - for each pattern: name, example file (cleanest instance),
              file list, structure, registration points
            - these accumulate for Phase 3's patterns.md

Step 4: Write subsystem document
         - write to agent-docs/subsystems/{name}.md
         - use subsystem-template.md structure
         - sections: Why It Exists, Boundaries, Evidence Anchors,
           Internal Structure, Key Contracts, Main Flows,
           Dependencies, Configuration, Design Decisions,
           Testing, Edge Cases & Gotchas, Detected Patterns,
           Open Questions, Coverage Notes
         - if recursion: also write child docs at
           agent-docs/subsystems/{name}/{child}.md

Step 5: Update analysis state
         - move subsystem from pending to completed
         - record detected patterns
         - if recursion occurred, record sub-module structure

Step 6: Report next steps
         - "Deep dive on {name} complete. [{N}/{total}]"
         - "Written: agent-docs/subsystems/{name}.md"
         - if recursion: "Also written: agent-docs/subsystems/{name}/{children}"
         - "Remaining: ..."
         - "When all done: /user:analyze-synthesize"
```

**Re-run behavior:**
If `agent-docs/subsystems/{name}.md` exists:
1. Read the existing document first
2. Compare against current code state
3. Update sections that have changed
4. Preserve sections still accurate
5. Add note: `> Updated on {date}. Previous analysis preserved where still accurate.`
6. If subsystem was previously flat but now qualifies for recursion:
   propose decomposition, keep existing doc as starting point for parent

---

### Phase 3: Synthesize

**Command:** `/user:analyze-synthesize`
**Runs:** Once per repo
**Produces:** All remaining files, with `agent-context.md` generated FIRST

```
Step 0: Read all existing docs
         - agent-docs/.analysis-state.md
         - agent-docs/system-overview.md
         - all files in agent-docs/subsystems/ (including recursive children)
         - if subsystems still pending: warn user, ask whether to continue
         - if state doesn't exist: halt, tell user to run Phase 1

Step 1: Generate agent-docs/agent-context.md  *** PRIMARY OUTPUT ***
         - load agent-context-rules.md for format constraints
         - use agent-context-template.md for structure
         - HARD CONSTRAINTS:
             under 120 lines total
             every line must be actionable for a coding agent
             use concrete file paths, not abstract descriptions
             no architectural prose — only navigation + patterns + rules
         - content sourced from:
             system-overview → "what this repo is" + architecture map
             all subsystem docs → key paths with one-line purpose
             accumulated patterns → "key patterns to follow"
             design decisions → "conventions" and "do NOT" rules
             contracts → key interfaces with file:line references
         - structure:
             ## What this repo is (2-3 sentences)
             ## Architecture map (flat path list, no tables)
             ## Key patterns (for each: "To add a new X: steps")
             ## Conventions (do-this with file references)
             ## Do NOT (anti-patterns with reasons)
             ## Key contracts (file:line — what it defines)
             ## For deeper context (pointers to other agent-docs/ files)

Step 2: Generate agent-docs/patterns.md
         - consolidate all patterns detected during deep dives
         - present to user in chat for confirmation (semi-automated):
           "I detected these code patterns. Confirm, edit, or remove:"
           - pattern name, example file, files following it, steps
         - after confirmation, write using patterns-template.md
         - group by category: endpoint, service, test, migration, config

Step 3: Generate agent-docs/agent-brief.md
         - compact architecture map, under 100 lines
         - more file-path-heavy than prose-heavy
         - mission, classification, architecture at a glance,
           subsystems that matter, flows, decisions, uncertainties,
           reading path for future agent

Step 4: Generate agent-docs/index.md
         - navigation hub, under 250 lines
         - what this repo is, documentation scope, reading order,
           subsystem inventory, flow inventory, quick links,
           confidence summary

Step 5: Generate agent-docs/decisions.md
         - consolidated architectural decisions from all analyses
         - 5-8 for medium/large, 3-5 for small
         - per decision: scope, chosen, evidence, enables, costs,
           alternatives, inference, assessment

Step 6: Generate agent-docs/glossary.md
         - project-specific terms, abstractions, domain vocabulary
         - prioritize: cross-subsystem terms, domain-specific,
           confusing/overloaded names

Step 7: Generate agent-docs/uncertainties.md
         - consolidated UNCERTAIN and NEEDS CLARIFICATION items
         - per item: topic, why uncertain, evidence, what resolves it

Step 8: Generate flow docs (if warranted)
         - only for cross-cutting flows spanning multiple subsystems
         - that teach something not covered in subsystem docs
         - write to agent-docs/flows/{name}.md
         - skip for simple repos

Step 9: Update analysis state
         - set phase_completed: 3
         - record all generated files

Step 10: Report completion with integration instructions
          - "Phase 3 complete. Documentation set ready."
          - "Generated files: [list]"
          -
          - "*** IMPORTANT: Wire agent-context.md into your agent ***"
          -
          - "For Claude Code — add to your CLAUDE.md:"
          -   Read agent-docs/agent-context.md at the start of every
          -   session for full codebase context.
          -
          - "For Cursor — add to your .cursorrules:"
          -   Read agent-docs/agent-context.md at the start of every
          -   session for full codebase context.
          -
          - "For Codex — add to your AGENTS.md:"
          -   Read agent-docs/agent-context.md at the start of every
          -   session for full codebase context.
          -
          - "If no config file exists yet, create one with just that line."
          -
          - "To update: re-run any phase. It augments existing agent-docs/."
```

**Re-run behavior:**
If synthesis docs exist:
1. Read all existing agent-docs/ first
2. Compare against current subsystem docs
3. Regenerate agent-context.md entirely (it's compact enough to rewrite)
4. Regenerate patterns.md (re-present to user for confirmation)
5. Update changed sections in other files
6. Remove entries for subsystems that no longer exist
7. Preserve entries still accurate
8. Add note: `> Updated on {date}.`

---

## Implementation Steps

### Step 1: shared/protocol.md — Canonical Behavioral Spec

**Source material:**
- Codex-output `shared/protocol.md`: core objectives, hard rules, output
  modes, phase structure, repo-type priorities, confidence rules,
  citation policy, read scope rules, quality bar, failure modes
- Claude-output command files: 3-phase model, state persistence,
  re-run behavior, progress tracking

**What to write:**
A single protocol document that defines:
- Core objectives (shifted: agent efficiency first, human docs second)
- Hard rules (read-only, chat-first, evidence-based, factual, honest)
- The 3-phase operational model (Discover, Deep-Dive, Synthesize)
- Output root: `agent-docs/` (not `docs/`)
- State persistence via `agent-docs/.analysis-state.md`
- Output priority hierarchy (agent-context > patterns > agent-brief > rest)
- Repo-type priorities (applications, libraries, frameworks, monorepos)
- Confidence labels (Confirmed, Inference, UNCERTAIN, NEEDS CLARIFICATION)
- Citation policy (moderate density)
- Quality bar (what "good enough" looks like, what "not good enough" looks like)
- Failure modes to avoid
- Re-run semantics (augment, don't replace)
- Recursive decomposition rules (thresholds, depth limit 4)
- Pattern detection rules (semi-automated)
- Agent context generation rules (token budget, format constraints)

**Depends on:** Nothing
**Estimated size:** ~350 lines

---

### Step 2: shared/references/ — Operational Playbooks (6 files)

**2a: ecosystem-playbook.md**
- Source: Codex-output version (wholesale — it's excellent)
- Enhancement: ensure Ruby, Elixir have exploration commands on par
  with Go/TS/Python. Add Swift/Kotlin mobile markers.
- All `docs/` references → `agent-docs/`
- ~240 lines

**2b: scale-and-scope.md**
- Source: Codex-output version (4 tiers, sampling, generated code, stop conditions)
- Enhancement: add recursive decomposition thresholds section:
    - 50+ files OR 3+ internal modules → propose depth-2
    - 30+ files at depth 2 OR 2+ internal modules → propose depth-3
    - depth 3: hard stop
    - rule: decompose only when parent doc loses actionable detail
    - many-files-one-pattern → pattern note, not recursion
- All `docs/` references → `agent-docs/`
- ~140 lines

**2c: subsystem-mapping-rubric.md**
- Source: Codex-output version (criteria, split/merge, naming, confidence,
  minimum evidence, monorepo guidance)
- Enhancement: add recursion section — when to decompose internally.
  Same 2-of-6 criteria applied at each level. Guidance on when to
  flatten (single responsibility despite many files) vs decompose
  (multiple responsibilities).
- All `docs/` references → `agent-docs/`
- ~130 lines

**2d: checkpoint-template.md**
- Source: Codex-output version (8 sections, strict format)
- Enhancement:
    - subsystem table adds "Recursion?" column
    - add Section 7.5: "Preliminary Patterns Detected" (pattern name,
      file cluster, example file)
    - section 7 (Proposed Plan) explicitly lists agent-context.md as
      primary deliverable
- All `docs/` references → `agent-docs/`
- ~90 lines

**2e: agent-context-rules.md** — NEW FILE
- Purpose: defines how to generate the compact agent-loadable context
- Content:
    - token budget: under 120 lines / ~3K tokens
    - structure: repo identity → architecture map → patterns →
      conventions → anti-patterns → contracts → deeper-docs pointers
    - every line must be actionable (no prose, no explanations)
    - use concrete file paths (not abstract subsystem names)
    - format as flat markdown: ## headings, - bullet lists, `code refs`
    - no tables (they waste tokens for agents)
    - no "Confirmed:" / "Inference:" labels (this is output for agents,
      not analysis)
    - the agent-context file is STANDALONE: an agent reading only this
      file should know where everything is and what patterns to follow
    - platform notes: content is identical for Claude Code / Cursor / Codex;
      the only difference is where it gets referenced from
      (CLAUDE.md vs .cursorrules vs AGENTS.md)
- ~80 lines

**2f: pattern-detection-guide.md** — NEW FILE
- Purpose: how the analyzing agent detects and documents code patterns
- Content:
    - what counts as a pattern: 3+ files following structurally similar
      shape (same directory, similar naming, similar internal structure)
    - detection method: during deep dive, identify file clusters → extract
      common structure → identify cleanest instance as template → note
      registration/wiring points
    - categories: endpoint/handler, service/module, data model/migration,
      test, configuration, adapter/integration
    - output format: "To add a new X: 1. create file at Y, 2. register
      at Z, 3. follow pattern in W"
    - semi-automated flow: agent proposes in checkpoint (Phase 1) and
      accumulates during deep dives (Phase 2), user confirms in
      Phase 3 before final output
    - negative guidance: single-instance files are NOT patterns, generic
      language idioms are NOT patterns, generated code structures are NOT
      patterns worth documenting
- ~80 lines

**Depends on:** Step 1
**Total estimated size for Step 2:** ~760 lines across 6 files

---

### Step 3: shared/templates/ — Output Document Templates (10 files)

**3a: agent-context-template.md** — NEW
- The template for `agent-docs/agent-context.md`
- Compact, no-prose structure
- Sections: What this repo is, Architecture map, Key patterns,
  Conventions, Do NOT, Key contracts, For deeper context
- Under 120 lines when filled
- ~60 lines (template with placeholders)

**3b: patterns-template.md** — NEW
- Template for `agent-docs/patterns.md`
- Per-pattern: category, name, example file, files following it,
  steps to add a new instance, conventions within pattern, anti-patterns
- ~40 lines

**3c: subsystem-template.md** — ENHANCED
- Source: Codex-output template
- Add from Claude-output: Testing section (test files, coverage,
  patterns, fixtures), Edge Cases and Gotchas section (implicit
  contracts, race conditions, limitations)
- Add new: Detected Patterns section (patterns found within this
  subsystem), Recursion marker (Sub-subsystems: [list] or "none",
  with links to child docs if applicable)
- All `docs/` references → `agent-docs/`
- ~100 lines

**3d-3j: remaining templates** (7 files)
- index-template.md: from Codex-output, `docs/` → `agent-docs/`
- agent-brief-template.md: from Codex-output, tighten to under 100
  lines target, more file-path-heavy
- system-overview-template.md: from Codex-output, `docs/` → `agent-docs/`
- flow-template.md: from Codex-output, `docs/` → `agent-docs/`
- decisions-template.md: from Codex-output, `docs/` → `agent-docs/`
- glossary-template.md: from Codex-output, `docs/` → `agent-docs/`
- uncertainties-template.md: from Codex-output, `docs/` → `agent-docs/`

**Depends on:** Steps 1-2
**Total estimated size for Step 3:** ~450 lines across 10 files

---

### Step 4: shared/examples/ — Quality Calibration (2 files)

**4a: checkpoint-example.md**
- Source: Codex-output version (TypeScript monorepo)
- Enhancement: add recursion-candidate column to subsystem table,
  add preliminary patterns section
- All `docs/` references → `agent-docs/`
- ~80 lines

**4b: agent-context-example.md** — NEW
- A fully filled-out `agent-context.md` for the same fictional
  TypeScript monorepo from the checkpoint example
- Shows the analyzing agent exactly what the primary output should
  look like: compact, actionable, path-heavy, no prose
- This is critical — without a concrete example, the agent will drift
  toward prose-heavy output
- ~100 lines

**Depends on:** Steps 1-3
**Total estimated size for Step 4:** ~180 lines across 2 files

---

### Step 5: claude-code/commands/ — Slash Commands (3 files)

**5a: analyze-discover.md**
- Base: Claude-output's version (self-contained, $ARGUMENTS, 8-step
  procedure, state file, progress tracking)
- Merge: references to shared/ playbooks with inline fallbacks
- Add: adaptive questioning step, recursion flagging, preliminary
  pattern detection, enhanced checkpoint
- All `docs/` → `agent-docs/`
- Key behavior: if `~/.claude/codebase-analysis/` exists, load
  references from there. If not, use inline fallback tables.
- ~300 lines

**5b: analyze-deep-dive.md**
- Base: Claude-output's version (per-subsystem, $ARGUMENTS, state read,
  progress tracking)
- Add: recursive decomposition logic (Step 2 in phase spec above),
  pattern detection per subsystem, testing section, edge cases section
- All `docs/` → `agent-docs/`
- ~250 lines

**5c: analyze-synthesize.md**
- Base: Claude-output's version (reads all docs, 8-step, state update)
- Major change: agent-context.md generated FIRST (Step 1), patterns.md
  generated SECOND (Step 2), rest follows
- Add: integration instructions for all 3 platforms in completion report
- All `docs/` → `agent-docs/`
- ~300 lines

**Depends on:** Steps 1-4
**Total estimated size for Step 5:** ~850 lines across 3 files

---

### Step 6: codex/ — Codex Wrapper (4 files)

**6a: AGENTS.md**
- Source: Claude-output version (behavioral contract)
- Enhancement: add agent-context.md as primary deliverable, pattern
  detection mention, recursion awareness, all `docs/` → `agent-docs/`
- ~100 lines

**6b: prompts/1-discover.md**
- Mirror of analyze-discover.md adapted for paste-able format
- {USER_DESCRIPTION} placeholder instead of $ARGUMENTS
- Same logic, same shared/ references, same inline fallbacks
- ~250 lines

**6c: prompts/2-deep-dive.md**
- Mirror of analyze-deep-dive.md for paste-able format
- {SUBSYSTEM_NAME} placeholder
- ~200 lines

**6d: prompts/3-synthesize.md**
- Mirror of analyze-synthesize.md for paste-able format
- Same agent-context-first output order
- ~250 lines

**Depends on:** Steps 1-4
**Total estimated size for Step 6:** ~800 lines across 4 files

---

### Step 7: cursor/SKILL.md — Cursor Skill (1 file)

- YAML frontmatter with auto-trigger keywords
- Complete 3-phase workflow inline
- References shared resources for full quality
- How to wire `agent-docs/agent-context.md` into `.cursor/rules/`
- ~140 lines

**Depends on:** Steps 5-6
**Total estimated size:** ~40 lines

---

### Step 8: README.md — Top-Level Guide (1 file)

- What this tool is (1 paragraph, agent-efficiency-first framing)
- What it produces (output tree with priority markers)
- The primary deliverable explained: agent-context.md
- Setup instructions for all 3 platforms
- The 3-phase workflow overview
- How to wire output into agent config
- Re-run instructions
- Design principles

**Depends on:** Steps 1-7
**Total estimated size:** ~150 lines

---

### Step 9: Validate on Real Repo

- Run the tool on a real codebase (this repo itself, or an open-source repo)
- Validate:
    - [ ] agent-context.md fits under 120 lines
    - [ ] agent-context.md contains only actionable content (no prose)
    - [ ] patterns.md contains real, useful patterns
    - [ ] recursive decomposition triggers correctly on large subsystems
    - [ ] recursive decomposition does NOT trigger on flat subsystems
    - [ ] re-run on same repo augments rather than overwrites
    - [ ] commands work from global install (~/.claude/commands/)
    - [ ] commands degrade gracefully without shared/ resources
    - [ ] output references agent-docs/ consistently (no stale docs/ refs)
    - [ ] generated agent-context.md works when loaded by Claude Code
    - [ ] Codex prompts produce equivalent output to Claude Code commands
    - [ ] checkpoint quality matches the example

---

## Execution Order & Parallelization

```
Step 1: protocol.md
  |
  v
Step 2: references/ (6 files) ──────────────────┐
  |                                              |
  v                                              v
Step 3: templates/ (10 files)              Step 4: examples/ (2 files)
  |                                              |
  ├──────────────────┬───────────────────────────┘
  v                  v                  v
Step 5:           Step 6:           Step 7:
commands/ (3)     codex/ (4)        cursor/ (1)
  |                  |                  |
  └──────────────────┴──────────────────┘
                     |
                     v
                  Step 8: README.md
                     |
                     v
                  Step 9: Validate
```

Steps 2-3, 3-4, and 5-6-7 can be parallelized.

---

## File Count Summary

| Layer | Files | Estimated Lines |
|-------|-------|-----------------|
| shared/protocol.md | 1 | ~350 |
| shared/references/ | 6 | ~760 |
| shared/templates/ | 10 | ~450 |
| shared/examples/ | 2 | ~180 |
| claude-code/commands/ | 3 | ~850 |
| codex/ | 4 | ~800 |
| cursor/ | 1 | ~40 |
| README.md | 1 | ~150 |
| **Total** | **28** | **~3,580** |

---

## Key Differences From Either Source Output

| Aspect | Claude-output | Codex-output | Merged |
|--------|--------------|--------------|--------|
| Primary deliverable | architecture docs | architecture docs | `agent-context.md` (compact, agent-loadable) |
| Output folder | `docs/` | `docs/` | `agent-docs/` |
| Pattern detection | none | none | semi-automated, per subsystem + consolidated |
| Subsystem recursion | none | none | adaptive, depth 3 max |
| Agent config integration | none | none | explicit wiring instructions for 3 platforms |
| Installation | per-repo | per-repo | user-global (`~/.claude/`) |
| Adaptive questioning | none | Phase 1 | built into Discover phase |
| Ecosystem playbook | inline tables | full bash commands | full bash commands + inline fallback |
| Quality bar | none | defined | defined + enforced via examples |
| State persistence | `.analysis-state.md` | none | `.analysis-state.md` (enhanced) |
| Re-run behavior | explicit per phase | not addressed | explicit per phase + augment semantics |
| Progress tracking | yes | no | yes |
| Token budget | none | none | 120 lines for agent-context.md |
