#!/bin/bash
# DOE Starter Kit — one-command setup
# For new/non-DOE projects: runs the init wizard (doe_init.py)
# For existing DOE projects: installs global commands, hooks, scripts, and settings.
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

# --- Wizard delegation ---
# If this is a new or non-DOE project, run the init wizard instead of blind-copy setup.
if [ ! -f "CLAUDE.md" ] || [ ! -d "directives" ]; then
    if [ -f "$SCRIPT_DIR/execution/doe_init.py" ]; then
        python3 "$SCRIPT_DIR/execution/doe_init.py" --kit-dir "$SCRIPT_DIR" "$@"
        # After wizard completes, fall through to install global tooling below
    fi
fi

# --- Global tooling installation ---
# Always runs: installs commands, hooks, scripts to ~/.claude/ (global, not per-project).

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

# 6. Activate git hooks (only if cwd is a git repo)
if git rev-parse --git-dir > /dev/null 2>&1; then
    git config core.hooksPath .githooks 2>/dev/null
    echo "✓ Git hooks activated"
fi

# 7. Copy Quality Stack files (only if not already present in project)
# Execution scripts for test orchestration, health checks, and verification
QS_SCRIPTS="run_test_suite.py health_check.py verify_tests.py generate_test_checklist.py audit_claims.py"
QS_SCRIPT_COUNT=0
if [ -d "$SCRIPT_DIR/execution" ]; then
    for script in $QS_SCRIPTS; do
        if [ -f "$SCRIPT_DIR/execution/$script" ] && [ ! -f "execution/$script" ]; then
            mkdir -p execution
            cp "$SCRIPT_DIR/execution/$script" "execution/$script"
            QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
        fi
    done
fi

# Test infrastructure: config, helpers, specs, baselines, playwright config
if [ -d "$SCRIPT_DIR/tests" ]; then
    # tests/config.json — only if missing (preserves project customisations)
    if [ -f "$SCRIPT_DIR/tests/config.json" ] && [ ! -f "tests/config.json" ]; then
        mkdir -p tests
        cp "$SCRIPT_DIR/tests/config.json" "tests/config.json"
        QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
    fi
    # tests/helpers.js
    if [ -f "$SCRIPT_DIR/tests/helpers.js" ] && [ ! -f "tests/helpers.js" ]; then
        mkdir -p tests
        cp "$SCRIPT_DIR/tests/helpers.js" "tests/helpers.js"
        QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
    fi
    # tests/*.spec.js — template specs
    for f in "$SCRIPT_DIR"/tests/*.spec.js; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        if [ ! -f "tests/$fname" ]; then
            mkdir -p tests
            cp "$f" "tests/$fname"
            QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
        fi
    done
    # tests/baselines/
    if [ -d "$SCRIPT_DIR/tests/baselines" ] && [ ! -d "tests/baselines" ]; then
        mkdir -p tests/baselines
        cp "$SCRIPT_DIR"/tests/baselines/* tests/baselines/ 2>/dev/null
        QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
    fi
fi

# playwright.config.js
if [ -f "$SCRIPT_DIR/playwright.config.js" ] && [ ! -f "playwright.config.js" ]; then
    cp "$SCRIPT_DIR/playwright.config.js" "playwright.config.js"
    QS_SCRIPT_COUNT=$((QS_SCRIPT_COUNT + 1))
fi

if [ "$QS_SCRIPT_COUNT" -gt 0 ]; then
    echo "✓ $QS_SCRIPT_COUNT Quality Stack files installed"
else
    echo "✓ Quality Stack files already present (not overwritten)"
fi

# 8. Copy CI workflow (only if not already present)
CI_COUNT=0
if [ -d "$SCRIPT_DIR/.github/workflows" ]; then
    for f in "$SCRIPT_DIR"/.github/workflows/*.yml; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        if [ ! -f ".github/workflows/$fname" ]; then
            mkdir -p .github/workflows
            cp "$f" ".github/workflows/$fname"
            CI_COUNT=$((CI_COUNT + 1))
        fi
    done
fi
if [ "$CI_COUNT" -gt 0 ]; then
    echo "✓ $CI_COUNT CI workflow(s) installed to .github/workflows/"
else
    echo "✓ CI workflows already present (not overwritten)"
fi

# 9. Copy PR template (only if not already present)
if [ -f "$SCRIPT_DIR/.github/pull_request_template.md" ] && [ ! -f ".github/pull_request_template.md" ]; then
    mkdir -p .github
    cp "$SCRIPT_DIR/.github/pull_request_template.md" ".github/pull_request_template.md"
    echo "✓ PR template installed to .github/"
fi

# 10. Set DOE Role in project STATE.md
STATE_FILE="STATE.md"
if [ -f "$STATE_FILE" ] && grep -q "DOE Role:" "$STATE_FILE"; then
    echo ""
    echo "Are you a DOE contributor? (Most users: no)"
    echo "  n = Consumer — you build projects using DOE (default)"
    echo "  y = Creator  — you contribute improvements back to the starter kit"
    printf "Choice [n]: "
    read -r DOE_ROLE_CHOICE
    if [ "$DOE_ROLE_CHOICE" = "y" ] || [ "$DOE_ROLE_CHOICE" = "Y" ]; then
        # Cross-platform sed -i (macOS needs '', Linux doesn't)
        if sed --version 2>/dev/null | grep -q GNU; then
            sed -i 's/\*\*DOE Role:\*\* consumer/**DOE Role:** creator/' "$STATE_FILE"
        else
            sed -i '' 's/\*\*DOE Role:\*\* consumer/**DOE Role:** creator/' "$STATE_FILE"
        fi
        echo "✓ DOE Role set to creator"
    else
        echo "✓ DOE Role set to consumer"
    fi
fi

# 11. Summary
echo ""
echo "✓ $COMMAND_COUNT commands installed to ~/.claude/commands/"
echo "✓ $HOOK_COUNT hooks installed to ~/.claude/hooks/"
echo "✓ $SCRIPT_COUNT scripts installed to ~/.claude/scripts/"
echo "✓ DOE Kit $KIT_VERSION installed ($TODAY)"
echo ""
echo "Ready — run claude and type /stand-up"
