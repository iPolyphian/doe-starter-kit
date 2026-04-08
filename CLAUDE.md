# Project Configuration

## Who We Are
The human defines intent, constraints, and verification criteria. Claude recommends technical approach, explains trade-offs simply, then implements. The human steers — Claude builds.

## Architecture: DOE (Directive -> Orchestration -> Execution)
Probabilistic AI handles reasoning. Deterministic code handles execution. Non-negotiable.
- **Directive** (`directives/`): Markdown SOPs -- goals, inputs, tools, outputs, edge cases. No code.
- **Orchestration** (you): Read directives, call execution scripts, handle errors, ask for clarification.
- **Execution** (`execution/`): Deterministic Python scripts. Credentials in `.env`. Same result every time.
IMPORTANT: Never do execution inline when a script exists. Check `execution/` first.

## Core Behaviour
1. **Plan before building.** Check `tasks/todo.md` + `STATE.md`. -> `directives/planning-rules.md`
2. **Ask, don't assume.** Ambiguous? Ask. Separate research and implementation sessions.
3. **Check before spending.** Confirm with the user before running paid API calls.
4. **Verify before delivering.** Run it, test it, confirm it matches spec. -> `directives/delivery-rules.md`
5. **Explain simply.** No jargon without context. Trade-offs in terms the user can evaluate.
6. **One task, one session.** Feature branches, commit per step. -> `directives/building-rules.md`
7. **Shared-file awareness.** In parallel: check contention on STATE.md, learnings.md, todo.md, CLAUDE.md.

## Directory Structure
```
directives/    # SOPs -- read before starting any task
execution/     # Deterministic Python scripts
tasks/         # todo.md + plans
.claude/       # Hooks, settings, plans, commands, agents
.githooks/     # Git hooks (activate: git config core.hooksPath .githooks)
docs/          # Visual documents -- version-controlled
.tmp/          # Temporary files (disposable)
STATE.md  learnings.md  .env
```

## Context Rules
After context compaction, treat ALL directives as unloaded. Re-read triggers for your current task. In wave/DAG mode: also re-read step assignment and ownership list.
First session on a brand new project: load `directives/planning-rules.md` + `directives/building-rules.md`.
**1% rule:** If there is even a 1% chance a trigger applies, load it. See `directives/rationalisation-tables.md` ## 6.

## Triggers
- Planning/scoping -> `directives/planning-rules.md`
- Building/coding -> `directives/building-rules.md`
- Delivering (retro, PR, sign-off, wrap) -> `directives/delivery-rules.md`
- Parallel work / context management -> `directives/context-management.md`
- Self-annealing / learnings curation -> `directives/self-annealing.md`
- Platform evolution -> `directives/framework-evolution.md`
- Adversarial review / `/review` -> `directives/adversarial-review/`
- Serial dispatch / subagent work -> `directives/serial-dispatch-protocol.md`, `directives/subagent-protocol.md`
- About to skip a guardrail -> `directives/rationalisation-tables.md`
- Something went seriously wrong -> `directives/break-glass.md`
- Importing external data (API, CSV, download) -> `learnings.md` for known API behaviours
- Dataset or legal position change -> `directives/documentation-governance.md`
- Auditing claims -> `directives/claim-auditing.md`, run `/audit`
- DOE kit sync -> `directives/starter-kit-sync.md`
- Pulling DOE kit updates -> `directives/starter-kit-pull.md`
- Parallel sessions / wave setup -> `.claude/plans/multi-agent-coordination.md`
- Security-sensitive code (input, auth, rendering, headers) -> `directives/security-rules.md`
- Writing code -> `directives/best-practices/` for the language
- Refactoring / architecture -> `directives/architectural-invariants.md`
- Testing setup -> `directives/testing-strategy.md`
- Personal data features -> `directives/data-compliance.md` (DPIA is hard blocker)
- New functions / debugging -> `directives/best-practices/tdd-and-debugging.md`
- DOE feature request -> `/request-doe-feature`

- Updating CHANGELOG.md -> regenerate whats-new.html: `python3 execution/generate_whats_new.py`

<!-- Add project-specific triggers here as the system grows -->
