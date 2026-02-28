First, check if ~/doe-starter-kit is accessible. If not, run: /add-dir ~/doe-starter-kit

Then read directives/starter-kit-sync.md and follow it precisely. The directive covers:

1. Diff all syncable files between this project and ~/doe-starter-kit. If nothing has changed, say "Starter kit is up to date — nothing to sync" and stop.
2. For files that differ, identify which changes are universal DOE improvements vs project-specific content
3. For each changed file, strip ALL project-specific content (names, paths, data, examples) and replace with generic equivalents
4. Show me the diff for each file before applying — wait for my approval
5. Copy approved files to ~/doe-starter-kit/
6. Verify: grep for project-specific references — must return zero results
7. Commit to the starter kit repo with message: "Sync from [project name]: [summary of what changed]"
8. Push to GitHub

Rules:
- Only sync universal DOE improvements. Never sync project-specific tasks, data, plans, or domain content.
- If unsure whether something is universal or project-specific, ask me.
- Show diffs before writing. Don't commit without my sign-off.
- If directives/starter-kit-sync.md doesn't exist, tell me — the starter kit may not be set up yet.
