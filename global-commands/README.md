# Slash Commands

Quick reference for all custom `/commands`. These are global — available in every project.

**Session timer:** `/stand-up` and `/crack-on` write a timestamp to `.tmp/.session-start`. This is read by `/sitrep` (elapsed time) and `/wrap` (total duration + per-commit timeline). Cleaned up naturally when `.tmp/` is cleared between sessions.

---

### 1. `/stand-up`
Reads project state, shows what's in progress and what's next. Presents a plan and waits for sign-off before doing anything. Starts the session timer.
*Added 28/02/26 · Updated 28/02/26 (session timer)*

### 2. `/crack-on`
Same context read as stand-up, but picks up the next incomplete step immediately. One step at a time — commit, push, stop, report. Starts the session timer.
*Added 28/02/26 · Updated 28/02/26 (session timer)*

### 3. `/wrap`
End-of-session routine. Updates STATE.md, todo.md, learnings.md. Computes session stats, awards badges, prints a themed wrap-up card with score and leaderboard. Now includes session duration and a commit-by-commit timeline.
*Added 27/02/26 · Updated 28/02/26 (session timer + timeline)*

### 4. `/roast`
Reads the codebase and roasts it. Specific, brutal, funny. References real files and real decisions.
*Added 28/02/26*

### 5. `/eli5`
Explains the current project and active work as if you're a curious 5-year-old. Dinosaurs and biscuits included.
*Added 28/02/26*

### 6. `/shower-thought`
One genuinely interesting programming observation or paradox. Two sentences max.
*Added 28/02/26*

### 7. `/pitch`
Generates 3-5 product ideas with structured pitches (size, type, value, effort). Only adds to ROADMAP.md with explicit approval.
*Added 28/02/26*

### 8. `/audit`
Runs full claim audit — checks governed docs, task format, roadmap consistency, orphan claims, and project-specific checks. Explains all FAIL/WARN items.
*Added 28/02/26*

### 9. `/quick-audit`
Fast checks only (<1 second) — front-matter, staleness, task format, version match. Says "All clear" if clean.
*Added 28/02/26*

### 10. `/sitrep`
Mid-session situation report. Shows current feature progress, completed/active/pending steps, session commits, elapsed time, blockers, and queue. Uses session timer if available, falls back to first-commit method. Read-only — no changes made.
*Added 28/02/26 · Updated 28/02/26 (session timer)*

### 11. `/sync-doe`
Syncs universal DOE framework improvements from the current project back to the starter kit repo (`~/doe-starter-kit`). Reads `directives/starter-kit-sync.md`, strips project-specific content, shows diffs for approval, commits and pushes. Uses `/add-dir` if the starter kit isn't already loaded.
*Added 28/02/26*
