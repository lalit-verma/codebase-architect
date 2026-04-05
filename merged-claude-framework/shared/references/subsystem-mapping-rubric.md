# Subsystem Mapping Rubric

Use this rubric to decide what counts as a subsystem, when to split or
merge, and when to flag a subsystem for recursive decomposition.

## What Counts as a Subsystem

A subsystem is a meaningful architectural unit, not merely a folder.
It must satisfy at least 2 of these criteria:

- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Is referenced across multiple parts of the system as a unit

Examples: request handling layer, provider abstraction, storage layer,
plugin registry, build graph package in a monorepo.

Non-examples (unless unusually central): generic utility folders, test
helpers, DTO-only folders with no meaningful behavior, generated code
directories.

## How to Split or Merge

### Split when:
- A directory contains multiple distinct responsibilities
- One area has a public contract and another is pure implementation
- One area has a different runtime role (e.g., CLI versus worker)
- One area has materially different dependencies or ownership

### Merge when:
- Two packages act as one conceptual unit with trivial separation
- One folder is just types/constants/helpers for another subsystem
- Splitting would produce documentation noise rather than insight

## Naming Guidance

Prefer names based on responsibility, not folder spelling alone.

Good: "API request layer", "workspace graph loader", "provider adapter
layer"

Weak: "utils", "common", "lib"

If a folder name is all you have, mark the label as tentative.

## Classification Tags

Tag each subsystem with one primary role:

- `entrypoint` — where execution begins
- `orchestration` — coordinates other subsystems
- `domain/core` — business logic and domain rules
- `integration` — talks to external systems
- `storage` — persistence and data access
- `configuration` — config loading and validation
- `tooling/build` — build, lint, deploy tooling
- `ui/presentation` — user interface layer
- `shared` — cross-cutting utilities with real architectural weight
- `generated` — auto-generated code

## Confidence Rules

- `high` — responsibility and boundaries are clearly evidenced
- `medium` — responsibility is likely but some edges are fuzzy
- `low` — provisional, inferred from directory shape only

Low-confidence subsystems should trigger clarification questions before
durable docs are written.

## Minimum Evidence for Each Subsystem Entry

Every subsystem in the checkpoint must include:

- Name
- Path or package scope
- Primary role tag
- Short responsibility statement (1-2 sentences)
- 2-5 evidence anchors (file paths that establish the claim)
- Key dependencies
- Confidence level

If you cannot supply evidence anchors, the subsystem is not ready to
be documented as a durable unit.

## Recursion Flagging

During Phase 1 checkpoint, flag subsystems that are candidates for
recursive decomposition during Phase 2:

- 50+ files visible in the subsystem directory
- Multiple internal sub-directories with own contracts or entrypoints
- Mixed responsibilities visible from file naming

Mark these in the checkpoint subsystem table with a "Recursion?" column.
The actual decision to decompose happens during Phase 2 deep dive, with
user confirmation. Maximum depth: 3 levels (system -> subsystem ->
sub-module).

## Monorepo-Specific Guidance

On the first pass, treat these as likely top-level subsystem classes:

- Apps and services (each is typically one subsystem)
- Shared packages (group by responsibility, not one-per-package)
- Infrastructure and build packages
- Developer tooling packages

Do not produce package-by-package deep docs until the user confirms the
target slice.

## Applying the Rubric Recursively

When decomposing a subsystem into sub-modules (depth 2+), apply the
same 2-of-6 criteria at each level. A sub-folder within a subsystem is
a sub-module only if it independently satisfies at least 2 criteria.

Large-but-uniform folders (many files, one pattern) should be documented
via a pattern entry in `patterns.md`, not decomposed into individual
sub-module docs.
