Claim a task from the active wave and start working in its worktree.

## Step 1: Claim

Run `python3 ~/.claude/scripts/multi_agent.py --claim --parent-pid $PPID` and capture the full output.

If the claim fails (no active wave, no pending tasks, or error), show the error and stop.

## Step 2: Enter the worktree

Parse the claim output for the worktree path (the line after "Worktree:" or the path printed by the script).

Run `cd <worktree-path>` to move into the worktree directory.

Verify you're in the worktree: run `pwd` and `git branch --show-current` to confirm.

## Step 3: Show the assignment

Show a brief summary:
```
Claimed: [taskId]
Worktree: [path]
Branch: [branch-name]
Model: [recommended model] / Thinking: [recommended level]
```

Then read the task's `description` and `acceptanceCriteria` from the wave file and show them.

## Step 4: Start working

Begin implementing the task immediately. Follow CLAUDE.md rules — commit after each completed step, verify before delivering.

When done, run:
```
python3 ~/.claude/scripts/multi_agent.py --complete <taskId> --parent-pid $PPID
```

If the task fails or you get stuck, run:
```
python3 ~/.claude/scripts/multi_agent.py --fail <taskId> --parent-pid $PPID
```

## Step 5: Check if wave is complete — auto-merge offer

After marking the task complete (or failed), run:
```
python3 ~/.claude/scripts/multi_agent.py --dashboard --json
```

Parse the JSON output. If `tasksCompleted + tasksFailed == totalTasks` (i.e. no tasks are pending or in progress), all work is done.

Show:
```
All [N] tasks complete. Merge to master now? (yes/no)
```

- **"yes"** → Run `python3 ~/.claude/scripts/multi_agent.py --merge --parent-pid $PPID` to merge all completed worktrees back to master in the defined merge order. Show the merge output.
- **"no"** → Show: `OK — run /hq --merge whenever you're ready.`

If tasks are still in progress, show a brief status instead:
```
Task [taskId] done. Wave still running — [N] task(s) remaining.
Run /hq to check progress.
```

IMPORTANT: ALL multi_agent.py commands MUST include `--parent-pid $PPID`.
