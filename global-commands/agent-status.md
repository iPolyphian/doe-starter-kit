Run `python3 ~/.claude/scripts/multi_agent.py --dashboard --json` and parse the output.

## If `mode` is `"no_wave"` — show the help card:

```
┌──────────────────────────────────────────────────────────────┐
│  HQ · DD/MM/YY                                               │
├──────────────────────────────────────────────────────────────┤
│  STATUS  No active wave                                      │
│                                                              │
│  ACTIONS                                                     │
│  /agent-status --plan      Create a wave from todo.md features         │
│  /agent-status --preview   Preview an existing wave before launching   │
│  /agent-status --launch    Start the wave                              │
│  /agent-status --merge     Merge completed tasks to main             │
│  /agent-status --reclaim   Reclaim tasks from stale terminals          │
│  /agent-status --abort     Cancel the active wave                      │
│  /agent-status --watch     Auto-refresh dashboard every 30s            │
│                                                              │
│  QUICK START                                                 │
│  1. /agent-status --plan     ← Claude proposes task breakdown          │
│  2. Review + "go"  ← You approve                             │
│  3. /agent-status --launch   ← Wave starts                             │
│  4. Open 2nd tab   ← Click + in VS Code terminal, type claude│
│  5. /agent-status --merge    ← After all tasks complete                │
└──────────────────────────────────────────────────────────────┘
```

This is read-only. Do not execute anything else.

---

## If `mode` is `"active"` — show the live dashboard:

```
┌────────────────────────────────────────────────────────────────┐
│  HQ · HH:MM - DD/MM/YY                                        │
├────────────────────────────────────────────────────────────────┤
│  WAVE    [waveId] · [feature]                                  │
│  MODE    [terminalMode] ([activeSessions] active)              │
│  STATUS  N/M tasks — X in progress · Y complete · Z pending   │
│                                                                │
│  TERMINALS                                                     │
│  [icon] [sessionId]  [claimedTask]  [model]  ♥ [ago]  [tok]   │
│  [icon] [sessionId]  [claimedTask]  [model]  ♥ [ago]  [tok]   │
│                                                                │
│  TASKS                                                         │
│  [icon] [taskId]  → [claimedBy]  [size]  [versionTag]  [status]│
│  [icon] [taskId]  → [claimedBy]  [size]  [versionTag]  [status]│
│                                                                │
│  CONFLICTS  [conflict details or "None detected"]              │
│  COST EST   ~[totalTokens] tokens (~[totalGBP])                │
│  MERGE      [task1] → [task2] → ... (in order)                │
└────────────────────────────────────────────────────────────────┘
```

### Card rules

- **WAVE:** `waveId` · `feature` from JSON
- **MODE:** `terminalMode` value + `activeSessions` count in parentheses
- **STATUS:** Show `totalTasks` total, then breakdown of `tasksInProgress`, `tasksCompleted`, `tasksPending`. If `tasksFailed` > 0, include that too.
- **TERMINALS:** One line per session. Use `●` for active (not stale), `○` for stale. Show `sessionId`, `claimedTask` (or "idle"), `model`, `♥` heartbeat ago, and `tokensUsed`. If no sessions registered, omit section.
- **TASKS:** One line per task. Icons: `⚪` pending, `🔵` in_progress, `🟢` completed, `🔴` failed. Show `taskId`, `→ claimedBy` (omit arrow if unclaimed), `size`, `versionTag`, `status`.
- **CONFLICTS:** If `conflicts` array is non-empty, show `⚠️` prefix with file and owners for each. Otherwise "None detected".
- **COST EST:** From `costEstimate.totalTokens` and `costEstimate.totalGBP`. If `actualTokensUsed` > 0, append "(used: N so far)".
- **MERGE:** Show `mergeOrder` as arrow-separated task IDs.
- **BORDER:** Size the box to fit the longest content line. All lines padded so the right border │ aligns.

This is read-only. Do not execute anything else.
