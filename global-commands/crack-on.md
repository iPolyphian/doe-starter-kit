As your very first action, start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start` — this timestamps when the session began.

Then read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md. Show me what's in progress and what's next.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version. Quick-diff key syncable files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many differ. Show a one-liner: `DOE Kit: vX.Y.Z · synced ✓` or `DOE Kit: vX.Y.Z · N files with pending changes — consider /sync-doe`. If the directory doesn't exist, skip silently.

Pick up from the next incomplete step. One step at a time — commit, push, then stop and show me what you did.
