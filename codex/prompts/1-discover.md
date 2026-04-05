# Phase 1: Discover & Map

## Progress

| Phase | Status |
|-------|--------|
| **1. Discover & Map** | **<-- current** |
| 2. Deep Dive (per subsystem) | pending |
| 3. Synthesize | pending |

## User's Description

{USER_DESCRIPTION}

> Replace `{USER_DESCRIPTION}` above with 2-3 lines about what this
> repo does before pasting this prompt.

---

## Mission

Produce an architecture map of this repository. Read-only learning
mode. Output durable documentation whose primary consumer is a coding
agent (Claude Code, Codex, Cursor) working in this codebase.

## Constraints

- **Read-only.** Do not modify source code.
- **Chat-first.** Present findings for confirmation. Write to
  `agent-docs/` only after explicit approval.
- **Evidence-based.** Cite file paths. Moderate citation density.
- **Factual only.** Label anything beyond direct evidence.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` /
  `NEEDS CLARIFICATION:`

---

## Procedure

### 1. Classify the Repository

Determine from evidence (manifests, file layout, entrypoints, README):

- **Archetype:** application, library, SDK, framework, monorepo, hybrid
- **Primary language** (and secondary if relevant)
- **Execution model:** CLI, server, worker, plugin host, library-only,
  build tool, or mixed
- **Scale:** small (<150 files), medium (150-800), large (800-2000),
  very large (2000+)

### 2. Detect Ecosystem & Explore

Check for ecosystem markers:

| Marker | Ecosystem |
|--------|-----------|
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

Use ecosystem-appropriate exploration:
- **Go:** `go.mod`, `cmd/*/main.go`, interfaces, `.proto`, `internal/` vs `pkg/`
- **TypeScript/JS:** `package.json`, `tsconfig.json`, monorepo markers,
  framework detection, `src/` structure
- **Python:** `pyproject.toml`, `__main__.py`/`app.py`/`manage.py`,
  framework detection, package boundaries
- **Rust:** `Cargo.toml`, workspace, traits, async runtime, feature flags
- **Java/Kotlin:** `pom.xml`/`build.gradle*`, Spring annotations, modules
- **C#/.NET:** `*.sln`/`*.csproj`, `Program.cs`/`Startup.cs`, DI

### 3. Adaptive Questions (if needed)

If repo purpose, scope, or boundaries are unclear from evidence, ask
2-4 targeted questions about: purpose, scope, hot areas, special
concerns. Skip if evidence is sufficient.

### 4. Evidence Scan

Inspect in priority order:
1. Manifests and workspace config
2. Entrypoints and bootstrapping
3. Public contracts and exported APIs
4. Registries, routers, DI, or plugin wiring
5. Central orchestration modules
6. Configuration loading
7. Representative tests
8. Existing docs or README

Reading depth by scale:
- Small: read most source files
- Medium: central files fully, sample leaves
- Large: entrypoints, contracts, registries, orchestration, config
- Very large: top-level architecture only, ask which slice

### 5. Map Subsystems

A folder is a subsystem if it satisfies at least 2 of:
- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Referenced across multiple parts of the system

Tag each: `entrypoint` | `orchestration` | `domain/core` |
`integration` | `storage` | `configuration` | `tooling/build` |
`ui/presentation` | `shared` | `generated`

Flag recursion candidates: subsystems with 50+ files or 3+ internal
modules with own contracts.

### 6. Detect Preliminary Patterns

Note file clusters with 3+ similar files. Record: pattern name,
category, example file, file count, subsystem. Full detection in Phase 2.

### 7. Present Checkpoint

Present in chat:

#### 1. Repository Classification
| Field | Value | Confidence | Evidence |

#### 2. Working Understanding
- `Confirmed:` / `Inference:` / `UNCERTAIN:`

#### 3. Candidate Subsystems
| Subsystem | Path | Role | Responsibility | Evidence | Deps | Confidence | Recursion? |

#### 4. Candidate Flows
| Flow | Trigger | Handoffs | Why It Matters | Confidence |

#### 5. Preliminary Patterns
| Pattern | Category | Example File | Count | Subsystem |

#### 6. Coverage Notes
- Read fully / sampled / skipped

#### 7. Open Questions
- `NEEDS CLARIFICATION:` ...

#### 8. Proposed Documentation Plan
List exact files for `agent-docs/`.

### 7b. Self-Validate Checkpoint

Before presenting to the user, verify:

1. Checkpoint has all 8 sections (Classification through Doc Plan)
2. Subsystem table has all required columns (Subsystem, Path, Role,
   Responsibility, Evidence Anchors, Dependencies, Confidence, Recursion)
3. Every subsystem row has >= 2 evidence anchors (concrete file paths)

If any check fails, fix the checkpoint before presenting it.

### 7c. Scope Selection (monorepos and very large repos only)

If the repo is a monorepo, hybrid, very large (2000+ files), or has
10+ candidate subsystems, present after the checkpoint:

> **Scope Selection — which areas should Phase 2 deep-dive?**
>
> | # | Package / App | Path | Est. Files | Centrality | Recommended |
> |---|---------------|------|------------|------------|-------------|
> | 1 | {name} | `{path}` | ~{N} | core/supporting/peripheral | yes/no |
>
> **Tell me which numbers to include.** You can expand scope later.

Record user's selection for `.analysis-state.md`. Skip for small/medium.

### 8. Ask for Confirmation

> **Does this subsystem map and scope look right? Should I write
> `agent-docs/system-overview.md` and save the analysis state?**

### 9. Write Files (after confirmation)

**`agent-docs/.analysis-state.md`** — Full checkpoint plus:
- `phase_completed: 1`
- `generated_on: {date}`
- `output_root: agent-docs`
- `subsystems_pending: [list]`
- `subsystems_completed: []`
- `recursion_candidates: [list]`
- `preliminary_patterns: [list]`
- `selected_scope: [list]` (only if scope selection was presented)
- `scope_selection_presented: true/false`

**`agent-docs/system-overview.md`** — Purpose, boundaries, shape,
subsystems, flows, state/config, design observations.

### 10. Report Next Steps

> **Phase 1 of 3 complete.**
> Created: `agent-docs/system-overview.md`, `agent-docs/.analysis-state.md`
>
> **Next:** Paste the Phase 2 prompt (`2-deep-dive.md`) for each
> subsystem. Recommended order:
> 1. {subsystem} — {reason}
> 2. ...
>
> **After all deep dives:** Paste the Phase 3 prompt (`3-synthesize.md`).

---

## Re-run Behavior

If `agent-docs/.analysis-state.md` exists, read it first, compare
against current state, and augment rather than overwrite.
