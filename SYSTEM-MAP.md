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
└── STATE.md             ← Blockers, current position, where we left off
```

## What Claude checks before building (Progressive Disclosure)

```
CLAUDE.md tells Claude to check these before starting work:
├── learnings.md         ← Project-specific patterns, decisions, and gotchas
├── STATE.md             ← Current blockers that affect this work
└── directives/          ← Phase-based directives loaded by trigger:
    ├── planning-rules.md      ← Contracts, dependencies, scale-aware planning
    ├── building-rules.md      ← Branches, code hygiene, file ownership, DAG push
    ├── delivery-rules.md      ← Retros, guardrails, performance budgets
    ├── context-management.md  ← Post-compaction, solo/parallel/formal modes
    ├── self-annealing.md      ← Failure response, learnings curation, degradation
    ├── framework-evolution.md ← Track native Claude Code features, absorption
    ├── adversarial-review/    ← Multi-agent scored review with custom agents
    ├── documentation-governance.md  ← Governed docs checklist + front-matter format
    └── claim-auditing.md            ← When/how to run audits
```

## File purposes

### 📋 The Rules (you update via me)

| File | Goes to | Purpose |
|------|---------|---------|
| CLAUDE.md | `./CLAUDE.md` | The operating system. 9 rules, guardrails, code hygiene, break glass, triggers. Auto-loaded. |
| settings.json | `./.claude/settings.json` | 3 pre-action hooks (protect directives, block secrets, block dangerous commands) |
| SYSTEM-MAP.md | `./SYSTEM-MAP.md` | This breakdown. For you, not Claude. |
| CUSTOMIZATION.md | `./CUSTOMIZATION.md` | What to keep, customize, or clear when starting a new project. For you, not Claude. |

### 🔒 The Guardrails (enforce the rules automatically)

| File | Goes to | Purpose |
|------|---------|---------|
| protect_directives.py | `./.claude/hooks/` | Blocks editing existing SOPs. Allows creating new ones. |
| block_secrets_in_code.py | `./.claude/hooks/` | Blocks API keys outside .env |
| block_dangerous_commands.py | `./.claude/hooks/` | Blocks force-push, rm -rf, etc |
| commit-msg | `./.githooks/` | Strips AI co-author trailers from git commits |
| pre-commit | `./.githooks/` | Runs fast claim audit checks before every commit. Blocks on FAILs. |
| pre-push | `./.githooks/` | Runs test_methodology.py --quick before push |

### 🧠 The Memory (Claude writes, Claude reads)

| File | Goes to | Purpose |
|------|---------|---------|
| STATE.md | `./STATE.md` | Session memory. Blockers, current position. Survives /clear. |
| learnings.md | `./learnings.md` | Project patterns, decisions, common mistakes. Max 50 lines. |
| stats.json | `./.claude/stats.json` | Persistent session stats, streaks, badges, scores. Updated by /wrap. |
| universal-claude-md-template.md | `~/.claude/CLAUDE.md` | One-time setup. Cross-project patterns. Max 30 lines. |

### 📝 The Workflow (task tracking)

| File | Goes to | Purpose |
|------|---------|---------|
| todo.md | `./tasks/todo.md` | Active tasks with numbered steps, version tags, timestamps. Last 3 done features. |
| archive.md | `./tasks/archive.md` | Full step-by-step detail for all completed features. |
| ROADMAP.md | `./ROADMAP.md` | Forward-looking: Up Next, Ideas, Parked. Plus Complete section (one-line summaries). |
| _TEMPLATE.md | `./directives/` | Template for new SOPs |

### 📐 The Directives (SOPs)

| File | Goes to | Purpose |
|------|---------|---------|
| planning-rules.md | `./directives/` | Contracts, dependencies, scale-aware planning rules |
| building-rules.md | `./directives/` | Branch discipline, code hygiene, file ownership, DAG push |
| delivery-rules.md | `./directives/` | Retro discipline, guardrails, performance budgets |
| context-management.md | `./directives/` | Post-compaction protocol, solo/parallel/formal mode switching |
| self-annealing.md | `./directives/` | Failure response, learnings curation, degradation handling |
| framework-evolution.md | `./directives/` | Track native Claude Code features, absorption decisions |
| adversarial-review/ | `./directives/` | Multi-agent scored review workflow |
| documentation-governance.md | `./directives/` | Governed doc registry, front-matter format, staleness rules |
| claim-auditing.md | `./directives/` | When/how to audit claims, pre-commit integration |
| starter-kit-sync.md | `./directives/` | How to sync DOE improvements back to the starter kit repo |

### 🤖 The Agents (custom agents for adversarial review)

| File | Goes to | Purpose |
|------|---------|---------|
| Finder.md | `./.claude/agents/` | Identifies issues (read-only) |
| Adversarial.md | `./.claude/agents/` | Filters false positives (read-only) |
| Referee.md | `./.claude/agents/` | Final arbiter (read-only) |
| ReadOnly.md | `./.claude/agents/` | General-purpose read-only agent |

### 🔍 The Execution Scripts

| File | Goes to | Purpose |
|------|---------|---------|
| dispatch_dag.py | `./execution/` | DAG executor for parallel step dispatch |
| test_methodology.py | `./execution/` | Structural methodology checks (17 scenarios) |
| audit_claims.py | `./execution/` | Automated false-positive detection. Extensible with project-specific checks via `@register()` decorator. |
| wrap_stats.py | `./execution/` | Deterministic session scoring. Gathers git metrics, computes streak/multiplier/score/badges, updates stats.json, outputs JSON for `/wrap` to render. |

### ⚡ The Commands (global — install once, available in every project)

All slash commands install to `~/.claude/commands/` so they work across every DOE project. They reference relative paths (`STATE.md`, `tasks/todo.md`, etc.) so they're project-agnostic.

| Command | Purpose |
|---------|---------|
| `/stand-up` | Dual-mode: kick-off (no session) or daily status (mid-session) |
| `/crack-on` | Pick up next step immediately — commit, push, stop, report |
| `/wrap` | End-of-session routine: stats, badges, themed summary |
| `/pitch` | Generate 3-5 product ideas with structured pitches |
| `/roast` | Roast the codebase — specific, brutal, funny |
| `/audit` | Full claim audit — all checks, detailed explanations |
| `/sitrep` | Mid-session situation report with progress, commits, elapsed time |
| `/eod` | End-of-day report aggregating all sessions, commits, features, and position |
| `/agent-status` | Multi-agent dashboard for wave status, terminal liveness, task progress, merge order |
| `/sync-doe` | Sync DOE improvements back to the starter kit repo |

### 🔀 Multi-Agent Coordination (global — install once, available in every project)

Multi-agent files install to machine-level locations via `setup.sh`. They use `Path.cwd()` so they work from any project directory.

| File | Goes to | Purpose |
|------|---------|---------|
| multi_agent.py | `~/.claude/scripts/` | Wave management, task claiming, session registry, heartbeats, merge protocol, cost tracking. All state in `.tmp/waves/`. Accepts `--project-root DIR` override. |
| heartbeat.py | `~/.claude/hooks/` | PostToolUse: updates session heartbeat every 30s during active waves |
| context_monitor.py | `~/.claude/hooks/` | PostToolUse: warns at 60% context usage, stops at 80% for graceful handoff |

## How they feed into each other

```
SESSION START
│
├─→ CLAUDE.md (auto-loaded — 9 rules + guardrails + break glass)
├─→ ~/.claude/CLAUDE.md (auto-loaded — universal learnings)
│
├─→ Rule #1 says: check todo.md + STATE.md
│   ├─→ tasks/todo.md → shows incomplete steps with version tags
│   └─→ STATE.md → shows current position and blockers
│
├─→ Progressive Disclosure says: check learnings + directives
│   ├─→ learnings.md → project patterns + decisions
│   └─→ directives/ → SOPs if a trigger matches
│
DURING WORK
│
├─→ .claude/settings.json → fires hooks before actions
│   ├─→ protect_directives.py → blocks edits to existing SOPs
│   ├─→ block_secrets_in_code.py → blocks API keys outside .env
│   └─→ block_dangerous_commands.py → blocks force-push, rm -rf, etc.
├─→ ~/.claude/settings.json → fires PostToolUse hooks (merged by setup.sh)
│   ├─→ heartbeat.py → updates session heartbeat during waves
│   └─→ context_monitor.py → warns when context is running low
├─→ .githooks/pre-commit → runs fast claim audit before every commit
│
├─→ execution/ → Claude runs scripts instead of inline code
│   ├─→ dispatch_dag.py → DAG executor for parallel step dispatch
│   ├─→ test_methodology.py → structural methodology checks
│   ├─→ audit_claims.py → automated false-positive detection
│   └─→ wrap_stats.py → deterministic session scoring for /wrap
├─→ ~/.claude/scripts/multi_agent.py → wave coordination for parallel sessions
├─→ .claude/plans/ → Claude reads feature designs (version map per step)
├─→ .tmp/ → scratch space for intermediate files
│
├─→ Rule #8: before every commit, check if STATE.md or learnings.md need updating
├─→ Rule #9: pitch spontaneously if a genuine improvement is spotted
│
PER STEP COMPLETION
│
├─→ Mark step complete with timestamp in todo.md
├─→ Bump version, update changelog, commit + push
│
FEATURE COMPLETION (retro)
│
├─→ Update version references
├─→ Update changelog (final entry)
├─→ Update roadmap status tags (IN PROGRESS → COMPLETE)
├─→ Update feature heading (vX.Y.x → vX.Y.N)
├─→ Run retro — log learnings
├─→ Move feature to Done (oldest rolls to archive.md)
├─→ Update ROADMAP.md Complete section
├─→ Git commit + push
│
SESSION END (/wrap)
│
├─→ STATE.md updated with position
├─→ tasks/todo.md updated with timestamps
├─→ learnings.md or ~/.claude/CLAUDE.md updated if anything was learned
├─→ .claude/stats.json updated with session metrics
├─→ Git commit + push
└─→ Themed session summary printed (score, badges, leaderboard)
```

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
│   ├── planning-rules.md
│   ├── building-rules.md
│   ├── delivery-rules.md
│   ├── context-management.md
│   ├── self-annealing.md
│   ├── framework-evolution.md
│   ├── adversarial-review/
│   ├── documentation-governance.md
│   ├── claim-auditing.md
│   └── starter-kit-sync.md
├── execution/
│   ├── dispatch_dag.py
│   ├── test_methodology.py
│   ├── audit_claims.py
│   └── wrap_stats.py
├── .claude/
│   ├── settings.json
│   ├── stats.json
│   ├── plans/
│   ├── hooks/
│   │   ├── protect_directives.py
│   │   ├── block_secrets_in_code.py
│   │   └── block_dangerous_commands.py
│   ├── agents/               ← custom agents for adversarial review
│   │   ├── Finder.md         ← Identifies issues (read-only)
│   │   ├── Adversarial.md    ← Filters false positives (read-only)
│   │   ├── Referee.md        ← Final arbiter (read-only)
│   │   └── ReadOnly.md       ← General-purpose read-only agent
│   └── claude-chat-sync-prompt.md
├── .githooks/
│   ├── commit-msg
│   ├── pre-commit
│   └── pre-push
├── .tmp/
└── .env (git-ignored)

MACHINE (lives on your computer, applies to all projects)
├── ~/.claude/CLAUDE.md          ← Universal learnings
├── ~/.claude/settings.json      ← Global settings (PostToolUse hooks merged by setup.sh)
├── ~/.claude/commands/          ← Slash commands
│   ├── stand-up.md
│   ├── crack-on.md
│   ├── wrap.md
│   ├── sitrep.md
│   ├── eod.md
│   ├── audit.md
│   ├── pitch.md
│   ├── roast.md
│   ├── sync-doe.md
│   └── agent-status.md
├── ~/.claude/hooks/
│   ├── heartbeat.py
│   └── context_monitor.py
└── ~/.claude/scripts/
    └── multi_agent.py
```
