# Directive: Self-Annealing

## Goal
Turn every failure into a system improvement. Classify, log, and prevent recurrence through learnings, directives, and hooks.

## When to Use
Loaded when something fails, during learnings curation, or when performance degradation is suspected.

## Failure Response

When something fails: read the full error -> diagnose WHY (not just what) -> fix -> retest -> log.

### Classify Before Writing
- **Project-specific** (references this project's configs, names, custom setup) -> add to `learnings.md`
- **Universal** (general pattern any project could hit) -> add to `~/.claude/CLAUDE.md`

### Severity Levels

**Routine failures:** One-line learning with source tag.
Example: `- macOS sed -i requires '' backup arg. [retro: feature-name]`

**Significant failures** (cost >30 min, broke production, recurred): Structured format in learnings.md:
```
### Learning: [title]
**What happened:** [description]
**Root cause:** [WHY -- context pollution? Ambiguous spec? Missing constraint?]
**Fix applied:** [what changed]
**Prevention:** [rule/hook/directive added, or "none needed -- one-off"]
[source tag]
```

**Test failures** (auto fails, regression, contract wrong): Structured format. Bad contracts get root cause "criteria didn't capture actual requirement" -- update guidance.

### Escalation
Recurring patterns (logged 3+ times) -> create a directive or hook. Single occurrences -> one-line learning is sufficient.

## Performance-Triggered Curation

Watch for these degradation symptoms -- they indicate the learnings/directives system needs maintenance:

### Degradation Symptoms
- 10+ consecutive `[quick: nothing to log]` retros -- suspicious, suggests retros are being rubber-stamped
- Same mistake recurring across sessions despite being logged -- learning isn't being checked or is poorly worded
- Agent frequently re-reading files it should know about -- context management is degraded
- Steps taking significantly longer than similar past steps -- accumulated context weight or missing patterns
- Contracts failing on criteria that previously passed -- regression in code or stale contracts

### When to Curate
Every 100 sessions (tracked in STATE.md `## Curation`):
1. Run `/doe-health` first -- use the grade and suggestions to inform what needs pruning
2. Review all entries in learnings.md and ~/.claude/CLAUDE.md
3. For each: still accurate? referenced? actionable? redundant?
4. Check quick-retro drift (see degradation symptoms above)
5. Present KEEP/EDIT/REMOVE/ESCALATE proposals for user approval

`/crack-on` and `/stand-up` check if curation is due at session start.

### Performance Monitoring
Track these signals across sessions (via `.claude/stats.json`):
- Steps completed per session (trending down = problem)
- Commits per session (consistently low = problem)
- INFRA vs APP ratio (heavily skewed = shipping debt)
- Time patterns (sessions getting longer for same-complexity work)

## Retro Quality

Every feature gets a mandatory retro. The retro is where self-annealing happens. For the canonical retro format (quick/full levels, procedure, wave deferred retros), see `directives/delivery-rules.md` ## Retro Discipline.

The purpose of retros is to feed the self-annealing loop. A retro that logs nothing is fine if nothing surprising happened. A retro that SHOULD have logged something but didn't is a system failure.
