Read `tasks/todo.md` (Queue section and Current section) and `STATE.md` to understand what features are ready to run.

## Step 0: Ensure queue items have contracts

Before anything else, check each feature in `## Queue` and `## Current` for contract blocks.

For each feature's uncompleted steps (lines starting with `- [ ]` or `N. [ ]`), check if a `Contract:` block exists (lines indented under the step with `- [ ] [auto]` or `- [ ] [manual]` criteria). A step without a Contract block — or with a Contract block missing executable `Verify:` patterns — is **not launchable**. Skip steps already marked `[x]`.

**If any steps are missing contracts:**

1. Read the feature's plan file (referenced in todo.md as "Plan: `.claude/plans/...`"). If no plan exists, stop and create one first (Step 2 handles this).
2. For each step missing a contract, generate one based on the plan's design, file ownership, and acceptance criteria:
   - `[auto]` criteria use executable `Verify:` patterns: `run:`, `file: <path> exists`, `file: <path> contains <string>`, `html: <path> has <selector>`
   - `[APP]` features require at least one `[manual]` criterion per step (visual/behavioural checks)
   - `[INFRA]` features can be fully `[auto]`
3. Write the contracts directly into `tasks/todo.md` under each step
4. Present the contracts to the user for approval in a bordered box. Use the same BORDER rules as Step 4 (ljust `line()` helper, Unicode box-drawing, ASCII-only content). Group by feature with separators. Footer row: `Approve? "yes" to write | "edit" to modify | "cancel" to stop`.
5. Wait for approval before proceeding. On "edit", ask what to change. On "cancel", stop.

**If all steps already have valid contracts**, skip to Step 1.

## Step 1: Identify parallelisable features

Look at `## Queue` in todo.md. Identify features that can run simultaneously:
- Features with no shared file ownership are parallelisable
- Features that depend on each other must be in the same wave with `dependsOn` set
- If plan files are referenced (`.claude/plans/...`), read them for file ownership details

If only one feature is in the queue, create a single-task wave (still useful for worktree isolation and tracking).

## Step 2: Check for plans

For each feature identified in Step 1, check if a plan exists:

1. Check if the todo.md entry references a plan file (e.g. "Plan: `.claude/plans/...`")
2. If referenced, read it and confirm it has enough detail (file ownership, acceptance criteria, implementation approach)
3. If NOT referenced, search for a matching plan:
   - Check `.claude/plans/` in the project (local plans)
   - Check `~/.claude/plans/` (global plans)
   - Match by feature name (fuzzy — e.g. "Comparison" matches `comparison-and-filter.md`)
4. If a plan is found but not linked, use it and note the link for the user

**If no plan exists for a feature:**

Create one. Before writing, read the codebase to understand context:
- `learnings.md` for project patterns, UI conventions, CSS prefix convention, card function patterns
- `STATE.md` for current position and blockers
- Existing `src/` files to understand the architecture and patterns to follow
- Existing plans in `.claude/plans/` for format reference

Write the plan to `.claude/plans/<feature-name>.md` using the **standard plan format** (match existing plans exactly):

```markdown
# Feature Name

## Context
One paragraph: why this feature, what it builds on, what data/APIs it needs (or "no new data — uses existing X, Y, Z"). Note if parallelisable with other features and why (file ownership boundaries).

## Design
**UI pattern:** How it presents (overlay, panel, card, etc.) and where it fits in the existing UI.
**User flow:** Numbered steps from trigger to completion.
**Layout:** ASCII wireframe if the feature has visual output (match briefing-pack.md style).
**CSS prefix:** `xx-` (2-3 letter prefix per feature, check learnings.md ## UI Patterns).
**Key functions:**
- `mainFunction(args)` — what it does
- `helperFunction(args)` — what it does

## File Ownership
Explicit list of files this feature will CREATE or MODIFY. Critical for multi-agent safety.
- NEW: `src/js/feature.js` — [what it contains]
- NEW: `src/styles/feature.css` — [what it contains]
- MODIFY: `src/js/map.js` — [what changes, e.g. "add button to toolbar"]
- READS: `src/data/geo.js`, `src/data/elections.js` — [no modifications]

## Steps
Each step includes a recommended model + thinking level.

### Step 1 → vX.Y.0: [Step name] — model: [Opus/Sonnet/Haiku] · thinking: [high/medium/low]
- [Specific implementation details]
- [What to build, what to wire up]

### Step 2 → vX.Y.1: Housekeeping — model: Sonnet · thinking: low
- Changelog, roadmap COMPLETE, showcase entry, retro

## Not in Scope
- [Things explicitly excluded to prevent scope creep]
```

Present the plan to the user. Show the **full plan content** (not a summary) so they can review it properly:

```
No plan found for [Feature Name]. Here's a proposed plan:

[full plan content]

Written to: .claude/plans/<feature-name>.md
OK to proceed? (yes / edit / cancel)
```

- **"yes"** → Continue to Step 3
- **"edit"** → Ask what to change, update the plan, re-present
- **"cancel"** → Stop

If multiple features need plans, present them one at a time so the user can review each properly.

Do NOT proceed to wave creation until every feature has an approved plan.

## Step 3: Build the wave file

For each task, determine:
- **taskId**: kebab-case identifier from the feature name (e.g. `comparison-overlay`)
- **description**: from the step description in todo.md
- **acceptanceCriteria**: from the task contract if one exists, otherwise from the plan's acceptance criteria
- **owns**: files/patterns this task will MODIFY — pull from the plan's file ownership section (critical — no overlap allowed between tasks)
- **reads**: files/patterns this task will READ but not modify (overlaps OK)
- **model**: recommend based on task complexity — `opus` for architectural/judgment tasks, `sonnet` for implementation, `haiku` for mechanical
- **thinking**: `high` for design decisions, `medium` for implementation, `low` for mechanical
- **size**: `S` (<30 min), `M` (30-90 min), `L` (90+ min)
- **versionTag**: from the step's version tag in todo.md (e.g. `v0.16.0`)
- **dependsOn**: task IDs this task must wait for (empty if independent)

Write the wave file to `.tmp/waves/.draft-wave.json` (draft location — not visible to `find_active_wave` or `find_latest_wave`).

Use this schema:
```json
{
  "waveId": "wave-{N}",
  "feature": "Feature Name(s)",
  "createdAt": "ISO timestamp",
  "createdBy": "agent-launch",
  "status": "pending",
  "tasks": [
    {
      "taskId": "task-name",
      "description": "What to build",
      "acceptanceCriteria": ["Criterion 1", "Criterion 2"],
      "owns": ["file-or-pattern"],
      "reads": ["file-or-pattern"],
      "ignores": ["*"],
      "model": "sonnet",
      "thinking": "high",
      "size": "M",
      "versionTag": "v0.X.Y",
      "dependsOn": [],
      "status": "pending"
    }
  ]
}
```

## Step 4: Preview

Run `python3 ~/.claude/scripts/multi_agent.py --preview .tmp/waves/.draft-wave.json --json` and parse the output.

Show a bordered preview card:

```
┌──────────────────────────────────────────────────────────────┐
│  AGENT LAUNCH · PREVIEW                                      │
├──────────────────────────────────────────────────────────────┤
│  WAVE      wave-N · Feature Name                             │
│  TASKS     N tasks · estimated ~£X.XX                        │
│                                                              │
│  [taskId]  [model]/[thinking]  [size]  [versionTag]          │
│    owns: [file list]                                         │
│    reads: [file list]                                        │
│                                                              │
│  [taskId]  [model]/[thinking]  [size]  [versionTag]          │
│    owns: [file list]                                         │
│    reads: [file list]                                        │
│                                                              │
│  CONFLICTS  [details or "None -- safe to launch"]            │
│  MERGE ORDER  task-1 -> task-2 -> ...                        │
│                                                              │
│  READY  [Yes/No -- if No, show blockers]                     │
├──────────────────────────────────────────────────────────────┤
│  "go" to launch · "edit" to modify · "cancel" to abort       │
└──────────────────────────────────────────────────────────────┘
```

BORDER: **Generate boxes programmatically** — define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width (number of `─` between corners). ALL rows including headers MUST use this helper — never construct `f"│{...}│"` manually. For headers with right-aligned text: build the inner content string first (e.g. `f"{left}{right:>{W - 2 - len(left)}}"`) then pass through `line()`. Use `|` not `·` for inline separators (middle dots have ambiguous width). Content inside borders must be ASCII-only. Borders use Unicode box-drawing (`┌─┐`, `├─┤`, `└─┘`, `│`).

Wait for the user's response.

## Step 5: Launch or adjust

- **"go"** → Move the draft to its final name: `mv .tmp/waves/.draft-wave.json .tmp/waves/wave-{N}.json`. Then run `python3 ~/.claude/scripts/multi_agent.py --init-wave .tmp/waves/wave-{N}.json`. Then ask:
  ```
  Wave launched. What should this terminal do?

  - "work"  → Claim a task and start building (/agent-start)
  - "monitor" → Stay as HQ and watch progress (/hq)
  ```
  - **"work"** → Run `/agent-start` in this terminal to claim the first task.
  - **"monitor"** → Run `/hq` to show the dashboard. Remind the user: `Open new terminal tabs, type "claude", then /agent-start in each.`

- **"edit"** → Ask what to change (models, ownership, task split), update the wave file, re-run preview.

- **"cancel"** → Delete the draft file (`rm .tmp/waves/.draft-wave.json`) and stop.

## Important rules

- NEVER create a wave where two tasks own the same file or pattern. This is the #1 source of merge conflicts.
- If the plan file specifies file ownership, use it. Don't guess.
- If you're unsure about ownership boundaries, ask the user before generating.
- For monolith HTML apps (single large HTML file), tasks CANNOT both own the HTML. Split ownership by JS/CSS section or use sequential waves.
- Always run `--preview` before `--init-wave`. Never skip the preview.
