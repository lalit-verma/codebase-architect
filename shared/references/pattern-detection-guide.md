# Pattern Detection Guide

Patterns are the highest-impact output for coding agents. When an agent
needs to add a new endpoint, service, test, or adapter, a documented
pattern tells it exactly what to create and where to register it.

## What Counts as a Pattern

A pattern is a recurring code structure where 3+ files follow the same
shape: similar directory placement, similar naming convention, similar
internal structure.

Examples:
- API endpoint handlers that all follow the same file structure
- Service classes that all implement the same interface and register
  the same way
- Database migration files with consistent naming and structure
- Test files that follow a consistent setup/teardown pattern
- Adapter implementations that all wrap external APIs the same way
- Configuration modules that follow a standard schema pattern

## What is NOT a Pattern

- Single-instance files (no repetition to follow)
- Generic language idioms (e.g., "Go uses interfaces") — agents already
  know these
- Generated code structures — agents should not create generated files
- Standard framework boilerplate documented in the framework's own docs
  (e.g., "Rails controllers inherit from ApplicationController")
- Patterns with fewer than 3 instances — not enough evidence

## Detection Method

### During Phase 1 (preliminary)

While scanning evidence:
1. Note directories containing 3+ files with similar names or structure
2. Note registration points where multiple similar items are wired
3. Record as "preliminary patterns" in the checkpoint
4. Do NOT deeply analyze yet — just flag for Phase 2

### During Phase 2 (per subsystem)

While deep-diving each subsystem:
1. Identify file clusters: groups of files in the same directory with
   similar naming (e.g., `handle_*.go`, `*_service.py`, `*Controller.java`)
2. Read the 2-3 cleanest/simplest instances fully
3. Extract the common structure:
   - File naming convention
   - Internal structure (imports, class/function shape, sections)
   - Registration or wiring point (where new instances are connected)
   - Test companion pattern (how tests are structured for these files)
4. Identify the "template file" — the cleanest, most representative
   instance that a future agent should copy when adding a new one
5. Record in the subsystem doc and accumulate for Phase 3

### During Phase 3 (consolidation)

1. Collect all patterns detected across subsystem deep dives
2. Deduplicate: merge patterns that are the same across subsystems
3. Present to user for confirmation (semi-automated):
   - Show each pattern with: name, category, example file, file count,
     proposed steps
   - User confirms, edits, or removes each pattern
4. Write confirmed patterns to `agent-docs/patterns.md`
5. Include the most important patterns in `agent-docs/agent-context.md`

## Pattern Categories

Tag each pattern with one category:

- `endpoint` — API routes, handlers, controllers
- `service` — business logic modules, use cases
- `model` — data models, entities, DTOs
- `migration` — database schema changes
- `test` — test file conventions
- `adapter` — external integrations, provider wrappers
- `config` — configuration modules
- `command` — CLI commands, job definitions
- `middleware` — request/response pipeline stages
- `event` — event handlers, subscribers, listeners

## Output Format for patterns.md

For each confirmed pattern, document:

```markdown
## {Pattern Name} ({category})

- Example file: `{path}` (cleanest instance to follow)
- Files following this pattern: {count} files in `{directory}`
- Registration point: `{file:line}` (where new instances are wired)

### To add a new instance:
1. Create `{path convention}` following `{example file}`
2. {implementation step with file reference}
3. Register in `{registration file:line}`
4. Add test at `{test path convention}` following `{test example}`

### Conventions within this pattern:
- {naming rule}
- {structural rule}
- {import/dependency rule}

### Anti-patterns:
- {what NOT to do when following this pattern}
```

## Output Format for agent-context.md

In `agent-context.md`, include only the recipe (steps to add a new
instance). Skip the metadata. Keep it terse:

```markdown
### To add a new {thing}
1. Create `{path}` following `{example}`
2. Register in `{file}`
3. Test at `{path}` following `{test example}`
```

## Semi-Automated Confirmation Flow

Pattern detection is semi-automated. The agent proposes, the user
confirms. This happens at two points:

1. **Phase 1 checkpoint:** Preliminary patterns are listed. User can
   say "that's not really a pattern" or "you missed the migration
   pattern."

2. **Phase 3 synthesis:** Before writing `patterns.md`, present the
   full list with examples. User confirms each or edits.

Never write patterns to durable docs without user confirmation.
