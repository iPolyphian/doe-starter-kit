# Slash Commands

Quick reference for all custom `/commands`. These are global — available in every project.

**Session timer:** `/stand-up` (in kick-off mode) and `/crack-on` write a timestamp to `.tmp/.session-start`. This is read by `/sitrep` (elapsed time) and `/wrap` (total duration + per-commit timeline). Cleaned up naturally when `.tmp/` is cleared between sessions.

**DOE Kit awareness:** `/stand-up` (kick-off), `/crack-on`, `/sitrep`, and `/wrap` check `~/doe-starter-kit` if it exists. All use smart diffing for CLAUDE.md (only universal sections trigger `*`, project-specific sections are ignored). Kit version is pinned in STATE.md.

**Contract enforcement:** `/stand-up` (kick-off) surfaces contract health for the next step (informational). `/crack-on` validates contracts before starting work and runs verification before marking steps done. Both enforce the same discipline that `--complete` provides in wave mode.

---

## Session Lifecycle

### `/stand-up`
Context-aware dual-mode command. **Kick-off mode** (no active session): starts the clock, reads project state, shows a bordered kick-off card with project name (right-aligned), feature, progress, blockers (from STATE.md), DOE Kit status with directional sync indicators (push/pull/push+pull), pipeline sync (Up Next vs Queue mismatch detection), contract health, last session summary, plan, and coaching focus. 100-session milestone celebration card. Waits for sign-off. **Status mode** (session already running): shows a bordered status card with progress, blockers, momentum, recent activity, and queue.
*Added 28/02/26 · Updated 10/03/26*

### `/crack-on`
Same context read as stand-up kick-off mode, but picks up the next incomplete step immediately. Validates task contracts before starting (pre-flight) and runs all Verify: patterns before marking steps done (post-completion). One step at a time — commit, push, stop, report. Starts the session timer.
*Added 28/02/26 · Updated 05/03/26*

### `/sitrep`
Mid-session situation report. Shows current feature progress, completed/active/pending steps, session commits, elapsed time, DOE Kit sync status, blockers, and queue. Read-only.
*Added 28/02/26 · Updated 28/02/26*

### `/wrap`
End-of-session routine. Updates STATE.md, todo.md, learnings.md. Computes session stats via `wrap_stats.py`, generates a visual HTML wrap-up via `wrap_html.py` with summary + breakdowns, commit groups with timeline percentages, decision/learning pills, system checks, and session vibe. Registers the project in `~/.claude/project-registry.json` for `/hq`. Opens in browser.
*Added 27/02/26 · Updated 10/03/26*

### `/eod`
End-of-day report aggregating all sessions into a visual HTML page via `eod_html.py`. Daily timeline, commit breakdown bars, 9-metric grid, features completed, and position summary. Answers "what did I do today?" — or for any past date (e.g. `/eod yesterday`, `/eod 2026-03-18`). Pulls from Gist if local data unavailable. Read-only. Opens in browser.
*Added 03/03/26 · Updated 24/03/26*

## Quality

### `/audit`
Comprehensive project audit — claims (governed docs, task format, roadmap consistency, staleness), workspace health (git status, stale temp files, STATE.md alignment), and DOE framework integrity (required files, hooks, commands, kit sync). Single bordered output with all findings.
*Added 28/02/26 · Updated 06/03/26 (merged /quick-audit, /vitals, /doe-health)*

### `/agent-verify`
Verifies contract criteria for the current task. Runs all `[auto]` criteria with auto-fix loop (up to 3 attempts), presents `[manual]` criteria as a checklist. Works in solo and wave mode.
*Added 05/03/26*

### `/fact-check`
Verifies the factual accuracy of a document against the actual codebase and corrects inaccuracies in place.
*Added 04/03/26*

### `/review`
Adversarial code reviewer with confidence scoring. Two-pass (spec compliance then code quality) in a single bordered box. Supports arguments: `--spec`, `--code`, `--tests`, `--all`, or a commit hash. Findings scored 0-100, only 80+ reported. Tags: SECURITY, BUG, BREAKING, DEAD, SILENT, CONVENTION, SCOPE. Verdict: PASS / PASS WITH NOTES / FAIL.
*Added 04/03/26 · Updated 24/03/26*

### `/test-suite`
Runs the project's accumulated test suite from `tests/suite.json`. Updates metadata, handles --prune/--add options.
*Added 05/03/26*

### `/codemap`
Generates a structured project index at `.claude/codemap.md`. Scans file tree, maps key modules, functions, and entry points. Helps agents navigate without re-exploring each session.
*Added 04/03/26*

### `/snagging`
Generates (or regenerates) an interactive HTML manual test checklist for the current feature. Identifies unchecked `[manual]` items from todo.md, optionally runs an automated code trace first, then calls `execution/generate_test_checklist.py`. Outputs a summary card and opens the checklist in the browser.
*Added 16/03/26*

### `/request-doe-feature`
Structured feature request for the DOE starter kit. Guides through description, use case, and context. Scans existing issues for duplicates, sanitises content, and files a GitHub Issue with labels on the upstream repo. Falls back to local markdown if `gh` is unavailable.
*Added 24/03/26*

### `/report-doe-bug`
Triage-first DOE framework bug reporter. 5-phase flow: gather user description + Claude's reconstruction + environment, check if fixed in newer version (route to `/pull-doe`), detect user error (route to tutorial docs), search for duplicates (offer to comment), then sanitise and file a GitHub Issue on the upstream repo with labels. Falls back to local markdown if `gh` is unavailable.
*Added 18/03/26*

### `/doe-health`
Runs the DOE methodology testing framework (`execution/test_methodology.py`). Checks structural integrity: session discipline, contract completeness, learnings freshness, trigger coverage, review discipline, CLAUDE.md quality grading, and cross-reference consistency.
*Added 24/03/26*

### `/code-trace`
Reads CLAUDE.md to understand project structure, then traces execution paths for a given function, endpoint, or feature. Maps the call chain from entry point to side effects.
*Added 24/03/26*

## Visual

### `/project-recap`
Generates a visual HTML project recap — current state, recent decisions, and cognitive debt hotspots. Opens in browser.
*Added 04/03/26*

### `/diff-review`
Generates a visual HTML diff review — before/after architecture comparison with code review analysis. Opens in browser.
*Added 04/03/26*

### `/plan-review`
Generates a visual HTML plan review — current codebase state vs. proposed implementation plan. Opens in browser.
*Added 04/03/26*

### `/generate-visual-plan`
Generates a visual HTML implementation plan — detailed feature spec with state machines, code snippets, and edge cases. Opens in browser.
*Added 04/03/26*

### `/generate-web-diagram`
Generates a beautiful standalone HTML diagram and opens it in the browser.
*Added 04/03/26*

### `/generate-slides`
Generates a stunning magazine-quality slide deck as a self-contained HTML page. Opens in browser.
*Added 04/03/26*

## Multi-Agent

### `/agent-status`
Multi-agent dashboard. Shows wave status, task claims, session health, and coordination info. Modes: `--plan`, `--preview`, `--launch`, `--merge`, `--reclaim`, `--abort`, `--watch`.
*Added 03/03/26 · Updated 06/03/26 (renamed from /hq)*

### `/agent-launch`
Dual-mode command. **Launch mode** (no active wave): scans Queue and Current for missing contracts, auto-generates them with user approval, identifies parallelisable features, builds wave JSON, previews conflicts and cost, launches, then auto-claims the first task and starts working. **Join mode** (active wave exists): claims the next unclaimed task and starts working immediately. One command for both — run `/agent-launch` in every terminal.
*Added 04/03/26 · Updated 05/03/26*

## Product

### `/scope`
Conversational feature scoping command. Guides a fuzzy idea through three phases (Explore, Define, Bound) to produce a structured brief. Phase 0 reflects the idea back until aligned. Phase 1 nails down problem, users, and success criteria. Phase 2 draws scope boundaries. Outputs a brief to `.claude/plans/{feature}-brief.md` and updates ROADMAP.md with a SCOPED status tag.
*Added 10/03/26*

### `/pitch`
Generates 3-5 product ideas with structured pitches (size, type, value, effort). Only adds to ROADMAP.md with explicit approval.
*Added 28/02/26*

## Utility

### `/roast`
Reads the codebase and roasts it. Specific, brutal, funny. References real files and real decisions.
*Added 28/02/26*

## Infrastructure

### `/hq`
Unified project dashboard. Reads `~/.claude/project-registry.json`, loads each project's `.claude/stats.json`, generates a single-page app with portfolio view and per-project drill-down (SPA hash routing). Shows project cards with recent activity, week-by-week session history, feature swimlanes, timeline scrubber, and search. Light/dark theme based on time of day. Opens in browser.
*Added 10/03/26 (replaces /archive-global)*

### `/sync-doe`
Syncs universal DOE improvements from the current project back to the starter kit repo (`~/doe-starter-kit`). Reads the sync directive, strips project-specific content, shows diffs for approval, commits and pushes to GitHub.
*Added 28/02/26*

### `/pull-doe`
Reverse sync — pulls DOE Kit updates into the current project. Reads the pull directive, compares kit files against local copies, shows diffs for approval, merges additively.
*Added 04/03/26*

### `/commands`
Shows installation health check and the full command reference. Checks DOE Kit version, installed command count, and available updates.
*Added 01/03/26 · Updated 06/03/26*
