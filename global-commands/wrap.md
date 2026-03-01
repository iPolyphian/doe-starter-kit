Before ending this session, complete all steps in order.

## Step 1: Housekeeping

1. **Update STATE.md** — Write the current position, any decisions made, blockers found, and a 1-2 sentence summary under Last Session.
2. **Update tasks/todo.md** — Make sure all completed steps have timestamps. Move any completed features to Done if needed.
3. **Check for learnings** — If anything failed and was fixed, or a useful pattern was discovered, log it to learnings.md or ~/.claude/CLAUDE.md.
4. **Commit and push** — Make sure all work is committed. No uncommitted changes should remain.
5. **DOE Kit sync check** — If `~/doe-starter-kit` exists, quick-diff key syncable files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) against the starter kit. If any files have changed since the last sync (especially if new universal learnings were added to `~/.claude/CLAUDE.md` this session), add a nudge line at the end of the housekeeping output: `💡 [N] DOE files changed since last sync — consider running /sync-doe`. If everything is synced, skip silently.

## Step 2: Gather Session Metrics

Run these commands and record the results internally (do NOT print them yet):

- Find the first commit of this session. Look at `git log --oneline` and identify where your work started (after the last "wrap" or "session" commit, or use the session start time).
- `git log --oneline <first-session-commit>^..HEAD` — count commits this session
- `git diff --shortstat <first-session-commit>^..HEAD` — insertions, deletions, files changed
- `git diff --stat <first-session-commit>^..HEAD` — per-file breakdown
- Check `tasks/todo.md` for `[x]` items timestamped today — count steps completed
- Count learnings you logged this session (if any)
- Recall how many failures occurred and how many were recovered
- Check if a feature was fully completed (all steps checked off)
- Check commit timestamps for time-of-day badges

Record these values:
- `commits`: number of commits
- `linesAdded`: total insertions
- `linesRemoved`: total deletions
- `filesTouched`: number of files changed
- `stepsCompleted`: todo steps completed today
- `learningsLogged`: learnings added this session
- `failures`: things that broke
- `recoveries`: failures that were fixed
- `featureCompleted`: boolean
- `firstCommitTime` / `lastCommitTime`: timestamps of first and last commit

## Step 3: Read and Update Stats

Read `.claude/stats.json`. If it doesn't exist or fails to parse as valid JSON, back up the broken file to `.claude/stats.json.bak` and create a fresh one with this structure:

```json
{
  "version": 1,
  "lifetime": {
    "totalSessions": 0,
    "totalCommits": 0,
    "totalLinesAdded": 0,
    "totalLinesRemoved": 0,
    "totalFilesTouched": 0,
    "totalStepsCompleted": 0,
    "totalLearningsLogged": 0,
    "totalBadgesEarned": 0,
    "firstSessionDate": null
  },
  "streak": {
    "current": 0,
    "best": 0,
    "lastSessionDate": null
  },
  "highScores": {
    "bestSessionScore": 0,
    "bestSessionDate": null,
    "bestSessionTitle": null,
    "bestRawScore": 0,
    "bestMultiplier": 1.0
  },
  "badges": { "allTimeEarned": {} },
  "recentSessions": []
}
```

### Compute Streak

- `lastSessionDate` is null → streak = 1
- `lastSessionDate` is today → streak stays the same (don't double-count)
- `lastSessionDate` is yesterday → streak = current + 1
- `lastSessionDate` is 2+ days ago → streak = 1
- Update `streak.best` if `streak.current` exceeds it

### Compute Multiplier (slow ramp)

Interpolate linearly between these milestones:

| Streak | Multiplier |
|--------|-----------|
| 1 day  | 1.0x |
| 2 days | 1.1x |
| 3 days | 1.2x |
| 4 days | 1.3x |
| 5 days | 1.5x |
| 7 days | 1.75x |
| 10 days | 2.0x |
| 14 days | 2.5x |
| 21+ days | 3.0x (cap) |

For days between milestones, interpolate linearly. E.g. day 6 = 1.5 + (1.75 - 1.5) / (7 - 5) × (6 - 5) = 1.625x.

### Compute Score

```
rawScore = (commits × 10)
         + floor(linesAdded / 100) × 15
         + floor(linesRemoved / 100) × 10
         + (filesTouched × 5)
         + (stepsCompleted × 25)
         + (learningsLogged × 20)
         + (recoveries × 15)
         + (featureCompleted ? 50 : 0)

finalScore = floor(rawScore × multiplier)
```

### Award Badges

Check each condition. Only award badges that are earned THIS session:

| Badge | Emoji | Condition | Card label |
|-------|-------|-----------|------------|
| BRICKLAYER | 🧱 | linesAdded >= 500 | 500+ lines |
| NOVELIST | 📖 | linesAdded >= 1000 | 1000+ lines |
| MACHINE GUN | 🔫 | commits >= 15 | 15+ commits |
| OCTOPUS | 🐙 | filesTouched >= 8 | 8+ files |
| SURGICAL | 🎯 | linesAdded + linesRemoved < 20 | <20 lines |
| SNIPER | 🔭 | commits == 1 AND filesTouched == 1 | 1 commit 1 file |
| DEMOLITION | 💣 | linesRemoved > linesAdded | net negative |
| SPEEDRUN | 🏃 | stepsCompleted >= 3 | 3+ steps |
| CLOSER | 🏁 | featureCompleted == true | feature done |
| FIRST BLOOD | 💀 | first step of a new feature completed | new feature |
| PHOENIX | 🔥 | failures >= 1 AND recoveries >= failures | fail → fix |
| SCHOLAR | 🎓 | learningsLogged >= 3 | 3+ learnings |
| STREAK×3 | 🔥 | streak.current >= 3 | 3 day streak |
| STREAK×7 | ⚡ | streak.current >= 7 | 7 day streak |
| CENTURION | 💯 | lifetime.totalSessions + 1 >= 10 | 10+ sessions |
| HIGH ROLLER | 🏆 | finalScore > highScores.bestSessionScore | new high score |
| NIGHT OWL | 🌙 | any commit between 00:00–05:00 local | after midnight |
| EARLY BIRD | 🌅 | any commit between 05:00–07:00 local | before 7am |
| MARATHON | ⏱️ | lastCommitTime - firstCommitTime >= 4 hours | 4+ hour session |
| ZERO DEFECT | ✨ | failures == 0 AND commits >= 5 | flawless 5+ |

### Check High Score

If `finalScore > highScores.bestSessionScore`, flag as new high score. Record the old values before overwriting so you can display "previous best".

### Update stats.json

- Increment all `lifetime` counters with this session's values
- Set `lifetime.firstSessionDate` if null
- Set `streak.lastSessionDate` to today
- Update `highScores` if beaten
- Increment `badges.allTimeEarned` counts for each earned badge
- Prepend this session to `recentSessions` (keep max 20, drop oldest). Each entry:

```json
{
  "date": "YYYY-MM-DD",
  "title": "Session Title",
  "commits": 0,
  "linesAdded": 0,
  "linesRemoved": 0,
  "filesTouched": 0,
  "stepsCompleted": 0,
  "rawScore": 0,
  "multiplier": 1.0,
  "finalScore": 0,
  "streak": 1,
  "badgesEarned": [],
  "genre": "action",
  "mood": "smooth_sailing",
  "sessionDuration": "Xh Ym"
}
```

For `sessionDuration`: read `.tmp/.session-start` and compute elapsed time from that timestamp to now. Format as "Xh Ym" (omit hours if 0, e.g. "42m" or "1h 15m"). If `.tmp/.session-start` doesn't exist, use the difference between first and last commit timestamps, or "unknown" if no commits.

Write the updated stats.json, then commit it with message: "Update session stats".

## Step 4: Print Session Wrap-Up

Build the full wrap-up and print it as one block. Use the structure below.

### Part 1: Title Card

Pick the genre by checking these conditions top-to-bottom (first match wins):

1. **Star Wars Crawl** — if featureCompleted OR linesAdded >= 500 OR commits >= 10 OR a version bump commit exists this session. Format:

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

Episode N = lifetime.totalSessions from stats. Title and crawl text MUST reference the actual feature, real files, and real problems from this session. Be melodramatic.

2. **Noir Detective** — failures >= 3 AND recoveries >= 2. Format: `"THE CASE OF THE [SPECIFIC THING]"` + 1-2 lines of hardboiled narration referencing actual errors.
3. **Heist Movie** — stepsCompleted >= 3 AND failures == 0. Format: `"THE [FEATURE] JOB"` + crew-assembled vibe.
4. **Epic Fantasy** — linesAdded >= 800. Format: `"THE SAGA OF [FEATURE]"` + quest narrative.
5. **Haiku** — linesAdded + linesRemoved < 20. Write a genuine 5-7-5 haiku about the specific change made.
6. **Horror** — linesRemoved > linesAdded. Format: `"THE PURGE OF [WHAT WAS REMOVED]"`.
7. **Short Film** — commits == 1. One punchy cinematic line.
8. **War Film** — filesTouched >= 8. Format: `"OPERATION [FEATURE]"` + multi-front campaign tone.
9. **Sports Movie** — failures >= 1 AND recoveries >= 1. Rocky-style comeback narrative.
10. **Action Movie** — default fallback. `"[FEATURE]: THE SESSION"`.

CRITICAL: Always reference specific files, functions, features, or data from the session. Never use generic titles or descriptions.

### Part 2: The Numbers

```
══════════════════════════════════════════════
  📊 THE NUMBERS
══════════════════════════════════════════════

     🔖 [X] commits        📁 [X] files changed
     📏 +[X] / -[Y] lines  📋 [X] steps completed
     💥 [X] failures → [X] fixed
     🧠 [X] learnings logged
     ⏱️ [Xh Ym] total session time

══════════════════════════════════════════════
```

For the ⏱️ line: read `.tmp/.session-start` for the session start time. Compute duration from that timestamp to now. Format as "Xh Ym" (omit hours if 0). If the file doesn't exist, show "⏱️ No timer — start with /crack-on".

### Part 2b: Session Timeline

Show after The Numbers. Read `.tmp/.session-start` for the start time. List every commit from this session in chronological order, showing local time and minutes elapsed since the previous event.

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
- Use `git log --format="%ai %s" --reverse` to get commit times and messages for this session.

### Part 3: Badges Earned

Only show if at least one badge was earned. Display each badge as a bordered card. Arrange in a horizontal row, 3-4 per line, wrapping to the next line if more:

```
  🏆 BADGES EARNED
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │     🧱      │  │     🏃      │  │     🏁      │
  │ BRICKLAYER  │  │  SPEEDRUN   │  │   CLOSER    │
  │  500+ lines │  │   3+ steps  │  │ feature done│
  └─────────────┘  └─────────────┘  └─────────────┘
```

The card label (bottom line) should be the short trigger description from the badge table. Centre-align text within each card.

### Part 4: Session Score

Display as a bordered box. Adapt the width to fit the longest content line.

If new high score:
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

If NOT new high score:
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

Column rules: Score = raw score, Multiplier = "[mult]x d[streak]" (e.g. "1.5x d5"), Final = raw × multiplier. Adapt column widths to fit content. The bottom row spans all columns for the high score / personal best line.

### Part 5a: Today's Sessions

Show all sessions from today individually, newest first. Pull from `recentSessions` where date matches today. If there's only one session today (this one), skip this section entirely — the leaderboard covers it.

```
  📋 TODAY'S SESSIONS
  ┌─────────────────────────────┬───────┬──────────────────────┐
  │  1.  THE AUDIT AWAKENS      │   450 │ 🧱🐙🏃🏁💀✨       │
  │  2.  THE GOVERNANCE DIR...  │   390 │ 🐙🏃🏁💀🎓✨       │
  │  3.  THE VERSION WARS       │   825 │ 🧱🔫🐙🏃🏁💣🔥🏆🌙│
  │  4.  Five Tiny Commands     │    35 │ 🎯🌙               │
  │  5.  THE GAMIFICATION WARS  │   400 │ 🧱🐙🔥🎓🏆🌙      │
  ├─────────────────────────────┼───────┼──────────────────────┤
  │  TODAY'S TOTAL              │  2100 │ 5 sessions           │
  └─────────────────────────────┴───────┴──────────────────────┘
```

The total row sums all session scores for today. Badge column shows emoji-only (no labels) for compactness.

### Part 5b: Last 10 Days Leaderboard

Always show exactly 10 rows — today plus the 9 preceding days. **Consolidate by date**: group all `recentSessions` entries with the same date into one row per day.

**Per-day consolidation rules:**
- **Score**: sum of all session scores for that day
- **Streak**: use the streak value from the latest session that day
- **Title**: if 1 session, use its title. If 2+, use the highest-scoring session's title + ` (+N more)` where N is the number of additional sessions. E.g. `THE VERSION WARS (+4 more)`

Days with no session entry show `--` for all fields. Mark today's row with `*`.

```
  📋 LAST 10 DAYS
  ┌────────────┬───────┬────────┬──────────────────────────────┐
  │ 28/02 *    │  2100 │  day 1 │ THE VERSION WARS (+4 more)   │
  │ 27/02      │    -- │     -- │ --                           │
  │ 26/02      │    -- │     -- │ --                           │
  │ 25/02      │    -- │     -- │ --                           │
  │ 24/02      │    -- │     -- │ --                           │
  │ 23/02      │    -- │     -- │ --                           │
  │ 22/02      │    -- │     -- │ --                           │
  │ 21/02      │    -- │     -- │ --                           │
  │ 20/02      │    -- │     -- │ --                           │
  │ 19/02      │    -- │     -- │ --                           │
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

Pick the best matching mood:
- 0 failures, 5+ commits → `😎 Smooth sailing`
- 0 failures, < 5 commits → `😌 Clean & quiet`
- failures > 0, all recovered → `💪 Hard-fought win`
- failures > 0, some unresolved → `🫠 We got there eventually`
- 1 failure, 1 fix, small session → `🩹 Quick patch`
- 1000+ lines added → `🏭 Factory floor`
- Mostly config/docs changes → `🧹 Housekeeping`

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

List commits in chronological order (oldest first, newest last).

```
  🔖 COMMITS
     • [short hash] [message]
     • [short hash] [message]
     • ...
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

### Part 12: Footer

```
══════════════════════════════════════════════
  STATE.md ✅ | todo.md ✅ | stats.json ✅ | Committed ✅
  Session [N] | Streak: [X] days | Lifetime: [Y] commits
  DOE Kit: vX.Y.Z · [synced ✓ / N pending — /sync-doe]
══════════════════════════════════════════════
```

The DOE Kit line uses the same check as step 5 (housekeeping). If `~/doe-starter-kit` doesn't exist, omit the line. Show `synced ✓` if all syncable files match, or `N pending — /sync-doe` if any differ.

## Important Rules

- Pull ALL numbers from git commands. Never estimate or make up stats.
- The Journey section must be genuine — reference specific things that happened.
- Title card must reference specific files, features, or data from this session.
- If stats.json doesn't exist yet, this is session 1 — everything is a new high score by default. Don't make a big deal about it being a "high score" on session 1.
- Commit stats.json BEFORE printing the wrap-up so the push includes it.
- Badge cards must be centre-aligned and use the exact box-drawing characters shown.
