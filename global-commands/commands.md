Before showing the reference below, run a quick health check:

1. **Version:** Read `~/.claude/.doe-kit-version`. If it exists, show the version and install date. If not, show "DOE Kit: not installed — run `./setup.sh` from the starter kit".

2. **Installation check:** List all `.md` files in `~/.claude/commands/` and compare against the 24 expected commands below. Report installed count (e.g. "24/24 commands installed" or "22/24 — missing: /audit, /review").

3. **Update check:** Run `gh release view --repo iPolyphian/doe-starter-kit --json tagName -q .tagName` to get the latest release version. Compare with the installed version from step 1. If newer, show: "Update available: vX.Y.Z → run `cd ~/doe-starter-kit && git pull && ./setup.sh`". If current, show "up to date". If the command fails (offline, no gh CLI), skip silently and just show "update check: skipped (offline or gh CLI not available)".

Format the health check as a compact status block:

```
DOE Kit v1.20.4 (installed 06/03/26) · up to date
24/24 commands installed
```

Or if issues are found:

```
DOE Kit v1.20.4 (installed 06/03/26) · update available: v1.21.0
22/24 commands installed — missing: /audit, /review
→ Run: cd ~/doe-starter-kit && git pull && ./setup.sh
```

Then show the full reference below.

---

# Slash Commands

Quick reference for all 24 `/commands`. These are global — install once with `./setup.sh`, available in every project. `/stand-up` is context-aware — it detects whether a session is active and adapts its output accordingly.

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
Comprehensive project audit — claims (governed docs, task format, roadmap consistency, staleness), workspace health (git status, stale temp files, STATE.md alignment), and DOE framework integrity (required files, hooks, commands, kit sync). Single bordered output with all findings. **Use at:** before releases, periodic validation, any time you want a full health check.

### `/agent-verify`
Verifies contract criteria for the current task. Runs all `[auto]` criteria with auto-fix loop (up to 3 attempts), presents `[manual]` criteria as a checklist. Works in solo and wave mode. **Use at:** after completing a task step.

### `/fact-check`
Verifies the factual accuracy of a document against the actual codebase. Identifies inaccuracies and corrects them in place with a verification summary. **Use at:** after major changes, before releases, or when docs may have drifted from reality.

### `/review`
Adversarial code review. Checks security, correctness, dead code, breaking changes, and contract compliance. Finds problems, not praise. **Use at:** before committing significant changes.

### `/test-suite`
Runs the project's accumulated test suite from `tests/suite.json`. Updates metadata, handles --prune/--add options. **Use at:** after changes that might break existing behaviour.

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
Generates 3-5 product ideas with structured pitches (size, type, value, effort). Only adds to ROADMAP.md with explicit approval. **Use when:** you want fresh feature ideas.

### `/roast`
Reads the codebase and roasts it. Specific, brutal, funny — references real files and real decisions, not generic jokes. **Use when:** you need a laugh.

### `/codemap`
Generates a structured project index at `.claude/codemap.md`. Maps file structure, key files, data flow, and active patterns. **Use when:** onboarding to a project or refreshing the navigation index.

### `/commands`
This command. Shows installation health check and the full command reference. **Use when:** you want to verify your setup or check for updates.

---

## Infrastructure

### `/sync-doe`
Syncs universal DOE framework improvements from the current project back to the starter kit repo (`~/doe-starter-kit`). Strips project-specific content, shows diffs for approval, commits, tags, pushes, and creates a GitHub release. **Use after:** completing [INFRA] features or discovering universal improvements.

### `/pull-doe`
Syncs improvements from the starter kit into the current project. Compares versions, shows diffs, proposes updates, merges additively. **Use when:** the kit has a newer version than your project.

---

## Multi-Agent

### `/agent-launch`
Launches a multi-agent wave. Checks contracts, identifies parallelisable features, creates plans, builds wave file, previews, and launches. **Use when:** starting parallel Claude Code sessions.

### `/agent-status`
Multi-agent dashboard for parallel Claude Code sessions. Shows wave status, terminal liveness, task progress, cost estimates, and merge order. Modes: `--plan`, `--preview`, `--launch`, `--merge`, `--reclaim`, `--abort`, `--watch`. **Use when:** monitoring or managing an active wave.

---

## Smart Filter (DOE Kit Sync Checks)

The lifecycle commands (`/stand-up` in kick-off mode, `/crack-on`, `/sitrep`, `/wrap`) check whether your project has DOE changes worth syncing to the starter kit. When comparing CLAUDE.md, they use a smart filter:

**Counts as pending** — changes to universal DOE sections: Operating Rules, Guardrails, Code Hygiene, Self-Annealing, Break Glass, Architecture: DOE.

**Ignored** — project-specific additions: Directory Structure entries, Progressive Disclosure triggers, project-specific comments. Rule of thumb: additions on top of the kit template are project-specific; modifications to existing template content are universal.

Commands show `DOE vX.Y.Z *` when either the kit's latest tag is newer than STATE.md's synced version (inbound) or any syncable files differ between the project and kit (outbound). The `*` means run `/sync-doe` or `/pull-doe` — either will show what's needed.
