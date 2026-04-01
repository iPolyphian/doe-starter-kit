# Changelog

All notable changes to the DOE Claude Code Starter Kit.

Format: `## [vX.Y.Z] — YYYY-MM-DD` with sections for Added, Changed, Fixed, Removed.
Versioning: patch for small fixes, minor for new features/commands/directives, major for breaking changes to CLAUDE.md rules or directory structure.

---

## v1.49.1 (2026-04-01)

### Added
- **todo.md structural linter** (`execution/lint_todo.py`) — enforces contract existence on every step, retro as last step, [APP] features require [manual] criteria
- **Quality gate runner** (`execution/quality_gate.py`) — wrapper for mid-feature checkpoints (`--checkpoint`) and pre-retro gates (`--pre-retro`), writes markers to `.tmp/`
- **Invariant bootstrap** (`execution/bootstrap_invariants.py`) — scans completed contracts and promotes lasting patterns to `tests/invariants.txt`
- **Invariants template** (`tests/invariants.txt`) — empty file with format docs, ready for project-specific invariants
- **5 new pre-commit checks** in `.githooks/pre-commit`:
  - Sign-off enforcement — blocks `[ ] [manual]` in `## Done` (`SKIP_SIGNOFF_CHECK=1`)
  - Structural lint — calls `lint_todo.py` when `todo.md` is staged (`SKIP_TODO_LINT=1`)
  - Quality gate checkpoint — blocks after 4+ steps without running gate (`SKIP_QUALITY_GATE=1`)
  - Pre-retro gate — blocks retro commit without methodology pass (`SKIP_RETRO_GATE=1`)

## v1.49.0 (2026-04-01)

### Added
- **Phase-based directives** — 6 new directives extracted from CLAUDE.md: `planning-rules.md`, `building-rules.md`, `delivery-rules.md`, `context-management.md`, `self-annealing.md`, `framework-evolution.md`
- **Adversarial review guide** (`directives/adversarial-review/README.md`) — blast radius matrix, Finder/Adversarial/Referee agent roles with scoring, invocation modes, DAG integration
- **DAG executor** (`execution/dispatch_dag.py`) — dependency graph from `Depends:`/`Owns:` metadata in todo.md. Modes: `--validate`, `--graph`, `--dispatch`, `--status`
- **Custom agent definitions** (`.claude/agents/`) — Finder, Adversarial, Referee, ReadOnly agents for adversarial review with mechanically blocked Edit/Write
- **8 new methodology scenarios** (10-17) in `audit_claims.py` and `test_methodology.py` — router coverage, rule completeness, scale consistency, DAG validation, directive schema, cross-reference consistency, agent definition integrity, plan vs actual
- **Three-Level Verification** section in `directives/testing-strategy.md` — Exists/Substantive/Wired depth levels for contract criteria
- **Pre-push methodology checks** (`.githooks/pre-push`) — runs `test_methodology.py --quick` before every push
- **Methodology Tests CI step** in `doe-ci.yml` — runs methodology checks in the DOE Gate tier
- **Upgrade guide** in `CUSTOMIZATION.md` — documents v1.49.0 CFA changes for existing users
- **Safe/Change with Care/Do Not Change** sections in `CUSTOMIZATION.md` — clear trichotomy for customisation risk

### Changed
- **CLAUDE.md** — rewritten from ~113-line monolith to ~55-line thin router. Rules replaced with one-liner pointers to phase directives. Trigger table replaces Progressive Disclosure section
- **SYSTEM-MAP.md** — updated to document CFA architecture (phase directives, agents, DAG executor, pre-push hook)
- **crack-on.md** — dependency analysis from DAG executor, session blocking for large features
- **test_methodology.py** — `--scenario` flag now accepts multiple values (`action="append"`)

## v1.48.0 (2026-03-31)

### Added
- **Agent Discipline directives** — rationalisation tables (6 domains, excuse-reality format), serial dispatch protocol (SDD workflow with decision tree), subagent status protocol (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED)
- **Adversarial review templates** (`directives/adversarial-review/`) — spec-reviewer, code-quality-reviewer, and implementer-prompt templates for two-pass confidence-scored code review
- **Data compliance directive** (`directives/data-compliance.md`) — UK GDPR, DPA 2018, PPERA guidance for personal data handling
- **Data safety directive** (`directives/data-safety.md`) — data protection, backup, and integrity rules
- **Kit write guard hook** (`.claude/hooks/guard_kit_writes.py`) — blocks direct writes to ~/doe-starter-kit, enforces /sync-doe workflow. File-based flag for bypass during sync, SKIP_KIT_GUARD=1 for kit-native work
- **DOE health checks** (`execution/test_methodology.py`) — 9 methodology scenarios including CLAUDE.md quality scoring with letter grades
- **/request-doe-feature** command — structured feature request filing for the DOE starter kit
- **Universal CI pipeline** (`.github/workflows/doe-ci.yml`) — three-tier auto-detecting CI (gates/advisory/AI review) with path filters and CI Result aggregator
- **Auto-rebase Action** (`.github/workflows/auto-rebase.yml`) — keeps open PR branches current with main

### Changed
- **9 commands updated** — crack-on, stand-up, sitrep, wrap, review, snagging, eod, hq, sync-doe. All now include PR conflict detection, branch staleness warnings, and open PR awareness
- **/review** — now supports arguments (--spec, --code, --tests, commit hash), confidence scoring (80+ threshold), bordered output with SPEC+CODE passes and verdict
- **/eod** — date argument support, Gist source fallback for past dates
- **/hq** — auto source (Gist + local fallback)
- **/sync-doe** — kit write guard flag integration
- **block_dangerous_commands.py** — added Supabase guards (DISABLE ROW LEVEL SECURITY, db reset, deleteMany, emptyBucket)
- **PR template** — CI Result replaces hardcoded ESLint/Playwright/Lighthouse checks
- **setup.sh** — enhanced for CI pipeline and org rename
- **GitHub org** — references updated from iPolyphian to Albion-Labs
- **Tutorial pages** — version badge in sidebar, PR workflow updates

## v1.47.0 (2026-03-22)

### Added
- **TDD & debugging directive** (`directives/best-practices/tdd-and-debugging.md`) — Red-Green-Refactor enforcement with 7-excuse rationalisation table, 4-phase systematic debugging protocol (Investigate, Pattern Analysis, Hypothesis Testing, Implementation). Includes "when to test" decision table by code type
- **Chrome verification directive** (`directives/chrome-verification.md`) — protocol for using Claude Code's Chrome MCP integration to auto-verify `[manual]` contract items. DOM checks, console checks, layout screenshots, with graceful degradation
- **4 CLAUDE.md triggers** — TDD enforcement on new code, systematic debugging on failures, Chrome verification in snagging, Chrome prompt in crack-on for [APP] features

### Changed
- **crack-on** — Chrome enablement prompt for [APP] features. Does not auto-enable (context cost); just asks
- **snagging** — new Chrome verification Step 5 between test generation and report. Auto-verifies DOM, console, and layout items; leaves subjective items as `[manual]`

### Fixed
- **wrap_html.py** — auto-calculate timeline durations from timestamps instead of hand-estimates. Handles midnight crossing. Falls back to session total when timestamps missing

## v1.46.0 (2026-03-21)

### Changed
- **DOE Kit sync check simplified** — stand-up, crack-on, and wrap now use version-only comparison (kit tag vs STATE.md). No more file diffs or u/c classification. Eliminates false positives from project-specific customisations
- **/sync-doe reverted to direct push** — commits directly to kit main instead of creating a sync branch + PR. The sync procedure itself is the quality gate
- **/wrap session-specific sync reminder** — at session end, checks if kit-syncable files were modified THIS session and shows a targeted reminder. Replaces the persistent outbound push detection
- **/pull-doe self-correcting** — always updates STATE.md version after sync, even on "already up to date". Prevents stale version mismatches

### Added
- **Code verification rule in manual-testing directive** — verify function names, parameter types, and valid inputs against actual code before presenting test steps. Prevents design-phase language from contracts reaching users as broken test instructions
- **Info banner in test checklist HTML** — reminds testers to verify exact function signatures against the code before testing

## v1.45.0 (2026-03-21)

### Added
- **Pre-commit innerHTML/XSS check** — warns (blocking with `SKIP_XSS_CHECK=1` bypass) when innerHTML is used without escaping in staged JS files
- **Pre-commit STATE.md staleness check** — warns when code changes are committed without updating STATE.md
- **Wrap Step 0: branch cleanup** — checks if on a feature branch with a merged PR before wrapping, offers to switch back to main
- **5 compliance triggers in CLAUDE.md** — auto-load legal/compliance docs when building: personal data features (GDPR), email/SMS (PECR), donations (PPERA), content generation (imprints), opposition research (defamation)

### Changed
- **Rule 6** rewritten for branch+PR workflow — feature branches, commit per step on branch, `gh pr create` at retro, CI must pass before merge, no direct commits to main
- **Rule 11** updated — retro step now includes PR creation with template auto-filled from contract criteria

## v1.43.0 (2026-03-19)

### Documentation
- **Testing tutorial rewrite**: 3 inline SVG diagrams (filter funnel, runs-when timeline, tool map), updated catches/misses table, expanded baselines explanation
- **Maestro getting-started section**: Full mobile testing onboarding (install, flows, template, custom flow guide, config)
- **Troubleshooting expansion**: 4 new sections (Maestro 5 scenarios, bundle size 3 scenarios, CI/GitHub Actions 4 scenarios, tests-pass-but-broken teaching)
- **README accuracy fixes**: Command count (24→29), page count (10→15), file count updated

### Fixed
- Broken directive references in getting-started, key-concepts, example-apps tutorials
- Lighthouse now included in --bootstrap dependency install
- Lighthouse error message now points to --bootstrap instead of global install

---

## [v1.42.0] — 2026-03-18

### Added
- **Multi-framework testing** — Quality Stack now supports 16 project types: static HTML, Next.js, Vite/React, Angular, Nuxt, Vue, SvelteKit, Remix, Astro, React Native, Expo, Flutter, Python, Go, PHP/Laravel, and Ruby/Rails. Auto-detects framework from project files and configures testing accordingly.
- **Maestro mobile testing** — React Native, Expo, and Flutter projects use Maestro for YAML-based UI testing. Bootstrap installs Maestro CLI automatically. Template flows in `.maestro/` (app-launch + navigation).
- **Framework-aware orchestrator** — `run_test_suite.py` reads `projectType` from `tests/config.json`, uses framework-specific build and serve commands. Adapters for all web frameworks, PHP built-in server, Rails, Go, and Python/Django.
- **Multi-language health check** — `health_check.py` scans 10+ languages with per-framework scan paths, stub patterns, TODO detection, and empty function detection. Supports `.js`, `.jsx`, `.ts`, `.tsx`, `.vue`, `.svelte`, `.astro`, `.py`, `.go`, `.php`, `.rb`, `.dart` files.
- **Path routing support** — `routeMode` field in `tests/config.json` — `"hash"` (default) or `"path"` (Next.js, Vite, SvelteKit, etc). helpers.js uses root path for path-based routing.
- **Distribution fix** — `setup.sh` copies Quality Stack execution scripts and test infrastructure to new projects. `/pull-doe` syncs Quality Stack files between kit and project.
- **Snagging auto-bootstrap** — `/snagging` automatically runs `--bootstrap` on first use instead of telling the user to do it manually.
- **Snagging copy dropdown** — Copy Results + Copy Bugs + Export section consolidated into a single dropdown menu with failure count badge.

### Changed
- **Generator multi-framework** — `generate_test_checklist.py` handles `maestro_results` with framework-specific tile labels, shows `projectType` badge in automated results header.
- **Health check per-language patterns** — TODO/FIXME detection uses `#` for Python/Ruby, `//` for JS/Go/Dart, `<!--` for Vue/Svelte/Astro templates. Empty function detection uses language-specific syntax (`def...pass` for Python, `func...{}` for Go, etc).

## [v1.41.3] — 2026-03-18

### Fixed
- **Snagging dark mode** — section header and export section had `background: white` without dark mode overrides, causing white strips in dark mode. Both now get `background: #1e293b`.

## [v1.41.2] — 2026-03-18

### Changed
- **`/report-doe-bug` enhanced issue template** — added Component field (searchable by DOE command/script), Error Output section (sanitised traceback), What Was Tried section, User's Description section, Project Type in environment table.
- **Duplicate escalation** — structured duplicate comment format with version/severity/description. Adds +1 reaction to issues for sorting by most-affected. Auto-escalates priority labels: 2+ duplicate reports → `priority:high`, 5+ → `priority:critical`.
- **Simplified project type question** — "web app or mobile app?" instead of framework-specific options. Labels: `project:web` / `project:mobile`.
- **Draft card** — now shows Component, Error Output, and What Was Tried sections in the preview.

## [v1.41.1] — 2026-03-18

### Changed
- **`/report-doe-bug` UX improvements** — bordered output cards for all phases (environment, version check, user error, duplicates, draft preview, result). Questions asked one at a time instead of batched. Added project type question (Static HTML / Next.js / React Native / Flutter / Other) with `project:` label for backlog filtering.

## [v1.41.0] — 2026-03-18

### Added
- **`/report-doe-bug` command** — triage-first bug reporter for the DOE framework. 5-phase flow: gather user description + Claude reconstruction + environment capture, check if fixed in newer version (route to `/pull-doe`), detect user error (route to tutorial docs via dynamic HTML scanning), search for duplicates (offer to comment), then sanitise and file a structured GitHub Issue with labels (`bug`, `user-reported`, version tag, severity). Falls back to local markdown if `gh` CLI is unavailable.
- **`execution/doe_bug_report.py`** — deterministic execution script supporting the bug reporter. Subcommands: `--environment` (DOE version, OS, Node, Python, shell), `--version-check` (compare to upstream releases, parse CHANGELOG), `--check-gh` (verify GitHub CLI), `--scan-tutorials` (search tutorial HTML headings via stdlib HTMLParser), `--search-duplicates` (query existing issues), `--sanitise` (strip API keys, secrets, paths, emails), `--file-issue` (create GitHub Issue with labels), `--add-comment` (add context to duplicates). All output JSON.
- **Tutorial update** — added `/report-doe-bug` entry to `commands.html` Quality section.

## [v1.40.1] — 2026-03-18

### Added
- **Universal learning** — DOE Starter Kit section in `universal-claude-md-template.md`: never commit directly to `~/doe-starter-kit` during feature work, always use `/sync-doe` for the full release pipeline.

## [v1.40.0] — 2026-03-18

### Added
- **Quality Stack** — full testing infrastructure now ships with the starter kit. Includes `run_test_suite.py` (orchestrator with server lifecycle, parallel Playwright + Lighthouse), `health_check.py` (stub/TODO/empty function detection), `verify_tests.py` (Playwright wrapper), and `playwright.config.js`.
- **Template test specs** — generic `app.spec.js`, `accessibility.spec.js`, `visual.spec.js` that auto-discover pages from `tests/config.json`. Shared `helpers.js` for config-driven app path resolution.
- **Bootstrap command** — `python3 execution/run_test_suite.py --bootstrap` installs npm deps, Playwright browser, and creates initial baselines in one step.
- **Code trace in snagging** — `/snagging` now runs code trace automatically (no more yes/no prompt). Results appear in the automated summary section via new `--code-trace` flag on `generate_test_checklist.py`.
- **Enhanced verify.py** — `--regression` and `--deposit` flags for regression suite accumulation.
- **Config-driven portability** — `tests/config.json` extended with `appPrefix`, `routes`, `initScript` fields. All scripts read project-specific values from config instead of hardcoding.

### Changed
- `generate_test_checklist.py` renders automated results section when either test suite OR code trace data is available (previously required test suite only).

## [v1.39.5] — 2026-03-17

### Fixed
- **SVG diagrams across 3 pages**: commands.html viewBox widened to 610 (fixes "weekly" text clipping). key-concepts.html and context.html SVGs changed from fixed `width`/`height` attributes to `width:100%;height:auto` so they scale responsively. Container padding reduced across all diagram containers.

## [v1.39.4] — 2026-03-17

### Fixed
- **SVG lifecycle diagram**: cropped viewBox from `0 0 720 320` to `0 0 590 254` to match actual content bounds. Eliminates ~76px dead whitespace below legend and ~130px unused right margin.

## [v1.39.3] — 2026-03-17

### Changed
- **Command card layout** (commands.html): badge + origin tag now share a row (flex-wrap), summary text forced below via `flex-basis: 100%`. Reduced card padding from 20px 24px to 18px 20px.
- **"Built-in" renamed to "Default"** across all 6 command entries, section heading, and TOC link. CSS class `.cmd-origin.builtin` renamed to `.cmd-origin.default`.
- **Origin tag styling**: now uses `display: inline-flex; align-items: center; height: 22px` for consistent vertical alignment with the command badge.
- **SVG lifecycle diagram**: reduced container padding (28px 24px → 20px 16px 12px), reduced bottom margin (40px → 24px), SVG width changed from `max-width: 100%` to `width: 100%` to fill container.
- **Annotation list specificity**: `.annotation-list` → `.content .annotation-list` to override `.content ul { padding-left: 20px }` without relying on source order.

## [v1.39.2] — 2026-03-17

### Changed
- **Command card layout** across 3 tutorial pages (commands.html, testing.html, daily-flow.html): command badge now sits above the description text instead of beside it. Cleaner layout for long command names like `/code-trace --integration`.

## [v1.39.1] — 2026-03-17

### Changed
- **testing.html**: New "The Snagging Checklist" section explaining the automated results card (4 metric tiles, status badge, dark mode toggle), baseline updates, and the new /snagging flow. Updated /snagging command card, "What Runs When" table, "Your Role" section, and signposting description.
- **troubleshooting.html**: New "Snagging v2 Issues" section with 5 scenario cards (Lighthouse errors, port conflicts, APP_PATH mismatch, visual regression diffs, dark mode toggle). TOC link and Quick Reference table updated.
- **commands.html**: /snagging entry updated to describe automated test suite integration, results card, dark mode toggle, and baseline updates.

## [v1.39.0] — 2026-03-17

### Added
- **Snagging v2: Automated test results integration** — `/snagging` now runs `execution/run_test_suite.py` (if it exists) before generating the checklist. Results rendered as an automated results card with status badge (ALL PASS / WARNINGS / FAILURES), metric tile strip (Browser Tests, Visual Regression, Accessibility, Performance), expandable detail sections (health check, route coverage), and banner divider separating auto from manual checks.
- **Dark mode toggle** on snagging checklists — moon/sun button in the top bar, preference persisted in localStorage. Light mode is always the default.
- **Concept C step stripes** — section cards now have a thin header stripe showing step pill, completion timestamp, and "N of M" position indicator. Card title is just the clean feature name.
- **`--test-results` argument** for `generate_test_checklist.py` — accepts path to orchestrator JSON output. When omitted, generator produces the same output as before (manual checks only). Fully backwards-compatible.
- **Signpost banner divider** — "YOUR REVIEW — N checks below" separates automated results from manual check sections.
- **Baseline update instructions** in `/snagging` command — `--update-baselines`, `--update-visual`, `--update-lighthouse`, `--update-a11y`.

### Changed
- Snagging command restructured: new Step 2 (run test suite, portability-guarded), steps renumbered, paste-back handling documented.
- Checkbox indentation tightened — less left padding, narrower number column, smaller gaps.
- Disclosure arrows upgraded from tiny unicode triangles to proportional SVG chevrons with rotation animation.
- Heading parser now handles `[APP]`/`[INFRA]` tags without version ranges (e.g. `### Feature [INFRA]`).
- `extract_console_commands()` genericized — project-specific patterns replaced with commented examples.

## [v1.38.0] — 2026-03-17

### Added
- **New command: `/code-trace`** — AI-driven code tracing with three modes: single module (deep logic trace with BUG/WARN/INFO severity), integration (cross-module data flow), and full sweep. The probabilistic layer of the Quality Stack.
- **New tutorial page: Testing & Quality** (`docs/tutorial/testing.html`) — explains the three-layer defence (deterministic/probabilistic/empirical), what runs when, the user's role, and the signposting system.
- **New tutorial page: Troubleshooting** (`docs/tutorial/troubleshooting.html`) — every tool covered with "what you see / what it means / what to do" format. ESLint, Playwright, Lighthouse, health check, /code-trace, npm/Node, and git hook scenarios.
- **Quality sidebar section** added to all 15 tutorial pages linking to Testing & Quality and Troubleshooting.
- **ESLint + stub detection** in pre-commit hook — lints staged JS files (blocks on errors, bypassable with `SKIP_ESLINT=1`), warns on stubs (`return null`, `return []`, empty functions, "not implemented" markers). Path configurable via `JS_PATH` variable.
- **TEST HEALTH row** in `/stand-up` kick-off card — shows regression suite count and health check results at session start.
- **Health check step** in `/wrap` housekeeping — runs `health_check.py --quick` + regression suite at session end, records results in System Checks.
- `/code-trace` and `/health-check` added to commands.html Quality & Review section.
- npm/package.json setup note added to getting-started.html.
- Quality stack callout added to daily-flow.html work cycle.

## [v1.37.4] — 2026-03-16

### Fixed
- `execution/audit_claims.py`: retro steps (name starting with "Retro") now exempt from version tag check, same as `[INFRA]` steps. Prevents false WARN on `[APP]` feature retros which structurally don't get their own version bump.

## [v1.37.3] — 2026-03-16

### Added
- `.githooks/commit-msg`: changelog enforcement — versioned commits (containing `(vX.Y.Z)` tag) now require `CHANGELOG.md` to be staged. Prevents shipping versioned steps without a changelog entry. Skippable with `SKIP_CHANGELOG_CHECK=1`.

## [v1.37.1] — 2026-03-16

### Changed
- `execution/generate_test_checklist.py`: Option C header redesign — feature name as h1 with [APP] pill badge, env cards (Browser/Viewport/OS) top-right, 12px split progress bar (green pass + red fail), elapsed timer bottom-left with label, progress card with subtitle, Copy Bugs button (amber, conditional), Reset All with red styling, buttons right-aligned
- `execution/generate_test_checklist.py`: added `--verify` mode — re-checks known bugs via code trace and outputs unicode-bordered terminal summary instead of regenerating full HTML

## [v1.37.0] — 2026-03-16

### Changed
- `global-commands/stand-up.md`: DOE KIT line now shows u/c classification — `* pull (1u 2c)` where `u` = user-facing (commands, hooks, rules) and `c` = creator-facing (kit infra, tutorials, setup)
- `global-commands/crack-on.md`: same u/c classification for DOE KIT line
- `global-commands/wrap.md`: DOE Kit sync check classifies diffs as u/c, JSON schema includes `userCount`/`creatorCount` fields for HTML renderers

## [v1.36.1] — 2026-03-16

### Fixed
- `global-commands/snagging.md`: report box now uses Unicode box-drawing characters (`┌─┐`, `├─┤`, `└─┘`, `│`) instead of ASCII (`+`, `--`, `|`) for consistency with all other DOE command output
- `docs/tutorial/*.html`: fixed stale footer version stamps (v1.32.0 -> v1.36.0) across all 13 tutorial pages

### Added
- `execution/stamp_tutorial_version.py`: automation script to update tutorial footer/hero badge version strings; integrated into sync directive and `/sync-doe` command so footers are stamped before every release commit

### Changed
- `directives/starter-kit-sync.md`: Step 10 now runs `stamp_tutorial_version.py` before `git add -A`; post-sync checklist updated to reference auto-stamping
- `global-commands/sync-doe.md`: added step 11a to run `stamp_tutorial_version.py` before committing

## [v1.36.0] — 2026-03-16

### Added
- `global-commands/snagging.md`: `/snagging` command — auto-generates interactive HTML test checklists from todo.md `[manual]` contract items
- `directives/manual-testing.md`: SOP for the manual testing workflow (generation, testing, feedback loop, sign-off)
- `execution/generate_test_checklist.py`: HTML checklist generator with three-state toggles, timer, localStorage persistence, console code blocks with copy buttons, and export-to-clipboard
- `docs/tutorial/workflows.html`: "Manual Testing & Sign-off" section covering the /snagging workflow
- `docs/tutorial/commands.html`: `/snagging` command reference entry
- `CLAUDE.md`: Progressive Disclosure trigger for manual testing

### Changed
- `global-commands/wrap.md`: explicit `git push` at every commit point (housekeeping, stats, wrap data); `awaitingSignOff` now scans `## Current` for completed steps with unchecked `[manual]` items; added `checklistPath` field for linking to test checklists
- `global-commands/README.md`: added `/snagging` entry in Quality section

## [v1.35.0] — 2026-03-16

### Added
- CLAUDE.md rule 11: retro discipline with escalation triggers and quick/full format
- CLAUDE.md Self-Annealing: 100-session learnings curation protocol
- CLAUDE.md Progressive Disclosure: curation trigger (session multiple of 100)
- `crack-on.md`: curation check at session start
- `stand-up.md`: curation check at session start

## [v1.34.3] — 2026-03-16

### Added
- Dev server learning in `universal-claude-md-template.md`: new `## Dev Servers` section — kill stale instances before starting new ones to prevent on-demand compilation hangs (macOS + Windows commands)

## [v1.33.0] — 2026-03-16

### Added
- `docs/tutorial/multi-agent.html` — new Multi-Agent Workflows tutorial page covering waves, /agent-launch, /agent-status, worked example, merge process, and common pitfalls
- `docs/tutorial/faq.html` — new FAQ page with 12 Q&A pairs across 3 categories (Setup, Session, Framework problems) with cross-links to relevant pages
- Right-side Table of Contents (TOC) with scrollspy on 3 content-heavy pages: commands, daily-flow, context
- Git basics orientation expandable section in getting-started page

### Changed
- Footer version updated to v1.32.0 across all tutorial pages
- Sidebar navigation updated across all 13 pages with multi-agent and FAQ links
- Pagination chain updated: workflows → multi-agent → example-apps, tips → faq → glossary
- Post-sync checklist added to starter-kit-sync directive for footer version tracking

## [v1.32.0] — 2026-03-15

### Added
- `docs/tutorial/context.html` — new Context Management tutorial page covering compaction, danger zone, /context command, /wrap, and recovery flows
- Tab infrastructure across all tutorial pages: content tabs (card-style toggling) and environment tabs (Terminal vs VSCode toggle)
- VSCode mockup component system with editor chrome, activity bar, and panel styling
- Hooks coverage and recovery flows section in tips-and-mistakes page
- Built-in vs DOE badge distinction on commands page

### Changed
- All 10 existing tutorial pages enhanced with Terminal/VSCode environment tabs (29 mockups across 9 pages)
- Getting Started: card-tabs for setup options with GitHub clone instructions
- Workflows: card-tabs with Path A as default active tab
- Commands: sidebar navigation with Planning/Maintenance section links
- Daily Flow: box-drawing terminal mockup classes for consistent styling
- Key Concepts and First Session: glossary cross-links to glossary.html anchors
- Context page added to sidebar navigation across all pages
- `crack-on.md`, `sitrep.md`, `stand-up.md` global commands: expanded DOE Kit check path mapping documentation

## [v1.31.0] — 2026-03-13

### Added
- `docs/tutorial/` — 10 self-contained HTML tutorial pages in Mintlify-style design system: landing page, getting started, first session, key concepts, commands, daily flow, workflows, example apps, tips & mistakes, glossary
- `docs/reference/` — 33 markdown reference docs covering commands, concepts, workflows, examples, file formats, and glossary
- Tutorial features: fixed sidebar navigation, dark mode toggle, terminal mockups with macOS dots, card grids, step components, callout boxes, expandable accordions, pagination, responsive layout (375px/768px/1440px)
- README: documentation section with tutorial and reference doc descriptions

## [v1.30.1] — 2026-03-12

### Fixed
- `CLAUDE.md` Rule 1 point (3): Awaiting Sign-off move now happens immediately when last step's `[auto]` criteria pass, not at session wrap — fixes circular dependency where manual checks couldn't be presented until a ceremony that required manual checks
- `todo.md` format rules step (6): Awaiting Sign-off is now the default destination for completed features; Done section description clarified to "all contracts verified"

## [v1.30.0] — 2026-03-12

### Added
- `## Awaiting Sign-off` section in todo.md format rules — intermediate state between code-complete and fully verified
- `check_manual_signoff` audit check in `audit_claims.py` — WARNs if unchecked `[manual]` contracts found in `## Done`
- SIGN-OFF row in `stand-up.md` (both kick-off and status modes) — surfaces pending manual verification counts
- SIGN-OFF row in `sitrep.md` — same pending count between COMMITS and ELAPSED
- `awaitingSignOff` field in `wrap.md` JSON schema — collapsible grouped cards for manual test items
- `render_awaiting_signoff()` in `wrap_html.py` — collapsible `<details>/<summary>` cards with themed groups, amber styling

### Changed
- `CLAUDE.md` Rule 1 `[manual]` criteria point (3): features now move to `## Awaiting Sign-off` at completion instead of `## Done`; `## Done` requires all `[manual]` criteria `[x]`
- todo.md format rules: added conditional retro routing — features with unchecked `[manual]` go to Awaiting Sign-off, not Done

## [v1.29.0] — 2026-03-12

### Added
- Platform/model/tag tracking in `wrap_stats.py` (`--platform`, `--model`, `--tag` CLI args, `auto_classify_tag()`)
- Badge helpers and CSS in `wrap_html.py` and `eod_html.py` (platform/model/tag pills)
- Dark/light toggle with auto mode (6am-6pm) and manual override via localStorage in all three renderers
- GitHub-style streak heatmap in `build_hq.py` (52-week SVG grid, responsive full-width)
- Side-by-side platform + model stats layout in `build_hq.py`

### Changed
- `build_hq.py`: search/filters moved below Features This Week swimlane
- `build_hq.py`: model stats shown even with single model (removed 2+ threshold)

### Fixed
- `eod_html.py`: breakdown bar CSS overflow (flex-shrink + max-width + overflow:hidden)
- `.githooks/commit-msg`: cross-platform temp file approach replaces macOS-only `sed -i ''`
- `.githooks/pre-commit`: added `PYTHONIOENCODING=utf-8` for Windows cp1252 compatibility

## [v1.28.0] — 2026-03-12

### Changed
- `wrap.md`: save session JSON to `docs/wraps/` instead of copying the rendered HTML. HTML is generated on demand from JSON. Smaller commits, HQ regenerates as needed.

## [v1.27.3] — 2026-03-11

### Fixed
- `build_hq.py`: HQ "This Week" summary now shows one headline activity per project (max 3) instead of dumping multiple semicolon-separated summary fragments that got truncated.

## [v1.27.2] — 2026-03-11

### Fixed
- `build_hq.py`: HQ project cards now read version from git tags (most reliable) with fallback to session summary text. Previously only checked summaries, so projects with tags but no version in summaries showed no version.

## [v1.27.1] — 2026-03-11

### Added
- `wrap_stats.py`: automatic git version tagging at wrap time. Reads `**Current app version:**` from STATE.md and creates the git tag if it doesn't exist. Ensures HQ dashboard always shows the project version.

## [v1.27.0] — 2026-03-10

### Added
- `/hq` command: unified project dashboard with portfolio view and per-project drill-down (SPA hash routing). Replaces `/archive-global`.
- `build_hq.py` global script: generates the HQ dashboard HTML with light/dark theme, search, feature swimlanes, timeline scrubber.

### Changed
- `/wrap` registry snippet now preserves existing fields (e.g. `displayName`) when re-registering a project.
- Version detection across `/commands`, `/sync-doe`, `/pull-doe` now reads from `git describe --tags` in `~/doe-starter-kit` instead of the stale `~/.claude/.doe-kit-version` file.
- `setup.sh` no longer writes `~/.claude/.doe-kit-version` — the git tag is the single source of truth.

### Fixed
- `.githooks/commit-msg`: case-insensitive regex now catches `Co-Authored-By` (previously only matched `Co-authored-by`).

### Removed
- `/archive-global` command (superseded by `/hq`).
- `~/.claude/.doe-kit-version` file dependency (replaced by git tags).

## [v1.26.0] — 2026-03-10

### Added
- `/archive-global` command: global portfolio dashboard aggregating all registered projects. Shows time allocation, project health cards (Active/Idle/Dormant), cross-project timeline. Reads `~/.claude/project-registry.json`.
- Two universal triggers in CLAUDE.md Progressive Disclosure: multi-agent coordination and `/scope` feature scoping.

### Changed
- `/wrap` now auto-registers the project in `~/.claude/project-registry.json` after committing stats, enabling the global archive to discover projects automatically.

## [v1.25.0] — 2026-03-10

### Added
- `/scope` command: conversational feature scoping through 3 phases (Explore, Define, Bound). Produces structured brief in `.claude/plans/` and updates ROADMAP.md with SCOPED status tag.
- New "Product" section in README grouping `/scope` and `/pitch`.

### Changed
- `/stand-up` DOE Kit indicator: directional sync labels (`* push`, `* pull`, `* push+pull`) replace generic `*`. Users now know which direction needs syncing.
- `/stand-up` kick-off: 100-session milestone celebration card for lifetime session milestones.

## [v1.24.5] — 2026-03-09

### Added
- `wrap_html.py`: `--theme light|dark` CLI flag for light/dark mode toggle
- `wrap_html.py`: `body.light` CSS variables with warm off-white palette (`#f0efe9` bg, `#f8f7f3` surface) for daytime readability
- `wrap_html.py`: body class toggle wiring for theme selection

## [v1.24.4] — 2026-03-09

### Changed
- `/stand-up` SINCE LAST MILESTONE: groups related commits by feature/theme with summaries instead of listing individually (max 6 groups)
- `/wrap` section 3e: auto-detects light/dark theme based on time of day (6am-6pm = light, otherwise dark)

## [v1.24.3] — 2026-03-07

### Added
- `/stand-up` BLOCKERS row: reads STATE.md `## Blockers & Edge Cases` and surfaces them with `!!` prefix in both kick-off and status mode cards. Positioned between CONTRACT and DOE KIT. Omitted when no blockers exist.

## [v1.24.2] — 2026-03-06

### Changed
- `/sync-doe` and `/pull-doe` now update STATE.md's DOE kit version as a final step, preventing false "inbound update pending" signals in `/stand-up`

## [v1.24.1] — 2026-03-06

### Changed
- EOD report stats bar format: "Friday 6th March | HH:MM | X Day streak" (human-readable date with ordinal suffix, current time, streak count)

## [v1.24.0] — 2026-03-06

Wrap and EOD report layout improvements — session stats promoted to below title card, report type label divider added above title card.

### Added
- Report label divider above title card in both wrap and eod HTML reports ("Session Report" / "End of Day Report")
- Session stats bar below title card (session number, streak, lifetime commits) — moved from footer

### Changed
- `wrap_html.py`: title card no longer includes "Session N —" prefix (session number now in stats bar)
- `eod_html.py`: title card no longer includes date (date now in stats bar)
- Footer simplified to DOE attribution only in both reports
- `wrap_stats.py`: session stats template includes `summary` field

## [v1.23.0] — 2026-03-06

Stand-up gains pipeline sync detection. Sync directive upgraded to 3-layer diffing with README consistency checks.

### Added
- `/stand-up` kick-off: PIPELINE row comparing ROADMAP.md Up Next count vs todo.md Queue count — nudges user to scope and promote features
- `sync-doe` directive: 3-layer comparison (DOE kit, installed global, local project) catches edits at any layer
- `sync-doe` directive: README consistency verification step ensures every command has a README entry

### Changed
- `/stand-up`: reads ROADMAP.md in kick-off mode
- `/agent-status`: card header renamed from "AGENT STATUS" to "HQ"
- `global-commands/README.md`: `/stand-up` description updated to mention pipeline sync

## [v1.22.6] — 2026-03-06

Fix summary-to-breakdown spacing in wrap and eod HTML reports.

### Fixed
- `.summary-lead` CSS: replaced `margin-bottom` with `padding-bottom` to prevent margin collapsing between summary paragraph and first breakdown heading
- `.breakdown-group` CSS: added `margin-top: 0.6rem` for consistent spacing between groups

## [v1.22.5] — 2026-03-06

Updated command reference (global-commands/README.md) to reflect recent changes.

### Added
- `/agent-verify` entry -- contract verification command (solo + wave mode)
- `/test-suite` entry -- persistent test suite runner

### Changed
- `/wrap` description updated to reflect HTML output (wrap_html.py, commit groups, decision/learning pills, timeline percentages, vibe)
- `/eod` description updated to reflect HTML output (eod_html.py, daily timeline, commit breakdown bars, 9-metric grid)
- `/audit` note added about merged commands (/quick-audit, /vitals, /doe-health)
- `/agent-status` description updated with full mode list (--plan, --preview, --launch, --merge, --reclaim, --abort, --watch)
- `/commands` date updated

---

## [v1.21.1] — 2026-03-06

### /wrap overhaul
- Summary section: plain English with vibe merged in (no separate section)
- Timeline: legend for dot colours, % per entry, total session time
- Commits: grouped by feature with headers and counts
- Decisions: Problem/Solution format with coloured pill labels
- Learnings: Discovery/Change format with coloured pill labels
- Today's Sessions: new section showing all sessions with duration and summary
- Section reorder: Timeline → Metrics → Commits → Decisions → Checks → Sessions → Next Up
- Removed Journey section, narrative guidance tightened to 2-3 sentences
- Session summary stored in stats.json for cross-session recall

---

## [v1.21.0] — 2026-03-06

Slash command audit: 29 to 24 commands. Consolidated overlapping commands, removed low-value ones.

### Changed
- **`/hq` renamed to `/agent-status`** — clearer name for the multi-agent dashboard command. File renamed from `hq.md` to `agent-status.md`. All internal references updated.
- **`/audit` now comprehensive** — merged `/quick-audit`, `/vitals`, and `/doe-health` into a single `/audit` command covering claims, workspace health, and DOE framework integrity in one bordered output.
- Updated `/commands` reference card, README, SYSTEM-MAP, CUSTOMIZATION, and global-commands/README to reflect new command set.

### Removed
- **`/quick-audit`** — absorbed into `/audit`
- **`/vitals`** — absorbed into `/audit`
- **`/doe-health`** — absorbed into `/audit`
- **`/shower-thought`** — low usage, removed
- **`/eli5`** — low usage, removed

---

## [v1.20.4] — 2026-03-06

Manual verification approach: batch at feature end, not per-step.

### Changed
- **Solo verification discipline** (CLAUDE.md Rule 1) — `[auto]` criteria gate each step autonomously. `[manual]` criteria batched and presented at feature completion as a single test checklist. Mid-feature visual checkpoint for 5+ step features. Prefer converting `[manual]` to `[auto]` where possible.
- **todo.md format rules** — `[manual]` criteria description updated to match: batch at feature end, prefer auto conversion.

## [v1.20.3] — 2026-03-06

Visual docs must be saved to project `docs/` directory, not ephemeral global paths.

### Added
- **Code Hygiene rule** — visual docs (brainstorms, diagrams, guides) go to `docs/` in the project root, never to `~/.agent/diagrams/` or other global paths
- **Directory Structure** — `docs/` entry added for generated visual documents

## [v1.20.2] — 2026-03-06

Retro rule improvement: completed features now get full roadmap cleanup, not just a status tag update.

### Changed
- **Retro step 3** — expanded from "update status tags" to also move feature from Up Next to Complete and refresh Suggested Next if it references the completed feature. Prevents stale roadmap entries accumulating.

## [v1.20.1] — 2026-03-06

Post-wave housekeeping fixes: audit regex, wave cleanup, and governed doc staleness surfacing.

### Fixed
- **Audit version tag regex** — now accepts both `→` (unicode) and `->` (ASCII), fixing false WARNs on wave-generated todo.md steps
- **Audit name extraction** — split pattern updated to handle `->` arrow format in task names
- **Wave file cleanup** — `--merge` now deletes completed wave JSON and log files instead of leaving them on disk (caused stale `active_wave` audit warnings)

### Added
- **Post-merge governed doc staleness check** — after merge completes, scans front-matter `Applies to` versions and warns if any governed doc is >1 minor version behind current app version
- **Updated post-merge message** — now explicitly mentions governed doc updates in the housekeeping checklist

## [v1.20.0] — 2026-03-05

Wave-1 post-mortem: fixed all multi-agent coordination bugs discovered during first parallel wave run. Hardened path resolution, log safety, todo update reliability, and added new monitoring tools.

### Added
- **`global-scripts/doe_utils.py`** — shared utility for worktree detection (`resolve_project_root()`), used by multi_agent.py, heartbeat.py, context_monitor.py
- **`--watch` flag** — auto-refreshing dashboard every 30 seconds, exits when all tasks complete
- **Wave agent guardrail** in CLAUDE.md — agents must not edit shared files on master during active waves
- **Post-merge auto-rebuild** — runs `buildCommand` from `tests/config.json` after each merge step

### Changed
- **CLAUDE.md Rule 1** — clearer solo vs wave verification distinction (wave mode defers to `--complete` and `--merge`)
- **`_update_todo_after_merge`** — searches entire todo.md file (not just `## Current`) and runs incrementally after each merge instead of once at the end
- **Stale threshold** — bumped from 120s to 300s to avoid false positives during long builds

### Fixed
- **Worktree path resolution** — `Path.cwd()` broke in worktrees; all scripts now use `doe_utils.resolve_project_root()` to find main repo root
- **Log race condition** — log file initialization moved inside `atomic_modify` lock to prevent two processes from clobbering each other
- **`--complete` verification** — passes worktree path to verify.py so file checks resolve correctly
- **`_analyze_wave`** — no longer rejects `manual:` prefixed criteria as invalid auto patterns

---

## [v1.19.0] — 2026-03-05

Combined `/agent-launch` and `/agent-start` into a single dual-mode command.

### Changed
- **`/agent-launch`** — now auto-detects mode: Launch (no active wave) creates wave and auto-claims first task; Join (active wave) claims next unclaimed task. Replaces the two-command workflow with one command for all terminals.

### Removed
- **`/agent-start`** — absorbed into `/agent-launch` Join mode. No longer needed as a separate command.

---

## [v1.18.4] — 2026-03-05

Pre-commit hook now gates on contract verification before allowing commits.

### Added
- **`.githooks/pre-commit`** — contract verification gate calls `execution/check_contract.py` before commit; skip with `SKIP_CONTRACT_CHECK=1`

---

## [v1.18.2] — 2026-03-05

Contract auto-generation in `/agent-launch`.

### Changed
- **`/agent-launch`** — added Step 0: scans Queue and Current for missing contracts, auto-generates from plan files, presents for user approval before wave creation
- **`global-commands/README.md`** — updated `/agent-launch` description

---

## [v1.17.3] — 2026-03-05

Complete verification coverage — solo, wave, and ad-hoc work.

### Changed
- **CLAUDE.md Rule 1** — added solo verification discipline (contract pre-flight + post-completion gate) and ad-hoc work verification (state criteria in conversation, verify before committing)

---

## [v1.17.2] — 2026-03-05

Pre-commit contract verification hook — hard gate for solo mode.

### Added
- **`execution/check_contract.py`** — parses todo.md, finds current step's contract, blocks commit if any criteria unchecked
- **`global-hooks/pre-commit`** — contract verification section appended (gated by `SKIP_CONTRACT_CHECK=1` env var)

---

## [v1.17.1] — 2026-03-05

Solo verification discipline — contract enforcement for all modes, not just waves.

### Changed
- **`/crack-on`** — contract pre-flight (validates Verify: patterns before starting) + post-completion verification (runs all criteria before marking steps done)
- **`/stand-up`** — kick-off mode surfaces contract health for next step (informational CONTRACT line in card)
- **Commands README** — updated /stand-up and /crack-on descriptions, added contract enforcement section

---

## [v1.17.0] — 2026-03-05

Mandatory task contracts with executable verification patterns.

### Changed
- **todo.md format rules** — contracts now mandatory for every step with `[auto]`/`[manual]` tags and 4 executable `Verify:` patterns (`run:`, `file: exists`, `file: contains`, `html: has`)
- **CLAUDE.md Rule 1** — appended contract requirement (tasks without testable contracts cannot be started)
- **CLAUDE.md Self-Annealing** — added test failure logging guidance (auto-test fails, regressions, bad contracts)

### Added
- **CLAUDE.md trigger** — testing setup maps to `directives/testing-strategy.md`

---

## [v1.16.0] — 2026-03-05

Restructured ROADMAP.md with new sections for better project planning visibility.

### Added
- **ROADMAP.md** — 4 new sections: Suggested Next (Claude's strategic recommendation), Must Plan (important items needing scoping), Claude Suggested Ideas (AI-pitched additions), plus HTML comment block with section rules for Claude
- **ROADMAP.md** — every entry now requires a `*(pitched/added DD/MM/YY)*` timestamp

### Changed
- **CLAUDE.md Rule 9** — pitch routing now specifies Ideas (casual) vs Must Plan (important) sections
- **ROADMAP.md** — description updated from "living notepad" to "sections flow from most concrete to most speculative"

---

## [v1.15.1] — 2026-03-05

Remove Last 10 Days leaderboard from /wrap.

### Removed
- **`/wrap` Part 8 (Last 10 Days Leaderboard)** -- entire section, template, rules, and `result.leaderboard` reference
- Leaderboard mention from README.md /wrap description

---

## [v1.15.0] — 2026-03-05

Card format cleanup and smart CLAUDE.md diffing across all DOE Kit-aware commands.

### Changed
- **`/stand-up` kick-off card** — removed BLOCKERS and LEARNINGS rows, PROJECT right-aligned on header row, added last-session SUMMARY above PLAN
- **`/stand-up` status card** — removed BLOCKERS and DECISIONS rows
- **`/eod` card** — removed Blockers from POSITION AT EOD section
- **DOE Kit sync check** (`/stand-up`, `/crack-on`, `/sitrep`, `/wrap`) — smart CLAUDE.md diff: only flags universal section changes (Operating Rules, Guardrails, Code Hygiene, Self-Annealing), ignores project-specific sections (Directory Structure, triggers)
- **`/crack-on`** — genericized project-specific example in header rule
- **README.md** — updated `/stand-up` description and DOE Kit awareness paragraph

---

## [v1.14.6] — 2026-03-05

New `/agent-start` command and simplified `/agent-launch` instructions.

### Added
- **`/agent-start` command** — claims a wave task, cd's into the worktree, shows the assignment, and starts working. Replaces manual `python3 multi_agent.py --claim` + `cd` workflow.

### Changed
- **`/agent-launch` instructions** — "go" output now shows `/agent-start` instead of manual python3 commands. Cleaner onboarding for new terminals.

---

## [v1.14.5] — 2026-03-05

Docs update: command count and wrap system checks heading.

### Fixed
- **Command count** — README claimed 15/22 commands; actual count is 27. Updated both READMEs with missing commands: `/agent-launch`, `/codemap`, `/doe-health`, `/review`, `/pull-doe`
- **Wrap system checks heading** — Added `🔍 SYSTEM CHECKS` section heading before the bordered audit/DOE Kit box

---

## [v1.14.4] — 2026-03-05

Round 4 fix: session ID resolution for all commands.

### Fixed
- **CRITICAL: --complete/--fail/--abandon session resolution** — `--parent-pid` now auto-reads `.session-id-{pid}` file and sets `_session_override` in `main()`, so ALL commands resolve the correct session ID. Previously only `--claim` and hooks could find the session.
- **agent-launch instructions** — ALL multi_agent.py commands now include `--parent-pid $PPID` (claim, complete, fail, abandon)

---

## [v1.14.3] — 2026-03-05

Round 3 fix: per-terminal isolation via Claude Code PID.

### Fixed
- **CRITICAL: Session ID isolation (take 3)** — per-terminal files using Claude Code PID (`os.getppid()` in hooks, `$PPID` in Bash). Each terminal gets `.session-id-{pid}`, `.last-heartbeat-{pid}`, `.context-usage-{pid}.json`, `.context-warned-{pid}`. Solves the two-directory problem: hooks stay in project root, coordination files stay in project root, but each terminal's markers are isolated.
- **Wave completion cleanup** — glob-based cleanup of all PID-specific marker files (`*.session-id-*`, etc.)
- **agent-launch draft wave** — wave file written to `.draft-wave.json` (dotfile) until user approves, then moved to `wave-{N}.json`. Prevents orphaned wave files if session crashes before approval.
- **Wave file filtering** — `find_active_wave`/`find_latest_wave` now skip dotfiles (draft waves)
- **agent-launch instructions** — claim command now includes `--parent-pid $PPID` and explicit cd-to-worktree step

### Added
- **`--parent-pid` CLI arg** — passes Claude Code PID to `--claim` for session-id file naming

---

## [v1.14.2] — 2026-03-05

Round 2 adversarial review fixes + new `/agent-launch` command.

### Fixed
- **Reclaim log accuracy** — captures task-to-session mapping before modifying claims, so log entries attribute the correct stale session to each task
- **Context monitor glob** — matches all wave file names (not just `wave-*.json`), so budget detection works with custom waveIds like `comparison-filter`

### Added
- **`/agent-launch` command** — reads todo.md Queue, builds wave file, runs preview, launches on approval
- **Failed task retry docs** — documented that failed tasks are intentionally retryable (not terminal state)

---

## [v1.14.1] — 2026-03-05

Should-fix multi-agent bugs from adversarial review.

### Fixed
- **Reclaim** — preserves worktree branch (`delete_branch=False`) so new session can continue partial work
- **Wave sort** — `find_active_wave`/`find_latest_wave` use numeric index extraction instead of string sort (fixes wave-10 sorting before wave-2)
- **Validation dedup** — `cmd_validate` now delegates to `_analyze_wave` internally, eliminating ~100 lines of duplicated logic

### Added
- **`--fail` subcommand** — marks a task as failed with optional `--reason`, keeps worktree+branch for debugging, logs failure event

---

## [v1.14.0] — 2026-03-05

Critical multi-agent bug fixes from adversarial review.

### Fixed
- **Heartbeat hook** — uses fixed marker file (not per-PID) and reads session ID from `.tmp/.session-id` written by `--claim`
- **Context monitor** — corrected field names (`claimedTask`/`taskId` instead of `currentTask`/`id`), reads session ID from file instead of PID matching
- **Merge command** — auto-detects default branch (`master`/`main`) instead of hardcoding `master`

### Added
- `--claim` now writes `.tmp/.session-id` for hooks to read consistent session identity

---

## [v1.13.10] — 2026-03-05

Visual-explainer Progressive Disclosure triggers.

### Added
- 3 new triggers in CLAUDE.md: suggest `/diff-review` before commits, `/project-recap` after absence, `/plan-review` for alignment checks

---

## [v1.13.9] — 2026-03-05

Hook templates and pre-commit audit sweep.

### Added
- `hook-templates/javascript.json` — Claude Code hook template: warns on `console.log` and non-strict equality (`==`/`!=`) in JS/TS files
- `hook-templates/python.json` — Claude Code hook template: warns on bare exception catching and `shell=True` in subprocess calls
- `hook-templates/universal.json` — reference doc for hooks already included in the kit
- Pre-commit audit sweep — warnings (non-blocking) for `console.log` in JS/TS, bare `TODO` without reference, hardcoded localhost URLs
- Hook Templates section in CUSTOMIZATION.md — explains activation process

---

## [v1.13.8] — 2026-03-05

/doe-health diagnostic command.

### Added
- `/doe-health` command — 8-point integrity check (required files, CLAUDE.md line count, Progressive Disclosure targets, commands, hooks, git hooks, STATE.md freshness, kit version). Report only, never modifies.

---

## [v1.13.7] — 2026-03-05

/codemap command and /wrap structural change detection.

### Added
- `/codemap` command — generates `.claude/codemap.md` with project structure, key files, data flow, and active patterns
- `/wrap` step 8 — detects new/moved/deleted files and prompts to run /codemap

---

## [v1.13.6] — 2026-03-05

Self-annealing enhancement — root cause analysis and structured format for significant failures.

### Changed
- **Self-Annealing** section in CLAUDE.md — added "diagnose WHY" step, two-tier format (routine one-liners vs structured significant failures)
- **learnings.md** template — added structured failure format with What/Root cause/Fix/Prevention fields

---

## [v1.13.5] — 2026-03-05

Language best practices directives — prevention-over-detection guides for common agent failure modes.

### Added
- `directives/best-practices/javascript.md` — strict equality, async error handling, XSS prevention, cleanup patterns
- `directives/best-practices/python.md` — specific exceptions, mutable defaults, pathlib, injection prevention
- `directives/best-practices/html-css.md` — accessibility, semantic HTML, CSS custom properties, no inline styles
- `directives/best-practices/react.md` — dependency arrays, state immutability, derived state, cleanup effects

---

## [v1.13.4] — 2026-03-05

Architectural invariants directive — non-negotiable truths that survive any refactor.

### Added
- `directives/architectural-invariants.md` — 10 invariants covering DOE architecture, session integrity, safety, and extensibility. Includes escalation process when changes would violate an invariant.
- Progressive Disclosure trigger for architectural changes

---

## [v1.13.3] — 2026-03-05

/review command — adversarial code review via subagent.

### Added
- `/review` command — reads git diff, checks security/correctness/dead code/breaking changes/contract compliance, outputs PASS/PASS WITH NOTES/FAIL with structured findings. Advisory only, never modifies files.

---

## [v1.13.2] — 2026-03-05

Task contracts — testable completion criteria for non-trivial todo.md steps.

### Added
- **Task contract format** in todo.md format rules — `Contract:` block with verifiable criteria. Prevents premature "done" marking on complex steps.

---

## [v1.13.1] — 2026-03-05

CLAUDE.md enrichments — identity reframe, research separation, sycophancy-aware verification, subagent context savings, and best practices trigger.

### Changed
- **Who We Are** — reframed from role-specific ("non-technical founder") to generic ("human defines intent, Claude builds")
- **Rule 2** — added research/implementation separation guidance for significant research tasks (3+ approaches)
- **Rule 4** — added sycophancy-aware evaluation: use neutral verification prompts, not leading questions
- **Rule 7** — added concrete context savings numbers (15k tokens → 500-token summary = 30x saving)

### Added
- Progressive Disclosure trigger: read language best practices directives before writing code

---

## [v1.13.0] — 2026-03-05

Added /pull-doe — the reverse of /sync-doe. Pulls kit updates into a project with version-aware diffing, file categorization, and safe merging.

### Added
- `/pull-doe` command — reverse sync (kit → project) with version-aware diffing, analysis box, and result summary
- `directives/starter-kit-pull.md` — 15-step pull procedure with file categorization (global installs, hooks, CLAUDE.md, templates, directives, execution scripts)
- Progressive Disclosure trigger for starter-kit-pull directive

### Changed
- `/sync-doe` — added cross-reference to `/pull-doe` for reverse direction

---

## [v1.12.7] — 2026-03-05

Upgraded /crack-on to bordered card format matching stand-up, sitrep, and other commands.

### Changed
- `/crack-on`: full bordered card with project in header, feature, progress bar, DOE Kit status, picking-up step with plain English summary, and model row
- `/crack-on`: removed separate model check paragraph — now integrated into card

---

## [v1.12.6] — 2026-03-05

Bordered card alignment fix and bidirectional DOE sync detection across all 8 global command files.

### Changed
- All bordered commands: explicit `line()` helper pattern in BORDER rules — prevents header misalignment
- All bordered commands: mandate "never construct `f"│{...}│"` manually" in generation rules
- 5 commands: bidirectional sync detection (inbound tag comparison + outbound file diff, not just file diff)
- Files: commands, crack-on, eod, sitrep, stand-up, sync-doe, vitals, wrap

---

## [v1.12.5] — 2026-03-05

Model allocation rules — plans and subagents must specify which model and thinking level to use.

### Changed
- Rule 1: plans must include recommended model + thinking level per step
- Rule 7: subagents must use deliberate model selection (Opus/Sonnet/Haiku)
- `/sitrep`: DOE KIT diff wording fix ("check" vs "count")

---

## [v1.12.4] — 2026-03-04

Standardised DOE sync status format across all 6 global commands. Compact notation replaces verbose text.

### Changed
- DOE sync status: compact `*` format across `/commands`, `/crack-on`, `/sitrep`, `/stand-up`, `/vitals`, `/wrap`
- Synced state: bare version (no tick, no "synced" text)
- Unsynced state: `vX.Y.Z *` (asterisk suffix)
- `/stand-up` WARNINGS: omit section when all PASS (was showing "None ✓")

---

## [v1.12.3] — 2026-03-04

Compressed CLAUDE.md from 117 to 83 lines by moving Break Glass to a directive and tightening 3 rules. Overhauled /sitrep.

### Added
- `directives/break-glass.md` — emergency recovery procedure (extracted from CLAUDE.md)
- Progressive Disclosure trigger for break-glass directive
- `/sitrep` COMPLETED section — cumulative session work log
- `/sitrep` push status indicator (pushed/committed)
- `/sitrep` DOE version in header row

### Changed
- CLAUDE.md compressed: Rule 1 (planning), Rule 8 (pre-commit checks), hook response format (117 → 83 lines)
- `/sitrep` reordered: ACTIVE shown first, DONE second, PENDING renamed to UP NEXT (capped at 5)
- `/sitrep` box auto-stretches to fit content instead of truncating
- `directives/starter-kit-sync.md` — Steps 7 and 9 now require bordered boxes (diff summary + changelog) for approval

### Removed
- Break Glass section from CLAUDE.md (moved to directive)
- `/sitrep` BLOCKERS, QUEUE, and DOE KIT rows (DOE version moved to header)

## [v1.12.2] — 2026-03-04

### Added
- **`/sync-doe` analysis box** — new required Analysis Box section showing a bordered diff summary with header (version right-aligned), context summary, numbered file list, verdict, and recommendation. Displayed before proposing changes so the user can approve or reject from a clear overview.

---

## [v1.12.1] — 2026-03-04

### Added
- **Universal learnings template** — added 3 Shell & Platform entries (emoji box-drawing, zsh nullglob, `$$` subshell PID), new Hooks & Session Files section (orphan file prevention), new Output section (single-block assembly, re-present script output as text). Template now has 6 sections and 11 learnings.

---

## [v1.12.0] — 2026-03-04

### Changed
- **`/commands` reference** — updated from 15 to 22 commands. Added `/fact-check` to Quality section. Added new Visual section with 6 commands: `/project-recap`, `/diff-review`, `/plan-review`, `/generate-visual-plan`, `/generate-web-diagram`, `/generate-slides`.

---

## [v1.11.8] — 2026-03-04

### Fixed
- **`/sync-doe` result box** — replaced hardcoded box width with dynamic computation (`W = max(len(line)) + 4`). Long summary lines no longer break the right border.

---

## [v1.11.7] — 2026-03-04

### Changed
- **`/wrap` layout** — moved NEXT UP section to render after the footer (was between Decisions and Numbers). Renumbered parts 6-9.

---

## [v1.11.6] — 2026-03-04

### Fixed
- **Session timer** — replaced per-PID `.session-start-$$` with single `.tmp/.session-start` file across 6 commands (`/stand-up`, `/crack-on`, `/sitrep`, `/wrap`, `/eod`, `/commands`). `$$` returned a different subshell PID per Bash tool call, making the timer unreliable. Worktrees handle multi-session isolation, so per-PID files were unnecessary.

---

## [v1.11.5] — 2026-03-04

### Changed
- **Box-drawing rules** — clarified in 5 global commands (`/audit`, `/sitrep`, `/stand-up`, `/sync-doe`, `/wrap`): explicitly use Unicode box-drawing characters (`┌─┐`, `├─┤`, `└─┘`, `│`) for borders, ASCII-only for content inside borders

---

## [v1.11.4] — 2026-03-04

### Changed
- **Commands README** — updated from 15 to 22 commands, added Visual category (`/project-recap`, `/diff-review`, `/plan-review`, `/generate-visual-plan`, `/generate-web-diagram`, `/generate-slides`), added `/fact-check` to Quality, reorganised table layout

---

## [v1.11.3] — 2026-03-04

### Changed
- **`/audit` result box** — output now ends with a programmatic bordered result box (matching `/sync-doe` and `/wrap` style) showing PASS/WARN/FAIL counts and key stats

---

## [v1.11.2] — 2026-03-04

### Added
- **`/wrap` agents stat** — new "agents spawned" metric in The Numbers section, counted from Agent tool calls in the session

### Changed
- **`/wrap` session time label** — shortened from "total session time" to "session time"
- **`/wrap` system checks box** — replaced hand-padded example boxes with programmatic generation instruction (collect lines, find max length, `.ljust()`)

### Removed
- **`/wrap` One-Stat Highlight** — removed Part 9 (redundant with The Numbers). Parts renumbered from 11 to 10.

---

## [v1.11.1] — 2026-03-04

### Changed
- **`/wrap` title card** — project name now uses spaced-out uppercase text (e.g. `M O N T Y`) centered in the box, generated from the current directory name. Narrative lines render as plain paragraphs below the code fence (no indentation).
- **`/wrap` output** — removed haiku section. Parts renumbered from 12 to 11. Narrative sections (vibe, journey, commits, decisions, next up) now appear before data tables (numbers, timeline, leaderboard).

---

## [v1.11.0] — 2026-03-04

### Added
- **7 new universal commands:** `diff-review.md` (visual HTML diff review), `fact-check.md` (verify doc accuracy against codebase), `generate-slides.md` (magazine-quality HTML slide decks), `generate-visual-plan.md` (visual HTML implementation plans), `generate-web-diagram.md` (standalone HTML diagrams), `plan-review.md` (visual HTML plan review), `project-recap.md` (visual HTML project recap).

---

## [v1.10.2] — 2026-03-04

### Changed
- **`sync-doe.md` result box templates** — moved status emojis above the box as standalone signal lines (e.g. `✅ SYNCED` before the bordered box). Emojis stay visible for quick-glance scanning without breaking box-drawing alignment.

---

## [v1.10.1] — 2026-03-04

### Fixed
- **`sync-doe.md` result box templates** — removed emojis from inside bordered boxes (they render double-width, breaking alignment). Added programmatic box generation rule and ASCII-only constraint matching other commands.

---

## [v1.10.0] — 2026-03-04

### Changed
- **Per-PID session timers for multi-terminal safety.** Session clock files changed from `.tmp/.session-start` to `.tmp/.session-start-$$` (shell PID). Each terminal gets an independent timer. Stale PID files are pruned on `/crack-on`, `/stand-up`, and `/wrap` via `kill -0` checks. `/eod` scans all PID files to detect multiple active sessions. Updated all 6 command files: `crack-on.md`, `stand-up.md`, `sitrep.md`, `wrap.md`, `eod.md`, `commands.md`.
- **Progress bar border exception** in `stand-up.md` — `█` and `░` characters now explicitly permitted inside bordered boxes (they render at fixed width in terminals).

---

## [v1.9.4] — 2026-03-04

### Added
- **Code Hygiene rule: plans go in the project.** New CLAUDE.md rule requiring plans to be written to the project's `.claude/plans/` directory with descriptive filenames, not to `~/.claude/plans/`. Prevents plan files from landing in the global directory where they're invisible to the project.

---

## [v1.9.3] — 2026-03-04

### Fixed
- **`wrap_stats.py` step counting** — `count_steps_completed_today()` counted all `[x]` steps with today's date, inflating `stepsCompleted` across multiple sessions on the same day. Replaced with `count_steps_completed_since()` which parses the `HH:MM DD/MM/YY` timestamp and only counts steps completed after the session start time.

---

## [v1.9.2] — 2026-03-04

### Fixed
- **`context_monitor.py` file accumulation** — replaced per-PID tracker files (`.context-{pid}.json`) with a single `.context-usage.json` that gets overwritten each tool call. Prevents hundreds of orphan files accumulating in `.tmp/` per session. Same fix applied to warn marker (`.context-warned-{pid}` → `.context-warned`).

---

## [v1.9.1] — 2026-03-04

### Added
- **`copy_plan_to_project.py` hook** — PostToolUse hook that auto-copies plans written to `~/.claude/plans/` into the current project's `.claude/plans/` directory. Fires after `write|edit` tool calls targeting `~/.claude/plans/*.md`.
- **PostToolUse section in `settings.json`** — registers the plan-copy hook

---

## [v1.9.0] — 2026-03-04

### Changed
- **Multi-agent system moved to global install** — no more per-project copies. `multi_agent.py` → `~/.claude/scripts/`, `heartbeat.py` + `context_monitor.py` → `~/.claude/hooks/`, `/hq` → `~/.claude/commands/`. Install once, works across all projects.
- **`setup.sh` extended** — 3 new install sections: hooks to `~/.claude/hooks/`, scripts to `~/.claude/scripts/`, merges PostToolUse into `~/.claude/settings.json`
- **Path refactor** — all multi-agent Python files use `Path.cwd()` instead of `Path(__file__)` for global execution
- **`--project-root` override** — `multi_agent.py` accepts `--project-root DIR` to specify the project directory explicitly
- **Template `.claude/settings.json` now PreToolUse-only** — PostToolUse hooks are merged into the global settings by `setup.sh`

---

## [v1.8.0] — 2026-03-04

### Added
- **Multi-agent coordination system** — `execution/multi_agent.py` for running 2-4 parallel Claude Code sessions. Wave management, task claiming, session registry, heartbeats, merge protocol, cost tracking. All state in `.tmp/waves/`.
- **`/hq` command** — `.claude/commands/hq.md` project-level dashboard. Shows wave status, terminal liveness, task progress, cost estimates, merge order. Modes: no_wave (help), active (live dashboard).
- **Heartbeat hook** — `.claude/hooks/heartbeat.py` PostToolUse hook updating session liveness every 30s during active waves. Stale sessions (>2 min) are detectable and reclaimable.
- **Context monitor hook** — `.claude/hooks/context_monitor.py` PostToolUse hook tracking estimated context usage. Warns at 60%, stops at 80% for graceful handoff. Model-aware budgets during waves (haiku: 30k, sonnet: 80k, opus: 200k).
- **Active wave audit check** — `check_active_wave` in `audit_claims.py` warns when a wave is active and results may be incomplete until merge. Runs in fast/hook mode.
- **PostToolUse hooks in settings.json** — heartbeat and context monitor fire after every tool use

---

## [v1.7.4] — 2026-03-03

### Removed
- **`/wrap`** — removed fortune cookie line from session footer. Adds noise without value.

---

## [v1.7.3] — 2026-03-03

### Changed
- **`/stand-up` (status mode)** — reordered card: PHASE GOAL now appears above PROGRESS for better readability. Added NEXT STEP line showing the first uncompleted step from todo.md, so the immediate task is always visible at a glance.

---

## [v1.7.2] — 2026-03-03

### Fixed
- **`execution/audit_claims.py`** — skip version tag WARN for `[INFRA]` tasks. Infrastructure features don't bump app version, so their todo steps never have version tags. `parse_completed_tasks()` now tracks heading context and `check_task_format()` skips the check for `[INFRA]` sections.

---

## [v1.7.0] — 2026-03-02

### Changed
- **`/wrap`** — lightweight rewrite. Removed scoring/badges/genre system. One dramatic narrative (no genre selection), added session haiku, one-stat highlight, fortune cookie footer. Leaderboard now shows commits/lines instead of scores. Vibe check determined inline instead of by script.
- **`/roast`** — removed score trend and badge pattern analysis bullets (stats.json no longer has these fields)
- **`/stand-up`** — removed "score trends" FOCUS bullet
- **`/eod`** — removed SCORE line from card, simplified session list to title + duration (no scores/badges)
- **`/commands`** — updated `/wrap` and `/roast` descriptions to reflect lightweight wrap

### Removed
- Scoring formula, badge definitions, genre selection, multiplier system, high score tracking from `/wrap`
- `execution/wrap_stats.py` scoring logic (978 → ~150 lines, now metrics + streak only)

---

## [v1.6.0] — 2026-03-02

### Added
- **`/eod`** — new end-of-day report command. Aggregates all sessions, commits, features, and position into one bordered summary. Shows day stats, session list, semantic "What Got Done" grouping, position at EOD, and day vibe.
- **`execution/wrap_stats.py`** — new deterministic scoring script (978 lines). Handles all session scoring computation: git metrics, streak, multiplier, raw/final score, badge evaluation (with once-per-day dedup), high score check, leaderboard consolidation. Outputs JSON for the `/wrap` prompt to render.

### Changed
- **`/stand-up`** — added WARNINGS section (surfaces audit WARN/FAIL findings in kick-off card with detail lines and "Fix now?" suggestions) and FOCUS section (2-3 coaching bullets from `stats.json` analysis: infra/product ratio, stale WARNs, commits/session trends, steps completed, time-of-day patterns, score trends)
- **`/vitals`** — added mandatory audit detail lines rule: WARN/FAIL items must each be shown on indented detail lines, using `--json` flag for reliable parsing
- **`/roast`** — added "And you..." developer habit analysis section: roasts session timing, infra/product ratio, score trends, badge patterns, commits/session, steps throughput, and streak from `stats.json`
- **`/wrap`** — rewrote to delegate all scoring computation to `execution/wrap_stats.py`. Steps 2+3 replaced with single script call. Display sections now reference `result.*` JSON fields. Prompt reduced from ~22K to ~17K chars.

---

## [v1.5.0] — 2026-03-02

### Changed
- **`/stand-up`** — rewritten as context-aware dual-mode command. Detects `.tmp/.session-start`: **kick-off mode** (no session) starts clock, reads project state, shows bordered card with plan, waits for sign-off. **Status mode** (session active) shows bordered daily status card with progress, momentum, activity since last milestone, blockers, pending decisions, and queue. Read-only in status mode.
- **`/commands`** — updated `/stand-up` description for dual-mode, updated smart filter section
- **Reference docs** — updated stand-up descriptions across README, SYSTEM-MAP, CUSTOMIZATION, and global-commands/README
- **CUSTOMIZATION** — corrected command count from 11 to 13 (added `/vitals`, `/commands` to list)

---

## [v1.4.0] — 2026-03-02

### Added
- **`/vitals`** — new workspace health check command: git status, quick audit, DOE Kit sync, STATE.md alignment, stale temp files. Bordered output with ✓/⚠️ per check.

### Changed
- **`/wrap`** — added quick audit to Step 1 housekeeping; replaced plain footer with bordered "System Checks" section showing audit results and DOE Kit sync status together
- **`/commands`** — updated to 13 commands, added `/vitals` under Quality category
- **README** — command count 12 → 13, added `/vitals` to Quality row in table
- **SYSTEM-MAP** — added vitals.md to file table, command reference, and directory tree

---

## [v1.3.0] — 2026-03-02

### Added
- **`setup.sh`** — one-command installer: copies commands to `~/.claude/commands/`, copies universal CLAUDE.md template (if none exists), activates git hooks, writes version receipt to `~/.claude/.doe-kit-version`
- **`/commands`** — new slash command replacing `/README`. Shows full command reference by category, checks installation status (missing commands), and checks GitHub for kit updates
- **Slash Commands section in README** — category table with smart filter explanation, links to `/commands` for full reference
- **Manual setup fallback** — collapsible details block in Quick Start for users who prefer not to use the script

### Changed
- Quick Start simplified from 6 steps to 3 (clone → `./setup.sh` → `/stand-up`)
- `global-commands/README.md` is now a short GitHub directory readme (no longer doubles as a command)
- Command count updated from 11 → 12 across README and command reference

### Removed
- `/README` command — replaced by `/commands`

---

## [v1.2.1] — 2026-03-01

### Changed
- `/sync-doe` now shows a bordered result summary box at the end of every sync — `✅ SYNCED`, `⏭️ NO CHANGES`, `❌ REJECTED`, or `⚠️ BLOCKED` with explanation and kit version

---

## [v1.2.0] — 2026-03-01

### Added
- **CLAUDE.md Rule 10: Parallelise by default** — automatically spawn sub-agents for independent tasks, flag sequential dependencies, commit one-at-a-time per Rule 6
- **CLAUDE.md Guardrail: Protect starter kit** — blocks direct edits to `~/doe-starter-kit`; all changes must go through `/sync-doe`

### Changed
- Renamed `/sync-kit` to `/sync-doe` across all files — command name, file (`sync-doe.md`), and 40+ references in 10 files. Better describes syncing DOE framework improvements.

---

## [v1.1.1] — 2026-02-28

### Added
- `/wrap` footer now shows DOE Kit version and sync status as the last line before closing

---

## [v1.1.0] — 2026-02-28

### Added
- **DOE Kit awareness** — `/stand-up`, `/crack-on`, `/sitrep`, and `/wrap` now check `~/doe-starter-kit` if it exists
- `/stand-up` and `/crack-on` show kit version + pending change count at session start
- `/sitrep` shows `DOE KIT` row with version and sync status
- `/wrap` nudges `/sync-doe` when DOE files have changed since last sync
- All four commands recommend `/sync-doe` when pending changes are detected

---

## [v1.0.0] — 2026-02-28

Initial release. 40 files across 8 directories.

### Added
- **CLAUDE.md** — 9 operating rules, guardrails, progressive disclosure triggers, directory structure
- **STATE.md** — Session memory template
- **ROADMAP.md** — Product roadmap template
- **SYSTEM-MAP.md** — Complete file-by-file documentation and relationship map
- **CUSTOMIZATION.md** — Guide for adapting the kit to new projects
- **Directives** — `_TEMPLATE.md`, `documentation-governance.md`, `claim-auditing.md`, `starter-kit-sync.md`
- **Execution** — `audit_claims.py` with universal checks and project extension point
- **11 slash commands** — `/stand-up`, `/crack-on`, `/wrap` (gamified), `/sitrep`, `/sync-doe`, `/pitch`, `/audit`, `/quick-audit`, `/roast`, `/eli5`, `/shower-thought`
- **Guardrail hooks** — `block_dangerous_commands.py`, `block_secrets_in_code.py`, `protect_directives.py`
- **Git hooks** — `commit-msg` (strip AI co-author trailers), `pre-commit` (fast audit)
- **Session timer** — `/stand-up` and `/crack-on` start clock, `/sitrep` and `/wrap` report duration
- **Gamification** — Scoring, badges, streaks, leaderboard, themed wrap-up cards
- **README.md** — Quick start guide and feature overview

### Fixed
- `commit-msg` hook uses macOS-compatible `sed -i ''` syntax
- `/sitrep` STATUS field has clearer instruction wording
- `/wrap` score table has separate high score / non-high score templates with `d[streak]` multiplier format

### Changed
- `/sync-doe` includes up-to-date check — stops early if nothing to sync
- Sync directive includes safety guardrails: pull-before-compare, three-way diff, additive merging, git stash backup
