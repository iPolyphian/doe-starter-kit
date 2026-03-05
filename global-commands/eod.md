End-of-day report aggregating all sessions, commits, features, and position. Answers "what did I do today?"

This is a read-only summary command. Do NOT modify any files or start/stop sessions.

## Data Gathering

Collect all of the following before building the card:

1. **Today's sessions** — Read `.claude/stats.json` and filter `recentSessions` where `date` matches today (YYYY-MM-DD). Count wrapped sessions. Check if `.tmp/.session-start` exists — if it does, there is one active unwrapped session.

2. **Today's commits** — Run `git log --oneline --since="$(date +%Y-%m-%d)T00:00:00"` to get all commits from today. Also run `git diff --shortstat $(git log --reverse --since="$(date +%Y-%m-%d)T00:00:00" --format="%H" | head -1)^..HEAD` for total lines/files (handle edge case where there's only one commit today — use the commit itself, not commit^).

3. **Steps completed today** — Read `tasks/todo.md` and count `[x]` items with timestamps containing today's date (DD/MM/YY format).

4. **Features completed today** — Check `tasks/todo.md` ## Done for features with completion timestamps matching today.

5. **Current position** — Read `STATE.md` for active feature, blockers, current version.

6. **Queue** — Read `tasks/todo.md` ## Queue for upcoming features.

7. **Plan files created today** — Run `find .claude/plans/ -name "*.md" -newer .tmp/.session-start 2>/dev/null | wc -l` or check git log for plan file commits today.

8. **Learnings logged today** — Check if `learnings.md` appears in today's commits via `git log --since="$(date +%Y-%m-%d)T00:00:00" --name-only --format="" | grep learnings.md | wc -l`.

## Output Format

Show a single bordered card:

```
┌────────────────────────────────────────────────────────────┐
│  EOD · DD/MM/YY                                             │
├────────────────────────────────────────────────────────────┤
│  SESSIONS  N today (X wrapped, Y active)                    │
│  STREAK    Day N                                            │
│                                                             │
│  DAY STATS                                                  │
│  N commits · N files · +X / -Y lines                        │
│  N features completed · N steps completed                   │
│  N plan files created · N learnings logged                  │
│                                                             │
│  SESSIONS                                                   │
│  1. TITLE                                   duration        │
│  2. TITLE                                   duration        │
│  3. (active)                                duration        │
│                                                             │
│  WHAT GOT DONE                                              │
│  [INFRA] Summary of shipped/completed work                  │
│  [APP]   Summary of planned/built work                      │
│                                                             │
│  POSITION AT EOD                                            │
│  Active: [current feature] — N/M steps done                 │
│  Queue:  [next features in order]                           │
│  Blockers: [from STATE.md or None]                          │
│                                                             │
│  DAY VIBE: [mood + one-liner summary]                       │
└────────────────────────────────────────────────────────────┘
```

## Card Rules

- **SESSIONS:** Count from stats.json `recentSessions` for today + check for active sessions by checking if `.tmp/.session-start` exists. Show "N today (X wrapped)" if no active session, or "N today (X wrapped, 1 active)" if the file exists.
- **STREAK:** From stats.json `streak.current`. Show "Day N".
- **DAY STATS:** Aggregate from git commands. Count commits, files touched, insertions/deletions. Count features completed and steps completed from todo.md. Count plan files from git log. Count learnings from git log.
- **SESSIONS list:** Show each wrapped session from stats.json: title, sessionDuration. If `.tmp/.session-start` exists, show one active session as "(active)" with duration computed from that file's timestamp to now. Newest first.
- **WHAT GOT DONE:** This is the key section. Read all commit messages from today. Group them by feature/task using the headings in todo.md (both ## Current and ## Done). Classify each group as [APP] or [INFRA] using the type tags from todo.md headings. Summarise each group in plain English — describe what actually happened, not raw commit messages. Order: shipped features first, then in-progress features, then housekeeping/planning. If only one type exists, skip the other.
- **POSITION AT EOD:** From STATE.md active feature + todo.md progress (count [x] vs [ ] steps). Queue from todo.md ## Queue (show feature names + type tags). Blockers from STATE.md ## Blockers & Edge Cases ("None" if empty).
- **DAY VIBE:** Pick the best match:
  - All planning, no code → "Architect mode"
  - Lots of code shipped (500+ lines) → "Factory floor"
  - Multiple features completed → "Sprint day"
  - Mostly config/docs changes → "Housekeeping day"
  - Mixed planning + building → "Builder's day"
  - Single focused feature all day → "Deep work"
  - Lots of failures + fixes → "Trench warfare"
  Add a one-liner summary after the vibe label (e.g. "Builder's day — planned INFRA overhaul and shipped 5 command upgrades").
- **BORDER:** Size the box to fit the longest content line. **Generate programmatically** — define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width. ALL rows including the header MUST use this helper — never construct `f"│{...}│"` manually. For headers with right-aligned text: build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`.

## Edge Cases

- **No wrapped sessions today:** Show "0 wrapped" in SESSIONS. DAY STATS still works from git log. SESSIONS list shows only the active session (if any) or "No sessions today".
- **No commits today:** Show "0 commits · 0 files · +0 / -0 lines" in DAY STATS. WHAT GOT DONE says "No commits today."
- **No stats.json:** Show "No stats file — run /wrap to start tracking" for SESSIONS and SCORE. Other sections still work from git.
- **1 session only:** Show the session in the list. No "(+N more)" needed.

## Important Rules

- This is READ-ONLY. Do not modify any files. Do not wrap the current session. Do not update stats.json.
- Pull all numbers from git commands and stats.json. Never estimate.
- WHAT GOT DONE must be semantic — describe what happened in plain English, not raw commit messages.
- Works correctly with 1 session or 10 sessions in a day.
