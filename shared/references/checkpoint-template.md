# Checkpoint Template

Use this exact structure for the mandatory chat checkpoint before any
durable docs are written in `agent-docs/`.

---

## 1. Repository Classification

| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|
| Repo archetype | `{application/library/SDK/framework/monorepo/hybrid}` | `{high/medium/low}` | `{files/markers}` |
| Primary language | `{language}` | `{high/medium/low}` | `{files/markers}` |
| Execution model | `{CLI/server/worker/library/plugin/build/mixed}` | `{high/medium/low}` | `{files/markers}` |
| Scale | `{small/medium/large/very large}` | `{high/medium/low}` | `{counts/layout}` |

## 2. Working Understanding of Repo Purpose

- `Confirmed:` {facts directly supported by code or docs}
- `Inference:` {best current understanding of what the repo does}
- `UNCERTAIN:` {what is still unclear}

## 3. Candidate Subsystems

| Subsystem | Path | Role Tag | Responsibility | Evidence Anchors | Dependencies | Confidence | Recursion? |
|-----------|------|----------|----------------|------------------|--------------|------------|------------|
| `{name}` | `{path}` | `{tag}` | `{1-2 sentences}` | `{2-5 file refs}` | `{names}` | `{high/med/low}` | `{yes/no}` |

Rules:
- Order from most central to least central
- Include only real architectural units (apply subsystem mapping rubric)
- Mark generated or shared noise separately
- Recursion? = yes if 50+ files or 3+ internal modules with own contracts

## 4. Candidate Flows Worth Documenting

| Flow | Trigger | Main Handoffs | Why It Matters | Confidence |
|------|---------|---------------|----------------|------------|
| `{name}` | `{trigger}` | `{A -> B -> C}` | `{architectural reason}` | `{high/med/low}` |

## 5. Preliminary Patterns Detected

| Pattern | Category | Example File | File Count | Subsystem |
|---------|----------|--------------|------------|-----------|
| `{name}` | `{endpoint/handler/service/test/adapter/config}` | `{cleanest instance}` | `{N files}` | `{subsystem}` |

These are preliminary observations. Full detection happens during Phase 2
deep dives. Final confirmation by user happens in Phase 3.

## 6. Coverage Notes

- What was read fully
- What was sampled (and why)
- What was intentionally skipped
- What appears generated or mechanically repetitive

## 7. Open Questions

- `NEEDS CLARIFICATION:` {question}
- `NEEDS CLARIFICATION:` {question}

Ask only questions that materially affect subsystem boundaries, repo
purpose, or documentation scope.

## 8. Proposed Documentation Plan

If the user approves writing, propose exactly what will be created:

- `agent-docs/agent-context.md` (primary deliverable)
- `agent-docs/patterns.md`
- `agent-docs/agent-brief.md`
- `agent-docs/agent-protocol.md`
- `agent-docs/system-overview.md`
- `agent-docs/index.md`
- `agent-docs/subsystems/{list}.md`
- `agent-docs/flows/{list}.md` (if warranted)
- `agent-docs/decisions.md`
- `agent-docs/glossary.md`
- `agent-docs/uncertainties.md`

Also state:
- Write scope (whole repo / specific slice)
- Expected citation density
- Unresolved limitations that will remain
- Subsystems flagged for recursive decomposition

## 8b. Scope Selection (monorepos and very large repos only)

If this is a monorepo, hybrid, very large (2000+ files), or has 10+
candidate subsystems, present a scope selection table:

> **Scope Selection — which areas should Phase 2 deep-dive?**
>
> | # | Package / App | Path | Est. Files | Centrality | Recommended |
> |---|---------------|------|------------|------------|-------------|
> | 1 | `{name}` | `{path}` | ~{N} | `{core/supporting/peripheral}` | `{yes/no}` |
>
> Centrality: **core** (central to primary function), **supporting**
> (used by core, not main surface), **peripheral** (optional, tooling).
>
> **Tell me which numbers to include in Phase 2 scope.** You can
> expand scope later by re-running Phase 1.

Skip this section for small/medium repos where all subsystems will be
analyzed.

## 9. Required Closing Question

End with a direct confirmation request:

> **Does this subsystem map and scope look right? Should I proceed to
> write `agent-docs/system-overview.md` and save the analysis state?**

Do NOT write any files until the user confirms.
