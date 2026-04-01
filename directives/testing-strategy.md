# Directive: Testing Strategy

## Goal
Define what, when, and how to test in this project -- so verification is consistent, fast, and never skipped.

## When to Use
- Setting up testing for a new project or configuring test tools
- Writing contract criteria for a new task
- Deciding whether a change needs [auto] or [manual] verification
- Debugging a verification failure

## Project Type
<!-- Fill in your project type from tests/config.json (e.g. html-app, python-cli, api-service) -->

## What to Test

### [auto] Criteria (deterministic, machine-verified)
Use these for anything a script can check reliably:
- **File existence:** `Verify: file: <path> exists`
- **File content:** `Verify: file: <path> contains <string>`
- **Script execution:** `Verify: run: <shell command>` (exit code 0 = pass)
- **HTML structure:** `Verify: html: <path> has <CSS selector>` (requires BeautifulSoup)

Rules:
- Every task in todo.md must have at least one `[auto]` criterion
- Prefer `file: ... contains` over `run: grep` -- it's faster and more readable
- `run:` commands must complete within the timeout set in tests/config.json (default 30s)
- Keep commands simple -- one check per criterion, no chained pipes when avoidable

### [manual] Criteria (human-verified)
Use these for things that require visual judgment or interaction:
- UI rendering, layout, and responsiveness
- Data accuracy that requires domain knowledge
- User flows that involve clicking, scrolling, or navigation
- Accessibility checks (screen reader, keyboard nav)

Rules:
- `[APP]` tasks must have at least one `[manual]` criterion
- `[INFRA]` tasks can be fully `[auto]`
- Write manual criteria as yes/no questions

## What NOT to Test
- Third-party API availability (flaky, not our fault)
- Exact pixel rendering (varies by browser/OS)
- Performance benchmarks (too environment-dependent for contracts)
- File sizes or line counts (brittle, break on unrelated changes)

## Verification Flow

### Solo mode (single terminal)
1. Write task + contract in todo.md
2. Implement the feature
3. Run `/agent-verify` (or verify manually)
4. All `[auto]` pass + all `[manual]` confirmed -> mark step done
5. If `[auto]` fails: fix and re-verify (up to 3 attempts)

### Wave mode (multi-agent)
1. `/agent-launch` validates contracts at pre-flight
2. Agent implements the feature
3. `--complete` runs `execution/verify.py` automatically
4. `--merge` runs regression checks (pre/post comparison)

## Build Step
<!-- If your project has a build step, tests/config.json buildCommand runs before verification -->

## Pattern Reference

| Pattern | Example | Checks |
|---------|---------|--------|
| `file: <path> exists` | `file: src/config.py exists` | File exists on disk |
| `file: <path> contains <str>` | `file: CLAUDE.md contains testing trigger` | Substring in file |
| `run: <cmd>` | `run: python3 execution/verify.py --self-test` | Exit code 0 |
| `html: <path> has <sel>` | `html: index.html has .main-content` | CSS selector match |

## Three-Level Verification

When writing `[auto]` contract criteria, aim for depth -- not just existence. Three levels of verification catch progressively more bugs:

### Level 1: Exists
The file or function is physically present.
```
Verify: file: src/feature.js exists
```
**Catches:** missing files, typos in filenames, forgotten creation.
**Misses:** stubs, placeholder code, dead functions.

### Level 2: Substantive
The implementation contains real logic, not stubs or placeholders.
```
Verify: file: src/feature.js contains calculateScore
Verify: run: ! grep -q 'return null' src/feature.js
```
**Catches:** stub implementations (`return null`, `// TODO`), empty function bodies, placeholder text.
**Misses:** code that exists but is never called.

### Level 3: Wired
The implementation is actually imported, called, and used by the rest of the application.
```
Verify: run: grep -rq 'calculateScore' src/
Verify: run: grep -rq 'featureInit' src/app.js
```
**Catches:** orphan code, dead functions, modules that exist but are never loaded.
**Misses:** logic correctness (use `/code-trace` for that).

### When to use each level
- **Quick tasks (1-2 files):** Level 1 is usually enough -- the contract criteria themselves describe the behaviour.
- **Data-layer steps (algorithms, scoring, derivation):** Use Level 2 to verify substantive implementation, then run `/code-trace` for logic correctness.
- **Integration steps (cross-module wiring):** Use Level 3 to verify the module is actually connected to the rest of the app.
- **All [APP] features:** The `[manual]` criteria naturally cover "is it wired?" since the tester sees the UI working.

### Post-Step Testing Protocol

After completing each step, Claude runs the appropriate quality checks based on the step type:

| Step type | What runs automatically | Signpost |
|-----------|------------------------|----------|
| Data-layer (algorithms, scoring, derivation) | `/code-trace` on the new module | "This is a data-layer step -- running code trace" |
| UI (pages, components, layouts) | Playwright browser tests | "Running browser tests for affected pages" |
| Integration (cross-module wiring) | `/code-trace --integration` | "Running integration trace across modules" |
| Any step | Regression suite (if wired) | "Regression: N/N passed" |
| Final step | Full sweep: regression + health check | "Running final verification sweep" |

Claude announces what testing will happen at the start of each step and reports results after completion. The user never has to remember what to run.

## Edge Cases
- `html:` pattern requires `beautifulsoup4` -- if not installed, criterion returns SKIP (not FAIL)
- `run:` commands inherit the project root as cwd
- `file:` paths are relative to project root unless absolute
- If `tests/config.json` is missing, verify.py uses defaults (30s timeout, no build step)

## Verification
- [ ] This directive exists and is referenced from CLAUDE.md triggers
- [ ] tests/config.json exists alongside this directive
- [ ] Pattern examples above match the patterns defined in todo.md format rules
