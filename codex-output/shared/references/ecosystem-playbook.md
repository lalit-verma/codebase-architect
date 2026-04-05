# Ecosystem Exploration Playbook

Use this playbook during repository classification and evidence scan.
The point is not to run every command blindly. The point is to reduce
variance and ensure the first pass touches the files that actually
shape the architecture.

## How To Use This Playbook

1. Detect the likely primary ecosystem from root manifests.
2. Run only the commands that help map structure, entrypoints,
   contracts, and configuration.
3. Use the architectural signals section to guide what you read next.
4. If multiple ecosystems are present, classify the repo as hybrid and
   identify which ecosystem owns the main runtime path.

## Universal First Pass

Run some form of these checks in every repo:

```bash
# root manifests and workspace markers
find . -maxdepth 2 \( -name 'package.json' -o -name 'go.mod' -o -name 'Cargo.toml' -o -name 'pyproject.toml' -o -name '*.csproj' -o -name 'pom.xml' -o -name 'build.gradle*' -o -name 'WORKSPACE' -o -name 'pnpm-workspace.yaml' -o -name 'turbo.json' \) | sort

# top-level directories
find . -maxdepth 2 -type d -not -path '*/.git*' -not -path '*/node_modules*' | sort | head -120

# existing docs
find . -maxdepth 2 \( -iname 'README*' -o -iname '*ARCHITECTURE*' -o -iname '*DESIGN*' -o -iname '*ADR*' \) | sort
```

## Detection Heuristics

Use these markers as signals, not as absolute truth:

| Marker File(s)                          | Ecosystem            |
|-----------------------------------------|----------------------|
| `go.mod`                                | Go                   |
| `package.json` + `tsconfig.json`        | TypeScript           |
| `package.json` only                     | JavaScript           |
| `Cargo.toml`                            | Rust                 |
| `pyproject.toml`, `setup.py`            | Python               |
| `pom.xml`, `build.gradle*`              | Java / Kotlin        |
| `*.csproj`, `*.sln`                     | C# / .NET            |
| `Gemfile`, `*.gemspec`                  | Ruby                 |
| `mix.exs`                               | Elixir               |
| `composer.json`                         | PHP                  |
| `CMakeLists.txt` + `.c/.cpp`            | C / C++              |
| `pnpm-workspace.yaml`, `turbo.json`     | JS/TS monorepo       |

If nothing matches, fall back to generic commands and say so in the
checkpoint.

## TypeScript / JavaScript

Key files:

- `package.json`
- `tsconfig.json`
- workspace files such as `pnpm-workspace.yaml`, `turbo.json`, `nx.json`
- entry files such as `src/index.ts`, `src/main.ts`, `src/app.ts`
- framework-specific roots such as `next.config.*`, `vite.config.*`,
  `nest-cli.json`

Useful commands:

```bash
find . -maxdepth 3 -type d -not -path '*/node_modules/*' -not -path '*/.*' | sort | head -160
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \) -not -path '*/node_modules/*' | wc -l
sed -n '1,220p' package.json
sed -n '1,220p' tsconfig.json 2>/dev/null
rg -n '"workspaces"|"main"|"bin"|"exports"' package.json
rg -n 'express|fastify|koa|hono|next|nuxt|nestjs|react|vue|angular' package.json
rg -n 'router\\.|app\\.(get|post|put|delete|use)|createRouter|createApp' -g '*.ts' -g '*.tsx' -g '*.js'
rg -n 'export (class|interface|type|enum)|module\\.exports|export default' -g '*.ts' -g '*.tsx' -g '*.js'
```

Architectural signals:

- monorepo layout under `apps/`, `packages/`, `services/`
- DI and module wiring in NestJS or inversify-style code
- barrel exports that hide the true public surface
- generated clients or schema-driven code
- path aliases that hide dependency boundaries

## Go

Key files:

- `go.mod`
- `cmd/*/main.go`
- `main.go`
- `internal/`, `pkg/`, `api/`, `proto/`

Useful commands:

```bash
find . -type f -name '*.go' | wc -l
find . -type f -name '*.go' -path '*/cmd/*' | sort
sed -n '1,220p' go.mod
rg -n 'type .* interface' -g '*.go'
rg -n 'func New|MustNew|Init' -g '*.go'
find . -name '*.proto' | sort
rg -n 'RegisterServer|RegisterService|http\\.HandleFunc|mux\\.Handle|gin\\.' -g '*.go'
```

Architectural signals:

- `internal/` versus `pkg/`
- interface boundaries as architectural contracts
- manual dependency injection in `cmd/`
- code generation and `.proto` boundaries
- build tags and environment-specific code paths

## Python

Key files:

- `pyproject.toml`
- `requirements.txt`
- `manage.py`, `app.py`, `main.py`, `__main__.py`
- `settings.py`, `config.py`, `.env.example`

Useful commands:

```bash
find . -type f -name '*.py' -not -path '*/venv/*' -not -path '*/__pycache__/*' | wc -l
sed -n '1,220p' pyproject.toml 2>/dev/null
find . -name '__main__.py' -o -name 'main.py' -o -name 'app.py' -o -name 'manage.py' | sort
rg -n 'from flask|from django|from fastapi|from starlette|import aiohttp|import click' -g '*.py'
rg -n 'class .*:|def .*\\(' -g '*.py' | head -120
rg -n '@app\\.|@router\\.|urlpatterns|path\\(' -g '*.py'
```

Architectural signals:

- framework conventions hiding routing and lifecycle
- package boundaries implied by `__init__.py`
- heavy use of decorators and metaprogramming
- async versus sync execution style
- migrations and background worker boundaries

## Rust

Key files:

- `Cargo.toml`
- `src/main.rs`
- `src/lib.rs`
- workspace member `Cargo.toml` files

Useful commands:

```bash
find . -type f -name '*.rs' | wc -l
sed -n '1,220p' Cargo.toml
rg -n '\\[workspace\\]|members\\s*=|workspace\\s*=' Cargo.toml
rg -n 'pub trait|pub struct|pub enum|mod |pub mod' -g '*.rs'
sed -n '1,220p' src/main.rs 2>/dev/null
```

Architectural signals:

- workspace layout
- traits as primary contracts
- feature flags in `Cargo.toml`
- macros as hidden abstraction layers
- runtime choice such as `tokio`

## Java / Kotlin

Key files:

- `pom.xml`
- `build.gradle*`
- `src/main/...`
- `application.yml`, `application.properties`

Useful commands:

```bash
find . -type f \( -name '*.java' -o -name '*.kt' \) -not -path '*/build/*' -not -path '*/target/*' | wc -l
sed -n '1,220p' pom.xml 2>/dev/null
sed -n '1,220p' build.gradle 2>/dev/null
rg -n 'SpringBoot|@RestController|@Service|@Repository|@Configuration' -g '*.java' -g '*.kt'
rg -n '@GetMapping|@PostMapping|@RequestMapping|public interface|abstract class' -g '*.java' -g '*.kt'
```

Architectural signals:

- Spring module wiring and annotation-driven boundaries
- DTO/entity separation
- package structure signaling layer boundaries
- multi-module builds

## C# / .NET

Key files:

- `*.sln`
- `*.csproj`
- `Program.cs`
- `Startup.cs`
- `appsettings*.json`

Useful commands:

```bash
find . -type f -name '*.cs' -not -path '*/bin/*' -not -path '*/obj/*' | wc -l
find . -name '*.csproj' -o -name '*.sln' | sort
find . -name 'Program.cs' -o -name 'Startup.cs' | sort
rg -n 'PackageReference|ProjectReference' -g '*.csproj'
rg -n '\\[ApiController\\]|\\[Route\\]|\\[HttpGet\\]|\\[HttpPost\\]|public interface' -g '*.cs'
```

Architectural signals:

- ASP.NET host wiring in `Program.cs`
- DI registration in startup files
- solution and project boundaries
- appsettings-driven behavior

## Generic Fallback

Use when the ecosystem is unclear:

```bash
find . -type f | sed 's/.*\\.//' | sort | uniq -c | sort -rn | head -20
find . -maxdepth 3 \( -name 'main.*' -o -name 'app.*' -o -name 'index.*' -o -name 'Program.cs' \) | sort
find . -maxdepth 2 \( -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.json' \) | sort
rg -n 'interface|abstract|trait|protocol' -g '*' | head -120
find . -type f | grep -i test | head -120
```

In the checkpoint, explicitly say that generic fallback was used and
that confidence may be lower.
