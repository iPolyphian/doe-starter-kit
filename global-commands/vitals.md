Run a quick workspace health check. Show results in a compact bordered summary.

## Checks

Run all 5 checks, then display results together:

1. **Git status** — Run `git status`. Flag uncommitted changes (modified, staged, untracked). Clean = no changes.
2. **Quick audit** — Run `python3 execution/audit_claims.py --hook` (fast checks only). Record PASS/WARN/FAIL counts. If the script doesn't exist, skip and show `Audit: no audit script`.
3. **DOE Kit sync** — If `~/doe-starter-kit` exists, check two things: (1) Is the kit tag newer than STATE.md's "DOE Starter Kit" version? (inbound). (2) Do any key syncable files differ? (outbound). Diff key syncable files (`~/.claude/commands/*.md` vs kit's `global-commands/*.md`, `.githooks/*`, `.claude/hooks/*`). For CLAUDE.md, only compare universal sections (Operating Rules, Guardrails, Code Hygiene, Self-Annealing, Break Glass) — ignore project-specific additions. If either condition is true, show `*`. If the directory doesn't exist, show `DOE Kit: not installed`.
4. **STATE.md alignment** — Read STATE.md's "Active feature" line and compare with `tasks/todo.md` ## Current heading. Flag if they disagree (e.g. STATE says "None" but todo has a current feature, or vice versa).
5. **Temp files** — Check `.tmp/` for files older than 24 hours. Flag stale files by name.

## Output Format

Show all results in a single bordered block:

If all clear:
```
  🩺 VITALS
  ┌──────────────────────────────────────────────────────────┐
  │  Git:     Clean ✓                                        │
  │  Audit:   5 PASS · 0 WARN · 0 FAIL ✓                    │
  │  DOE Kit: v1.3.0 ✓                                        │
  │  STATE:   Aligned ✓ (Constituency Comparison v0.16.x)    │
  │  .tmp/:   Clean ✓                                        │
  ├──────────────────────────────────────────────────────────┤
  │  All clear — ready to go.                                │
  └──────────────────────────────────────────────────────────┘
```

If issues found, show details inline:
```
  🩺 VITALS
  ┌──────────────────────────────────────────────────────────┐
  │  Git:     3 uncommitted files ⚠️                          │
  │           M ROADMAP.md, M STATE.md, M tasks/todo.md      │
  │  Audit:   3 PASS · 1 WARN · 0 FAIL ⚠️                    │
  │           WARN: learnings.md — 2 minor versions behind   │
  │  DOE Kit: v1.3.0 * ⚠️                                      │
  │  STATE:   Aligned ✓                                      │
  │  .tmp/:   1 stale file ⚠️ (last-audit.txt)                │
  ├──────────────────────────────────────────────────────────┤
  │  3 items need attention.                                 │
  └──────────────────────────────────────────────────────────┘
```

## Rules

- Show ALL 5 checks every time, even if they pass — the bordered block should always have the same structure so it's scannable.
- Use ✓ for passing checks, ⚠️ for issues.
- **Audit detail lines are mandatory.** When the audit has any WARN or FAIL findings, show each non-PASS item on its own indented line below the summary. Format: `│           WARN: <file> — <message>  │` (or `FAIL:` prefix for failures). Use the `--json` flag (`python3 execution/audit_claims.py --hook --json`) to parse findings reliably. If all PASS, no detail lines needed.
- The summary line at the bottom counts how many checks have issues. If 0, say "All clear — ready to go."
- Keep it compact — this should be a 5-second glance, not a report.
- **Generate the box programmatically** — define a `line(content)` helper: `f"│  {content}".ljust(W + 1) + "│"` where W is computed from the longest content line. ALL rows MUST use this helper — never construct `f"│{...}│"` manually. Never hand-pad bordered output.
- Do NOT fix any issues automatically. Just report them. The user decides what to act on.
