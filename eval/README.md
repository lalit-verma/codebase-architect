# Evaluation Rubrics

Two evaluation prompts for grading the codebase analysis framework
and the documentation it produces.

## Which eval to use

| Situation | Use |
|-----------|-----|
| Evolving the framework (changing prompts, templates, references) | `eval-toolkit.md` |
| Comparing this framework against an alternative approach | `eval-toolkit.md` |
| Checking output quality after running the tool on a repo | `eval-output.md` |
| Debugging why a coding agent performed poorly with these docs | `eval-output.md` |
| Both — full quality audit | Run `eval-toolkit.md` first, then `eval-output.md` on a real run |

## How to run

Paste the eval prompt into a coding agent (Claude Code, Codex, or
Cursor) and point it at the target:

- **eval-toolkit.md** needs access to the framework files only
  (shared/, claude-code/, codex/, cursor/)
- **eval-output.md** needs access to BOTH the `agent-docs/` output
  AND the source repository that was analyzed (for spot-checking
  file references)

Both produce a scored report with PASS/PARTIAL/FAIL per dimension,
quoted evidence, and a prioritized gap list.

## Scoring

**eval-toolkit.md:** 8 weighted dimensions, max score 28.
Grades: Excellent (24-28), Good (18-23), Needs Work (12-17),
Fundamental Issues (<12).

**eval-output.md:** 10 weighted dimensions, max score 32.
Grades: Excellent (28-32), Good (22-27), Needs Work (16-21),
Significant Gaps (<16).

Both include critical-fail override rules — certain foundational
failures automatically cap the grade regardless of other scores.

## Known Limitations

**These are manual rubrics, not empirical benchmarks.** They do not:

- Compare cold-start vs doc-loaded agent behavior on identical tasks
- Measure wall-clock time savings from loading docs
- Run automated checks (line counts, grep scans are done by the
  evaluating agent, not by a script)
- Produce statistically significant results across multiple repos

**To build an empirical benchmark,** you would need to:

1. Select a set of representative tasks across multiple repos
2. Run each task twice: once cold-start, once with agent-docs loaded
3. Measure: task completion rate, correctness, time to first correct
   file edit, convention violations
4. Compare the delta — that's the tool's actual value

The manual rubrics are a proxy for this: they predict whether the docs
*would* help an agent, based on structural quality and simulated task
navigation. They don't prove it empirically.

## Extending the evals

To add new dimensions or criteria:

1. Add the dimension to the appropriate eval file with weight, checks,
   and grading criteria
2. Update the weighted scoring table in the Synthesis section
3. Update the max score and grade bands
4. If the new dimension checks something that should be a
   critical-fail, add it to the Critical-Fail Overrides section
