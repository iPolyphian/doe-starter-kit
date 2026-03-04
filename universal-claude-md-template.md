# Universal Learnings

Cross-project patterns that apply to any codebase. Auto-loaded by Claude Code at every session start.

<!-- 
Claude: short bullet points under descriptive ## headings. One learning per line.
Max 30 lines of content. When full, remove the least useful before adding new.
Only truly universal patterns here — project-specific learnings go in that project's learnings.md.
Tag source: e.g. "[retro: feature-name vX.Y.Z]"

## Python Execution

- When caching large API downloads to disk, always delete stale caches before re-running with different parameters (e.g. changed page size). A partial cache from a previous run will silently produce incomplete results. [retro: universal]
- macOS system Python 3.9 has an old OpenSSL that fails TLS 1.3 sites (`TLSV1_ALERT_PROTOCOL_VERSION`). Use `subprocess` + `curl` for downloads from sites requiring modern TLS. [retro: universal]

## Shell & Platform

- macOS `sed -i` requires an empty backup extension: `sed -i '' '...'`. Linux uses `sed -i '...'` with no argument. Git hooks and shell scripts must account for this or they'll fail silently on one platform. [retro: universal]
- Emojis render as double-width characters in terminal monospace fonts, breaking box-drawing border alignment. Never use emojis inside bordered ASCII boxes — use text-only labels. Emojis are fine in standalone/unbounded contexts. [retro: universal]
- zsh `for f in glob-*` fails with `no matches found` when no files match (bash silently skips). Guard with `(setopt nullglob 2>/dev/null; for f in ...)` or `ls glob-* 2>/dev/null`. [retro: universal]
- `$$` in Claude Code Bash tool calls is the subshell PID, not the parent Claude Code process. Each tool call gets a different `$$`. Don't use `$$` for cross-call file naming — use a fixed name instead (worktrees handle multi-session isolation). [retro: universal]

## Hooks & Session Files

- Hooks that write per-invocation files (e.g. per-PID tracking) will accumulate hundreds of orphans per session. Always write to a single fixed-name file and overwrite — hooks only need the latest state, not history. [retro: universal]

## Output

- Multi-section formatted output (wrap-ups, reports, dashboards) must be assembled and printed as a single block — never fragment across multiple tool calls. Generate the entire output in one script. [retro: universal]
- After generating formatted output (wrap-ups, dashboards) via a Bash/Python script, re-present the full output as text in your response. Tool output alone is not sufficient — the user expects it as your actual reply. Never summarise what was already generated; echo it in full. [retro: universal]

## Verification

- After creating or editing files, verify with `ls`/`cat`/`grep` before reporting success. Don't skip this even for "obvious" edits. [retro: universal]
-->
