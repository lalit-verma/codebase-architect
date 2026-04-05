# Template: `agent-docs/patterns.md`

This document captures code and test conventions observed across the
repository. Coding agents should read this before writing new code to
match existing style. Per-subsystem specifics are in subsystem docs.

```markdown
# {Repo Name} — Code and Test Patterns

> Conventions observed through static analysis. Follow these when
> adding new code to maintain consistency.

## Naming Conventions

| Element | Convention | Example | Scope |
|---------|-----------|---------|-------|
| {files} | {kebab-case/camelCase/snake_case/etc.} | `{example}` | {system-wide / subsystem} |
| {functions} | {convention} | `{example}` | {scope} |
| {types/classes} | {convention} | `{example}` | {scope} |
| {constants} | {convention} | `{example}` | {scope} |
| {test files} | {convention} | `{example}` | {scope} |

## File Organization

| Convention | Description | Example |
|-----------|-------------|---------|
| {pattern} | {how files/folders are organized} | `{path}` |

## Error Handling

| Pattern | Where Used | Example File |
|---------|-----------|--------------|
| {pattern: custom error classes / result types / error codes / etc.} | {subsystems} | `{file}` |

## Common Abstractions

Recurring patterns used across multiple subsystems.

| Abstraction | Purpose | Interface/Contract | Implementations |
|-------------|---------|-------------------|-----------------|
| {pattern name} | {what it standardizes} | `{file:line}` | `{file}`, `{file}` |

## Import and Module Conventions

| Convention | Description | Example |
|-----------|-------------|---------|
| {barrel exports / direct imports / path aliases / etc.} | {details} | `{file}` |

## Test Structure and Conventions

| Aspect | Convention | Example File |
|--------|-----------|--------------|
| Framework | {jest/vitest/pytest/go test/etc.} | `{file}` |
| Location | {colocated / __tests__ / *_test.go / etc.} | `{path}` |
| Structure | {describe/it / table-driven / BDD / etc.} | `{file}` |
| Naming | {test file naming pattern} | `{example}` |

## Fixture and Mock Patterns

| Pattern | Usage | Example File |
|---------|-------|--------------|
| {shared fixtures / factory functions / mock builders / etc.} | {where used} | `{file}` |

## Cross-Subsystem Inconsistencies

> Note any places where conventions differ between subsystems. A
> coding agent should follow the local convention of the subsystem
> it is modifying.

| Inconsistency | Subsystem A | Subsystem B | Recommendation |
|--------------|-------------|-------------|----------------|
| {what differs} | {convention in A} | {convention in B} | {which to follow, or "follow local"} |
```
