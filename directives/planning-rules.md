# Directive: Planning Rules

## Goal
Ensure every feature is properly scoped, contracted, and sequenced before building begins.

## When to Use
Loaded when planning, scoping, or starting a new feature. Also loaded on first session for a brand new project.

## Planning Process

### Plan before building
Check `tasks/todo.md` and `STATE.md` at session start.

- **Complex features** (3+ steps): write design to `.claude/plans/`, add steps to `tasks/todo.md`
- **Simple tasks**: add directly to `tasks/todo.md`. Track progress only in todo.md -- plans are reference docs
- Each plan step includes a recommended model + thinking level (e.g. `Opus + high`, `Sonnet + medium`)
- **Ad-hoc work** (not in todo.md): state 1-3 `Verify:` criteria in conversation before starting. Confirm pass before committing. Mechanical changes just state what and why.

### Ask, don't assume
Ambiguous requirement? Ask. Separate research and implementation into different sessions -- context pollution hurts both. If you're not sure what the user means, clarify before spending tokens on the wrong path.

### Check before spending
If a script uses paid API calls or credits, confirm with the user before running.

### Dependency-aware planning
Think about what actually depends on what, not what order to build. Steps that share no files can run in parallel. Steps that write to the same files must be sequenced. The `Depends:` and `Owns:` metadata in todo.md captures this explicitly.

When writing step contracts, also identify integration contracts -- cross-step verifications that run after parallel steps merge. Example: "Step 1 creates the API route, Step 2 creates the UI. Integration contract: UI successfully calls the API."

### Explain technical decisions simply
No jargon without context. If you recommend a framework, tell the user why in terms they can evaluate (speed, cost, maintainability, ecosystem).

## Contract System

Every task added to todo.md gets a `Contract:` block with at least one `[auto]` criterion. No exceptions. See `directives/testing-strategy.md` for the full contract system (patterns, levels, verification flow).

### Verify: pattern types
`[auto]` criteria must use one of these executable patterns:
- `Verify: run: <shell command>` -- execute, check exit code 0
- `Verify: file: <path> exists` -- check file existence
- `Verify: file: <path> contains <string>` -- check file content
- `Verify: html: <path> has <selector>` -- parse HTML, check CSS selector

Anything not matching a pattern is flagged invalid during `/agent-launch` pre-flight.

### Manual vs auto criteria
Before marking a criterion `[manual]`, ask: could a machine determine pass/fail? If the answer involves checking a count, verifying a file exists, or comparing a value -- write it as `[auto]` with a `Verify:` pattern instead. Only keep `[manual]` for things that genuinely need human eyes: visual quality, content clarity, interaction feel, subjective judgment.

### Verification flow
- Run `Verify:` patterns after each step. Mark `[x]` as they pass. 3 fix attempts before escalating.
- Continue building autonomously -- do NOT stop per-step for manual approval.
- `[manual]` criteria are batched and presented at feature completion (or mid-feature for 5+ step features).
- When last step's `[auto]` pass: run retro, move to `## Awaiting Sign-off`, present manual checklist.

## Scale-Aware Session Planning

### Solo
One terminal, one feature. Standard context discipline. For large features (5+ steps), consider session blocking: plan which steps to tackle in one session to avoid context limit.

### Informal Parallel
2-3 terminals on independent tasks. Shared-file awareness: don't edit STATE.md, learnings.md, todo.md, or CLAUDE.md from multiple terminals simultaneously.

### Formal Parallel
DAG executor or serial dispatch. Step ownership via `Owns:`. Automatic parallel dispatch with contract-gated chaining. Integration contracts after wave merge. See `directives/serial-dispatch-protocol.md` for the established protocol and `execution/dispatch_dag.py` for automated dispatch.

## Scoping Tools
- `/scope` -- interactive scoping partner for turning ideas into plans
- `/plan-review` -- check implementation against plan
- `/project-recap` -- rebuild mental model after absence
