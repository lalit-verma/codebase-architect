---
name: codebase-analysis
description: >
  Deep-dive architecture analysis and documentation for any codebase.
  Produces a high-level architecture overview with Mermaid diagrams,
  then generates ready-to-run prompts for per-subsystem deep dives.
  Use this skill whenever the user wants to understand, learn from,
  document, or map the architecture of a repository — even if they
  say something casual like "help me understand this repo", "what does
  this codebase do", "walk me through the architecture", "I'm new to
  this repo", "document this codebase", or "how is this project
  structured". Also trigger when the user says "analyze this codebase",
  "generate architecture docs", or "I want to learn how this is built".
  This skill is for learning and understanding — not for modifying,
  refactoring, or contributing code.
---

# Codebase Architecture Analysis

Produces thorough architecture documentation for any codebase. The goal
is deep understanding of design decisions and trade-offs — not
modification or contribution.

## Workflow

Execute these steps in order. Do not skip steps.

### Step 1: Detect Language & Ecosystem

Read `references/language-detection.md` for the full detection logic
and language-specific commands.

Quick detection: check for these files at the repo root.

| File                      | Language/Ecosystem         |
|---------------------------|----------------------------|
| go.mod                    | Go                         |
| package.json              | TypeScript / JavaScript    |
| Cargo.toml                | Rust                       |
| pyproject.toml, setup.py  | Python                     |
| pom.xml, build.gradle     | Java / Kotlin              |
| *.csproj, *.sln           | C# / .NET                  |
| Gemfile                   | Ruby                       |
| mix.exs                   | Elixir                     |
| composer.json             | PHP                        |

If multiple are present, identify the primary language by line count
or ask the user. Store the detected language — it determines which
exploration commands to use in later steps.

### Step 2: Interview the User

Before exploring, ask the user these questions. All of them — don't
skip any. Present them as a numbered list and wait for answers.

1. **What does this repo do?** (Even a vague answer like "it's some
   kind of API" helps. If they have no idea, that's fine too — say so.)
2. **What's your relationship to it?** (Joining the team? Evaluating
   for adoption? Studying it to learn patterns? This shapes what the
   docs emphasize.)
3. **What do you already know about it?** (Any subsystems, patterns,
   or technologies you've already identified? This avoids redundant
   exploration.)
4. **Are there specific areas you're most interested in?** (If yes,
   those get prioritized in the deep-dive order.)

Use the answers to guide exploration focus. If the user says "I know
nothing, just analyze it," that's a valid answer — proceed with a
fully exploratory approach.

### Step 3: Explore Repository Structure

Using the language-specific commands from `references/language-detection.md`,
execute these exploration steps:

1. **Map the directory layout**
   - `find . -type d -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/vendor/*' -not -path '*/__pycache__/*' | head -80`
   - `find . -type f -name '*.{ext}' | wc -l` (for the detected language's file extensions)

2. **Read the entry points**
   - Find and read main/entrypoint files (language-specific — see detection reference)
   - Trace the boot sequence: what gets initialized, in what order

3. **Read dependency manifests**
   - go.mod / package.json / Cargo.toml / pyproject.toml / etc.
   - Categorize dependencies: core framework, HTTP/RPC, database,
     messaging, observability, testing, internal/proprietary

4. **Read configuration**
   - Config files, env examples, feature flag setup
   - How is the app configured at runtime?

5. **Scan for architectural markers**
   - Dependency injection / wire / container setup
   - Plugin or module registration systems
   - Middleware chains
   - Router or handler registration
   - Proto/OpenAPI/GraphQL schema definitions

6. **Identify subsystems**
   This is the critical output of exploration. Based on directory
   structure, package boundaries, and entry points, produce a list of
   subsystems/domains with:
   - Name
   - Directory path
   - Brief description (what it appears to do)
   - Key entry files
   - Estimated complexity (number of files, apparent depth)

   Present this list to the user for confirmation before proceeding.
   Ask: "Does this subsystem map look right? Anything missing or
   mislabeled?"

### Step 4: Produce Architecture Overview

Read `references/overview-template.md` for the full document template.

Create `docs/` directory if it doesn't exist. Write the architecture
overview to `docs/architecture-overview.md`.

Key requirements:
- Use Mermaid for ALL diagrams (```mermaid fenced blocks)
- Cite specific file paths and line numbers for every claim
- Mark uncertainty with "UNCERTAIN:" prefix
- Keep under 2000 lines
- Do NOT modify any source code — read only

After writing, tell the user: "I've produced the architecture overview.
Review it before proceeding — errors here will compound in the deep
dives."

### Step 5: Generate Deep-Dive Prompts

Read `references/deepdive-template.md` for the per-subsystem template.

For each subsystem identified in Step 3, generate a ready-to-paste
prompt file. Write them to:

```
docs/analysis-prompts/
├── README.md                    (instructions for running the prompts)
├── 01-{subsystem-name}.md       (one per subsystem, numbered)
├── ...
└── synthesis.md                 (final synthesis prompt)
```

**README.md** should contain:
- Brief explanation of the workflow
- Instructions: "Run each prompt below as a SEPARATE Claude Code
  session. One session per file. Run them in numbered order."
- A checklist the user can mark off as they complete each one
- Reminder to review and correct each doc before running the next

**Each numbered prompt file** should contain:
- The full prompt text, ready to copy-paste into a new Claude Code
  session
- The subsystem name, directory path, and description filled in
  from Step 3
- Reference to docs/architecture-overview.md so the deep dive has
  the high-level context
- All sections from the deep-dive template, customized to this
  specific subsystem
- Language-specific exploration commands appropriate for this
  subsystem

**synthesis.md** should contain the Phase 3 prompt from
`references/synthesis-template.md`.

**Ordering the prompts:** Use this priority logic:
1. Subsystems the user said they're most interested in (from Step 2)
2. Core/foundational subsystems that others depend on
3. Entry point subsystems (what handles external requests)
4. Supporting subsystems (utilities, config, observability)
5. Lowest priority: generated code, vendor code, test infrastructure

### Step 6: Present Results

Tell the user exactly what was created and what to do next. Example:

"Done. Here's what I produced:

- `docs/architecture-overview.md` — high-level architecture with
  Mermaid diagrams
- `docs/analysis-prompts/` — {N} deep-dive prompts, one per subsystem

Next steps:
1. Review `docs/architecture-overview.md` and fix any errors
2. Open `docs/analysis-prompts/README.md` for instructions
3. Run each numbered prompt in a fresh Claude Code session
4. After all deep dives, run `synthesis.md` to produce the index
   and lessons doc"

## Rules (apply throughout)

- Do NOT modify, reformat, or refactor any source code. Read only.
- Use Mermaid for all diagrams.
- Cite file paths and line numbers for every architectural claim.
- Flag uncertainty explicitly — never guess at behavior.
- When encountering proprietary/internal libraries, explain based on
  usage context rather than assuming implementation.
- Adapt exploration commands to the detected language (see
  `references/language-detection.md`).
