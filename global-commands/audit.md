Run a comprehensive project audit covering claims, workspace health, and DOE framework integrity. Report only — do not fix anything automatically.

## Step 1: Claim Audit

Run `python3 execution/audit_claims.py` (full mode, not --hook). Capture PASS/WARN/FAIL counts and any non-PASS findings with their details.

## Step 2: Workspace Health

Run these checks and collect results:

1. **Git status** — Run `git status`. Flag uncommitted changes (modified, staged, untracked). Clean = no changes.
2. **Temp files** — Check `.tmp/` for files older than 24 hours. Flag stale files by name.
3. **STATE.md alignment** — Read STATE.md's "Active feature" line and compare with `tasks/todo.md` ## Current heading. Flag if they disagree.

## Step 3: DOE Health

Run these checks and collect results as PASS/WARN/FAIL:

1. **Required files** — Check these exist: `CLAUDE.md`, `STATE.md`, `tasks/todo.md`, `learnings.md`, `.claude/settings.json`, `directives/` (with at least one .md), `execution/`. Missing = FAIL, empty dir = WARN.
2. **CLAUDE.md size** — Count lines. Under 120 = PASS. 120-149 = WARN. 150+ = FAIL.
3. **Progressive Disclosure** — For each trigger in CLAUDE.md that references a file, check it exists. Missing file = FAIL, missing section = WARN.
4. **Commands installed** — List `~/.claude/commands/`. Cross-reference against commands mentioned in CLAUDE.md or directives. Flag missing commands.
5. **Hooks registered** — Read `.claude/settings.json`. For each hook, check the file exists at the specified path. Missing = FAIL.
6. **Git hooks active** — Check `git config core.hooksPath`. If it points to `.githooks/`, verify that directory exists and has hook files. If not set, WARN.
7. **STATE.md freshness** — Compare STATE.md "Last Session" with last 5 git commits. Flag if they don't match.
8. **DOE Kit version** — If `~/doe-starter-kit` exists, compare kit tag (`git describe --tags --abbrev=0`) with STATE.md's recorded version. Match = PASS, mismatch = WARN. Also diff key syncable files for outbound drift.

## Output

Collect ALL results from all three steps, then present everything in a single bordered box. **Generate the box programmatically** — collect all content lines into a list, compute `W = max(len(l) for l in lines) + 4`, define `line(c)` as `f"│  {c}".ljust(W + 1) + "│"`, then pass ALL rows through `line()`. Unicode box-drawing borders. Content inside borders must be ASCII-only (no emojis).

Structure:

```
┌──────────────────────────────────────────────────────────────┐
│  PROJECT AUDIT                              [project name]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CLAIMS      7 PASS, 0 WARN, 0 FAIL                         │
│  WORKSPACE   git clean, 0 stale tmp, STATE aligned           │
│  DOE         8/8 checks pass                                 │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  RESULT: All clear                                           │
└──────────────────────────────────────────────────────────────┘
```

When there are non-PASS items, expand with detail lines below each section:

```
┌──────────────────────────────────────────────────────────────┐
│  PROJECT AUDIT                              [project name]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CLAIMS      5 PASS, 2 WARN, 1 FAIL                         │
│    FAIL: data-governance.md -- version not updated           │
│    WARN: learnings.md -- 2 minor versions behind             │
│    WARN: ROADMAP.md -- status tag stale                      │
│                                                              │
│  WORKSPACE   3 uncommitted, 1 stale tmp, STATE misaligned   │
│    Modified: STATE.md, tasks/todo.md, learnings.md           │
│    Stale: .tmp/last-audit.txt                                │
│    STATE says "None" but todo.md has active feature           │
│                                                              │
│  DOE         7 PASS, 1 WARN, 0 FAIL                         │
│    [WARN] Git hooks: core.hooksPath not set                  │
│    -> Fix: git config core.hooksPath .githooks               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  RESULT: 5 items need attention                              │
└──────────────────────────────────────────────────────────────┘
```

## Rules

- Run ALL checks every time. No flags, no modes, no shortcuts.
- Show all three sections in the output even if they all pass.
- For WARN and FAIL items in the DOE section, add a one-line actionable recommendation prefixed with `->`.
- For claim FAIL items, explain in plain English what's wrong.
- Save findings to `.tmp/last-audit.txt` (the audit script does this automatically for claims).
- Keep it fast — no paid API calls, no expensive scans. File existence and git checks only (beyond the audit script).
- After showing results, re-present the full bordered output as text in your response. Tool output alone is not sufficient.
