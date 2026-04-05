# Architecture Overview Template

Use this template to produce `docs/architecture-overview.md`.
Fill every section based on actual code exploration — not assumptions.
Adapt section names and content to what actually exists in the repo.

---

## Document Structure

```markdown
# {Repo Name} — Architecture Overview

> Auto-generated architecture documentation. Review and correct before
> using as reference. Generated on {date}.

## System Overview

{One paragraph: what this system does, who/what calls it, what it
calls, and why it exists.}

{Mermaid C4-style context diagram showing:
- External actors (users, client apps, other services)
- This system (as a single box)
- Downstream dependencies (databases, message queues, external APIs,
  internal services)
- Arrows labeled with protocol/mechanism (gRPC, REST, Kafka, etc.)}

## Technology Stack

| Category       | Technology              | Notes                    |
|----------------|-------------------------|--------------------------|
| Language       | {lang + version}        |                          |
| Framework      | {if applicable}         |                          |
| RPC / API      | {gRPC, REST, GraphQL}   |                          |
| Database       | {Postgres, Redis, etc.} | {what's stored where}    |
| Messaging      | {Kafka, SQS, etc.}     | {what flows through}     |
| Observability  | {metrics, logging, tracing} |                      |
| Build          | {Make, npm, cargo, etc.}|                          |
| Testing        | {framework + approach}  |                          |

## Service Architecture

{Mermaid component diagram showing:
- Each major subsystem/domain as a box
- Arrows showing dependencies between them
- External boundaries clearly marked
- Color-code or label: externally-exposed vs internal-only}

### Subsystem Descriptions

For each subsystem identified:

#### {Subsystem Name}
- **Path:** `{directory path}`
- **Responsibility:** {2-3 sentences}
- **Exposure:** {external (gRPC/REST handler) | internal only |
  async consumer}
- **Key files:** {3-5 most important files}
- **Depends on:** {other subsystems}
- **Depended on by:** {other subsystems}

## Request Flows

Trace the most important flows through the system. For each flow,
provide a Mermaid sequence diagram and a brief prose explanation.

Identify flows by looking at:
- gRPC/REST handlers (external entry points)
- Kafka/SQS consumers (async entry points)
- Cron jobs or scheduled tasks
- Internal orchestration (if a subsystem coordinates others)

Prioritize flows that:
1. Touch the most subsystems (reveals integration patterns)
2. Represent the core business logic (what the system exists to do)
3. Have interesting branching or error handling

For each flow:
```
### {Flow Name}

**Trigger:** {what initiates this flow}
**Path:** {handler} → {service} → {dependencies}

{Mermaid sequence diagram}

**Key decisions:**
- {decision point 1: what determines the branch?}
- {decision point 2}

**Error handling:**
- {how failures propagate}
- {retry behavior, if any}
```

Aim for 3-5 flows. More for complex systems, fewer for simple ones.

## Data Flow

{Mermaid flowchart showing:
- Synchronous paths (solid arrows, labeled with protocol)
- Asynchronous paths (dashed arrows, labeled with queue/topic)
- Data stores (cylinders, labeled with what lives there)
- External systems (rounded boxes)}

### State & Storage

| Store       | What lives there        | Access pattern           |
|-------------|-------------------------|--------------------------|
| {Redis}     | {sessions, cache}       | {read-heavy, TTL-based}  |
| {Postgres}  | {user data, configs}    | {CRUD via ORM}           |
| {Kafka}     | {events, async tasks}   | {pub/sub, consumer groups}|

## Key Interfaces & Abstractions

These are the architectural contracts — the types/interfaces that
define how subsystems interact. Identifying these is more important
than documenting individual functions.

For each key interface:

| Interface         | Defined in         | Purpose                     | Implementations        |
|-------------------|--------------------|-----------------------------|-----------------------|
| {ProviderClient}  | {path:line}        | {abstracts LLM providers}   | {Bedrock, Gemini...}  |
| {Executor}        | {path:line}        | {abstracts task execution}  | {Lambda, Local...}    |

## External Dependencies

| Dependency         | Purpose                | Internal/External | Critical? |
|--------------------|------------------------|-------------------|-----------|
| {package name}     | {what it's used for}   | {internal/ext}    | {yes/no}  |

"Critical" = the system cannot function without it, and there's no
fallback.

## Configuration

- **How configured:** {env vars, config files, remote config, CLI flags}
- **Config loading:** {where in the boot sequence, what reads it}
- **Environment-specific:** {how dev/staging/prod differ}
- **Feature flags / experiments:** {mechanism, where defined}

## Build & Run

```bash
# Build
{command}

# Test
{command}

# Run locally
{command}

# Other useful commands
{command}   # {description}
```

## Observations

### Strengths
- {Well-designed patterns, clean abstractions}

### Concerns
- {Tech debt, inconsistencies, dead code}
- {v1/v2 coexistence, if any}
- {Missing tests, unclear ownership}

### Patterns Worth Noting
- {Interesting design patterns used in this codebase}
- {Conventions that aren't immediately obvious}

---

*File paths cited are relative to repo root. Line numbers are
approximate and may shift with future changes.*
```

---

## Guidance for Filling This Template

- Not every section will apply to every repo. Skip sections that
  genuinely don't apply (e.g., "Messaging" if there's no async),
  but explain why you're skipping.
- For small repos (under 10k lines), this overview may be all the
  documentation needed. Scale depth to repo size.
- For monorepos, treat each app/package as a subsystem.
- If the repo has an existing README or architecture doc, read it
  first and incorporate — don't duplicate or contradict without
  noting the discrepancy.
- The subsystem list produced here is the input for generating
  Phase 2 deep-dive prompts. Get it right.
