As your very first action, start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start` — this timestamps when the session began.

**Model check:** Before reading project files, display your current model and thinking configuration: `💻 [Model] · 🧠 [Thinking: low/medium/high]`. Map model IDs to display names: `claude-opus-4-6` → "Opus 4.6", `claude-sonnet-4-6` → "Sonnet 4.6", `claude-haiku-4-5` → "Haiku 4.5". For thinking level, report your reasoning effort: ≤33 → "low", 34-66 → "medium", ≥67 → "high". If uncertain, show "default". This lets the user switch models before committing to work.

Then read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md. Show me what's in progress and what's next.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version. Check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (2) Do any key syncable files differ? If either is true: show `DOE Kit: vX.Y.Z *` (run `/sync-doe` or `/pull-doe`). If neither: show `DOE Kit: vX.Y.Z`. If the directory doesn't exist, skip silently.

Pick up from the next incomplete step. One step at a time — commit, push, then stop and show me what you did.
