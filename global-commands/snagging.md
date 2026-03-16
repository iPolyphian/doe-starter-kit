Generate (or regenerate) the manual test checklist for the current feature.

## Step 1: Identify the target feature

If arguments were passed (e.g. `/snagging Pulse 2.0`), use that as the feature name.

Otherwise, read `tasks/todo.md` and `STATE.md` to identify the current in-progress feature and its unchecked `[manual]` items.

If no unchecked `[manual]` items exist for the current feature, check `## Awaiting Sign-off` in `tasks/todo.md` for features with pending manual items.

If nothing is found anywhere, report: "No manual tests pending." and stop.

## Step 2: Offer automated code trace

If automated code trace verification hasn't been run yet for this feature's `[manual]` items, offer:

```
Some [manual] items may be verifiable by code trace. Run automated checks first to reduce manual testing burden? (yes/no)
```

If yes, perform a code trace on the relevant files. If any bugs are found, write them to `.tmp/test-bugs.json`:

```json
[{"title": "Bug title", "description": "Description", "file": "path/to/file.js", "line": 123, "severity": "High|Medium|Low", "found_by": "automated code trace"}]
```

If no, or if bugs file doesn't exist after trace, proceed without `--bugs`.

## Step 3: Run the generator

```bash
python3 execution/generate_test_checklist.py [--feature "Name"] [--bugs .tmp/test-bugs.json]
```

Include `--feature` if targeting a named feature. Include `--bugs` only if `.tmp/test-bugs.json` exists.

## Step 4: Report

Show a brief summary:

```
┌──────────────────────────────────────────────────┐
│  TEST CHECKLIST -- [Feature name]                │
├──────────────────────────────────────────────────┤
│  Manual checks:  N items                         │
│  Bugs surfaced:  N (or none)                     │
│  Checklist:      open in browser                 │
└──────────────────────────────────────────────────┘
```

Use Unicode box-drawing characters (`┌─┐`, `├─┤`, `└─┘`, `│`). No emojis inside the box.

Then tell the user:

```
Work through the checklist, then paste the exported results back here.
I'll fix any failures and regenerate.
```

## Important notes

- If `execution/generate_test_checklist.py` doesn't exist, report the error and stop — do not generate a checklist inline
- Arguments override auto-detection: `/snagging Feature Name` always targets that feature
- Clean up `.tmp/test-bugs.json` after the checklist is generated (it's ephemeral)
