# DOE Claude Code Starter Kit

A structured framework for AI-assisted development using Claude Code. **Directive → Orchestration → Execution.**

## What This Is

A template repository containing everything you need to run Claude Code with guardrails, session memory, gamified workflows, and documentation governance. Drop these files into any new project and Claude Code knows how to behave.

## Quick Start

1. Clone this repo or copy files into your project
2. Run `./setup.sh` (installs commands, activates hooks, writes version receipt)
3. Start Claude Code and type `/stand-up`

<details>
<summary>Manual setup (if you prefer not to use the script)</summary>

1. Copy `global-commands/*.md` (except README.md) to `~/.claude/commands/`
2. Copy `universal-claude-md-template.md` to `~/.claude/CLAUDE.md` (if you don't have one)
3. Run `git config core.hooksPath .githooks` to activate hooks
4. Start Claude Code — it reads CLAUDE.md automatically

</details>

## What's Included

**Framework (39 files)**

- **CLAUDE.md** — 9 operating rules, progressive disclosure triggers, guardrails
- **STATE.md** — Session memory (blockers, current position)
- **Directives** — SOPs for documentation governance, claim auditing, starter kit sync
- **Audit system** — Automated false-positive detection with pre-commit hook
- **13 slash commands** — session lifecycle, quality checks, utilities, and infrastructure (see below)
- **Session timer** — `/stand-up` (in kick-off mode) and `/crack-on` start a clock, `/sitrep` and `/wrap` report elapsed time
- **Gamification** — Session scoring, badges, streaks, leaderboard, themed wrap-up cards
- **Git hooks** — Pre-commit claim audit, commit message cleanup
- **Guardrail hooks** — Block secrets, protect directives, prevent dangerous commands

**Guides**

- **CUSTOMIZATION.md** — What to keep, what to customize, what to clear for your project
- **SYSTEM-MAP.md** — Complete file-by-file documentation and relationship map

## Slash Commands

13 commands in `global-commands/`. Install with `./setup.sh` or copy manually. Run `/commands` inside Claude Code for the full reference and installation health check.

| Category | Commands | Purpose |
|----------|----------|---------|
| **Session Lifecycle** | `/stand-up`, `/crack-on`, `/sitrep`, `/wrap` | Dual-mode stand-up, track progress, end with gamified wrap-up |
| **Quality** | `/audit`, `/quick-audit`, `/vitals` | Claim auditing, workspace health checks |
| **Utility** | `/pitch`, `/roast`, `/eli5`, `/shower-thought` | Feature ideas, code roasts, ELI5, programming observations |
| **Infrastructure** | `/sync-doe`, `/commands` | Sync DOE improvements; installation health check |

**Smart filter:** The lifecycle commands check for DOE Kit sync opportunities. When comparing CLAUDE.md, they distinguish universal changes (Operating Rules, Guardrails, etc.) from project-specific additions (Directory Structure, triggers) — so you only get nudged when there's something genuinely worth syncing.

## Syncing Improvements From Projects

When you improve the DOE system during project work (new rules, better directives, new commands), sync improvements back here:

```bash
# From your project directory in Claude Code:
/add-dir ~/doe-starter-kit
# Then say:
# "Sync DOE improvements to the starter kit — read directives/starter-kit-sync.md first"
```

The sync directive handles stripping project-specific content, verifying the result, updating the changelog, bumping the version, and creating a GitHub release.

## Customizing for Your Project

See **CUSTOMIZATION.md** for the full guide. Short version:

1. Keep all operating rules and commands as-is
2. Edit CLAUDE.md triggers for your project's domain
3. Edit documentation-governance.md with your governed docs
4. Clear task/session content, keep structure
5. Add project-specific audit checks to `audit_claims.py`

## Versioning

The starter kit uses semantic versioning with GitHub releases. Every `/sync-doe` run that pushes changes will bump the version, update CHANGELOG.md, tag the commit, and create a release. See CHANGELOG.md for the full history.

## File Count

42 files across 8 directories. See SYSTEM-MAP.md for the complete map.
