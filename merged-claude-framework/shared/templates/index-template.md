# Template: `agent-docs/index.md`

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture documentation. Review uncertain sections
> before relying as ground truth. Generated on {date}.

## What This Repo Is

{1 paragraph: what the repository is, its runtime shape, and the scope
these docs cover.}

## Documentation Scope

- Coverage: {whole repo / top-level monorepo architecture / specific slice}
- Evidence quality: {high/medium/mixed} with brief reason
- Generated on: {date}

## Recommended Reading Order

1. **Coding agents:** Load `agent-context.md` at session start (primary).
2. `agent-brief.md` — compact architecture map.
3. `system-overview.md` — full system shape.
4. Subsystem docs relevant to your task.
5. `patterns.md` — code patterns and conventions to follow.
6. `decisions.md` — key trade-offs to respect.
7. `uncertainties.md` — check before making risky assumptions.

## Subsystem Inventory

| Subsystem | Role | Why It Exists | Confidence | Doc |
|-----------|------|---------------|------------|-----|
| {name} | {tag} | {1 sentence} | {level} | `subsystems/{name}.md` |

## Flow Inventory

| Flow | Trigger | Handoffs | Why Read It | Doc |
|------|---------|----------|-------------|-----|
| {flow} | {trigger} | {A -> B -> C} | {1 sentence} | {doc path or "see system-overview.md"} |

## Quick Links

- `agent-context.md` — primary context file for coding agents
- `patterns.md` — code patterns and conventions
- `agent-brief.md` — compact architecture for agents
- `system-overview.md` — top-level architecture
- `decisions.md` — architectural trade-offs
- `glossary.md` — project-specific terms
- `uncertainties.md` — unresolved questions

## Confidence Summary

- High confidence: {areas}
- Medium confidence: {areas}
- `UNCERTAIN:` {areas that need care}
```
