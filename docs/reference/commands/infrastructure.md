# Infrastructure & Maintenance Commands

These commands handle the plumbing — keeping the framework updated, checking what's installed, and managing the connection between your project and the DOE Starter Kit it was built from.

---

## /pull-doe

**What it does:** Pulls the latest updates from the DOE Starter Kit into your project.

**When to use it:** When the starter kit has been updated (new commands, bug fixes, improved hooks) and you want those improvements in your project.

**How it works:**

1. Checks the current starter kit version your project is using.
2. Checks the latest version available.
3. Shows you what changed between versions (a changelog).
4. Applies the updates safely, without overwriting your project-specific customisations.

**What to expect:**

```
Current version: v1.29.0
Latest version: v1.30.1

Changes in v1.30.1:
  - New: /codemap command for project indexing
  - Fixed: /wrap streak calculation off-by-one
  - Improved: Pre-commit hook now checks for trailing whitespace

Apply update? (y/n)
```

The update is non-destructive. If you've customised a file that the update also changes, you'll be shown the conflict and asked how to resolve it.

---

## /commands

**What it does:** Shows all available slash commands, their status, and version information.

**When to use it:** When you want to see what commands are available, check if something is installed correctly, or troubleshoot a missing command.

**How it works:** Scans the `.claude/commands/` directory and checks each command file against expected conventions: does it exist, is it properly formatted, is it the latest version?

**What to expect:**

```
┌─ Commands ──────────────────────────────────┐
│ Session                                      │
│   /stand-up       ✓ installed                │
│   /crack-on       ✓ installed                │
│   /sitrep         ✓ installed                │
│   /wrap           ✓ installed                │
│   /eod            ✓ installed                │
│                                              │
│ Quality                                      │
│   /audit          ✓ installed                │
│   /fact-check     ✓ installed                │
│   /review         ✓ installed                │
│   /agent-verify   ✓ installed                │
│   /test-suite     ✓ installed                │
│   /codemap        ✓ installed                │
│                                              │
│ Visual                                       │
│   /project-recap  ✓ installed                │
│   /diff-review    ✓ installed                │
│   ...                                        │
│                                              │
│ Framework: DOE Starter Kit v1.30.1           │
│ All commands operational.                    │
└──────────────────────────────────────────────┘
```

If a command is missing or broken, the output will tell you what's wrong and how to fix it (usually a `/pull-doe` will resolve it).

---

## /hq

**What it does:** Shows a project dashboard — a bird's-eye view of session history, feature timelines, and metrics across your projects and over time.

**When to use it:** When you want the big picture. How many sessions have you run? What features have you shipped? What's your commit velocity? This is the "zoom all the way out" view.

**What to expect:**

```
┌─ HQ Dashboard ──────────────────────────────┐
│                                              │
│ Project: my-project                          │
│ Sessions: 117 total, 12-day streak           │
│ Features shipped: 14                         │
│ Current: Targeting Page v2 (90%)             │
│                                              │
│ This week:                                   │
│   Mon ████████ 4 sessions, 12 commits        │
│   Tue ██████   3 sessions, 8 commits         │
│   Wed ████     2 sessions, 5 commits         │
│                                              │
│ Recent features:                             │
│   Targeting Page v2    ██████████░ 90%        │
│   Home Page Rebuild    ████████████ Done      │
│   Data Pipeline v3     ████████████ Done      │
│                                              │
│ All-time: 117 sessions, 847 commits          │
│           +34,291 / -12,847 lines            │
└──────────────────────────────────────────────┘
```

This is a read-only, feel-good command. It doesn't change anything — it just shows you what you've built. Useful for motivation, for reporting to others, or for spotting trends (are sessions getting shorter? are you shipping more per session?).

---

## When to Use These Commands

| Situation | Command |
|-----------|---------|
| "Is my framework up to date?" | `/pull-doe` |
| "What commands do I have?" | `/commands` |
| "Show me the big picture" | `/hq` |

These are maintenance commands — you won't use them every session. `/commands` is useful when getting started. `/pull-doe` is worth running every week or two. `/hq` whenever you want perspective.
