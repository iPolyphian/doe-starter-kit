This command has two modes. Check which mode to use **before doing anything else**:

- Run `ls .tmp/.session-start 2>/dev/null && echo "SESSION_ACTIVE" || echo "NO_SESSION"`
- If `NO_SESSION` → **Kick-off mode** (below)
- If `SESSION_ACTIVE` → **Status mode** (further below)

---

## Kick-off mode (no active session)

Start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start`

Read CLAUDE.md, tasks/todo.md, STATE.md, learnings.md, and ROADMAP.md.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version, and `git log -1 --format="%ai" $(git describe --tags --abbrev=0)` to get the last release date. Then check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (inbound). (2) Do any key syncable files differ? (outbound). Diff key files (~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many have changes. **For CLAUDE.md**, do a smart diff: only flag if universal sections (Who We Are, Operating Rules, Guardrails, Code Hygiene, Self-Annealing) differ between kit and project. Ignore project-specific sections (Directory Structure, Progressive Disclosure triggers, project-specific additions). If only project-specific sections differ, do not count as a change. Show a directional sync indicator: `* push` if only outbound changes exist (syncable files differ but kit tag matches STATE.md version), `* pull` if only inbound changes exist (kit tag is newer than STATE.md version but no file diffs), `* push+pull` if both conditions are true, or `synced` if everything matches. If the directory doesn't exist, skip the DOE Kit line entirely.

Show a bordered kick-off card, then present a plan and wait for sign-off:

```
┌──────────────────────────────────────────────────┐
│  STAND-UP · HH:MM - DD/MM/YY    [dir] vX.Y.Z     │
├──────────────────────────────────────────────────┤
│  FEATURE    [active feature] [APP/INFRA] vX.Y.x   │
│  PROGRESS   ██████░░░░ N/M steps                  │
│  BLOCKERS   [from STATE.md blockers section]       │
│    !! [each blocker on its own line]               │
│  DOE KIT    vX.Y.Z [synced / * push/pull/push+pull]│
│  PIPELINE   N in Up Next, M in Queue              │
│  SIGN-OFF   N features (M manual items pending)   │
│  WARNINGS   [audit WARN/FAIL items]               │
│    ⚠️ [detail line for each WARN/FAIL item]        │
├──────────────────────────────────────────────────┤
│  [1-2 line summary of last session from STATE.md]  │
│                                                   │
│  PLAN                                             │
│  → [proposed next steps as bullets]               │
│                                                   │
│  FOCUS                                            │
│  · [coaching bullet from stats.json analysis]     │
│  · [coaching bullet]                              │
├──────────────────────────────────────────────────┤
│  Model: [model] · Thinking: [level]              │
└──────────────────────────────────────────────────┘
```

Card rules:
- MODEL ROW: Final row of the card, separated by `├──┤`. Shows `Model: [name] · Thinking: [level]`. IMPORTANT: This line is always shorter than other content lines. You MUST pad it with trailing spaces so the right `│` is at the exact same character position as every other `│` in the card. Count the inner width of the longest line, then pad the model row to match. No emojis (they break alignment). You know your model ID from your system prompt (look for "The exact model ID is..."). Display names: `claude-opus-4-6` → "Opus 4.6", `claude-sonnet-4-6` → "Sonnet 4.6", `claude-haiku-4-5` → "Haiku 4.5". For thinking level, report your reasoning effort: ≤33 → "low", 34-66 → "medium", ≥67 → "high". If uncertain, show "default". This helps the user decide if they need to switch models before starting work.
- PROJECT: Right-aligned on the header row, same line as the date. Show `[dir name] vX.Y.Z` (directory name + version from STATE.md "Current app version"). If no version in STATE.md, omit the version. Build the header as: left = `STAND-UP -- HH:MM - DD/MM/YY`, right = `[dir] vX.Y.Z`, then right-align within the line width.
- FEATURE: from STATE.md "Active feature" line. If no active feature, show "No active feature".
- PROGRESS: count [x] and [ ] steps for the current feature in todo.md ## Current. Bar uses █ for done, ░ for remaining, scaled to 10 characters. If no current feature, omit this line.
- DOE KIT: `vX.Y.Z synced` if everything matches. `vX.Y.Z * push` if project has outbound changes to push to the starter kit via `/sync-doe` (syncable files differ but kit tag matches STATE.md version). `vX.Y.Z * pull` if the kit has inbound updates to pull into the project via `/pull-doe` (kit tag is newer than STATE.md version but no file diffs). `vX.Y.Z * push+pull` if both directions need syncing. Omit entirely if `~/doe-starter-kit` doesn't exist.
- SIGN-OFF: Parse `## Awaiting Sign-off` in todo.md. Count `###` headings (features) and `[ ] [manual]` lines (pending manual items). Show `SIGN-OFF   N features (M manual items pending)`. If the section is empty or has no features, omit entirely.
- PIPELINE: Compare ROADMAP.md `## Up Next` item count against todo.md `## Queue` item count. Count feature headings (lines starting with `###`) in each section. If Up Next has more items than Queue, show `PIPELINE   N in Up Next, M in Queue -- scope to promote`. If counts match (including both being 0), show `PIPELINE   Synced (N items)`. This nudges the user to scope and promote features without auto-syncing. Omit if ROADMAP.md doesn't exist.
- WARNINGS: Run `python3 execution/audit_claims.py --hook --json` and parse the JSON output. If any findings have severity "WARN" or "FAIL", show a WARNINGS row with a summary count (e.g. "2 audit WARNs") followed by indented detail lines for each non-PASS item — use `⚠️` prefix for WARN and `❌` for FAIL. Each detail line shows the file name and message from the finding. If the first WARN/FAIL item is actionable in this session (e.g. a stale doc or missing version tag), add an indented `→ Fix now?` suggestion. **If all findings are PASS, omit the WARNINGS section entirely** — it only appears when there are problems. If the audit script doesn't exist or fails, also omit.
- SUMMARY: After the `├──┤` separator, show 1-2 lines summarising the last session from STATE.md ## Last Session. Keep it brief — what happened, where we left off. Then a blank line before PLAN.
- CONTRACT: After the PROGRESS line, check the contract block of the next step to be worked on. Show `CONTRACT   Valid (N auto, M manual)` if the next step has a well-formed contract with executable Verify: patterns, `CONTRACT   Needs fix -- invalid Verify: patterns` if patterns don't match executable forms, or `CONTRACT   Missing` if no contract block exists. This is informational only -- it surfaces problems early so the plan can account for them (e.g. "First fix the missing contract, then start Step 2"). If no current feature or all steps complete, omit this line.
- BLOCKERS: Read STATE.md `## Blockers & Edge Cases`. If the section has any bullet points, show a `BLOCKERS` row after CONTRACT with the count (e.g. "2 active"), followed by indented detail lines with `!!` prefix for each blocker. Truncate long blockers to fit the 56-char content width. **If the section is empty or has no bullets, omit the BLOCKERS section entirely** -- it only appears when there are problems. This row appears in both kick-off and status mode cards, positioned between CONTRACT and DOE KIT.
- PLAN: the proposed next steps — what you recommend doing this session. This is the "present a plan" part.
- FOCUS: After PLAN, analyse `.claude/stats.json` (if it exists) to surface 2-3 coaching bullets based on `recentSessions` (last 5-10 entries). Look for these patterns and show whichever are most relevant:
  - **Infrastructure vs product ratio:** Count sessions where the commit messages or todo.md steps were [INFRA] vs [APP]. If heavily skewed, note it (e.g. "4/5 recent sessions were [INFRA] — consider shipping product").
  - **Stale WARNs:** If the WARNINGS section above shows items, and the same items appeared in previous sessions (check if the warning is about a doc that's been stale for multiple minor versions), flag persistence.
  - **Commits/session trend:** Calculate average commits across recent sessions. If trending down or consistently low (< 2), suggest aiming higher.
  - **Steps completed trend:** Calculate average steps completed per session. If consistently 0, flag it.
  - **Time-of-day patterns:** Check session dates/times. If most sessions are very late (after midnight), note the pattern.
  Show 2-3 bullets max. Keep coaching tone constructive and specific — use real numbers. If stats.json doesn't exist or has no recentSessions, omit the FOCUS section entirely.
- BORDER: Fixed width — always 60 `─` characters between `│` borders (62 total per line). All content lines: `│` + 2 spaces + content + trailing spaces + `│` = 62 chars. If content would exceed 56 characters, truncate with `…`. Never dynamically size — the box is always the same width. **Generate boxes programmatically** — define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width. ALL rows including headers MUST use this helper — never construct `f"│{...}│"` manually. For headers with right-aligned text: build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`. Never hand-pad bordered output. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no `·`, `✓`, `⚠️`, `—`, `…`) — use `--` for separators, commas for lists. Exception: progress bar uses `█` (done) and `░` (remaining) — these render at fixed width in terminals.

**Milestone celebration:** After generating the kick-off card, check `.claude/stats.json` → `lifetime.totalSessions`. If `totalSessions` is a multiple of 100 (i.e. `totalSessions % 100 == 0`), show a celebration card **below** the kick-off card. The celebration card summarises the project's lifetime: total sessions, commits, lines added/removed, net code, first session date, days active, streak, avg commits/session, features shipped (count from ROADMAP.md ## Complete), key version milestones, and a one-liner at the bottom. Use the same bordered box style (W=60, programmatic `line()` helper). If not a milestone session, skip this entirely.

Wait for sign-off before executing anything.

---

## Status mode (session already active)

This is a read-only daily status check. Do NOT start the session clock. Do NOT modify any files. Do NOT execute anything.

Read tasks/todo.md and STATE.md. Run `git tag --sort=-v:refname` and `git log --oneline`.

Show a bordered status card:

```
┌──────────────────────────────────────────────────┐
│  STAND-UP · DD/MM/YY                              │
├──────────────────────────────────────────────────┤
│  WORKING ON   [feature] [APP/INFRA] vX.Y.x        │
│  PHASE GOAL   [what done looks like]              │
│  PROGRESS     ██████░░░░ N/M steps (X%)           │
│  NEXT STEP    [next uncompleted step from todo]   │
│  BLOCKERS     [from STATE.md blockers section]    │
│    !! [each blocker on its own line]              │
│                                                   │
│  SINCE LAST MILESTONE (vX.Y.Z)                    │
│  · [commit/shipped item]                          │
│  · [commit/shipped item]                          │
│                                                   │
│  MOMENTUM     [On track / Ahead / Behind] — why   │
│  QUEUE        [next feature or "Empty"]           │
│  SIGN-OFF     N features (M manual items pending) │
├──────────────────────────────────────────────────┤
│  Model: [model] · Thinking: [level]              │
└──────────────────────────────────────────────────┘
```

Card rules:
- MODEL ROW: same as kick-off mode — final row with `Model: [name] · Thinking: [level]`, padded to match the card's full width.
- WORKING ON: from todo.md ## Current heading — feature name, type tag [APP/INFRA], and version range. If no current feature, show "No active feature" and skip PROGRESS, PHASE GOAL, and SINCE LAST MILESTONE sections.
- PHASE GOAL: read the feature description under ## Current in todo.md. If a plan file is referenced (e.g. "Plan: .claude/plans/..."), read it and summarise what "done" looks like for this feature in one sentence. If no plan file, summarise from the step list.
- PROGRESS: count [x] and [ ] steps for the current feature. Bar uses █ for done, ░ for remaining, scaled to 10 characters. Show "N/M steps (X%)" where X is the percentage complete.
- NEXT STEP: find the first uncompleted step (line starting with `[ ]`) for the current feature in todo.md. Show the step number and description (e.g. "Step 4 — /agent-status command"). If all steps are complete, show "All steps complete — ready for retro".
- SINCE LAST MILESTONE: run `git tag --sort=-v:refname | head -1` to get the latest version tag. Then `git log --oneline <tag>..HEAD` to list commits since that tag. **Group related commits** by feature or theme instead of listing each one individually -- look at commit message patterns (shared prefixes, related file areas, sequential feature work). Show each group as a single bullet with the group name and a brief summary of what those commits achieved, with commit count in parentheses. Example: `-- Entity Page Redesign: grid layouts, tabbed CRM, section grouping across 5 pages (8 commits)`. Standalone commits that don't belong to a group get their own bullet without a count. Max 6 groups. If no tags exist, show commits from the last 7 days instead.
- MOMENTUM: assess based on completed vs remaining steps and time context. More than half done → "On track". All done except housekeeping → "Ahead". Zero steps done and the feature has been in ## Current for 2+ sessions (check STATE.md ## Last Session for evidence of prior sessions working on this feature) → "Behind". Add a brief reason after the dash explaining the assessment.
- QUEUE: first feature heading from ## Queue in todo.md. Show name + type tag, or "Empty" if nothing queued.
- SIGN-OFF: same as kick-off mode -- parse `## Awaiting Sign-off` in todo.md, count features and `[ ] [manual]` items. Show `SIGN-OFF   N features (M manual items pending)`. Omit if section is empty.
- BORDER: Fixed width — always 60 `─` characters between `│` borders (62 total per line). All content lines: `│` + 2 spaces + content + trailing spaces + `│` = 62 chars. If content would exceed 56 characters, truncate with `…`. Never dynamically size — the box is always the same width. **Generate boxes programmatically** — define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width. ALL rows including headers MUST use this helper — never construct `f"│{...}│"` manually. For headers with right-aligned text: build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`. Never hand-pad bordered output. Use Unicode box-drawing characters for borders (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only (no emojis, no `·`, `✓`, `⚠️`, `—`, `…`) — use `--` for separators, commas for lists. Exception: progress bar uses `█` (done) and `░` (remaining) — these render at fixed width in terminals.
- This is READ-ONLY. Do not start the session clock. Do not modify any files. Do not execute anything (except the box-generation snippet).
