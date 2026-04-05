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

| Subsystem | Path / Scope | Role Tag | Responsibility | Evidence Anchors | Key Dependencies | Confidence |
|-----------|--------------|----------|----------------|------------------|------------------|------------|
| Web application | `apps/web` | entrypoint | Browser-facing product UI and request orchestration | `apps/web/src/main.ts`, `apps/web/src/router.ts`, `apps/web/package.json` | API client package, config package | high |
| CLI application | `apps/cli` | entrypoint | User-facing terminal interface for batch and local tasks | `apps/cli/src/index.ts`, `apps/cli/package.json` | runtime package, config package | high |
| Runtime core | `packages/runtime` | orchestration | Shared execution primitives and request lifecycle management | `packages/runtime/src/index.ts`, `packages/runtime/src/executor.ts` | config package, provider adapters | medium |
| Provider adapters | `packages/providers` | integration | Wraps external API/provider behavior behind a shared contract | `packages/providers/src/index.ts`, `packages/providers/src/openai.ts` | external SDKs, runtime core | high |
| Shared config | `packages/config` | configuration | Loads and validates env/config used by apps and packages | `packages/config/src/index.ts`, `packages/config/src/schema.ts` | none | high |

## 4. Candidate Flows Worth Documenting

| Flow | Trigger | Main Handoffs | Why It Matters | Confidence |
|------|---------|---------------|----------------|------------|
| CLI command execution | user invokes CLI | `apps/cli -> runtime -> providers` | Reveals how user intent becomes provider calls | high |
| Web request handling | browser action | `apps/web -> runtime -> providers` | Shows how UI and backend-facing logic share infrastructure | medium |

## 5. Coverage Notes

- Read fully: root manifests, workspace config, entrypoints for apps,
  `packages/runtime`, `packages/providers`, shared config.
- Sampled: leaf utility files under `packages/runtime/src/utils`.
- Skipped in first pass: generated API clients under `packages/api-gen`.

## 6. Open Questions

- `NEEDS CLARIFICATION:` Is `packages/runtime` intended as the stable
  internal platform layer, or is it still in flux?
- `NEEDS CLARIFICATION:` Which app should be documented deeply first:
  `apps/web` or `apps/cli`?

## 7. Proposed Documentation Plan

- `docs/index.md`
- `docs/agent-brief.md`
- `docs/system-overview.md`
- `docs/subsystems/web-application.md`
- `docs/subsystems/runtime-core.md`
- `docs/subsystems/provider-adapters.md`
- `docs/flows/cli-command-execution.md`
- `docs/decisions.md`
- `docs/glossary.md`
- `docs/uncertainties.md`

Write scope: top-level monorepo architecture plus the CLI/runtime slice.

## 8. Required Closing Question

Does this subsystem map and scope look right, and do you want me to
stay in chat mode or write the approved docs to `docs/`?
