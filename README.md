# DOE Claude Code Starter Kit

A structured framework for AI-assisted development using Claude Code. **Directive → Orchestration → Execution.**

## What This Is

A template repository containing everything you need to run Claude Code with guardrails, session memory, gamified workflows, and documentation governance. Drop these files into any new project and Claude Code knows how to behave.

## Quick Start

1. Clone this repo or copy files into your project
2. Copy `global-commands/*.md` to `~/.claude/commands/` (one-time machine setup)
3. Copy `universal-claude-md-template.md` to `~/.claude/CLAUDE.md` (if you don't have one)
4. Run `git config core.hooksPath .githooks` to activate hooks
5. Start Claude Code — it reads CLAUDE.md automatically
6. Type `/stand-up` to begin your first session

## What's Included

**Framework (39 files)**

- **CLAUDE.md** — 9 operating rules, progressive disclosure triggers, guardrails
- **STATE.md** — Session memory (blockers, current position)
- **Directives** — SOPs for documentation governance, claim auditing, starter kit sync
- **Audit system** — Automated false-positive detection with pre-commit hook
- **11 slash commands** — `/stand-up`, `/crack-on`, `/wrap` (gamified), `/sitrep`, `/sync-doe`, `/pitch`, `/audit`, `/roast`, `/eli5`, `/quick-audit`, `/shower-thought`
- **Session timer** — `/stand-up` and `/crack-on` start a clock, `/sitrep` and `/wrap` report elapsed time
- **Gamification** — Session scoring, badges, streaks, leaderboard, themed wrap-up cards
- **Git hooks** — Pre-commit claim audit, commit message cleanup
- **Guardrail hooks** — Block secrets, protect directives, prevent dangerous commands

**Guides**

- **CUSTOMIZATION.md** — What to keep, what to customize, what to clear for your project
- **SYSTEM-MAP.md** — Complete file-by-file documentation and relationship map

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

41 files across 8 directories. See SYSTEM-MAP.md for the complete map.
