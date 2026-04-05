# Template: `agent-docs/agent-context.md`

This is the PRIMARY output of the entire analysis. Keep under 120 lines.
No prose. No tables. Every line must be actionable for a coding agent.

```markdown
# {Repo Name} — Agent Context

> Load this file at session start for full codebase context.
> Generated: {YYYY-MM-DD HH:MM UTC} | v1 | {short_sha}

## What this repo is
{2-3 sentences: what it does, archetype, language, execution model.}

## Architecture map
- `{path}/` — {one-line purpose}
- `{path}/` — {one-line purpose}
- `{path}/` — {one-line purpose}
- `{path}/` — {one-line purpose}
- `{path}/` — {one-line purpose}

## Key patterns

### To add a new {thing}
1. Create `{path}` following `{example file}`
2. {step with file reference}
3. Register in `{file:line}`
4. Add test at `{test path}` following `{test example}`

### To add a new {thing}
1. {step}
2. {step}

## Conventions
- {convention} (see `{file}`)
- {convention} (see `{file}`)
- {convention} (see `{file}`)

## Do NOT
- {anti-pattern} — {reason}
- {anti-pattern} — {reason}
- {anti-pattern} — {reason}

## Key contracts
- `{file:line}` — {what it defines, who implements it}
- `{file:line}` — {what it defines, who implements it}

## For deeper context
- `agent-docs/routing-map.md` — structured task-to-doc lookup (machine-readable)
- `agent-docs/agent-brief.md` — full architecture overview
- `agent-docs/patterns.md` — all detected code patterns with recipes
- `agent-docs/subsystems/{name}.md` — {when to read}
- `agent-docs/decisions.md` — architectural trade-offs to respect
- `agent-docs/uncertainties.md` — known gaps, check before assuming
```
