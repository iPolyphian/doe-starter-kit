Report a bug in the DOE framework. This command acts as a triage-first system: it gathers context, checks if the issue is already fixed, detects user error, searches for duplicates, and only files a GitHub Issue if it's a genuine new bug.

**All bordered output MUST be generated programmatically.** Define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is the inner width (compute from content). ALL rows including headers MUST use this helper — never construct `f"│{...}│"` manually. Use Unicode box-drawing characters (`┌─┐`, `├─┤`, `└─┘`, `│`). Content inside borders must be ASCII-only — no emojis, use `--` for separators.

## Phase 1: Gather

**User's account:** If $ARGUMENTS was provided, use that as the initial description. Otherwise ask: "What were you trying to do, and what went wrong?" Wait for the user's response before continuing.

**Claude's reconstruction:** From the current conversation context, reconstruct:
- What command or script was being used when the issue occurred
- What error messages or unexpected behaviour appeared
- What was attempted to fix it (if anything)
- The sequence of events leading to the problem

If there's no relevant conversation context (user is reporting from memory), note that and rely more heavily on the user's account.

**Environment capture:** Run the execution script to gather system info:

```bash
python3 execution/doe_bug_report.py --environment
```

Parse the JSON output. Present the environment in a bordered card:

```
┌──────────────────────────────────────────────────┐
│  ENVIRONMENT                                      │
├──────────────────────────────────────────────────┤
│  DOE Kit     v1.41.0                              │
│  OS          Darwin 25.3.0                        │
│  Node        v18.16.0                             │
│  Python      3.9.6                                │
│  Shell       /bin/zsh                             │
│  Branch      master                               │
└──────────────────────────────────────────────────┘
```

**Project type:** Ask: "What type of project are you working on? (a) Static HTML, (b) Next.js/Vite/React, (c) React Native/Expo, (d) Flutter, (e) Other"

Wait for their response. Map to labels: a = `project:html`, b = `project:web-framework`, c = `project:react-native`, d = `project:flutter`, e = `project:other`. Also note the project type for the issue body — it helps narrow which DOE components are involved (e.g. Playwright vs Maestro, serve vs dev server).

**Severity:** Ask: "How much did this block you? (a) Completely blocked, (b) Found a workaround, (c) Minor annoyance"

Wait for their response. Map to labels: a = `severity:blocking`, b = `severity:workaround`, c = `severity:cosmetic`.

**Reproducibility:** Then ask: "Does this happen every time, or was it a one-off?"

Wait for their response before proceeding to Phase 2.

## Phase 2: Gate — Version Check

Run the version check:

```bash
python3 execution/doe_bug_report.py --version-check
```

Parse the JSON output. Present the result in a bordered card:

**If up to date (is_behind = false):**
```
┌──────────────────────────────────────────────────┐
│  VERSION CHECK                            PASSED  │
├──────────────────────────────────────────────────┤
│  Local: v1.41.0  Latest: v1.41.0                  │
│  You are on the latest version.                   │
└──────────────────────────────────────────────────┘
```

**If behind and fix found:**
```
┌──────────────────────────────────────────────────┐
│  VERSION CHECK                       FIX FOUND    │
├──────────────────────────────────────────────────┤
│  Local: v1.39.0  Latest: v1.41.0                  │
│  This looks like it was fixed in v1.40.0:         │
│                                                   │
│  v1.40.0 -- [relevant changelog entry]            │
│                                                   │
│  Run /pull-doe to update your DOE kit.            │
└──────────────────────────────────────────────────┘
```

**Stop here if fix found — do not file an issue.**

If behind but no relevant fix in changelog, or if version check errors: continue to Phase 3.

## Phase 3: Gate — User Error Detection

This is a judgment call. Based on the user's description and Claude's reconstruction, assess whether this is:
- **A DOE framework bug** — something in the DOE kit itself is broken (a command, hook, script, or directive behaves incorrectly)
- **A usage mistake** — the user is using DOE correctly but misunderstands a feature, or their project code has an issue

Signs of user error: the error is in their project code (not in `execution/`, `global-commands/`, `.githooks/`, or `.claude/hooks/`), they're using a command with wrong arguments, their project config is missing required fields.

Signs of a framework bug: a DOE command crashes or produces wrong output, a hook blocks valid actions, an execution script fails on valid input, documentation is wrong or misleading.

If you assess this as user error:
1. Explain what went wrong and how to fix it
2. Scan tutorials for relevant documentation:

```bash
python3 execution/doe_bug_report.py --scan-tutorials "<relevant keywords>"
```

3. Present in a bordered card:

```
┌──────────────────────────────────────────────────┐
│  USER ERROR DETECTED                              │
├──────────────────────────────────────────────────┤
│  [1-2 line explanation of what went wrong]        │
│                                                   │
│  HOW TO FIX                                       │
│  [Clear fix instructions]                         │
│                                                   │
│  DOCS                                             │
│  -- [page] > [section]                            │
│  -- [page] > [section]                            │
│                                                   │
│  No issue filed -- this is a usage question.      │
└──────────────────────────────────────────────────┘
```

**Stop here — do not file an issue.**

If uncertain, err on the side of filing — false positives are better than lost bug reports.

## Phase 4: Gate — Duplicate Search

Search for existing issues that might match:

```bash
python3 execution/doe_bug_report.py --search-duplicates "<keywords from the bug description>"
```

If matches are found, present in a bordered card:

```
┌──────────────────────────────────────────────────┐
│  DUPLICATE CHECK                     N MATCHES    │
├──────────────────────────────────────────────────┤
│  #12  [/snagging] crashes on empty manual items   │
│       severity:blocking  v1.39.0  opened 15/03    │
│                                                   │
│  #8   [snagging] no output when todo.md empty     │
│       severity:cosmetic  v1.38.0  opened 12/03    │
│                                                   │
│  Is this the same as one of these?                │
│  Say the issue number to add your context,        │
│  or "new" to file a separate report.              │
└──────────────────────────────────────────────────┘
```

- If the user picks an issue number: add their context as a comment using `--add-comment`, then stop.
- If the user says "new" or it's different: continue to Phase 5.

If no matches or search fails: continue to Phase 5.

## Phase 5: Draft, Sanitise, and File

**Assemble the draft issue:**

Title: A concise summary (under 80 chars). Format: "[component] brief description" — e.g. "[/snagging] crashes when no manual items exist"

Body: Use this structure:
```
## Summary
[2-3 sentence description combining user's account and Claude's reconstruction]

## Environment
| Field | Value |
|-------|-------|
| DOE Kit Version | [from --environment] |
| Project Type | [from user response — html/web-framework/react-native/flutter/other] |
| OS | [os + version] |
| Node | [version] |
| Python | [version] |
| Shell | [shell] |

## Steps to Reproduce
[Numbered list of steps to reproduce the issue]

## Expected vs Actual
**Expected:** [what should have happened]
**Actual:** [what actually happened]

## Claude's Analysis
[Claude's reconstruction of what went wrong technically — which component failed and why]

## User's Description
[The user's own words about the problem — verbatim or lightly edited for clarity]

## Severity
[blocking / workaround / cosmetic]

## Reproducibility
[every time / intermittent / one-off]

---
*Filed via `/report-doe-bug` from DOE Kit [version]*
```

**Sanitise the draft:**

```bash
python3 execution/doe_bug_report.py --sanitise "<full draft body>"
```

This strips API keys, secrets, absolute paths, and email addresses. Review the sanitised output — if it removed something that was actually needed for the bug report (e.g. a path that's part of the error), add it back in generic form (e.g. `~/project/src/file.js` instead of the absolute path).

**Present the draft in a bordered card:**

```
┌──────────────────────────────────────────────────────────────┐
│  DRAFT ISSUE                                                  │
├──────────────────────────────────────────────────────────────┤
│  TITLE   [/snagging] crashes when no manual items exist       │
│  LABELS  bug, user-reported, v1.41.0, severity:blocking,      │
│          project:html                                         │
│                                                               │
│  SUMMARY                                                      │
│  [2-3 sentence summary]                                       │
│                                                               │
│  STEPS TO REPRODUCE                                           │
│  1. [step]                                                    │
│  2. [step]                                                    │
│                                                               │
│  EXPECTED: [what should happen]                               │
│  ACTUAL:   [what happened]                                    │
│                                                               │
│  CLAUDE'S ANALYSIS                                            │
│  [Technical reconstruction]                                   │
│                                                               │
│  USER'S DESCRIPTION                                           │
│  [Their words]                                                │
│                                                               │
│  Severity: blocking  Reproducibility: every time              │
├──────────────────────────────────────────────────────────────┤
│  Say "file it" to submit, or tell me what to change.          │
└──────────────────────────────────────────────────────────────┘
```

**File or fallback:**

If the user approves:

```bash
python3 execution/doe_bug_report.py --file-issue "<title>" "<sanitised body>" "bug,user-reported,<version>,<severity>,<project-type>"
```

Present the result in a bordered card:

**If filed successfully:**
```
┌──────────────────────────────────────────────────┐
│  BUG REPORT FILED                                 │
├──────────────────────────────────────────────────┤
│  Issue: #N -- [title]                             │
│  URL:   https://github.com/.../issues/N           │
│  Labels: bug, user-reported, v1.41.0              │
│                                                   │
│  You will get updates via GitHub notifications.   │
└──────────────────────────────────────────────────┘
```

**If fell back to local file:**
```
┌──────────────────────────────────────────────────────────────┐
│  BUG REPORT SAVED LOCALLY                                     │
├──────────────────────────────────────────────────────────────┤
│  Could not reach GitHub. Report saved to:                     │
│  .tmp/doe-bug-report-20260318-134500.md                       │
│                                                               │
│  To file manually:                                            │
│  1. Go to github.com/williamporter/doe-starter-kit/issues/new │
│  2. Copy the title and body from the saved file               │
│  3. Add the labels listed in the file                         │
└──────────────────────────────────────────────────────────────┘
```

## Behavioural Rules

- **Sanitise aggressively.** The upstream repo is public. Never include API keys, .env values, project-specific source code, or identifiable paths. When in doubt, redact.
- **Neutral tone.** Don't blame the user or the framework. Present facts.
- **Don't file unless all gates pass.** The goal is quality over quantity — one well-documented bug report is worth ten vague ones.
- **One question at a time.** Never present multiple questions in a single message. Ask, wait for the response, then continue.
- **Respect the user's time.** Move through phases efficiently. Don't ask unnecessary questions. If the conversation already contains the answers, use them.
- **Be transparent about limitations.** If you can't determine whether something is a framework bug or user error, say so and let the user decide.
