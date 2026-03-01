As your very first action, start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start` — this timestamps when the session began.

Then read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md. Show me what's in progress and what's next.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version, and `git log -1 --format="%ai" $(git describe --tags --abbrev=0)` to get the last release date. Then do a quick count of syncable files that differ between the project and the kit: diff key files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many have changes. Report a one-liner in your stand-up output:

```
DOE Kit: v1.0.0 (released 28/02/26) · 2 files with pending changes — consider /sync-doe
```

If everything is synced, show: `DOE Kit: v1.0.0 (released 28/02/26) · synced ✓`
If files differ, append: `— consider /sync-doe`
If the directory doesn't exist, skip this line entirely — don't mention the kit.

Then present a plan for tackling the next incomplete task — wait for my sign-off before executing anything.
