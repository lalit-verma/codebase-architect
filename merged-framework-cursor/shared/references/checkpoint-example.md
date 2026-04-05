# Example Checkpoint

This is a format example, not a claim about a real repository.

## 1. Repository Classification

| Field | Value | Confidence | Evidence |
|-------|-------|------------|----------|
| Repo archetype | monorepo | high | `pnpm-workspace.yaml`, `apps/`, `packages/` |
| Primary language | TypeScript | high | `package.json`, `tsconfig.json`, `.ts` file distribution |
| Execution model | mixed: web app + CLI + shared packages | medium | `apps/web`, `apps/cli`, package exports |
| Scale | large | high | >900 TS/JS files, multiple apps/packages |

## 2. Working Understanding Of Repo Purpose

- `Confirmed:` The repo contains a web application, a CLI, and several
  shared packages for API clients, config, and build tooling.
- `Inference:` This appears to be a product monorepo where the web app
  and CLI share domain models and infrastructure packages.
- `UNCERTAIN:` It is not yet clear whether `packages/runtime` is a real
  platform boundary or just a shared helper layer.

## 3. Candidate Subsystems

| Subsystem | Path / Scope | Role Tag | Responsibility | Evidence Anchors | Key Dependencies | Confidence | Decomposition |
|-----------|--------------|----------|----------------|------------------|------------------|------------|---------------|
| Web application | `apps/web` | entrypoint | Browser-facing product UI and request orchestration | `apps/web/src/main.ts`, `apps/web/src/router.ts`, `apps/web/package.json` | API client, config | high | — |
| CLI application | `apps/cli` | entrypoint | Terminal interface for batch and local tasks | `apps/cli/src/index.ts`, `apps/cli/package.json` | runtime, config | high | — |
| Runtime core | `packages/runtime` | orchestration | Shared execution primitives and request lifecycle | `packages/runtime/src/index.ts`, `packages/runtime/src/executor.ts` | config, provider adapters | medium | **Candidate for sub-module split:** >80 files, appears to contain executor, scheduler, and plugin-loader as distinct concerns |
| Provider adapters | `packages/providers` | integration | Wraps external APIs behind a shared contract | `packages/providers/src/index.ts`, `packages/providers/src/openai.ts` | external SDKs, runtime | high | — |
| Shared config | `packages/config` | configuration | Loads and validates env/config | `packages/config/src/index.ts`, `packages/config/src/schema.ts` | none | high | — |

## 4. Candidate Flows Worth Documenting

| Flow | Trigger | Main Handoffs | Why It Matters | Confidence |
|------|---------|---------------|----------------|------------|
| CLI command execution | user invokes CLI | `apps/cli → runtime → providers` | Reveals how user intent becomes provider calls | high |
| Web request handling | browser action | `apps/web → runtime → providers` | Shows how UI and backend share infrastructure | medium |

## 5. System-Wide Patterns Observed

| Pattern | Where Seen | Example File |
|---------|-----------|--------------|
| Barrel re-exports per package | all packages | `packages/runtime/src/index.ts` |
| Zod schemas for config validation | config, runtime | `packages/config/src/schema.ts` |
| Provider interface + per-vendor adapter | providers | `packages/providers/src/types.ts` |
| Vitest with `describe`/`it` structure | all packages | `packages/runtime/src/__tests__/executor.test.ts` |

## 6. Coverage Notes

- Read fully: root manifests, workspace config, entrypoints for apps,
  `packages/runtime`, `packages/providers`, shared config.
- Sampled: leaf utility files under `packages/runtime/src/utils`.
- Skipped in first pass: generated API clients under `packages/api-gen`.

## 7. Open Questions

- `NEEDS CLARIFICATION:` Is `packages/runtime` intended as the stable
  internal platform layer, or is it still in flux?
- `NEEDS CLARIFICATION:` Which app should be documented deeply first:
  `apps/web` or `apps/cli`?

## 8. Proposed Documentation Plan

- `agent-docs/index.md`
- `agent-docs/agent-brief.md`
- `agent-docs/system-overview.md`
- `agent-docs/patterns.md`
- `agent-docs/subsystems/web-application.md`
- `agent-docs/subsystems/cli-application.md`
- `agent-docs/subsystems/runtime-core.md` (parent doc)
- `agent-docs/subsystems/runtime-core/executor.md` (sub-module, if split confirmed)
- `agent-docs/subsystems/runtime-core/scheduler.md` (sub-module, if split confirmed)
- `agent-docs/subsystems/runtime-core/plugin-loader.md` (sub-module, if split confirmed)
- `agent-docs/subsystems/provider-adapters.md`
- `agent-docs/subsystems/shared-config.md`
- `agent-docs/flows/cli-command-execution.md`
- `agent-docs/decisions.md`
- `agent-docs/glossary.md`
- `agent-docs/uncertainties.md`
- `agent-docs/agent-protocol.md`

Write scope: top-level monorepo architecture plus the CLI/runtime slice.

---

> **Does this subsystem map and scope look right? Should I proceed to
> write `agent-docs/system-overview.md` and save the analysis state?**
