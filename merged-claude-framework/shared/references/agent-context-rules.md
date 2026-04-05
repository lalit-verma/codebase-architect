# Agent Context Generation Rules

`agent-docs/agent-context.md` is the primary deliverable of the entire
analysis. It is the file a coding agent loads at session start to gain
deep codebase understanding. Every decision in this file should optimize
for: "does this help an agent write better code?"

## Hard Constraints

- Under 120 lines total. Every line must earn its place.
- Every line must be actionable — no prose, no explanations, no history.
- Use concrete file paths, not abstract subsystem names.
- Use flat markdown: `##` headings, `- ` bullets, `` `code refs` ``.
- Do NOT use tables. They waste tokens for agent consumption.
- Do NOT use confidence labels (`Confirmed:`, `Inference:`, etc.). This
  file contains assertions, not analysis. Uncertainty belongs in
  `agent-docs/uncertainties.md`.
- The file must be standalone: an agent reading ONLY this file should
  know where everything is and what patterns to follow.
- Regenerate entirely on re-runs. Stale context is worse than no context.

## Required Sections (in this order)

### `## What this repo is`
2-3 sentences maximum. Cover:
- What the repo does (not its history or motivation)
- Archetype (application, library, framework, etc.)
- Primary language and execution model

### `## Architecture map`
Flat bullet list of key paths with one-line purpose. Format:
```
- `path/` — purpose
```
Include only paths an agent would actually need to navigate to.
Typically 8-20 entries. Order by importance, not alphabetically.

### `## Key patterns`
For each detected pattern, provide a recipe. Format:
```
### To add a new {thing}
1. Create `{path}` following `{example file}`
2. Register in `{registration file}`
3. Add tests in `{test path}`
```
Include only patterns with 3+ instances in the codebase.
Typically 2-6 patterns.

### `## Conventions`
Bullet list of project-specific rules with file references. Format:
```
- {convention} (see `{file}`)
```
Focus on: naming conventions, dependency injection approach, error
handling style, test structure, import organization.
Typically 4-10 entries.

### `## Do NOT`
Bullet list of anti-patterns specific to THIS codebase. Format:
```
- {what not to do} — {why}
```
Focus on: generated files not to edit, boundary violations, deprecated
patterns, architectural constraints.
Typically 3-8 entries.

### `## Key contracts`
Important interfaces, types, or abstractions an agent must know. Format:
```
- `{file:line}` — {what it defines, who implements it}
```
Include only contracts that are central to the architecture.
Typically 3-8 entries.

### `## For deeper context`
Pointers to other `agent-docs/` files for on-demand loading. Format:
```
- `agent-docs/{file}` — {when to read it}
```
Always include: agent-brief.md, patterns.md, decisions.md,
uncertainties.md, and the most important subsystem docs.

## Content Sourcing

When generating `agent-context.md` during Phase 3:

| Section | Source |
|---------|--------|
| What this repo is | `agent-docs/system-overview.md` purpose section |
| Architecture map | All subsystem docs — extract key paths |
| Key patterns | `agent-docs/patterns.md` (consolidated from Phase 2) |
| Conventions | Design decisions + observed consistency in deep dives |
| Do NOT | Edge cases, gotchas, and anti-patterns from subsystem docs |
| Key contracts | Contracts and types sections from subsystem docs |
| For deeper context | Fixed structure pointing to other agent-docs/ files |

## Platform Notes

The content of `agent-context.md` is identical regardless of which
agent platform reads it (Claude Code, Codex, Cursor). The only
difference is how it gets referenced:

- Claude Code: `CLAUDE.md` contains `Read agent-docs/agent-context.md
  at the start of every session for full codebase context.`
- Cursor: `.cursorrules` contains the same line.
- Codex: `AGENTS.md` contains the same line.

The user wires this reference manually after Phase 3 completes. Phase 3
reports the exact line to add.

## Quality Check

Before finalizing, verify:
- [ ] Under 120 lines?
- [ ] Every line contains a file path or actionable instruction?
- [ ] No architectural prose or explanations?
- [ ] No tables?
- [ ] No confidence labels?
- [ ] An agent reading only this file could navigate the repo?
- [ ] An agent reading only this file would follow correct patterns?
- [ ] An agent reading only this file would know what NOT to do?
