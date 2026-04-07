# Template: `agent-docs/agent-context-nano.md`

This is the **inlined nano-digest**. Generated in Phase 3 alongside
`agent-context.md`. Its purpose is to be pasted directly into
`CLAUDE.md` / `AGENTS.md` / `.cursorrules` so that the most-needed
codebase context lives in the agent's system prompt, paid for once,
without triggering tool-call reads or accumulating context across the
session.

**Hard ceiling: 40 lines.** Target: 25–35.

**Forbidden inside this file:** any reference to `agent-docs/` paths
(`agent-docs/patterns.md`, `agent-docs/subsystems/`, etc.). The whole
point of the nano-digest is that the main thread should never need to
read deeper docs to do common tasks. Pointers to deeper docs are
generated separately as the Explore-enrichment block.

```markdown
# {Repo Name} — Quick Context

> Inlined nano-context for coding agents.
> Generated: {YYYY-MM-DD} | v1 | {short_sha}

## What this is
{1-2 sentences: what the repo does, primary language, execution model.}

## Where things live
- `{path}/` — {purpose}
- `{path}/` — {purpose}
- `{path}/` — {purpose}
- `{path}/` — {purpose}
- `{path}/` — {purpose}
{5-8 entries — only the most navigation-critical paths}

## How to add a new {most common thing}
1. Create `{path}` following `{example file}`
2. {step with concrete file reference}
3. Register in `{file:line}`
4. Test at `{test path}` following `{test example}`

## How to add a new {second most common thing}
1. Create `{path}` following `{example file}`
2. {step with concrete file reference}
3. Register in `{file:line}`
4. Test at `{test path}` following `{test example}`

## Do NOT
- {anti-pattern} — {1-line reason}
- {anti-pattern} — {1-line reason}
- {anti-pattern} — {1-line reason}
{2-3 entries — only the highest-impact gotchas}
```

## Sourcing rules

When generating, pull from existing Phase 3 outputs (do not re-explore):

- **What this is** — first 1-2 sentences of `agent-context.md`'s "What this repo is"
- **Where things live** — top 5-8 entries of `agent-context.md`'s "Architecture map", chosen by navigation centrality (entrypoints, primary subsystems, registration points)
- **How to add patterns** — the 2 patterns from `agent-context.md`'s "Key patterns" with the highest file count (most common)
- **Do NOT** — the 2-3 entries from `agent-context.md`'s "Do NOT" with the highest blast radius (boundary violations, deprecated patterns, generated-file edits)

The nano-digest is a strict subset of `agent-context.md` content. Do not
introduce any fact in the nano that is not also in `agent-context.md`.
