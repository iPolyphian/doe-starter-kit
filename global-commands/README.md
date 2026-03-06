# Slash Commands

Quick reference for all custom `/commands`. These are global — available in every project.

**Session timer:** `/stand-up` (in kick-off mode) and `/crack-on` write a timestamp to `.tmp/.session-start`. This is read by `/sitrep` (elapsed time) and `/wrap` (total duration + per-commit timeline). Cleaned up naturally when `.tmp/` is cleared between sessions.

**DOE Kit awareness:** `/stand-up` (kick-off), `/crack-on`, `/sitrep`, and `/wrap` check `~/doe-starter-kit` if it exists. All use smart diffing for CLAUDE.md (only universal sections trigger `*`, project-specific sections are ignored). Kit version is pinned in STATE.md.

**Contract enforcement:** `/stand-up` (kick-off) surfaces contract health for the next step (informational). `/crack-on` validates contracts before starting work and runs verification before marking steps done. Both enforce the same discipline that `--complete` provides in wave mode.

---

## Session Lifecycle

### `/stand-up`
Context-aware dual-mode command. **Kick-off mode** (no active session): starts the clock, reads project state, shows a bordered kick-off card with project name (right-aligned), feature, progress, DOE Kit status, contract health, last session summary, plan, and coaching focus. Waits for sign-off. **Status mode** (session already running): shows a bordered status card with progress, momentum, recent activity, and queue.
*Added 28/02/26 · Updated 05/03/26*

### `/crack-on`
Same context read as stand-up kick-off mode, but picks up the next incomplete step immediately. Validates task contracts before starting (pre-flight) and runs all Verify: patterns before marking steps done (post-completion). One step at a time — commit, push, stop, report. Starts the session timer.
*Added 28/02/26 · Updated 05/03/26*

### `/sitrep`
Mid-session situation report. Shows current feature progress, completed/active/pending steps, session commits, elapsed time, DOE Kit sync status, blockers, and queue. Read-only.
*Added 28/02/26 · Updated 28/02/26*

### `/wrap`
End-of-session routine. Updates STATE.md, todo.md, learnings.md. Computes session stats, prints a themed wrap-up card with title card, numbers, timeline, system checks, and agents-spawned count.
*Added 27/02/26 · Updated 04/03/26*

### `/eod`
End-of-day report aggregating all sessions, commits, features, and position. Answers "what did I do today?" Read-only — no files modified.
*Added 03/03/26*

## Quality

### `/audit`
Comprehensive project audit — claims (governed docs, task format, roadmap consistency, staleness), workspace health (git status, stale temp files, STATE.md alignment), and DOE framework integrity (required files, hooks, commands, kit sync). Single bordered output with all findings.
*Added 28/02/26 · Updated 06/03/26*

### `/fact-check`
Verifies the factual accuracy of a document against the actual codebase and corrects inaccuracies in place.
*Added 04/03/26*

### `/review`
Adversarial code reviewer. Reviews staged changes (or specified files) for bugs, security issues, performance problems, and code quality. Direct, specific, and neutral — finds problems, not praise.
*Added 04/03/26*

### `/codemap`
Generates a structured project index at `.claude/codemap.md`. Scans file tree, maps key modules, functions, and entry points. Helps agents navigate without re-exploring each session.
*Added 04/03/26*

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
Multi-agent dashboard. Shows wave status, task claims, session health, and coordination info. When no wave is active, shows help card with setup instructions.
*Added 03/03/26 · Renamed from /hq 06/03/26*

### `/agent-launch`
Dual-mode command. **Launch mode** (no active wave): scans Queue and Current for missing contracts, auto-generates them with user approval, identifies parallelisable features, builds wave JSON, previews conflicts and cost, launches, then auto-claims the first task and starts working. **Join mode** (active wave exists): claims the next unclaimed task and starts working immediately. One command for both — run `/agent-launch` in every terminal.
*Added 04/03/26 · Updated 05/03/26*

## Utility

### `/pitch`
Generates 3-5 product ideas with structured pitches (size, type, value, effort). Only adds to ROADMAP.md with explicit approval.
*Added 28/02/26*

### `/roast`
Reads the codebase and roasts it. Specific, brutal, funny. References real files and real decisions.
*Added 28/02/26*

## Infrastructure

### `/sync-doe`
Syncs universal DOE improvements from the current project back to the starter kit repo (`~/doe-starter-kit`). Reads the sync directive, strips project-specific content, shows diffs for approval, commits and pushes to GitHub.
*Added 28/02/26*

### `/pull-doe`
Reverse sync — pulls DOE Kit updates into the current project. Reads the pull directive, compares kit files against local copies, shows diffs for approval, merges additively.
*Added 04/03/26*

### `/commands`
Shows installation health check and the full command reference. Checks DOE Kit version, installed command count, and available updates.
*Added 01/03/26*
