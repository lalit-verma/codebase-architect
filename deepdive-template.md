# Deep-Dive Prompt Template

When generating deep-dive prompts in Step 5 of the workflow, use this
template. For each subsystem, fill in {PLACEHOLDERS} with the actual
values discovered during exploration.

Generate one prompt file per subsystem. Each file should contain the
complete prompt below, fully filled in and ready to paste into a fresh
Claude Code session.

---

## Prompt Template

```
Read docs/architecture-overview.md to understand how {SUBSYSTEM_NAME}
fits into the overall system. Then do a deep-dive analysis of the
{SUBSYSTEM_NAME} subsystem. Write the results to
docs/domains/{FILENAME}.md.

**Subsystem:** {SUBSYSTEM_NAME}
**Directory:** {DIRECTORY_PATH}
**Description:** {BRIEF_DESCRIPTION}
**Key entry files:** {ENTRY_FILES}

Explore {DIRECTORY_PATH} thoroughly before writing. Read every file
in the directory (or if there are more than ~30 files, read all
non-test files and sample the tests).

Write the document with these sections:

## Overview
- What this subsystem does and why it exists
- Mermaid component diagram showing internal structure
- How it connects to the rest of the system (reference the
  architecture overview)
- One paragraph on the design philosophy: is this a thin wrapper?
  A thick abstraction? Event-driven? Pipeline? State machine?

## File Inventory

List every file in the subsystem with a one-line description.
Group by responsibility:

| File | Role | Layer |
|------|------|-------|
| {file} | {what it does} | {handler/service/model/util/test/config} |

## Core Types & Interfaces

Document every key exported type and interface. For each:

### {TypeName}
- **Defined in:** `{file:line}`
- **Purpose:** {what it represents}
- **Key fields/methods:** {the important ones, not exhaustive}
- **Created by:** {who constructs it}
- **Consumed by:** {who uses it}

After documenting individually, provide a Mermaid class/type diagram
showing relationships between key types (inheritance, composition,
dependency).

## Request / Data Flows

Trace every entry point into this subsystem:
{ENTRY_POINTS}

For each entry point, provide:
1. A Mermaid sequence diagram showing the complete flow
2. Prose explanation of what happens at each step
3. Error handling: what errors are returned, how failures propagate,
   retry behavior
4. Async handoffs: where does sync processing end and async begin?

## State & Storage

- What state does this subsystem manage?
- Where is it stored (Redis, database, in-memory, file system)?
- Cache patterns: what's cached, TTLs, invalidation strategy
- Data lifecycle: how is data created, updated, and cleaned up?

If this subsystem is stateless, say so and explain how it avoids
state (passes through, delegates, etc.).

## Dependencies

### Internal (other subsystems in this repo)

| Subsystem | Why | Direction |
|-----------|-----|-----------|
| {name} | {what it uses from there} | {imports / imported by / bidirectional} |

### External (libraries and packages)

| Package | Purpose | Replaceable? |
|---------|---------|-------------|
| {name} | {what it does} | {yes/no — is it load-bearing?} |

Mermaid dependency graph showing all connections.

Flag any circular dependencies or surprising coupling.

## Configuration

- What config values does this subsystem read?
- What feature flags or experiment hooks exist?
- What defaults are assumed?
- What environment-specific behavior exists?

## Edge Cases & Gotchas

Non-obvious things someone working in this code needs to know:
- Implicit contracts (e.g., "this function must be called before that
  one")
- Race conditions or concurrency concerns
- Known limitations
- Tech debt or TODO comments in the code
- Behavior that surprised you when reading

## Testing

{LANGUAGE_SPECIFIC_TEST_COMMAND}

- What test files exist? List them.
- What's tested vs. what's not?
- Test helpers, fixtures, mocks worth noting
- Test patterns used (table-driven, BDD, snapshot, etc.)

## Design Decisions & Trade-offs

This section is the highest-value part for learning. For each major
design choice in this subsystem:

1. **What was chosen:** {the pattern/approach used}
2. **What it enables:** {advantages of this approach}
3. **What it costs:** {disadvantages, limitations, complexity}
4. **Alternative approaches:** {how else could this have been done}
5. **Assessment:** {your read on whether this was a good trade-off}

Aim for 2-4 design decisions per subsystem.

## Questions for the Team

Things that can't be determined from code alone. Mark each with
"NEEDS CLARIFICATION:". These become interview questions for the
user to take to the team.

---

Rules:
- Cite specific file paths and line numbers for every claim.
- Use Mermaid for all diagrams (```mermaid fenced blocks).
- If something is ambiguous, say "UNCERTAIN:" — don't guess.
- Do NOT modify any source code. Read only.
- Keep under 1500 lines. Prefer precise references over verbose
  descriptions.
```

---

## Customization Notes

When generating prompts from this template:

1. **{ENTRY_POINTS}** — List the specific entry points you discovered
   during Step 3 exploration. Example:
   - "gRPC handler `HandleChat` in `internal/chat/handler.go`"
   - "Kafka consumer `ProcessEvent` in `internal/chat/consumer.go`"
   - "Internal call from AI Gateway via `ChatService.Execute()`"

2. **{LANGUAGE_SPECIFIC_TEST_COMMAND}** — Use the appropriate command
   from `references/language-detection.md`. Examples:
   - Go: `go test -v ./{DIRECTORY_PATH}/...`
   - TS: `npx jest --listTests {DIRECTORY_PATH}`
   - Python: `pytest {DIRECTORY_PATH} --collect-only`
   - Rust: `cargo test -p {package} -- --list`

3. **For small subsystems** (under 10 files), the File Inventory and
   Core Types sections can be combined. Don't over-structure small
   packages.

4. **For very large subsystems** (50+ files), suggest the user split
   into multiple deep dives and note which sub-directories to tackle
   separately.

5. **Adapt the "Design Decisions" framing** based on what the user
   said in Step 2. If they're learning to build something similar,
   emphasize "what would you do differently." If they're evaluating
   for adoption, emphasize "what does this mean for maintenance cost."
