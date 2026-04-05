# Deep Comparative Analysis: merged-claude-framework vs merged-framework-cursor

## Context

This repository contains a codebase analysis tool that generates architecture documentation optimized for coding agents. Two independent "merged" versions of this tool exist in the repo — each was created by a different AI agent session that merged the same two original frameworks (claude-output and codex-output) into what it considered the best synthesis.

Your job is to do a deep, rigorous comparative analysis of both and determine which one better achieves the tool's objective.

## The Tool's Objective

**Primary:** Maximize coding agent efficiency. The generated documentation should give Claude Code, Codex, and Cursor agents deep, structured understanding of any codebase so they write better code — fewer convention violations, fewer architectural mistakes, less wasted context.

**Secondary:** Human readability. Developers should also be able to read the output and understand the system.

## The Two Candidates

**Candidate A: `merged-claude-framework/`** (30 files)
- Created by a Claude Code session
- Structure: `claude-code/commands/`, `codex/prompts/`, `cursor/install.md`, `shared/` (references, templates, examples), `PLAN.md`, `README.md`
- Notable unique files: `PLAN.md`, `shared/protocol.md`, `shared/docs-schema.md`, `shared/references/agent-context-rules.md`, `shared/references/pattern-detection-guide.md`, `shared/examples/` folder, `shared/templates/agent-context-template.md`

**Candidate B: `merged-framework-cursor/`** (24 files)  
- Created by a Cursor session
- Structure: `claude-code/commands/`, `codex/prompts/`, `cursor/SKILL.md`, `shared/` (references, templates), `README.md`
- Notable unique files: `shared/templates/agent-protocol.md`, `shared/templates/sub-module.md`, `cursor/SKILL.md`

## Analysis Requirements

Do NOT rush. Quality and depth matter more than speed. Read every file in both directories before forming conclusions. For each dimension below, cite specific file paths and quote specific passages to support your claims.

### Dimension 1: Core Workflow Quality
Compare the 3-phase workflow (Discover → Deep Dive → Synthesize) implementation in both. For each phase, read the Claude Code command AND the Codex prompt AND the Cursor integration. Evaluate:
- Clarity of instructions to the agent running the analysis
- Completeness of what gets captured
- State management between phases (`.analysis-state.md`)
- Error handling and edge cases (what happens if a phase fails or is re-run?)
- Self-containedness of prompts (can the agent execute without external context?)

### Dimension 2: Agent-First Documentation Design
The core differentiator of this tool is that output is optimized for coding agents, not just humans. Evaluate:
- Do the templates produce documentation that agents can efficiently consume?
- Are there modification guides telling agents HOW to change code in each subsystem?
- Are there pattern/convention capture mechanisms so agents match existing code style?
- Are there playbooks for common changes?
- Is there an agent loading protocol (how to wire output into CLAUDE.md, AGENTS.md, .cursor/rules)?
- Confidence labels (Confirmed/Inference/UNCERTAIN/NEEDS CLARIFICATION) — present and consistent?

### Dimension 3: Recursive Decomposition
Both should support breaking large subsystems into sub-modules. Evaluate:
- Are triggers for decomposition clearly defined (file count, responsibility count)?
- What's the max depth? Is it enforced?
- Is there a sub-module template or does it reuse the subsystem template?
- How does recursion interact with state management?

### Dimension 4: Cross-Platform Parity
The tool must work equally well on Claude Code, Codex, and Cursor. Evaluate:
- Do all three platforms get equivalent functionality?
- Are there features present in one platform's prompts but missing from another?
- Is the Cursor integration a proper SKILL.md or something weaker?
- How does each handle the hybrid approach (self-contained prompts vs referencing shared resources)?

### Dimension 5: Operational Guidance Quality
Evaluate the supporting references and guardrails:
- Ecosystem playbook (language-specific exploration commands)
- Scale and scope rules (reading depth by repo size)
- Subsystem mapping rubric (what counts as a subsystem)
- Anti-patterns and quality bar
- Checkpoint examples

### Dimension 6: Re-run / Augmentation Behavior
The tool should support re-running on a repo with existing `agent-docs/` without overwriting. Evaluate:
- Is augment-vs-overwrite behavior explicitly defined?
- How does each handle detecting existing documentation?
- Is the behavior consistent across all three platforms?

### Dimension 7: README and Onboarding
- How clear is the setup process for each platform?
- Is there a post-generation wiring step (telling agents to read the output)?
- Could a developer with no prior context set this up from the README alone?

### Dimension 8: Unique Strengths
What does each candidate have that the other lacks entirely? For each unique element, assess whether it's genuinely valuable or unnecessary complexity.

## Output Format

For each dimension:
1. **Winner** — which candidate is stronger on this dimension (or "Tie")
2. **Evidence** — specific file paths and quoted passages supporting the verdict
3. **Gap** — what the loser is missing or doing worse

Then provide:
- **Overall Verdict** — which candidate should be kept, with confidence level
- **Cherry-pick List** — specific elements from the losing candidate worth merging into the winner
- **Remaining Gaps** — things neither candidate handles well that should be addressed

Do not hedge. Take clear positions. Support them with evidence.