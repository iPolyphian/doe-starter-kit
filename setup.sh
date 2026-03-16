#!/bin/bash
# DOE Starter Kit — one-command setup
# Installs global commands, hooks, scripts, and settings. Activates git hooks.
# Safe to run repeatedly (updates in place, never overwrites user config).

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMANDS_SRC="$SCRIPT_DIR/global-commands"
COMMANDS_DST="$HOME/.claude/commands"
HOOKS_SRC="$SCRIPT_DIR/global-hooks"
HOOKS_DST="$HOME/.claude/hooks"
SCRIPTS_SRC="$SCRIPT_DIR/global-scripts"
SCRIPTS_DST="$HOME/.claude/scripts"
SETTINGS_FILE="$HOME/.claude/settings.json"

# Get kit version from latest git tag (fall back to "unknown")
KIT_VERSION=$(cd "$SCRIPT_DIR" && git describe --tags --abbrev=0 2>/dev/null || echo "unknown")
TODAY=$(date +%d/%m/%y)

# 1. Install commands
mkdir -p "$COMMANDS_DST"
COMMAND_COUNT=0
for f in "$COMMANDS_SRC"/*.md; do
    fname=$(basename "$f")
    # Skip README.md — it's the GitHub directory readme, not a command
    if [ "$fname" = "README.md" ]; then
        continue
    fi
    cp "$f" "$COMMANDS_DST/$fname"
    COMMAND_COUNT=$((COMMAND_COUNT + 1))
done

# 2. Install global hooks
mkdir -p "$HOOKS_DST"
HOOK_COUNT=0
for f in "$HOOKS_SRC"/*.py; do
    [ -f "$f" ] || continue
    cp "$f" "$HOOKS_DST/$(basename "$f")"
    HOOK_COUNT=$((HOOK_COUNT + 1))
done

# 3. Install global scripts
mkdir -p "$SCRIPTS_DST"
SCRIPT_COUNT=0
for f in "$SCRIPTS_SRC"/*.py; do
    [ -f "$f" ] || continue
    cp "$f" "$SCRIPTS_DST/$(basename "$f")"
    SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
done

# 4. Merge PostToolUse hooks into ~/.claude/settings.json
python3 -c "
import json
from pathlib import Path

settings_path = Path('$SETTINGS_FILE')
settings = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        pass

hooks = settings.setdefault('hooks', {})
post_hooks = hooks.get('PostToolUse', [])

# The hooks we want installed (global paths)
GLOBAL_HOOKS = [
    {
        'hooks': [
            {
                'type': 'command',
                'command': 'python3 ~/.claude/hooks/heartbeat.py',
                'description': 'Update session heartbeat during active waves',
            },
            {
                'type': 'command',
                'command': 'python3 ~/.claude/hooks/context_monitor.py',
                'description': 'Warn at 60% context usage, stop at 80%',
            },
        ]
    }
]

# Check if our global hooks are already present (by command string)
global_cmds = {h['command'] for entry in GLOBAL_HOOKS for h in entry.get('hooks', [])}
existing_cmds = {h.get('command', '') for entry in post_hooks for h in entry.get('hooks', [])}

if not global_cmds.issubset(existing_cmds):
    # Remove any old entries matching our commands, then append fresh
    cleaned = []
    for entry in post_hooks:
        entry_hooks = [h for h in entry.get('hooks', []) if h.get('command', '') not in global_cmds]
        if entry_hooks:
            entry['hooks'] = entry_hooks
            cleaned.append(entry)
    cleaned.extend(GLOBAL_HOOKS)
    hooks['PostToolUse'] = cleaned
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + '\n')
    print('  ✓ PostToolUse hooks merged into settings.json')
else:
    print('  ✓ PostToolUse hooks already present in settings.json')
"

# 5. Copy universal CLAUDE.md template (only if user doesn't have one)
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
if [ ! -f "$CLAUDE_MD" ]; then
    if [ -f "$SCRIPT_DIR/universal-claude-md-template.md" ]; then
        cp "$SCRIPT_DIR/universal-claude-md-template.md" "$CLAUDE_MD"
        echo "✓ Universal CLAUDE.md installed to ~/.claude/CLAUDE.md"
    fi
else
    echo "✓ ~/.claude/CLAUDE.md already exists (not overwritten)"
fi

# 6. Activate git hooks (only if in a git repo)
if [ -d "$SCRIPT_DIR/.git" ] || git -C "$SCRIPT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    git -C "$SCRIPT_DIR" config core.hooksPath .githooks 2>/dev/null
    echo "✓ Git hooks activated"
fi

# 7. Set DOE Role in STATE.md
STATE_FILE="$SCRIPT_DIR/STATE.md"
if [ -f "$STATE_FILE" ] && grep -q "DOE Role:" "$STATE_FILE"; then
    echo ""
    echo "Are you a DOE contributor? (Most users: no)"
    echo "  n = Consumer — you build projects using DOE (default)"
    echo "  y = Creator  — you contribute improvements back to the starter kit"
    printf "Choice [n]: "
    read -r DOE_ROLE_CHOICE
    if [ "$DOE_ROLE_CHOICE" = "y" ] || [ "$DOE_ROLE_CHOICE" = "Y" ]; then
        sed -i '' 's/\*\*DOE Role:\*\* consumer/**DOE Role:** creator/' "$STATE_FILE"
        echo "✓ DOE Role set to creator"
    else
        echo "✓ DOE Role set to consumer"
    fi
fi

# 8. Summary
echo ""
echo "✓ $COMMAND_COUNT commands installed to ~/.claude/commands/"
echo "✓ $HOOK_COUNT hooks installed to ~/.claude/hooks/"
echo "✓ $SCRIPT_COUNT scripts installed to ~/.claude/scripts/"
echo "✓ DOE Kit $KIT_VERSION installed ($TODAY)"
echo ""
echo "Ready — run claude and type /stand-up"
