Before ending this session, complete all steps in order.

## Step 1: Housekeeping

1. **Update STATE.md** — Write the current position, any decisions made, blockers found, and a 1-2 sentence summary under Last Session.
2. **Update tasks/todo.md** — Make sure all completed steps have timestamps. Move any completed features to Done if needed.
3. **Check for learnings** — If anything failed and was fixed, or a useful pattern was discovered, log it to learnings.md or ~/.claude/CLAUDE.md.
4. **Commit and push** — Make sure all work is committed. No uncommitted changes should remain.
5. **Clean up session timer** — Run `rm -f .tmp/.session-start` to delete the session timer file.
6. **DOE Kit sync check** — If `~/doe-starter-kit` exists, check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (inbound). (2) Do any key syncable files differ? (outbound). Diff key files (~/.claude/commands/*.md, .githooks/*, .claude/hooks/*.py) against the starter kit. **For CLAUDE.md**, do a smart diff: only flag if universal sections (Who We Are, Operating Rules, Guardrails, Code Hygiene, Self-Annealing) differ. Ignore project-specific sections (Directory Structure, Progressive Disclosure triggers). If either condition is true, record for the System Checks section (meaning `/sync-doe` or `/pull-doe` needed). If neither, record as synced.
7. **Quick audit** — Run `python3 execution/audit_claims.py --hook` (fast checks only). Record the PASS/WARN/FAIL counts for the System Checks section. If any FAIL items exist, fix them before proceeding. WARN items can be noted and left for the next session.
8. **Structural change check** — Run `git diff --name-status HEAD~$(git rev-list --count HEAD --since="$(cat .tmp/.session-start 2>/dev/null || echo '1 hour ago')") 2>/dev/null` to detect new/moved/deleted files this session. If structural changes are found (files added, renamed, or deleted — not just modified), ask: "Structural changes detected — run /codemap to update the project index?" Only run `/codemap` if the user says yes.

## Step 2: Compute Session Stats

Find the first commit of this session: look at `git log --oneline` and identify where your work started (after the last "Update session stats" or "wrap" commit, or use the session start time from `.tmp/.session-start`).

Read `.tmp/.session-start` for the session start ISO timestamp. If it doesn't exist, use the first commit time.

Run the stats script:
```bash
python3 execution/wrap_stats.py \
  --since <first-session-commit-hash> \
  --session-start <ISO-timestamp-from-.tmp/.session-start> \
  --todo tasks/todo.md \
  --stats .claude/stats.json
```

This script gathers git metrics, computes streak, updates stats.json (v2), and outputs JSON to stdout.

Parse the JSON output. The key fields:

```
result.metrics      → commits, linesAdded, linesRemoved, filesTouched,
                      stepsCompleted, sessionDuration, commitLog
result.streak       → current streak day count
result.stats        → the full updated stats.json
```

After composing your session summary (a plain English sentence of what was done), update stats.json to add it to the most recent session entry before committing:

```bash
python3 -c "
import json
with open('.claude/stats.json') as f: data = json.load(f)
if data.get('recentSessions'):
    data['recentSessions'][0]['summary'] = '<YOUR_SUMMARY_HERE>'
    with open('.claude/stats.json', 'w') as f: json.dump(data, f, indent=2)
"
```

Do this BEFORE committing stats.json.

Commit stats.json with message: "Update session stats".

Register this project in the global project registry (for `/archive-global`):
```bash
python3 -c "
import json
from pathlib import Path
from datetime import datetime
reg = Path.home() / '.claude' / 'project-registry.json'
data = json.loads(reg.read_text()) if reg.exists() else {'projects': []}
root = str(Path.cwd().resolve())
existing = next((p for p in data['projects'] if p.get('path') == root), {})
data['projects'] = [p for p in data['projects'] if p.get('path') != root]
existing.update({'path': root, 'name': Path(root).name, 'lastUpdated': datetime.now().strftime('%Y-%m-%d')})
data['projects'].append(existing)
reg.write_text(json.dumps(data, indent=2))
"
```

## Step 3: Generate HTML Wrap-Up

Build the wrap-up as an HTML page using `execution/wrap_html.py`. This renders beautifully in the browser instead of fighting terminal formatting.

### 3a: Compose the wrap-up data

Using the stats JSON from Step 2, compose a JSON object with this schema. You must write the content (title, summary, breakdowns, vibe) yourself based on what happened this session:

```json
{
  "projectName": "PROJECT_DIR_NAME_UPPERCASED",
  "episode": result.stats.lifetime.totalSessions,
  "title": "Short Descriptive Title",
  "summary": "One plain English sentence summarising the session. What happened, in a way anyone would understand.",
  "breakdowns": [
    {"heading": "Area of work", "bullets": ["What was done", "Another thing done"]},
    {"heading": "Another area", "bullets": ["What changed"]}
  ],
  "vibe": {"emoji": "EMOJI", "text": "Vibe description"},
  "metrics": {
    "commits": N,
    "linesAdded": N,
    "linesRemoved": N,
    "filesTouched": N,
    "stepsCompleted": N,
    "sessionDuration": "Xh Ym",
    "agentsSpawned": N,
    "commitLog": [
      {"hash": "abc1234", "time": "HH:MM", "message": "Commit message", "type": "normal|fix|test"}
    ]
  },
  "commitGroups": [
    {"name": "Feature/task name", "commits": ["hash1", "hash2"]},
    {"name": "Housekeeping", "commits": ["hash3"]}
  ],
  "todaySessions": [
    {"number": 76, "duration": "1h 9m", "summary": "Plain English what was done"}
  ],
  "timeline": [
    {"time": "HH:MM", "desc": "Session started", "dur": "", "type": "start"},
    {"time": "HH:MM", "desc": "What happened", "dur": "Nm", "type": "normal|major|fix"}
  ],
  "decisions": [
    {"title": "Short decision title", "problem": "What the problem was", "solution": "What was decided and why"}
  ],
  "learnings": [
    {"title": "Short learning title", "problem": "What went wrong or was discovered", "solution": "What changed as a result"}
  ],
  "checks": {
    "audit": {"pass": N, "warn": N, "fail": N, "details": ["detail string if warn/fail"]},
    "doeKit": {"version": "vX.Y.Z", "synced": true|false}
  },
  "awaitingSignOff": [
    {
      "feature": "Feature Name [APP] (vX.Y.Z)",
      "summary": "One-line description of what needs testing",
      "manualItems": N,
      "groups": [
        {"name": "Group Name", "items": ["Manual check description", "..."]},
        {"name": "Another Group", "items": ["..."]}
      ]
    }
  ],
  "footer": {
    "session": N,
    "streak": N,
    "lifetimeCommits": N
  },
  "nextUp": "What to do next session -- pull from todo.md"
}
```

**awaitingSignOff**: Parse `## Awaiting Sign-off` in todo.md. For each feature heading (`###`), collect all unchecked `[ ] [manual]` lines. Group related items by theme (e.g. "Modal & Navigation", "Responsive", "Data Validation") -- use your judgment to create 2-5 groups per feature based on what the checks are testing. Each entry has: `feature` (heading text), `summary` (one-line description of what needs testing overall), `manualItems` (total count), and `groups` (array of `{name, items}` where items are the check descriptions stripped of `- [ ] [manual]` prefix). Cards render as collapsible -- the summary and count are always visible, groups expand on click. If the section is empty or has no features, use an empty array `[]` -- the renderer omits the section.

**commitGroups**: Group commits by feature or task. Use feature names from todo.md where possible. Commits that don't belong to a feature go in "Housekeeping" or "Other". Every commit in commitLog must appear in exactly one group.

**todaySessions**: Pull from stats.json recentSessions, filtering to today's date. Each entry needs a `number`, `duration`, and `summary` field. For the CURRENT session, write the summary yourself based on what you did. For previous sessions today that lack a summary, derive one from their commit messages in git log.

**decisions**: Each decision uses `title` (short label), `problem` (what was going wrong), and `solution` (what was decided and why). Renders as Problem:/Solution: under the title. Example: `{"title": "Batch manual verification at feature end", "problem": "Per-step manual approval was blocking autonomous building and killing throughput", "solution": "Accumulate manual checks and present as a single checklist at feature completion. Auto-verified steps proceed without waiting."}`

**learnings**: Each learning uses `title` (short label), `problem` (what went wrong or was discovered), and `solution` (what changed as a result). Renders as Discovery:/Change: under the title. Example: `{"title": "Contract patterns are planning-time guesses", "problem": "Wrote contains pcon= in the contract but actual code used pcon: with a colon — the = only appeared at runtime via buildHash()", "solution": "Now verify contract Verify: patterns match actual code before marking done. Quick fix, not a process problem."}`

### 3b: Vibe selection

Pick the vibe based on what happened:
- Smooth session, no failures, 5+ commits: `{"emoji": "😎", "text": "Smooth sailing"}`
- Clean but small session: `{"emoji": "😌", "text": "Clean & quiet"}`
- Had failures but recovered: `{"emoji": "💪", "text": "Hard-fought win"}`
- Had failures, messy: `{"emoji": "🫠", "text": "We got there eventually"}`
- Single quick fix: `{"emoji": "🩹", "text": "Quick patch"}`
- Massive output (1000+ lines): `{"emoji": "🏭", "text": "Factory floor"}`
- Mostly docs/config changes: `{"emoji": "🧹", "text": "Housekeeping"}`

### 3c: Timeline construction

Build the timeline from `result.metrics.commitLog`:
- First entry: session start time from `.tmp/.session-start`, type "start"
- Each commit: local time, short description (truncate long messages), duration since previous event, type:
  - "major" for feature additions, new files, significant changes
  - "fix" for bug fixes, corrections
  - "normal" for everything else (housekeeping, docs, state updates)
- Group rapid commits (< 1 min apart) into a single timeline entry
- For each timeline entry with a duration, the renderer will automatically calculate and display what percentage of total session time it represents. Include the total session duration in metrics.sessionDuration.

### 3d: Commit classification

For each commit in commitLog, set the type:
- "test" if the message contains "test" and it's clearly a test artifact (not a test framework)
- "fix" if the message starts with "Fix" or "fix:"
- "normal" for everything else

### 3e: Generate and open

Determine the theme based on the current time: run `date +%H` to get the current hour (0-23). If the hour is >= 6 AND < 18, use `--theme light`. Otherwise use `--theme dark` (the default).

Run:
```bash
python3 execution/wrap_html.py --json '<the JSON string>' --theme <light|dark> --output .tmp/wrap.html
```

Then save the JSON data permanently for HQ and open the HTML in the browser:
```bash
mkdir -p docs/wraps
python3 -c "import json; open('docs/wraps/session-<SESSION_NUMBER>.json', 'w').write(json.dumps(<THE_JSON_OBJECT>, indent=2))"
open .tmp/wrap.html
```

The `docs/wraps/session-N.json` file is what gets committed. The HTML is generated on demand (by `build_session_archive.py` regenerating it from JSON). The `.tmp/wrap.html` copy is disposable.

Print a one-line summary to the terminal: `Session [N] wrap-up opened in browser. [X] commits, [Y] steps, [duration].`

## Important Rules

- Pull ALL numbers from the wrap_stats.py JSON output. Never estimate or make up stats.
- The `summary` is one plain English sentence -- what happened this session in a way anyone would understand. No jargon, no drama.
- The `breakdowns` array groups the session's work into small subheadings (2-4 groups), each with 1-3 bullet points. Name specific features, files, and outcomes. Keep bullets short and scannable.
- Title, summary, and breakdowns MUST reference actual features, real files, and real problems from this session.
- If stats.json doesn't exist yet, this is session 1.
- Commit stats.json BEFORE generating the wrap-up so the push includes it.
- The `decisions` array should list decisions written to STATE.md this session, or `["None this session"]`.
- The `learnings` array should list learnings written to learnings.md or ~/.claude/CLAUDE.md, or `["None this session"]`.
- For agents spawned, count how many times the Agent tool was invoked during this session.
