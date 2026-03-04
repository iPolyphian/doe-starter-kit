First, check if ~/doe-starter-kit is accessible. If not, run: /add-dir ~/doe-starter-kit

Then read directives/starter-kit-sync.md and follow it precisely. The directive covers:

1. Pull latest from GitHub first — another project may have synced since your last pull
2. Diff all syncable files between this project and ~/doe-starter-kit. If nothing has changed, say "Starter kit is up to date — nothing to sync" and stop.
3. Three-way comparison: show what the starter kit has, what this project has, and the diff. Flag any starter kit content that this project doesn't have (it came from another project — preserve it).
4. For files that differ, identify which changes are universal DOE improvements vs project-specific content
5. Strip ALL project-specific content (names, paths, data, examples) and replace with generic equivalents
6. Create a safety backup (git stash) before writing anything
7. Apply changes surgically — merge improvements in, never replace whole files
8. Show me the exact edits before applying — wait for my approval
9. Verify: grep for project-specific references — must return zero results
10. Update CHANGELOG.md with what changed, bump the version (patch/minor/major)
11. Commit to the starter kit repo with message: "v[X.Y.Z]: Sync from [project] — [summary]"
12. Tag the version, push, push tags, create GitHub release

Rules:
- NEVER replace a file wholesale. Merge additively — add new content, update changed content, preserve existing starter kit content.
- If the starter kit has something this project doesn't, keep it. It came from another project.
- Only sync universal DOE improvements. Never sync project-specific tasks, data, plans, or domain content.
- If unsure whether something is universal or project-specific, ask me.
- Show diffs before writing. Don't commit without my sign-off.
- If directives/starter-kit-sync.md doesn't exist, tell me — the starter kit may not be set up yet.
- Version bumps: patch for fixes/tweaks, minor for new commands/directives/features, major for breaking CLAUDE.md or structure changes.

## Result Summary (REQUIRED)

After completing all steps — or when stopping early because nothing changed — ALWAYS end the sync output with this bordered result box. This is the last thing printed, no exceptions.

Pick the matching status. **Generate boxes programmatically** — use a Python snippet with `.ljust(W)` to pad content lines to the exact inner width. Never hand-pad bordered output. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no Unicode arrows) — use `->` instead of `→`, text labels instead of emoji icons.

**Nothing to sync:**
```
⏭️  NO CHANGES
┌──────────────────────────────────────────────────────┐
│  SYNC RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [1-2 line explanation]                              │
│  Kit: vX.Y.Z (unchanged)                            │
└──────────────────────────────────────────────────────┘
```

**Changes approved and pushed:**
```
✅ SYNCED
┌──────────────────────────────────────────────────────┐
│  SYNC RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [1-2 line summary of what was synced]               │
│  Kit: vX.Y.Z -> vX.Y.Z                              │
└──────────────────────────────────────────────────────┘
```

**User declined proposed changes:**
```
❌ REJECTED
┌──────────────────────────────────────────────────────┐
│  SYNC RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [What was proposed and why it was declined]         │
│  Kit: vX.Y.Z (unchanged)                            │
└──────────────────────────────────────────────────────┘
```

**Blocked by an issue:**
```
⚠️  BLOCKED
┌──────────────────────────────────────────────────────┐
│  SYNC RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [What went wrong -- e.g. conflicts, missing dir]   │
│  Kit: vX.Y.Z (unchanged)                            │
└──────────────────────────────────────────────────────┘
```

Adapt box width to fit the longest content line. Pad all lines so the right border aligns.
