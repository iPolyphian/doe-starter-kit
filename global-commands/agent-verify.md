Verify contract criteria for the current task. Works in both solo mode (todo.md) and wave mode (wave JSON).

## Step 1: Determine mode and load criteria

Check if you're in a wave worktree:
```
python3 ~/.claude/scripts/multi_agent.py --dashboard --json 2>/dev/null
```

- **Wave mode** (active wave with a claimed task): extract `acceptanceCriteria` from the task JSON.
- **Solo mode** (no active wave or not in a worktree): read criteria from `tasks/todo.md` using:
  ```
  python3 -c "
  import json, sys; sys.path.insert(0, '.'); from execution.verify import parse_todo_contract
  criteria = parse_todo_contract()
  print(json.dumps(criteria, indent=2))
  "
  ```

If no criteria are found, show "No contract criteria found for the current step" and stop.

## Step 2: Run build step

Run the build command from `tests/config.json` (if configured):
```
python3 -c "
import sys; sys.path.insert(0, '.'); from execution.verify import run_build_step
result = run_build_step()
if result: print(f'Build: [{result[\"status\"]}] {result[\"detail\"]}')
else: print('Build: no build command configured')
"
```

If the build fails, show the error and stop -- verification results would be meaningless.

## Step 3: Run [auto] criteria

For each `[auto]` criterion with a `Verify:` pattern, run it through verify.py:
```
python3 -c "
import json, sys; sys.path.insert(0, '.'); from execution.verify import run_criterion
result = run_criterion('<verify_pattern>')
print(json.dumps(result))
"
```

Collect all results. Show a bordered results card:

```
+-------------------------------------------------+
|  VERIFY -- Step N: [step description]            |
+-------------------------------------------------+
|  [PASS] file: src/foo.js exists                  |
|  [FAIL] run: python3 -m pytest                   |
|         Exit code 1: ...                         |
|  [SKIP] html: index.html has .bar                |
|         beautifulsoup4 not installed              |
+-------------------------------------------------+
|  Result: N/M passed                              |
+-------------------------------------------------+
```

Use simple ASCII borders (`+`, `-`, `|`). No emojis inside the box.

## Step 4: Auto-fix loop (if failures)

If any `[auto]` criterion fails:

1. Attempt to fix the issue (read the error, identify the cause, make the change)
2. Re-run ALL `[auto]` criteria (not just the failed ones -- fixes can break other things)
3. Repeat up to 3 times total
4. After each fix attempt, show which attempt it is: "Fix attempt 1/3", "Fix attempt 2/3", etc.

If all criteria pass after a fix, commit the fix:
```
git add <changed-files> && git commit -m "fix: verification failure in [criterion]"
```

If after 3 attempts criteria still fail, stop and report:
```
Verification failed after 3 fix attempts. Remaining failures:
  [FAIL] <criterion>
         <detail>
Escalate to the user.
```

## Step 5: Present [manual] criteria

After all `[auto]` criteria pass, present each `[manual]` criterion as a yes/no question to the user:

```
Manual verification required:
  1. [description of what to check]
     Pass? (yes/no)
```

Wait for user response on each. If any manual criterion fails, note it but continue with the others.

## Step 6: Conditional /review gate

Check if a code review is needed:

```
CURRENT_HASH=$(git diff --staged | md5)
LAST_HASH=$(cat .tmp/.review-ran 2>/dev/null || echo "none")
```

- If `CURRENT_HASH == LAST_HASH`: skip review (no new changes since last review)
- If `CURRENT_HASH != LAST_HASH`: suggest running `/review` before committing

This is advisory, not blocking. Show: "Code changed since last review -- consider running /review" or "No new changes -- review still valid."

## Step 7: Summary

Show final summary:

```
+--------------------------------------------------+
|  VERIFICATION COMPLETE                            |
+--------------------------------------------------+
|  Auto:    N/M passed                              |
|  Manual:  N/M confirmed                           |
|  Review:  current / stale / skipped               |
|  Result:  ALL PASS / X FAILURES                   |
+--------------------------------------------------+
```

If all pass, the step is ready to be marked `[x]` in todo.md (solo) or `--complete` (wave).

## Important notes

- NEVER mark a step done in todo.md from this command -- that's the caller's responsibility
- SKIP counts as pass (dependency not available, not a code problem)
- Always run ALL criteria, even if early ones fail -- the full picture helps diagnosis
- If `execution/verify.py` doesn't exist, show an error and stop
