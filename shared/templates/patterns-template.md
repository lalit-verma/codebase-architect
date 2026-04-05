# Template: `agent-docs/patterns.md`

```markdown
# Code Patterns and Conventions

> Detected patterns for common operations in this codebase.
> Confirmed by user. Follow these when adding new instances.
> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

## {Pattern Name} ({category})

- Example file: `{path}` (cleanest instance — copy this structure)
- Files following this pattern: {count} files in `{directory}/`
- Registration point: `{file:line}`

### To add a new instance
1. Create `{path convention}` following `{example file}`
2. {implementation step with file reference}
3. Register in `{registration file:line}`
4. Add test at `{test path convention}` following `{test example}`

### Conventions within this pattern
- {naming rule}
- {structural rule}
- {import or dependency rule}

### Anti-patterns
- {what NOT to do and why}
```
