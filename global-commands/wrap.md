Before ending this session, complete all steps in order.

## Step 1: Housekeeping

1. **Update STATE.md** — Write the current position, any decisions made, blockers found, and a 1-2 sentence summary under Last Session.
2. **Update tasks/todo.md** — Make sure all completed steps have timestamps. Move any completed features to Done if needed.
3. **Check for learnings** — If anything failed and was fixed, or a useful pattern was discovered, log it to learnings.md or ~/.claude/CLAUDE.md.
4. **Commit and push** — Make sure all work is committed. No uncommitted changes should remain.
5. **Clean up session timer** — Run `rm -f .tmp/.session-start` to delete the session timer file.
6. **DOE Kit sync check** — If `~/doe-starter-kit` exists, check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (inbound). (2) Do any key syncable files differ? (outbound). Diff key files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) against the starter kit. If either condition is true, record for the System Checks section (meaning `/sync-doe` or `/pull-doe` needed). If neither, record as synced.
7. **Quick audit** — Run `python3 execution/audit_claims.py --hook` (fast checks only). Record the PASS/WARN/FAIL counts for the System Checks section. If any FAIL items exist, fix them before proceeding. WARN items can be noted and left for the next session.

## Step 2: Compute Session Stats

Find the first commit of this session: look at `git log --oneline` and identify where your work started (after the last "Update session stats" or "wrap" commit, or use the session start time from `.tmp/.session-start`).

Read `.tmp/.session-start` for the session start ISO timestamp. If it doesn't exist, use the first commit time.

Run the stats script:
```bash
python3 execution/wrap_stats.py \
  --since <first-session-commit-hash> \
  --session-start <ISO-timestamp-from-.tmp/.session-start> \
  --todo tasks/todo.md \
  --stats .claude/stats.json
```

This script gathers git metrics, computes streak, updates stats.json (v2), and outputs JSON to stdout.

Parse the JSON output. The key fields:

```
result.metrics      → commits, linesAdded, linesRemoved, filesTouched,
                      stepsCompleted, sessionDuration, commitLog
result.streak       → current streak day count
result.leaderboard  → 10-entry consolidated leaderboard (commits/lines per day)
result.stats        → the full updated stats.json
```

Commit stats.json with message: "Update session stats".

## Step 3: Print Session Wrap-Up

Build the full wrap-up and print it as one block. Use the script's JSON output for all numbers.

### Part 1: Title Card

Write a dramatic title and 3-4 line narrative about the session. Always reference specific files, features, or data from this session. Be melodramatic — think movie poster tagline meets opening crawl. One style, every time:

```
╔══════════════════════════════════════════╗
║                                          ║
║        P R O J E C T   N A M E          ║
║                                          ║
║     Episode [N]: [TITLE IN CAPS]         ║
║                                          ║
╚══════════════════════════════════════════╝

[Dramatic opening line about the state of the codebase.]
[Line referencing what was actually built this session.]
[Line referencing specific challenges or data wrangled.]
[Line about what lies ahead, trailing off into the distance...]
```

The project name is the current directory name (uppercased), displayed with spaces between each letter for a large, bold feel (e.g. `M O N T Y`). Episode N = `result.stats.lifetime.totalSessions`. Title and crawl MUST reference actual features, real files, and real problems. **Generate the title card programmatically** — use `.center(W)` to center each `║` line within the exact inner width (W = 42 minimum, expand if the spaced name or episode title is wider than 38 chars). Never hand-pad the title card. **Output the title card box inside a code fence** (triple backticks) so the terminal preserves leading spaces for centering. The narrative lines go below the code fence as plain markdown paragraphs — no leading spaces, no indentation. Each line is its own paragraph.

### Part 2: Vibe Check

Determine the vibe from what actually happened this session:
- Smooth session, no failures, 5+ commits → `😎 Smooth sailing`
- Clean but small session → `😌 Clean & quiet`
- Had failures but recovered → `💪 Hard-fought win`
- Had failures, messy → `🫠 We got there eventually`
- Single quick fix → `🩹 Quick patch`
- Massive output (1000+ lines) → `🏭 Factory floor`
- Mostly docs/config changes → `🧹 Housekeeping`

```
  🎭 VIBE: [mood]
```

### Part 3: The Journey

```
  📜 THE JOURNEY
  [2-4 lines telling the specific story of what happened this session.
   Reference real files, real problems, real solutions.
   If it was a grind, say so. If something clicked, celebrate it.
   Be genuine — not generic summaries.]
```

### Part 4: Commits

List commits in chronological order from `result.metrics.commitLog`.

```
  🔖 COMMITS
     • [short hash] [message]
     • [short hash] [message]
```

### Part 5: Decisions & Learnings

```
  📝 DECISIONS LOGGED
     • [decisions written to STATE.md, or "None this session"]

  🧠 LEARNINGS CAPTURED
     • [learnings written, or "None this session"]
```

### Part 6: The Numbers

Use `result.metrics` for all values. For agents spawned, count how many times the Agent tool was invoked during this session (review your own conversation history). Count each `Agent` tool call as 1, regardless of whether it ran in foreground or background.

```
══════════════════════════════════════════════
  📊 THE NUMBERS
══════════════════════════════════════════════

     🔖 [X] commits        📁 [X] files changed
     📏 +[X] / -[Y] lines  📋 [X] steps completed
     ⏱️ [sessionDuration] session time
     🤖 [X] agents spawned

══════════════════════════════════════════════
```

### Part 7: Session Timeline

Use `result.metrics.commitLog` for commit times and messages. Read `.tmp/.session-start` for the start time.

```
  ⏱️ SESSION TIMELINE
  ┌───────┬──────────────────────────────────────────────┬──────┬──────┐
  │ 20:30 │ Session started                              │      │      │
  │ 20:44 │ Add feature showcase page (v0.13.4)          │  14m │  70% │
  │ 20:50 │ Update session stats                         │   6m │  30% │
  ├───────┴──────────────────────────────────────────────┼──────┼──────┤
  │                                               Total │  20m │ 100% │
  └─────────────────────────────────────────────────────┴──────┴──────┘
```

Rules:
- First row is always "Session started" with the local time from `.tmp/.session-start`.
- Each subsequent row: local time of the commit, commit message, minutes since the previous event (right-aligned), and percentage of total session time (right-aligned).
- Total at bottom: minutes from session start to now, and 100%.
- If `.tmp/.session-start` doesn't exist, skip this section and print: `⏱️ No session timeline — start with /crack-on or /stand-up`.

### Part 8: Last 10 Days Leaderboard

Use `result.leaderboard` (already consolidated per day, 10 entries). Mark today's row with `*`. Days with null commits show `--`.

```
  📋 LAST 10 DAYS
  ┌────────────┬──────────────┬────────────────┬─────────────────────────┐
  │ Date       │ Commits/Lines│ Model          │ Title                   │
  ├────────────┼──────────────┼────────────────┼─────────────────────────┤
  │ 02/03 *    │   4 / +146   │ Opus 4.6 / hi  │ THE BLUEPRINT OFFENSIVE │
  │ 01/03      │  18 / +1297  │ Opus 4.6 / hi  │ THE LAST CARD (+5 more) │
  │ 28/02      │  59 / +2627  │ Sonnet 4.6 / md│ THE VERSION WARS (+8)   │
  │ 27/02      │           -- │ --             │ --                      │
  │ ...        │              │                │                         │
  └────────────┴──────────────┴────────────────┴─────────────────────────┘
```

Always include the header row and separator. Adapt column widths to fit content. Model column shows `[name] / [thinking]` abbreviated: hi = high, md = medium, lo = low. Use the model and thinking level from the current session for today's row. For past days, pull from `stats.json` `recentSessions` if available, otherwise show `--`.

### Part 9: System Checks & Footer

Show audit results and DOE Kit sync status in a bordered block. **Generate this box programmatically** — collect all content lines, compute `W = max(len(l) for l in lines) + 4`, define `line(c)` as `f"│  {c}".ljust(W + 1) + "│"`, then pass ALL rows through `line()` — never construct `f"│{...}│"` manually. Never hand-pad this box.

Rules:
- Always show both Audit and DOE Kit lines inside the border.
- If audit has only PASS results, show one line with counts and "all clear".
- If audit has WARN or FAIL, show summary line + indented detail for each non-PASS finding.
- DOE Kit: Show kit's latest tag. `vX.Y.Z *` if either kit tag is newer than STATE.md's version or any syncable files differ (the `*` means `/sync-doe` or `/pull-doe` needed). `vX.Y.Z` if neither. If `~/doe-starter-kit` doesn't exist, show `DOE Kit: not installed`.

Example content lines (padding is illustrative — real padding must be computed):
- `  Audit:   5 PASS, 0 WARN, 0 FAIL -- all clear`
- `  DOE Kit: v1.3.0`
- `    FAIL  HTML file is v0.15.0 but STATE.md says v0.15.1`
- `    WARN  learnings.md -- 2 minor versions behind`

Then the footer:
```
════════════════════════════════════════════════════════════════
  STATE.md ✅ | todo.md ✅ | stats.json ✅ | Committed ✅
  Session [N] · 🔥 Day [streak] · Lifetime: [Y] commits
════════════════════════════════════════════════════════════════

  🎯 NEXT UP
  [What to do next session — pull from todo.md]
```

## Important Rules

- Pull ALL numbers from the wrap_stats.py JSON output. Never estimate or make up stats.
- The Journey section must be genuine — reference specific things that happened.
- Title card must reference specific files, features, or data from this session.
- If stats.json doesn't exist yet, this is session 1. Don't make a big deal about firsts.
- Commit stats.json BEFORE printing the wrap-up so the push includes it.
- Model info is shown in the LAST 10 DAYS leaderboard table, not the footer.
- **Box-drawing alignment:** Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside the `│` borders must be ASCII-only: no emojis, no Unicode symbols (no `·`, `✓`, `⚠️`, `—`, `…`). Use ASCII equivalents: commas for separators, `--` for dashes, `ok`/`all clear` for checkmarks. Emojis are fine in section headers OUTSIDE the box. **Generate boxes programmatically** — use a Python snippet with `.ljust(W)` to pad content lines to the exact inner width. Never hand-pad bordered output. If a commit message contains non-ASCII characters, replace them with ASCII equivalents before placing in a box.
