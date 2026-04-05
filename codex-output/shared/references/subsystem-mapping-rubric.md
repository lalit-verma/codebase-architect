# Subsystem Mapping Rubric

Use this rubric to decide what counts as a subsystem and to keep the
checkpoint structurally consistent.

## What Counts As A Subsystem

A subsystem is a meaningful architectural unit, not merely a folder.
It should satisfy at least two of these:

- owns a clear responsibility
- exposes an entrypoint, contract, or API
- coordinates other modules
- encapsulates a state boundary
- has a distinct dependency pattern
- is referenced across multiple parts of the system as a unit

Examples:

- request handling layer
- provider abstraction layer
- storage/repository layer
- plugin registry
- build graph package in a monorepo

Non-examples unless they are unusually central:

- generic utility folders
- test helpers
- DTO-only folders with no meaningful behavior
- generated code directories

## How To Split Or Merge

Split when:

- a directory contains multiple distinct responsibilities
- one area has a public contract and another is pure implementation
- one area has a different runtime role, such as CLI versus worker
- one area has materially different dependencies or ownership

Merge when:

- two packages act as one conceptual unit with trivial separation
- one folder is just types/constants/helpers for another subsystem
- splitting would produce documentation noise rather than insight

## Naming Guidance

Prefer names based on responsibility, not folder spelling alone.

Good:

- "API request layer"
- "workspace graph loader"
- "provider adapter layer"

Weak:

- "utils"
- "common"
- "lib"

If a folder name is all you have, mark the label as tentative.

## Classification Tags

Tag each subsystem with one primary role:

- `entrypoint`
- `orchestration`
- `domain/core`
- `integration`
- `storage`
- `configuration`
- `tooling/build`
- `ui/presentation`
- `shared`
- `generated`

This helps later docs stay consistent.

## Confidence Rules

Use:

- `high` when the responsibility and boundaries are clearly evidenced
- `medium` when the responsibility is likely but some edges are fuzzy
- `low` when the unit is provisional or inferred from directory shape

Low-confidence subsystems should trigger clarification before durable
docs are written.

## Minimum Evidence For Each Subsystem Entry

Every subsystem in the checkpoint should include:

- name
- path or package scope
- primary role tag
- short responsibility statement
- 2-5 evidence anchors
- key dependencies
- confidence level

If you cannot supply evidence anchors, the subsystem is not ready to be
documented as a durable unit.

## Monorepo-Specific Guidance

On the first pass, treat these as likely top-level subsystem classes:

- apps/services
- shared packages
- infrastructure/build packages
- developer tooling packages

Do not produce package-by-package deep docs until the user confirms the
target slice.
