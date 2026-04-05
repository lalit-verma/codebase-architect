# Template: `agent-docs/agent-brief.md`

Target: under 100 lines. Optimize for file paths and signal density
over prose.

```markdown
# {Repo Name} Agent Brief

> Compact architecture context. For the minimal version, read
> `agent-context.md` instead. This file provides deeper detail.

## What This Repo Is

{2-4 sentences: what the repo does, archetype, key architectural shape.}

## Classification

| Field | Value |
|-------|-------|
| Archetype | {application/library/SDK/framework/monorepo/hybrid} |
| Primary language | {language} |
| Execution model | {model} |
| Scale | {size tier} |

## Architecture at a Glance

- Main entrypoints: `{paths}`
- Central subsystems: {names with paths}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most

| Subsystem | Why It Matters | Doc |
|-----------|----------------|-----|
| {name} | {1 sentence} | `subsystems/{name}.md` |

## Flows That Explain the System

| Flow | Why It Matters | Doc |
|------|----------------|-----|
| {flow} | {1 sentence} | `{doc path}` |

## Key Decisions

- {decision with short rationale} (see `decisions.md`)
- {decision with short rationale}
- {decision with short rationale}

## Known Uncertainties

- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}

## Reading Path for an Agent

1. Start with `agent-context.md` (if not already loaded)
2. Read `system-overview.md` for full architecture
3. Read the subsystem doc most relevant to your task
4. Read `patterns.md` before creating new files
5. Read `decisions.md` before proposing architectural changes
6. Check `uncertainties.md` before making risky assumptions
```
