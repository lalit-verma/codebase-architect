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
3. **This file** — everything not in PLAN.md.
4. **Pick the next pending milestone in PLAN.md** and execute it.
5. **Update PLAN.md** as you work: tick the milestone checkbox `[x]`,
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
costs ~5× more per token).

The without-docs baseline runs stayed under 200K and used Haiku throughout.

**Implication:** any wiring that puts agent-docs content into main-thread
context will eventually trigger fallback. The fix is **not** to put
docs in main-thread context. The fix is to inline only the load-bearing
content into the system prompt (where it's paid for once and never
accumulates) and use harness-enforced wiring (PreToolUse hooks) to
remind the agent of the rest.

### The quality mechanism: pattern fidelity on the writer

The Medium-bucket benchmark win in v1's full-load runs (lenient pass
70% vs baseline 70%, strict pass 30% vs 20%) came from the **main
thread internalizing pattern conventions** before generating code. When
patterns were the actual text in the agent's context, the writer
reproduced them with verbatim fidelity — variable names, error handling
style, ordering.

When the explore-routing experiment moved doc reads into a subagent,
the main thread saw only summaries of patterns. Strict pass on Medium
fell from 30% to 10%; lenient pass collapsed from 70% to 30%.
**Subagent summarization loses load-bearing detail.**

**Implication:** patterns must reach the writer verbatim. The only way
to do this without triggering long-context fallback is to inline them
into the system prompt, where they're paid for once and never accumulate.

### Why "lean wiring" didn't help either

Between full-load and explore-routing, v1 tried "lean wiring" — fewer
docs read at session start, conditional reads. It produced essentially
the same model mix as full-load (still triggered fallback) because the
agent still loaded enough content over the session to push past 200K.
**The trigger isn't ritual phrasing; it's accumulated tokens.**

## Benchmark history — the numbers

Three benchmarks were run on the same 30-task suite (10 Easy, 10
Medium, 10 Difficult) on the same calibration repo. We don't have the
calibration repo's name in this conversation — see "Open questions"
below.

| Run | Avg tokens | Avg cost | Avg time | Quality | Lenient pass | Verdict |
|---|---|---|---|---|---|---|
| **Full-load wiring (original)** | 1.57M | $1.07 | 3.59m | 7.17 | 46.7% | Cost +11%, lenient −3.3pp vs baseline |
| **Lean wiring (post-Step1-5 ritual cut)** | similar | similar | similar | similar | similar | No meaningful change vs full-load |
| **Explore-routed (subagent reads docs)** | 1.80M | $0.843 | 4.16m | 6.83 | 36.7% | Cost −13% (real win) but tokens +2%, quality −0.47, lenient −13.3pp |
| **Baseline (no agent-docs at all)** | 1.76M | $0.965 | 3.75m | 7.30 | 50.0% | Reference |

**Key observation:** baseline beats every wiring variant on lenient pass
and on quality. Cost wins only come at quality cost.

**The Medium bucket is where the framework's value is concentrated:**
- Full-load Medium: lenient 70% vs baseline 70% (tied), strict 30% vs 20% (+10pp)
- Lean Medium: similar to full-load
- Explore-routed Medium: lenient **30%** vs 70% (−40pp collapse), strict 10% vs 20%

The Medium-bucket collapse on explore-routing is the single most
important data point. It proves pattern fidelity on the writer is
load-bearing for quality.

## graphify deepdive — what we adopted

Lalit pointed me at `/Users/lalit.verma@zomato.com/Desktop/tinkering/graphify-3`,
a Python skill that solves a similar problem (give coding agents
pre-built context to navigate codebases) with a fundamentally different
architecture. Key findings shape v2:

### Things we're adopting from graphify

| What | Why | Phase |
|---|---|---|
| **PreToolUse hook in `.claude/settings.json`** that fires on `Glob\|Grep` and reminds the agent the docs exist | Harness-enforced wiring is structurally stronger than CLAUDE.md instructions because it doesn't rely on agent compliance. Cost is ~30 tokens per Glob/Grep, only when docs exist. | A |
| **AST-first extraction with tree-sitter** | LLM tokens spent on enumeration (functions, classes, imports, calls) is paying retail for wholesale work. Free, deterministic, perfect recall. graphify's measured 71.5× token reduction came primarily from this. | B |
| **SHA256 incremental cache** | Re-runs only re-process changed files. Makes auto-rebuild on commits viable. | B |
| **Auto-measured benchmark per run** | graphify prints token reduction at the end of every run. We need this to catch regressions on every repo, not via external benchmarks weeks later. | A |
| **Worked examples with honest `review.md` files** | They ship `worked/karpathy-repos/review.md` listing what the graph got right AND wrong. Trust comes from publishing failure modes alongside wins. | D |
| **Continuous confidence scores (0.0–1.0) on inferred edges** | More expressive than 4-tier categorical labels. Filterable, sortable, threshold-able. | D |
| **MCP server for structured runtime queries** | Agents can query the artifact directly without reading markdown. | D |
| **Multi-platform skill files generated from a single source** | We currently hand-maintain Claude Code / Codex / Cursor variants. They drift. | D |

### Things we're explicitly NOT adopting from graphify

| What | Why not |
|---|---|
| Multi-modal extraction (PDFs, images, screenshots) | graphify is for the "/raw folder" use case (papers + tweets + diagrams + code). We're a code framework. Scope creep. |
| Leiden community detection / graph topology clustering | Our subsystem identification is human-confirmed and produces named architectural concepts. Algorithmic clustering loses human-meaningful naming. |
| Persistent graph + query DSL as the primary output shape | Different paradigm. We keep markdown as the human-readable view + JSON as the structured store. |
| `--watch` mode | Our re-run cadence is per-major-refactor, not live sync. |
| Hyperedges / embeddings / BFS subgraph queries | Graph-shape features. Our markdown shape doesn't need them. |

### Things our framework has that graphify doesn't (the moat we're keeping)

| What | Why it matters |
|---|---|
| **Pattern recipes** ("To add a new handler: 1. Create `path/x.go` following `path/y.go` 2. Register in `file:line` 3. ...") | The Medium-bucket benchmark win came from this. Tells the writer how to extend, not just what exists. graphify shows topology; we show recipes. |
| **`Conventions` section** with file references | "This codebase uses `Result<T, AppError>` for errors (see `src/errors.ts`)" — uncaptured by graphify. |
| **`Do NOT` / anti-patterns list** | "Do not edit `api-gen/` — it's regenerated." graphify won't catch this. |
| **`decisions.md` for architectural trade-offs** | First-class structure for "we chose X over Y because Z." graphify has rationale nodes from comments but no dedicated trade-off structure. |
| **Chat-first checkpoint** with human-confirmed subsystem boundaries | Catches misclassification before any durable doc is written. graphify trusts its extractor; we don't. |

## v1 → v2 transition state

### What v1 ships today (preserved as fallback)

v1 lives in the same repo at `shared/`, `claude-code/`, `codex/`,
`cursor/`. **Don't touch these directories** unless explicitly asked —
they're the fallback if v2 stumbles.

Recent v1 changes (already shipped, do not redo):

- **Hybrid wiring** (lean wiring → hybrid wiring with inlined nano + Explore enrichment)
  - `shared/templates/agent-protocol-template.md` rewritten for hybrid wiring
  - `claude-code/commands/analyze-synthesize.md` adds Step 1c/1d for nano-digest generation
  - `codex/prompts/3-synthesize.md` mirrors the same change
  - `cursor/SKILL.md` mirrors it
  - `shared/protocol.md` and `shared/docs-schema.md` updated with nano-digest in the output schema
  - `README.md` rewired with hybrid instructions and "Why hybrid wiring" rationale
  - `eval/eval-output.md` Dimension 5 rewritten to evaluate hybrid wiring instead of the old 5-step protocol
  - `eval/eval-toolkit.md` framework-self-check updated
- **New v1 files:**
  - `shared/templates/agent-context-nano-template.md` — the nano-digest template
  - `shared/references/nano-context-rules.md` — generation rules for the nano

The v1 hybrid wiring ships an `agent-context-nano.md` file (≤40 lines)
that's a strict subset of `agent-context.md`, designed to be pasted
directly into CLAUDE.md / AGENTS.md / .cursorrules. This format carries
forward to v2 — the nano-digest design is good, the issue v1 had was
that it didn't ALSO ship a PreToolUse hook to remind agents the rest of
the docs exist.

### What v2 will replace

The whole approach to extraction (Phase 2 deep dives that have the LLM
read every file) is being replaced by AST extraction + LLM
interpretation. The 13-file output sprawl is being reduced to 4 main
artifacts (see PLAN.md "Output schema").

The slash-command-only distribution model is being replaced by a
pip-installable Python package with slash commands as thin wrappers.

## Active open questions (need user input before some milestones)

These are unresolved at the time of this dump and may block specific
milestones. Don't assume answers — ask Lalit when you hit them.

| Question | Blocks | Notes |
|---|---|---|
| **Name and path of the calibration repo** | A13 (run auto-benchmark on calibration repo) | Same repo + same 30 tasks the teammate has been benchmarking externally. Lalit hasn't named it in conversation yet. |
| **Teammate's contact / coordination protocol** | A14 (compare auto-benchmark to teammate's external) | Need the teammate's most recent benchmark numbers to validate against. |
| **Whether to commit at each milestone or batch commits** | Any time after a milestone completes | Lalit has been offered both. No standing preference. Default: ask before committing. |
| **PyPI package name reservation timing** | D8 | Decision deferred until after Phase C. Internal-first for A–B. |

## Things explicitly decided against (don't re-litigate)

| Rejected | Reason |
|---|---|
| 5-step "before every task" loading ritual ("Step 1: read X. Step 2: identify subsystem. Step 5: confirm understanding before writing code.") | Tested in v1's first wiring iteration. Triggered cost regression with no quality gain. |
| "Quote the specific pattern from patterns.md" requirement | Forced extra reasoning turns without improving pass rate. Cut. |
| "Do not skip steps. Do not start writing code until you have read X" framing | Cost driver, not quality driver. |
| Pure subagent routing for all doc reads | Tested in v1's third wiring iteration (explore-routed). Fixed cost but tanked Medium-bucket lenient pass from 70% to 30% via summarization fidelity loss. |
| Reading agent-docs/ files from the main thread | Triggers long-context fallback. The main thread only ever sees the inlined nano-digest (in the system prompt) and reminders from the PreToolUse hook. Deeper docs go through Explore subagents. |
| Time-boxed phases / week estimates | Lalit pushed back. Plan is milestone-driven with proceed criteria. |
| Embeddings / vector search | graphify doesn't use them either. Graph topology + AST structure is enough. |
| Auto-running the benchmark in Phase 3 by default | Cost ($0.50–$2 per run) + time. Opt-in via `--benchmark` flag. |
| 3 months of focused work framing | Lalit specifically called this out. Plan in milestones, not time. |

## Critical gotchas that will surprise a fresh agent

1. **Don't accumulate context in main-thread reads.** The single biggest
   v1 lesson. If you find yourself thinking "the agent should read
   `agent-docs/foo.md`," stop. Either inline what's needed into the nano-
   digest or make it accessible via Explore subagent / MCP server / hook
   reminder.

2. **The Medium bucket is the canary.** Watch lenient pass rate on Medium-
   difficulty tasks. If it drops, pattern fidelity has been broken
   somewhere in the pipeline. This was the early warning we missed in v1.

3. **The PreToolUse hook is harness-enforced, not LLM-instructed.** It's
   installed in `.claude/settings.json`, fires before Glob/Grep, and
   echoes a one-line reminder. The agent doesn't choose to trigger it.
   This is mechanically different from CLAUDE.md instructions and you
   should think of it as a fundamentally stronger wiring primitive.

4. **AST extraction is free; LLM extraction is expensive AND worse.**
   When in doubt about who should do work, default to: "if it can be
   extracted by tree-sitter, the LLM should not be doing it."

5. **The chat-first checkpoint is preserved from v1.** Even with AST
   extraction, the user must confirm the subsystem map before any
   durable doc is written. graphify doesn't do this. We do, because
   algorithmic clustering produces wrong-but-confident boundaries on a
   meaningful fraction of repos.

6. **Two load-bearing artifacts: nano + patterns.** Everything else is
   either supporting these or human-readable secondary docs. If a new
   feature doesn't help the nano or the patterns, it probably doesn't
   belong.

7. **v1 directories are FALLBACK, not legacy.** Don't refactor or "clean
   up" `shared/`, `claude-code/`, `codex/`, `cursor/`. They're the
   working escape hatch if v2 stumbles. Touching them risks our
   ability to fall back.

8. **Lalit's teammate is doing external benchmarks in parallel.** Don't
   assume our auto-benchmark replaces theirs. In Phase A specifically,
   their external benchmark is the QA layer that catches measurement
   bugs in our auto-benchmark. The two should converge within ~10% on
   the same calibration repo before we trust the auto-benchmark alone.

## Operational guidance (how to actually do the work)

### Use the task tool, but PLAN.md is canonical

The Task tool is for in-session tracking. PLAN.md is for cross-session
state. Don't rely on the task tool to remember anything between
sessions — it'll get cleaned up. Update PLAN.md after every milestone,
including:

- Tick the checkbox `[x]` on the completed milestone
- Add a one-line completion note in the milestone bullet (date + what
  was done)
- Append a note to the Phase Notes section of the current phase
- Update the Status header at the top of PLAN.md if the phase status
  changed
- If a new decision was made, append to the Decisions log table at the
  bottom
- If a kill criterion was hit, append to the Kill criteria results table
- If a non-obvious lesson emerged, append to the Notes / lessons /
  unlearning section

### Tools and permissions

- Use Read, Write, Edit, Glob, Grep, Bash as standard
- Prefer Edit over Write for modifying existing files
- Prefer dedicated tools over Bash equivalents (Read not cat, Glob not
  find, Grep not grep, etc.)
- Tree-sitter / Python work in Phase B+ requires creating a real Python
  package — that's fine, the Bash tool can handle pip install, pytest
  runs, etc.

### When to ask vs when to just do

- **Just do:** well-scoped milestones from PLAN.md (the milestones are
  intentionally written to be executable)
- **Ask first:** decisions that affect file layout, breaking changes,
  destructive operations, anything that touches v1 directories, name
  changes
- **Push back when you disagree:** if a milestone seems wrong given
  what you've discovered, say so. Don't execute mechanically.

### When the benchmark says we're losing

This will happen at least once. The honest path is:

1. Record the failure in the kill criteria results table in PLAN.md
2. Don't proceed to the next phase
3. Iterate on the failing milestones in the current phase
4. If iteration doesn't move the number, surface the failure to Lalit
   and discuss whether the design needs to change

Don't rationalize a regression as "well, this metric isn't really
representative." The whole point of measurement is honesty.

## Parallel agent coordination (if multiple agents are working at once)

If Lalit is running you in parallel with another agent:

1. **Agree on milestone ownership before starting.** Don't both work
   on A2 simultaneously.
2. **Avoid touching the same files.** PLAN.md is the only file both
   agents will need to update — coordinate updates carefully.
3. **Default rule:** when two agents are active, one is the "executor"
   on the active milestone and the other is in a holding / consulting
   role (review-only) until ownership is reassigned.
4. **If you discover the other agent has touched a file you're about
   to modify**, re-read the file before editing. The state may have
   changed.
5. **PLAN.md edits are not safe to parallelize.** Whoever finishes a
   milestone first updates PLAN.md, the other waits and re-reads
   before their next update.

## Quality expectations across agent instances

You should know this: a different agent reading this dump will not
produce identical output to the agent that wrote it. Same model,
different conversation history → different stylistic accumulations and
some judgment calls will diverge.

Specifically:

- **Execution-focused milestones** (write a file, install a hook,
  extract AST from a Python file): comparable quality across agents
- **Judgment calls** (when to push back, how much detail in a response,
  whether to ask vs decide): some divergence; Lalit may need to
  recalibrate
- **Design decisions** that aren't in PLAN.md: will diverge. When you
  encounter one, ask before deciding — don't assume the other agent
  would have decided the same way.

If you find yourself making a decision that's not anchored in PLAN.md
or this file, that's a signal to ask Lalit rather than proceed.

## What good looks like at the end of Phase A

Phase A ends with a number: `benchmark.json` showing whether the hybrid
wiring + PreToolUse hook beats baseline on the calibration repo. The
target is:

- Lenient pass rate ≥ baseline (no quality regression)
- Cost ≤ 105% of baseline
- Auto-benchmark numbers correlate with the teammate's external
  benchmark within ~10%

If those conditions hold, Phase B starts. If they don't, we iterate on
the wiring before moving on. The proceed criterion is not a deadline;
it's a quality gate.

## File map (current state of the repo)

```
codebase-analysis-skill/
├── README.md                       v1 README (preserved)
├── PLAN.md                         ★ canonical v2 plan + tracker
├── pensieve-context.md             ★ this file
├── pensieve/                       ★ v2 build (Phase A scaffolding)
│   ├── README.md
│   ├── python/.gitkeep             populated in A2
│   ├── commands/.gitkeep
│   ├── templates/.gitkeep
│   ├── references/.gitkeep
│   ├── examples/.gitkeep
│   ├── worked/.gitkeep
│   └── tests/.gitkeep
├── shared/                         v1 fallback — don't touch
├── claude-code/                    v1 fallback — don't touch
├── codex/                          v1 fallback — don't touch
├── cursor/                         v1 fallback — don't touch
└── eval/                           v1 eval rubrics (updated for hybrid wiring)
```

## Pointer to graphify (the comparison framework)

If you need to understand the reference design we're learning from,
graphify lives at:

```
/Users/lalit.verma@zomato.com/Desktop/tinkering/graphify-3
```

The most important files in graphify for understanding the design we're
adopting:

| File | What to look at |
|---|---|
| `README.md` | The product story, the 71.5× token reduction claim, the always-on hook explanation |
| `ARCHITECTURE.md` | The pipeline (detect → extract → build → cluster → analyze → report → export), module responsibilities |
| `graphify/__main__.py` lines 26–38 | `_SETTINGS_HOOK` — the PreToolUse hook installer pattern we're stealing for Phase A |
| `graphify/__main__.py` lines 220–251 | `_install_claude_hook` — how the hook gets written to `.claude/settings.json` |
| `graphify/extract.py` | AST extraction patterns we'll mirror in Phase B |
| `graphify/cache.py` | SHA256 cache pattern for incremental re-runs |
| `graphify/benchmark.py` | Auto-benchmark pattern (their version measures token reduction; ours will measure cost/quality/time on simulated tasks) |
| `worked/karpathy-repos/review.md` | The "honest review" format for worked examples |
| `worked/karpathy-repos/GRAPH_REPORT.md` | Their nano-equivalent — a one-page summary the agent reads |

Don't copy graphify's code wholesale. The goal is to learn the patterns
and apply them with our own design constraints (markdown-friendly
output, pattern recipes, chat-first checkpoint, decisions as
first-class).

---

**Final note:** if anything in this file conflicts with PLAN.md, PLAN.md
wins. This file is a context supplement, not a replacement.
