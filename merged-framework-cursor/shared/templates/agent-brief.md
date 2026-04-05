# Template: `agent-docs/agent-brief.md`

This is the single most important file for coding agent performance.
An agent should read this FIRST before any coding task.

```markdown
# {Repo Name} — Agent Brief

> Load this file before starting any coding task in this repository.
> Then load the specific subsystem doc relevant to your task.

## What This Repo Is

{2-4 sentences: what the repo does, its archetype, and the key
architectural shape. Be concrete, not vague.}

## Classification

| Field | Value |
|-------|-------|
| Archetype | {application/library/SDK/framework/monorepo/hybrid} |
| Primary language | {language} |
| Execution model | {model} |
| Scale | {size tier} |

## Architecture at a Glance

- Main entrypoints: `{paths}`
- Central subsystems: {names}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Config sources: {files/env/flags}

## Subsystems That Matter Most

| Subsystem | Why It Matters | Read Next |
|-----------|----------------|-----------|
| {name} | {1 sentence} | `subsystems/{name}.md` |

## Flows That Explain the System

| Flow | Why It Matters | Read Next |
|------|----------------|-----------|
| {flow} | {1 sentence} | `flows/{name}.md` or `system-overview.md` |

## Top Patterns to Follow

The most important code conventions in this repo. Full details in
`patterns.md`; per-subsystem specifics in each subsystem doc.

| Pattern | Scope | Example |
|---------|-------|---------|
| {convention} | {system-wide / specific subsystem} | `{file}` |

## Common Change Playbooks

Quick guides for the most frequent types of changes. Each refers to
the subsystem doc with the full modification guide.

### Adding a new {endpoint/handler/command/etc.}

1. {step — which file to create, pattern to follow}
2. {step — where to register}
3. {step — test file and pattern}
4. See: `subsystems/{name}.md` → Modification Guide

### Adding a new {provider/adapter/plugin/etc.}

1. {step}
2. {step}
3. See: `subsystems/{name}.md` → Modification Guide

## Key Decisions

- {decision with short rationale}
- {decision with short rationale}
- Full analysis: `decisions.md`

## Known Uncertainties

- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}
- Full list: `uncertainties.md`

## Reading Path for a Coding Agent

1. **You are here** — `agent-brief.md`
2. Read `system-overview.md` for full architecture
3. Read the subsystem doc most relevant to your task
4. Read `patterns.md` before writing new code
5. Read `decisions.md` before proposing structural changes
6. Check `uncertainties.md` for assumptions near your change area
```
