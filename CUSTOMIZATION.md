# Customization Guide

How to adapt this starter kit for your project. Every file is categorized as **use as-is**, **customize**, or **start fresh**.

---

## Use As-Is (no changes needed)

These files work in any project without modification.

| File | What it does |
|------|-------------|
| `global-commands/*.md` | All 13 slash commands — `/stand-up`, `/crack-on`, `/wrap`, `/sitrep`, `/vitals`, `/sync-doe`, `/commands`, `/roast`, `/eli5`, `/pitch`, `/shower-thought`, `/audit`, `/quick-audit` |
| `global-commands/README.md` | Documents all slash commands |
| `directives/_TEMPLATE.md` | Template for creating new SOP directives |
| `directives/starter-kit-sync.md` | How to sync improvements back to this repo |
| `.claude/hooks/*.py` | Guardrail hooks — block secrets, protect directives, block dangerous commands |
| `.claude/plans/gamified-wrap.md` | Design doc for the gamification system |
| `.githooks/commit-msg` | Strips AI co-author trailers from commits |
| `.githooks/pre-commit` | Runs pre-commit checks |
| `universal-claude-md-template.md` | Template for `~/.claude/CLAUDE.md` (global learnings) |
| `.gitignore` | Standard ignores for DOE projects |

### Global commands install (one-time)

```bash
mkdir -p ~/.claude/commands
cp global-commands/*.md ~/.claude/commands/
# Don't copy README.md — it stays in the repo for reference
```

### Activate git hooks

```bash
git config core.hooksPath .githooks
```

---

## Customize (edit for your project)

These files have universal structure but need project-specific content.

### CLAUDE.md — Master rules

**~90% universal.** Keep all sections — architecture, operating rules, guardrails, code hygiene, break glass, progressive disclosure. Only change:

- **Directory structure** — add any project-specific files/folders
- **Progressive Disclosure triggers** — replace example triggers with your own. Format: `- [situation] → read [directive or file]`

### directives/documentation-governance.md

**~80% universal.** The governance process works anywhere. Replace the "Governed Documents" registry with your own docs that need front-matter tracking.

### directives/claim-auditing.md

**~70% universal.** The audit concept is generic. Update the check categories if your project has different document types.

### execution/audit_claims.py

**~60% universal.** The framework (front-matter checks, task format checks, staleness detection) works in any project. The extension point for project-specific checks is clearly marked:

```python
# Add project-specific checks below using @register("yourproject", ...)
```

Keep universal checks (`@register("universal")`), add your own project checks.

### tasks/todo.md

**Structure is 100% universal.** The format rules in the HTML comment define versioning, step format, completion timestamps, and retro process. Clear the task content and start fresh.

### ROADMAP.md

Replace entirely with your project's roadmap. Keep the format pattern (phases, status tags) if useful.

### SYSTEM-MAP.md

Replace the content but keep the concept — a single doc that maps every file, its purpose, and how files relate. Invaluable for Claude Code context loading.

---

## Start Fresh (clear content, keep structure)

| File | Action |
|------|--------|
| `STATE.md` | Clear all section content. Keep headings. |
| `learnings.md` | Clear entries. Keep section headings and front-matter. |
| `tasks/todo.md` | Clear tasks. Keep format rules comment. |
| `tasks/archive.md` | Clear everything below the heading. |
| `.claude/stats.json` | Already zeroed in the template. |

---

## Bootstrap Checklist

```
[ ] Clone/copy starter kit into your project
[ ] Copy global-commands/*.md to ~/.claude/commands/ (one-time)
[ ] Run: git config core.hooksPath .githooks
[ ] Edit CLAUDE.md — update directory structure, add your triggers
[ ] Edit directives/documentation-governance.md — list your governed docs
[ ] Clear STATE.md, learnings.md, tasks/todo.md, tasks/archive.md content
[ ] If using audit_claims.py, add project-specific checks with @register("yourproject")
[ ] Copy universal-claude-md-template.md to ~/.claude/CLAUDE.md (if you don't have one)
[ ] Run /stand-up to start your first session
```

---

## What NOT to put in the starter kit

When syncing improvements back (see `directives/starter-kit-sync.md`), never sync:

- Project-specific data files, API scripts, or import pipelines
- Project-specific directives (legal frameworks, domain governance)
- Task content (todo items, archive history)
- Session data (STATE.md content, stats.json scores)
- Feature plans specific to one project
- Project-specific audit checks
- .env files or credentials
