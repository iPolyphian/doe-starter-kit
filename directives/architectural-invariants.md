# Directive: Architectural Invariants

## Goal
Define truths that must survive any refactor, migration, or feature addition. These are non-negotiable constraints -- if a change would violate one, stop and flag it before proceeding.

## When to Use
- Before any refactor or architectural change -- read this first
- When /review flags a potential breaking change
- When proposing a new pattern or dependency
- At session start if working on structural changes

## Invariants

### DOE Architecture
1. **Execution scripts are always deterministic.** Python or bash. No LLM calls inside execution scripts. If a script needs AI reasoning, that happens in orchestration (the conversation), not in the script.
2. **Directives are natural language, not code.** No executable logic in `directives/`. They define goals, inputs, process, outputs -- Claude reads and follows them.
3. **Progressive Disclosure is the context management strategy.** CLAUDE.md stays compact (under 150 lines). Detailed instructions live in directives, learnings, and plans -- loaded on demand via triggers.

### Session Integrity
4. **STATE.md reflects current position, not history.** Replace stale info, don't accumulate. History lives in git log and archive.md.
5. **learnings.md captures reusable patterns, not session notes.** Each entry must be actionable by a future session that has no context about the current one.
6. **One task, one commit.** Every commit is independently revertable. No batching.

### Safety
7. **Secrets live in .env only.** No API keys in code, comments, logs, or committed files.
8. **No destructive git operations without explicit permission.** Force-push, hard reset, branch deletion, revert -- all require user confirmation.
9. **/wrap runs before ending a session.** Session state must be persisted so the next session can pick up cleanly.

### Extensibility
10. **New invariants require user approval.** Claude can propose additions to this list but must not add them unilaterally. These are constitutional constraints, not suggestions.

## Process
When a proposed change would violate an invariant:
1. Stop before making the change
2. Name the invariant that would be violated (by number)
3. Explain why the change conflicts
4. Propose an alternative that preserves the invariant
5. If no alternative exists, ask the user whether to proceed (they can override)

## Edge Cases
- A user explicitly asks to violate an invariant (e.g. "put the API key in the script") -- warn clearly, cite the invariant, but comply if they insist. Log the exception in learnings.md.
- Two invariants conflict -- flag both, explain the tension, let the user resolve it.
- A new pattern doesn't clearly violate any invariant but feels architecturally wrong -- mention it as a pitch (Rule 9), don't block on it.

## Verification
- [ ] No execution scripts contain LLM/API calls for reasoning
- [ ] CLAUDE.md is under 150 lines
- [ ] STATE.md has no accumulated history (just current position)
- [ ] All secrets are in .env, not in code
