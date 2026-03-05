"""PostToolUse hook: update session heartbeat every 30 seconds during active waves.

Runs after every tool use. Uses a temp file to track last heartbeat time
so we only shell out to multi_agent.py when >30 seconds have elapsed.
Only active when a wave is running and this session is registered.

Per-terminal isolation: uses os.getppid() (Claude Code PID) to find
this terminal's session-id file and heartbeat marker. In Bash tool calls,
$PPID resolves to the same Claude Code PID.

Worktree-aware: resolves main project root via .git file detection so
heartbeats work correctly from worktree contexts.
"""
import json
import os
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "scripts"))
from doe_utils import resolve_project_root

MAIN_ROOT, _ = resolve_project_root()
SESSIONS_FILE = MAIN_ROOT / ".tmp" / "waves" / "sessions.json"
HEARTBEAT_INTERVAL = 30  # seconds


def main():
    # Accept and discard stdin (hook protocol requires it)
    json.load(sys.stdin)

    # Quick exit: no wave active
    if not SESSIONS_FILE.exists():
        print(json.dumps({}))
        return

    # Per-terminal marker using Claude Code PID (stable across hook invocations)
    ppid = os.getppid()
    marker = MAIN_ROOT / ".tmp" / f".last-heartbeat-{ppid}"

    now = time.time()
    if marker.exists():
        try:
            last = float(marker.read_text().strip())
            if now - last < HEARTBEAT_INTERVAL:
                print(json.dumps({}))
                return
        except (ValueError, OSError):
            pass

    # Time to heartbeat — write marker and fire the update
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(now))

    # Read session ID from per-terminal file (written by --claim --parent-pid $PPID)
    session_id_file = MAIN_ROOT / ".tmp" / f".session-id-{ppid}"
    cmd = ["python3", str(Path.home() / ".claude" / "scripts" / "multi_agent.py"), "--heartbeat"]
    if session_id_file.exists():
        try:
            sid = session_id_file.read_text().strip()
            if sid:
                cmd.extend(["--session", sid])
        except OSError:
            pass

    subprocess.run(cmd, cwd=str(MAIN_ROOT), capture_output=True, text=True)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
