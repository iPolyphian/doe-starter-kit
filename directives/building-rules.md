# Directive: Building Rules

## Goal
Enforce code quality, branch discipline, and collaboration patterns during implementation.

## When to Use
Loaded when building, coding, or implementing features. Also loaded on first session for a brand new project.

## Branch & Commit Discipline

Work on feature branches, commit per step. `/crack-on` creates `feature/<name>` from main.
- Commit after every completed step. Push immediately. Never batch multiple steps.
- Do not commit directly to main. No "Co-authored-by" trailers.
- At retro: `gh pr create` with PR template auto-filled from contracts. CI must pass before merge.

## Subagent Protocol

Delegate to subagents to preserve context. Spawn when: 3+ files, doc research, 50+ lines, or verbose output. Pass only needed files. Stay in main thread for direct edits and back-and-forth.

- Model selection: Opus for judgment/architecture, Sonnet for implementation, Haiku for lookups
- **Status protocol:** Must report DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
  - See `directives/subagent-protocol.md` for format. No ad-hoc "I'm done" -- require the report

## Parallelise by Default

2+ independent tasks -> parallel subagents. Commit one at a time per branch discipline. For interdependent steps, use serial dispatch -- see `directives/serial-dispatch-protocol.md`.

## Code Hygiene

- **Check before creating.** Check if a similar file exists. Never create `filename-new`, `_v2`, `-copy` variants. Edit the existing file.
- **Surgical edits only.** When fixing a bug, edit only the affected code. Never rewrite an entire file to fix a small problem. If a rewrite is genuinely needed, say so and get approval first.
- **Pre-refactor cleanup.** Before any structural refactor on a file >300 LOC, first commit a dead-code removal pass (unused imports, dead props, orphaned exports). Separate commit -- cleanup and logic changes must be distinct in the diff.
- **Reuse before writing.** Check `execution/` and project files for existing logic before writing new. Flag duplication.
- **One task, one session.** If the conversation drifts, recommend `/clear`. Do not let unrelated context accumulate.
- **Refactor is not rewrite.** Change structure only. Do not change behaviour. If behaviour must change, say so explicitly.
- **No orphan files.** If you replace a file, delete the old one.
- **Plans go in `.claude/plans/`, not global.** Never write to `~/.claude/plans/`.
- **Visual docs go in `docs/`, not global.** Never write to `~/.agent/diagrams/`.
- **Files in designated directories.** Follow the directory structure in CLAUDE.md. Do not create files in the project root or invent new directories without approval.
- **Rename safety protocol.** When renaming or changing a function/type/variable signature, run separate searches for: direct calls, type references, string literals containing the name, dynamic imports, re-exports, barrel files, test mocks. Never assume a single grep caught everything.

## Search & Tool-Use Discipline

- **Search truncation awareness.** When grep/search results look suspiciously small, re-run with narrower scope (single directory, stricter glob). State explicitly when truncation is suspected rather than working from incomplete results.

## File Ownership in Parallel Work

When working alongside other agents (wave mode or DAG executor), respect the owns list:
- Only edit files listed in your step's `Owns:` metadata
- CLAUDE.md, STATE.md, todo.md, learnings.md are shared files -- off-limits to all parallel agents
- If you need a file you don't own, report `NEEDS_CONTEXT` (subagent status protocol)
- Pre-commit hooks enforce ownership mechanically in DAG mode

### DAG Push Mode
In DAG parallel mode (formal parallel), individual steps do NOT push to the feature branch. Instead:
1. Each agent works in its own worktree on a sub-branch
2. After all steps in a wave complete and pass contracts
3. The executor performs the wave merge into the feature branch
4. Integration contracts run on the merged result
5. Feature branch pushes to remote after integration passes

## Explain Technical Decisions
When making technical choices during building, explain simply. No jargon without context. If recommending a library, framework, or pattern, explain why in terms the user can evaluate.

## Build-Phase Triggers
These triggers apply during building (absorbed from the original CLAUDE.md trigger table):
- Editing `src/` or scripts that write to `src/data/` -> run `python3 execution/build.py` to rebuild HTML
- Creating a new execution script -> check `execution/` for reusable patterns, review `learnings.md` ## Execution Script Gotchas
- Completing a data-layer step -> run `/code-trace`. Announce: "Data-layer step -- running code trace."
- Completing a UI step -> run `npx playwright test` on affected pages. Announce: "Running browser tests."
- Completing an integration step -> run `/code-trace --integration`
- Checking implementation vs plan -> suggest `/plan-review`

## Structured JSON Logging
For any backend or API code, use structured JSON logging rather than unstructured print/console.log. This enables log aggregation, search, and alerting in production. Format: `{"level": "info", "message": "...", "context": {...}}`.

## Data Integrity Testing
When building features that process or display data, add data integrity checks:
- Validate data codes (e.g. PCON24 codes are real constituency codes)
- Check numeric sums (e.g. vote shares sum to ~100%)
- Verify no NaN/null in required numeric fields
- Check no orphan codes (references to entities that don't exist)

Template: `~/doe-starter-kit/tests/data/test_data_integrity_template.py`
