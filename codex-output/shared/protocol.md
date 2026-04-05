# Shared Analysis Protocol

This protocol is the canonical workflow for producing high-quality,
durable architecture documentation from an unfamiliar repository.

It is designed for learning and long-term reuse by later agents. It is
not designed for editing, refactoring, or contributing code.

## Core Objectives

- understand what the repository is for
- identify the architectural boundaries that matter
- capture design decisions and trade-offs with evidence
- produce durable docs that later agents can consume efficiently
- avoid confident guesses when the evidence is weak

## Hard Rules

- Default to read-only behavior.
- Default to chat-first behavior.
- Do not write any docs unless the user explicitly approves writing.
- If confidence is low on purpose, subsystem boundaries, runtime flow,
  or package ownership, ask clarifying questions before proceeding.
- Treat undocumented intent as inference, not fact.
- Do not pretend completeness on very large or highly dynamic repos.

## Output Modes

### Mode A: Chat-Only Discovery

Use this by default. Produce:

- repo classification
- subsystem map
- confidence report
- open questions
- proposed documentation plan

Do not write files in this mode.

### Mode B: Durable Docs

Enter this mode only after the user confirms the subsystem map and
explicitly asks for documentation to be written. Use the structure in
`docs-schema.md`.

## Required Companion References

Use these shared files during analysis:

- `references/ecosystem-playbook.md` for language and ecosystem
  discovery
- `references/scale-and-scope.md` for depth limits and stop conditions
- `references/subsystem-mapping-rubric.md` for deciding what counts as
  a subsystem
- `references/checkpoint-template.md` for the exact chat checkpoint
- `templates/` for durable document structure
- `examples/checkpoint-example.md` as the target shape for checkpoint
  quality

## Phase 0: Classify the Repository

Before deep analysis, classify the repo along these axes:

- repo archetype: application, library, SDK, framework, monorepo, or
  hybrid
- primary language and secondary languages
- execution model: CLI, server, worker, plugin host, library-only,
  build tool, or mixed
- scale: small, medium, large
- confidence: high, medium, or low

### Classification Signals

Use evidence such as:

- manifests and workspace files
- package/crate/module layout
- entrypoints and exported APIs
- framework or runtime markers
- build and test configuration
- README and architecture docs, if present

Then use `references/ecosystem-playbook.md` to guide the first-pass
commands and reading order.

### Monorepo Rule

For monorepos, default to top-level architecture only on the first
pass. Identify:

- workspace manager
- top-level apps and packages
- shared infrastructure packages
- likely ownership boundaries
- cross-package dependency patterns

Then stop and ask which package or app should be deepened next.

Do not attempt full package-level deep dives by default.

## Phase 1: Adaptive User Alignment

Ask only the minimum questions needed to avoid low-confidence
assumptions.

Preferred question themes:

- what the user believes the repo is for
- what they need the docs for
- whether they care about the whole repo or a package/app
- whether there are known hot areas or confusing subsystems

### Questioning Rule

If the code makes the repo purpose and scope clear, ask fewer
questions. If the evidence is ambiguous, ask more. Clarity beats speed
when confidence is low.

## Phase 2: Evidence Scan

Gather evidence before producing polished explanations.

Always prioritize:

- manifests and workspace config
- entrypoints and bootstrapping code
- public contracts and exported APIs
- registries, routers, dependency injection, or plugin wiring
- central orchestration modules
- configuration loading
- tests that reveal intended behavior
- existing docs, if present

Use the ecosystem playbook to choose concrete commands rather than
inventing repo-by-repo ad hoc exploration.

### Repo-Type Priorities

#### Applications

Focus on:

- external entrypoints
- request or event flows
- state and storage
- orchestration layers
- configuration and deployment boundaries

#### Libraries and SDKs

Focus on:

- public API surface
- compatibility boundaries
- core abstractions and extension points
- error handling model
- packaging and versioning structure

#### Frameworks

Focus on:

- lifecycle hooks
- inversion-of-control points
- plugin or module registration
- conventions vs explicit wiring
- extension surfaces for adopters

#### Monorepos

Focus on:

- workspace graph
- app/package roles
- shared packages
- build and test orchestration
- architectural seams between packages

## Phase 3: Subsystem Mapping

Before any durable docs are written, produce a subsystem map in chat.

Use `references/subsystem-mapping-rubric.md` to decide whether a folder
or package is a real subsystem or just supporting noise.

For each subsystem, include:

- name
- path or package scope
- probable responsibility
- key entry files or contracts
- major dependencies
- confidence level

Also include:

- what seems central vs peripheral
- what remains unclear
- what should be documented first

### Mandatory Checkpoint

Stop after presenting the subsystem map. Ask the user to confirm:

- what is correct
- what is mislabeled
- what should be out of scope
- for monorepos, which package/app to deepen next

Use the exact structure from `references/checkpoint-template.md`. Do
not replace it with a free-form summary.

Do not write durable docs before this checkpoint is resolved.

## Phase 4: Documentation Plan

After the subsystem map is confirmed, propose the documentation set in
chat before writing.

The plan should include:

- files to be generated
- intended audience
- scope boundary
- known uncertainties that will remain
- expected citation density

If the user does not approve writing, stay in chat and continue with
analysis only.

## Phase 5: Durable Documentation

If the user approves writing, generate the documents described in
`docs-schema.md`.

Use the templates in `templates/` rather than inventing document
structure from scratch.

Documentation should be:

- durable rather than conversational
- easy for humans to skim
- easy for later agents to load incrementally
- explicit about uncertainty
- structured around architecture, not file-by-file churn

## Confidence and Clarification Rules

Use these labels consistently:

- `Confirmed:` grounded directly in code or docs
- `Inference:` inferred from multiple code signals
- `UNCERTAIN:` plausible but weakly supported
- `NEEDS CLARIFICATION:` should be answered by a human if accuracy
  matters

Ask for clarification when any of these are true:

- the repo purpose is ambiguous
- subsystem boundaries are not stable
- monorepo ownership is unclear
- dynamic registration hides the actual runtime graph
- generated code obscures the control flow
- the user’s stated purpose conflicts with the code evidence

## Citation Policy

Citations should be moderately strict and easy to consume.

Use these rules:

- each major section should anchor itself in 1-3 concrete references
- major architectural claims should cite the files that establish them
- flow descriptions should cite the entrypoint and key handoffs
- trade-off analysis may cite code plus explicitly labeled inference
- avoid attaching a citation to every sentence

Good coverage is more important than exhaustive footnoting.

## Read Scope Rules

Do not blindly read every file in large repos.

Use the thresholds and stop conditions in
`references/scale-and-scope.md`.

Use tiered reading:

- always read central files fully
- sample repetitive leaf modules when patterns are obvious
- use tests selectively to validate intended behavior
- note when coverage is sampled rather than exhaustive

For small subsystems, full reading is acceptable.

## Durable Doc Writing Rules

When writing docs:

- every file should answer a distinct retrieval question
- `index.md` and `agent-brief.md` should stay concise and high signal
- subsystem docs should center on boundaries, contracts, and flows
- flow docs should explain architectural learning value, not narrate
  every helper call
- decisions docs should separate code facts from inferred rationale
- unresolved ambiguity must be preserved in `uncertainties.md`

## Quality Bar

The analysis is good enough when it:

- explains what the system is and how it is organized
- identifies the real architectural seams
- traces the most important flows with evidence
- captures meaningful trade-offs instead of generic praise
- gives later agents a reliable starting map

The analysis is not good enough if it:

- reads like boilerplate architecture prose
- hides uncertainty
- overstates confidence
- confuses code organization with architectural responsibility
- claims runtime facts that are not evidenced
