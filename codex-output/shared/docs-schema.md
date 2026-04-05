# Durable Documentation Schema

Use this schema only after the user confirms the subsystem map and
approves writing docs.

Target root:

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

The structure is intentionally retrieval-friendly for later agents.
`index.md` and `agent-brief.md` are the primary entry points.

Use the concrete files in `templates/` when writing these docs. The
sections below describe intent; the templates define the minimum shape.

## 1. `docs/index.md`

Purpose:

- navigation hub for humans and agents
- explain what exists, how to read it, and where confidence is weak

Recommended sections:

- repository summary
- documentation scope
- recommended reading order
- subsystem inventory table
- flow inventory table
- quick links
- confidence summary

Guidance:

- keep concise
- optimize for orientation, not completeness
- include pointers to the most important files
- use `templates/index-template.md`

## 2. `docs/agent-brief.md`

Purpose:

- compact context-loading file for later Codex/Claude sessions
- summarize the architecture without forcing the agent to read the
  whole docs tree first

Recommended sections:

- what this repository is for
- repo archetype and scale
- top-level architectural shape
- most important subsystems
- most important flows
- key design decisions
- known uncertainties
- suggested next docs to read

Guidance:

- target compactness over completeness
- keep it high signal
- avoid deep prose
- reference other docs rather than duplicating them
- use `templates/agent-brief-template.md`

## 3. `docs/system-overview.md`

Purpose:

- durable high-level architecture overview
- establish the system shape before the reader dives into subsystem docs

Recommended sections:

- system purpose
- external actors and boundaries
- major subsystems
- architectural style
- primary runtime or usage flows
- data/state boundaries
- configuration model
- strengths and concerns

Guidance:

- include diagrams only when they reduce ambiguity
- focus on system-level seams and interactions
- use `templates/system-overview-template.md`

## 4. `docs/subsystems/<subsystem>.md`

Purpose:

- deep understanding of a single subsystem

Recommended sections:

- role in the system
- boundaries and dependencies
- key contracts and types
- main control flows
- configuration inputs
- tests and evidence quality
- design decisions and trade-offs
- open questions

Guidance:

- organize by architecture, not by raw file order
- cite enough to audit the claims
- mark sampled coverage when not all files were read
- use `templates/subsystem-template.md`

## 5. `docs/flows/<flow>.md`

Purpose:

- trace an end-to-end flow that crosses important boundaries

Recommended sections:

- trigger
- preconditions
- sequence of handoffs
- state changes or side effects
- failure handling
- notable trade-offs

Guidance:

- choose flows that teach the architecture
- prefer a few important flows over many trivial ones
- use `templates/flow-template.md`

## 6. `docs/decisions.md`

Purpose:

- consolidate the main architectural decisions and trade-offs

Recommended sections:

- what was chosen
- what it enables
- what it costs
- alternatives
- assessment

Guidance:

- separate code facts from inferred rationale
- focus on decisions that shape multiple areas
- use `templates/decisions-template.md`

## 7. `docs/glossary.md`

Purpose:

- define project-specific terms, abstractions, and overloaded names

Recommended sections:

- term
- meaning
- where used
- related docs

Guidance:

- prioritize terms that would confuse a new engineer or another agent
- use `templates/glossary-template.md`

## 8. `docs/uncertainties.md`

Purpose:

- preserve unresolved questions rather than burying them in prose

Recommended sections:

- uncertain claim
- why it is uncertain
- evidence seen
- what would resolve it

Guidance:

- this file prevents false confidence from contaminating the rest of
  the docs
- use `templates/uncertainties-template.md`

## Citation Guidance

Use moderate citation density:

- cite major claims
- cite flow anchors
- cite non-obvious design observations
- avoid citation spam

Acceptable patterns:

- section-level evidence anchors
- inline file references for pivotal claims
- explicit `Inference:` tags for design rationale
- explicit `Coverage mode:` notes in subsystem docs when sampling was
  used

## Writing Order

Recommended generation order after approval:

1. `system-overview.md`
2. `index.md`
3. `agent-brief.md`
4. `subsystems/`
5. `flows/`
6. `decisions.md`
7. `glossary.md`
8. `uncertainties.md`

If the repo is large, write only the docs that the confirmed scope can
support with reasonable confidence.
