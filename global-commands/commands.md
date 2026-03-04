Before showing the reference below, run a quick health check:

1. **Version:** Read `~/.claude/.doe-kit-version`. If it exists, show the version and install date. If not, show "DOE Kit: not installed — run `./setup.sh` from the starter kit".

2. **Installation check:** List all `.md` files in `~/.claude/commands/` and compare against the 22 expected commands below. Report installed count (e.g. "22/22 commands installed" or "20/22 — missing: /audit, /quick-audit").

3. **Update check:** Run `gh release view --repo iPolyphian/doe-starter-kit --json tagName -q .tagName` to get the latest release version. Compare with the installed version from step 1. If newer, show: "Update available: vX.Y.Z → run `cd ~/doe-starter-kit && git pull && ./setup.sh`". If current, show "✓ up to date". If the command fails (offline, no gh CLI), skip silently and just show "update check: skipped (offline or gh CLI not available)".

Format the health check as a compact status block:

```
DOE Kit v1.3.0 (installed 02/03/26) · ✓ up to date
22/22 commands installed
```

Or if issues are found:

```
DOE Kit v1.3.0 (installed 02/03/26) · update available: v1.4.0
20/22 commands installed — missing: /audit, /quick-audit
→ Run: cd ~/doe-starter-kit && git pull && ./setup.sh
```

Then show the full reference below.

---

# Slash Commands

Quick reference for all 22 `/commands`. These are global — install once with `./setup.sh`, available in every project. `/stand-up` is context-aware — it detects whether a session is active and adapts its output accordingly.

---

## Session Lifecycle

Commands that bookend your work sessions. `/stand-up` (in kick-off mode) and `/crack-on` start the session timer (writes to `.tmp/.session-start`), which `/sitrep` and `/wrap` read for elapsed time.

### `/stand-up`
Context-aware dual-mode command. **Kick-off mode** (no active session): starts the clock, reads project state (CLAUDE.md, STATE.md, todo.md, learnings.md), shows a bordered kick-off card with project context, presents a plan, and waits for sign-off. **Status mode** (session already running): shows a bordered daily status card with progress, momentum, recent activity since last milestone, blockers, pending decisions, and queue. Read-only in status mode — no clock, no execution. **Use at:** session start, or any time mid-project to check where things stand.

### `/crack-on`
Same context read as `/stand-up` kick-off mode, but picks up the next incomplete step and executes it immediately. One step — commit, push, stop, report. **Use at:** mid-session, when you want to resume without planning.

### `/sitrep`
Mid-session situation report. Shows mission, progress bar, completed/active/pending steps, commits, elapsed time, context usage, blockers, and queue. Read-only — no changes made. **Use at:** any time, to check status.

### `/wrap`
End-of-session routine. Updates STATE.md, todo.md, learnings.md. Computes session stats, prints a themed wrap-up card with haiku, timeline, and leaderboard. **Use at:** session end.

### `/eod`
End-of-day report. Aggregates all sessions, commits, features, and position into one bordered summary. Shows day stats, session list, semantic "What Got Done" grouping, position at EOD, and day vibe. **Use at:** end of day, after your last `/wrap`.

---

## Quality

### `/audit`
Full claim audit — checks governed docs, task format, roadmap consistency, orphan claims, staleness, and project-specific checks. Explains all FAIL/WARN items. **Use at:** before releases, periodic validation.

### `/quick-audit`
Fast checks only (<1 second) — front-matter, staleness, task format, version match. Says "All clear" if clean. **Use at:** quick pre-commit sanity check.

### `/vitals`
Workspace health check — git status, quick audit, DOE Kit sync, STATE.md alignment, stale temp files. Shows a bordered summary with ✓/⚠️ per check. Reports only, doesn't fix. **Use at:** session start (after stand-up), before wrapping, or any time you want a quick sanity check.

### `/fact-check`
Verifies the factual accuracy of a document against the actual codebase. Identifies inaccuracies and corrects them in place with a verification summary. **Use at:** after major changes, before releases, or when docs may have drifted from reality.

---

## Visual

Commands that generate beautiful standalone HTML pages for visual understanding.

### `/project-recap`
Rebuilds a mental model of a project's current state, recent decisions, and cognitive debt hotspots. Generates a visual HTML recap over a configurable time window. **Use when:** returning to a project after time away, or when you need to see the big picture.

### `/diff-review`
Generates a visual HTML diff showing before/after architecture comparison with code review analysis. Auto-detects scope from branch names, commit hashes, or PR numbers. **Use when:** reviewing changes before merging or after a feature branch.

### `/plan-review`
Compares current codebase state against a proposed implementation plan as a visual HTML review. Blueprint/editorial aesthetics. **Use when:** evaluating whether a plan is ready to execute.

### `/generate-visual-plan`
Produces a detailed visual HTML implementation plan with state machines, code snippets, edge cases, and feature specifications. **Use when:** designing a complex feature and want a visual spec.

### `/generate-web-diagram`
Generates a beautiful standalone HTML diagram with Mermaid visualizations and optional AI-generated illustrations. Opens in the browser. **Use when:** you need architecture diagrams, flow charts, or system maps.

### `/generate-slides`
Creates a magazine-quality HTML slide deck with distinctive aesthetics (Midnight Editorial, Warm Signal, etc.) and Mermaid diagram support. **Use when:** presenting ideas, pitches, or technical concepts.

---

## Utility

### `/pitch`
Generates 3–5 product ideas with structured pitches (size, type, value, effort). Only adds to ROADMAP.md with explicit approval. **Use when:** you want fresh feature ideas.

### `/roast`
Reads the codebase and roasts it. Specific, brutal, funny — references real files and real decisions, not generic jokes. **Use when:** you need a laugh.

### `/eli5`
Explains the current project and active work as if to a curious 5-year-old. Dinosaurs and biscuits included. **Use when:** you need to reset perspective or simplify complexity.

### `/shower-thought`
One genuinely interesting programming observation or paradox. Two sentences max. **Use when:** you want a break.

---

## Infrastructure

### `/sync-doe`
Syncs universal DOE framework improvements from the current project back to the starter kit repo (`~/doe-starter-kit`). Strips project-specific content, shows diffs for approval, commits, tags, pushes, and creates a GitHub release. **Use after:** completing [INFRA] features or discovering universal improvements.

### `/commands`
This command. Shows installation health check and the full command reference. **Use when:** you want to verify your setup or check for updates.

---

## Multi-Agent

### `/hq`
Multi-agent dashboard for parallel Claude Code sessions. Shows wave status, terminal liveness, task progress, cost estimates, and merge order. Modes: no active wave (help text), active wave (live dashboard). Requires `~/.claude/scripts/multi_agent.py` (installed by `setup.sh`). **Use when:** running parallel Claude Code sessions via wave management.

---

## Smart Filter (DOE Kit Sync Checks)

The lifecycle commands (`/stand-up` in kick-off mode, `/crack-on`, `/sitrep`, `/wrap`) check whether your project has DOE changes worth syncing to the starter kit. When comparing CLAUDE.md, they use a smart filter:

**Counts as pending** — changes to universal DOE sections: Operating Rules, Guardrails, Code Hygiene, Self-Annealing, Break Glass, Architecture: DOE.

**Ignored** — project-specific additions: Directory Structure entries, Progressive Disclosure triggers, project-specific comments. Rule of thumb: additions on top of the kit template are project-specific; modifications to existing template content are universal.

If pending changes are detected, the commands suggest running `/sync-doe`.
