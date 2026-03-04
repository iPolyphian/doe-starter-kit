Read STATE.md and tasks/todo.md. Run `git log --oneline` to see this session's commits (look for today's date — commits since the session started). Then output a mid-session situation report in this exact format:

```
┌─────────────────────────────────────────────────┐
│  SITREP -- HH:MM - DD/MM/YY      DOE vX.Y.Z     │
├─────────────────────────────────────────────────┤
│  MISSION   [feature name] [APP/INFRA] vX.Y      │
│  PROGRESS  ██████░░░░ N/M steps                  │
│  STATUS    [one-line summary of what's happening] │
│                                                  │
│  ACTIVE                                          │
│  → [current step name]                           │
│                                                  │
│  DONE                                            │
│  ✓ [completed step name]                         │
│  ✓ [completed step name]                         │
│                                                  │
│  UP NEXT                                         │
│  · [remaining step name]                         │
│                                                  │
│  COMPLETED                                       │
│  x [thing done this session]                     │
│                                                  │
│  COMMITS   N this session, pushed | X uncommitted │
│  ELAPSED   Xh Ym since first commit              │
│  CONTEXT   ██████░░░░ ~X% — [recommendation]     │
├─────────────────────────────────────────────────┤
│  Model: [model] · Thinking: [level]             │
└─────────────────────────────────────────────────┘
```

Rules:
- MODEL ROW: Final row of the card, separated by `├──┤`. Shows `Model: [name] · Thinking: [level]`. IMPORTANT: This line is always shorter than other content lines. You MUST pad it with trailing spaces so the right `│` is at the exact same character position as every other `│` in the card. Count the inner width of the longest line, then pad the model row to match. No emojis (they break alignment). Model display names: `claude-opus-4-6` → "Opus 4.6", `claude-sonnet-4-6` → "Sonnet 4.6", `claude-haiku-4-5` → "Haiku 4.5". Thinking level from reasoning effort: ≤33 → "low", 34-66 → "medium", ≥67 → "high". If uncertain, show "default".
- Progress bar: use █ for done steps, ░ for remaining. Scale to 10 characters total.
- STATUS: one plain-English sentence describing what's actually happening right now in the session. This may differ from the MISSION — e.g. you might be debugging, experimenting, or doing housekeeping unrelated to the current feature step. Look at the conversation history to determine this. If work is aligned with the active step, just summarise that step.
- ACTIVE section: the step currently being worked on (first unchecked step). If nothing is actively being worked on, show "Awaiting next step". Shown first.
- DONE section: list completed steps from the current feature (steps with [x]). Shown after ACTIVE. Omit section if none.
- UP NEXT section: remaining unchecked steps after the active one. Show at most 5. If more remain, add a final line: "  . ... and N more". Omit section if none.
- COMPLETED section: everything accomplished this session, whether it's a planned todo step or ad-hoc work. Build the list from session commits (git log) and conversation history. These are concrete deliverables — e.g. "Compressed CLAUDE.md (123 to 89 lines)", "Moved Break Glass to directive", "Updated /sitrep format". Include all work, not just feature steps — if the session was housekeeping, debugging, or exploratory, log those too. STATUS describes what's happening now; COMPLETED is the cumulative record. Omit section if nothing completed yet.
- ELAPSED: check if `.tmp/.session-start` exists. If yes, read the ISO timestamp from it and compute the time difference between that timestamp and now. Format as "Xh Ym" (omit hours if 0, e.g. "12m" or "1h 23m"). If the file doesn't exist, fall back to the old method: run `git log --format="%ai" --reverse` and find the first commit of this session (after the last "Update session stats" commit). Compute the time difference between that first commit and now. Format as "Xh Ym since first commit". If neither source is available, show "No timer — start with /crack-on".
- COMMITS: count today's git commits. If you can identify which ones are from this session (by timestamp clustering), use that instead. After the count, check push status: run `git status -sb` and check if the branch is ahead of the remote. If all pushed: append ", pushed". If N commits not yet pushed: append ", committed" (meaning saved locally but not on GitHub yet). After the pipe, run `git status --short` and show the count of uncommitted files (e.g. "| 2 uncommitted"). If the working tree is clean, omit the pipe and uncommitted count entirely.
- DOE KIT: Shown in the header row, right-aligned. If `~/doe-starter-kit` exists, run `git describe --tags --abbrev=0` to get the version. Quick-diff key syncable files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many differ. If synced: show `DOE vX.Y.Z`. If any files differ: show `DOE vX.Y.Z *` (the `*` means /sync-doe needed). If the directory doesn't exist, omit the kit portion from the header.
- If no feature is in ## Current, show MISSION as "No active feature" and skip DONE/ACTIVE/PENDING. Just show commits and context.
- CONTEXT: estimate your current context window usage as a percentage. Show the percentage and a recommendation: under 60% = "Plenty of room", 60-80% = "Consider /clear soon", over 80% = "Compact or /clear".
- BORDER: **Generate boxes programmatically** — use a Python snippet. Inner width W = 58 (content area between pipes). All content lines: `│` + 2-space indent + content + padding + `│`. After building all content lines, compute W as `max(len(indent + content))` across all lines (minimum 58). If any line exceeds 58 chars, W stretches to fit — never truncate content. Use `.ljust(W + 2)` to pad each line. Border width = W + 2. Never hand-pad. Use Unicode box-drawing (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no `·`, `✓`, `⚠️`, `—`, `…`) — use `--` for separators, commas for lists.
- Do not execute anything except the box-generation snippet. This is otherwise read-only.
