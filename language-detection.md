# Language Detection & Ecosystem-Specific Commands

## Detection Logic

Check the repo root for these files in order. Stop at the first match.
If multiple match (e.g., a Go repo with a package.json for tooling),
use the primary application language — determined by which has more
source files.

| Marker File(s)                          | Ecosystem        |
|-----------------------------------------|------------------|
| go.mod                                  | Go               |
| package.json + tsconfig.json            | TypeScript        |
| package.json (no tsconfig)              | JavaScript        |
| Cargo.toml                              | Rust              |
| pyproject.toml, setup.py, setup.cfg     | Python            |
| pom.xml, build.gradle, build.gradle.kts | Java / Kotlin     |
| *.csproj, *.sln                         | C# / .NET         |
| Gemfile, *.gemspec                      | Ruby              |
| mix.exs                                 | Elixir            |
| composer.json                           | PHP               |
| CMakeLists.txt, Makefile (with .c/.cpp) | C / C++           |
| deno.json                               | Deno (TypeScript) |

If nothing matches, fall back to generic commands.

---

## Go

**File extensions:** .go
**Entry points:** `cmd/*/main.go`, `main.go`
**Dependency manifest:** `go.mod`
**Config patterns:** YAML/JSON config files, env vars, Viper

**Exploration commands:**
```bash
# Structure
find . -type f -name '*.go' | wc -l
find . -type f -name '*.go' -path '*/cmd/*'
tree -L 2 -d --prune -I vendor

# Dependencies
cat go.mod
go list -m all 2>/dev/null | head -40

# Interfaces & types (architectural contracts)
grep -rn 'type.*interface' --include='*.go' | head -30
grep -rn 'func New' --include='*.go' | head -20

# gRPC / proto
find . -name '*.proto' | head -20
grep -rn 'RegisterServer\|RegisterService' --include='*.go' | head -15

# Test patterns
find . -name '*_test.go' | wc -l
grep -rn 'func Test' --include='*_test.go' | head -10

# Build
cat Makefile 2>/dev/null | head -40
```

**Architectural signals to look for:**
- `internal/` vs `pkg/` separation (Go convention for private vs public)
- Wire or manual dependency injection in `cmd/`
- Interface definitions — these are the architectural contracts
- `//go:generate` directives
- Build tags for environment-specific compilation

---

## TypeScript / JavaScript

**File extensions:** .ts, .tsx, .js, .jsx
**Entry points:** `src/index.ts`, `src/main.ts`, `src/app.ts`, bin entries in package.json
**Dependency manifest:** `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
**Config patterns:** .env files, config/ directory, dotfiles

**Exploration commands:**
```bash
# Structure
find src -type f \( -name '*.ts' -o -name '*.tsx' \) 2>/dev/null | wc -l
find . -maxdepth 3 -type d -not -path '*/node_modules/*' -not -path '*/\.*'

# Dependencies
cat package.json | head -60
# Check for monorepo
ls packages/ 2>/dev/null || ls apps/ 2>/dev/null

# Exports & entry points
grep -r '"main"\|"bin"\|"exports"' package.json
cat tsconfig.json 2>/dev/null

# Framework detection
grep -l 'express\|fastify\|koa\|hono\|next\|nuxt\|react\|vue\|angular\|nestjs' package.json

# Class/interface structure
grep -rn 'export class\|export interface\|export type\|export enum' --include='*.ts' | head -30
grep -rn 'export default' --include='*.ts' --include='*.tsx' | head -20

# Route/handler registration
grep -rn 'router\.\|app\.\(get\|post\|put\|delete\|use\)' --include='*.ts' | head -20

# Test patterns
find . -name '*.test.ts' -o -name '*.spec.ts' | wc -l
cat jest.config* vitest.config* 2>/dev/null | head -20

# Build
cat package.json | grep -A 20 '"scripts"'
```

**Architectural signals to look for:**
- Monorepo structure (packages/, apps/, workspace config)
- Framework choice (Express, Fastify, NestJS, Next.js, etc.)
- DI containers (tsyringe, inversify, NestJS modules)
- Barrel exports (index.ts files re-exporting)
- Path aliases in tsconfig.json

---

## Python

**File extensions:** .py
**Entry points:** `__main__.py`, `main.py`, `app.py`, `manage.py`, CLI entry in pyproject.toml
**Dependency manifest:** `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`, `poetry.lock`
**Config patterns:** .env, settings.py, config.py, YAML configs

**Exploration commands:**
```bash
# Structure
find . -type f -name '*.py' -not -path '*/__pycache__/*' -not -path '*/venv/*' | wc -l
find . -type d -name '__pycache__' -prune -o -type d -not -path '*/venv/*' -print | head -40

# Dependencies
cat pyproject.toml 2>/dev/null || cat requirements.txt 2>/dev/null | head -40
pip list 2>/dev/null | head -30

# Entry points
cat pyproject.toml 2>/dev/null | grep -A 10 '\[project.scripts\]'
find . -name '__main__.py' -o -name 'main.py' -o -name 'app.py' | head -5

# Framework detection
grep -rl 'from flask\|from django\|from fastapi\|from starlette\|import tornado\|import aiohttp' --include='*.py' | head -5

# Class/module structure
grep -rn 'class .*:' --include='*.py' | grep -v test | head -30
grep -rn 'def .*(' --include='*.py' | grep -v test | grep -v '__' | head -30

# API routes
grep -rn '@app\.\|@router\.\|urlpatterns\|path(' --include='*.py' | head -20

# Test patterns
find . -name 'test_*.py' -o -name '*_test.py' | wc -l
cat pytest.ini 2>/dev/null || grep -A 5 '\[tool.pytest\]' pyproject.toml 2>/dev/null

# Build
cat Makefile 2>/dev/null | head -40
```

**Architectural signals to look for:**
- Framework choice (Django, FastAPI, Flask, etc.)
- Package structure (__init__.py files define packages)
- Abstract base classes (ABC) — these are the contracts
- Async patterns (asyncio, async def)
- Type hints density — indicates code maturity
- Alembic/migrations directory

---

## Rust

**File extensions:** .rs
**Entry points:** `src/main.rs`, `src/lib.rs`
**Dependency manifest:** `Cargo.toml`, `Cargo.lock`
**Config patterns:** .env, config/ directory, build.rs

**Exploration commands:**
```bash
# Structure
find . -type f -name '*.rs' | wc -l
tree -L 2 -d --prune -I target

# Dependencies
cat Cargo.toml
# Workspace detection
grep -A 20 '\[workspace\]' Cargo.toml 2>/dev/null

# Module structure
grep -rn 'pub mod\|mod ' --include='*.rs' | grep -v test | head -30
grep -rn 'pub trait\|pub struct\|pub enum' --include='*.rs' | head -30

# Entry points
cat src/main.rs 2>/dev/null | head -50

# Test patterns
grep -rn '#\[cfg(test)\]\|#\[test\]' --include='*.rs' | wc -l

# Build
cargo build --dry-run 2>&1 | head -10
```

**Architectural signals to look for:**
- Workspace structure (multiple crates)
- Trait definitions — these are the architectural contracts
- Error handling patterns (thiserror, anyhow, custom)
- Async runtime (tokio, async-std)
- Macro usage (procedural macros = abstraction layer)
- Feature flags in Cargo.toml

---

## Java / Kotlin

**File extensions:** .java, .kt
**Entry points:** Classes with `public static void main`, `@SpringBootApplication`
**Dependency manifest:** `pom.xml`, `build.gradle`, `build.gradle.kts`
**Config patterns:** application.yml, application.properties

**Exploration commands:**
```bash
# Structure
find . -type f \( -name '*.java' -o -name '*.kt' \) -not -path '*/build/*' -not -path '*/target/*' | wc -l
find src -type d 2>/dev/null | head -40

# Dependencies
cat pom.xml 2>/dev/null | head -80
cat build.gradle* 2>/dev/null | head -80

# Framework detection
grep -rl 'SpringBoot\|@RestController\|@Service' --include='*.java' --include='*.kt' | head -5

# Interface/class structure
grep -rn 'public interface\|abstract class\|interface ' --include='*.java' --include='*.kt' | head -30

# API routes
grep -rn '@GetMapping\|@PostMapping\|@RequestMapping\|@Path' --include='*.java' --include='*.kt' | head -20

# Test patterns
find . -name '*Test.java' -o -name '*Test.kt' -o -name '*Spec.kt' | wc -l

# Build
./mvnw --version 2>/dev/null || ./gradlew --version 2>/dev/null
```

**Architectural signals to look for:**
- Spring Boot annotations (service layers, DI)
- Module structure (multi-module Maven/Gradle)
- Interface segregation patterns
- DTO vs Entity separation
- Config profiles (application-{env}.yml)

---

## C# / .NET

**File extensions:** .cs
**Entry points:** `Program.cs`, `Startup.cs`
**Dependency manifest:** `*.csproj`, `*.sln`, `Directory.Build.props`
**Config patterns:** `appsettings.json`, `appsettings.{env}.json`

**Exploration commands:**
```bash
# Structure
find . -type f -name '*.cs' -not -path '*/bin/*' -not -path '*/obj/*' | wc -l
find . -name '*.csproj' | head -10
cat *.sln 2>/dev/null | head -30

# Dependencies
cat **/*.csproj 2>/dev/null | grep -i 'PackageReference' | head -30

# Entry & DI
find . -name 'Program.cs' -o -name 'Startup.cs' | head -5

# Interface/class structure
grep -rn 'public interface\|public abstract class' --include='*.cs' | head -30

# API routes
grep -rn '\[HttpGet\]\|\[HttpPost\]\|\[Route\]\|\[ApiController\]' --include='*.cs' | head -20

# Test patterns
find . -name '*Tests.cs' -o -name '*Test.cs' | wc -l
```

---

## Generic Fallback

If the language isn't detected, use these universal commands:

```bash
# Map structure
tree -L 2 -d --prune -I 'node_modules|vendor|target|build|dist|__pycache__|.git'
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15

# Find likely entry points
find . -maxdepth 3 -name 'main.*' -o -name 'app.*' -o -name 'index.*' | head -10

# Find config
find . -maxdepth 2 -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.json' | grep -i config | head -10

# Find interfaces/contracts (language-agnostic grep)
grep -rn 'interface\|abstract\|trait\|protocol' --include='*.go' --include='*.ts' --include='*.py' --include='*.rs' --include='*.java' | head -30

# Find API definitions
find . -name '*.proto' -o -name '*.graphql' -o -name 'openapi*' -o -name 'swagger*' | head -10

# Tests
find . -type f | grep -i test | wc -l

# README
cat README.md 2>/dev/null | head -80
```

Proceed with best-effort analysis using the generic approach. Note the
detected file type distribution in the architecture overview so the
user knows what they're dealing with.
