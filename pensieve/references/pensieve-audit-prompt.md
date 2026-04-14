# Pensieve Audit Prompt

Use this prompt after a real coding task to audit whether `pensieve brief` helped in practice.

## When To Use

Use this prompt when:
- you want to evaluate whether Pensieve improved a real task
- you want a concrete post-task audit with numbers, not vague impressions
- you are comparing Pensieve-assisted workflow vs likely grep-first / read-first behavior
- you are validating adoption, speed, token efficiency, and output quality

Do not use this prompt when:
- the task was too small for Pensieve to matter
- `pensieve brief` clearly did not apply
- you are doing a lightweight check instead of a deep audit

## How To Use

1. Run or complete a real coding task.
2. If you used `pensieve brief`, answer the audit with concrete numbers and short justifications.
3. If you did not use `pensieve brief`, answer item 1 and stop unless you want to explain the non-applicability in more detail.
4. Prefer estimates grounded in actual task behavior:
   - files opened
   - grep/glob calls
   - approximate lines read
   - approximate brief size
5. Be honest about counterfactuals:
   - estimates are acceptable
   - invented certainty is not

## Notes

- This is a deep audit prompt, not a lightweight routine check.
- Use it for validation sessions, benchmark-style comparisons, or important manual reviews.
- Optimize for truth, not for proving Pensieve was useful.

---

Pensieve Effectiveness Audit — answer with concrete numbers, not vibes:

1. Did you run `pensieve brief` for this task?
- Yes / No
- If no, stop here and explain why it didn't apply.

2. Counterfactual baseline. Without Pensieve, estimate what you would have done:
- Files opened (full reads): ___
- Grep/Glob calls: ___
- Lines of code ingested into context: ___

3. Actual with Pensieve:
- Files opened: ___
- Grep/Glob calls: ___
- Lines ingested: ___
- Pensieve brief output size (approx lines): ___

4. Optimization estimates (% reduction vs. counterfactual, with a one-line justification each):
- File opens: ___% — justification
- Token usage: ___% — justification (account for the brief's own token cost)
- Wall-clock time: ___% — justification
- Attention dilution (how much irrelevant code entered context): ___% — justification
- Answer quality (was the final output more accurate or complete because of the brief? +/- ___%) — justification

5. Net verdict: Was Pensieve worth it here?
- One of: clear win, marginal win, neutral, marginal loss (brief cost > savings), clear loss
- One sentence why.

6. Failure modes caught.
- Did the brief surface any file you would have missed with grep-first discovery?
- Name it, or say `none`.

7. One improvement.
- If you could change one thing about how you used Pensieve on this task, what would it be?
