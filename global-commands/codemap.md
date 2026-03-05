Generate a structured project index at `.claude/codemap.md`. This helps agents navigate the codebase quickly without re-exploring each session.

## Process

1. Scan the project file tree (exclude `.tmp/`, `node_modules/`, `.git/`, `__pycache__/`, build artefacts)
2. Read the first 5 lines of each significant file (skip binary, generated, and data files)
3. Generate `.claude/codemap.md` with these sections:

### Structure
```
## Project Structure
[directory tree with 1-line description per directory]

## Key Files
[table: file | purpose | last modified]
Files that define architecture, entry points, config, or APIs.

## Data Flow
[brief description of how data moves through the system]
From input (APIs, files, user) → processing (execution scripts) → output (UI, files, services)

## Active Patterns
[bullet list of reusable patterns found in the codebase]
E.g. "Card builder: buildXxxHTML(code, props) returns info-card div"
E.g. "Import scripts: fetch → transform → write to src/data/"
```

4. After generating, show a brief summary: file count, key directories, any structural observations

## Rules
- Do NOT include file contents -- just structure and purpose
- Do NOT include .tmp/, node_modules/, or build artefacts
- Keep the codemap under 100 lines -- this is a navigation aid, not documentation
- If `.claude/codemap.md` already exists, overwrite it (it's always regenerated fresh)
- Use relative paths from project root

## When called from /wrap
If `/wrap` detects structural changes (new/moved/deleted files since last commit), it will ask: "Structural changes detected -- run /codemap?" Only regenerate if the user says yes.
