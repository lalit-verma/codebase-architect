# Scope Selection Rules

For monorepos and very large repos, Phase 1 must present a structured
scope selection after the checkpoint and before asking for write
confirmation. This prevents wasted deep-dive effort on areas the user
does not care about.

## When to Present Scope Selection

Present when ANY of these conditions hold:

- Repo archetype is "monorepo" or "hybrid"
- Scale is "very large" (2000+ source files)
- 10+ candidate subsystems identified in the checkpoint
- Multiple distinct apps or services detected

Skip for small and medium repos where all subsystems will be analyzed.

## Scope Selection Table

Present this table in chat after the checkpoint, before the closing
confirmation question:

> **Scope Selection — which areas should Phase 2 deep-dive?**
>
> | # | Package / App | Path | Est. Files | Centrality | Recommended |
> |---|---------------|------|------------|------------|-------------|
> | 1 | {name} | `{path}` | ~{N} | core | yes |
> | 2 | {name} | `{path}` | ~{N} | supporting | yes |
> | 3 | {name} | `{path}` | ~{N} | peripheral | no |
>
> **Centrality categories:**
> - **core** — central to the system's primary function
> - **supporting** — used by core subsystems, not the main product
>   surface
> - **peripheral** — optional, tooling, or rarely changed
>
> Recommended = "yes" for core and supporting subsystems. "no" for
> peripheral unless the user requests it.
>
> **Tell me which numbers to include in the deep-dive scope.**
> You can expand scope later by re-running Phase 1.

## State Tracking

Add these fields to `.analysis-state.md` YAML frontmatter when scope
selection is presented:

```yaml
selected_scope:
  - {subsystem-name}
  - {subsystem-name}
scope_selection_presented: true
```

If scope selection was not needed (small/medium repo), omit these
fields entirely. Their absence means "analyze all subsystems."

## Phase 2 Behavior

When `selected_scope` is present in `.analysis-state.md`:
- Only deep-dive subsystems listed in `selected_scope`
- If the user requests a subsystem NOT in `selected_scope`, warn:
  > **{name} is not in the selected scope.** Selected: {list}.
  > To add it, re-run Phase 1 to update scope, or say "analyze
  > anyway" to proceed with this subsystem.
- In the "Remaining subsystems" report, show unselected subsystems
  separately: "(not in selected scope — re-run Phase 1 to expand)"

When `selected_scope` is NOT present:
- Deep-dive all subsystems in `subsystems_pending` (default behavior
  for small/medium repos)

## Expanding Scope

To add more subsystems after initial scope selection:
1. Re-run Phase 1 (it reads existing state and augments)
2. The scope selection table is re-presented showing current state
   (which subsystems are already completed, which are pending, which
   were not selected)
3. User selects additional subsystems
4. `selected_scope` is updated to include the new selections
5. Previously completed subsystems are not re-analyzed
