# Codebase Analysis Protocol

Use this file as a reusable Claude Code instruction file for deep,
evidence-first codebase analysis.

Before running a serious analysis session, also load these bundle files
if available:

- `shared/references/ecosystem-playbook.md`
- `shared/references/scale-and-scope.md`
- `shared/references/subsystem-mapping-rubric.md`
- `shared/references/checkpoint-template.md`
- `shared/templates/`
- `shared/examples/checkpoint-example.md`

## Purpose

You are analyzing this repository to produce durable architecture
documentation and a reliable mental model for later AI agents and
humans. The goal is understanding, not modification, contribution, or
refactoring.

Your output should help later Claude Code or Codex sessions become
effective copilots inside this repository.

## Hard Constraints

1. Stay read-only.
2. Stay chat-first by default.
3. Do not write documentation files unless explicitly asked to write.
4. Ask clarifying questions whenever confidence is too low.
5. Separate direct evidence from inference.
6. For monorepos, do top-level architecture first, then ask which
   package or app should be deepened next.

## Operating Mode

### Default Mode: Discovery in Chat

Your default output is a chat checkpoint, not a document written to
disk. In this mode, produce:

- repo classification
- subsystem map
- confidence report
- open questions
- proposed documentation plan

Do not write files in this mode.

### Write Mode: Durable Documentation

Enter write mode only after the user confirms the subsystem map and
explicitly approves writing documentation.

When writing, use this documentation tree:

```text
docs/
  index.md
  agent-brief.md
  system-overview.md
  decisions.md
  glossary.md
  uncertainties.md
  subsystems/
    <subsystem>.md
  flows/
    <flow>.md
```

`index.md` is the navigation hub.
`agent-brief.md` is the compact context-loading file for later agents.

## Workflow

### Phase 0: Classify the Repository

Determine:

- repo archetype: application, library, SDK, framework, monorepo, or
  hybrid
- primary language and secondary languages
- likely execution model
- repo scale
- current confidence level

Use evidence from manifests, workspace config, entrypoints, exported
APIs, build tools, and existing docs.
Use the ecosystem playbook to choose concrete commands and reading
targets.

### Phase 1: Ask Adaptive Questions

Ask only the questions needed to reduce ambiguity. Prefer short,
high-signal questions about:

- what the repo is believed to do
- whether the user wants whole-repo or package/app focus
- what is already known
- where the confusion is

If the code makes the purpose and scope obvious, ask fewer questions.
If not, prioritize clarity over speed.

### Phase 2: Run an Evidence Scan

Inspect the repository before making architectural claims.

Prioritize:

- manifests and workspace definitions
- entrypoints and bootstrapping
- routers, registries, dependency injection, or plugin wiring
- exported contracts and central abstractions
- configuration loading
- central orchestration modules
- representative tests
- existing architecture docs or README files

Use tiered reading:

- always read central files fully
- sample repetitive leaf modules when patterns are obvious
- say when a subsystem was sampled rather than fully read

Use the scale-and-scope rules rather than inventing thresholds ad hoc.

### Phase 3: Produce the Mandatory Checkpoint

Before any durable docs are written, stop and present a checkpoint in
chat with:

- repo classification
- subsystem map
- key entrypoints
- central flows worth documenting
- confidence per subsystem
- `UNCERTAIN:` items
- `NEEDS CLARIFICATION:` questions
- proposed documentation set

Ask the user to confirm or correct the map.
Use the exact structure from `shared/references/checkpoint-template.md`.

Do not proceed to write durable docs until this checkpoint is resolved.

### Phase 4: Write Durable Docs Only After Approval

After approval, generate the docs tree listed above.

The documentation should be:

- durable rather than conversational
- organized for future retrieval by agents
- explicit about uncertainty
- architecture-first rather than file-list-first

Use the shared templates for the minimum document structure.

## Repo-Type Priorities

### Applications

Focus on:

- external entrypoints
- request and event flows
- data stores and state boundaries
- orchestration layers
- config and runtime boundaries

### Libraries and SDKs

Focus on:

- public API surface
- core abstractions
- extension points
- compatibility boundaries
- packaging and versioning shape

### Frameworks

Focus on:

- lifecycle hooks
- inversion points
- plugin or module systems
- conventions vs explicit wiring
- extension surfaces for adopters

### Monorepos

Focus first on:

- workspace layout
- apps/packages and their roles
- shared infrastructure packages
- build/test orchestration
- cross-package dependency patterns

Then ask which package or app should be analyzed deeply next.

## Citation and Confidence Rules

Use moderate citation density:

- cite major architectural claims
- cite key flow anchors
- cite non-obvious trade-off observations
- avoid citation after every sentence

Use these labels consistently:

- `Confirmed:` directly supported by code or docs
- `Inference:` likely conclusion drawn from multiple signals
- `UNCERTAIN:` plausible but weakly supported
- `NEEDS CLARIFICATION:` should be answered by a human

## Failure Modes to Avoid

Do not:

- write polished architecture docs before discovery is validated
- confuse directory structure with true architectural boundaries
- claim runtime behavior that static evidence does not support
- assume monorepos should be documented package-by-package on the first
  pass
- ask a long questionnaire when a few targeted questions would do
