# Directive: DOE Starter Kit Sync

## Goal
Keep the universal DOE Claude Code Starter Kit repository in sync with improvements made during project work. When a project improves the DOE system itself (new directives, better rules, new commands, workflow refinements), those improvements should flow back to the starter kit — stripped of all project-specific content.

## When to Sync
- After completing an [INFRA] feature that changed DOE files (CLAUDE.md, todo.md format rules, directives, commands, hooks, audit script)
- After a retro identifies a new universal learning that was added to learnings.md or ~/.claude/CLAUDE.md
- After creating a new directive or command that would benefit other projects
- When explicitly asked to sync

## How to Sync

### Step 1: Add the starter kit directory
```
/add-dir ~/doe-starter-kit
```

### Step 2: Check if anything changed
Compare files that exist in both the current project and the starter kit. If all syncable files are identical, say "Starter kit is up to date — nothing to sync" and stop.

Files to compare:
- CLAUDE.md (rules, triggers, directory structure)
- tasks/todo.md (format rules only — not task content)
- directives/*.md (universal ones only)
- execution/audit_claims.py (universal checks only)
- ~/.claude/commands/*.md (global commands)
- .githooks/* (hook scripts)
- .claude/hooks/*.py (guardrail hooks)
- SYSTEM-MAP.md (structure documentation)
- .claude/claude-chat-sync-prompt.md

### Step 3: Strip project-specific content
Before copying anything to the starter kit, remove ALL project-specific references:
- Project names (e.g. "Monty", "Broker Platform")
- Project-specific file paths (e.g. monty-app-v0.12.3.html)
- Project-specific data (constituency names, API endpoints)
- Project-specific audit checks (only `@register("universal")` checks go to starter kit)
- Project-specific directives (only universal SOPs go to starter kit)
- Project-specific governed documents in the registry (only learnings.md stays)

Replace with generic equivalents:
- "Monty" → "[project name]" or remove entirely
- Specific HTML filenames → "your-app.html"
- Project-specific examples → generic examples

### Step 4: Apply changes
Copy stripped files to the starter kit directory. For files that exist in both:
- Diff first, show what's changing
- Preserve any starter-kit-only content (e.g. setup instructions, template comments)

### Step 5: Verify
```bash
# Zero project-specific references
grep -ri "monty\|broker\|pleasantly" ~/doe-starter-kit/ --include="*.md" --include="*.py" --include="*.json"

# Audit script has only universal checks
grep '@register(' ~/doe-starter-kit/execution/audit_claims.py

# Extension point comment exists
grep 'yourproject' ~/doe-starter-kit/execution/audit_claims.py

# Commands are project-agnostic
grep -ri "monty\|broker" ~/.claude/commands/
```

### Step 6: Commit to starter kit
```bash
cd ~/doe-starter-kit
git add -A
git diff --staged --stat
# Show diff, wait for sign-off
git commit -m "Sync from [project]: [what changed]"
git push
```

## What NOT to sync
- Task content (todo.md items, archive.md history)
- STATE.md session content
- stats.json data
- Project-specific learnings (only universal patterns)
- Project-specific directives
- Project-specific audit checks
- .env files
- .tmp/ contents

## Edge Cases
- If a format rule was added to todo.md, sync the rule itself but not the tasks
- If a new trigger was added to CLAUDE.md, check if it references project-specific directives — if so, genericize the directive path
- If a new command references project-specific files, either genericize it or don't sync it
- If audit_claims.py gained new universal checks, sync those but leave the extension point comment intact
