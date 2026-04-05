# Codebase Analysis Protocol

Canonical behavioral specification for evidence-first codebase analysis.

This protocol produces documentation whose **primary consumer is a
coding agent** (Claude Code, Codex, Cursor). Human readability is a
secondary benefit. Every output decision should be evaluated against:
"does this help an agent write better code in this repo?"

## Core Objectives

1. Generate a compact, actionable agent-context file that a coding agent
   loads at session start to gain deep codebase understanding.
2. Detect and document recurring code patterns so agents follow
   established conventions rather than inventing new ones.
3. Map architectural boundaries, contracts, and flows with evidence.
4. Capture design decisions and constraints that prevent agents from
   making bad changes.
5. Preserve uncertainty explicitly — false confidence is worse than
   admitted gaps.

## Hard Rules

- Default to read-only. Never modify, reformat, or refactor source code.
- Default to chat-first. Present findings for confirmation before writing
  files. Write to `agent-docs/` only after explicit user approval.
- Do not write durable docs before the subsystem map is confirmed.
- If confidence is low on repo purpose, subsystem boundaries, runtime
  flows, or package ownership — ask clarifying questions before
  proceeding.
- Treat undocumented intent as inference, not fact.
- Do not pretend completeness on very large or highly dynamic repos.
- For monorepos, do top-level architecture first, then ask which slice
  to deepen. Do not attempt full package-level deep dives by default.

## Output Root

All generated documentation is written to `agent-docs/` in the target
repository root. This avoids collisions with the repo's own `docs/`
folder.

```
agent-docs/
  .analysis-state.md          # cross-phase state (internal)
  agent-context.md            # PRIMARY: compact agent-loadable context
  patterns.md                 # detected code patterns and conventions
  agent-brief.md              # compact architecture map
  agent-protocol.md           # wiring instructions for agents
  index.md                    # navigation hub
  system-overview.md          # top-level architecture
  decisions.md                # architectural trade-offs
  glossary.md                 # project-specific terms
  uncertainties.md            # unresolved questions
  subsystems/
    {name}.md                 # one per subsystem
    {name}/                   # sub-module docs (if recursion)
      {child}.md
  flows/
    {name}.md                 # cross-cutting flows (if warranted)
```

## Output Priority

When making trade-offs about depth, token budget, or time:

1. `agent-context.md` — highest priority. The single file a coding agent
   loads to become effective.
2. `patterns.md` — actionable "how to add a new X" recipes.
3. `agent-brief.md` — compact architecture for deeper context loading.
4. `subsystems/*.md` — on-demand deep reference per subsystem.
5. Everything else — supporting documentation.

## The Three Phases

### Phase 1: Discover & Map

Run once per repo. Classify, scan evidence, map subsystems, present
checkpoint for user confirmation.

Internal steps:
1. Classify the repository (archetype, language, execution model, scale)
2. Ask adaptive questions (only if evidence is insufficient)
3. Run evidence scan (follow ecosystem playbook, apply scale rules)
4. Map subsystems (apply mapping rubric, flag recursion candidates)
5. Detect preliminary patterns (note repetitive file clusters)
6. Present mandatory checkpoint (use checkpoint template, 8 sections)
7. Write `agent-docs/.analysis-state.md` and
   `agent-docs/system-overview.md` after user confirms

### Phase 2: Deep Dive

Run once per subsystem. Analyze boundaries, contracts, flows,
dependencies, patterns. Recursively decompose large subsystems.

Internal steps:
1. Read analysis state, match target subsystem
2. Read subsystem files (depth per scale rules)
3. Evaluate recursion need — propose decomposition if warranted
4. Analyze: boundaries, structure, contracts, flows, dependencies,
   config, design decisions, testing, edge cases, patterns
5. Write `agent-docs/subsystems/{name}.md` (and children if recursive)
6. Update analysis state

### Phase 3: Synthesize

Run once per repo. Generate agent-context.md FIRST, then patterns.md,
then remaining documentation.

Internal steps:
1. Read all existing agent-docs/
2. Generate `agent-docs/agent-context.md` (primary output)
3. Generate `agent-docs/patterns.md` (semi-automated: propose, confirm)
4. Generate remaining docs (agent-brief, index, decisions, glossary,
   uncertainties, flow docs, agent-protocol)
5. Report completion with agent integration instructions

## State Persistence

Cross-phase state is stored in `agent-docs/.analysis-state.md`:

```yaml
phase_completed: {1|2|3}
generated_on: {date}
output_root: agent-docs
subsystems_pending: [{list}]
subsystems_completed: [{list}]
recursion_candidates: [{list}]
preliminary_patterns: [{list}]
```

Each phase reads this file before proceeding. Phase 2 updates it after
each subsystem. This enables multi-session analysis.

## Re-run Semantics

All phases support re-runs on repos with existing `agent-docs/`:

- Read existing state first.
- Compare against current code.
- Augment rather than overwrite — preserve accurate sections.
- Flag new, removed, or changed subsystems.
- Reset pending status for subsystems that changed significantly.
- Regenerate `agent-context.md` and `patterns.md` entirely on re-run
  (they are compact enough to rewrite; stale context is harmful).
- Add update timestamp to modified files.

## Confidence and Clarification Labels

Use these labels consistently in all analysis output:

- `Confirmed:` directly supported by code or docs
- `Inference:` likely conclusion drawn from multiple code signals
- `UNCERTAIN:` plausible but weakly supported
- `NEEDS CLARIFICATION:` should be answered by a human

Ask for clarification when:
- repo purpose is ambiguous
- subsystem boundaries are not stable
- monorepo ownership is unclear
- dynamic registration hides the actual runtime graph
- generated code obscures the control flow
- user's stated purpose conflicts with code evidence

Note: `agent-context.md` does NOT use these labels. It contains only
confirmed and high-confidence inferred facts, stated as plain
assertions. Uncertainty belongs in `uncertainties.md`.

## Citation Policy

Use moderate citation density:

- Each major section anchors itself in 1-3 concrete file references.
- Major architectural claims cite the files that establish them.
- Flow descriptions cite the entrypoint and key handoffs.
- Trade-off analysis may cite code plus explicitly labeled inference.
- Avoid attaching a citation to every sentence.

Good coverage is more important than exhaustive footnoting.

## Repo-Type Priorities

### Applications
- External entrypoints
- Request or event flows
- State and storage boundaries
- Orchestration layers
- Configuration and deployment boundaries

### Libraries and SDKs
- Public API surface
- Compatibility boundaries
- Core abstractions and extension points
- Error handling model
- Packaging and versioning structure

### Frameworks
- Lifecycle hooks
- Inversion-of-control points
- Plugin or module registration
- Conventions vs explicit wiring
- Extension surfaces for adopters

### Monorepos
- Workspace graph
- App/package roles
- Shared packages
- Build and test orchestration
- Architectural seams between packages
Then ask which package or app to deepen next.

## Recursive Decomposition

Large subsystems produce shallow documentation when forced into a single
file. The protocol supports recursive decomposition:

**Triggers** (evaluate during Phase 2):
- Subsystem has 50+ files, OR
- Subsystem contains 3+ internal modules with own contracts/entrypoints

**When triggered:**
1. Propose decomposition in chat with candidate sub-modules.
2. Wait for user confirmation.
3. Write parent doc (`agent-docs/subsystems/{name}.md`) covering overview,
   internal map, cross-cutting concerns.
4. Deep-dive each sub-module, writing to
   `agent-docs/subsystems/{name}/{child}.md`.

**Depth limit:** 3 levels maximum (system -> subsystem -> sub-module).
- Depth 1: every subsystem (default)
- Depth 2: 50+ files OR 3+ internal modules
- Depth 3: hard stop — summarize remaining complexity

**When NOT to decompose:**
- Many files following one pattern (e.g., 50 handler files with identical
  structure) — document the pattern, not each file.
- Files that are mechanically generated.
- Folders that are large but have a single clear responsibility.

## Pattern Detection

Patterns are the highest-impact output for coding agents. A "pattern"
is a recurring code structure that an agent should follow when adding
new instances of the same kind.

**Detection criteria:** 3+ files following structurally similar shape
(same directory, similar naming, similar internal structure).

**Semi-automated flow:**
1. Phase 1: detect preliminary patterns during evidence scan, include in
   checkpoint for user awareness.
2. Phase 2: refine pattern detection per subsystem during deep dive.
   Record pattern name, example file, file list, structure, registration
   points.
3. Phase 3: consolidate all detected patterns. Present to user for
   confirmation before writing `patterns.md`.

**What is NOT a pattern:**
- Single-instance files.
- Generic language idioms (e.g., "Go uses interfaces").
- Generated code structures.
- Standard framework boilerplate documented in framework docs.

## Agent Context Generation Rules

`agent-context.md` is the primary deliverable. It must:

- Stay under 120 lines / ~3K tokens.
- Contain only actionable content — no prose, no explanations.
- Use concrete file paths, not abstract subsystem names.
- Use flat markdown: `##` headings, `- ` bullets, `` `code refs` ``.
- Not use tables (they waste tokens for agents).
- Not use confidence labels (this is output for agents, not analysis).
- Be standalone: an agent reading only this file should know where
  everything is and what patterns to follow.
- Be regenerated entirely on re-runs (compact enough to rewrite; stale
  context is harmful).

## Quality Bar

The analysis is good enough when:
- `agent-context.md` lets an agent navigate the repo and follow patterns
  without reading any other file.
- `patterns.md` contains actionable recipes that match real code.
- Subsystem docs identify real architectural seams with evidence.
- Important flows are traced with file references.
- Design decisions capture constraints an agent must respect.
- Uncertainty is preserved, not hidden.

The analysis is not good enough if:
- It reads like boilerplate architecture prose.
- It hides uncertainty or overstates confidence.
- It confuses file organization with architectural responsibility.
- It claims runtime behavior without static evidence.
- `agent-context.md` contains descriptions instead of navigation.
- Patterns are theoretical rather than observed in code.

## Failure Modes to Avoid

- Writing polished docs before the subsystem map is confirmed.
- Confusing directory structure with true architectural boundaries.
- Claiming runtime behavior that static evidence does not support.
- Assuming monorepos should be documented package-by-package on the
  first pass.
- Asking a long questionnaire when a few targeted questions would do.
- Generating prose-heavy output that burns agent context window tokens.
- Documenting patterns that don't actually exist in the code.
- Decomposing subsystems that are large but uniform (use patterns instead).

## Required Companion References

During analysis, load these files from the shared resources directory:

- `references/ecosystem-playbook.md` — language-specific exploration
- `references/scale-and-scope.md` — reading depth and stop conditions
- `references/subsystem-mapping-rubric.md` — subsystem identification
- `references/checkpoint-template.md` — mandatory checkpoint format
- `references/agent-context-rules.md` — agent-context generation rules
- `references/pattern-detection-guide.md` — pattern detection method
- `templates/` — output document structures
- `examples/` — quality calibration targets
