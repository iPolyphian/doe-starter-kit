Help the user submit a feature request for the DOE starter kit. Guide them through a conversational flow, then file it as a GitHub issue.

## Conversational Flow

Walk through these 5 phases. Keep each phase brief — one question, one response. Do not dump all questions at once.

### Phase 1: Spark
Ask: "What would you like to see in the DOE framework? Describe it in plain language — no technical terms needed."

Wait for their response before continuing.

### Phase 2: Pain
Ask: "What's the workaround right now? How are you currently handling this without the feature?"

Wait for their response before continuing.

### Phase 3: Picture
Ask: "If this existed perfectly, what would using it look like? Walk me through a scenario."

Wait for their response before continuing.

### Phase 4: Analysis

Run these checks silently (no need to show raw output to the user):

1. **Overlap scan:** `python3 ~/doe-starter-kit/execution/doe_feature_request.py --scan-existing "<user's description>"`
   - If overlaps found, tell the user: "I found some related existing features: [list]. Your request might extend these, or it might be genuinely new. I'll note the overlap."

2. **Duplicate check:** `python3 ~/doe-starter-kit/execution/doe_feature_request.py --search-duplicates "<user's description>"`
   - If duplicates found, tell the user: "There's an existing issue that might cover this: [#N title]. Want to add your perspective to that issue instead, or file a new one?"
   - If they choose to add context, use `gh issue comment` to append.

3. **Categorise:** `python3 ~/doe-starter-kit/execution/doe_feature_request.py --categorise "<user's description>"`
   - Use the result for labelling. Don't ask the user about categories.

4. **Sanitise:** `python3 ~/doe-starter-kit/execution/doe_feature_request.py --sanitise "<user's full input>"`
   - Sanitise all user input before including in the issue body.

### Phase 5: Draft + File

Build a structured draft and present it in a bordered box. **Generate programmatically** — define `W = 60`, define `line(c)` as `f"│  {c}".ljust(W + 1) + "│"`, then pass ALL rows through `line()`.

```
┌────────────────────────────────────────────────────────────┐
│  DOE FEATURE REQUEST                                       │
├────────────────────────────────────────────────────────────┤
│  TITLE: [concise title]                                    │
│  AREA:  [Commands/Execution/Directives/Hooks/Docs/Structure]│
│                                                            │
│  PROBLEM                                                   │
│  [pain point from Phase 2, sanitised]                      │
│                                                            │
│  CURRENT WORKAROUND                                        │
│  [workaround from Phase 2]                                 │
│                                                            │
│  DESIRED OUTCOME                                           │
│  [picture from Phase 3]                                    │
│                                                            │
│  OVERLAP                                                   │
│  [related features found, or "None detected"]              │
│                                                            │
│  LABELS: enhancement, user-requested [, quick-win]         │
├────────────────────────────────────────────────────────────┤
│  File this? (yes / edit / cancel)                          │
└────────────────────────────────────────────────────────────┘
```

If the user says **yes**: Save the draft as JSON, then run `python3 ~/doe-starter-kit/execution/doe_feature_request.py --file <json_path>`. If gh fails, automatically run `--fallback` to save locally and tell the user where the file is.

If the user says **edit**: Ask what to change, update the draft, re-present.

If the user says **cancel**: Acknowledge and stop.

## Rules

- Keep the conversation brief and natural. Don't be robotic.
- Sanitise ALL user input before including in the issue body — no exceptions.
- If `~/doe-starter-kit` doesn't exist, skip the overlap scan and note it.
- If `gh` is unavailable, use the local fallback and tell the user how to file manually later.
- Do not file without the user's explicit approval ("yes" or equivalent).
- The `quick-win` label is your judgment call — add it if the feature seems achievable in 1-2 sessions with no dependencies. When in doubt, omit it.
