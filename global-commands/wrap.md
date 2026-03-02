Before ending this session, complete all steps in order.

## Step 1: Housekeeping

1. **Update STATE.md** — Write the current position, any decisions made, blockers found, and a 1-2 sentence summary under Last Session.
2. **Update tasks/todo.md** — Make sure all completed steps have timestamps. Move any completed features to Done if needed.
3. **Check for learnings** — If anything failed and was fixed, or a useful pattern was discovered, log it to learnings.md or ~/.claude/CLAUDE.md.
4. **Commit and push** — Make sure all work is committed. No uncommitted changes should remain.
5. **DOE Kit sync check** — If `~/doe-starter-kit` exists, quick-diff key syncable files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) against the starter kit. If any files have changed since the last sync (especially if new universal learnings were added to `~/.claude/CLAUDE.md` this session), record the count for the System Checks section. If everything is synced, record as synced.
6. **Quick audit** — Run `python3 execution/audit_claims.py --hook` (fast checks only). Record the PASS/WARN/FAIL counts for the System Checks section. If any FAIL items exist, fix them before proceeding. WARN items can be noted and left for the next session.

## Step 2: Compute Session Stats

Find the first commit of this session: look at `git log --oneline` and identify where your work started (after the last "Update session stats" or "wrap" commit, or use the session start time from `.tmp/.session-start`).

Read `.tmp/.session-start` for the session start ISO timestamp. If it doesn't exist, use the first commit time.

**Also record from your session context** (the script can't know these):
- `failures`: how many things broke during the session
- `recoveries`: how many failures were fixed

Run the scoring script:
```bash
python3 execution/wrap_stats.py \
  --since <first-session-commit-hash> \
  --session-start <ISO-timestamp-from-.tmp/.session-start> \
  --todo tasks/todo.md \
  --stats .claude/stats.json
```

This script:
- Gathers all git metrics (commits, lines, files, commit log)
- Counts steps completed from todo.md
- Reads and updates .claude/stats.json (streak, multiplier, score, badges, leaderboard)
- Outputs a JSON blob to stdout with all computed values

Parse the JSON output. The key fields you need for display:

```
result.metrics      → commits, linesAdded, linesRemoved, filesTouched, stepsCompleted,
                      learningsLogged, sessionDuration, commitLog, featureCompleted
result.scoring      → rawScore, multiplier, finalScore, streak, isHighScore, previousBest
result.badges       → array of badge names earned this session
result.genre        → genre key for title card selection
result.mood         → mood key for vibe check
result.todaySessions → previous sessions from today (for Today's Sessions section)
result.leaderboard  → 10-entry consolidated leaderboard
result.stats        → the full updated stats.json
```

**Note:** The script defaults `failures` and `recoveries` to 0. If you recorded session failures/recoveries above, override these values when displaying The Numbers and use them for badge evaluation (PHOENIX, ZERO DEFECT). The script already handles all other badge logic including once-per-day deduplication.

Commit stats.json with message: "Update session stats".

## Step 3: Print Session Wrap-Up

Build the full wrap-up and print it as one block. Use the script's JSON output for all numbers.

### Part 1: Title Card

Use `result.genre` to pick the format. Check top-to-bottom (first match wins):

1. **Star Wars Crawl** (`star_wars`) — Format:

```
          ╔══════════════════════════════════════╗
          ║                                      ║
          ║   [P R O J E C T   N A M E]           ║
          ║                                      ║
          ║   Episode [N]: [TITLE IN CAPS]       ║
          ║                                      ║
          ╚══════════════════════════════════════╝

  [Dramatic opening line about the state of the codebase.]
  [Line referencing what was actually built this session.]
  [Line referencing specific challenges or data wrangled.]
  [Line about what lies ahead, trailing off into the distance...]
```

Episode N = `result.stats.lifetime.totalSessions`. Title and crawl text MUST reference the actual feature, real files, and real problems from this session. Be melodramatic.

2. **Noir Detective** (`noir`) — `"THE CASE OF THE [SPECIFIC THING]"` + 1-2 lines of hardboiled narration referencing actual errors.
3. **Heist Movie** (`heist`) — `"THE [FEATURE] JOB"` + crew-assembled vibe.
4. **Epic Fantasy** (`fantasy`) — `"THE SAGA OF [FEATURE]"` + quest narrative.
5. **Haiku** (`haiku`) — Write a genuine 5-7-5 haiku about the specific change made.
6. **Horror** (`horror`) — `"THE PURGE OF [WHAT WAS REMOVED]"`.
7. **Short Film** (`short_film`) — One punchy cinematic line.
8. **War Film** (`war`) — `"OPERATION [FEATURE]"` + multi-front campaign tone.
9. **Sports Movie** (`sports`) — Rocky-style comeback narrative.
10. **Action Movie** (`action`) — `"[FEATURE]: THE SESSION"`.

CRITICAL: Always reference specific files, functions, features, or data from the session. Never use generic titles or descriptions.

### Part 2: The Numbers

Use `result.metrics` for all values.

```
══════════════════════════════════════════════
  📊 THE NUMBERS
══════════════════════════════════════════════

     🔖 [X] commits        📁 [X] files changed
     📏 +[X] / -[Y] lines  📋 [X] steps completed
     💥 [X] failures → [X] fixed
     🧠 [X] learnings logged
     ⏱️ [sessionDuration] total session time

══════════════════════════════════════════════
```

### Part 2b: Session Timeline

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
- If `.tmp/.session-start` doesn't exist, skip this entire section and print: `⏱️ No session timeline — start with /crack-on or /stand-up`.

### Part 3: Badges Earned

Use `result.badges` for the list. Only show if at least one badge was earned. Display each badge as a bordered card:

```
  🏆 BADGES EARNED
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │     🧱      │  │     🏃      │  │     🏁      │
  │ BRICKLAYER  │  │  SPEEDRUN   │  │   CLOSER    │
  │  500+ lines │  │   3+ steps  │  │ feature done│
  └─────────────┘  └─────────────┘  └─────────────┘
```

Badge emoji and label reference:

| Badge | Emoji | Card label |
|-------|-------|------------|
| BRICKLAYER | 🧱 | 500+ lines |
| NOVELIST | 📖 | 1000+ lines |
| MACHINE GUN | 🔫 | 15+ commits |
| OCTOPUS | 🐙 | 8+ files |
| SURGICAL | 🎯 | <20 lines |
| SNIPER | 🔭 | 1 commit 1 file |
| DEMOLITION | 💣 | net negative |
| SPEEDRUN | 🏃 | 3+ steps |
| CLOSER | 🏁 | feature done |
| FIRST BLOOD | 💀 | new feature |
| PHOENIX | 🔥 | fail → fix |
| SCHOLAR | 🎓 | 3+ learnings |
| STREAK×3 | 🔥 | 3 day streak |
| STREAK×7 | ⚡ | 7 day streak |
| CENTURION | 💯 | 10+ sessions |
| HIGH ROLLER | 🏆 | new high score |
| NIGHT OWL | 🌙 | after midnight |
| EARLY BIRD | 🌅 | before 7am |
| MARATHON | ⏱️ | 4+ hour session |
| ZERO DEFECT | ✨ | flawless 5+ |

### Part 4: Session Score

Use `result.scoring` for all values.

If `result.scoring.isHighScore`:
```
  ⚡ SESSION SCORE
  ┌─────────────┬─────────────┬─────────────┐
  │ Score       │ Multiplier  │ Final       │
  ├─────────────┼─────────────┼─────────────┤
  │  [raw] pts  │ [mult]x d[N]│ [final] pts │
  ├─────────────┴─────────────┴─────────────┤
  │  🎆 NEW HIGH SCORE!                     │
  │  Previous: [old] pts ([date] — "[title]")│
  └─────────────────────────────────────────┘
```

If NOT high score:
```
  ⚡ SESSION SCORE
  ┌─────────────┬─────────────┬─────────────┐
  │ Score       │ Multiplier  │ Final       │
  ├─────────────┼─────────────┼─────────────┤
  │  [raw] pts  │ [mult]x d[N]│ [final] pts │
  ├─────────────┴─────────────┴─────────────┤
  │  Best: [score] pts ([date] — "[title]") │
  └─────────────────────────────────────────┘
```

Column rules: Score = rawScore, Multiplier = "[mult]x d[streak]" (e.g. "1.5x d5"), Final = finalScore. Adapt column widths to fit content. The bottom row spans all columns.

### Part 5a: Today's Sessions

Use `result.todaySessions`. Show all sessions from today individually, newest first. If there's only one session today (this one), skip this section entirely.

```
  📋 TODAY'S SESSIONS
  ┌─────────────────────────────┬───────┬──────────────────────┐
  │  1.  THE AUDIT AWAKENS      │   450 │ 🧱🐙🏃🏁💀✨       │
  │  2.  THE GOVERNANCE DIR...  │   390 │ 🐙🏃🏁💀🎓✨       │
  ├─────────────────────────────┼───────┼──────────────────────┤
  │  TODAY'S TOTAL              │  2100 │ 5 sessions           │
  └─────────────────────────────┴───────┴──────────────────────┘
```

### Part 5b: Last 10 Days Leaderboard

Use `result.leaderboard` (already consolidated per day, 10 entries). Mark today's row with `*`. Days with null score show `--`.

```
  📋 LAST 10 DAYS
  ┌────────────┬───────┬────────┬──────────────────────────────┐
  │ 02/03 *    │  2100 │  day 3 │ THE VERSION WARS (+4 more)   │
  │ 01/03      │   869 │  day 2 │ THE LAST CARD (+5 more)      │
  │ 28/02      │  2435 │  day 1 │ THE VERSION WARS (+11 more)  │
  │ 27/02      │    -- │     -- │ --                           │
  │ ...        │       │        │                              │
  └────────────┴───────┴────────┴──────────────────────────────┘
```

### Part 6: Diff of the Day

Pick the most interesting change from the session. Priority: (1) largest new file created, (2) file with most insertions, (3) most complex function written, (4) most satisfying bug fix.

```
  📸 DIFF OF THE DAY
  [filename] ([+X lines] or [stat])
  "[Witty one-liner about this specific change]"
```

### Part 7: Vibe Check

Use `result.mood`:
- `smooth_sailing` → `😎 Smooth sailing`
- `clean_quiet` → `😌 Clean & quiet`
- `hard_fought` → `💪 Hard-fought win`
- `got_there` → `🫠 We got there eventually`
- `quick_patch` → `🩹 Quick patch`
- `factory_floor` → `🏭 Factory floor`
- `housekeeping` → `🧹 Housekeeping`

```
  🎭 VIBE: [mood]
```

### Part 8: The Journey

```
  📜 THE JOURNEY
  [2-4 lines telling the specific story of what happened this session.
   Reference real files, real problems, real solutions.
   If it was a grind, say so. If something clicked, celebrate it.
   Be genuine — not generic summaries.]
```

### Part 9: Commits

List commits in chronological order from `result.metrics.commitLog`.

```
  🔖 COMMITS
     • [short hash] [message]
     • [short hash] [message]
```

### Part 10: Decisions & Learnings

```
  📝 DECISIONS LOGGED
     • [decisions written to STATE.md, or "None this session"]

  🧠 LEARNINGS CAPTURED
     • [learnings written, or "None this session"]
```

### Part 11: Next Up

```
  🎯 NEXT UP
  [What to do next session — pull from todo.md]
```

### Part 12: System Checks & Footer

Show audit results and DOE Kit sync status in a bordered block, then the session summary line.

If all clear:
```
  🔍 SYSTEM CHECKS
  ┌──────────────────────────────────────────────────────────┐
  │  Audit:   5 PASS · 0 WARN · 0 FAIL ✓                   │
  │  DOE Kit: v1.3.0 · synced ✓                             │
  └──────────────────────────────────────────────────────────┘
```

If issues found, expand with detail lines:
```
  🔍 SYSTEM CHECKS
  ┌──────────────────────────────────────────────────────────┐
  │  Audit:   3 PASS · 1 WARN · 1 FAIL ⚠️                   │
  │    FAIL  HTML file is v0.15.0 but STATE.md says v0.15.1 │
  │    WARN  learnings.md — 2 minor versions behind         │
  │  DOE Kit: v1.3.0 · 2 files changed — /sync-doe ⚠️       │
  └──────────────────────────────────────────────────────────┘
```

Rules:
- Always show both Audit and DOE Kit lines inside the border.
- If audit has only PASS results, show one line with counts + ✓.
- If audit has WARN or FAIL, show summary line + indented detail for each non-PASS finding.
- DOE Kit line: show `synced ✓` if all files match, or `N files changed — /sync-doe ⚠️` if any differ. If `~/doe-starter-kit` doesn't exist, show `DOE Kit: not installed` (no warning).

Then the session summary (outside the border):
```
══════════════════════════════════════════════
  STATE.md ✅ | todo.md ✅ | stats.json ✅ | Committed ✅
  Session [N] | Streak: [X] days | Lifetime: [Y] commits
══════════════════════════════════════════════
```

## Important Rules

- Pull ALL numbers from the wrap_stats.py JSON output. Never estimate or make up stats.
- The Journey section must be genuine — reference specific things that happened.
- Title card must reference specific files, features, or data from this session.
- If stats.json doesn't exist yet, this is session 1 — everything is a new high score by default. Don't make a big deal about it being a "high score" on session 1.
- Commit stats.json BEFORE printing the wrap-up so the push includes it.
- Badge cards must be centre-aligned and use the exact box-drawing characters shown.
