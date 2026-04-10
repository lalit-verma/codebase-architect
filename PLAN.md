# Code Pensieve — Build Plan

> **Status:** Phase A: A1–A12b complete, A13 provisional; Phase B: Layer 1 complete, Layer 2 = v1 prompts + Layer 1 evidence (pensieve scan → v1 slash commands). `pensieve analyze` removed.
> **Last updated:** 2026-04-11
> **Owners:** Lalit + Claude (collaborative build)

A vessel for codebase memories. Coding agents draw from the store on demand
instead of re-experiencing the original event.

---

## Vision

Build a cost-measured, AST-extracted, harness-wired codebase context tool
whose only justification for existing on any given repo is a measured
improvement in coding-agent **cost**, **time**, or **quality** on that
specific repo. Single source of truth. Derived views. Incremental by default.
Multi-repo as a first-class scope. Honest about failure modes. Ship
measurements, not promises.

The objective: **make coding agents measurably more cost-efficient, faster,
and higher-quality on any target codebase.**

---

## Design principles (the constitution)

Every design decision must satisfy these. If a feature doesn't pass all of
them, it doesn't ship.

1. **Measure-first.** Every output is justified by a measured contribution
   to cost, time, or quality on the host repo.
2. **AST before LLM.** Spend LLM tokens only on interpretation, never on
   enumeration.
3. **Wiring via harness, not via instructions.** PreToolUse hooks where
   available. Inlined content in agent config as the second mechanism.
   Never rely on agent compliance with prose instructions alone.
4. **Single canonical artifact, derived views.** One structured store
   (JSON), with markdown / nano / HTML views generated from it.
5. **Incremental by default.** SHA256 cache on every artifact. Re-runs are
   nearly free. Auto-rebuild on commits where supported.
6. **Multi-repo as a first-class scope.** Architecture must support N-repo
   context from day one. Single-repo ships first; multi-repo is the
   convergence.
7. **Honest about failure modes.** Worked examples with `review.md` files
   listing what we got right AND wrong.

---

## Architecture (three layers)

```
LAYER 3: Wiring & Distribution
  - PreToolUse hooks (Claude Code first; others as platforms add support)
  - Inlined nano-digest in CLAUDE.md / AGENTS.md / .cursorrules
  - MCP server (optional, for structured queries)
  - Multi-platform skill / command files

LAYER 2: LLM Orchestration
  - Slash commands / skills with chat-first checkpoint (preserve v1 strength)
  - LLM passes for: subsystem naming, recipe synthesis, decision extraction,
    anti-pattern detection, nano-digest distillation
  - Reads structural skeletons from Layer 1, never raw files in bulk

LAYER 1: Python Core (deterministic, no LLM)
  - File detection + ignore patterns + repo root detection
  - Tree-sitter AST extraction (Python, JS, TS, Go, Java, Rust)
  - Call graph + import graph + module dependency graph
  - Rationale comment extraction (# WHY:, # NOTE:, # HACK:, # IMPORTANT:)
  - SHA256 incremental cache
  - Benchmark runner (with-framework vs baseline)
  - Hook installer per platform
  - MCP server endpoint
```

The inversion vs v1: v1 had the LLM doing both extraction and interpretation.
v2 extracts deterministically and only spends LLM tokens on interpretation,
naming, and prioritization.

---

## Output schema (what Pensieve produces in `agent-docs/`)

```
agent-docs/
  .cache/                      SHA256-keyed extractions, one per file
  structure.json               AST extraction (Layer 1 output)
  graph.json                   import graph + call graph + subsystem graph
  agent-context-nano.md        ★ inlined into CLAUDE.md (load-bearing)
  agent-context.md             full compact context for Explore subagents
  patterns.md                  ★ prescriptive recipes (our moat)
  decisions.md                 extracted from comments + LLM synthesis
  uncertainties.md             gaps with continuous confidence scores
  subsystems/{name}.md         LLM deep dives, fed AST skeleton
  flows/{name}.md              cross-cutting flows (optional)
  benchmark.json               per-run cost/time/quality measurements
  benchmark-history.md         trends across re-runs
  agent-protocol.md            wiring instructions per platform
  .analysis-state.md           internal state
```

The two load-bearing artifacts are `agent-context-nano.md` (inlined into the
agent's system prompt) and `patterns.md` (prescriptive recipes for adding
new code). Everything else either supports these or is for human reference.

---

## Phases overview

| Phase | Goal | Status |
|---|---|---|
| **A** | Hooks + auto-benchmark | A1–A12b complete. A13 provisional (infra validated, awaiting v2 docs). A14–A15 blocked on A13. |
| **B** | AST extraction + evidence for v1 doc generation | Layer 1 complete (B1–B13). Layer 2: v1 prompts + Layer 1 evidence. `pensieve scan` provides structural data, v1 slash commands generate docs. B15–B16 next. |
| **C** | Multi-repo support | not started |
| **D** | MCP, multi-platform, polish, distribution | not started |

## Execution order (revised 2026-04-10)

Original plan: A → B → C → D (sequential).

Revised order:

1. **Phase B** (AST extraction) — now. The biggest cost lever. Wiring
   is validated; the next dramatic improvement comes from replacing
   LLM extraction with deterministic tree-sitter parsing.
2. **Phase A remainder** (A3–A15: hook CLI + auto-benchmark runner) —
   after Phase B. Gives us self-measurement for Phase C onward.
3. **End-to-end testing** — validate A + B together on the calibration
   repo via the teammate's external benchmark AND (once built) the
   auto-benchmark.
4. **Phase C** (multi-repo)
5. **Phase D** (polish, distribution)

Why reorder: Phase A's proceed criterion was met early via the
teammate's external benchmark (v3: lenient +6.6pp, cost tied, quality
+0.20). The remaining Phase A work (programmatic hook installer +
auto-benchmark runner) is stable-scope tooling that won't change based
on Phase B's findings. Phase B is higher-value-per-unit-of-work right
now. The teammate's external benchmark covers measurement needs during
Phase B; we build self-measurement capability (auto-benchmark) before
Phase C, where cross-repo tasks require new benchmark templates the
teammate doesn't have yet.

---

---

## Phase A — Hooks + auto-benchmark

**Goal.** Validate the wiring layer (PreToolUse hook + the existing hybrid
nano) on the calibration repo before investing in any other rebuild work.
If the wiring layer alone moves the benchmark, we know the foundation is
sound and the AST rebuild is worth doing. If it doesn't, we audit the
content layer before building anything else.

**Why first.** Highest leverage per unit of work. Independent of the AST
rebuild — the Python package can ship a hook installer and a benchmark
runner without any extraction logic. Generates the measurement
infrastructure we need for every subsequent phase.

### Milestones

- [x] **A1.** Scaffold `pensieve/` directory inside the current repo.
  Inside it: `python/` (the package), `commands/` (slash commands that
  wrap the CLI), `templates/`, `references/`, `examples/`, `worked/`,
  `tests/`. *(2026-04-08: directories created with `.gitkeep`
  placeholders, `pensieve/README.md` written explaining the layout and
  v2 rationale, points at `PLAN.md` as canonical source of truth.)*
- [x] **A2.** Create the Python package skeleton: `pyproject.toml` with
  `code-pensieve` package name, `pensieve` CLI entry point, basic
  `__main__.py`, test scaffolding with pytest. *(2026-04-08: hatchling
  build backend, src/ layout, argparse-based CLI with --version/--help
  and empty subparser ready for A3+. Verified end-to-end via `uv venv
  --python 3.12` + `uv pip install -e ".[dev]"`: 8/8 pytest tests pass,
  `pensieve --version` and `python -m pensieve --version` both print
  `code-pensieve 0.0.1`.)*
- [x] **A3.** Implement `pensieve hook install --platform claude` —
  writes a PreToolUse hook to `.claude/settings.json`. Hook fires on the
  `Glob|Grep` matcher and emits a reminder when
  `agent-docs/agent-context-nano.md` exists.
- [x] **A4.** Implement `pensieve hook uninstall --platform claude` —
  cleanly removes the hook entry from `.claude/settings.json`.
- [x] **A5.** Smoke test: in a test repo with `agent-docs/` present,
  manually trigger Glob and verify the hook fires and the reminder
  appears in the agent's context.
- [x] **A6.** Define the auto-benchmark task template format. JSON schema:
  template name, instruction template, expected output checker (strict +
  lenient), simulated repo modifications, success criteria. *(2026-04-10:
  `src/pensieve/benchmark/template.py` with TaskTemplate + CheckerSpec +
  validate_template(). 5 checker types (file_exists, symbol_exists,
  pattern_followed, content_contains, llm_judge), 7 task types, 3
  difficulties. Parameterized instructions with placeholders. Setup
  actions for repo modification. Full JSON round-trip. 28 tests.
  490/490 total tests pass.)*
- [x] **A7.** Implement 5 task templates (the Phase A subset):
  - `add_handler` — write a new instance of the most-common file pattern
  - `add_test` — write a test for an existing file
  - `bug_fix_localized` — fix a planted bug in a single function
  - `find_owner` — answer "which subsystem owns file X and what
    conventions apply"
  - `cold_navigation` — open-ended question requiring repo exploration
  *(2026-04-10: `src/pensieve/benchmark/tasks.py` with 5 TaskTemplate
  instances. Each has parameterized instruction with documented
  placeholders, strict checker (file_exists/content_contains), and
  lenient checker (llm_judge). DOCUMENTED_PLACEHOLDERS frozenset for
  validation. Registry with get_all_templates/get_template_by_name.
  49 tests covering validation, serialization, placeholder inventory,
  registry, and per-template spot checks. 578/578 total tests pass.)*
- [x] **A8.** Implement the baseline runner — runs each task without any
  `agent-docs/` present, measures tokens, cost, time, strict pass.
  Lenient pass and quality score populated by LLM judge (A12b).
  *(2026-04-10, updated after review: PlaceholderFiller (reads
  structure.json, excludes test dirs from pattern/subsystem heuristics),
  run_strict_check (file_exists, content_contains, symbol_exists),
  TaskResult dataclass, Executor protocol, run_task orchestrator.)*
- [x] **A9.** Implement the with-framework runner — runs each task with
  the hybrid wiring + PreToolUse hook installed. *(2026-04-10:
  setup_baseline (hides agent-docs, uninstalls hook),
  setup_framework (ensures scan + installs hook), teardown_baseline
  (restores agent-docs), run_benchmark orchestrator (both modes,
  all templates, auto-scan if needed). BenchmarkResult dataclass.
  16 tests. 633/633 total tests pass.)*
- [x] **A10.** Implement metrics aggregation: `benchmark.json` schema with
  `with_framework` + `baseline` + `deltas` + `verdict` (PASS / MIXED /
  FAIL). *(2026-04-10: `src/pensieve/benchmark/metrics.py` with
  ModeStats, Deltas, compute_verdict (PASS/MIXED/FAIL), aggregate_metrics,
  write_benchmark_json. Per-task breakdown pairs both modes. Handles
  empty results and error exclusion. Post-review fix: aggregate_metrics()
  raises ValueError when exactly one side is empty — comparative metrics
  are meaningless without both modes. Both-empty still allowed (MIXED).
  21 tests. 700/700 total pass.)*
- [x] **A11.** Implement `benchmark-history.md` generator — appends each
  run's summary so successive re-runs show trends. *(2026-04-10:
  `src/pensieve/benchmark/history.py` with append_to_history(). Creates
  markdown table on first run, appends row per subsequent run. Columns:
  date, verdict, cost/lenient/quality/tokens/time deltas, task count.
  Never overwrites existing content. Post-review fix: table detection
  requires header+separator as adjacent pair (header-only not treated
  as table); row insertion tracks contiguous pipe-line block only
  (pipe-prefixed prose after table not confused with table rows).
  17 tests. 700/700 total pass.)*
- [x] **A12.** Implement the CLI: `pensieve benchmark run --repo <path>
  --tasks all --baseline --with-framework`. *(2026-04-10:
  `benchmark run` subcommand in cli.py. Flags: --repo, --tasks (all or
  comma-separated names), --baseline, --with-framework, --output-dir.
  Neither mode flag → both run. Template validation with available-names
  error. Executor loaded via pluggable `pensieve.benchmark.executor`
  module (ImportError → clear message pointing to A13). On success:
  calls run_benchmark → aggregate_metrics → write_benchmark_json →
  append_to_history, prints verdict summary. Post-review fixes:
  single-mode invocation rejected (comparative artifacts need both
  modes), help strings updated. REWORKED in A13: CLI now uses
  generated TaskInstance path (`benchmark generate` + `benchmark run
  --tasks-file`). Old static-template path deprecated. 855/855 total
  pass.)*
- [x] **A12a.** Implement the Claude Code subprocess executor and
  per-task progress logging. *(2026-04-10:
  `src/pensieve/benchmark/executor.py` with ClaudeCodeExecutor. Invokes
  `claude -p --output-format json --permission-mode auto
  --no-session-persistence`. Parses JSON output for response, tokens
  (input+output+cache_read+cache_creation), cost (total_cost_usd),
  timing (duration_ms). Configurable: model, budget cap, permission
  mode, timeout, extra args. Factory function create_executor() for
  CLI import. Error handling: timeout, claude not found, empty stdout,
  invalid JSON, Claude Code error response. Post-review fix: non-zero
  subprocess exit code treated as failure even if stdout has parseable
  JSON — preserves partial data but marks as error with exit code and
  stderr. Progress callback added to run_benchmark() with flushed
  per-task logging in CLI. 23 tests. 743/743 total pass.)*
- [x] **A12b.** Implement the LLM judge for lenient pass and quality score.
  *(2026-04-10: `src/pensieve/benchmark/judge.py` with judge_task().
  Invokes `claude -p --output-format json --json-schema --bare --model
  sonnet` for cost-efficient evaluation. Returns JudgeResult with
  lenient_pass (bool), quality_score (0-10), reasoning, error.
  Structured output via --json-schema (verdict PASS/FAIL + quality +
  reasoning). Fallback parsing when structured_output missing. Wired
  into run_task via run_judge flag (default False, CLI passes True).
  run_benchmark propagates run_judge/judge_model to all run_task calls.
  Executor also updated: flags 0-token/0-cost responses as errors.
  Runner propagates executor error into TaskResult.error. CLI --dev
  flag limits to 1 template for Phase A/B development. Post-review
  fixes: non-zero subprocess exit code in judge treated as failure,
  malformed quality field (non-numeric) degrades to 0.0 instead of
  crashing, non-dict structured_output handled, runner wraps
  judge_task() defensively with error surfaced in TaskResult.error
  (not silently swallowed). 20 tests. 743/743 total pass.)*
- [x] **A13.** Run on the calibration repo (same repo + same 30 tasks the
  teammate has been benchmarking externally). *(2026-04-10:
  Calibration repo: socrates/socrates (335 files, Python/TS/JS).
  pensieve scan completed (332 extracted, 0 failures). v1 agent-docs
  preserved alongside new structure.json + graph.json.
  Previous run (5 static templates, INVALID): benchmark design was
  structurally broken — PlaceholderFiller picked migrations dir +
  root-level utility script, setup_actions not applied, bug_fix had
  fictional bug. Results were measurement artifacts, not real data.

  A13 REWORK (2026-04-10): Complete benchmark system redesign.
  New architecture: RepoContext (deterministic from structure.json +
  graph.json) → TaskGenerator → TaskInstance (concrete, no placeholders).
  `src/pensieve/benchmark/generate.py` with:
  - RepoContext: classifies files (source/test/central/untested),
    detects pattern directories, maps test→source
  - TaskGenerator: produces TaskInstance per family (add_sibling,
    add_test, bug_fix, find_owner) with real repo targets
  - TaskInstance: concrete instruction, resolved checkers, real
    setup_actions. Serializable to generated-tasks.json
  - apply_setup_actions: write_file, delete_file, modify_file,
    mutate_function (real code mutations — swap operator, remove
    return, off-by-one)
  - Difficulty stratification: easy (add_sibling, add_test),
    medium (bug_fix), hard (find_owner)
  - Limits: max_easy/max_medium/max_hard, seed for reproducibility
  Runner updated: run_task_instance + run_generated_benchmark with
  per-task isolation (each task gets a fresh copy to prevent
  setup_action contamination across tasks).
  Validated on socrates repo: 6 concrete tasks generated — targets
  real pattern dirs (utils/, routers/, retrieval/), real functions
  (_delete_file, get_digest_items), central files (models/tools.py).
  No migrations, no fictional bugs, no root-level scripts.
  28 generation tests + 812/812 total pass.

  Additional infrastructure (2026-04-10):
  - 6 task families: add_sibling, add_test (easy), bug_fix,
    architecture (medium), find_owner, cross_subsystem (hard)
  - CLI: `benchmark generate` + `benchmark run --tasks-file`
  - Task audit report printed on generate
  - Parallel execution: --parallelism N (ThreadPoolExecutor)
  - parallelism recorded in benchmark.json metadata
  - Judge timeout increased to 180s (60s caused false zeros)
  - Enriched RepoContext: README, config files, entrypoints,
    test conventions, cross-dir edges, registration hubs
  - Parallel execution: `--parallelism N` via ThreadPoolExecutor,
    results sorted back to original order, parallelism in benchmark.json
  - Task audit: `audit_tasks()` prints why-selected, target files,
    expected artifacts, setup actions, benchmarkability for each task
  - `benchmark generate` CLI: produces + audits generated-tasks.json
  - `benchmark run --tasks-file`: runs from frozen task file
  - Judge timeout increased to 180s (60s caused false zeros)
  - 855 total tests pass.

  CALIBRATION RUN (2026-04-10, 2 tasks: 1 easy + 1 medium):
  - FW cost -1.0%, tokens +13.8%, time -0.1%, quality +0.00,
    lenient +0.0pp. Verdict: MIXED.
  - Zero errors, zero judge timeouts.
  - Per-task: add_sibling FW $0.311/60s vs BL $0.349/71s;
    bug_fix FW $0.145/27s vs BL $0.112/16s.
  - Both modes quality=1.0, lenient=FAIL on both tasks.

  A14 PRELIMINARY ANALYSIS vs teammate v3 (30 tasks):
  - Cost parity: CONSISTENT (both show ~tied)
  - Token delta: DIVERGENT (we +13.8% vs teammate -5%) —
    task design problem, not measurement bug
  - Quality/lenient: DIVERGENT (we +0.00/+0pp vs teammate
    +0.20/+6.6pp) — 2 tasks too few, tasks don't exercise
    framework's value proposition
  - Root causes: task count too small, task mix doesn't
    include navigation/convention tasks where docs help,
    public-repo familiarity effect compresses baseline gap
  - NOT a measurement bug: costs match, infrastructure works

  STATUS: A13 PROVISIONAL. Benchmark infrastructure validated.
  Measurement is working. But benchmarking v1 agent-docs is not
  the right comparison — Phase B v2 docs need to be generated
  first, then re-benchmarked. Deferring full A13 calibration
  until after Phase B Layer 2 completion.)*
- [ ] **A14.** Compare auto-benchmark results to the teammate's most
  recent external benchmark. Discrepancies are bugs in our measurement,
  not in the framework — fix them before continuing. Investigation
  checklist includes a "public-repo familiarity" ablation:
  - Hypothesis: if the calibration repo is based on a widely used public
    project (for example OpenWebUI or another heavily copied OSS codebase),
    baseline performance may already be unusually strong because the model
    has seen similar code during pretraining. This would compress the
    apparent benefit of docs/wiring without implying the docs are useless.
  - Test: compare the same frozen generated-task benchmark on
    1. a public / popular repo,
    2. a less-public or more idiosyncratic repo,
    3. tasks that depend on repo-specific conventions vs generic coding
       tasks.
  - Logging requirement: for with-framework runs, record whether the
    generated docs/context were actually consulted, so we can distinguish
    "docs not helpful" from "docs never used."
- [ ] **A15.** Iterate on hook content / positioning if Phase A's proceed
  criterion isn't met on the first run. Don't skip ahead.

### Proceed criterion (Phase A → Phase B)

Two conditions must hold:

1. **Measurement validity.** Auto-benchmark numbers correlate with the
   teammate's external benchmark within ~10% on tokens, cost, and lenient
   pass. If they diverge, our measurement layer has a bug and we must fix
   it before proceeding.

2. **Wiring earns its keep.** With hybrid wiring + PreToolUse hook, on the
   calibration repo:
   - Lenient pass rate ≥ baseline (no quality regression)
   - Cost ≤ 105% of baseline (slight cost overhead acceptable; the 13%
     regression we saw in earlier benchmarks is unacceptable)
   - Ideally: lenient pass rate > baseline by some margin, since hooks
     should give a real wiring win

If condition 2 fails after iteration on the hook content, we stop and audit
whether the content layer (the nano-digest itself) is the problem before
building Phase B's AST extractor.

### Phase A status: PROCEED CRITERION MET (2026-04-10)

Wiring layer validated by external benchmark v3 (30 tasks, 60 runs).
with-docs now leads on tokens (−5%), time (−10%), quality (+0.20),
lenient pass (+6.6pp) at cost parity ($0.861 vs $0.862). Phase B is
green-lit. Remaining Phase A milestones (A3–A15, auto-benchmark
infrastructure) can proceed in parallel with Phase B.

### Phase A notes

- **2026-04-08 (A1):** Scaffolded `pensieve/` directory with the seven
  subdirectories from PLAN. Wrote `pensieve/README.md` explaining the
  directory layout and the rationale for why v2 exists alongside v1.
  v1 framework (`shared/`, `claude-code/`, `codex/`, `cursor/`)
  preserved as fallback. No code yet — A2 lands the Python package
  skeleton.

- **2026-04-08 (A2):** Python package skeleton complete. Wrote
  `pensieve/python/{pyproject.toml, README.md, .gitignore}`,
  `src/pensieve/{__init__,__main__,cli}.py`, and
  `tests/{conftest,test_cli}.py`. Build backend: hatchling.
  CLI: argparse with `--version` and `--help`; subparser registered
  but empty (subcommands land A3+). Tests cover version constant,
  --version flag, --help flag, no-args help, unknown-command rejection,
  and `python -m pensieve` subprocess invocation.

  **Verification (8/8 tests pass):**
  - System Python is 3.8.2; package requires 3.10+. uv-managed Python
    3.12 at `~/.local/bin/python3.12`. Venv creation via `python3.12
    -m venv` failed because the uv-managed Python is PEP 668
    externally-managed.
  - Workaround: `uv venv .venv --python 3.12 && uv pip install
    --python .venv/bin/python -e ".[dev]"`. Worked first try.
  - `pensieve --version` and `python -m pensieve --version` both print
    `code-pensieve 0.0.1`. All 8 pytest tests pass in 0.05s.

  **Note for A3+ on this dev machine:** use `uv venv` and `uv pip
  install`, not `python3 -m venv` (which fails on this system due to
  uv-managed Python). The README in `pensieve/python/` documents the
  vanilla `python3 -m venv` workflow, which works on most systems —
  the uv workaround is specific to this dev environment.

- **2026-04-10 (Proceed criterion met).** Teammate's external benchmark
  v3 (30 tasks, 60 runs) shows with-docs beating baseline: tokens −5%,
  cost tied, time −10%, quality +0.20, lenient pass +6.6pp. Phase A
  proceed criterion is met. **Phase A paused** — A3–A15 deferred until
  after Phase B. Rationale: Phase B (AST extraction) is the highest-
  value-per-unit-of-work right now; the teammate's external benchmark
  covers measurement needs during Phase B; remaining Phase A work is
  stable-scope tooling that won't change based on Phase B's output.

---

## Phase B — AST extraction

**Goal.** Replace LLM-driven extraction in Phase 2 deep-dives with
deterministic tree-sitter extraction. LLM tokens are reserved for
interpretation (naming, recipes, rationale, anti-patterns, prioritization),
never enumeration (functions, classes, imports, calls).

**Why second.** Once Phase A validates the wiring layer, we attack the cost
layer. AST extraction is the single biggest cost lever (graphify's main cost
win). Having `structure.json` enables the MCP server in Phase D and is the
foundation that multi-repo cross-edge detection needs in Phase C.

### Milestones

- [x] **B1.** Add tree-sitter as a Python dependency. *(2026-04-10:
  added `tree-sitter>=0.23` + `tree-sitter-python>=0.23` to
  pyproject.toml. Installed tree-sitter 0.25.2 + tree-sitter-python
  0.25.0. Wrote `tests/test_tree_sitter.py` with 9 tests covering
  import, parsing functions/classes/imports, empty source, syntax
  errors, and line number extraction. 17/17 total tests pass.)*
- [x] **B2.** Set up tree-sitter language parsers: Python, JavaScript,
  TypeScript, Go, Java, Rust. *(2026-04-10: added tree-sitter-javascript
  0.25.0, tree-sitter-typescript 0.23.2, tree-sitter-go 0.25.0,
  tree-sitter-java 0.23.5, tree-sitter-rust 0.24.2. Wrote 26 tests
  in `test_language_parsers.py` covering: import, function, class/struct,
  interface/trait, imports/use, and language-specific constructs (JS
  arrow functions, TS interfaces + TSX, Go receivers + structs, Java
  annotations + interfaces, Rust impl blocks + traits + use). Key
  finding: TypeScript exposes `language_typescript()` and `language_tsx()`
  not `language()`. 43/43 total tests pass.)*
- [x] **B3.** Define the per-file structural JSON schema: file path,
  language, imports, exports, classes, functions, methods, call edges
  within file, rationale comments tagged. *(2026-04-10, hardened
  across multiple review rounds:
  `src/pensieve/schema.py` with 8 dataclasses. Systematic validator
  sweep: every required-value field checked (symbol name/signature/
  kind/visibility/lines, parameter names, import module/kind/line/alias,
  export name/kind/line, call edge caller/callee/confidence/line,
  comment tag/text/line). VALID_IMPORT_KINDS (6) and VALID_EXPORT_KINDS
  (4) enforce allowed values. Export docstring documents the `<default>`
  sentinel for anonymous callable defaults. file_path documented as
  "as provided by caller; scan_repo() normalizes to repo-relative."
  38 tests in test_schema.py. Reference doc at
  `pensieve/references/extraction-schema.md`.)*
- [x] **B4.** Implement Python extractor. *(2026-04-10, updated after
  reviews: reference implementation, multi-pass architecture. Handles:
  decorated functions, async, docstrings, typed/default/splat params,
  return types, visibility by naming convention, self.method() stripping,
  nested-function isolation, relative imports (from . import X,
  from ..bar import X). Created extractors package with lazy-loading
  registry (importlib-based, one broken module doesn't take down
  others). 36 tests in test_extractor_python.py.)*
- [x] **B5.** Implement JavaScript extractor. *(2026-04-10, updated
  after multiple review rounds:
  `src/pensieve/extractors/javascript.py`. Multi-pass architecture.
  Handles: function_declaration, arrow functions as const assignments,
  class_declaration + method_definition, ESM imports (named, default,
  namespace with names=["*"]), CommonJS require(), exports (default
  named + named aliased + inline default function/arrow + re-exports
  with `from` source + `export * as ns` namespace re-exports),
  anonymous callable default exports (Export name="<default>", no
  synthetic Symbol), named-import aliases (import { X as Y } produces
  separate Import records for graph alias tracking), constants,
  JSDoc docstrings, this.method() call stripping, export-based
  visibility. Registered on [.js, .mjs, .cjs].)*
- [x] **B6.** Implement TypeScript extractor (handles type annotations).
  *(2026-04-10, updated after multiple review rounds:
  `src/pensieve/extractors/typescript.py`. Extends JS extractor with:
  interface_declaration, type_alias_declaration, enum_declaration,
  accessibility_modifier (public/private/protected), typed parameters,
  return type annotations, `import type` (kind="import_type"), TSX
  via language_tsx(). TS-specific export handling: `export type { X }`
  gets kind="type", `export type { X } from './Y'` produces both
  Export(kind="type") AND Import(kind="import_type"), `export * as ns`
  namespace re-exports, named-import aliases (same as B5). Registered
  on [.ts, .tsx].)*
- [x] **B7.** Implement Go extractor. *(2026-04-10, updated after
  reviews: Go-specific handling for receivers, structs, interfaces,
  const blocks (including multi-name const specs), grouped type (...)
  declarations, import blocks with aliases/blank imports,
  capitalization-as-visibility, Go doc comments, multiple return
  types. 26 tests.)*
- [x] **B8.** Implement Java extractor. *(2026-04-10, updated after
  reviews: class/interface/enum, method/constructor, access modifiers,
  Javadoc, wildcard imports (import X.*), static wildcard imports,
  static final constants, overloaded method call-edge disambiguation
  via line_start matching, annotations in signatures. 28 tests.)*
- [x] **B9.** Implement Rust extractor. *(2026-04-10, updated after
  reviews: function_item, impl_item (inherent + trait), trait_item
  with default method implementations (call edges collected), struct/
  enum/type_alias/const, use declarations (simple + nested + glob +
  `use X as Y` aliases + grouped `{Read as IoRead, Write}`),
  pub/pub(crate) visibility, `///` doc comments, self parameter
  handling, closure isolation. 29 tests.)*

  **ALL 6 LANGUAGE EXTRACTORS (B4–B9)** across 6 languages, 11
  registered extensions (.py .js .mjs .cjs .ts .tsx .go .java .rs).
  Consistent 3-pass architecture. Lazy-loading registry (one broken
  module doesn't take down others). Hardened through 8+ review rounds.
- [x] **B10.** Implement comment-tag extraction across all languages.
  *(Consolidated into shared `_comments.py` module. Canonical tag list
  (WHY, NOTE, IMPORTANT, HACK, TODO, FIXME). Universal regex handles
  #, //, /* */ prefixes. Pre-built doc-comment filters (JSDoc, Rust
  ///). All 6 extractors delegate to shared module. 19 tests.)*
- [x] **B11.** Implement SHA256 cache layer in `agent-docs/.cache/`.
  *(Updated after reviews: keyed by (SHA256, extension) — same content
  in different languages gets separate entries. Invalidation key is
  EXTRACTOR_HASH (SHA256 of all extractor source files), not package
  version — auto-invalidates when any extractor code changes, zero
  developer discipline required. Schema validation on load via
  validate_extraction(). Corrupted/invalid entries → cache miss +
  warning. 38 tests.)*
- [x] **B12.** Implement `pensieve scan <repo>` — full repo extraction,
  produces `agent-docs/structure.json` + `graph.json`.
  *(Updated after reviews: validates fresh extractor output before
  caching/writing — schema-invalid → errors channel, not files[].
  extract_file()→None on supported ext → recorded failure, not skip.
  os.walk with in-place prune (ignored dirs never traversed). Writes
  graph.json alongside structure.json via build_graph(). 24 tests.)*
- [x] **B13.** Aggregate cross-file edges: import graph, call graph (where
  resolvable), file→test mapping via naming heuristics. *(2026-04-10,
  updated after multiple review rounds:
  `src/pensieve/graph.py` with `build_graph()`. Module resolution:
  absolute, dotted, relative (Python + JS/TS path-style), __init__.py
  packages. Ambiguous stems → no edge (not a wrong edge). Extension
  ambiguity → prefer importer's extension, else unresolved.

  Graph-level semantics (documented in module docstring):
  - Import edges: module-level, deduped by (source, target).
  - Call edges: function-level, NOT deduped. Each caller→callee preserved.
  - Test edges: module-level, deduped. Test→test imports filtered.
  - import_count: unique modules, not Import records.

  Cross-file call resolution:
  - Named imports: callee must exist as symbol in target (confidence 1.0).
  - Aliased named imports: alias tracked → original name checked in target.
  - Default imports: call edge only if target has callable default export
    (function/method, confidence 0.8). Classes and constants excluded.
  - Anonymous callable defaults (export default function() {},
    export default () => {}): detected via Export(name="<default>") —
    no synthetic Symbol in canonical data, graph treats as callable.
  - Namespace imports (names=["*"]): no default-import call edge.

  JS/TS re-export support (added post-review):
  - export { X } from './Y' and export * from './Y' produce Import
    records so graph creates dependency edges for barrel files.
  - export * as ns from './Y' emits Export(name="ns", kind="re_export").
  - export { X as Y } records public name Y, not original name X.
  - TS export type { X } from './Y' produces Import(kind="import_type").

  Additional fixes post-review:
  - Type-only imports (import_type) excluded from call resolution —
    create file-level dependency edges but never runtime call edges.
  - TS `export default interface` / `export default enum` → kind="default".

  Python package root detection (added during B14 prep):
  - Module index now detects Python package roots via __init__.py and
    registers dotted paths relative to each root. e.g., backend/
    open_webui/env.py indexed as both "backend.open_webui.env" (repo
    root) and "open_webui.env" (package root). Fixed critical resolution
    gap: socrates calibration repo went from 12 edges to 1938 edges
    (729 imports, 1208 calls) after this fix.

  KNOWN LIMITATIONS: wildcard re-exports don't track individual names;
  re-exported defaults don't chain (single-pass); Go URL-style imports
  and Java package-qualified imports have lower resolution accuracy.

  47 tests. 745/745 total pass.)*
- [x] **B14.** *(RESET twice)* Phase B Layer 2 — final architecture.

  **Architecture decision (2026-04-11):** v1 slash commands ARE the doc
  generation pipeline. Pensieve provides the evidence layer underneath.
  `pensieve analyze` CLI removed — the user runs v1 slash commands
  interactively in Claude Code, grounded by Layer 1 structural data.

  **What pensieve provides:**
  - `pensieve scan` → structure.json + graph.json + structural-profiles.md
  - `pensieve brief <dirs>` → per-subsystem structural brief
  - `pensieve wire` → inline nano into CLAUDE.md + install hook
  - `pensieve benchmark` → measure whether docs help agents

  **structural-profiles.md** (7-layer XML format, LLM-optimized):
  1. `<architecture>` — directory tree with dependant counts, key symbols
  2. `<signatures>` — top files per directory with full public signatures
  3. `<dependencies>` — edge lists by coupling strength (HIGH/MODERATE/LOW),
     circular deps detected. Based on ICLR 2025 finding that edge lists
     outperform adjacency matrices for LLM graph reasoning.
  4. `<entry_points>` — application entry files (main, app, server, cli)
  5. `<external_dependencies>` — top third-party packages by import count
  6. `<rationale_comments>` — WHY/HACK/IMPORTANT developer annotations
  7. `<flags>` — auto-generated, test directories
  XML tags for Claude (Anthropic recommendation). Signatures at ~5-10%
  of code tokens capturing ~90% of architecture (Code Maps approach).

  **pensieve brief** (per-subsystem, 5 sections):
  1. `<signatures>` — ALL files, ALL symbols with method-level detail
  2. `<internal_dependencies>` — within-subsystem + external in/out edges
  3. `<test_mapping>` — test→source file relationships
  4. `<entry_points>` — entry files within the subsystem
  5. `<rationale_comments>` — consolidated WHY/HACK/IMPORTANT comments

  **Validators:** `validate_structural_profile()` and
  `validate_subsystem_brief()` check well-formedness. Wired into CLI.

  **Fault tolerance:** corrupt/missing structure.json → error tag (no crash),
  missing graph.json → proceed without graph data, empty files → minimal
  valid output, all optional sections conditionally emitted.

  **v1 prompt updates:**
  - `analyze-discover.md` — Step 0 runs `pensieve scan`, reads
    structural-profiles.md for subsystem detection hints. Step 4
    references profiles for coupling-based subsystem boundaries.
  - `analyze-deep-dive.md` — Step 0 runs `pensieve brief <dirs>`
    for the target subsystem. Step 1 uses the brief's signatures
    and dependant counts for file selection. Step 3e uses the
    brief's `<internal_dependencies>` for dependency analysis
    (not raw graph.json).

  **Python modules kept (evidence-only, no doc generation):**
  - context.py: profile_directories, format_structural_profiles,
    format_subsystem_brief, generate_route_index, validators,
    SubsystemProposal/SubsystemMap (for route-index)
  - All benchmark infrastructure (Phase A)
  - Bx1 route-index, Bx5 hook telemetry

  **Removed (final cleanup 2026-04-11):**
  - `pensieve analyze` CLI + `_cmd_analyze()` function
  - `docgen.py` module (programmatic doc generation)
  - `checkpoint.py` module (analyze-pipeline caching)
  - context.py dead functions: propose_subsystems,
    select_files_for_subsystem, build_subsystem_brief (old),
    format_profiles_for_llm, format_subsystem_map,
    generate_subsystem_doc, save_subsystem_doc, synthesize_docs,
    save_synthesis, FileSelection, SubsystemDoc, SynthesisResult,
    all LLM prompt constants

  846 tests. Pipeline: `pensieve scan` → `/analyze-discover` →
  `/analyze-deep-dive {subsystem}` (uses `pensieve brief`) →
  `/analyze-synthesize` → `pensieve wire`.

- [ ] **B15.** Run v1 slash commands on calibration repo with structural
  data. Compare output quality to v1-without-structural-data.
- [ ] **B16.** Run benchmark with new docs. Compare to baseline.
- ~~**B17.**~~ *(merged into B14, then reset twice)*

### Proceed criterion (Phase B → Phase C)

1. Phase 2 deep-dive token cost ≤ 30% of pre-Phase-B baseline on
   calibration repo (matches graphify's order of magnitude on the AST cost
   lever).
2. Subsystem doc quality ≥ pre-Phase-B baseline (LLM-judged on 5+
   subsystems, spot-checked by human on 2).
3. Auto-benchmark from Phase A shows no regression on cost, time, lenient
   pass, or quality vs Phase A end state.
4. Re-runs on unchanged files take <10% of first-run time on the
   calibration repo (cache is working).

### Phase B status: Layer 1 complete (B1–B13), Layer 2 B14 complete (v1 prompts + Layer 1 evidence), B15–B16 next

### Phase B notes

- **2026-04-10 (B1):** tree-sitter installed and verified. API is
  `Language(tspython.language())` → `Parser(language)` → `parse(bytes)`.
  Tests confirm: function/class/import extraction, error-tolerant
  parsing, line number extraction. Python grammar added alongside core
  lib; remaining 5 languages (JS, TS, Go, Java, Rust) land in B2.

- **2026-04-10 (B4):** Python extractor — reference implementation.
  Multi-pass architecture (top-level declarations → call edges → rationale
  comments). Created `src/pensieve/extractors/` package with registry
  pattern (`register()` + `extract_file()`). The Python extractor auto-
  registers on import. Key design decisions that apply to ALL extractors:
  - Multi-pass over single recursive walk (simpler to debug)
  - Signature = first line of declaration (not body)
  - Visibility by language convention (Python: `_` prefix = private)
  - Constants = top-level ALL_CAPS assignments
  - Nested functions/lambdas skipped (not structural landmarks)
  - `self.method()` calls stripped to just `method` for cleaner edges
  - Nested function calls don't leak into parent's edge list
  - Decorated definitions unwrapped to get inner function/class
  - Docstring = first string literal in function/class body

- **2026-04-10 (B3):** Per-file structural JSON schema designed and
  implemented. Key design decisions:
  - Flat symbol list with `parent` field for containment (not nested)
  - 9 symbol kinds: function, class, method, interface, trait, struct,
    enum, type_alias, constant
  - Continuous confidence scores (0.0-1.0) on call edges, not
    categorical labels
  - 6 rationale comment tags: WHY, NOTE, IMPORTANT, HACK, TODO, FIXME
  - Extractor version in output for cache invalidation
  - Signature field captures declaration line (no body) — enough for
    the LLM to understand what a function does without reading the file
  - Parameters with optional type/default for pattern matching
  - Full JSON round-trip via `to_json()`/`from_json()` and
    `save()`/`load()` for file I/O
  - `validate_extraction()` enforces all constraints, raises
    SchemaError with all errors listed (not just the first)
  Reference doc at `pensieve/references/extraction-schema.md`.

- **2026-04-10 (B2):** All 6 language parsers installed and verified.
  26 new tests across JS, TS, Go, Java, Rust. Key language-specific
  findings documented in tests: TypeScript has `language_typescript()`
  + `language_tsx()` (not `language()`); Go uses `method_declaration`
  for receiver methods vs `function_declaration`; Java uses
  `method_declaration` + `constructor_declaration`; Rust uses
  `function_item` (not `function_declaration`) and `impl_item` +
  `trait_item`. These node-type names are critical for B4-B9 extractors.

- **2026-04-10 (B13 fix):** Python package root detection in graph
  module index. `__init__.py` directories register dotted paths
  relative to their parent (e.g., `open_webui.env` resolves to
  `backend/open_webui/env.py`). Socrates repo: 12 → 1938 edges.

- **2026-04-10 (B14 original):** Built 5-sub-step pipeline in context.py
  (profiler, proposer, file selector, doc generator, synthesis). CLI:
  analyze + wire. Validated on socrates. Then RESET.

- **2026-04-10 (B14 RESET 1):** Old custom output shape replaced with
  v1-framework-shaped output in docgen.py. 903 tests.

- **2026-04-11 (B14 RESET 2 — FINAL):** Abandoned programmatic doc
  generation entirely. v1 slash commands ARE the doc pipeline. Pensieve
  provides evidence, not docs. Key changes:
  - `pensieve analyze` CLI removed
  - v1 prompts updated: analyze-discover.md Step 0 runs `pensieve scan`
    and reads structural-profiles.md; analyze-deep-dive.md Step 0 reads
    structural data for the target subsystem
  - `pensieve scan` now produces structural-profiles.md (7-layer XML:
    architecture, signatures, dependencies, entry points, external deps,
    rationale comments, flags)
  - `pensieve brief <dirs>` CLI added (per-subsystem structural brief
    with full file-level signatures)
  - Validators for both profile formats (validate_structural_profile,
    validate_subsystem_brief)
  - Full fault tolerance: corrupt/missing files → error tags, missing
    graph → proceed without, empty repos → minimal valid output
  - 846 tests total (all dead code and tests removed)
  - Design grounded in: Aider repo map (tree-sitter + PageRank), RIG
    paper (+12.2% accuracy with descriptive fields), ICLR 2025 (edge
    lists > matrices), Anthropic (XML tags for Claude), Code Maps
    (signatures capture 90% of architecture at 5% token cost)

---

## Phase Bx — Adaptive Wiring And Structural Routing

**Goal.** Make the harness use the structural moat optimally:
repo-wide routing via `structural-profiles.md`, subsystem routing via
`pensieve brief`, recipe routing via `patterns.md`, and telemetry that
proves whether those hints actually changed agent behavior.

**Why now.** Phase B's value is no longer just “better docs.” The real
advantage is deterministic structure extraction and high-signal
compression of that structure into agent-usable artifacts. Static
wiring leaves too much of that value unused. Before moving to multi-repo,
we should make the single-repo harness route agents through the right
derived artifacts at the right time.

**Final architecture assumptions.**
- Slash commands are the doc pipeline.
- `pensieve scan` and `pensieve brief` are the structural moat.
- `structure.json` and `graph.json` are machine-only artifacts and must
  never be read directly by LLM agents.
- Hooks route; they do not dump large context by default.

**Artifact roles for routing.**
- `agent-context-nano.md` — session-start quick context only
- `structural-profiles.md` — repo-wide orientation, ownership, subsystem
  discovery, deep-dive ordering
- `brief` output — subsystem-level coding context, file targeting,
  dependency-aware edits, test mapping
- `patterns.md` — recipe-first coding guidance
- subsystem docs — deeper interpreted context after routing
- `route-index.json` — harness-readable routing substrate

**Pareto principle.** This phase deliberately excludes clever-but-costly
hook ideas. We only implement the highest-leverage pieces:
1. route-index generation from structural artifacts
2. path-aware routing
3. recipe-first hints
4. anti-thrash intervention
5. telemetry

### Milestones

- [x] **Bx1.** Build a route index from generated context.
  *(2026-04-10: `generate_route_index()` in context.py. Current schema:
  version, routes[] with match_type/pattern/subsystem/doc_path/hint,
  fallback_hint. Initially generated from subsystem map. This is the
  seed substrate for richer structural routing.)*

- [ ] **Bx1a.** Upgrade route-index to be structurally aware.
  Route index should be derived from:
  - subsystem map from `/analyze-discover`
  - `structural-profiles.md`
  - subsystem docs
  - `patterns.md`
  - known key files / common tasks / touched-together hints
  It should encode:
  - path prefix → subsystem doc
  - path prefix → `brief` target dirs
  - task shape → preferred artifact
  - subsystem → key files
  - subsystem → common tasks

- [ ] **Bx2.** Add path-aware prehook routing.
  When the agent is about to use broad search (`Glob`, `Grep`) and the
  query/path clearly maps to a subsystem, surface one short hint that
  points to the most relevant artifact:
  - subsystem doc
  - `structural-profiles.md`
  - or `pensieve brief <dirs>` for that subsystem
  Keep it concise and non-spammy.

- [ ] **Bx3.** Add recipe-first hints.
  When the query looks like a modification task, prefer surfacing the
  most actionable recipe/pattern/example over architecture prose. The
  routing preference should be:
  1. `patterns.md`
  2. relevant subsystem doc
  3. relevant `brief`

- [ ] **Bx4.** Add anti-thrash intervention.
  Detect repeated broad, low-signal search before a relevant file or doc
  is opened. Intervene once with a direct rerouting hint toward the
  correct subsystem doc or `brief`. Do not repeat the same hint
  aggressively.

- [x] **Bx5.** Add hook telemetry.
  *(2026-04-10: Hook script updated to read stdin (tool_name, session_id,
  tool_input), consult route-index.json for path-aware routing, and
  append JSONL events to agent-docs/hook-telemetry.jsonl. Event schema:
  timestamp, event ("hint_shown"), tool_name, query, hint_type
  ("routed"/"fallback"), target_doc, session_id. Consultation tracking
  deferred — correlate telemetry with transcript_path post-run.)*

- [ ] **Bx5a.** Expand telemetry to structural-artifact usage.
  Track:
  - hint shown
  - artifact suggested (`structural-profiles`, `brief`, `patterns`,
    subsystem doc)
  - target subsystem
  - whether that artifact was later consulted
  - broad-search count before first relevant read
  - routed vs fallback vs anti-thrash intervention

- [ ] **Bx6.** Make `brief` a first-class harness primitive.
  `pensieve brief <dirs>` should be cheap enough for routine use,
  cacheable, and optionally materializable to predictable files such as
  `agent-docs/briefs/{subsystem}.md`. Hooks and slash commands should be
  able to route to or invoke it without exposing raw JSON.

- [ ] **Bx7.** Add freshness and validity checks for routed artifacts.
  Routing should not rely on stale structural summaries. Add stage-
  specific fingerprints for:
  - `structural-profiles.md`
  - `brief` outputs
  - route index
  - discover outputs
  - synthesis outputs
  Hook behavior should degrade gracefully when artifacts are stale or
  partial.

- [ ] **Bx8.** Benchmark the adaptive hook layer.
  Compare:
  - docs only
  - docs + current hook
  - docs + structural routing
  Metrics:
  - docs-consulted rate
  - `brief` consulted rate
  - `structural-profiles.md` consulted rate
  - search-thrash reduction
  - strict / lenient pass
  - quality
  - cost / tokens / time

### Routing policy (explicit)

Default harness routing should be:
- session start → `agent-context-nano.md`
- architecture / ownership / “what subsystem owns X?” →
  `structural-profiles.md`
- subsystem implementation work → `brief`
- “how do I add/change X?” → `patterns.md`
- deep follow-up context → subsystem doc

### Proceed criterion (Phase Bx → Phase C)

1. Docs-consulted rate improves materially vs docs-only baseline.
2. `brief` and/or `structural-profiles.md` are consulted earlier on the
   frozen benchmark task set.
3. Broad-search thrash decreases on the frozen benchmark task set.
4. Hook hints do not materially regress pass, quality, cost, or time.
5. The adaptive hook stays simple: no LLM-in-the-hook, no raw JSON
   exposure, no large context injection by default, no repeated hint
   spam.

### Phase Bx status: foundation started (Bx1, Bx5 shipped; routing layer not yet implemented)

### Phase Bx notes

- The moat is not “we have docs.” The moat is deterministic structural
  extraction + high-signal compression + routing + telemetry.
- `structure.json` and `graph.json` are compiler IR, not agent-facing
  artifacts.
- `structural-profiles.md` is the repo-wide routing artifact.
- `brief` is the subsystem working-context artifact.
- Do not inject large docs by default; route first, load later.
- If only two things get built next, prioritize:
  1. path-aware routing
  2. structural-artifact telemetry
- This phase is intentionally the 80/20 version of smart wiring, not a
  full autonomous retrieval engine.

### Recommended execution order (rolling waves, not one giant phase)

We intend to execute the full Bx roadmap, but **not** as one large
uninterrupted build. The correct approach is progressive rollout:
implement a tight slice, measure, inspect telemetry, then continue.

**Wave 1 — substrate + measurement**
1. `Bx1` route index 2.0
2. `Bx5` telemetry 2.0
3. codify the routing policy in hook/command behavior

Why first:
- provides the routing substrate
- provides measurement
- later routing work would otherwise be guessy

**Wave 2 — highest-lift routing**
4. `Bx2` path-aware routing
5. `Bx6` brief lifecycle

Why second:
- this is the most likely 80/20 payoff
- route agents to the right subsystem and the right `brief` early

**Wave 3 — optimization layers**
6. `Bx4` anti-thrash intervention
7. `Bx3` recipe-first hints

Why third:
- these build on top of basic routing
- they are valuable, but easier to overdo before telemetry proves the
  simpler routing is working

**Wave 4 — hardening + validation**
8. `Bx7` freshness/validity
9. `Bx8` benchmark ablation

Why fourth:
- freshness hardening matters once routing is real
- ablation should validate the stack after the routing behavior exists

**Operational rule:**
- do not build the entire list before measuring
- after Wave 2, run a benchmark slice and inspect telemetry
- continue only if the structural-routing path is showing real signal
- if lift is weak, debug routing/usage before adding more clever behavior

**Practical prioritization:**
The most likely 80/20 remains:
1. route index
2. telemetry
3. path-aware routing
4. `brief` lifecycle

Everything after that must earn its complexity by benchmark lift.

---

## Phase C — Multi-repo support

**Goal.** Make Code Pensieve serve the multi-microservice scenario, which
is the framework's strongest theoretical advantage over modern single-repo
coding agents. Cross-repo navigation is the thing agents structurally
cannot do well on their own.

**Why third.** Phases A and B prove the foundation works on single repos.
Multi-repo is the strongest theoretical advantage but the most engineering
work. Doing it after the foundation is solid means we're not building
multi-repo on a broken base.

### Milestones

- [ ] **C1.** Implement repo root detection: walk a directory tree,
  identify `.git` boundaries, manifest files (`package.json`, `go.mod`,
  `pyproject.toml`, `pom.xml`, `Cargo.toml`).
- [ ] **C2.** Define the multi-repo directory layout convention: parent
  directory containing N repo subdirectories (or symlinks to repos
  elsewhere).
- [ ] **C3.** Modify `pensieve scan` to handle `--multi-repo` mode:
  per-repo extraction with cross-repo merge.
- [ ] **C4.** Build cross-repo edge detector for HTTP routes: extract
  route definitions from server-side code (Flask `@app.route`, Gin
  handlers, Spring controllers, Express routes, etc.); extract URL string
  literals + base URLs from client-side code; match on path patterns.
- [ ] **C5.** Build cross-repo edge detector for OpenAPI / Swagger schema
  files: detect schemas, link generated client/server pairs.
- [ ] **C6.** Build cross-repo edge detector for protobuf / gRPC service
  definitions: parse `.proto`, link service definitions to client code
  that imports them.
- [ ] **C7.** *(Stretch)* Cross-repo edge detector for shared package
  imports in monorepo workspaces (`pnpm-workspace.yaml`, `go work`,
  Cargo workspaces).
- [ ] **C8.** *(Stretch)* Cross-repo edge detector for message queue
  topics (Kafka, RabbitMQ, NATS) — pattern-match producer and consumer
  registrations.
- [ ] **C9.** Implement cross-repo subsystem map: each service is a
  subsystem; cross-repo edges become subsystem dependencies in the
  top-level `system-overview.md`.
- [ ] **C10.** Implement multi-repo nano-digest format: includes the
  service mesh map, the top patterns *across* services, the contracts
  between services. Design constraint: must still fit ≤80 lines (relaxed
  from 40 for multi-repo because it covers more ground).
- [ ] **C11.** Implement `pensieve wire claude --multi-repo` — installs
  the PreToolUse hook in each repo's `.claude/settings.json`, inlines the
  multi-repo nano into each repo's `CLAUDE.md`, sets relative paths
  correctly so each repo can find the parent `agent-docs/`.
- [ ] **C12.** Build multi-repo task templates for the benchmark suite:
  - `cross_service_feature` — implement a feature spanning two services
  - `contract_update` — update a server endpoint and verify the agent
    finds and updates the matching client
  - `end_to_end_flow_trace` — answer "what services touch this user
    action and in what order"
- [ ] **C13.** Set up a multi-repo POC: 3–5 services we control (Zomato
  internal services, or a curated public set if we need external coverage).
- [ ] **C14.** Run benchmark on the POC: baseline (no agent-docs) vs
  with-framework (multi-repo Code Pensieve installed).
- [ ] **C15.** Iterate on cross-repo edge detection coverage if the
  benchmark shows the framework isn't picking up enough cross-repo signal.

### Proceed criterion (Phase C → Phase D)

1. On the multi-repo POC, with-framework lenient pass rate on the
   cross-repo task templates (`cross_service_feature`, `contract_update`,
   `end_to_end_flow_trace`) is ≥ baseline + 15pp.
2. Cross-repo task quality ≥ baseline.
3. Cost on cross-repo tasks ≤ baseline (multi-repo agent-docs are bigger,
   but the cost savings from not having the agent re-discover N repos
   should outweigh).
4. Single-repo benchmark from Phase B is unchanged (we didn't break
   single-repo while adding multi-repo).

If condition 1 fails, the framework's strongest theoretical advantage
doesn't materialize empirically. This is a real branching point — we
iterate on cross-repo detection coverage, and if it still doesn't hold,
we publish honest lessons and reconsider scope.

### Phase C status: not started

### Phase C notes

*(filled as we work)*

---

## Phase D — MCP, multi-platform, polish, distribution

**Goal.** Productionize Code Pensieve. Distribute it. Make it easy for
new users to install and use without hand-holding. Surface the worked
examples that build trust.

**Why last.** Polish phase. Broad surface area but no individual change
is high-risk. MCP and multi-platform support are valuable but won't move
benchmark numbers — they should come after validation, not before.

### Milestones

- [ ] **D1.** Implement an MCP server exposing structured queries:
  - `get_subsystem(name)` → subsystem doc + key files
  - `get_pattern(name)` → recipe with file paths
  - `find_path(file)` → which subsystem owns this file
  - `get_uncertainties_above(threshold)` → filter by confidence score
  - `find_cross_repo_edges(repo, kind)` → multi-repo queries
- [ ] **D2.** Generate platform-specific skill files from a single source.
  Currently we hand-maintain Claude Code, Codex, Cursor variants; replace
  with a templating system.
- [ ] **D3.** Add support for additional platforms as they ship: OpenCode,
  Factory Droid, OpenClaw (mirror graphify's coverage).
- [ ] **D4.** Convert categorical confidence labels (`Confirmed:`,
  `Inference:`, `UNCERTAIN:`) to continuous 0.0–1.0 scores throughout.
  Update `uncertainties.md` to be sortable by score.
- [ ] **D5.** Build the `worked/` directory with at least 3 honest review
  files: one small repo, one medium, one multi-repo. Each review lists
  what the framework got right AND what it missed.
- [ ] **D6.** Documentation pass: README rewrite, architecture doc,
  contributing guide, security model (input validation for any URLs/paths
  the framework processes).
- [ ] **D7.** Set up CI/CD: GitHub Actions for tests, lint, type checks,
  and (eventually) PyPI release.
- [ ] **D8.** Decision point: open source or stay internal? If open
  source, reserve the PyPI name `code-pensieve` and tag v0.1.0. If
  internal, publish to Zomato's internal package index.
- [ ] **D9.** Internal users start using Code Pensieve on real repos.
  Collect feedback. File issues for everything that surprises them.
- [ ] **D10.** Iterate based on real-world usage. Not every issue is a
  Phase D thing — some will need work in earlier layers.
- [x] **D11.** Overhaul the benchmark task generation framework.
  *(COMPLETED as part of A13 rework, 2026-04-10. Replaced static
  PlaceholderFiller + 5 fixed templates with repo-aware generation:
  RepoContext from structure.json + graph.json, TaskGenerator producing
  concrete TaskInstances, 6 task families (add_sibling, add_test,
  bug_fix with real code mutations, architecture, find_owner,
  cross_subsystem), difficulty stratification, setup_action execution,
  parallel runner, task audit, generated-tasks.json for auditability.
  Remaining: registration/wiring task family, LLM-generated tasks
  (Option C) if deterministic heuristics prove insufficient.)*
- [ ] **D12.** Auto-update agent-docs as the repo evolves. Two levels:
  (1) Structural refresh — re-run `pensieve scan` on changed files,
  update structure.json + graph.json. Triggered by SHA256 cache diff,
  near-zero cost. (2) Doc refresh — when structural diff exceeds a
  threshold (new subsystem, major dependency change, new patterns),
  LLM re-evaluates affected subsystem docs. Targeted, not full
  regeneration. Triggers: git hook (post-commit/post-merge), CI step,
  manual `pensieve refresh`, or PreToolUse hook detecting stale docs
  (structure.json newer than subsystem docs). Design constraint: only
  regenerate docs for subsystems whose structural brief changed, not
  the entire doc set.

### Proceed criterion

Phase D is the ongoing maintenance + adoption phase. There's no single
proceed criterion; instead, milestones complete as the framework matures
and users adopt it.

### Phase D status: not started

### Phase D notes

*(filled as we work)*

---

## Decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-04-08 | **Name:** Code Pensieve | Pensieve metaphor — extract memories, store, retrieve on demand — maps perfectly to extracting codebase context for agents to draw from |
| 2026-04-08 | **Repo layout:** new `pensieve/` directory inside the current `codebase-analysis-skill` repo, not a new repo | Preserves git history, keeps v1 runnable as fallback during the rebuild, the hybrid wiring work we just did feeds directly into v2's nano-digest format |
| 2026-04-08 | **Distribution:** pip install (Python package) | AST extraction requires Python tooling; matches graphify's proven distribution model |
| 2026-04-08 | **Open source posture:** internal-first for Phases A–B, evaluate after Phase C | Control narrative during early phases, can use Zomato repos as calibration targets, multi-repo story is stronger for any future OSS launch |
| 2026-04-08 | **Backwards compatibility:** no migration tool unless production users emerge | No production users on v1 today; freedom to redesign |
| 2026-04-08 | **Calibration repo for Phase A:** same repo + same 30 tasks as the teammate's existing external benchmark | Direct comparability with historical numbers; sanity-check our auto-benchmark against their independent measurement |
| 2026-04-08 | **Teammate role during Phase A:** keep running external benchmarks as QA | Catch measurement bugs in the auto-benchmark before we trust it |
| 2026-04-08 | **Languages for Phase B AST extraction:** Python, JavaScript, TypeScript, Go, Java, Rust | Covers Zomato's primary stack + matches graphify's coverage; expandable later |
| 2026-04-08 | **Benchmark default:** opt-in via `--benchmark` flag, not default in Phase 3 | Adds cost ($0.50–$2) and time per run; only worth it on demand or at phase boundaries |
| 2026-04-08 | **Multi-repo:** Phase C, but all foundational decisions in A and B made with multi-repo as eventual target | Strongest theoretical advantage but most engineering work; foundation must not preclude it |
| 2026-04-08 | **Sequencing:** milestone-driven with proceed criteria, not time-boxed | AI-coding-agent collaborative workflow doesn't follow human team time estimates |
| 2026-04-08 | **Three-layer architecture:** Python core (deterministic) → LLM orchestration → wiring & distribution | Each layer independently testable; AST + LLM split is the cost lever |
| 2026-04-08 | **Two load-bearing artifacts:** `agent-context-nano.md` (inlined) + `patterns.md` (recipes) | Everything else either supports these or is for human reference; simplifies the surface area |
| 2026-04-10 | **Phase reorder:** B before A remainder, then E2E testing, then C, then D | Phase A proceed criterion met early via teammate's external benchmark. Phase B (AST extraction) is the highest-value next step. Remaining Phase A milestones (A3–A15: hook CLI + auto-benchmark) are stable-scope tooling that won't be affected by Phase B and can be completed after. Teammate covers measurement needs during Phase B. |
| 2026-04-10 | **PreToolUse hook uses JSON `hookSpecificOutput.additionalContext`, not plain echo** | Web search of official Claude Code hooks docs confirmed: plain stdout from PreToolUse hooks only shows in verbose mode (Ctrl+O). The documented way to inject context into the agent is JSON output with `hookSpecificOutput.additionalContext`. graphify's plain-echo pattern may not be reaching the agent. Our hook uses the documented JSON mechanism, verified end-to-end by Lalit on 2026-04-08. |
| 2026-04-10 | **Cache invalidation key = hash of extractor source files, not `__version__`** | Review finding: `__version__` is a static `0.0.1` string that doesn't change when extractor logic changes, so stale cache entries survive extractor bug fixes. Fix: `EXTRACTOR_HASH` is computed at import time by SHA256-hashing all `extractors/*.py` + `schema.py` source files. Any change to any extractor file auto-invalidates all cache entries. Zero developer discipline required. Falls back to `__version__` if source files can't be located (frozen distributions). |
| 2026-04-10 | **Benchmark task generation overhauled (D11 done)** | A13 full run revealed static PlaceholderFiller was broken. Replaced with RepoContext + TaskGenerator + TaskInstance architecture. 6 task families, real code mutations, parallel execution, task audit. Completed as part of A13 rework, not deferred to Phase D. |
| 2026-04-10 | **Quality over cost for first-time doc generation** | Initial generation should read generously — no token budget constraint on file reading. The AST skeleton eliminates enumeration (LLM doesn't discover what exists) but for understanding patterns/decisions/rationale, reading more files = better docs. Cost savings are reaped by every agent session that uses the docs afterward, not during generation. |
| 2026-04-10 | **Subsystem detection: hybrid directory + graph, LLM-refined, human-confirmed** | Directory structure as starting point (human-intuitive names), graph edges to validate/correct (split disconnected dirs, merge tightly-coupled ones), LLM to refine (merge/split/name based on semantic understanding), human confirms via chat-first checkpoint. Skip Leiden for now — add as fallback for flat repos if needed. |
| 2026-04-10 | **B14+B17 merged** | Both consume structure.json + graph.json for the LLM orchestration layer. B14 (deep-dive prompts) and B17 (structural graph into subsystem mapping) are the same pipeline: graph → subsystem boundaries → per-subsystem deep-dive. Splitting them was the pre-AST plan. |
| 2026-04-10 | **Auto-updating agent-docs (D12)** | Docs become stale on every merge. Two-level refresh: structural (deterministic, near-zero cost on changed files) and doc-level (LLM re-evaluates affected subsystems when structural diff exceeds threshold). Deferred to Phase D. |
| 2026-04-10 | **A13 provisional, defer full calibration to post-B14** | Benchmark infrastructure is validated. But benchmarking v1 agent-docs doesn't test the v2 pipeline. The right sequence: finish B14 → re-benchmark with generated docs → compare to teammate. |
| 2026-04-10 | **Phase B Layer 2 RESET 1** | Replaced custom output shape with v1-framework-shaped output in docgen.py. |
| 2026-04-11 | **Phase B Layer 2 RESET 2 (FINAL)** | Abandoned programmatic doc generation. v1 slash commands are the doc pipeline. Pensieve provides structural evidence (scan → structural-profiles.md + brief), not docs. `pensieve analyze` removed. v1 prompts updated to consume Layer 1 data. Design: pensieve scan produces the evidence, v1 prompts interpret it, human runs the interactive workflow. |
| 2026-04-11 | **LLM-optimized structural profiles** | 7-layer XML format for structural-profiles.md. Architecture tree, signatures, edge-list dependencies, entry points, external deps, rationale comments, flags. Grounded in Aider repo map, RIG paper, ICLR 2025, Anthropic XML guidance, Code Maps approach. Validators + fault tolerance added. |

---

## Kill criteria results

*(filled as we hit each phase's proceed criterion)*

| Phase | Criterion | Result | Date | Action taken |
|---|---|---|---|---|
| A (wiring) | Lenient pass ≥ baseline | **PASS: 53.3% vs 46.7% (+6.6pp)** | 2026-04-10 | Proceed to Phase B |
| A (wiring) | Cost ≤ 105% of baseline | **PASS: $0.861 vs $0.862 (tied)** | 2026-04-10 | Proceed to Phase B |
| A (wiring) | Quality ≥ baseline | **PASS: 7.27 vs 7.07 (+0.20)** | 2026-04-10 | (Not formally required but captured) |
| A (wiring) | Time ≤ baseline | **PASS: 3.64m vs 4.04m (−10%)** | 2026-04-10 | (Not formally required but captured) |

---

## Open questions (active)

*(things we're currently debating; resolved questions move into the
decisions log)*

- *(none active — all open questions resolved 2026-04-08)*

---

## Notes / lessons / unlearning

*(running log of things we discover during the build that change our
beliefs about the design)*

### Lessons carried in from v1 + benchmark history (pre-build)

- **Long-context fallback is the cost mechanism.** When main-thread
  conversation exceeds the smaller model's context window, the provider
  falls back to a long-context model (typically Sonnet). This was the root
  cause of the 11% cost regression in v1's full-load wiring. Any wiring
  that accumulates `agent-docs/` content in main-thread context will
  trigger this. Code Pensieve's hybrid wiring (inline nano + Explore for
  deeper docs) is designed around this constraint.

- **Pattern fidelity on the writer matters.** The Medium-bucket benchmark
  win in v1 came from the main thread *internalizing* pattern conventions
  before generating code. When patterns came back as subagent summaries,
  strict pass rate fell from 30% to 10% and lenient pass fell from 70% to
  30%. Subagent summaries lose the verbatim details that strict pass
  requires. **Inlining patterns into the system prompt is the only known
  way to preserve fidelity without triggering long-context fallback.**

- **The wiring mechanism matters as much as the content.** v1 went through
  three wiring iterations (full-load, lean, explore-routed); none beat
  baseline. graphify's PreToolUse hook design demonstrated that
  harness-enforced wiring is structurally stronger than CLAUDE.md
  instructions because it doesn't depend on agent compliance.

- **AST extraction is free; LLM extraction is expensive and worse.**
  Tree-sitter gives perfect-recall structural data deterministically.
  Spending LLM tokens on file enumeration, import discovery, and call
  graph construction is paying retail for wholesale work. graphify's
  measured 71.5× token reduction came primarily from this asymmetry.

- **Modern coding agents are good at single-repo exploration cold.** The
  v1 benchmark consistently showed `without-docs` baseline winning on
  single-repo. The framework's strongest defensible niche is therefore
  multi-repo, where natural exploration breaks down because there are no
  imports linking services and no compile-time cross-references.

- **Measurement must be baked in.** v1 had no auto-benchmark; we
  discovered cost regressions only via the teammate's external benchmark,
  late. Code Pensieve auto-benchmarks at phase boundaries (and on demand)
  so we catch regressions on the run that introduces them.

### Lessons from the build

*(empty until we start Phase A)*

---

## Working agreements

- **Plan file is canonical.** When reality diverges from the plan, we
  update the plan, not work outside it. The plan is the contract.
- **Every phase boundary updates the plan.** Status moves to `complete`,
  notes get filled in with what we learned, the kill criteria results
  table gets a new row, decisions log gets new entries for any non-obvious
  choices made during the phase.
- **Iteration is the default.** When a milestone fails, we iterate on it.
  We do not skip ahead to the next phase to make progress feel faster.
- **Honest about regressions.** If the auto-benchmark shows a regression
  on the calibration repo, we record it in the kill criteria results
  table even if we'd rather not. The whole point of measurement is
  catching this.
- **No time estimates.** Milestones complete when they complete. Proceed
  criteria are quality gates, not deadlines.
