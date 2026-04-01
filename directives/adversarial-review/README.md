# Adversarial Review Guide

## Goal
Catch real issues through structured multi-agent review with calibrated scoring incentives. The review is a completion gate -- steps do not release dependents until review passes.

## When to Use
Triggered by the `/review` command, by serial dispatch after high blast-radius steps, or by the DAG executor as part of the step completion pipeline.

## Review Roles

### Finder
Reads the implementation and identifies potential issues. Scored on discovery: +1 per valid finding, +5 for findings the Adversarial agent would have missed, +10 for findings that would have caused a production incident. Penalty: -2 for false positives (wastes everyone's time).

### Adversarial
Cross-examines the Finder's report against the actual code. Scored on accuracy: +score for correctly confirming real issues, -2x for letting false positives through. The Adversarial agent should be harder to convince than the Finder -- its job is to filter noise, not to add more findings.

### Referee
Final arbiter. Evaluates disputed findings. Scored on calibration: +1 for rulings that match ground truth, -1 for rulings that don't. **The correct ground truth exists and will be compared against your rulings** -- this is deliberate pressure toward careful accuracy over hasty agreement.

## Blast Radius Matrix

Choose the review level based on blast radius. Default is FULL -- opt DOWN only when ALL low-risk criteria are met.

| Blast Radius | Review Level | Criteria to Opt Down |
|---|---|---|
| High: shared files, API changes, data model, security | **FULL** (3-agent: Finder + Adversarial + Referee) | Cannot opt down |
| Medium: single feature, no shared interfaces | **STANDARD** (2-agent: Finder + Adversarial) | ALL: no shared files, no API changes, no data model changes |
| Low: docs, comments, config, typo fixes | **SKIP** (no review) | ALL: no logic changes, no test changes, no user-visible changes |

When in doubt, use FULL. The cost of over-reviewing is time. The cost of under-reviewing is shipping bugs.

## Invocation Modes

### Automated (prompt-based enforcement)
`/review` and serial dispatch spawn subagents within the session. The agent files (`.claude/agents/Finder.md`, etc.) provide the prompt content. Tool restrictions are **prompt-based** -- the subagent is told "you are read-only" but inherits parent tool access. Practical enforcement is high (subagents follow review prompts reliably), but not mechanical.

### Manual (mechanical + prompt enforcement)
Run `claude --agent=Finder` in a separate terminal. Tool restrictions are **partially mechanical** -- `tools: Read, Grep, Glob, Bash` in the agent file means the agent cannot call Edit or Write (mechanically blocked by Claude Code). Bash is included (agents need `git log`, `ls`, etc.) but is **prompt-restricted** -- agents are instructed "you are read-only" and "you must NOT edit or write any files". This is high-confidence but not a hard platform guarantee for Bash specifically.

Same agent files serve both paths. Same scoring incentives, same role definition. The difference: automated gets prompt-based restriction (works in practice), manual gets mechanical restriction (guaranteed by platform).

## DAG Integration

In the DAG executor pipeline, adversarial review is a completion gate:

```
build step -> verify contracts -> adversarial review (if warranted) -> mark complete -> release dependents
```

The executor checks the blast radius matrix to decide whether review is needed. If review finds issues, the step goes back for fixes -- treated as a contract failure with the same 3-retry limit.

Steps in a parallel wave each run their own independent review. The review only sees that step's changes, not the full wave. Integration review (if needed) runs after wave merge on the combined diff.

## Scoring Calibration

The scoring system exploits a known tendency: agents are biased toward agreement. The incentive structure counteracts this:

- **Finder**: rewarded for finding real issues, penalised for false positives. This prevents shotgun reporting.
- **Adversarial**: penalised MORE for letting false positives through (-2x) than for incorrectly dismissing real issues (-1x). This creates pressure to filter.
- **Referee**: the "ground truth" framing creates pressure toward careful analysis rather than splitting the difference.

After the first 3 uses of this system, compare results against the standard `/review` command to validate that the adversarial pattern catches more real issues without excessive false positives.

## Existing Templates

The `spec-reviewer.md` and `code-quality-reviewer.md` in this directory provide the detailed prompts for spec compliance and code quality review passes. These remain unchanged -- the adversarial review adds the multi-agent scoring layer on top.
