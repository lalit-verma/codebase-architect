---
name: codebase-analysis-protocol
description: >
  Evidence-first architecture analysis for unfamiliar repositories.
  Use this skill when the user wants to understand a codebase deeply,
  generate durable architecture documentation, map subsystem boundaries,
  or prepare docs that later Codex or Claude sessions can consume.
  This skill is for learning and documentation, not code changes. It is
  chat-first by default, read-only by default, supports applications,
  libraries, SDKs, frameworks, and monorepos, and asks for clarification
  whenever confidence is too low.
---

# Codebase Analysis Protocol

Use `references/protocol.md` for the portable protocol summary and
`references/docs-schema.md` for the durable docs structure.

For high-quality output, also follow the bundle-wide shared materials:

- `../shared/references/ecosystem-playbook.md`
- `../shared/references/scale-and-scope.md`
- `../shared/references/subsystem-mapping-rubric.md`
- `../shared/references/checkpoint-template.md`
- `../shared/templates/`
- `../shared/examples/checkpoint-example.md`

## Behavior Contract

- Stay read-only.
- Stay chat-first unless the user explicitly approves writing docs.
- Clarify low-confidence assumptions instead of guessing.
- For monorepos, do top-level architecture first and then ask which
  package or app to deepen.
- Optimize for durable docs that later agents can consume.

## Default Workflow

### 1. Classify First

Determine:

- repo archetype
- primary language
- execution model
- repo scale

Do not start writing documentation yet.

### 2. Ask Adaptive Questions

Ask only what is needed to reduce ambiguity. Prioritize:

- what the repo is believed to do
- whether the user wants whole-repo or package/app focus
- what is already known
- what is especially important or confusing

If the code evidence is already clear, keep questions minimal.

### 3. Run an Evidence Scan

Inspect:

- manifests and workspace config
- entrypoints and orchestration
- public contracts
- registries, routers, DI, or plugin wiring
- config loading
- existing docs
- representative tests

Use tiered reading. Do not pretend every file was read in large repos.
Use the ecosystem playbook and scale rules instead of improvising.

### 4. Stop at the Checkpoint

Produce a chat-only checkpoint containing:

- repo classification
- subsystem map
- confidence per subsystem
- open questions
- a proposed docs plan

Ask the user to confirm or correct it.
Use the strict format from `../shared/references/checkpoint-template.md`.

Do not write durable docs before this confirmation.

### 5. Write Only After Approval

If the user explicitly asks to persist docs, write them using the
schema in `references/docs-schema.md`.

Use the shared templates for the actual document body shape.

Default output tree:

```text
docs/
  index.md
  agent-brief.md
  system-overview.md
  decisions.md
  glossary.md
  uncertainties.md
  subsystems/
  flows/
```

## Required Labels

Use these explicitly:

- `Confirmed:`
- `Inference:`
- `UNCERTAIN:`
- `NEEDS CLARIFICATION:`

## Citation Rule

Be moderately strict:

- cite major architectural claims
- cite flow anchors
- cite non-obvious design judgments
- do not attach citations to every sentence

## Anti-Patterns

Do not:

- generate polished docs before the subsystem map is confirmed
- infer undocumented runtime behavior as fact
- treat monorepos as single-package codebases
- overwhelm the user with unnecessary questions
- switch from analysis into modification work
