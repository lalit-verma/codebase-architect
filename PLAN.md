# Code Pensieve — Build Plan

> **Status:** Phase B — B1–B13 complete; B14 next; Phase A paused
> **Last updated:** 2026-04-10
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
| **A** | Hooks + auto-benchmark | **paused** — proceed criterion met (2026-04-10); A1, A2 complete; A3–A15 deferred until after Phase B |
| **B** | AST extraction (Layer 1 + integration into Layer 2) | in progress (B1–B13 complete) |
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
- [ ] **A6.** Define the auto-benchmark task template format. JSON schema:
  template name, instruction template, expected output checker (strict +
  lenient), simulated repo modifications, success criteria.
- [ ] **A7.** Implement 5 task templates (the Phase A subset):
  - `add_handler` — write a new instance of the most-common file pattern
  - `add_test` — write a test for an existing file
  - `bug_fix_localized` — fix a planted bug in a single function
  - `find_owner` — answer "which subsystem owns file X and what
    conventions apply"
  - `cold_navigation` — open-ended question requiring repo exploration
- [ ] **A8.** Implement the baseline runner — runs each task without any
  `agent-docs/` present, measures tokens, cost, time, lenient pass via
  LLM judge.
- [ ] **A9.** Implement the with-framework runner — runs each task with
  the hybrid wiring + PreToolUse hook installed.
- [ ] **A10.** Implement metrics aggregation: `benchmark.json` schema with
  `with_framework` + `baseline` + `deltas` + `verdict` (PASS / MIXED /
  FAIL).
- [ ] **A11.** Implement `benchmark-history.md` generator — appends each
  run's summary so successive re-runs show trends.
- [ ] **A12.** Implement the CLI: `pensieve benchmark run --repo <path>
  --tasks all --baseline --with-framework`.
- [ ] **A13.** Run on the calibration repo (same repo + same 30 tasks the
  teammate has been benchmarking externally).
- [ ] **A14.** Compare auto-benchmark results to the teammate's most
  recent external benchmark. Discrepancies are bugs in our measurement,
  not in the framework — fix them before continuing.
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
  within file, rationale comments tagged. *(2026-04-10: wrote
  `src/pensieve/schema.py` with 8 dataclasses (FileExtraction, Symbol,
  Parameter, Import, Export, CallEdge, RationaleComment + SchemaError).
  9 symbol kinds × 6 languages × 5 visibilities × 6 comment tags. Flat
  symbol list with `parent` for containment. Continuous confidence
  scores on call edges. Full JSON round-trip serialization + file I/O.
  `validate_extraction()` checks all fields. 38 tests in
  `test_schema.py` (construction, serialization, deserialization,
  round-trip, file I/O, 13 validation-invalid cases, edge cases). Human-
  readable reference at `pensieve/references/extraction-schema.md`. 81/81
  total tests pass.)*
- [x] **B4.** Implement Python extractor. *(2026-04-10: reference
  implementation in `src/pensieve/extractors/python.py`. Multi-pass
  architecture: Pass 1 = top-level declarations (functions, classes,
  methods, imports, constants), Pass 2 = call edges within function
  bodies, Pass 3 = rationale comments with containing-symbol context.
  Handles: decorated functions/methods (@staticmethod, @classmethod,
  @property, custom decorators), async functions, docstring extraction,
  typed/default/splat parameters, return types, visibility by naming
  convention (_private, __very_private, __dunder__ = public), self.method()
  call stripping, nested-function-call isolation. Created extractors
  package with `__init__.py` registry (`extract_file(path)` dispatches
  by extension, `supported_extensions()`). 36 tests in
  `test_extractor_python.py` covering all extraction paths + a realistic
  auth-module integration test. 117/117 total tests pass.)*
- [x] **B5.** Implement JavaScript extractor. *(2026-04-10:
  `src/pensieve/extractors/javascript.py`. Follows B4's multi-pass
  architecture. Handles: function_declaration, arrow functions as
  const assignments, class_declaration + method_definition (constructor,
  static, async), ESM imports (named, default, namespace), CommonJS
  require(), export_statement (default + named + inline), constants
  (const ALL_CAPS), JSDoc docstrings (/** ... */ as preceding sibling),
  this.method() call stripping, export-based visibility (exported =
  public). Registered on [.js, .mjs, .cjs]. 28 tests in
  `test_extractor_javascript.py` + realistic integration test.
  145/145 total tests pass.)*
- [x] **B6.** Implement TypeScript extractor (handles type annotations).
  *(2026-04-10: `src/pensieve/extractors/typescript.py`. Reuses stable
  helpers from JS extractor (call edges, comments, JSDoc). TS-specific:
  interface_declaration → kind="interface", type_alias_declaration →
  kind="type_alias", enum_declaration → kind="enum",
  accessibility_modifier → visibility (public/private/protected),
  required_parameter with type annotations, return type from
  type_annotation, `import type` detection (kind="import_type"), TSX
  via language_tsx() for .tsx files. Fixed: TS-specific
  `_extract_ts_exports` wrapping JS version to handle interface/type/enum
  exports; constants inside `export const` now extracted. Registered on
  [.ts, .tsx]. 27 tests + realistic PgUserRepository integration test.
  172/172 total tests pass.)*
- [x] **B7.** Implement Go extractor. *(2026-04-10:
  `src/pensieve/extractors/go.py`. Go-specific: function_declaration +
  method_declaration with receivers (pointer + value), type_declaration
  for structs + interfaces, const_declaration (single + block), import
  blocks with aliases + blank imports, capitalization-as-visibility
  (uppercase = public, lowercase = private), Go doc comments (preceding
  `//` lines, excluding rationale tags), multiple return types via
  parameter_list. Bug found and fixed: return-type parameter_list was
  being counted as another param set instead of captured as return type.
  Registered on [.go]. 26 tests + realistic auth service integration
  test. 198/198 total tests pass.)*
- [x] **B8.** Implement Java extractor. *(2026-04-10:
  `src/pensieve/extractors/java.py`. Java-specific: class_declaration +
  interface_declaration + enum_declaration, method_declaration +
  constructor_declaration, access modifiers from `modifiers` node
  (public/private/protected/package-private), Javadoc (/** */ preceding
  sibling, strips @param/@return tags), imports via scoped_identifier,
  static final ALL_CAPS as constants, method_invocation + object_creation
  for call edges (this.method stripped), annotations preserved in
  signatures. Passed all 28 tests first try — no bugs found. Registered
  on [.java]. 226/226 total tests pass.)*
- [x] **B9.** Implement Rust extractor. *(2026-04-10:
  `src/pensieve/extractors/rust.py`. Rust-specific: function_item (both
  standalone + inside impl_item), impl_item handling (inherent + trait
  impls with _get_impl_type resolving the target type), trait_item with
  function_signature_item (abstract methods) + function_item (default
  impls), struct_item, enum_item, type_item (type aliases), const_item,
  use_declaration (simple + nested `{self, A, B}` + glob), pub/pub(crate)
  visibility, `///` doc comments via outer_doc_comment_marker (filtered
  from rationale tags), self/&self/&mut self parameters, return types
  after `->`, self.method() call stripping, closure isolation. Second
  extractor to pass all tests first try (29/29). Registered on [.rs].
  255/255 total tests pass.)*

  **ALL 6 LANGUAGE EXTRACTORS COMPLETE (B4–B9).** Total: Python, JS,
  TS, Go, Java, Rust. 255 tests across 10 test files. Registered
  extensions: .py, .js, .mjs, .cjs, .ts, .tsx, .go, .java, .rs.
  Architecture consistent: 3-pass (declarations → call edges →
  rationale comments), flat symbols with parent, continuous confidence
  scores, schema-validated output.
- [x] **B10.** Implement comment-tag extraction across all languages
  (`# WHY:`, `# NOTE:`, `# IMPORTANT:`, `# HACK:`, `# TODO:`,
  language-aware comment syntaxes).
- [x] **B11.** Implement SHA256 cache layer in `agent-docs/.cache/`.
  Re-runs only re-extract files whose hash changed. *(2026-04-10:
  `src/pensieve/cache.py` — `ExtractionCache` class keyed by SHA256
  of file content. get/put/has/invalidate/clear/stats API. Version-
  aware invalidation (extractor_version mismatch → cache miss).
  Corrupted-file resilience (JSON parse errors → warning + cache miss,
  never crash). Lazy directory creation on first put(). Hash integrity
  check (cached sha256 must match lookup key). Documented: caller must
  fix file_path on shared-content cache hits. 29 tests covering all
  5 identified failure cases + normal path + real extraction round-trip.
  332/332 total tests pass. Not implemented: concurrent-write safety
  (not needed for single-agent usage).)*
- [x] **B12.** Implement `pensieve scan <repo>` — full repo extraction,
  produces `agent-docs/structure.json`. *(2026-04-10:
  `src/pensieve/scan.py` with `scan_repo()` + `_collect_files()`.
  CLI subcommand `pensieve scan <path> [--output-dir]` registered in
  cli.py. Walks repo, detects files by supported extension, extracts
  via extract_file() with SHA256 cache from B11, normalizes file_path
  to relative (fixes review finding #4), writes structure.json.
  Default ignore patterns for 15+ common dirs (node_modules, .git,
  vendor, __pycache__, .venv, agent-docs, etc.) with os.walk pruning
  (ignored subtrees are never traversed). Validates fresh extractor
  output via validate_extraction() before caching or writing —
  schema-invalid extractions go to errors channel, not files[].
  extract_file()→None on supported extensions counted as failure, not
  skip. 24 tests covering: file detection with pruning verification,
  mixed-language scan, cache behavior, ignore patterns, CLI dispatch,
  empty/error cases, invalid extractor output, None-on-supported-file.
  SCOPE NOTE: graph.json deferred to B13 (cross-file edges needed).
  363/363 total tests pass.)*
- [x] **B13.** Aggregate cross-file edges: import graph, call graph (where
  resolvable), file→test mapping via naming heuristics. *(2026-04-10:
  `src/pensieve/graph.py` with `build_graph()`. Module index maps
  importable names → file paths (handles absolute, dotted, relative,
  __init__.py). Import edges resolved for all in-repo modules; external
  imports (stdlib, third-party) tracked separately. Cross-file call edges
  resolved through import tracking: if main.py imports helper from
  utils.py AND main() calls helper(), a cross-file call edge is created.
  Test→source mapping via naming heuristics (test_*.py, *_test.py,
  tests/ directory); test-importing-test filtered out. graph.json
  written by scan_repo() alongside structure.json. 23 tests covering
  import edges, external imports, circular imports, cross-file calls,
  unresolved calls, test detection, relative imports, node structure,
  and two integration tests with scan_repo().
  KNOWN LIMITATIONS: wildcard imports unresolvable without runtime
  analysis; Go import paths (URL-style) and Java package-qualified
  imports have lower resolution accuracy than Python/JS/TS.
  386/386 total tests pass.)*
- [ ] **B14.** Update Phase 2 deep-dive prompts to consume `structure.json`
  + 5–10 sample files chosen by centrality, instead of reading every file
  in the subsystem.
- [ ] **B15.** Validate quality on the calibration repo: LLM-judged
  subsystem doc quality must match or beat pre-Phase-B output.
- [ ] **B16.** Run auto-benchmark from Phase A end state on the
  calibration repo. Phase 2 token cost should drop dramatically; quality
  should be flat or up.
- [ ] **B17.** Add structural extraction to Phase 1 (subsystem mapping) —
  feed the LLM the structural graph instead of letting it explore raw
  files for classification. Chat-first checkpoint preserved.

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

### Phase B status: in progress (B1 complete)

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
