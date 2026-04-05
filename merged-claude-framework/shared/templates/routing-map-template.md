# Template: `agent-docs/routing-map.md`

Machine-readable task-to-doc routing. A coding agent can parse the
YAML block to look up which subsystem doc, pattern recipe, template
file, and test template apply to a given task — instead of scanning
agent-context.md manually.

## Content Sourcing

- `subsystem_routing` entries: one per completed subsystem. Pull
  `owns_paths` from subsystem doc Boundaries section. `key_files`
  from Evidence Anchors. `key_tests` from Testing section.
  `common_tasks` from Modification Guide "To add a new X" items.
- `pattern_routing` entries: one per pattern from `patterns.md`. Pull
  `template_file` from the pattern's example file. `registration`
  from the registration point. `test_template` from the "Add test"
  step. `doc` uses `patterns.md#` plus a slugified anchor of the
  pattern heading (lowercase, hyphens for spaces, strip special chars).

```markdown
# Routing Map

> Machine-readable task-to-doc routing. Use this for structured
> lookups instead of scanning agent-context.md manually.
> Generated: {YYYY-MM-DD HH:MM UTC}
> Analysis version: v1 | Source commit: {short_sha}

```yaml
subsystem_routing:
  - name: "{subsystem}"
    doc: "agent-docs/subsystems/{name}.md"
    owns_paths:
      - "{path glob}"
    key_files:
      - "{file}"
    key_tests:
      - "{test file}"
    common_tasks:
      - "{task description from Modification Guide}"

pattern_routing:
  - pattern: "{pattern name}"
    doc: "agent-docs/patterns.md#{slugified-anchor}"
    subsystem: "{subsystem name}"
    template_file: "{best file to copy}"
    registration: "{file:line}"
    test_template: "{best test to copy}"
`` `
`` `
```

Note: The triple-backtick nesting above is for template illustration.
When generating, emit a single YAML code block inside the markdown file.
