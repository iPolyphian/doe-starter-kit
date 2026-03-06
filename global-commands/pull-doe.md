First, check if ~/doe-starter-kit is accessible. If not, run: /add-dir ~/doe-starter-kit

Then read directives/starter-kit-pull.md and follow it precisely. The directive covers:

1. Pull latest kit from GitHub — ensure you have the newest version before comparing
2. Read the project's last-synced version from `.doe-kit-version` in the project root
3. Read the kit's current version from `git describe --tags` in ~/doe-starter-kit
4. If versions match, say "Already up to date" and stop
5. Show kit CHANGELOG entries between the two versions — this is what changed
6. Global installs: run `~/doe-starter-kit/setup.sh` to update commands, hooks, scripts
7. Project hooks: compare .claude/hooks/, .claude/settings.json, .githooks/ — show diffs, propose updates, preserve project additions
8. CLAUDE.md: diff what changed between versions in the kit, propose surgical edits, flag project-specific content
9. Templates: compare learnings.md and todo.md format rules — add new headings/rules, never touch content
10. Directives: list kit vs project directives — update universal ones, add new ones, skip project-specific
11. Execution scripts: compare universal checks in audit_claims.py — add new universal checks, preserve @register("project-specific") checks
12. Show full summary — get approval before applying
13. Apply approved changes
14. Update `.doe-kit-version` in the project root
15. Update STATE.md's "DOE Starter Kit" line to the new version (e.g. `v1.24.1 · ~/doe-starter-kit · synced`)
16. Commit: "Pull DOE kit v[X.Y.Z] — [summary]"

To push DOE improvements FROM this project to the starter kit (reverse direction), use `/sync-doe`.

Rules:
- NEVER replace a file wholesale. Merge additively — add new content, update changed content, preserve project-specific content.
- Project-specific sections in CLAUDE.md (triggers referencing project directives, project-specific guardrails) must be preserved untouched.
- If unsure whether a kit change conflicts with a project customization, ask me.
- Show diffs before writing. Don't apply without my sign-off.
- If directives/starter-kit-pull.md doesn't exist, tell me — the starter kit may not be set up yet.
- If `.doe-kit-version` doesn't exist, treat this as a first pull — be extra cautious and show everything.

## Analysis Box (REQUIRED)

After comparing kit changes against the project, present the analysis in a bordered box BEFORE proposing any changes. This is the decision-support summary the user reads to approve or reject. **Generate programmatically** — compute W from content, define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"`. ALL rows including headers MUST use this helper — never construct `f"│{...}│"` manually. For headers with right-aligned text: build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`. Unicode box-drawing borders. Content inside borders must be ASCII-only.

Structure:
- **Header row:** "INCOMING KIT CHANGES" left-aligned, version range (e.g. "v1.12.0 -> v1.13.0") right-aligned, with `├─┤` separator below
- **Summary:** 2-3 lines of context about what changed in the kit since last pull
- **Numbered list:** One entry per file/category that changed, with a short explanation
- **VERDICT:** 1-2 lines — are the changes safe to pull?
- **RECOMMENDATION:** 1-2 lines — pull all, pull selectively, or skip

```
┌──────────────────────────────────────────────────────────────────────┐
│  INCOMING KIT CHANGES                         vX.Y.Z -> vX.Y.Z      │
├──────────────────────────────────────────────────────────────────────┤
│  [2-3 line summary of what changed in the kit]                      │
│                                                                     │
│  1. [category/file] -- [what changed] ([safe/review/conflict])      │
│  2. [category/file] -- [what changed] ([safe/review/conflict])      │
│                                                                     │
│  VERDICT                                                            │
│                                                                     │
│  [Assessment of whether changes are safe to pull]                   │
│                                                                     │
│  RECOMMENDATION                                                     │
│                                                                     │
│  [Pull all / pull selectively / skip / ask user about conflicts]    │
└──────────────────────────────────────────────────────────────────────┘
```

If the user approves, proceed with the pull. If not, skip to the Result Summary.

## Result Summary (REQUIRED)

After completing all steps — or when stopping early because nothing changed — ALWAYS end the pull output with this bordered result box. This is the last thing printed, no exceptions.

Pick the matching status. **Generate boxes programmatically** — collect all content lines into a list, compute `W = max(len(l) for l in lines) + 4`, define `line(c)` as `f"│  {c}".ljust(W + 1) + "│"`, then pass ALL rows through `line()` — never construct `f"│{...}│"` manually. Never hardcode W — always compute from content. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no Unicode arrows) — use `->` instead of `→`, text labels instead of emoji icons.

**Already up to date:**
```
UP TO DATE
┌──────────────────────────────────────────────────────┐
│  PULL RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [1-2 line explanation]                              │
│  Kit: vX.Y.Z -- project already synced               │
└──────────────────────────────────────────────────────┘
```

**Changes approved and applied:**
```
PULLED
┌──────────────────────────────────────────────────────┐
│  PULL RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [1-2 line summary of what was pulled]               │
│  Kit: vX.Y.Z -> vX.Y.Z                              │
└──────────────────────────────────────────────────────┘
```

**Blocked by an issue:**
```
BLOCKED
┌──────────────────────────────────────────────────────┐
│  PULL RESULT                                         │
├──────────────────────────────────────────────────────┤
│  [What went wrong -- e.g. conflicts, missing dir]    │
│  Kit: vX.Y.Z (not pulled)                            │
└──────────────────────────────────────────────────────┘
```

Adapt box width to fit the longest content line. Pad all lines so the right border aligns.
