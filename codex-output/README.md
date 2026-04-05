# Codebase Analysis Protocol Bundle

This folder contains a reusable, evidence-first codebase analysis
protocol with two wrappers:

- `shared/` - the canonical protocol, confidence rules, and durable
  documentation schema
- `codex/` - a Codex skill wrapper
- `claude-code/` - a reusable `CLAUDE.md` wrapper for Claude Code

Design goals:

- optimize for durable architecture documentation, not code changes
- stay read-only and structural by default
- remain chat-first until the user explicitly approves writing docs
- ask for clarification whenever confidence is too low
- work across applications, libraries, SDKs, frameworks, and monorepos

Recommended usage order:

1. Read `shared/protocol.md`
2. Read `shared/docs-schema.md`
3. Read `shared/references/checkpoint-template.md`
4. Read `shared/references/subsystem-mapping-rubric.md`
5. Use either `codex/SKILL.md` or `claude-code/CLAUDE.md`

The wrappers are intentionally concise. The shared files are the source
of truth for behavior, checkpoints, and output structure.

Portability notes:

- `codex/` contains the Codex wrapper, but the highest-quality version
  of the workflow depends on the shared playbooks and templates in this
  bundle.
- `claude-code/CLAUDE.md` is self-contained so it can be dropped into a
  repo directly.
- `shared/` is the canonical spec for maintaining both wrappers in sync.

What changed in this bundle:

- `shared/references/` now contains the operational playbooks that
  reduce output variance across ecosystems and repo sizes.
- `shared/templates/` now contains durable document templates rather
  than only a high-level schema.
- `shared/examples/` contains concrete exemplars so the agent has a
  target level of rigor and structure.
