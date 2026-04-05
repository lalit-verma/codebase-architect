# Codex Wrapper Reference: Protocol Summary

This file is the short local summary for the Codex wrapper. When the
bundle's `shared/` directory is available, prefer the richer workflow
there for better quality and consistency.

## Defaults

- read-only by default
- chat-first by default
- durable docs only after explicit approval
- clarification over low-confidence assumptions

## Required Sequence

1. Classify the repository
2. Ask adaptive questions only where needed
3. Run an evidence scan
4. Present a checkpoint in chat
5. Write durable docs only after confirmation and approval

## Required Checkpoint Output

Before writing docs, present:

- repo archetype and scale
- primary language and execution model
- subsystem map
- likely key entrypoints
- central flows worth documenting
- confidence levels
- `UNCERTAIN:` items
- `NEEDS CLARIFICATION:` items
- proposed docs plan

## Repo-Type Rules

### Applications

Prioritize external entrypoints, request or event flows, state
boundaries, orchestration, and configuration.

### Libraries and SDKs

Prioritize public API surfaces, extension points, compatibility
boundaries, abstractions, and packaging shape.

### Frameworks

Prioritize lifecycle hooks, inversion points, registration systems,
conventions, and extension surfaces.

### Monorepos

Do top-level architecture first:

- workspace layout
- top-level apps/packages
- shared packages
- build/test orchestration
- cross-package dependency patterns

Then ask which package or app to deepen next.

## Labels

Use:

- `Confirmed:`
- `Inference:`
- `UNCERTAIN:`
- `NEEDS CLARIFICATION:`

## Citation Rule

Use moderate citation density:

- cite major architectural claims
- cite key flow anchors
- cite non-obvious design observations
- avoid citation after every sentence

## Quality Addendum

If `../shared/` exists, also use:

- `../shared/references/ecosystem-playbook.md`
- `../shared/references/scale-and-scope.md`
- `../shared/references/subsystem-mapping-rubric.md`
- `../shared/references/checkpoint-template.md`
- `../shared/templates/`
- `../shared/examples/checkpoint-example.md`
