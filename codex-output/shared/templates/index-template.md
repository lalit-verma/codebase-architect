# Template: `docs/index.md`

```markdown
# {Repo Name} Documentation Index

> Auto-generated architecture map. Review uncertain sections before
> relying on this as ground truth.

## What This Repo Is

{1 short paragraph describing the repository, its runtime shape, and
the scope covered by these docs.}

## Documentation Scope

- Coverage: {whole repo | top-level monorepo architecture | specific app/package}
- Evidence quality: {high/medium/mixed} with brief reason
- Generated on: {date}

## Recommended Reading Order

1. Start with `agent-brief.md` for a compact architecture map.
2. Then read `system-overview.md` for the top-level system shape.
3. Then read the subsystem and flow docs relevant to your task.
4. Read `decisions.md` for the most important trade-offs.
5. Read `uncertainties.md` before making risky assumptions.

## Subsystem Inventory

| Subsystem | Role | Why It Exists | Confidence | Doc |
|-----------|------|---------------|------------|-----|
| {name} | {tag} | {1 sentence} | {level} | `{path}` |

## Flow Inventory

| Flow | Trigger | Main Handoffs | Why Read It | Doc |
|------|---------|---------------|-------------|-----|
| {flow} | {trigger} | {A -> B -> C} | {1 sentence} | `{path}` |

## Quick Links

- `agent-brief.md`
- `system-overview.md`
- `decisions.md`
- `glossary.md`
- `uncertainties.md`

## Confidence Summary

- High confidence: {areas}
- Medium confidence: {areas}
- `UNCERTAIN:` {areas that need care}
```
