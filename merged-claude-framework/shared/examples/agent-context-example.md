# Example: agent-context.md

This is a format example showing the target quality and structure for
`agent-docs/agent-context.md`. Based on the same fictional TypeScript
monorepo from the checkpoint example.

Note: under 120 lines, no prose, no tables, every line actionable.

---

```markdown
# Acme Platform — Agent Context

> Load this file at session start for full codebase context.
> Generated on 2026-04-06. Re-run analysis to update.

## What this repo is
TypeScript monorepo for the Acme platform. Contains a Next.js web app,
a CLI tool, and shared packages for runtime execution, provider
adapters, and configuration. Uses pnpm workspaces + turborepo.

## Architecture map
- `apps/web/` — Next.js web application (product UI, API routes)
- `apps/web/src/routes/` — API route handlers
- `apps/web/src/components/` — React UI components
- `apps/web/src/lib/` — web-specific utilities and hooks
- `apps/cli/` — CLI tool for batch operations
- `apps/cli/src/commands/` — CLI command handlers
- `packages/runtime/` — shared execution engine and request lifecycle
- `packages/runtime/src/executor.ts` — core execution loop
- `packages/providers/` — external API adapters (OpenAI, Anthropic, etc.)
- `packages/providers/src/base.ts` — Provider interface definition
- `packages/config/` — configuration loading and validation
- `packages/config/src/schema.ts` — config schema (Zod)
- `packages/api-gen/` — generated API client (do not edit)
- `turbo.json` — build orchestration
- `pnpm-workspace.yaml` — workspace definition

## Key patterns

### To add a new provider adapter
1. Create `packages/providers/src/{name}.ts` following `packages/providers/src/openai.ts`
2. Implement the `Provider` interface from `packages/providers/src/base.ts:14`
3. Export from `packages/providers/src/index.ts`
4. Add config schema in `packages/config/src/schema.ts`
5. Add test at `packages/providers/tests/{name}.test.ts` following `openai.test.ts`

### To add a new CLI command
1. Create `apps/cli/src/commands/{name}.ts` following `apps/cli/src/commands/run.ts`
2. Export command definition with `name`, `description`, `handler`
3. Register in `apps/cli/src/commands/index.ts`
4. Add test at `apps/cli/tests/commands/{name}.test.ts`

### To add a new API route
1. Create `apps/web/src/routes/{name}.ts` following `apps/web/src/routes/health.ts`
2. Export route handler with method and path
3. Route is auto-registered by the file-based router
4. Add test at `apps/web/tests/routes/{name}.test.ts`

## Conventions
- Constructor injection for all services (see `packages/runtime/src/executor.ts:8`)
- Zod schemas for all config validation (see `packages/config/src/schema.ts`)
- Barrel exports via `index.ts` in every package (see `packages/providers/src/index.ts`)
- Tests use vitest with factory helpers (see `packages/runtime/tests/helpers.ts`)
- Error wrapping with `AppError` class (see `packages/runtime/src/errors.ts:5`)
- Environment config via `.env` files loaded in app entrypoints only

## Do NOT
- Edit files in `packages/api-gen/` — they are generated from OpenAPI spec
- Import directly between apps (`apps/web` must not import from `apps/cli`)
- Add provider-specific logic outside `packages/providers/`
- Put shared types in app packages — use `packages/runtime/src/types/`
- Bypass the `Provider` interface for external API calls
- Use `process.env` directly — always go through `packages/config`

## Key contracts
- `packages/providers/src/base.ts:14` — `Provider` interface, all adapters implement this
- `packages/runtime/src/types/request.ts:8` — `ExecutionRequest` type, input to executor
- `packages/runtime/src/types/response.ts:5` — `ExecutionResult` type, output from executor
- `packages/config/src/schema.ts:12` — `AppConfig` Zod schema, validates all config
- `apps/cli/src/commands/types.ts:3` — `CommandDef` interface, all CLI commands implement

## For deeper context
- `agent-docs/agent-brief.md` — full architecture overview
- `agent-docs/patterns.md` — all detected patterns with recipes
- `agent-docs/subsystems/runtime-core.md` — execution engine internals
- `agent-docs/subsystems/provider-adapters.md` — how providers work
- `agent-docs/subsystems/web-application.md` — web app architecture
- `agent-docs/decisions.md` — why monorepo, why pnpm, why Zod
- `agent-docs/uncertainties.md` — runtime package stability unclear
```
