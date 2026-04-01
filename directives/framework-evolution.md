# Directive: Framework Evolution

## Goal
Track Claude Code platform capabilities and prefer native features over custom DOE systems when they reach parity. Prevent DOE from becoming bloated by reimplementing what the platform provides.

## When to Use
Loaded when evaluating new Claude Code features, planning infrastructure changes, or deciding whether to build custom tooling.

## Foundation Absorption Principle

DOE's value is in patterns and discipline, not in reimplementing what the platform provides.

When a native Claude Code feature reaches parity with a custom DOE system:
1. Evaluate whether the native feature covers the DOE system's requirements
2. If yes: migrate to native, remove the custom system, log the absorption in learnings.md
3. If partial: use native where it covers, keep custom only for the gap
4. If no: keep custom, note the gap, revisit when the platform evolves

**The test:** "Would removing this custom system and using the native feature change the quality of the output?" If no, absorb it.

## Native Features to Track

### Currently Used by DOE
- `claude -w` (worktrees) -- used by DAG executor for parallel step isolation. Native since Claude Code launch. DOE adds contract verification and ownership enforcement on top.
- Custom agents (`.claude/agents/`) -- used for adversarial review roles (Finder, Adversarial, Referee). Platform-enforced tool restrictions when run via `claude --agent=X`.
- Hooks (PostToolUse, PreToolUse, SessionStart) -- used for heartbeats, context tracking, audit enforcement. Native hook system.

### Watch for Parity
- `/loop` (recurring task automation) -- potential for PR babysitting, deployment monitoring. Currently manual.
- `/batch` (mass parallel dispatch) -- potential for large migrations, bulk refactors. Currently manual multi-terminal.
- `/branch` (session forking) -- potential for exploration without context pollution. Currently approximated by `/clear` + restart.
- Built-in task tracking -- if Claude Code ships native task/step management, evaluate against todo.md contracts.
- Built-in code review -- if Claude Code ships native review with scoring, evaluate against adversarial review protocol.

## Decision Framework

When considering building a new custom system:

1. **Does a native feature exist?** Check Claude Code docs and changelog first.
2. **Is the gap real?** Sometimes the native feature works differently but achieves the same outcome.
3. **Is the gap permanent?** Platform features evolve fast. If the gap is likely to close in weeks, wait rather than build.
4. **Is the custom system worth maintaining?** Every custom system adds maintenance burden, context tokens, and onboarding friction.

Default: use native. Override only when the gap is real, permanent, and the custom system provides measurable quality improvement.

## Logging Absorptions

When a native feature absorbs a custom DOE system, log in learnings.md:
```
- [framework-evolution] Absorbed X into native Y. Reason: Z. Removed: [files]. [date]
```
