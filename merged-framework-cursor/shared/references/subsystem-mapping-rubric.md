# Subsystem Mapping Rubric

Use this rubric to decide what counts as a subsystem, when to split or
merge, and when to trigger recursive decomposition into sub-modules.

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

## When To Recurse Into Sub-Modules

A subsystem should be flagged for recursive decomposition when:

- it contains **>60 source files**
- it has **>3 clearly distinct internal responsibilities** that could
  each stand as a coherent documentation unit
- during deep dive, the agent cannot produce a quality subsystem doc
  without splitting because the content is too internally diverse

### How To Propose The Split

During Phase 2 (Deep Dive), if a subsystem triggers decomposition:

1. List the proposed sub-modules with:
   - name (based on responsibility, not just folder name)
   - path within the subsystem
   - 1-sentence responsibility
   - key files
2. Explain how the sub-modules relate to each other.
3. Ask the user to confirm or adjust the split.
4. After confirmation, write:
   - a parent subsystem doc (overview, relationships, shared patterns)
   - a sub-module doc for each child

### Sub-Module Qualification

Sub-modules follow the same "at least 2 of 6" rule as subsystems, but
within the parent subsystem's scope. A sub-folder that is just helpers
or types for another sub-module should be merged, not documented
separately.

### Depth Limit

Maximum 3 levels: system overview → subsystem → sub-module.
Do not recurse further. If a sub-module still feels too large, note
it as a limitation and suggest a future focused analysis pass.

## Naming Guidance

Prefer names based on responsibility, not folder spelling alone.

Good:

- "API request layer"
- "workspace graph loader"
- "provider adapter layer"
- "auth middleware (sub-module of API layer)"

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

Use the same tags for sub-modules, prefixed with the parent name when
reporting (e.g., "API Layer → Auth Middleware [integration]").

## Confidence Rules

Use:

- `high` when the responsibility and boundaries are clearly evidenced
- `medium` when the responsibility is likely but some edges are fuzzy
- `low` when the unit is provisional or inferred from directory shape

Low-confidence subsystems should trigger clarification before durable
docs are written.

## Minimum Evidence For Each Entry

Every subsystem (or sub-module) in the checkpoint should include:

- name
- path or package scope
- primary role tag
- short responsibility statement
- 2-5 evidence anchors (file paths)
- key dependencies
- confidence level

If you cannot supply evidence anchors, the unit is not ready to be
documented as a durable entry.

## Monorepo-Specific Guidance

On the first pass, treat these as likely top-level subsystem classes:

- apps/services
- shared packages
- infrastructure/build packages
- developer tooling packages

Do not produce package-by-package deep docs until the user confirms the
target slice.
