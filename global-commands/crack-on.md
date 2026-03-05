As your very first action, start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start`

Read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version. Check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (inbound). (2) Do any key syncable files differ? (outbound). Diff key files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many have changes. If either condition is true, show `*` (meaning `/sync-doe` or `/pull-doe` needed). If the directory doesn't exist, skip the DOE Kit line entirely.

Show a bordered kick-off card, then immediately pick up the next incomplete step. One step at a time -- commit, push, then stop and show what you did.

```
┌──────────────────────────────────────────────────┐
│  CRACK ON -- HH:MM - DD/MM/YY          [project]  │
├──────────────────────────────────────────────────┤
│  FEATURE    [active feature] [APP/INFRA] vX.Y.x   │
│  PROGRESS   ██████░░░░ N/M steps                  │
│  DOE KIT    vX.Y.Z [synced / * if pending]        │
│                                                   │
│  PICKING UP Step N -- [step description]          │
│  [1-2 line plain English summary of what you      │
│   are about to do for this step]                  │
│                                                   │
├──────────────────────────────────────────────────┤
│  Model: [model] -- Thinking: [level]             │
└──────────────────────────────────────────────────┘
```

Card rules:
- HEADER ROW: "CRACK ON -- HH:MM - DD/MM/YY" left-aligned, project name right-aligned. Project name is the current directory name + version from STATE.md "Current app version" (e.g. "monty v0.15.1"). If no version in STATE.md, just show the directory name. Build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`.
- MODEL ROW: Final row of the card, separated by `├──┤`. Shows `Model: [name] -- Thinking: [level]`. IMPORTANT: This line is always shorter than other content lines. You MUST pad it with trailing spaces so the right `│` is at the exact same character position as every other `│` in the card. Count the inner width of the longest line, then pad the model row to match. No emojis (they break alignment). You know your model ID from your system prompt (look for "The exact model ID is..."). Display names: `claude-opus-4-6` → "Opus 4.6", `claude-sonnet-4-6` → "Sonnet 4.6", `claude-haiku-4-5` → "Haiku 4.5". For thinking level, report your reasoning effort: ≤33 → "low", 34-66 → "medium", ≥67 → "high". If uncertain, show "default". This helps the user decide if they need to switch models before starting work.
- FEATURE: from STATE.md "Active feature" line. If no active feature, show "No active feature".
- PROGRESS: count [x] and [ ] steps for the current feature in todo.md ## Current. Bar uses `█` for done, `░` for remaining, scaled to 10 characters. If no current feature, omit this line.
- DOE KIT: `vX.Y.Z` if synced, `vX.Y.Z *` if either the kit tag is newer than STATE.md's version or any syncable files differ (the `*` means `/sync-doe` or `/pull-doe` needed). Omit entirely if `~/doe-starter-kit` doesn't exist.
- PICKING UP: the next incomplete step (first `[ ]` line) from todo.md ## Current. Show step number and short description. If all steps complete, show "All steps complete -- ready for retro". If no current feature, omit this line.
- SUMMARY: Immediately after PICKING UP, add 1-2 lines of plain English explaining what you are about to do for this step. Read the step's plan file if one is referenced, or use the step description and todo.md context. Keep it concrete and jargon-free -- e.g. "Creating the reverse sync command so kit updates can flow into projects safely." Not a restatement of the step name -- explain the actual work.
- BORDER: Fixed width -- always 60 `─` characters between `│` borders (62 total per line). All content lines: `│` + 2 spaces + content + trailing spaces + `│` = 62 chars. If content would exceed 56 characters, truncate with `...`. Never dynamically size -- the box is always the same width. **Generate boxes programmatically** -- define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width. ALL rows including headers MUST use this helper -- never construct `f"│{...}│"` manually. Never hand-pad bordered output. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no `·`, `✓`, `⚠️`, `—`, `…`) -- use `--` for separators, commas for lists. Exception: progress bar uses `█` (done) and `░` (remaining) -- these render at fixed width in terminals.

After showing the card, immediately start working on the step shown in PICKING UP. No sign-off needed -- just go.
