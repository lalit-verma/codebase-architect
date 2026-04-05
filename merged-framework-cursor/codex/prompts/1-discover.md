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
mode. Output durable documentation that coding agents (Cursor, Claude
Code, Codex) consume to gain deep context before writing code. Agent
understanding is the primary goal; human readability is secondary.

## Constraints

- **Read-only.** Do not modify source code.
- **Chat-first.** Present findings for confirmation. Write files only after explicit approval.
- **Evidence-based.** Cite file paths. Use moderate citation density.
- **Factual only.** Label anything beyond direct evidence.
- Labels: `Confirmed:` / `Inference:` / `UNCERTAIN:` / `NEEDS CLARIFICATION:`

## Anti-Patterns

- Do not generate polished docs before the subsystem map is confirmed
- Do not confuse directory structure with architectural boundaries
- Do not claim runtime behavior without static evidence
- Do not document monorepos package-by-package on first pass
- Do not ask lengthy questionnaires when a few questions would do

---

## Procedure

### 1. Classify the Repository

Determine from evidence (manifests, file layout, entrypoints, README):

- **Archetype:** application, library, SDK, framework, monorepo, or hybrid
- **Primary language** (and secondary if relevant)
- **Execution model:** CLI, server, worker, plugin host, library-only, build tool, or mixed
- **Scale:** small (<150 files), medium (150-800), large (800-2000), very large (2000+)

### 2. Detect Ecosystem & Explore

Check repo root for ecosystem markers:

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
| `CMakeLists.txt` + `.c/.cpp` | C / C++ |

Use ecosystem-appropriate commands to explore:

- **Go:** `go.mod`, `cmd/*/main.go`, interfaces, `.proto`, `internal/` vs `pkg/`
- **TypeScript/JS:** `package.json`, `tsconfig.json`, monorepo markers, framework detection, `src/`
- **Python:** `pyproject.toml`, `__main__.py`/`app.py`/`manage.py`, framework detection, package boundaries
- **Rust:** `Cargo.toml`, workspace members, traits, async runtime, feature flags
- **Java/Kotlin:** `pom.xml`/`build.gradle*`, Spring annotations, module structure
- **C#/.NET:** `*.sln`/`*.csproj`, `Program.cs`/`Startup.cs`, DI registration

Generic fallback: count file types by extension, find entry files, scan config.

### 3. Evidence Scan

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
- Very large: top-level architecture only, ask which slice to deepen

### 4. Detect System-Wide Patterns

While scanning, observe and record:

- Naming conventions (files, functions, types, constants)
- File organization patterns
- Error handling style
- Test structure and conventions
- Common abstractions and recurring patterns

### 5. Map Subsystems

A folder is a subsystem if it satisfies at least 2 of:
- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Referenced across multiple parts of the system

Tag each: `entrypoint` | `orchestration` | `domain/core` | `integration` | `storage` | `configuration` | `tooling/build` | `ui/presentation` | `shared` | `generated`

**Flag for recursive decomposition** any subsystem with >60 files or
>3 distinct internal responsibilities.

### 6. Present Checkpoint

Present in chat using this exact structure:

#### 1. Repository Classification
| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|

#### 2. Working Understanding
- `Confirmed:` / `Inference:` / `UNCERTAIN:` items

#### 3. Candidate Subsystems
| Subsystem | Path | Role | Responsibility | Key Files | Dependencies | Confidence | Decomposition |
|-----------|------|------|----------------|-----------|--------------|------------|---------------|

#### 4. Candidate Flows Worth Documenting
| Flow | Trigger | Handoffs | Why It Matters | Confidence |
|------|---------|----------|----------------|------------|

#### 5. System-Wide Patterns Observed
| Pattern | Where Seen | Example File |
|---------|-----------|--------------|

#### 6. Coverage Notes
- Read fully / sampled / skipped

#### 7. Open Questions
- `NEEDS CLARIFICATION:` {question}

#### 8. Proposed Documentation Plan
List exact files to generate in `agent-docs/`.

### 7. Ask for Confirmation

End with:

> **Does this subsystem map and scope look right? Should I write `agent-docs/system-overview.md` and save the analysis state?**

### 8. Write Files (after confirmation)

**`agent-docs/.analysis-state.md`** — Full checkpoint plus YAML metadata:

```yaml
---
phase_completed: 1
generated_on: {date}
subsystems_pending_deep_dive:
  - {subsystem-name}
subsystems_completed: []
subsystems_flagged_for_decomposition:
  - {subsystem-name}: {reason}
system_patterns:
  - {pattern}: {description}
---
```

Followed by the full checkpoint content.

**`agent-docs/system-overview.md`** — Structure:
- Purpose (1 paragraph)
- External boundaries table
- Architectural shape (1 paragraph)
- Major subsystems table (with Has Sub-Modules column)
- Primary flows (3-5 most important)
- State and configuration
- Patterns at a glance
- Design observations with evidence labels

### 9. Report Next Steps

> **Phase 1 of 3 complete.**
> Created: `agent-docs/system-overview.md`, `agent-docs/.analysis-state.md`
>
> **Next:** Paste the Phase 2 prompt (`2-deep-dive.md`) for each subsystem.
> Recommended order:
> 1. {subsystem} - {reason}
> 2. ...
>
> **After all deep dives:** Paste the Phase 3 prompt (`3-synthesize.md`).

---

## Re-run Behavior

If `agent-docs/.analysis-state.md` exists, read it first, compare against
current state, and augment rather than overwrite.
