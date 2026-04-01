As your very first action, start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start`

Read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md.

**PR check:** Run `gh pr list --state open --json number,title,headRefName 2>/dev/null` to check for open PRs. If any exist, show them in the kick-off card as an `OPEN PRS` row (count + titles). If on `main` and about to create a new branch, add a prompt after the card: "N open PR(s) -- merge first or branch independently? Reply 'merge #N' to merge, or 'go' to continue." Wait for the user's response before branching. If on a feature branch that matches an open PR, note it as the active PR.

**Branch check:** Run `git branch --show-current` to check the current branch. If on `main`, create a feature branch for the active feature: `git checkout -b feature/<feature-slug>` (derive the slug from the feature heading in todo.md ## Current — lowercase, hyphens, no version tag, e.g. "PR Workflow Migration" becomes "feature/pr-workflow-migration"). Push the branch: `git push -u origin feature/<feature-slug>`. If already on a feature branch, continue on it. Show the branch name in the PICKING UP line of the kick-off card.

**Curation check:** Read `.claude/stats.json` → `lifetime.totalSessions` and STATE.md → `## Curation` → `next-curation`. If `totalSessions >= next-curation` value (e.g. `session-200` means 200), announce "Learnings curation due (session #N)" in the kick-off card and trigger the curation protocol (see CLAUDE.md Self-Annealing section) before starting any feature work.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version. Compare against STATE.md's "DOE Starter Kit" version. If versions match → `synced`. If kit tag is newer → `* pull`. No outbound push detection — `/wrap` handles session-specific reminders for modified kit-syncable files. If the directory doesn't exist, skip the DOE Kit line entirely.

**Dependency analysis:** Parse `Depends:` and `Owns:` metadata from steps in todo.md ## Current. If `execution/dispatch_dag.py` exists, run `python3 execution/dispatch_dag.py --graph 2>&1` to see the wave structure. Show the next wave in the card. If the next wave has 2+ steps (parallel opportunity), add a line after PICKING UP: `PARALLEL   Wave has N steps -- run sequential or parallel? (parallel uses dispatch_dag.py)`. Wait for the user's response. If "parallel", run `python3 execution/dispatch_dag.py --dispatch`. If "sequential" or no response after showing the card, proceed with the first step as usual.

**Session blocking (session block):** For large features (5+ remaining steps), suggest which steps to tackle this session based on context budget. A session can typically handle 3-4 steps before context degrades. Show: `SESSION BLOCK   Suggest Steps N-M this session (N steps remaining, ~K context budget)`. This is advisory -- the user can override.

Show a bordered kick-off card, then immediately pick up the next incomplete step. One step at a time -- commit, push, then stop and show what you did.

```
┌──────────────────────────────────────────────────┐
│  CRACK ON -- HH:MM - DD/MM/YY          [project]  │
├──────────────────────────────────────────────────┤
│  FEATURE    [active feature] [APP/INFRA] vX.Y.x   │
│  PROGRESS   ██████░░░░ N/M steps                  │
│  BRANCH     feature/xxx (or main)                  │
│  DOE KIT    vX.Y.Z [synced / * pull]                │
│  OPEN PRS   N open (list titles briefly)           │
│                                                   │
│  PICKING UP Step N -- [step description]          │
│  [1-2 line plain English summary of what you      │
│   are about to do for this step]                  │
│                                                   │
├──────────────────────────────────────────────────┤
│  Model: [model] -- Thinking: [level]             │
└──────────────────────────────────────────────────┘
```

Card rules:
- HEADER ROW: "CRACK ON -- HH:MM - DD/MM/YY" left-aligned, project name right-aligned. Project name is the current directory name + version from STATE.md "Current app version" (e.g. "myproject v1.2.3"). If no version in STATE.md, just show the directory name. Build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`.
- MODEL ROW: Final row of the card, separated by `├──┤`. Shows `Model: [name] -- Thinking: [level]`. IMPORTANT: This line is always shorter than other content lines. You MUST pad it with trailing spaces so the right `│` is at the exact same character position as every other `│` in the card. Count the inner width of the longest line, then pad the model row to match. No emojis (they break alignment). You know your model ID from your system prompt (look for "The exact model ID is..."). Display names: `claude-opus-4-6` → "Opus 4.6", `claude-sonnet-4-6` → "Sonnet 4.6", `claude-haiku-4-5` → "Haiku 4.5". For thinking level, report your reasoning effort: ≤33 → "low", 34-66 → "medium", ≥67 → "high". If uncertain, show "default". This helps the user decide if they need to switch models before starting work.
- FEATURE: from STATE.md "Active feature" line. If no active feature, show "No active feature".
- PROGRESS: count [x] and [ ] steps for the current feature in todo.md ## Current. Bar uses `█` for done, `░` for remaining, scaled to 10 characters. If no current feature, omit this line.
- BRANCH: Run `git branch --show-current`. Show the current branch name (e.g. `feature/pr-workflow-migration` or `main`).
- DOE KIT: `vX.Y.Z synced` if kit version matches STATE.md version. `vX.Y.Z * pull` if the kit has a newer version. Omit entirely if `~/doe-starter-kit` doesn't exist.
- OPEN PRS: Run `gh pr list --state open --json number,title --jq '.[] | "#\(.number) \(.title)"' 2>/dev/null`. If none, show "None". If 1-3, show count and titles. If 4+, show count only. Omit entirely if none. **Conflict detection:** If 2+ PRs are open, check for file overlaps: run `gh pr view N --json files --jq '.files[].path'` for each PR. If any files appear in multiple PRs, add a warning line after the PR list: `  !! Conflict risk: [overlapping files] -- merge [ready PR] first, then rebase the other`. If no overlaps, no warning needed. **Branch staleness:** If on a feature branch, run `git rev-list --count HEAD..origin/main`. If > 0, add: `  !! Branch is N commits behind main -- rebase before merging`.
- PICKING UP: the next incomplete step (first `[ ]` line) from todo.md ## Current. Show step number and short description. If all steps complete, show "All steps complete -- ready for retro". If no current feature, omit this line.
- SUMMARY: Immediately after PICKING UP, add 1-2 lines of plain English explaining what you are about to do for this step. Read the step's plan file if one is referenced, or use the step description and todo.md context. Keep it concrete and jargon-free -- e.g. "Creating the reverse sync command so kit updates can flow into projects safely." Not a restatement of the step name -- explain the actual work.
- BORDER: Fixed width -- always 60 `─` characters between `│` borders (62 total per line). All content lines: `│` + 2 spaces + content + trailing spaces + `│` = 62 chars. If content would exceed 56 characters, truncate with `...`. Never dynamically size -- the box is always the same width. **Generate boxes programmatically** -- define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width. ALL rows including headers MUST use this helper -- never construct `f"│{...}│"` manually. Never hand-pad bordered output. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no `·`, `✓`, `⚠️`, `—`, `…`) -- use `--` for separators, commas for lists. Exception: progress bar uses `█` (done) and `░` (remaining) -- these render at fixed width in terminals.

**Contract pre-flight:** Before starting work on the step, read its contract block in todo.md. Validate all `Verify:` patterns are executable (match `run:`, `file: ... exists`, `file: ... contains`, or `html: ... has`). If the contract is missing, write one based on the step description and present it for approval before proceeding. If patterns are invalid, fix them and note the fix. Show contract status in the card as a line after PICKING UP: `CONTRACT   Valid (N auto, M manual)` or `CONTRACT   Missing -- will write before starting`.

**Post-completion verification:** After finishing the step's work but BEFORE marking it `[x]` in todo.md, run all `[auto]` `Verify:` patterns (via `/agent-verify` if available, or execute them manually). Present `[manual]` criteria to the user for confirmation. Mark each criterion `[x]` in the contract block as it passes. If an `[auto]` criterion fails, attempt up to 3 fixes. Only mark the step `[x]` after all criteria pass.

**Chrome prompt (APP features only):** If the feature is tagged `[APP]`, show after the card: "This is an [APP] feature -- enable Chrome for visual verification? Run `/chrome` to enable, or skip to use manual checks only." Do not auto-enable Chrome (it increases context usage). If the feature is `[INFRA]`, skip this prompt.

After showing the card (and passing contract pre-flight), immediately start working on the step shown in PICKING UP. No sign-off needed -- just go.
