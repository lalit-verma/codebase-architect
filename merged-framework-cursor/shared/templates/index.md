# Template: `agent-docs/index.md`

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture documentation. Review uncertain sections
> before relying as ground truth.

## What This Repo Is

{1 paragraph: what the repository is, its runtime shape, and the scope
these docs cover.}

## Documentation Scope

- Coverage: {whole repo / top-level monorepo architecture / specific app or package}
- Evidence quality: {high/medium/mixed} with brief reason
- Generated on: {date}

## Recommended Reading Order

1. Start with `agent-brief.md` for a compact architecture map.
2. Then `system-overview.md` for the full system shape.
3. Then subsystem docs relevant to your task.
4. Read `patterns.md` before writing new code.
5. Read `decisions.md` for key trade-offs.
6. Check `uncertainties.md` before making risky assumptions.

## Subsystem Inventory

| Subsystem | Role | Why It Exists | Confidence | Doc | Sub-Modules |
|-----------|------|---------------|------------|-----|-------------|
| {name} | {tag} | {1 sentence} | {level} | `{path}` | {list or "—"} |

## Flow Inventory

| Flow | Trigger | Main Handoffs | Why Read It | Doc |
|------|---------|---------------|-------------|-----|
| {flow} | {trigger} | {A -> B -> C} | {1 sentence} | `{path}` |

## Quick Links

- `agent-brief.md` — compact context for coding agents
- `agent-protocol.md` — instructions for loading these docs
- `system-overview.md` — top-level architecture
- `patterns.md` — code and test conventions
- `decisions.md` — key architectural trade-offs
- `glossary.md` — project-specific terms
- `uncertainties.md` — unresolved questions

## Confidence Summary

- High confidence: {areas}
- Medium confidence: {areas}
- `UNCERTAIN:` {areas that need care}
```
