You are running Phase 1 of a 3-phase codebase analysis workflow.

## Progress

| Phase | Status |
|-------|--------|
| **1. Discover & Map** | **<-- current** |
| 2. Deep Dive (per subsystem) | pending |
| 3. Synthesize | pending |

## User's Description

$ARGUMENTS

---

## Mission

Produce an architecture map of this repository. You are in read-only
learning mode. Your output will become durable documentation that later
AI agents consume to become effective copilots in this codebase.

## Hard Constraints

- **Read-only.** Do not modify, reformat, or refactor any source code.
- **Chat-first.** Present findings in chat. Write files only after explicit user confirmation.
- **Evidence-based.** Cite file paths for architectural claims.
- **Moderate citations.** Anchor each major section in 1-3 concrete references. Do not cite every sentence.
- **Factual only.** Limit analysis to observable code structure. Label anything beyond direct evidence.
- Use these labels consistently:
  - `Confirmed:` directly supported by code or docs
  - `Inference:` likely conclusion from multiple signals
  - `UNCERTAIN:` plausible but weakly supported
  - `NEEDS CLARIFICATION:` should be answered by a human

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
| Scale | small (<150 source files), medium (150-800), large (800-2000), very large (2000+) |

### Step 2: Detect Ecosystem & Explore

Check for ecosystem markers at the repo root and use the appropriate
exploration strategy:

| Marker File(s) | Ecosystem |
|---|---|
| `go.mod` | Go |
| `package.json` + `tsconfig.json` | TypeScript |
| `package.json` (no tsconfig) | JavaScript |
| `Cargo.toml` | Rust |
| `pyproject.toml` or `setup.py` | Python |
| `pom.xml` or `build.gradle*` | Java / Kotlin |
| `*.csproj` or `*.sln` | C# / .NET |
| `Gemfile` | Ruby |
| `mix.exs` | Elixir |
| `composer.json` | PHP |
| `CMakeLists.txt` + `.c/.cpp` | C / C++ |

**Ecosystem-specific exploration priorities:**

- **Go:** `go.mod`, `cmd/*/main.go`, interface definitions (`type X interface`), `.proto` files, `internal/` vs `pkg/` separation
- **TypeScript/JS:** `package.json`, `tsconfig.json`, monorepo markers (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`), framework detection (Express, Fastify, NestJS, Next.js, React, Vue), `src/` structure
- **Python:** `pyproject.toml` or `requirements.txt`, `__main__.py`/`app.py`/`manage.py`, framework detection (Django, FastAPI, Flask), `__init__.py` package boundaries, abstract base classes
- **Rust:** `Cargo.toml`, workspace members, trait definitions, async runtime (tokio), feature flags
- **Java/Kotlin:** `pom.xml` or `build.gradle*`, Spring Boot annotations, module structure, `application.yml`
- **C#/.NET:** `*.sln`/`*.csproj`, `Program.cs`/`Startup.cs`, DI registration, `appsettings.json`

If nothing matches, use a generic approach: count file types by extension, find `main.*`/`app.*`/`index.*`, scan for config files.

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

**Reading depth by scale:**

- **Small:** Read all central files, most source files
- **Medium:** Read central files fully, sample repetitive leaf modules
- **Large:** Focus on entrypoints, contracts, registries, orchestration, config. Sample leaves after pattern is established.
- **Very large / monorepo:** Map top-level architecture only. Identify packages/apps. Ask which slice to deepen.

Always note what was read fully vs. sampled vs. skipped.

### Step 4: Map Subsystems

Identify the real architectural subsystems. A folder is a subsystem only
if it satisfies **at least 2** of:

- Owns a clear responsibility
- Exposes an entrypoint, contract, or API
- Coordinates other modules
- Encapsulates a state boundary
- Has a distinct dependency pattern
- Is referenced across multiple parts of the system

**Not subsystems** (unless unusually central): generic utility folders,
test helpers, DTO-only folders, generated code directories.

Tag each subsystem with one primary role:
`entrypoint` | `orchestration` | `domain/core` | `integration` | `storage` | `configuration` | `tooling/build` | `ui/presentation` | `shared` | `generated`

**Repo-type focus adjustments:**

- **Applications:** Prioritize entrypoints, request/event flows, state/storage, orchestration, config
- **Libraries/SDKs:** Prioritize public API surface, core abstractions, extension points, error model, packaging
- **Frameworks:** Prioritize lifecycle hooks, inversion points, plugin/module systems, conventions, extension surfaces
- **Monorepos:** Do top-level architecture first. Identify workspace layout, app/package roles, shared packages, build orchestration. Ask which slice to deepen. Do NOT attempt full package-level deep dives by default.

### Step 5: Present Checkpoint

Present your findings in chat using this exact structure:

---

#### 1. Repository Classification

| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|
| Archetype | {value} | {high/medium/low} | {files/markers} |
| Primary language | {value} | {high/medium/low} | {files/markers} |
| Execution model | {value} | {high/medium/low} | {files/markers} |
| Scale | {value} | {high/medium/low} | {counts/layout} |

#### 2. Working Understanding

- `Confirmed:` {facts directly supported by code/docs}
- `Inference:` {best understanding of repo purpose}
- `UNCERTAIN:` {what remains unclear}

#### 3. Candidate Subsystems

| Subsystem | Path | Role | Responsibility | Key Files | Dependencies | Confidence |
|-----------|------|------|----------------|-----------|--------------|------------|

Order from most central to least central. Include only real
architectural units.

#### 4. Candidate Flows Worth Documenting

| Flow | Trigger | Handoffs | Why It Matters | Confidence |
|------|---------|----------|----------------|------------|

#### 5. Coverage Notes

- What was read fully
- What was sampled
- What was intentionally skipped

#### 6. Open Questions

- `NEEDS CLARIFICATION:` {question}

Only questions that materially affect subsystem boundaries, repo
purpose, or documentation scope.

#### 7. Proposed Documentation Plan

List the exact files that will be generated in `docs/`.

---

### Step 6: Ask for Confirmation

End the checkpoint with exactly:

> **Does this subsystem map and scope look right? Should I proceed to write `docs/system-overview.md` and save the analysis state?**

Do NOT write any files until the user confirms.

### Step 7: Write Files (after confirmation only)

After the user confirms, write exactly two files:

**File 1: `docs/.analysis-state.md`**

Contains the full checkpoint from Step 5 plus:

```markdown
---
phase_completed: 1
generated_on: {date}
subsystems_pending_deep_dive:
  - {subsystem-name}
  - {subsystem-name}
subsystems_completed: []
---
```

Followed by the full checkpoint content.

**File 2: `docs/system-overview.md`**

Structure:

```markdown
# {Repo Name} System Overview

> Auto-generated. Review before relying as ground truth. Generated {date}.

## Purpose
{1 paragraph: what this system does, who interacts with it, why it exists.
Mark inference explicitly.}

## External Boundaries
| Actor / System | Interaction | Evidence |
|----------------|-------------|----------|
| {actor} | {protocol} | {file path} |

## Architectural Shape
{1 paragraph: layered? modular? event-driven? pipeline? plugin-based? hybrid?}

## Major Subsystems
| Subsystem | Role | Key Files | Depends On | Confidence |
|-----------|------|-----------|------------|------------|

## Primary Flows
For each of the 3-5 most important flows:
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
- `Confirmed:` {directly evidenced facts}
- `Inference:` {trade-off or design rationale}
- `UNCERTAIN:` {what static analysis cannot confirm}
```

### Step 8: Report Next Steps

After writing, tell the user:

> **Phase 1 of 3 complete.**
>
> Created:
> - `docs/system-overview.md`
> - `docs/.analysis-state.md`
>
> **Next:** Run `/project:analyze-deep-dive {subsystem-name}` for each subsystem. Recommended order:
> 1. {subsystem} - {reason}
> 2. {subsystem} - {reason}
> 3. ...
>
> **After all deep dives:** Run `/project:analyze-synthesize`

---

## Re-run Behavior

If `docs/.analysis-state.md` already exists:

1. Read it first
2. Compare current repo state against the recorded subsystem map
3. Flag new, removed, or changed subsystems
4. Update rather than overwrite — preserve existing confirmations
5. Update `docs/system-overview.md` to reflect changes
6. Reset `subsystems_pending_deep_dive` for any subsystems that changed
