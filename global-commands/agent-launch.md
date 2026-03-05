Read `tasks/todo.md` (Queue section) and `STATE.md` to understand what features are ready to run.

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

Create one. Read the relevant codebase files (existing patterns, data structures, UI conventions from `learnings.md`) to understand what the feature needs. Write a plan to `.claude/plans/<feature-name>.md` covering:

- **What:** One-paragraph summary of the feature
- **File ownership:** Which files/sections this task will create or modify (critical for wave safety)
- **Implementation approach:** Key technical decisions, patterns to follow, data sources to use
- **Acceptance criteria:** Testable conditions for "done"
- **Edge cases:** Known gotchas or things to watch for

Present the plan to the user:
```
No plan found for [Feature Name]. Here's a proposed plan:

[plan summary — key points only, not the whole file]

Written to: .claude/plans/<feature-name>.md
OK to proceed? (yes / edit / cancel)
```

- **"yes"** → Continue to Step 3
- **"edit"** → Ask what to change, update the plan, re-present
- **"cancel"** → Stop

If multiple features need plans, present them together so the user can approve in one go.

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

Generate this box programmatically — compute W from content, use `line()` helper. Content inside borders must be ASCII-only.

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
