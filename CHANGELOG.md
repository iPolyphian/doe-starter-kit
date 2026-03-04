# Changelog

All notable changes to the DOE Claude Code Starter Kit.

Format: `## [vX.Y.Z] — YYYY-MM-DD` with sections for Added, Changed, Fixed, Removed.
Versioning: patch for small fixes, minor for new features/commands/directives, major for breaking changes to CLAUDE.md rules or directory structure.

---

## [v1.11.7] — 2026-03-04

### Changed
- **`/wrap` layout** — moved NEXT UP section to render after the footer (was between Decisions and Numbers). Renumbered parts 6-9.

---

## [v1.11.6] — 2026-03-04

### Fixed
- **Session timer** — replaced per-PID `.session-start-$$` with single `.tmp/.session-start` file across 6 commands (`/stand-up`, `/crack-on`, `/sitrep`, `/wrap`, `/eod`, `/commands`). `$$` returned a different subshell PID per Bash tool call, making the timer unreliable. Worktrees handle multi-session isolation, so per-PID files were unnecessary.

---

## [v1.11.5] — 2026-03-04

### Changed
- **Box-drawing rules** — clarified in 5 global commands (`/audit`, `/sitrep`, `/stand-up`, `/sync-doe`, `/wrap`): explicitly use Unicode box-drawing characters (`┌─┐`, `├─┤`, `└─┘`, `│`) for borders, ASCII-only for content inside borders

---

## [v1.11.4] — 2026-03-04

### Changed
- **Commands README** — updated from 15 to 22 commands, added Visual category (`/project-recap`, `/diff-review`, `/plan-review`, `/generate-visual-plan`, `/generate-web-diagram`, `/generate-slides`), added `/fact-check` to Quality, reorganised table layout

---

## [v1.11.3] — 2026-03-04

### Changed
- **`/audit` result box** — output now ends with a programmatic bordered result box (matching `/sync-doe` and `/wrap` style) showing PASS/WARN/FAIL counts and key stats

---

## [v1.11.2] — 2026-03-04

### Added
- **`/wrap` agents stat** — new "agents spawned" metric in The Numbers section, counted from Agent tool calls in the session

### Changed
- **`/wrap` session time label** — shortened from "total session time" to "session time"
- **`/wrap` system checks box** — replaced hand-padded example boxes with programmatic generation instruction (collect lines, find max length, `.ljust()`)

### Removed
- **`/wrap` One-Stat Highlight** — removed Part 9 (redundant with The Numbers). Parts renumbered from 11 to 10.

---

## [v1.11.1] — 2026-03-04

### Changed
- **`/wrap` title card** — project name now uses spaced-out uppercase text (e.g. `M O N T Y`) centered in the box, generated from the current directory name. Narrative lines render as plain paragraphs below the code fence (no indentation).
- **`/wrap` output** — removed haiku section. Parts renumbered from 12 to 11. Narrative sections (vibe, journey, commits, decisions, next up) now appear before data tables (numbers, timeline, leaderboard).

---

## [v1.11.0] — 2026-03-04

### Added
- **7 new universal commands:** `diff-review.md` (visual HTML diff review), `fact-check.md` (verify doc accuracy against codebase), `generate-slides.md` (magazine-quality HTML slide decks), `generate-visual-plan.md` (visual HTML implementation plans), `generate-web-diagram.md` (standalone HTML diagrams), `plan-review.md` (visual HTML plan review), `project-recap.md` (visual HTML project recap).

---

## [v1.10.2] — 2026-03-04

### Changed
- **`sync-doe.md` result box templates** — moved status emojis above the box as standalone signal lines (e.g. `✅ SYNCED` before the bordered box). Emojis stay visible for quick-glance scanning without breaking box-drawing alignment.

---

## [v1.10.1] — 2026-03-04

### Fixed
- **`sync-doe.md` result box templates** — removed emojis from inside bordered boxes (they render double-width, breaking alignment). Added programmatic box generation rule and ASCII-only constraint matching other commands.

---

## [v1.10.0] — 2026-03-04

### Changed
- **Per-PID session timers for multi-terminal safety.** Session clock files changed from `.tmp/.session-start` to `.tmp/.session-start-$$` (shell PID). Each terminal gets an independent timer. Stale PID files are pruned on `/crack-on`, `/stand-up`, and `/wrap` via `kill -0` checks. `/eod` scans all PID files to detect multiple active sessions. Updated all 6 command files: `crack-on.md`, `stand-up.md`, `sitrep.md`, `wrap.md`, `eod.md`, `commands.md`.
- **Progress bar border exception** in `stand-up.md` — `█` and `░` characters now explicitly permitted inside bordered boxes (they render at fixed width in terminals).

---

## [v1.9.4] — 2026-03-04

### Added
- **Code Hygiene rule: plans go in the project.** New CLAUDE.md rule requiring plans to be written to the project's `.claude/plans/` directory with descriptive filenames, not to `~/.claude/plans/`. Prevents plan files from landing in the global directory where they're invisible to the project.

---

## [v1.9.3] — 2026-03-04

### Fixed
- **`wrap_stats.py` step counting** — `count_steps_completed_today()` counted all `[x]` steps with today's date, inflating `stepsCompleted` across multiple sessions on the same day. Replaced with `count_steps_completed_since()` which parses the `HH:MM DD/MM/YY` timestamp and only counts steps completed after the session start time.

---

## [v1.9.2] — 2026-03-04

### Fixed
- **`context_monitor.py` file accumulation** — replaced per-PID tracker files (`.context-{pid}.json`) with a single `.context-usage.json` that gets overwritten each tool call. Prevents hundreds of orphan files accumulating in `.tmp/` per session. Same fix applied to warn marker (`.context-warned-{pid}` → `.context-warned`).

---

## [v1.9.1] — 2026-03-04

### Added
- **`copy_plan_to_project.py` hook** — PostToolUse hook that auto-copies plans written to `~/.claude/plans/` into the current project's `.claude/plans/` directory. Fires after `write|edit` tool calls targeting `~/.claude/plans/*.md`.
- **PostToolUse section in `settings.json`** — registers the plan-copy hook

---

## [v1.9.0] — 2026-03-04

### Changed
- **Multi-agent system moved to global install** — no more per-project copies. `multi_agent.py` → `~/.claude/scripts/`, `heartbeat.py` + `context_monitor.py` → `~/.claude/hooks/`, `/hq` → `~/.claude/commands/`. Install once, works across all projects.
- **`setup.sh` extended** — 3 new install sections: hooks to `~/.claude/hooks/`, scripts to `~/.claude/scripts/`, merges PostToolUse into `~/.claude/settings.json`
- **Path refactor** — all multi-agent Python files use `Path.cwd()` instead of `Path(__file__)` for global execution
- **`--project-root` override** — `multi_agent.py` accepts `--project-root DIR` to specify the project directory explicitly
- **Template `.claude/settings.json` now PreToolUse-only** — PostToolUse hooks are merged into the global settings by `setup.sh`

---

## [v1.8.0] — 2026-03-04

### Added
- **Multi-agent coordination system** — `execution/multi_agent.py` for running 2-4 parallel Claude Code sessions. Wave management, task claiming, session registry, heartbeats, merge protocol, cost tracking. All state in `.tmp/waves/`.
- **`/hq` command** — `.claude/commands/hq.md` project-level dashboard. Shows wave status, terminal liveness, task progress, cost estimates, merge order. Modes: no_wave (help), active (live dashboard).
- **Heartbeat hook** — `.claude/hooks/heartbeat.py` PostToolUse hook updating session liveness every 30s during active waves. Stale sessions (>2 min) are detectable and reclaimable.
- **Context monitor hook** — `.claude/hooks/context_monitor.py` PostToolUse hook tracking estimated context usage. Warns at 60%, stops at 80% for graceful handoff. Model-aware budgets during waves (haiku: 30k, sonnet: 80k, opus: 200k).
- **Active wave audit check** — `check_active_wave` in `audit_claims.py` warns when a wave is active and results may be incomplete until merge. Runs in fast/hook mode.
- **PostToolUse hooks in settings.json** — heartbeat and context monitor fire after every tool use

---

## [v1.7.4] — 2026-03-03

### Removed
- **`/wrap`** — removed fortune cookie line from session footer. Adds noise without value.

---

## [v1.7.3] — 2026-03-03

### Changed
- **`/stand-up` (status mode)** — reordered card: PHASE GOAL now appears above PROGRESS for better readability. Added NEXT STEP line showing the first uncompleted step from todo.md, so the immediate task is always visible at a glance.

---

## [v1.7.2] — 2026-03-03

### Fixed
- **`execution/audit_claims.py`** — skip version tag WARN for `[INFRA]` tasks. Infrastructure features don't bump app version, so their todo steps never have version tags. `parse_completed_tasks()` now tracks heading context and `check_task_format()` skips the check for `[INFRA]` sections.

---

## [v1.7.0] — 2026-03-02

### Changed
- **`/wrap`** — lightweight rewrite. Removed scoring/badges/genre system. One dramatic narrative (no genre selection), added session haiku, one-stat highlight, fortune cookie footer. Leaderboard now shows commits/lines instead of scores. Vibe check determined inline instead of by script.
- **`/roast`** — removed score trend and badge pattern analysis bullets (stats.json no longer has these fields)
- **`/stand-up`** — removed "score trends" FOCUS bullet
- **`/eod`** — removed SCORE line from card, simplified session list to title + duration (no scores/badges)
- **`/commands`** — updated `/wrap` and `/roast` descriptions to reflect lightweight wrap

### Removed
- Scoring formula, badge definitions, genre selection, multiplier system, high score tracking from `/wrap`
- `execution/wrap_stats.py` scoring logic (978 → ~150 lines, now metrics + streak only)

---

## [v1.6.0] — 2026-03-02

### Added
- **`/eod`** — new end-of-day report command. Aggregates all sessions, commits, features, and position into one bordered summary. Shows day stats, session list, semantic "What Got Done" grouping, position at EOD, and day vibe.
- **`execution/wrap_stats.py`** — new deterministic scoring script (978 lines). Handles all session scoring computation: git metrics, streak, multiplier, raw/final score, badge evaluation (with once-per-day dedup), high score check, leaderboard consolidation. Outputs JSON for the `/wrap` prompt to render.

### Changed
- **`/stand-up`** — added WARNINGS section (surfaces audit WARN/FAIL findings in kick-off card with detail lines and "Fix now?" suggestions) and FOCUS section (2-3 coaching bullets from `stats.json` analysis: infra/product ratio, stale WARNs, commits/session trends, steps completed, time-of-day patterns, score trends)
- **`/vitals`** — added mandatory audit detail lines rule: WARN/FAIL items must each be shown on indented detail lines, using `--json` flag for reliable parsing
- **`/roast`** — added "And you..." developer habit analysis section: roasts session timing, infra/product ratio, score trends, badge patterns, commits/session, steps throughput, and streak from `stats.json`
- **`/wrap`** — rewrote to delegate all scoring computation to `execution/wrap_stats.py`. Steps 2+3 replaced with single script call. Display sections now reference `result.*` JSON fields. Prompt reduced from ~22K to ~17K chars.

---

## [v1.5.0] — 2026-03-02

### Changed
- **`/stand-up`** — rewritten as context-aware dual-mode command. Detects `.tmp/.session-start`: **kick-off mode** (no session) starts clock, reads project state, shows bordered card with plan, waits for sign-off. **Status mode** (session active) shows bordered daily status card with progress, momentum, activity since last milestone, blockers, pending decisions, and queue. Read-only in status mode.
- **`/commands`** — updated `/stand-up` description for dual-mode, updated smart filter section
- **Reference docs** — updated stand-up descriptions across README, SYSTEM-MAP, CUSTOMIZATION, and global-commands/README
- **CUSTOMIZATION** — corrected command count from 11 to 13 (added `/vitals`, `/commands` to list)

---

## [v1.4.0] — 2026-03-02

### Added
- **`/vitals`** — new workspace health check command: git status, quick audit, DOE Kit sync, STATE.md alignment, stale temp files. Bordered output with ✓/⚠️ per check.

### Changed
- **`/wrap`** — added quick audit to Step 1 housekeeping; replaced plain footer with bordered "System Checks" section showing audit results and DOE Kit sync status together
- **`/commands`** — updated to 13 commands, added `/vitals` under Quality category
- **README** — command count 12 → 13, added `/vitals` to Quality row in table
- **SYSTEM-MAP** — added vitals.md to file table, command reference, and directory tree

---

## [v1.3.0] — 2026-03-02

### Added
- **`setup.sh`** — one-command installer: copies commands to `~/.claude/commands/`, copies universal CLAUDE.md template (if none exists), activates git hooks, writes version receipt to `~/.claude/.doe-kit-version`
- **`/commands`** — new slash command replacing `/README`. Shows full command reference by category, checks installation status (missing commands), and checks GitHub for kit updates
- **Slash Commands section in README** — category table with smart filter explanation, links to `/commands` for full reference
- **Manual setup fallback** — collapsible details block in Quick Start for users who prefer not to use the script

### Changed
- Quick Start simplified from 6 steps to 3 (clone → `./setup.sh` → `/stand-up`)
- `global-commands/README.md` is now a short GitHub directory readme (no longer doubles as a command)
- Command count updated from 11 → 12 across README and command reference

### Removed
- `/README` command — replaced by `/commands`

---

## [v1.2.1] — 2026-03-01

### Changed
- `/sync-doe` now shows a bordered result summary box at the end of every sync — `✅ SYNCED`, `⏭️ NO CHANGES`, `❌ REJECTED`, or `⚠️ BLOCKED` with explanation and kit version

---

## [v1.2.0] — 2026-03-01

### Added
- **CLAUDE.md Rule 10: Parallelise by default** — automatically spawn sub-agents for independent tasks, flag sequential dependencies, commit one-at-a-time per Rule 6
- **CLAUDE.md Guardrail: Protect starter kit** — blocks direct edits to `~/doe-starter-kit`; all changes must go through `/sync-doe`

### Changed
- Renamed `/sync-kit` to `/sync-doe` across all files — command name, file (`sync-doe.md`), and 40+ references in 10 files. Better describes syncing DOE framework improvements.

---

## [v1.1.1] — 2026-02-28

### Added
- `/wrap` footer now shows DOE Kit version and sync status as the last line before closing

---

## [v1.1.0] — 2026-02-28

### Added
- **DOE Kit awareness** — `/stand-up`, `/crack-on`, `/sitrep`, and `/wrap` now check `~/doe-starter-kit` if it exists
- `/stand-up` and `/crack-on` show kit version + pending change count at session start
- `/sitrep` shows `DOE KIT` row with version and sync status
- `/wrap` nudges `/sync-doe` when DOE files have changed since last sync
- All four commands recommend `/sync-doe` when pending changes are detected

---

## [v1.0.0] — 2026-02-28

Initial release. 40 files across 8 directories.

### Added
- **CLAUDE.md** — 9 operating rules, guardrails, progressive disclosure triggers, directory structure
- **STATE.md** — Session memory template
- **ROADMAP.md** — Product roadmap template
- **SYSTEM-MAP.md** — Complete file-by-file documentation and relationship map
- **CUSTOMIZATION.md** — Guide for adapting the kit to new projects
- **Directives** — `_TEMPLATE.md`, `documentation-governance.md`, `claim-auditing.md`, `starter-kit-sync.md`
- **Execution** — `audit_claims.py` with universal checks and project extension point
- **11 slash commands** — `/stand-up`, `/crack-on`, `/wrap` (gamified), `/sitrep`, `/sync-doe`, `/pitch`, `/audit`, `/quick-audit`, `/roast`, `/eli5`, `/shower-thought`
- **Guardrail hooks** — `block_dangerous_commands.py`, `block_secrets_in_code.py`, `protect_directives.py`
- **Git hooks** — `commit-msg` (strip AI co-author trailers), `pre-commit` (fast audit)
- **Session timer** — `/stand-up` and `/crack-on` start clock, `/sitrep` and `/wrap` report duration
- **Gamification** — Scoring, badges, streaks, leaderboard, themed wrap-up cards
- **README.md** — Quick start guide and feature overview

### Fixed
- `commit-msg` hook uses macOS-compatible `sed -i ''` syntax
- `/sitrep` STATUS field has clearer instruction wording
- `/wrap` score table has separate high score / non-high score templates with `d[streak]` multiplier format

### Changed
- `/sync-doe` includes up-to-date check — stops early if nothing to sync
- Sync directive includes safety guardrails: pull-before-compare, three-way diff, additive merging, git stash backup
