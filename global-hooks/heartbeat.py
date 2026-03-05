"""PostToolUse hook: update session heartbeat every 2 minutes during active waves.

Runs after every tool use. Uses a temp file to track last heartbeat time
so we only shell out to multi_agent.py when >2 minutes have elapsed.
Only active when a wave is running and this session is registered.

Per-terminal isolation: uses os.getppid() (Claude Code PID) to find
this terminal's session-id file and heartbeat marker. In Bash tool calls,
$PPID resolves to the same Claude Code PID.
"""
import json
import os
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path.cwd()
SESSIONS_FILE = PROJECT_ROOT / ".tmp" / "waves" / "sessions.json"
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
    marker = PROJECT_ROOT / ".tmp" / f".last-heartbeat-{ppid}"

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
    session_id_file = PROJECT_ROOT / ".tmp" / f".session-id-{ppid}"
    cmd = ["python3", str(Path.home() / ".claude" / "scripts" / "multi_agent.py"), "--heartbeat"]
    if session_id_file.exists():
        try:
            sid = session_id_file.read_text().strip()
            if sid:
                cmd.extend(["--session", sid])
        except OSError:
            pass

    subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
