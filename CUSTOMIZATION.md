# Customization Guide

How to adapt this starter kit for your project. Every file is categorized as **use as-is**, **customize**, or **start fresh**.

---

## Use As-Is (no changes needed)

These files work in any project without modification.

| File | What it does |
|------|-------------|
| `global-commands/*.md` | All 31 slash commands — `/stand-up`, `/crack-on`, `/wrap`, `/eod`, `/sitrep`, `/sync-doe`, `/commands`, `/roast`, `/pitch`, `/audit`, `/review`, `/agent-status`, `/agent-launch`, and more |
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

### tests/config.json — Quality Stack configuration

**Structure is 100% universal.** Fill in project-specific values:

- `appPrefix` — your app's HTML filename prefix (e.g. `"my-app"` for `my-app-v1.0.0.html`). If empty, auto-detected from STATE.md.
- `routes` — array of hash routes to test. Each entry: `{"hash": "dashboard", "pageId": "page-dashboard", "label": "Dashboard"}`. Leave empty for single-page apps.
- `initScript` — JS to run before each test (e.g. `"localStorage.setItem('role', 'admin');"`)
- `buildCommand` — your build script (e.g. `"python3 execution/build.py"`)
- `projectType` — framework type. Supported: `"html-app"`, `"nextjs"`, `"vite"`, `"angular"`, `"nuxt"`, `"vue"`, `"svelte"`, `"remix"`, `"astro"`, `"react-native"`, `"expo"`, `"flutter"`, `"python"`, `"go"`, `"php"`, `"ruby"`. Auto-detected from project files if empty.
- `routeMode` — `"hash"` (default, for static HTML) or `"path"` (for Next.js, Vite with path-based routing)

**First-time setup:** Run `python3 execution/run_test_suite.py --bootstrap` to install dependencies and create initial baselines. For web projects this installs Playwright + axe-core. For mobile projects (React Native, Expo, Flutter) this installs Maestro CLI. Then run `/snagging` to see automated results.

**Mobile testing with Maestro:** If `projectType` is `react-native`, `expo`, or `flutter`, the Quality Stack uses Maestro for testing instead of Playwright. Template flows are in `.maestro/` — customize `app-launch.yaml` and `navigation.yaml` for your app. Maestro uses YAML-based flows that work across all mobile frameworks.

### tests/*.spec.js — Test specs

Template specs work out-of-the-box for basic page load, accessibility, and visual regression testing. For project-specific tests (custom routes, localStorage setup, module-specific assertions), edit the specs directly. They read config from `tests/config.json`.

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
[ ] Run: python3 execution/run_test_suite.py --bootstrap (installs Quality Stack)
[ ] Edit tests/config.json — set appPrefix, routes, initScript for your project
[ ] Run /stand-up to start your first session
```

---

## Hook Templates (optional)

The `hook-templates/` directory contains Claude Code hook configurations for language-specific quality checks. These are **not active by default** — they're reference templates you can activate per-project.

| Template | Checks |
|----------|--------|
| `javascript.json` | `console.log` usage, non-strict equality (`==`/`!=`) |
| `python.json` | Bare exception catching (`except:`/`except Exception:`), `shell=True` in subprocess |
| `universal.json` | Documents the hooks already included in the kit (reference only) |

### Activating a template

1. Open the template file (e.g. `hook-templates/javascript.json`)
2. Merge its `hooks` array entries into your project's `.claude/settings.json` under `hooks.PreToolUse`
3. The hooks will fire on Write/Edit tool calls targeting matching file types

These hooks **warn but don't block** — they print to stderr so you see the warning but can proceed.

---

## Upgrading from Older Kit Versions

If your project was set up with an older version of the kit, here's what changed:

### v1.49.0 — Context-First Architecture

**CLAUDE.md is now a thin router.** The ~113-line inline rulebook is now a ~55-line trigger table that loads directives on demand. If you reference rules by number (e.g. "Rule 6"), update those references to point to the directive file instead.

**Phase-based directives replace inline rules:**
- `directives/planning-rules.md` — contracts, dependencies, scale-aware planning
- `directives/building-rules.md` — branches, code hygiene, file ownership
- `directives/delivery-rules.md` — retros, guardrails, performance budgets
- `directives/context-management.md` — post-compaction, solo/parallel/formal modes
- `directives/self-annealing.md` — failure response, learnings curation
- `directives/framework-evolution.md` — track native Claude Code features

**DAG executor for parallel dispatch.** `~/.claude/scripts/dispatch_dag.py` parses `Depends:` and `Owns:` metadata from todo.md to build a dependency graph. Use `--validate` to check your step metadata, `--graph` to see wave groupings, `--dispatch` to run parallel steps.

**Custom agent definitions.** `.claude/agents/` contains Finder, Adversarial, Referee, and ReadOnly agents for adversarial review. Edit/Write are mechanically blocked. Run with `claude --agent=Finder`.

**Pre-push methodology checks.** `.githooks/pre-push` runs `test_methodology.py --quick` before every push. Catches structural issues (broken cross-refs, invalid contracts) before they reach CI.

---

## Safe to Change

- **CLAUDE.md triggers** — add or remove triggers to match your project's workflow
- **Directive content** — edit rules to match your team's conventions
- **Contract patterns** — adjust the `Verify:` patterns in todo.md to match your tooling
- **Commands** — edit or add slash commands in `~/.claude/commands/`
- **Hooks** — add or remove hooks in `.claude/settings.json`
- **Stats categories** — customise `.claude/stats.json` tracking

## Change with Care

- **Core Behaviour rules** — these are always-on for a reason. Removing one removes a safety net.
- **Post-compaction recovery** — if you modify the recovery instructions in context-management.md, test by running `/clear` mid-feature and checking if the agent recovers correctly
- **Shared file list** — the SHARED_FILES constant in dispatch_dag.py defines which files are off-limits to parallel agents. Adding files to this list is safe; removing files risks merge conflicts.

## Do Not Change

- **Hook enforcement model** — the three-hook system (protect directives, block secrets, block dangerous commands) is the last line of defence against agent misbehaviour
- **Contract requirement** — every step needs at least one `[auto]` criterion. This is the only thing that makes autonomous building safe.

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
