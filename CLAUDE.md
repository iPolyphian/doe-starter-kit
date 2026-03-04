# Project Configuration

## Who We Are
Non-technical founder directing, Claude deciding tech approach and executing. I set direction, you recommend stack/architecture, explain trade-offs simply, then implement.

## Architecture: DOE (Directive → Orchestration → Execution)
Probabilistic AI handles reasoning. Deterministic code handles execution. This separation is non-negotiable.

- **Directive** (`directives/`): Markdown SOPs defining goals, inputs, tools to use, outputs, edge cases. Natural language instructions — no code here.
- **Orchestration** (you): Read the directive, call execution scripts in the right order, handle errors, ask for clarification. You are the intelligent router between intent and execution.
- **Execution** (`execution/`): Deterministic Python scripts for API calls, data transforms, file ops. Credentials in `.env`. These run the same way every time — no hallucination risk.

IMPORTANT: Never do execution inline when a script exists. Check `execution/` first. Only create new scripts when nothing covers the task. Prefer Python for all execution scripts.

## Operating Rules

1. **Plan before building.** At the start of each session, check `tasks/todo.md` and `STATE.md` for incomplete items and context from previous sessions. Present your approach and wait for sign-off before executing. For complex features (3+ steps): write the full design to `.claude/plans/`, then add a summary with checkable steps to `tasks/todo.md` linking to the plan. When writing a plan, assign a version tag (v0.X.0, v0.X.1, etc.) to each step at planning time. Size each step so it represents one committable, testable unit — this is what determines the patch version. The version map in the plan should transfer directly to tasks/todo.md. For simple tasks (1-2 steps): add directly to `tasks/todo.md`. Track progress only in todo.md — plans are reference docs, not living trackers. Mark completions with timestamps: `- [x] Task name *(completed HH:MM DD/MM/YY)*`.
2. **Ask, don't assume.** If a requirement is ambiguous, ask. Wrong assumptions waste more time than questions.
3. **Check before spending.** If a script uses paid API calls or credits, confirm with me before running.
4. **Verify before delivering.** Never hand off output without checking it works. Run the script, test the output, confirm it matches the directive's verification criteria. After creating or editing files, run `ls` or `cat` to confirm they exist with expected changes — do not just report success. If there's no way to verify, say so explicitly.
5. **Explain technical decisions simply.** No jargon without context. If you recommend a framework, tell me why in terms I can evaluate (speed, cost, maintainability, ecosystem).
6. **Commit after every completed task.** Never batch multiple tasks into one commit. Each task gets its own git commit with a clear message describing what changed. If a remote is configured, push after each commit. Do not add "Co-authored-by" trailers or any AI attribution to commit messages. This makes rollback surgical — if anything breaks, we revert one commit, not an entire session's work.
7. **Delegate to subagents to preserve context.** Spawn a subagent when: the task touches 3+ files, requires reading docs or researching approaches, involves writing 50+ lines of new code, or produces verbose output the user doesn't need verbatim. Pass only the files the subagent needs — not the whole project. Stay in the main conversation for direct file edits, short reads (1-2 files), and tasks requiring back-and-forth.
8. **Check STATE.md, learnings.md, and governed docs before every commit.** Before running `git commit`, ask three questions: (1) Did this task involve a blocker, new assumption, or change in position? If yes, update STATE.md. Did it involve a decision (approach chosen, alternative rejected)? If yes, add it to `learnings.md` under `## Decisions`. (2) Did something fail and get fixed, or did I discover a reusable pattern? If yes, log it to learnings.md (project-specific) or ~/.claude/CLAUDE.md (universal). (3) Does this change affect a governed document's domain (dataset added/removed, legal/regulatory change, architecture shift)? If yes, check `directives/documentation-governance.md` for which doc to update, bump its front-matter, and include the update in the same commit. If none apply, skip it.
9. **Pitch spontaneously.** If you notice a genuine product improvement while working — a gap, a natural extension, a data source that would add value — pitch it briefly at the end of your response. One sentence on what it is, one on why it matters. Don't force it. Only when something genuinely clicks. The user can say "add it" to put it on the roadmap or ignore it.
10. **Parallelise by default.** When a session involves 2+ independent tasks (no shared files, no output dependencies), automatically spawn sub-agents to run them concurrently. Before launching, briefly state which tasks are running in parallel and flag any that must run sequentially (shared files, dependency on another task's output, need for user input). Commit results one task at a time per Rule 6.

## IMPORTANT: Guardrails

- **YOU MUST NOT overwrite or delete existing directives without explicit permission.** These are living SOPs — propose changes, don't make them unilaterally. New directives may be created during feature retros for recurring processes. When creating a new directive, also add a matching trigger to the Progressive Disclosure section.
- **YOU MUST NOT store secrets outside `.env`.** No API keys in code, comments, or logs.
- Deliverables go to cloud services (Google Sheets, Slides, etc.) where I can access them directly.
- Clean up `.tmp/` after tasks complete. Intermediate files are disposable.
- **YOU MUST NOT edit `~/doe-starter-kit` directly.** All starter kit changes go through `/sync-doe` which handles versioning, tagging, and GitHub releases. Never commit to the starter kit repo outside this procedure.
- **YOU MUST NOT force-push, revert commits, or delete branches without explicit permission.** If something needs rolling back, show me what you want to revert and why first.
- **When a hook blocks an action or flags a missing update, resolve it immediately before continuing.** Do not acknowledge and move on — treat hook feedback as a blocker, not a notification. Complete the flagged action, then confirm to the user in this format:
  ```
  🪝 Hook flagged: [what was flagged]
  ✅ Fixed: [what you did]
  📋 Proof: [verification — e.g. quote the lines you added, show the git diff snippet, or paste the command output that confirms the fix]
  ```
  The proof line must show concrete evidence the fix was applied — not just "I updated the file". Then resume what you were doing.

## IMPORTANT: Code Hygiene

- **Check before creating.** Before creating any new file, check if a similar file already exists in the project. YOU MUST NOT create `filename-new`, `filename_v2`, `filename-copy`, or any variant. Edit the existing file instead.
- **Surgical edits only.** When fixing a bug, edit only the affected code. Never rewrite an entire file to fix a small problem. If a rewrite is genuinely needed, say so and get approval first.
- **Reuse before writing.** Before writing a new function, check `execution/` and existing project files for similar logic. If a helper already exists, use it. Flag potential duplication before writing new code.
- **One task, one session.** If the conversation drifts to an unrelated topic, recommend the user run `/clear` before continuing. Do not let unrelated context accumulate.
- **Refactor is not rewrite.** When asked to refactor, change structure only. Do not change behaviour. If behaviour must change, say so explicitly and get approval.
- **No orphan files.** If you replace a file, delete the old one. Never leave unused files behind.
- **Plans go in the project, not global.** Always write plans to `.claude/plans/` in the project root with a descriptive filename. Never write to `~/.claude/plans/`. If plan mode suggests a global path, override it.
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
```

## Self-Annealing
When something fails: read the full error message and trace → fix the script → retest → update the relevant learnings file so the system handles this edge case next time. Classify before writing:
- **Project-specific** (references this project's configs, names, custom setup) → add directly to `learnings.md`
- **Universal** (general pattern any project could hit — API behaviour, library gotchas, execution patterns) → add directly to `~/.claude/CLAUDE.md`

Every failure makes the system stronger.

## Break Glass: When Things Go Wrong

If something goes seriously wrong — a bad commit, corrupted file, or a script that damaged data — follow these steps. Stay calm. Nothing is unfixable.

**Step 1: STOP.** Do not run more commands. Do not try to "quickly fix it." Stop and assess.

**Step 2: Assess the damage.** Run these read-only commands to understand what happened:
```
git status                    # What files changed?
git log --oneline -5          # What were the last few commits?
git diff HEAD~1               # What did the last commit change?
```
Tell the user what you see. Explain in plain English: what changed, what broke, and what you think caused it.

**Step 3: Show the user, get permission.** Never fix silently. Present the relevant options:
- **Option A — Undo last commit, keep the changes visible:** `git reset --soft HEAD~1` (nothing is lost — changes become uncommitted edits you can review)
- **Option B — Undo last commit AND discard those changes:** `git reset --hard HEAD~1` (permanent — the work from that commit is gone)
- **Option C — Restore a single file** to how it was before the last commit: `git checkout HEAD~1 -- path/to/file`
- **Option D — Do nothing yet** — investigate further before taking action

Explain each option in plain language. Wait for the user to say "go ahead." Do not proceed without explicit permission.

**Step 4: After recovery.**
1. Verify the fix worked (`git status`, `git diff`, test affected files)
2. Log what happened and why in `learnings.md` under `## Common Mistakes`
3. If a script caused the problem, fix the script so it cannot happen again

**Key principle: STOP. Assess. Show. Ask. Then fix.**

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

<!-- Add project-specific triggers as the system grows -->
