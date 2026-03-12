# Project Configuration

## Who We Are
The human defines intent, constraints, and verification criteria. Claude recommends technical approach, explains trade-offs simply, then implements. The human steers — Claude builds.

## Architecture: DOE (Directive → Orchestration → Execution)
Probabilistic AI handles reasoning. Deterministic code handles execution. This separation is non-negotiable.

- **Directive** (`directives/`): Markdown SOPs defining goals, inputs, tools to use, outputs, edge cases. Natural language instructions — no code here.
- **Orchestration** (you): Read the directive, call execution scripts in the right order, handle errors, ask for clarification. You are the intelligent router between intent and execution.
- **Execution** (`execution/`): Deterministic Python scripts for API calls, data transforms, file ops. Credentials in `.env`. These run the same way every time — no hallucination risk.

IMPORTANT: Never do execution inline when a script exists. Check `execution/` first. Only create new scripts when nothing covers the task. Prefer Python for all execution scripts.

## Operating Rules

1. **Plan before building.** Check `tasks/todo.md` and `STATE.md` at session start. Complex features (3+ steps): write design to `.claude/plans/`, add steps to `tasks/todo.md`. Simple tasks: add directly to `tasks/todo.md`. Track progress only in todo.md — plans are reference docs. Each step in a plan must include a recommended model + thinking level (e.g. `Opus + high` for design judgment, `Sonnet + medium` for spec-driven implementation, `Sonnet + low` for mechanical work). Every task added to todo.md must include a Contract block with testable criteria tagged `[auto]` or `[manual]`. `[auto]` criteria must use an executable Verify: pattern (`run:`, `file: ... exists`, `file: ... contains`, `html: ... has`). Tasks without testable contracts cannot be started. **Solo verification discipline:** Before starting any todo.md task, validate its contract: confirm `[auto]`/`[manual]` criteria exist and `Verify:` patterns use valid executable forms (`run:`, `file: ... exists`, `file: ... contains`, `html: ... has`). If patterns are invalid, fix them. If no contract exists, write one and get user approval before starting. **`[auto]` criteria:** Run all `Verify:` patterns after each step (via `/agent-verify` when available, manually when not). Mark each `[auto]` criterion `[x]` as it passes. If any fail, attempt up to 3 fixes before escalating. Log failures to learnings.md. Mark the step `[x]` when all `[auto]` criteria pass — do not wait for `[manual]` sign-off to continue building. **`[manual]` criteria:** These require human testing (visual/UX checks). Do NOT stop after every step to wait for manual approval — this kills autonomy. Instead: (1) Prefer converting `[manual]` criteria to `[auto]` where possible (DOM checks, function call verification, data flow assertions via `run:` scripts). Only keep `[manual]` for things that genuinely need human eyes (visual layout, interaction feel, print rendering). (2) Continue building autonomously through all steps. (3) At **feature completion**, move the feature to `## Awaiting Sign-off` in todo.md and present a single consolidated manual test checklist: what to test, how to test it, and which step/contract each test relates to. The user tests, reports pass/fail, and any failures get fixed. The feature moves to `## Done` only when all `[manual]` criteria are `[x]` -- no exceptions. Features in Awaiting Sign-off are code-complete and buildable; they just haven't been visually verified yet. (4) For **large features (5+ steps)**, add a single mid-feature visual checkpoint after the core UI step — present manual checks accumulated so far before continuing. This catches visual bugs before dependent steps build on them. In wave mode, criteria are verified at `--complete` and todo.md is updated at `--merge`. Wave agents do not edit shared files on master (todo.md, CLAUDE.md, learnings.md, STATE.md). Solo mode keeps the "mark as you go" rule above. **Ad-hoc work verification:** For tasks not tracked in todo.md (bug fixes, quick changes, one-off requests): before starting work, state 1-3 acceptance criteria with executable `Verify:` patterns in the conversation. These are ephemeral — they don't go in todo.md. After completing the work, run the `Verify:` patterns (via `/agent-verify` if available, manually if not) and confirm they pass before committing. No exceptions for changes that affect behaviour — even a typo fix gets `Verify: file: README.md contains correct-spelling`. For purely mechanical changes (version bumps, deletions, comment edits), state what changed and why instead of a `Verify:` pattern.
2. **Ask, don't assume.** If a requirement is ambiguous, ask. Wrong assumptions waste more time than questions. For tasks requiring significant research (3+ approaches to evaluate, extensive doc reading), separate research and implementation into different sessions — research pollutes implementation context and vice versa.
3. **Check before spending.** If a script uses paid API calls or credits, confirm with me before running.
4. **Verify before delivering.** Never hand off output without checking it works. Run the script, test the output, confirm it matches the directive's verification criteria. After creating or editing files, run `ls` or `cat` to confirm they exist with expected changes — do not just report success. If there's no way to verify, say so explicitly. Use neutral verification prompts — "Does this output match the spec?" not "This looks great, right?" Sycophantic self-evaluation hides bugs.
5. **Explain technical decisions simply.** No jargon without context. If you recommend a framework, tell me why in terms I can evaluate (speed, cost, maintainability, ecosystem).
6. **Commit after every completed task.** Never batch multiple tasks into one commit. Each task gets its own git commit with a clear message describing what changed. If a remote is configured, push after each commit. Do not add "Co-authored-by" trailers or any AI attribution to commit messages. This makes rollback surgical — if anything breaks, we revert one commit, not an entire session's work.
7. **Delegate to subagents to preserve context.** Spawn a subagent when: the task touches 3+ files, requires reading docs or researching approaches, involves writing 50+ lines of new code, or produces verbose output the user doesn't need verbatim. Pass only the files the subagent needs — not the whole project (a 15k-token task description compresses to a 500-token summary = 30x context saving). Stay in the main conversation for direct file edits, short reads (1-2 files), and tasks requiring back-and-forth. Choose subagent model deliberately: Opus for tasks requiring judgment, cross-file reasoning, or architectural decisions; Sonnet for straightforward implementation; Haiku for quick lookups, searches, and mechanical tasks.
8. **Check STATE.md, learnings.md, and governed docs before every commit.** Update STATE.md if position changed, log learnings if something failed/was discovered, update governed docs if their domain was affected (check `directives/documentation-governance.md`). Skip if none apply.
9. **Pitch spontaneously.** If you notice a genuine product improvement while working — a gap, a natural extension, a data source that would add value — pitch it briefly at the end of your response. One sentence on what it is, one on why it matters. Don't force it. Only when something genuinely clicks. The user can say "add it" to put it on the roadmap (Ideas section) or "this is important" to flag it (Must Plan section).
10. **Parallelise by default.** When a session involves 2+ independent tasks (no shared files, no output dependencies), automatically spawn sub-agents to run them concurrently. Before launching, briefly state which tasks are running in parallel and flag any that must run sequentially (shared files, dependency on another task's output, need for user input). Commit results one task at a time per Rule 6.

## IMPORTANT: Guardrails

- **YOU MUST NOT overwrite or delete existing directives without explicit permission.** These are living SOPs — propose changes, don't make them unilaterally. New directives may be created during feature retros for recurring processes. When creating a new directive, also add a matching trigger to the Progressive Disclosure section.
- **YOU MUST NOT store secrets outside `.env`.** No API keys in code, comments, or logs.
- Deliverables go to cloud services (Google Sheets, Slides, etc.) where I can access them directly.
- Clean up `.tmp/` after tasks complete. Intermediate files are disposable.
- **YOU MUST NOT edit `~/doe-starter-kit` directly.** All starter kit changes go through `/sync-doe` which handles versioning, tagging, and GitHub releases. Never commit to the starter kit repo outside this procedure.
- **YOU MUST NOT force-push, revert commits, or delete branches without explicit permission.** If something needs rolling back, show me what you want to revert and why first.
- **When a hook blocks an action, fix it immediately before continuing.** Show the user what was flagged, what you fixed, and concrete proof (git diff, command output, quoted lines). Do not just say "I updated the file."
- **During an active wave, wave agents MUST NOT edit shared files on master.** This includes `todo.md`, `CLAUDE.md`, `learnings.md`, `STATE.md`, and any file not in the task's `owns` list. Fixes to contracts or shared docs happen from the coordinator terminal after `--merge`. Editing shared files from a worktree causes stash conflicts during merge.

## IMPORTANT: Code Hygiene

- **Check before creating.** Before creating any new file, check if a similar file already exists in the project. YOU MUST NOT create `filename-new`, `filename_v2`, `filename-copy`, or any variant. Edit the existing file instead.
- **Surgical edits only.** When fixing a bug, edit only the affected code. Never rewrite an entire file to fix a small problem. If a rewrite is genuinely needed, say so and get approval first.
- **Reuse before writing.** Before writing a new function, check `execution/` and existing project files for similar logic. If a helper already exists, use it. Flag potential duplication before writing new code.
- **One task, one session.** If the conversation drifts to an unrelated topic, recommend the user run `/clear` before continuing. Do not let unrelated context accumulate.
- **Refactor is not rewrite.** When asked to refactor, change structure only. Do not change behaviour. If behaviour must change, say so explicitly and get approval.
- **No orphan files.** If you replace a file, delete the old one. Never leave unused files behind.
- **Plans go in the project, not global.** Always write plans to `.claude/plans/` in the project root with a descriptive filename. Never write to `~/.claude/plans/`. If plan mode suggests a global path, override it.
- **Visual docs go in `docs/`, not global.** Generated HTML documents (brainstorms, diagrams, guides, visual explainers) go to `docs/` in the project root. Never write to `~/.agent/diagrams/` or other global paths — those are ephemeral and not version-controlled.
- **YOU MUST place files in designated directories.** Follow the directory structure below exactly. Do not create files in the project root or invent new directories without approval.

## Directory Structure
```
directives/     # SOPs — read these before starting any task (use _TEMPLATE.md for new ones)
execution/      # Deterministic Python scripts
tasks/          # Plans and todo tracking for complex builds
learnings.md    # Project-specific institutional memory — check before building (governed doc)
STATE.md        # Session memory — blockers, current position (check at session start; decisions go in learnings.md)
.tmp/           # Temporary/intermediate files (disposable)
.env            # API keys and credentials (NEVER commit)
.claude/        # Hooks, settings, plans, and commands (deterministic guardrails + feature designs)
.githooks/      # Git hooks — strips AI co-author trailers + pre-commit audit (activate: git config core.hooksPath .githooks)
docs/           # Generated visual documents (brainstorms, diagrams, guides) — version-controlled
```

## Self-Annealing
When something fails: read the full error → diagnose WHY (not just what) → fix → retest → log. Classify before writing:
- **Project-specific** (references this project's configs, names, custom setup) → add directly to `learnings.md`
- **Universal** (general pattern any project could hit — API behaviour, library gotchas, execution patterns) → add directly to `~/.claude/CLAUDE.md`

**Routine failures:** one-line learning with source tag. E.g. `- macOS sed -i requires '' backup arg. [retro: feature-name]`
**Significant failures** (cost >30 min, broke production, or recurred): use structured format in learnings.md — What happened, Root cause, Fix applied, Prevention added. If the failure pattern recurs, create a directive or hook to prevent it.
**Test failures** (auto-test fails, regression during merge, contract passed but result was wrong): use the structured format. Bad contracts get root cause "contract criteria didn't capture actual requirement" — update contract writing guidance in learnings.md to prevent recurrence.

Every failure makes the system stronger.

## Progressive Disclosure
For task-specific instructions, check the relevant directive in `directives/` before starting. Check `learnings.md` for project-specific patterns and `STATE.md` for recent decisions before building anything new. Universal learnings (`~/.claude/CLAUDE.md`) are auto-loaded. This file covers universal rules only — detailed SOPs live in their own docs.

### Triggers
When a task matches a trigger below, load the linked doc before starting:

- Importing external data (API, CSV, download) → check `learnings.md` for known API behaviours, then review the matching `execution/import_*.py` script if one exists
- Creating a new execution script → check `execution/` for existing scripts to reuse patterns from, and review `learnings.md` ## Execution Script Gotchas
- Version bump or release → check `tasks/todo.md` ## Done for the version bump step pattern
- Adding/removing a dataset, changing legal/regulatory position, or completing a feature → read `directives/documentation-governance.md` for the governed docs checklist and front-matter format
- Auditing claims, preparing for a demo, or completing a phase → read `directives/claim-auditing.md`, then run `python3 execution/audit_claims.py` (or use `/audit`)
- Syncing DOE improvements to the starter kit repo, or completing an [INFRA] feature → read `directives/starter-kit-sync.md`
- Pulling DOE kit updates into the project → read `directives/starter-kit-pull.md`
- Before writing code, identify the primary language(s) → read the relevant best practices directive(s) in `directives/best-practices/` if they exist
- Refactoring, restructuring, or proposing architectural changes → read `directives/architectural-invariants.md` first
- Reviewing changes before commit → suggest `/diff-review` for a visual before/after comparison
- Returning to a project after absence or context loss → suggest `/project-recap` for a visual state rebuild
- Checking whether implementation matches the plan → suggest `/plan-review` for visual alignment check
- Setting up testing for a new project or configuring test tools → read `directives/testing-strategy.md`
- Running parallel sessions, setting up a wave, or using `/agent-status` → read `.claude/plans/multi-agent-coordination.md` for the full coordination protocol
- Scoping a new feature or exploring a product idea → run `/scope` for a conversational scoping session that produces a brief
- Something went seriously wrong (bad commit, corrupted file, data damage) → read `directives/break-glass.md` and follow it

<!-- Add project-specific triggers as the system grows -->
