Run a diagnostic check on DOE framework integrity. Report only -- do not fix anything automatically.

## Checks

Run each check and collect results as PASS/WARN/FAIL:

### 1. Required files exist
Check that these files exist in the project root:
- `CLAUDE.md`
- `STATE.md`
- `tasks/todo.md`
- `learnings.md`
- `.claude/settings.json`
- `directives/` directory (with at least one .md file)
- `execution/` directory

Missing files = FAIL. Empty directories = WARN.

### 2. CLAUDE.md line count
Count lines in CLAUDE.md. Under 120 = PASS. 120-149 = WARN ("approaching 150-line ceiling"). 150+ = FAIL.

### 3. Progressive Disclosure integrity
Read all triggers from CLAUDE.md's Progressive Disclosure section. For each trigger that references a file (e.g. `directives/foo.md`, `learnings.md ## Section`):
- Check the referenced file exists = PASS
- File doesn't exist = FAIL (broken trigger)
- Section reference doesn't exist in the file = WARN

### 4. Commands installed
List files in `~/.claude/commands/`. Cross-reference against commands mentioned in CLAUDE.md or directives. Flag any referenced commands that don't exist as files.

### 5. Hooks registered
Read `.claude/settings.json`. For each hook registered in `hooks`:
- Check the hook file exists at the specified path = PASS
- File doesn't exist = FAIL (will cause blocking errors on every tool call)
- File exists but isn't readable = WARN

### 6. Git hooks active
Check `git config core.hooksPath`. If it points to `.githooks/`, verify the directory exists and contains hook files. If not set, WARN.

### 7. STATE.md freshness
Read STATE.md "Last Session" section. If it references work that doesn't match recent git log (last 5 commits), WARN ("STATE.md may be stale").

### 8. DOE Kit version
If `~/doe-starter-kit` exists:
- Read kit version: `cd ~/doe-starter-kit && git describe --tags --abbrev=0`
- Read project's recorded version from STATE.md
- Match = PASS. Mismatch = WARN (need /pull-doe or /sync-doe)
If `~/doe-starter-kit` doesn't exist, skip this check.

## Output

Present results in a bordered box. **Generate programmatically** -- collect all content lines into a list, compute `W = max(len(l) for l in lines) + 4`, define `line(c)` as `f"│  {c}".ljust(W + 1) + "│"`, then pass ALL rows through `line()`. Unicode box-drawing borders. Content inside borders must be ASCII-only.

```
┌──────────────────────────────────────────────────────────┐
│  DOE HEALTH CHECK                        [project name]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  [PASS]  Required files             8/8 present          │
│  [PASS]  CLAUDE.md line count       85 lines             │
│  [PASS]  Progressive Disclosure     12/12 targets exist  │
│  [PASS]  Commands installed         24 commands           │
│  [PASS]  Hooks registered           2/2 files present    │
│  [WARN]  Git hooks                  core.hooksPath not set│
│  [PASS]  STATE.md freshness         matches recent work  │
│  [PASS]  DOE Kit version            v1.13.7 (synced)     │
│                                                          │
│  RESULT: 7 PASS, 1 WARN, 0 FAIL                         │
│                                                          │
│  Recommendations:                                        │
│  - Run: git config core.hooksPath .githooks              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Rules
- Report only. Never modify files or settings.
- Show recommendations for WARN and FAIL items -- one line each, actionable.
- If everything passes, just show the result line and "DOE framework is healthy."
- Keep it fast -- no API calls, no expensive scans. File existence checks only.
