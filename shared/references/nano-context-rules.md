# Nano-Context Generation Rules

`agent-docs/agent-context-nano.md` is the **inlined nano-digest** —
a 25-40 line subset of `agent-context.md` designed to be pasted
directly into `CLAUDE.md` / `AGENTS.md` / `.cursorrules` so it lives
in the agent's system prompt.

## Why it exists

Benchmark data showed that loading `agent-context.md` (and its deeper
companions) into the main thread via tool-call reads triggered
long-context fallback to larger models, inflating cost without a
corresponding quality gain. Pushing reads into a subagent fixed cost
but lost the pattern fidelity that the main-thread writer needed.

The nano-digest threads the needle: it lives in the system prompt
(no Read calls, no accumulation, no fallback trigger) and contains
just enough pattern content to handle the common case without
delegating to a subagent.

## Hard Constraints

- **40 lines maximum.** Target 25-35.
- **~1.5-2.5K tokens.** Stays well under any context-window threshold.
- **Strict subset of `agent-context.md`.** Do not introduce facts
  that are not already in `agent-context.md`. The nano is a
  prioritized excerpt, not a separate analysis.
- **No `agent-docs/` references.** Not in the architecture map, not
  in the patterns, not in the Do NOT section, not anywhere. The
  point of the nano is that the main thread does not need to read
  deeper docs for common tasks. Any path reference invites a Read
  and re-introduces the long-context fallback path.
- **No "For deeper context" pointer section.** Pointers to deeper
  docs are generated separately as the Explore-enrichment block in
  `agent-protocol.md` and live outside the inlined nano block in
  the user's agent config.
- **No tables.** Same reason as `agent-context.md`.
- **No confidence labels.**
- **Regenerated entirely on re-runs.**

## Required Sections (in this order)

### `## What this is`
1-2 sentences. Sourced verbatim from `agent-context.md`'s "What this
repo is" section, trimmed to first 1-2 sentences if longer.

### `## Where things live`
5-8 path bullets. Format: `` - `path/` — purpose ``.

Selection rule: navigation centrality, not exhaustive coverage.
Include the entrypoints, the primary subsystem roots, and the
registration points an agent will need to find for the most common
tasks. **Skip** generated-code paths, build configs, and
documentation paths unless they are critical to navigation.

If `agent-context.md` has 15+ entries in its Architecture map, take
the top 5-8 by importance. The nano is meant to be the fast path,
not the full map.

### `## How to add a new {thing}` (×2)
Exactly 2 patterns. Format: numbered steps with file paths, identical
to the `agent-context.md` pattern format.

Selection rule: pick the 2 patterns from `agent-context.md`'s "Key
patterns" with the highest file count (most-used in the codebase).
These are the patterns the writer is most likely to need to follow.

If `agent-context.md` has fewer than 2 patterns, include only what
exists. Do not invent patterns.

### `## Do NOT`
2-3 anti-patterns. Format: `` - {what not to do} — {1-line reason} ``.

Selection rule: pick the 2-3 entries from `agent-context.md`'s "Do
NOT" with the highest blast radius. Examples of high blast radius:
- Editing generated files (causes silent regressions)
- Crossing architectural boundaries
- Bypassing the main registration point
- Using a deprecated pattern that still compiles

Skip lower-impact gotchas (style preferences, minor naming
conventions). Those live in `agent-context.md`'s full list.

## What is excluded (and why)

| Section | Excluded because |
|---|---|
| Full Architecture map (8-20 entries) | Top 5-8 are enough for navigation; the rest are accessible via Explore subagent if needed |
| Conventions list | Lower-impact than patterns; included in full `agent-context.md` |
| Key contracts (file:line refs) | Too granular for system-prompt economy; the writer can find these via Explore when actually working on contracts |
| "For deeper context" pointers | Would invite Reads from main thread, defeating the entire purpose |
| All `UNCERTAIN:` notes | Belong in `uncertainties.md`, not in the system prompt |

## Quality Check

Before finalizing the nano-digest, verify:

- [ ] Under 40 lines total?
- [ ] Every fact also present in `agent-context.md`?
- [ ] Zero references to `agent-docs/`?
- [ ] Zero tables?
- [ ] Zero confidence labels?
- [ ] All 5 sections present (What this is, Where things live, 2 patterns, Do NOT)?
- [ ] Each pattern has 3+ numbered steps with file paths?
- [ ] Each Do NOT entry has a 1-line reason?
- [ ] Reading only this digest, can you answer "where do I add a new {most common thing}"?

If a check fails, fix before proceeding to wiring instructions.
