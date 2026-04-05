# Synthesis Prompt Template

This is the final phase. Generate this as `docs/analysis-prompts/synthesis.md`,
ready to paste into a fresh Claude Code session after all deep dives
are complete.

---

## Prompt Template

```
Read all files in docs/ — both the architecture overview and every
domain deep dive. Then produce two documents.

---

### Document 1: docs/README.md

This is a navigation index for the architecture documentation.
Someone new to this repo should open this first.

Write it with these sections:

## About This Documentation
- One paragraph: what this repo is and what these docs cover
- When the docs were generated and what they're based on
- Caveat that these were auto-generated and may contain errors

## Reading Order
A numbered list recommending the order to read the docs, with a
one-sentence reason for each. Structure as:
1. Start with X because {reason}
2. Then Y because {reason}
...

## Table of Contents

| Document | Covers | Key Topics |
|----------|--------|------------|
| {doc path} | {subsystem} | {3-4 keywords} |

## System Map

Mermaid diagram showing all subsystems and their dependencies —
consolidated from the individual deep-dive dependency graphs. This
should be the single diagram someone looks at to understand how the
whole system fits together.

Color-code or group by:
- External-facing (handles requests from outside)
- Core (business logic, orchestration)
- Infrastructure (storage, messaging, config)

## Glossary

Extract recurring terms, abstractions, and domain-specific vocabulary
from across all docs. For each:

| Term | Meaning | Where Used |
|------|---------|------------|
| {term} | {definition} | {which subsystems} |

Focus on terms that are:
- Used across multiple subsystems (shared vocabulary)
- Domain-specific (not generic programming terms)
- Potentially confusing (overloaded terms, internal jargon)

Keep README.md under 250 lines. It's a map, not a document to read
end-to-end.

---

### Document 2: docs/architecture-lessons.md

This is the learning payoff. It synthesizes what the deep dives
revealed into transferable architectural knowledge.

Write it with these sections:

## Key Architectural Decisions

The 5 most significant design decisions in this codebase. For each:

### {Decision Title}
- **What:** {the choice that was made}
- **Where:** {which subsystems it affects}
- **Why (inferred):** {the likely reasoning — technical constraints,
  team structure, performance, etc.}
- **Trade-off:** {what was gained vs. what was given up}
- **Verdict:** {your assessment — good trade-off? Reasonable for the
  constraints? Something you'd do differently?}

## Patterns Worth Adopting

Architectural patterns from this codebase that are well-executed and
transferable to other projects. For each:

### {Pattern Name}
- **What it is:** {description}
- **Where it's used:** {specific files/subsystems}
- **Why it works well:** {what problem it solves cleanly}
- **When to use it:** {the conditions that make this pattern a good fit}
- **Example:** {brief code reference or structural description}

Aim for 3-5 patterns.

## Patterns to Avoid or Improve

Things that create problems, add unnecessary complexity, or that you'd
approach differently. For each:

### {Pattern Name}
- **What it is:** {description}
- **Where it's used:** {specific files/subsystems}
- **What goes wrong:** {the concrete problem it causes}
- **Better alternative:** {what you'd do instead and why}

Be specific — "the code is messy" is not useful. "The provider
abstraction leaks implementation details because X, which causes Y
when Z" is useful.

Aim for 3-5 anti-patterns.

## Cross-Cutting Observations

Things that don't fit neatly into one subsystem but matter across the
whole codebase:
- Error handling philosophy and consistency
- Logging and observability approach
- Testing philosophy and coverage patterns
- Code organization conventions
- Dependency management approach

## Comparison to Alternatives

How does this codebase's approach compare to other known ways of
solving the same problems? Reference specific architectural choices
and note how other well-known projects or frameworks approach them
differently. This is where the user extracts "what I'd do if I built
this from scratch" insights.

## If You Only Read 3 Files

Recommend exactly 3 source files (not docs — actual code files) that
give the deepest understanding of how this system works. For each:
- File path
- Why this file matters
- What you'll understand after reading it

Keep architecture-lessons.md under 600 lines.

---

Rules:
- Cite file paths for every claim.
- Mermaid for all diagrams.
- Base everything on the docs you just read — don't re-explore
  the codebase.
- If multiple deep dives noted the same concern or pattern, consolidate
  rather than repeating.
- Be opinionated in the lessons doc. The user is here to learn —
  hedged non-answers aren't useful. State your assessment and explain
  your reasoning.
```

---

## Customization Notes

When generating this prompt file:

1. If the user stated a specific purpose in Step 2 (e.g., "learning
   to build something similar"), add to the Comparison section:
   "Pay special attention to patterns that would transfer to
   {user's context}."

2. If the user flagged specific areas of interest, add:
   "In the Key Architectural Decisions section, prioritize decisions
   related to {user's interest areas}."

3. For small repos where only 2-3 deep dives were done, scale the
   document down — 3 decisions instead of 5, 2 patterns instead of
   3-5.
