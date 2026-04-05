# Deep Comparative Analysis: merged-claude-framework vs merged-framework-cursor

## Context

This repository contains a codebase analysis tool that generates
architecture documentation optimized for coding agents. Two independent
"merged" versions exist — each was created by a different AI agent
session (one Claude Code, one Cursor) that merged the same two original
source frameworks into what it considered the best synthesis.

Your job is a rigorous, evidence-based comparative analysis to determine
which one better achieves the tool's objective.

## The Tool's Objective

**Primary (non-negotiable): Coding agent efficiency.**
The generated docs are consumed by coding agents (Claude Code, Codex,
Cursor) at session start. The agent loads this context and writes
higher-quality code than a cold start — it knows the architecture,
follows established patterns, respects constraints, navigates to the
right files. When the two implementations conflict on any design
decision, evaluate against: **"which one makes a coding agent write
better code on its first task in the repo?"** That is the only question
that matters.

**Secondary: Human-readable documentation.**
Developers can also read the output. But when a design decision
optimizes for human readability at the cost of agent efficiency, that
is the wrong trade-off.

## The Two Candidates

Both live in the same parent directory:

```
/Users/lalit.verma@zomato.com/Desktop/tinkering/codebase-analysis-skill/
├── merged-claude-framework/    <-- Candidate A (30 files)
└── merged-framework-cursor/    <-- Candidate B (24 files)
```

Both implement a 3-phase workflow (Discover, Deep Dive, Synthesize)
that produces documentation in `agent-docs/` for any target repository.
Both support Claude Code, Codex, and Cursor.

**Do not trust these summaries.** Read every file yourself.

---

## How To Work

### Phase 1: Read everything first

Read every single file in both directories before forming any
conclusions. Do not skim. Do not summarize from file names. There are
~30 files in each — this is not large.

Suggested reading order per candidate (to absorb design philosophy
fastest):
1. `README.md` — how the tool presents itself
2. The Phase 3 synthesize command (`claude-code/commands/analyze-synthesize.md`) — reveals output priorities and what the tool considers its primary deliverable
3. The primary deliverable template (whichever file the coding agent loads at session start)
4. The subsystem doc template
5. Shared references (ecosystem playbook, scale-and-scope, rubric)
6. Phase 1 and Phase 2 commands
7. Codex prompts and Cursor integration
8. Everything else

After reading, note the following before moving to analysis:
- What is the primary file a coding agent loads at session start?
- What sections does the subsystem template contain?
- How does each handle Cursor specifically?
- What does the Phase 3 synthesize command produce, and in what order?

### Phase 2: Dimension-by-dimension comparison

For each of the 13 dimensions below, produce exactly this structure:

> **Dimension N: {Name}**
>
> **Winner:** A or B (or Tie — but ties should be rare; push yourself to pick one)
>
> **Evidence:** Specific file paths and **quoted passages** from both
> candidates that support the verdict. Do not paraphrase — quote the
> actual text so the reader can verify.
>
> **Gap:** What the losing candidate is missing or doing worse.
> Reference the specific file and section where the gap exists.

Do not be diplomatic. Do not hedge. One is better at each dimension.

---

## The 13 Dimensions

### Dimension 1: Primary Deliverable Design

The single most important dimension. What file does the coding agent
load at session start?

Evaluate:
- What is this file called? What's its stated token/line budget?
- Is it prose-heavy (architecture descriptions) or action-heavy (file
  paths, patterns, rules, anti-patterns)?
- Is it standalone — can an agent reading ONLY this file navigate the
  repo and follow conventions?
- Does it include a "Do NOT" / anti-pattern section?
- Does it include code patterns with concrete steps ("to add a new X,
  do 1, 2, 3")?
- Does it include key contracts with file:line references?
- Are there tables? (Tables waste tokens for agent consumption.)
- Is there a concrete filled-out example of this file?

### Dimension 2: Pattern Detection and Documentation

Patterns are the highest-impact output for agents. "To add a new
endpoint, follow this recipe" prevents convention drift.

Evaluate:
- How are patterns detected? (fully automated / semi-automated with
  user confirmation / manual)
- When are patterns detected? (Phase 1 preliminary, Phase 2 refined,
  Phase 3 consolidated — or something else?)
- Is there a dedicated `patterns.md` output file?
- What's the format — actionable recipes ("to add a new X, do Y") or
  descriptive ("the codebase follows pattern X")?
- Is there user confirmation before patterns are written to durable docs?
- Is there a dedicated pattern detection guide in the shared references?
- Does the subsystem doc template include a "Detected Patterns" section?

### Dimension 3: Recursive Subsystem Decomposition

Large subsystems need recursive decomposition to maintain doc quality.

Evaluate:
- What triggers decomposition? (file count? responsibility count? both?)
- What is the max depth? Is it enforced?
- Is there a dedicated lighter template for sub-modules (vs reusing the
  full subsystem template)?
- How does the parent doc reference child docs?
- When is recursion explicitly NOT applied? (many-files-one-pattern,
  generated code, single responsibility)
- How does recursion interact with state management
  (`.analysis-state.md`)?

### Dimension 4: Cursor Support

Cursor is one of the three target platforms. How seriously is it treated?

Evaluate:
- Is there a dedicated Cursor skill file (`SKILL.md`) with YAML
  frontmatter and auto-trigger keywords?
- Or is Cursor support just "paste the Codex prompts into Composer"?
- Does Cursor get equivalent functionality to Claude Code and Codex?
- Can Cursor run all 3 phases in one session (via skill) or must the
  user manually paste each phase?

### Dimension 5: Subsystem Doc Depth and Completeness

Subsystem docs are the deep reference an agent reads when working in a
specific area.

Evaluate:
- What sections does the subsystem template include? List them all.
- Is there a "Modification Guide" or equivalent (tells agents HOW to
  change code, not just what exists)?
- Is there a "Testing" section (test files, patterns, fixtures, gaps)?
- Is there an "Edge Cases and Gotchas" section (implicit contracts,
  race conditions, surprises)?
- Is there a "Detected Patterns" section (patterns local to this
  subsystem)?
- How are dependencies documented (internal vs external, load-bearing
  flag)?
- Is there a "Coverage Notes" section (what was read fully vs sampled)?

### Dimension 6: Wiring Instructions (Connecting Output to Agent)

After analysis completes, the user must wire `agent-docs/` into their
coding agent's config. This is the critical last mile.

Evaluate:
- Does the tool provide a multi-step tiered loading strategy, or just
  "add this one line to CLAUDE.md"?
- Does it force the agent to read context BEFORE writing code?
- Does it include a comprehension checkpoint (agent must state its
  understanding before acting)?
- Is there tiered loading (always load X, conditionally load Y based
  on task)?
- Is there a generated `agent-protocol.md` output file with wiring
  instructions, or are instructions only in the README / completion
  report?
- Are wiring instructions provided for all 3 platforms?

### Dimension 7: Shared Reference Quality

The shared references govern how well the analyzing agent explores
any codebase.

Evaluate:
- **Ecosystem playbook:** How many languages? Are there actual bash
  commands or just descriptions? Is there a generic fallback?
- **Scale-and-scope rules:** Are there explicit stop conditions?
  Generated code handling? Write eligibility criteria?
- **Subsystem mapping rubric:** Split/merge guidance? Naming guidance?
  Minimum evidence requirements? Monorepo-specific rules?
- **Checkpoint template/example:** How structured? Is there a concrete
  filled-out example?
- **Agent-context rules:** Is there a dedicated reference defining how
  to generate the primary deliverable? Token budget? Quality checklist?
- **Pattern detection guide:** Is there a dedicated reference for how
  to detect patterns?

### Dimension 8: Protocol and Behavioral Spec

How well is the overall tool behavior specified?

Evaluate:
- Is there a single canonical spec (`protocol.md`) or is behavior
  spread across individual command files?
- Does it define a quality bar ("good enough when..." / "not good
  enough if...")?
- Does it list failure modes to avoid?
- Does it define output priority (which file matters most)?
- Does it address re-run semantics in one place?
- Does it define the output root (`agent-docs/`) in one authoritative
  place?

### Dimension 9: Self-Containedness vs Modularity

What happens when the tool runs without shared resources?

Evaluate:
- Do Claude Code commands include inline fallback content (ecosystem
  tables, subsystem criteria, reading depth rules) so they work without
  `shared/`?
- What degrades if `shared/` is missing? Everything? Or just quality?
- Are templates inlined in commands (self-contained) or only in
  `shared/templates/` (requires the bundle)?
- Could someone install just the 3 command files and get a working
  (if lower-quality) analysis?

### Dimension 10: Output File Set

What exactly gets produced in `agent-docs/`?

Evaluate:
- List every file each candidate produces
- Is there an `agent-protocol.md` (generated wiring instructions that
  live IN the output)?
- How many total files? Is there output bloat — files that duplicate
  content from other files?
- What's the recommended reading order for an agent?
- Is there a `docs-schema.md` or equivalent defining the output tree?

### Dimension 11: Re-run and Incremental Update

The tool must support re-running on repos with existing `agent-docs/`.

Evaluate:
- Is augment-vs-overwrite behavior explicitly defined per phase?
- Which files are regenerated entirely vs updated selectively?
- Is stale content explicitly addressed? (Stale agent-context is worse
  than no context.)
- Is re-run behavior consistent across Claude Code, Codex, and Cursor?
- Is there a timestamp mechanism for updated docs?

### Dimension 12: Token Efficiency of Output

Every token loaded into an agent's context window costs — it displaces
tokens that could be used for the actual task.

Evaluate:
- What is the token budget for the primary deliverable?
- Are tables used where bullets would be more token-efficient?
- Is there content duplication between output files (e.g., patterns
  appearing in both agent-context and patterns.md)?
- If an agent loads the primary deliverable + one subsystem doc, how
  many total tokens is that approximately?
- Is there unnecessary prose that could be replaced with structured
  key-value content?

### Dimension 13: Unique Strengths

What does each candidate have that the other lacks entirely?

For each unique element:
- Name it and cite the specific file
- Assess: is this genuinely valuable for a coding agent, or is it
  unnecessary complexity / nice-to-have-for-humans?
- Would the other candidate be materially better if it had this?

---

## Phase 3: Synthesis

After the dimension comparison, produce these sections:

### What A does better than B

Bullet list. Each bullet must reference a specific file path and quote
the relevant passage. Not generalities — specifics.

### What B does better than A

Same format.

### Gaps in both

What is missing from BOTH implementations that would improve coding
agent efficiency? Think about:
- What would a coding agent actually need at runtime that neither
  provides?
- Are there common scenarios neither handles well?
- Are there output formats more efficient than what either produces?
- Is there anything both do that actually doesn't help agents?

### Recommendation

Choose exactly one:

**(a)** Use A as-is — it's good enough, no changes needed.

**(b)** Use B as-is — it's good enough, no changes needed.

**(c)** Use A as the base, cherry-pick specific things from B.
For each cherry-pick: name the source file in B, name the target
location in A, describe what changes. Example level of specificity:
"Take `cursor/SKILL.md` from B and replace A's `cursor/install.md`
with it. This gives A proper Cursor auto-trigger support."

**(d)** Use B as the base, cherry-pick specific things from A.
Same specificity requirements.

**(e)** Neither is sufficient. Fundamental redesign needed.
Explain specifically what's wrong at the architectural level.

State your confidence level: high / medium / low. Explain what would
change your mind.

---

## Rules

- **Read every file before judging.** First impressions from file
  names and directory structure are often wrong. The actual content is
  what matters.
- **Quote, don't paraphrase.** When citing evidence, quote the actual
  text from the file. This prevents memory errors and lets the reader
  verify.
- **Pick winners.** Ties should be rare. If you can't decide, ask:
  "which one helps the coding agent more at runtime?" and that breaks
  the tie.
- **Token efficiency is a first-class concern.** A 150-line file
  loaded on every task is not "just 30 more lines" than 120 — it's
  25% more context window consumed on every single session. Evaluate
  accordingly.
- **Distinguish tool-time from runtime.** Some features help the
  ANALYZING agent do a better job (tool-time). Others help the CODING
  agent that later reads the output (runtime). Both matter, but runtime
  impact on coding agents is the primary objective. Call out which is
  which when evaluating.
- **Don't confuse completeness with quality.** More files, more
  sections, more words is not inherently better. If it doesn't help
  the coding agent at runtime, it's bloat.
- **Look for what's missing, not just what's present.** The most
  important finding might be something neither candidate does.
