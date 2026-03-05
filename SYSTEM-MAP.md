# DOE Starter Kit — System Map

How all the files work together. Read this if you're confused about what does what.

## What loads automatically (Claude Code reads these at launch)

```
./CLAUDE.md              ← Your project rules. Claude reads this first, every session.
~/.claude/CLAUDE.md      ← Your universal learnings. Auto-loaded into every project.
```

Everything else is loaded **on demand** — Claude reads them because CLAUDE.md tells it to.

## What Claude checks at session start (Rule #1)

```
CLAUDE.md tells Claude to check these:
├── tasks/todo.md        ← What's in progress, what's next
└── STATE.md             ← Decisions, blockers, where we left off
```

## What Claude checks before building (Progressive Disclosure)

```
CLAUDE.md tells Claude to check these before starting work:
├── learnings.md         ← Project-specific patterns and gotchas
├── STATE.md             ← Recent decisions that affect this work
└── directives/          ← SOPs for recurring tasks (if a trigger matches)
    ├── documentation-governance.md  ← Governed docs checklist + front-matter format
    └── claim-auditing.md            ← When/how to run audits
```

## File purposes

### 📋 The Rules (you update via me)

| File | Goes to | Lines | Purpose |
|------|---------|-------|---------|
| CLAUDE.md | `./CLAUDE.md` | ~115 | The operating system. 9 rules, guardrails with proof requirement, break glass procedure, code hygiene. Auto-loaded. |
| settings.json | `./.claude/settings.json` | ~25 | 3 PreToolUse guardrail hooks (PostToolUse hooks now in global `~/.claude/settings.json`) |
| SYSTEM-MAP.md | `./SYSTEM-MAP.md` | — | This breakdown. For you, not Claude. |
| CUSTOMIZATION.md | `./CUSTOMIZATION.md` | — | What to keep, customize, or clear when starting a new project. For you, not Claude. |

### 🔒 The Guardrails (enforce the rules automatically)

| File | Goes to | Purpose |
|------|---------|---------|
| protect_directives.py | `./.claude/hooks/` | Blocks editing existing SOPs. Allows creating new ones. |
| block_secrets_in_code.py | `./.claude/hooks/` | Blocks API keys outside .env |
| block_dangerous_commands.py | `./.claude/hooks/` | Blocks force-push, rm -rf, etc |
| commit-msg | `./.githooks/` | Strips AI co-author trailers from git commits |
| pre-commit | `./.githooks/` | Runs fast claim audit checks before every commit. Blocks on FAILs. |

### 🧠 The Memory (Claude writes, Claude reads)

| File | Goes to | Purpose |
|------|---------|---------|
| STATE.md | `./STATE.md` | Session memory. Blockers, current position, last session. Decisions go in learnings.md. Survives /clear. |
| learnings.md | `./learnings.md` | Project patterns. Max 50 lines. Governed doc. |
| stats.json | `./.claude/stats.json` | Persistent session stats, streaks, badges, scores. Updated by /wrap. |
| universal-claude-md-template.md | `~/.claude/CLAUDE.md` | One-time setup. Cross-project patterns. Max 30 lines. |

### 📝 The Workflow (task tracking)

| File | Goes to | Purpose |
|------|---------|---------|
| todo.md | `./tasks/todo.md` | Active tasks, steps, timestamps. Features tagged [APP] or [INFRA]. |
| archive.md | `./tasks/archive.md` | Completed features moved from todo |
| ROADMAP.md | `./ROADMAP.md` | Ideas notepad. No automation. |

### 📐 The Directives (SOPs)

| File | Goes to | Purpose |
|------|---------|---------|
| _TEMPLATE.md | `./directives/` | Template for new SOPs |
| documentation-governance.md | `./directives/` | Governed doc registry, front-matter format, staleness rules |
| claim-auditing.md | `./directives/` | When/how to audit claims, pre-commit integration |
| starter-kit-sync.md | `./directives/` | How to sync DOE improvements back to the starter kit repo |

### 🔍 The Audit System

| File | Goes to | Purpose |
|------|---------|---------|
| audit_claims.py | `./execution/` | Automated false-positive detection. 6 universal checks (incl. active wave detection). Extensible with project-specific checks via `@register()` decorator. |
| wrap_stats.py | `./execution/` | Deterministic session scoring. Gathers git metrics, computes streak/multiplier/score/badges, updates stats.json, outputs JSON for `/wrap` to render. |

### ⚡ The Commands (global — install once, available in every project)

All slash commands install to `~/.claude/commands/` so they work across every DOE project. They reference relative paths (`STATE.md`, `tasks/todo.md`, etc.) so they're project-agnostic.

| File | Goes to | Purpose |
|------|---------|---------|
| wrap.md | `~/.claude/commands/` | Type `/wrap` — gamified session summary; calls `execution/wrap_stats.py` for deterministic scoring, badges, streaks, genre title cards |
| eod.md | `~/.claude/commands/` | Type `/eod` — end-of-day report aggregating all sessions, commits, features, and position |
| pitch.md | `~/.claude/commands/` | Type `/pitch` — generate 3-5 product improvement ideas based on current state |
| audit.md | `~/.claude/commands/` | Type `/audit` — full claim audit with explanations |
| quick-audit.md | `~/.claude/commands/` | Type `/quick-audit` — fast checks only (<1 second) |
| vitals.md | `~/.claude/commands/` | Type `/vitals` — workspace health check (git, audit, DOE sync, STATE alignment, temp files) |
| stand-up.md | `~/.claude/commands/` | Type `/stand-up` — dual-mode: kick-off (no session) starts clock + plan; status (mid-session) shows daily status card |
| crack-on.md | `~/.claude/commands/` | Type `/crack-on` — start session clock, pick up next step, commit, push, stop |
| roast.md | `~/.claude/commands/` | Type `/roast` — comedy roast of the codebase + developer habits from stats.json |
| eli5.md | `~/.claude/commands/` | Type `/eli5` — explain current work like you're 5 |
| shower-thought.md | `~/.claude/commands/` | Type `/shower-thought` — one weird programming observation |
| sitrep.md | `~/.claude/commands/` | Type `/sitrep` — mid-session situation report with progress, commits, elapsed time |
| sync-doe.md | `~/.claude/commands/` | Type `/sync-doe` — sync DOE improvements back to the starter kit repo |
| hq.md | `~/.claude/commands/` | Type `/hq` — multi-agent dashboard for wave status, terminal liveness, task progress, merge order |
| README.md | `~/.claude/commands/` | Quick reference for all 15 slash commands |

### 🔀 Multi-Agent Coordination (global — install once, available in every project)

Multi-agent files install to machine-level locations via `setup.sh`. They use `Path.cwd()` so they work from any project directory.

| File | Goes to | Purpose |
|------|---------|---------|
| multi_agent.py | `~/.claude/scripts/` | Wave management, task claiming, session registry, heartbeats, merge protocol, cost tracking. All state in `.tmp/waves/`. Accepts `--project-root DIR` override. |
| heartbeat.py | `~/.claude/hooks/` | PostToolUse: updates session heartbeat every 30s during active waves |
| context_monitor.py | `~/.claude/hooks/` | PostToolUse: warns at 60% context usage, stops at 80% for graceful handoff |

### 📐 The Plans & Sync

| File | Goes to | Purpose |
|------|---------|---------|
| gamified-wrap.md | `./.claude/plans/` | Design plan for the gamified wrap system |
| claude-chat-sync-prompt.md | `./.claude/` | Paste into Claude Chat to sync it with Claude Code changes |

## How they feed into each other

```
SESSION START
│
├─→ CLAUDE.md (auto-loaded — the rules)
├─→ ~/.claude/CLAUDE.md (auto-loaded — universal learnings)  
├─→ /stand-up (kick-off mode) or /crack-on starts session clock → .tmp/.session-start
│
├─→ Rule #1 says: check todo.md + STATE.md
│   ├─→ tasks/todo.md → shows incomplete steps
│   └─→ STATE.md → shows last session's decisions/blockers
│
├─→ Progressive Disclosure says: check learnings + directives
│   ├─→ learnings.md → project patterns
│   └─→ directives/ → SOPs if a trigger matches
│       ├─→ documentation-governance.md → governed docs checklist
│       └─→ claim-auditing.md → audit procedure
│
DURING WORK
│
├─→ Rule #8 before every commit: check STATE.md + learnings.md + governed docs
├─→ .claude/settings.json → fires PreToolUse guardrail hooks
│   ├─→ protect_directives.py → blocks edits to existing SOPs
│   ├─→ block_secrets_in_code.py → blocks API keys outside .env
│   └─→ block_dangerous_commands.py → blocks force-push, rm -rf, etc.
├─→ ~/.claude/settings.json → fires PostToolUse hooks (merged by setup.sh)
│   ├─→ heartbeat.py → updates session heartbeat during waves
│   └─→ context_monitor.py → warns when context is running low
├─→ .githooks/pre-commit → runs fast claim audit before every commit
│
├─→ execution/ → Claude runs scripts instead of inline code
│   ├─→ audit_claims.py → automated false-positive detection
│   └─→ wrap_stats.py → deterministic session scoring for /wrap
├─→ ~/.claude/scripts/multi_agent.py → wave coordination for parallel sessions
├─→ .claude/plans/ → Claude reads feature designs
├─→ .tmp/ → scratch space for intermediate files
│
SESSION END (or /wrap)
│
├─→ STATE.md updated with decisions + position
├─→ tasks/todo.md updated with timestamps
├─→ learnings.md or ~/.claude/CLAUDE.md updated if anything was learned
├─→ .claude/stats.json updated with score, streak, badges
├─→ directives/ gets new SOP if process was recurring (retro)
├─→ tasks/archive.md receives old completed features
├─→ Git commit + push
└─→ Gamified session summary printed (genre title, badges, leaderboard)
```

## Slash commands

| Command | What it does |
|---------|-------------|
| `/stand-up` | Dual-mode: kick-off (no session) starts clock + bordered card + plan; status (mid-session) shows progress, momentum, blockers, decisions |
| `/crack-on` | Start session clock, read state, pick up next incomplete step, commit, push, stop, report |
| `/wrap` | End-of-session routine: housekeeping, git metrics, stats.json, gamified summary |
| `/pitch` | Generate 3-5 product improvement ideas. Approved ideas go to ROADMAP.md |
| `/roast` | Comedy roast of the codebase. Specific, brutal, funny. |
| `/eli5` | Explain current work like you're 5. Dinosaurs included. |
| `/shower-thought` | One weird programming observation. Two sentences max. |
| `/audit` | Full claim audit — all checks, detailed explanations |
| `/quick-audit` | Fast checks only (<1 second) — front-matter, staleness, task format |
| `/vitals` | Workspace health check — git, audit, DOE sync, STATE alignment, temp files |
| `/sitrep` | Mid-session situation report — progress bar, commits, elapsed time, blockers, context usage |
| `/hq` | Multi-agent dashboard — wave status, terminal liveness, task progress, merge order |
| `/sync-doe` | Sync universal DOE improvements from current project to the starter kit repo |

## What's project-level vs machine-level

```
PROJECT (lives in your repo, shared via git)
├── CLAUDE.md
├── CUSTOMIZATION.md
├── STATE.md  
├── ROADMAP.md
├── SYSTEM-MAP.md
├── learnings.md
├── universal-claude-md-template.md
├── .gitignore
├── tasks/
│   ├── todo.md
│   └── archive.md
├── directives/
│   ├── _TEMPLATE.md
│   ├── documentation-governance.md
│   ├── claim-auditing.md
│   └── starter-kit-sync.md
├── execution/
│   ├── audit_claims.py
│   └── wrap_stats.py
├── .claude/
│   ├── settings.json (PreToolUse only)
│   ├── stats.json
│   ├── claude-chat-sync-prompt.md
│   ├── hooks/
│   │   ├── protect_directives.py
│   │   ├── block_secrets_in_code.py
│   │   └── block_dangerous_commands.py
│   └── plans/
│       └── gamified-wrap.md
├── .githooks/
│   ├── commit-msg
│   └── pre-commit
├── .tmp/
└── .env (git-ignored)

MACHINE (lives on your computer, applies to all projects)
├── ~/.claude/CLAUDE.md
├── ~/.claude/settings.json (PostToolUse hooks merged by setup.sh)
├── ~/.claude/commands/
│   ├── README.md
│   ├── wrap.md
│   ├── pitch.md
│   ├── stand-up.md
│   ├── crack-on.md
│   ├── roast.md
│   ├── eli5.md
│   ├── shower-thought.md
│   ├── audit.md
│   ├── quick-audit.md
│   ├── vitals.md
│   ├── sitrep.md
│   ├── sync-doe.md
│   ├── hq.md
│   └── eod.md
├── ~/.claude/hooks/
│   ├── heartbeat.py
│   └── context_monitor.py
└── ~/.claude/scripts/
    └── multi_agent.py
```

Total: 49 files across 10 directories. If you see a file not on this list, it shouldn't be there.
