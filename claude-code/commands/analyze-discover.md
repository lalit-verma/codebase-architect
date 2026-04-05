You are running Phase 1 of a 3-phase codebase analysis workflow.
The primary goal is to produce documentation that helps coding agents
(Claude Code, Codex, Cursor) gain deep codebase context.

## Progress

| Phase | Status |
|-------|--------|
| **1. Discover & Map** | **<-- current** |
| 2. Deep Dive (per subsystem) | pending |
| 3. Synthesize | pending |

## User's Description

$ARGUMENTS

---

## Shared Resources

Look for shared reference files at `~/.claude/codebase-analysis/`.
If that directory exists, load these files on demand during analysis:
- `references/ecosystem-playbook.md` — language-specific exploration
- `references/scale-and-scope.md` — reading depth and stop conditions
- `references/subsystem-mapping-rubric.md` — subsystem identification
- `references/checkpoint-template.md` — checkpoint format
- `references/validation-rules.md` — self-check criteria
- `references/scope-selection-rules.md` — monorepo scope selection
- `examples/checkpoint-example.md` — quality calibration target

If the directory does not exist, use the inline fallback guidance
embedded in this command. The command is self-contained but works at
higher quality with the shared resources.

---

## Mission

Produce an architecture map of this repository. You are in read-only
learning mode. Your output will become durable documentation whose
primary consumer is a coding agent working in this codebase.

## Hard Constraints

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings in chat. Write files only after
  explicit user confirmation.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 references.
- **Factual only.** Label anything beyond direct evidence.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

---

## Procedure

Execute these steps in order. Do not skip steps.

### Step 1: Classify the Repository

Determine from evidence (manifests, file layout, entrypoints, README):

| Field | What to determine |
|-------|-------------------|
| Archetype | application, library, SDK, framework, monorepo, or hybrid |
| Primary language | and secondary languages if relevant |
| Execution model | CLI, server, worker, plugin host, library-only, build tool, or mixed |
| Scale | small (<150 files), medium (150-800), large (800-2000), very large (2000+) |

If `~/.claude/codebase-analysis/references/ecosystem-playbook.md`
exists, load it and follow the language-specific exploration commands.

**Inline fallback — ecosystem detection markers:**

| Marker File(s) | Ecosystem |
|---|---|
| `go.mod` | Go |
| `package.json` + `tsconfig.json` | TypeScript |
| `package.json` only | JavaScript |
| `Cargo.toml` | Rust |
| `pyproject.toml` or `setup.py` | Python |
| `pom.xml` or `build.gradle*` | Java / Kotlin |
| `*.csproj` or `*.sln` | C# / .NET |
| `Gemfile` | Ruby |
| `mix.exs` | Elixir |
| `composer.json` | PHP |
| `CMakeLists.txt` + `.c/.cpp` | C / C++ |
| `Package.swift` | Swift |

**Inline fallback — ecosystem exploration priorities:**

- **Go:** `go.mod`, `cmd/*/main.go`, interface definitions, `.proto`,
  `internal/` vs `pkg/`
- **TypeScript/JS:** `package.json`, `tsconfig.json`, monorepo markers,
  framework detection, `src/` structure
- **Python:** `pyproject.toml`, `__main__.py`/`app.py`/`manage.py`,
  framework detection, package boundaries
- **Rust:** `Cargo.toml`, workspace members, traits, async runtime,
  feature flags
- **Java/Kotlin:** `pom.xml`/`build.gradle*`, Spring annotations,
  module structure
- **C#/.NET:** `*.sln`/`*.csproj`, `Program.cs`/`Startup.cs`, DI
  registration

Generic fallback: count file types, find entry files, scan config.

### Step 2: Adaptive Questions

If the repo purpose, scope, or key boundaries are unclear from evidence
alone, ask 2-4 targeted questions. Themes:

- What the user believes the repo is for
- Whether they care about the whole repo or a specific slice
- Known hot areas or confusing subsystems
- Whether there are special concerns (performance-critical paths,
  security boundaries, etc.)

If the code makes the purpose and scope obvious, skip this step
entirely.

### Step 3: Evidence Scan

Inspect the repository in this priority order:

1. Manifests and workspace config
2. Entrypoints and bootstrapping code
3. Public contracts and exported APIs
4. Registries, routers, DI, or plugin wiring
5. Central orchestration modules
6. Configuration loading
7. Representative tests (to reveal intended behavior)
8. Existing docs, README, or architecture files

**Reading depth by scale** (load `scale-and-scope.md` if available):

- **Small:** Read all central files, most source files
- **Medium:** Read central files fully, sample repetitive leaves
- **Large:** Focus on entrypoints, contracts, registries, orchestration,
  config. Sample after pattern is established.
- **Very large / monorepo:** Map top-level architecture only. Ask which
  slice to deepen.

Always note what was read fully vs. sampled vs. skipped.

### Step 4: Map Subsystems

Identify real architectural subsystems. A folder is a subsystem only
if it satisfies **at least 2** of (load `subsystem-mapping-rubric.md`
if available):

- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Referenced across multiple parts of the system

**Not subsystems** (unless unusually central): generic utility folders,
test helpers, DTO-only folders, generated code directories.

Tag each subsystem:
`entrypoint` | `orchestration` | `domain/core` | `integration` |
`storage` | `configuration` | `tooling/build` | `ui/presentation` |
`shared` | `generated`

**Flag recursion candidates:** Mark subsystems with 50+ files or 3+
internal modules with own contracts. These will be proposed for
recursive decomposition during Phase 2.

**Repo-type focus:**
- **Applications:** entrypoints, flows, state, orchestration, config
- **Libraries/SDKs:** API surface, abstractions, extension points,
  error model, packaging
- **Frameworks:** lifecycle hooks, inversion points, plugin systems,
  conventions
- **Monorepos:** top-level architecture first, ask which slice to deepen

### Step 5: Detect Preliminary Patterns

While mapping, note file clusters that follow similar structures:
- 3+ files with similar naming in the same directory
- Registration points where multiple similar items are wired
- Test files that follow a consistent companion pattern

Record as preliminary observations. Full detection happens in Phase 2.

### Step 6: Present Checkpoint

Present findings in chat. If `checkpoint-template.md` is available,
use its exact structure. Otherwise use this format:

#### 1. Repository Classification
| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|

#### 2. Working Understanding
- `Confirmed:` / `Inference:` / `UNCERTAIN:`

#### 3. Candidate Subsystems
| Subsystem | Path | Role | Responsibility | Evidence Anchors | Dependencies | Confidence | Recursion? |
|-----------|------|------|----------------|------------------|--------------|------------|------------|

Order from most central to least central.

#### 4. Candidate Flows
| Flow | Trigger | Handoffs | Why It Matters | Confidence |
|------|---------|----------|----------------|------------|

#### 5. Preliminary Patterns Detected
| Pattern | Category | Example File | File Count | Subsystem |
|---------|----------|--------------|------------|-----------|

#### 6. Coverage Notes
- Read fully / sampled / skipped

#### 7. Open Questions
- `NEEDS CLARIFICATION:` {question}

#### 8. Proposed Documentation Plan
List exact files to generate in `agent-docs/`.

### Step 6b: Self-Validate Checkpoint

Before presenting to the user, verify your checkpoint output:

If `~/.claude/codebase-analysis/references/validation-rules.md` exists,
load it and run the Phase 1 checks. Otherwise use these inline checks:

1. Checkpoint has all 8 sections (Classification through Doc Plan)
2. Subsystem table has all required columns (Subsystem, Path, Role,
   Responsibility, Evidence Anchors, Dependencies, Confidence, Recursion)
3. Every subsystem row has >= 2 evidence anchors (concrete file paths)

If any check fails, fix the checkpoint content before presenting it.

### Step 6c: Scope Selection (monorepos and very large repos only)

If the repo is a monorepo, hybrid, very large (2000+ files), or has
10+ candidate subsystems, present a scope selection table after the
checkpoint:

> **Scope Selection — which areas should Phase 2 deep-dive?**
>
> | # | Package / App | Path | Est. Files | Centrality | Recommended |
> |---|---------------|------|------------|------------|-------------|
> | 1 | {name} | `{path}` | ~{N} | core/supporting/peripheral | yes/no |
>
> Centrality: **core** (central to primary function), **supporting**
> (used by core), **peripheral** (optional, tooling, rarely changed).
> Recommended = "yes" for core and supporting.
>
> **Tell me which numbers to include in the deep-dive scope.**
> You can expand scope later by re-running Phase 1.

Record the user's selection for inclusion in `.analysis-state.md`.
Skip this step for small/medium repos.

### Step 7: Ask for Confirmation

End the checkpoint with:

> **Does this subsystem map and scope look right? Should I proceed to
> write `agent-docs/system-overview.md` and save the analysis state?**

Do NOT write any files until the user confirms.

### Step 8: Write Files (after confirmation only)

**File 1: `agent-docs/.analysis-state.md`**

```markdown
---
phase_completed: 1
generated_on: {date}
output_root: agent-docs
subsystems_pending:
  - {subsystem-name}
  - {subsystem-name}
subsystems_completed: []
recursion_candidates:
  - {subsystem-name}
preliminary_patterns:
  - {pattern-name}: {category} ({example file})
selected_scope:          # only if scope selection was presented
  - {subsystem-name}
scope_selection_presented: true/false
---

{Full checkpoint content from Step 6}
```

**File 2: `agent-docs/system-overview.md`**

```markdown
# {Repo Name} System Overview

> Auto-generated. Review before relying as ground truth.
> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

## Purpose
{1 paragraph: what this system does, who interacts with it, why it
exists. Mark inference explicitly.}

## External Boundaries
| Actor / System | Interaction | Evidence |
|----------------|-------------|----------|

## Architectural Shape
{1 paragraph: layered? modular? event-driven? etc.}

## Major Subsystems
| Subsystem | Role | Key Files | Depends On | Confidence |
|-----------|------|-----------|------------|------------|

## Primary Flows
### {Flow Name}
- Trigger: {what starts it}
- Path: {A -> B -> C}
- Why it matters: {1-2 sentences}
- Evidence: {file paths}

## State and Configuration
- State boundaries: {stores, caches, or "stateless"}
- Config sources: {env/files/flags}
- Environment differences: {if known}

## Design Observations
- `Confirmed:` {facts}
- `Inference:` {trade-off or design rationale}
- `UNCERTAIN:` {what static analysis cannot confirm}
```

### Step 9: Report Next Steps

After writing, tell the user:

> **Phase 1 of 3 complete.**
>
> Created:
> - `agent-docs/system-overview.md`
> - `agent-docs/.analysis-state.md`
>
> **Next:** Run `/user:analyze-deep-dive {subsystem-name}` for each
> subsystem. Recommended order:
> 1. {subsystem} — {reason}
> 2. {subsystem} — {reason}
> 3. ...
>
> Subsystems flagged for recursive decomposition: {list}
>
> **After all deep dives:** Run `/user:analyze-synthesize`

---

## Re-run Behavior

If `agent-docs/.analysis-state.md` already exists:

1. Read it first
2. Compare current repo state against the recorded subsystem map
3. Flag new, removed, or changed subsystems
4. Update rather than overwrite — preserve existing confirmations
5. Update `agent-docs/system-overview.md` to reflect changes
6. Reset `subsystems_pending` for subsystems that changed significantly
