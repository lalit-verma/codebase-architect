# Template: `docs/agent-brief.md`

```markdown
# {Repo Name} Agent Brief

## Mission

{2-4 sentences describing what this repository is for and what a later
agent should assume about its architectural shape.}

## Repo Classification

| Field | Value |
|-------|-------|
| Archetype | {application/library/SDK/framework/monorepo/hybrid} |
| Primary language | {language} |
| Execution model | {model} |
| Scale | {size tier} |

## Architecture In One View

- Main entrypoints: {paths}
- Central subsystems: {names}
- Core flows: {names}
- State boundaries: {stores or "mostly stateless"}
- Configuration sources: {files/env/flags}

## Subsystems That Matter Most

| Subsystem | Why It Matters | Read Next |
|-----------|----------------|----------|
| {name} | {1 sentence} | `{doc path}` |

## Flows That Explain The System Fastest

| Flow | Why It Matters | Read Next |
|------|----------------|----------|
| {flow} | {1 sentence} | `{doc path}` |

## Most Important Decisions

- {decision with short rationale}
- {decision with short rationale}
- {decision with short rationale}

## Known Uncertainties

- `UNCERTAIN:` {item}
- `NEEDS CLARIFICATION:` {item}

## Suggested Reading Path For A Future Agent

1. Read `system-overview.md`
2. Read the most relevant subsystem doc
3. Read the flow doc that touches that subsystem
4. Read `decisions.md` before proposing changes
5. Check `uncertainties.md` for unresolved assumptions
```
