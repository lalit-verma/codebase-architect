# Ecosystem Exploration Playbook

Use this playbook during repository classification and evidence scan.
The point is to reduce variance and ensure the first pass touches files
that actually shape the architecture.

## How To Use This Playbook

1. Detect the likely primary ecosystem from root manifests.
2. Run only the commands that help map structure, entrypoints,
   contracts, and configuration.
3. Use the architectural signals section to guide what to read next.
4. If multiple ecosystems are present, classify the repo as hybrid and
   identify which ecosystem owns the main runtime path.

## Universal First Pass

Run these checks in every repo regardless of ecosystem:

```bash
# root manifests and workspace markers
find . -maxdepth 2 \( -name 'package.json' -o -name 'go.mod' \
  -o -name 'Cargo.toml' -o -name 'pyproject.toml' -o -name '*.csproj' \
  -o -name 'pom.xml' -o -name 'build.gradle*' -o -name 'WORKSPACE' \
  -o -name 'pnpm-workspace.yaml' -o -name 'turbo.json' \
  -o -name 'Gemfile' -o -name 'mix.exs' -o -name 'composer.json' \
  -o -name 'Package.swift' \) | sort

# top-level directories
find . -maxdepth 2 -type d \
  -not -path '*/.git*' -not -path '*/node_modules*' \
  -not -path '*/vendor*' -not -path '*/__pycache__*' \
  -not -path '*/venv*' -not -path '*/.venv*' | sort | head -120

# existing docs and architecture files
find . -maxdepth 2 \( -iname 'README*' -o -iname '*ARCHITECTURE*' \
  -o -iname '*DESIGN*' -o -iname '*ADR*' -o -iname 'CLAUDE.md' \
  -o -iname '.cursorrules' -o -iname 'AGENTS.md' \) | sort
```

## Detection Heuristics

| Marker File(s) | Ecosystem |
|---|---|
| `go.mod` | Go |
| `package.json` + `tsconfig.json` | TypeScript |
| `package.json` only | JavaScript |
| `Cargo.toml` | Rust |
| `pyproject.toml`, `setup.py`, `setup.cfg` | Python |
| `pom.xml`, `build.gradle*` | Java / Kotlin |
| `*.csproj`, `*.sln` | C# / .NET |
| `Gemfile`, `*.gemspec` | Ruby |
| `mix.exs` | Elixir |
| `composer.json` | PHP |
| `CMakeLists.txt` + `.c/.cpp/.h` | C / C++ |
| `Package.swift` | Swift |
| `pnpm-workspace.yaml`, `turbo.json`, `nx.json` | JS/TS monorepo |

If nothing matches, fall back to generic commands and say so in the
checkpoint.

---

## TypeScript / JavaScript

Key files:
- `package.json`, `tsconfig.json`
- Workspace files: `pnpm-workspace.yaml`, `turbo.json`, `nx.json`
- Entry files: `src/index.ts`, `src/main.ts`, `src/app.ts`
- Framework roots: `next.config.*`, `vite.config.*`, `nest-cli.json`,
  `nuxt.config.*`, `angular.json`

Useful commands:
```bash
find . -maxdepth 3 -type d -not -path '*/node_modules/*' \
  -not -path '*/.*' | sort | head -160
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' \
  -o -name '*.jsx' \) -not -path '*/node_modules/*' | wc -l
sed -n '1,220p' package.json
sed -n '1,220p' tsconfig.json 2>/dev/null
rg -n '"workspaces"|"main"|"bin"|"exports"' package.json
rg -n 'express|fastify|koa|hono|next|nuxt|nestjs|react|vue|angular' \
  package.json
rg -n 'router\.|app\.(get|post|put|delete|use)|createRouter|createApp' \
  -g '*.ts' -g '*.tsx' -g '*.js'
rg -n 'export (class|interface|type|enum)|module\.exports|export default' \
  -g '*.ts' -g '*.tsx' -g '*.js'
```

Architectural signals:
- Monorepo layout under `apps/`, `packages/`, `services/`
- DI and module wiring in NestJS or inversify-style code
- Barrel exports that hide the true public surface
- Generated clients or schema-driven code
- Path aliases that hide dependency boundaries

---

## Go

Key files:
- `go.mod`, `go.sum`
- `cmd/*/main.go`, `main.go`
- `internal/`, `pkg/`, `api/`, `proto/`

Useful commands:
```bash
find . -type f -name '*.go' | wc -l
find . -type f -name '*.go' -path '*/cmd/*' | sort
sed -n '1,220p' go.mod
rg -n 'type .* interface' -g '*.go'
rg -n 'func New|MustNew|Init' -g '*.go'
find . -name '*.proto' | sort
rg -n 'RegisterServer|RegisterService|http\.HandleFunc|mux\.Handle|gin\.' \
  -g '*.go'
rg -n 'func main\(\)' -g '*.go'
```

Architectural signals:
- `internal/` versus `pkg/` visibility boundaries
- Interface boundaries as architectural contracts
- Manual dependency injection in `cmd/`
- Code generation and `.proto` boundaries
- Build tags and environment-specific code paths

---

## Python

Key files:
- `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`
- `manage.py`, `app.py`, `main.py`, `__main__.py`
- `settings.py`, `config.py`, `.env.example`

Useful commands:
```bash
find . -type f -name '*.py' -not -path '*/venv/*' \
  -not -path '*/.venv/*' -not -path '*/__pycache__/*' | wc -l
sed -n '1,220p' pyproject.toml 2>/dev/null
find . -name '__main__.py' -o -name 'main.py' -o -name 'app.py' \
  -o -name 'manage.py' | sort
rg -n 'from flask|from django|from fastapi|from starlette|import aiohttp|import click|import typer' \
  -g '*.py'
rg -n 'class .*:|def .*\(' -g '*.py' | head -120
rg -n '@app\.|@router\.|urlpatterns|path\(' -g '*.py'
```

Architectural signals:
- Framework conventions hiding routing and lifecycle
- Package boundaries implied by `__init__.py`
- Heavy use of decorators and metaprogramming
- Async versus sync execution style
- Migrations and background worker boundaries
- Celery/RQ/Dramatiq task definitions

---

## Rust

Key files:
- `Cargo.toml`, workspace `Cargo.toml` files
- `src/main.rs`, `src/lib.rs`

Useful commands:
```bash
find . -type f -name '*.rs' | wc -l
sed -n '1,220p' Cargo.toml
rg -n '\[workspace\]|members\s*=|workspace\s*=' Cargo.toml
rg -n 'pub trait|pub struct|pub enum|mod |pub mod' -g '*.rs'
sed -n '1,220p' src/main.rs 2>/dev/null
rg -n 'async fn|#\[tokio|#\[actix' -g '*.rs'
```

Architectural signals:
- Workspace layout
- Traits as primary contracts
- Feature flags in `Cargo.toml`
- Macros as hidden abstraction layers
- Runtime choice (tokio, async-std)

---

## Java / Kotlin

Key files:
- `pom.xml`, `build.gradle*`, `settings.gradle*`
- `src/main/...`
- `application.yml`, `application.properties`

Useful commands:
```bash
find . -type f \( -name '*.java' -o -name '*.kt' \) \
  -not -path '*/build/*' -not -path '*/target/*' | wc -l
sed -n '1,220p' pom.xml 2>/dev/null
sed -n '1,220p' build.gradle 2>/dev/null
rg -n 'SpringBoot|@RestController|@Service|@Repository|@Configuration' \
  -g '*.java' -g '*.kt'
rg -n '@GetMapping|@PostMapping|@RequestMapping|public interface|abstract class' \
  -g '*.java' -g '*.kt'
find . -name 'application.yml' -o -name 'application.properties' | sort
```

Architectural signals:
- Spring module wiring and annotation-driven boundaries
- DTO/entity separation
- Package structure signaling layer boundaries
- Multi-module builds

---

## C# / .NET

Key files:
- `*.sln`, `*.csproj`
- `Program.cs`, `Startup.cs`
- `appsettings*.json`

Useful commands:
```bash
find . -type f -name '*.cs' -not -path '*/bin/*' \
  -not -path '*/obj/*' | wc -l
find . -name '*.csproj' -o -name '*.sln' | sort
find . -name 'Program.cs' -o -name 'Startup.cs' | sort
rg -n 'PackageReference|ProjectReference' -g '*.csproj'
rg -n '\[ApiController\]|\[Route\]|\[HttpGet\]|\[HttpPost\]|public interface' \
  -g '*.cs'
```

Architectural signals:
- ASP.NET host wiring in `Program.cs`
- DI registration in startup files
- Solution and project boundaries
- appsettings-driven behavior

---

## Ruby

Key files:
- `Gemfile`, `*.gemspec`
- `config/routes.rb`, `config/application.rb`
- `app/`, `lib/`, `spec/`, `test/`

Useful commands:
```bash
find . -type f -name '*.rb' -not -path '*/vendor/*' | wc -l
sed -n '1,220p' Gemfile
find . -name 'routes.rb' -o -name 'application.rb' | sort
rg -n 'class .* < |module ' -g '*.rb' | head -120
rg -n 'Rails\.application|Sinatra|Hanami|Grape' -g '*.rb'
rg -n 'get |post |put |patch |delete |resources |namespace ' \
  config/routes.rb 2>/dev/null
```

Architectural signals:
- Rails conventions (app/models, app/controllers, app/services)
- Gem-based modularity
- Concerns and mixins as shared behavior
- Background job frameworks (Sidekiq, Resque)
- Engine-based decomposition

---

## Elixir

Key files:
- `mix.exs`
- `lib/`, `config/`
- `lib/{app_name}/application.ex`

Useful commands:
```bash
find . -type f -name '*.ex' -o -name '*.exs' | wc -l
sed -n '1,220p' mix.exs
find . -name 'application.ex' -o -name 'router.ex' | sort
rg -n 'defmodule|use GenServer|use Phoenix|use Plug' -g '*.ex'
rg -n 'def start|def init|def handle_' -g '*.ex' | head -80
```

Architectural signals:
- OTP supervision trees
- Phoenix contexts as domain boundaries
- GenServer/Agent-based state management
- Umbrella project structure
- PubSub and event-driven patterns

---

## PHP

Key files:
- `composer.json`
- `public/index.php`, `artisan`
- `app/`, `src/`, `config/`

Useful commands:
```bash
find . -type f -name '*.php' -not -path '*/vendor/*' | wc -l
sed -n '1,220p' composer.json
rg -n 'namespace |class |interface |trait ' -g '*.php' | head -120
rg -n 'Route::|->get\(|->post\(' -g '*.php'
find . -name '*.php' -path '*/Controller*' | sort
```

Architectural signals:
- Laravel/Symfony service providers and DI containers
- Route definitions and middleware
- Eloquent/Doctrine model boundaries
- Artisan command definitions

---

## Swift

Key files:
- `Package.swift`
- `*.xcodeproj`, `*.xcworkspace`
- `Sources/`, `Tests/`

Useful commands:
```bash
find . -type f -name '*.swift' | wc -l
sed -n '1,220p' Package.swift 2>/dev/null
rg -n 'protocol |class |struct |enum |actor ' -g '*.swift' | head -120
rg -n 'import |@main|@Observable' -g '*.swift' | head -80
```

Architectural signals:
- Swift Package Manager targets and dependencies
- Protocol-oriented architecture
- Actor-based concurrency
- SwiftUI vs UIKit layering

---

## Generic Fallback

Use when the ecosystem is unclear:

```bash
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
find . -maxdepth 3 \( -name 'main.*' -o -name 'app.*' \
  -o -name 'index.*' -o -name 'Program.cs' \) | sort
find . -maxdepth 2 \( -name '*.yml' -o -name '*.yaml' \
  -o -name '*.toml' -o -name '*.json' \) | sort
rg -n 'interface|abstract|trait|protocol' -g '*' | head -120
find . -type f | grep -i test | head -120
```

In the checkpoint, explicitly say that generic fallback was used and
confidence may be lower.
