Read STATE.md and tasks/todo.md. Run `git log --oneline` to see this session's commits (look for today's date — commits since the session started). Then output a mid-session situation report in this exact format:

```
┌─────────────────────────────────────────────────┐
│  SITREP · HH:MM - DD/MM/YY                      │
├─────────────────────────────────────────────────┤
│  MISSION   [feature name] [APP/INFRA] vX.Y      │
│  PROGRESS  ██████░░░░ N/M steps                  │
│  STATUS    [one-line summary of what's happening] │
│                                                  │
│  DONE                                            │
│  ✓ [completed step name]                         │
│  ✓ [completed step name]                         │
│                                                  │
│  ACTIVE                                          │
│  → [current step name]                           │
│                                                  │
│  PENDING                                         │
│  · [remaining step name]                         │
│                                                  │
│  COMMITS   N this session | X uncommitted        │
│  ELAPSED   Xh Ym since first commit              │
│  CONTEXT   ██████░░░░ ~X% — [recommendation]     │
│  DOE KIT   vX.Y.Z · [synced ✓ / N — /sync-doe]   │
│  BLOCKERS  [any from STATE.md, or "None"]        │
│  QUEUE     [next feature from Queue, or "Empty"] │
└─────────────────────────────────────────────────┘
```

Rules:
- Progress bar: use █ for done steps, ░ for remaining. Scale to 10 characters total.
- STATUS: one plain-English sentence describing what's actually happening right now in the session. This may differ from the MISSION — e.g. you might be debugging, experimenting, or doing housekeeping unrelated to the current feature step. Look at the conversation history to determine this. If work is aligned with the active step, just summarise that step.
- DONE section: list completed steps from the current feature (steps with [x]).
- ACTIVE section: the step currently being worked on (first unchecked step). If nothing is actively being worked on, show "Awaiting next step".
- PENDING section: remaining unchecked steps after the active one. Omit section if none.
- ELAPSED: check if `.tmp/.session-start` exists. If yes, read the ISO timestamp from it and compute the time difference between that timestamp and now. Format as "Xh Ym" (omit hours if 0, e.g. "12m" or "1h 23m"). If the file doesn't exist, fall back to the old method: run `git log --format="%ai" --reverse` and find the first commit of this session (after the last "Update session stats" commit). Compute the time difference between that first commit and now. Format as "Xh Ym since first commit". If neither source is available, show "No timer — start with /crack-on".
- COMMITS: count today's git commits. If you can identify which ones are from this session (by timestamp clustering), use that instead. After the pipe, run `git status --short` and show the count of uncommitted files (e.g. "| 2 uncommitted"). If the working tree is clean, omit the pipe and uncommitted count entirely — just show the commit count.
- DOE KIT: if `~/doe-starter-kit` exists, run `git describe --tags --abbrev=0` to get the version. Quick-diff key syncable files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many differ. Show `vX.Y.Z · synced ✓` if clean, or `vX.Y.Z · N pending — consider /sync-doe` if any files differ. If the directory doesn't exist, omit this line entirely.
- BLOCKERS: pull from STATE.md ## Blockers & Edge Cases. "None" if empty.
- QUEUE: first feature from ## Queue in todo.md. "Empty" if nothing queued.
- If no feature is in ## Current, show MISSION as "No active feature" and skip DONE/ACTIVE/PENDING. Just show commits, blockers, and queue.
- CONTEXT: estimate your current context window usage as a percentage. Show the percentage and a recommendation: under 60% = "Plenty of room", 60-80% = "Consider /clear soon", over 80% = "Compact or /clear".
- BORDER: size the box to fit the longest content line. All lines must be padded with spaces to match that width so the right border │ aligns consistently. Never let any line break the right border. Double-check every line has the same total character count before outputting.
- Do not execute anything. This is read-only.
