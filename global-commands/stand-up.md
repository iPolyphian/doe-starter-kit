This command has two modes. Check which mode to use **before doing anything else**:

- Run `test -f .tmp/.session-start && echo "SESSION_ACTIVE" || echo "NO_SESSION"`
- If `NO_SESSION` → **Kick-off mode** (below)
- If `SESSION_ACTIVE` → **Status mode** (further below)

---

## Kick-off mode (no active session)

Start the session clock: run `mkdir -p .tmp && date -u +%Y-%m-%dT%H:%M:%S+00:00 > .tmp/.session-start`

Read CLAUDE.md, tasks/todo.md, STATE.md, and learnings.md.

**DOE Kit check:** If `~/doe-starter-kit` exists, run `cd ~/doe-starter-kit && git describe --tags --abbrev=0 2>/dev/null` to get the current kit version, and `git log -1 --format="%ai" $(git describe --tags --abbrev=0)` to get the last release date. Then do a quick count of syncable files that differ between the project and the kit: diff key files (CLAUDE.md, ~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) and count how many have changes. If the directory doesn't exist, skip the DOE Kit line entirely.

Show a bordered kick-off card, then present a plan and wait for sign-off:

```
┌──────────────────────────────────────────────────┐
│  STAND-UP · HH:MM - DD/MM/YY                     │
├──────────────────────────────────────────────────┤
│  PROJECT    [dir name] vX.Y.Z                     │
│  FEATURE    [active feature] [APP/INFRA] vX.Y.x   │
│  PROGRESS   ██████░░░░ N/M steps                  │
│  DOE KIT    vX.Y.Z · [synced ✓ / N — /sync-doe]  │
│  BLOCKERS   [from STATE.md or "None"]             │
│  LEARNINGS  N entries · last updated DD/MM        │
├──────────────────────────────────────────────────┤
│  PLAN                                             │
│  → [proposed next steps as bullets]               │
└──────────────────────────────────────────────────┘
```

Card rules:
- PROJECT: current directory name + version from STATE.md "Current app version". If no version in STATE.md, omit the version.
- FEATURE: from STATE.md "Active feature" line. If no active feature, show "No active feature".
- PROGRESS: count [x] and [ ] steps for the current feature in todo.md ## Current. Bar uses █ for done, ░ for remaining, scaled to 10 characters. If no current feature, omit this line.
- DOE KIT: `vX.Y.Z · synced ✓` if clean, `vX.Y.Z · N files with pending changes — /sync-doe` if any differ. Omit entirely if `~/doe-starter-kit` doesn't exist.
- BLOCKERS: from STATE.md ## Blockers & Edge Cases. "None" if empty.
- LEARNINGS: count bullet-point lines in learnings.md (lines starting with `- `). Show last-modified date from the front-matter `Last updated` field if present, otherwise use `stat` or `git log -1` on the file.
- PLAN: the proposed next steps — what you recommend doing this session. This is the "present a plan" part.
- BORDER: size the box to fit the longest content line. All lines padded with spaces so the right border │ aligns consistently. Same conventions as /sitrep and /vitals.

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
│  PROGRESS     ██████░░░░ N/M steps (X%)           │
│  PHASE GOAL   [what done looks like]              │
│                                                   │
│  SINCE LAST MILESTONE (vX.Y.Z)                    │
│  · [commit/shipped item]                          │
│  · [commit/shipped item]                          │
│                                                   │
│  MOMENTUM     [On track / Ahead / Behind] — why   │
│  BLOCKERS     [from STATE.md or "None"]           │
│  DECISIONS    [pending decisions or "None"]        │
│  QUEUE        [next feature or "Empty"]           │
└──────────────────────────────────────────────────┘
```

Card rules:
- WORKING ON: from todo.md ## Current heading — feature name, type tag [APP/INFRA], and version range. If no current feature, show "No active feature" and skip PROGRESS, PHASE GOAL, and SINCE LAST MILESTONE sections.
- PROGRESS: count [x] and [ ] steps for the current feature. Bar uses █ for done, ░ for remaining, scaled to 10 characters. Show "N/M steps (X%)" where X is the percentage complete.
- PHASE GOAL: read the feature description under ## Current in todo.md. If a plan file is referenced (e.g. "Plan: .claude/plans/..."), read it and summarise what "done" looks like for this feature in one sentence. If no plan file, summarise from the step list.
- SINCE LAST MILESTONE: run `git tag --sort=-v:refname | head -1` to get the latest version tag. Then `git log --oneline <tag>..HEAD` to list commits since that tag. Show as bullet points (max 8 — if more, show the 8 most recent and note "and N more"). If no tags exist, show commits from the last 7 days instead.
- MOMENTUM: assess based on completed vs remaining steps and time context. More than half done → "On track". All done except housekeeping → "Ahead". Zero steps done and the feature has been in ## Current for 2+ sessions (check STATE.md ## Last Session for evidence of prior sessions working on this feature) → "Behind". Add a brief reason after the dash explaining the assessment.
- BLOCKERS: from STATE.md ## Blockers & Edge Cases. Show content or "None".
- DECISIONS: scan STATE.md for any pending decisions, open questions, or items needing user input. "None" if nothing found.
- QUEUE: first feature heading from ## Queue in todo.md. Show name + type tag, or "Empty" if nothing queued.
- BORDER: size the box to fit the longest content line. All lines padded with spaces so the right border │ aligns consistently. Same conventions as /sitrep and /vitals.
- This is READ-ONLY. Do not start the session clock. Do not modify any files. Do not execute anything.
