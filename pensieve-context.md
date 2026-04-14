# Code Pensieve — Context Dump for New Agents

> **Read this AND `PLAN.md` before doing anything.** PLAN.md is the
> canonical plan and tracker. This file captures everything else: user
> profile, mechanism story, benchmark history, design rejections, and
> operational guidance that's not in PLAN.md.

## Onboarding sequence (read in this order)

1. **`PLAN.md`** at repo root — vision, design principles, 4-phase plan
   with checkbox milestones, proceed criteria, decisions log, lessons
   carried in from v1, working agreements. **This is canonical. When in
   doubt, PLAN.md wins.**
2. **`pensieve/README.md`** — directory layout for v2 and the rationale
   for why v2 exists alongside v1.
3. **`builder-agent-ethics.md`** — operating guidelines for all agent
   work on this project. Treat code/tests/schema/plan as separate
   contracts, don't mark complete because happy-path tests pass, prefer
   smaller correct slice, add regression tests for realistic edge cases,
   assume work will be audited.
4. **This file** — everything not in PLAN.md.
5. **Pick the next pending milestone in PLAN.md** and execute it.
6. **Update PLAN.md** as you work: tick the milestone checkbox `[x]`,
   add a one-line completion note in the milestone bullet, append to
   the Phase Notes section, and update the Status header at the top.

## Who you're working with

- **Name:** Lalit Verma
- **Team:** Zomato engineering
- **Build partners:** Lalit + you (an AI coding agent). One teammate is
  running external benchmarks as QA on the Phase A auto-benchmark — see
  "Teammate context" below.
- **Mode:** Side / focused build. Iterative. Long-term commitment to a
  meaty problem. Not time-boxed.

### Communication preferences (very important — match these)

| Do | Don't |
|---|---|
| Lead with the answer or action | Preamble like "Great question! Let me think..." |
| Use pros/cons tables when presenting options | Walls of prose listing options |
| Always include a recommendation alongside options | Present options without taking a stance |
| Push back when you disagree, with reasoning | Sycophancy, hedging, "you're absolutely right" reflex |
| Ask when unsure rather than guess | Make assumptions on judgment calls |
| Be honest about regressions and failures | Hide bad news in qualifications |
| Use file:line references for code | Vague references like "in the auth code" |
| Update PLAN.md after each milestone | Rely on chat memory for state |
| Keep responses tight | Recap what you just did unless asked |

### Hard rules from prior conversation

- **No time estimates.** Lalit pushed back hard on "3 months of focused
  work" framing. Plan in milestones and proceed criteria, not weeks.
- **No ceremonial trailing summaries.** "I just did X, then Y, then Z"
  closings get cut.
- **No emojis** unless explicitly asked.
- **Pros/cons + recommendation** is a saved memory preference. Apply it
  whenever presenting choices.
- **Honest about failure.** When a measurement says the framework is
  losing to baseline, say so directly. Don't soften it.

### Stored memory entries (active across sessions)

- `feedback_options_format.md`: when presenting choices, include
  trade-offs and a recommended pick.

---

## Current state (as of 2026-04-10)

### Progress summary

| Phase | Status | Milestones |
|---|---|---|
| **A** Hooks + auto-benchmark | A1-A11 complete, A12-A15 remaining | Hook installer, benchmark templates, runner, metrics, history done |
| **B** AST extraction | Layer 1 complete (B1-B13), Layer 2 pending (B14-B17) | 6-language extractors, schema, cache, scanner, cross-file graph done |
| **C** Multi-repo | Not started | |
| **D** MCP, polish, distribution | Not started | |

### Test coverage

- **657 test functions** across **31 test files**
- All passing (verified at each milestone)
- Includes regression tests from 8+ review rounds with Codex as external reviewer

### Next milestone: A12

`pensieve benchmark run` CLI — wires the benchmark runner, metrics
aggregation, and history generator into the CLI entry point.

---

## The two-line history

v1 was a markdown-based codebase documentation generator. Benchmarks
showed it lost to a baseline of "no agent-docs at all" on cost AND pass
rate across multiple wiring iterations. **Code Pensieve (v2) is a
rebuild that fixes the structural issues v1 couldn't fix with wiring
alone.**

## Why v1 lost — the mechanism story

This is the most important technical context in this file. Internalize
it before making design calls.

### The cost mechanism: long-context fallback

Claude Code does **not** implement a per-turn complexity router. Lalit's
teammate read the CLI source to confirm this. Model selection is driven
by:

1. User / subscription defaults and aliases
2. Plan-mode upgrade from Haiku to Sonnet
3. **Provider-specific fallbacks (e.g., long-context fallback when
   conversation exceeds the smaller model's context window)**
4. Fixed per-feature defaults for side queries

The cost regression in v1's full-load wiring was almost certainly
**long-context fallback**. Haiku 4.5 has a ~200K context window. Sonnet
has 1M. When the agent loaded `agent-context.md` + multiple subsystem
docs + `patterns.md` + `decisions.md`, the conversation accumulated past
~200K within a few turns and the provider fell back to Sonnet (which
costs ~5x more per token).

**Implication:** any wiring that puts agent-docs content into main-thread
context will eventually trigger fallback. The fix is to inline only the
load-bearing content into the system prompt (where it's paid for once and
never accumulates) and use harness-enforced wiring (PreToolUse hooks) to
remind the agent of the rest.

### The quality mechanism: pattern fidelity on the writer

The Medium-bucket benchmark win in v1's full-load runs came from the
**main thread internalizing pattern conventions** before generating code.
When patterns were the actual text in the agent's context, the writer
reproduced them with verbatim fidelity.

When the explore-routing experiment moved doc reads into a subagent,
the main thread saw only summaries of patterns. Strict pass on Medium
fell from 30% to 10%; lenient pass collapsed from 70% to 30%.
**Subagent summarization loses load-bearing detail.**

**Implication:** patterns must reach the writer verbatim. The only way
to do this without triggering long-context fallback is to inline them
into the system prompt, where they're paid for once and never accumulate.

---

## Benchmark history — the numbers

Three benchmarks were run on the same 30-task suite (10 Easy, 10
Medium, 10 Difficult) on the same calibration repo.

| Run | Avg tokens | Avg cost | Avg time | Quality | Lenient pass | Verdict |
|---|---|---|---|---|---|---|
| **Full-load wiring (original)** | 1.57M | $1.07 | 3.59m | 7.17 | 46.7% | Cost +11%, lenient -3.3pp vs baseline |
| **Lean wiring (post-Step1-5 ritual cut)** | similar | similar | similar | similar | similar | No meaningful change vs full-load |
| **Explore-routed (subagent reads docs)** | 1.80M | $0.843 | 4.16m | 6.83 | 36.7% | Cost -13% but tokens +2%, quality -0.47, lenient -13.3pp |
| **Baseline (no agent-docs at all)** | 1.76M | $0.965 | 3.75m | 7.30 | 50.0% | Reference |
| **Hybrid wiring v3 (nano + hook)** | ~1.67M | $0.861 | ~3.38m | 7.50 | 56.6% | tokens -5%, cost tied, time -10%, quality +0.20, lenient +6.6pp |

**Key result:** Hybrid wiring v3 beats baseline on ALL axes. This
validated Phase A's proceed criterion and green-lit Phase B.

---

## What's been built (Layer 1 Python package)

### Package structure

```
pensieve/python/
  pyproject.toml                    hatchling build, code-pensieve package
  src/pensieve/
    __init__.py                     package root
    __main__.py                     python -m pensieve entry
    _version.py                     EXTRACTOR_HASH (SHA256 of extractors + schema)
    cli.py                          argparse CLI with subcommands
    schema.py                       8 dataclasses, validate_extraction()
    cache.py                        ExtractionCache (SHA256+ext key, EXTRACTOR_HASH invalidation)
    scan.py                         scan_repo() with os.walk pruning, error channel
    graph.py                        build_graph() — import/call/test edges
    hooks.py                        install_hook()/uninstall_hook() for Claude Code
    extractors/
      __init__.py                   lazy-loading registry, 11 extensions
      _comments.py                  shared rationale comment extraction
      python.py                     Python extractor
      javascript.py                 JS extractor (.js/.mjs/.cjs)
      typescript.py                 TS extractor (.ts/.tsx), extends JS
      go.py                         Go extractor
      java.py                       Java extractor
      rust.py                       Rust extractor
    benchmark/
      __init__.py
      template.py                   TaskTemplate + CheckerSpec + validate_template()
      tasks.py                      5 task templates with parameterized instructions
      runner.py                     PlaceholderFiller, run_task, run_benchmark
      metrics.py                    ModeStats, Deltas, compute_verdict, aggregate_metrics
      history.py                    append_to_history() markdown table generator
  tests/
    conftest.py
    test_cli.py                     CLI smoke tests
    test_tree_sitter.py             tree-sitter import and basic parsing
    test_language_parsers.py        6-language parser verification
    test_schema.py                  schema validation, round-trip, edge cases
    test_extractor_python.py        Python extractor
    test_extractor_javascript.py    JS extractor
    test_extractor_typescript.py    TS extractor
    test_extractor_go.py            Go extractor
    test_extractor_java.py          Java extractor
    test_extractor_rust.py          Rust extractor
    test_comments.py                rationale comment extraction
    test_cache.py                   cache layer
    test_scan.py                    scanner
    test_graph.py                   cross-file graph builder
    test_hooks.py                   hook install/uninstall
    test_benchmark_template.py      template format and validation
    test_benchmark_tasks.py         5 task templates
    test_benchmark_runner.py        runner integration
    test_benchmark_modes.py         mode isolation
    test_benchmark_metrics.py       metrics aggregation + verdict
    test_benchmark_history.py       history generator
    test_anon_default_export.py     anonymous callable default exports
    test_reexports.py               JS/TS re-export import edges
    test_type_import_and_default_ts.py  TS-specific type import + default export
    test_codex_review_fixes.py      regression tests from Codex reviews
    test_review_round2_fixes.py     round 2 review regressions
    test_review_round3_fixes.py     round 3 review regressions
    test_phase_b_review_fixes.py    Phase B review regressions
    test_final_b_review.py          final Phase B review regressions
    test_a8_a9_review_fixes.py      A8/A9 review regressions
    test_phase_a_review_fixes.py    Phase A review regressions
```

### Key architectural decisions in the code

**Extractors:**
- Multi-pass architecture (declarations -> call edges -> comments)
- Lazy-loading registry: one broken module doesn't take down others
- 11 extensions: .py .js .mjs .cjs .ts .tsx .go .java .rs
- `self.method()` / `this.method()` calls stripped to just `method`
- Namespace imports: `names=["*"]` (distinguishes from default imports)
- Anonymous callable defaults: `Export(name="<default>")`, no synthetic Symbol
- Named-import aliases tracked as separate Import records for graph resolution

**Graph (`graph.py`):**
- Module resolution: absolute, dotted, relative (Python + JS/TS path-style)
- Ambiguous stems -> no edge (not a wrong edge). No false positives.
- Import edges: module-level, deduped by (source, target)
- Call edges: function-level, NOT deduped
- Test edges: module-level, deduped. Test->test imports filtered
- Default-import calls: only when target has callable default export
- Type-only imports (`import_type`) excluded from call resolution
- `import_count` = unique modules, not Import records

**Cache (`cache.py`):**
- Key: `{sha256}_{ext}.json` (same content, different lang = separate entries)
- Invalidation: EXTRACTOR_HASH (SHA256 of all extractor + schema source files)
- Invalid entries -> cache miss + warning, not crash

**Benchmark:**
- Mode isolation via `shutil.copytree` — original repo never modified
- PlaceholderFiller reads `structure.json`, excludes test dirs from heuristics
- Verdict: PASS (cost <= baseline AND lenient >= baseline+5pp AND quality >= baseline AND no errors), FAIL (cost > 105% AND lenient < baseline), MIXED (everything else)
- Task breakdown: index-based pairing, preserves duplicate template instances
- History: appends row to existing markdown table, preserves prose around table

**Hooks (`hooks.py`):**
- Writes PreToolUse hook to `.claude/settings.json`
- Uses `hookSpecificOutput.additionalContext` JSON mechanism (NOT stdout)
- Identity by exact command match (`_OUR_COMMAND`), not substring

---

## graphify deepdive — what we adopted

Lalit pointed me at `/Users/lalit.verma@zomato.com/Desktop/tinkering/graphify-3`,
a Python skill that solves a similar problem with a different architecture.

### Adopted from graphify

| What | Why | Phase |
|---|---|---|
| **PreToolUse hook in `.claude/settings.json`** | Harness-enforced wiring, ~30 tokens per Glob/Grep, only when docs exist | A (done) |
| **AST-first extraction with tree-sitter** | 71.5x token reduction vs LLM extraction. Free, deterministic, perfect recall | B (Layer 1 done) |
| **SHA256 incremental cache** | Re-runs only re-process changed files | B (done) |
| **Auto-measured benchmark per run** | Catch regressions per-repo, not via external benchmarks weeks later | A (partially done, A12 next) |
| **Worked examples with honest `review.md` files** | Trust comes from publishing failure modes alongside wins | D |
| **Continuous confidence scores (0.0-1.0)** | More expressive than categorical labels | B (done, on call edges) |
| **MCP server for structured runtime queries** | Agents query artifact directly without reading markdown | D |
| **Multi-platform skill files from single source** | Prevent drift across Claude Code / Codex / Cursor variants | D |

### NOT adopted from graphify

| What | Why not |
|---|---|
| Multi-modal extraction (PDFs, images) | We're a code framework. Scope creep. |
| Leiden community detection / graph clustering | Our subsystem identification is human-confirmed with named architectural concepts |
| Persistent graph + query DSL as primary output | Different paradigm. We keep markdown + JSON |
| `--watch` mode | Our re-run cadence is per-major-refactor, not live sync |
| Hyperedges / embeddings / BFS subgraph queries | Graph-shape features our markdown shape doesn't need |

### Our moat (things graphify doesn't have)

| What | Why it matters |
|---|---|
| **Pattern recipes** | The Medium-bucket benchmark win. Tells the writer how to extend, not just what exists |
| **`Conventions` section with file references** | Uncaptured by topology-only analysis |
| **`Do NOT` / anti-patterns list** | Prevents common mistakes graphify can't detect |
| **`decisions.md` for architectural trade-offs** | First-class trade-off structure vs comment-only rationale |
| **Chat-first checkpoint** | Catches misclassification before durable docs are written |

---

## v1 -> v2 transition state

v1 lives in the same repo at `shared/`, `claude-code/`, `codex/`,
`cursor/`. **Don't touch these directories** unless explicitly asked —
they're the fallback if v2 stumbles.

The v1 hybrid wiring ships an `agent-context-nano.md` file (<=40 lines)
that's a strict subset of `agent-context.md`, designed to be pasted
directly into CLAUDE.md / AGENTS.md / .cursorrules. This format carries
forward to v2 — the nano-digest design is good, the issue v1 had was
that it didn't ALSO ship a PreToolUse hook to remind agents the rest of
the docs exist.

---

## Active open questions (need user input before some milestones)

| Question | Blocks | Notes |
|---|---|---|
| **Name and path of the calibration repo** | A13 | Same repo + same 30 tasks the teammate has been benchmarking externally |
| **Teammate's contact / coordination protocol** | A14 | Need the teammate's most recent benchmark numbers to validate against |
| **PyPI package name reservation timing** | D8 | Decision deferred until after Phase C. Internal-first for A-B |

## Things explicitly decided against (don't re-litigate)

| Rejected | Reason |
|---|---|
| 5-step "before every task" loading ritual | Tested in v1. Triggered cost regression with no quality gain |
| "Quote the specific pattern from patterns.md" requirement | Forced extra reasoning turns without improving pass rate |
| "Do not skip steps" framing | Cost driver, not quality driver |
| Pure subagent routing for all doc reads | Fixed cost but tanked Medium-bucket lenient pass from 70% to 30% |
| Reading agent-docs/ files from the main thread | Triggers long-context fallback |
| Time-boxed phases / week estimates | Lalit pushed back. Milestone-driven |
| Embeddings / vector search | Graph topology + AST structure is enough |
| Auto-running benchmark by default | Cost ($0.50-$2 per run). Opt-in via `--benchmark` flag |

---

## Critical gotchas that will surprise a fresh agent

1. **Don't accumulate context in main-thread reads.** The single biggest
   v1 lesson. If you find yourself thinking "the agent should read
   `agent-docs/foo.md`," stop. Either inline what's needed into the nano-
   digest or make it accessible via Explore subagent / MCP server / hook
   reminder.

2. **The Medium bucket is the canary.** Watch lenient pass rate on Medium-
   difficulty tasks. If it drops, pattern fidelity has been broken.

3. **The PreToolUse hook is harness-enforced, not LLM-instructed.** It's
   installed in `.claude/settings.json`, fires before Glob/Grep, and uses
   `hookSpecificOutput.additionalContext` JSON. The agent doesn't choose
   to trigger it.

4. **AST extraction is free; LLM extraction is expensive AND worse.**
   Default to: "if it can be extracted by tree-sitter, the LLM should
   not be doing it."

5. **The chat-first checkpoint is preserved from v1.** Even with AST
   extraction, the user must confirm the subsystem map before any
   durable doc is written.

6. **Two load-bearing artifacts: nano + patterns.** Everything else is
   either supporting these or human-readable secondary docs.

7. **v1 directories are FALLBACK, not legacy.** Don't refactor or "clean
   up" `shared/`, `claude-code/`, `codex/`, `cursor/`.

8. **Lalit's teammate is doing external benchmarks in parallel.** Don't
   assume our auto-benchmark replaces theirs. The two should converge
   within ~10% before we trust the auto-benchmark alone.

9. **Review-driven development.** Every milestone gets reviewed by Codex
   as an external reviewer. Regression tests are added for every finding.
   This is why the test count is high relative to the code volume.

10. **builder-agent-ethics.md is an operating guideline.** Treat it as a
    contract, not advice. Key rules: code and tests are separate
    deliverables, don't mark complete because happy-path passes, prefer
    smaller correct slice over larger incorrect one, add regression tests
    for realistic edge cases, assume your work will be audited.

---

## Operational guidance

### Use the task tool, but PLAN.md is canonical

The Task tool is for in-session tracking. PLAN.md is for cross-session
state. Update PLAN.md after every milestone, including:

- Tick the checkbox `[x]` on the completed milestone
- Add a one-line completion note in the milestone bullet
- Append a note to the Phase Notes section
- Update the Status header at the top
- Append to Decisions log if a new decision was made
- Append to Kill criteria results if a kill criterion was hit

### Dev environment

- **Python 3.12** managed by `uv` (not system Python)
- Create venv: `uv venv .venv --python 3.12`
- Install: `uv pip install --python .venv/bin/python -e ".[dev]"`
- Tests: `cd pensieve/python && .venv/bin/pytest tests/ -q`
- Do NOT use `python3 -m venv` on this machine (uv-managed Python is
  PEP 668 externally-managed, it will fail)

### When to ask vs when to just do

- **Just do:** well-scoped milestones from PLAN.md
- **Ask first:** decisions that affect file layout, breaking changes,
  destructive operations, anything that touches v1 directories
- **Push back when you disagree:** if a milestone seems wrong given
  what you've discovered, say so

### When the benchmark says we're losing

1. Record the failure in the kill criteria results table in PLAN.md
2. Don't proceed to the next phase
3. Iterate on the failing milestones
4. If iteration doesn't move the number, surface to Lalit

Don't rationalize a regression as "well, this metric isn't really
representative."

---

## Key bugs fixed during development (for pattern awareness)

These represent the types of issues that recur. New code in the same
areas should be watchful:

- **Circular imports:** `_version.py` importing `pensieve.extractors`
  caused circular dependency. Fixed by using `__file__` paths only.
- **Language-specific AST surprises:** Go `parameter_list` for return
  types entering the param branch, TS `export` not knowing about
  interfaces/types/enums, Java `asterisk` as separate AST child for
  wildcard imports, Rust `use_as_clause` for aliases.
- **Graph false positives:** Last-segment fallback resolving `pkg.bar`
  to wrong `other/bar.py`, ambiguous stems (`utils.py` in multiple
  packages), extension priority in mixed-language directories.
- **Mode contamination:** Framework mutations leaking into baseline
  runs (fixed with `shutil.copytree` isolation).
- **Identity matching:** Hook identity using substring match catching
  unrelated hooks (fixed with exact command match).

---

**Final note:** if anything in this file conflicts with PLAN.md, PLAN.md
wins. This file is a context supplement, not a replacement.
