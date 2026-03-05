"""PostToolUse hook: monitor estimated context usage and warn when running low.

Tracks cumulative tool I/O size across the session. Warns at 60% of estimated
context budget, hard-warns at 80% to trigger graceful handoff.

Budget is model-aware during waves (haiku: 30k, sonnet: 80k, opus: 200k).
Solo sessions use 200k (full context window).

Per-terminal isolation: uses os.getppid() (Claude Code PID) to find
this terminal's session-id file, context tracker, and warning marker.
"""
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path.cwd()
WAVES_DIR = PROJECT_ROOT / ".tmp" / "waves"
TMP_DIR = PROJECT_ROOT / ".tmp"

CHARS_PER_TOKEN = 4
WARN_PCT = 0.60
STOP_PCT = 0.80
WARN_INTERVAL = 120  # seconds between stderr warnings

MODEL_BUDGETS = {"haiku": 30_000, "sonnet": 80_000, "opus": 200_000}
DEFAULT_BUDGET = 200_000

RESERVED_FILES = {"claims.json", "sessions.json", "stats.json"}


def main():
    hook_input = json.load(sys.stdin)

    # Per-terminal files using Claude Code PID
    ppid = os.getppid()
    tracker_file = TMP_DIR / f".context-usage-{ppid}.json"

    # Load or initialise tracker
    tracker = _load_tracker(tracker_file, ppid)

    # Estimate tokens from this tool use
    input_str = json.dumps(hook_input.get("tool_input", {}))
    output_str = str(hook_input.get("tool_output", ""))
    new_tokens = (len(input_str) + len(output_str)) // CHARS_PER_TOKEN

    tracker["tokens"] += new_tokens

    # Calculate percentage
    budget = tracker["budget"]
    pct = tracker["tokens"] / budget if budget > 0 else 0

    # Save tracker
    tracker_file.parent.mkdir(parents=True, exist_ok=True)
    tracker_file.write_text(json.dumps(tracker))

    # Check thresholds
    if pct >= STOP_PCT:
        msg = (
            f"Context at ~{pct:.0%} ({tracker['tokens']:,}/{budget:,} est. tokens) "
            f"— wrap up current work and commit NOW"
        )
        _maybe_warn(f"\U0001f6d1 {msg}", ppid)
        print(json.dumps({"warning": msg}))
    elif pct >= WARN_PCT:
        msg = (
            f"Context at ~{pct:.0%} ({tracker['tokens']:,}/{budget:,} est. tokens) "
            f"— consider committing soon"
        )
        _maybe_warn(f"\u26a0\ufe0f {msg}", ppid)
        print(json.dumps({"warning": msg}))
    else:
        print(json.dumps({}))


def _load_tracker(tracker_file, ppid):
    """Load existing tracker or initialise with budget detection."""
    if tracker_file.exists():
        try:
            return json.loads(tracker_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Initialise new tracker with budget detection
    budget = _detect_budget(ppid)
    return {"tokens": 0, "budget": budget}


def _detect_budget(ppid):
    """Check active wave for model-specific budget, else use default."""
    sessions_file = WAVES_DIR / "sessions.json"
    if not sessions_file.exists():
        return DEFAULT_BUDGET

    try:
        # Read session ID from per-terminal file (written by --claim --parent-pid)
        session_id_file = TMP_DIR / f".session-id-{ppid}"
        if not session_id_file.exists():
            return DEFAULT_BUDGET
        sid = session_id_file.read_text().strip()
        if not sid:
            return DEFAULT_BUDGET

        sessions = json.loads(sessions_file.read_text())
        for session in sessions.get("sessions", []):
            if session.get("sessionId", "") == sid:
                task_id = session.get("claimedTask")
                if task_id:
                    return _budget_for_task(task_id)
    except (json.JSONDecodeError, OSError):
        pass

    return DEFAULT_BUDGET


def _budget_for_task(task_id):
    """Look up model budget from the active wave file."""
    try:
        for f in sorted(WAVES_DIR.glob("*.json")):
            if f.name.endswith("-log.json") or f.name in RESERVED_FILES:
                continue
            wave = json.loads(f.read_text())
            for task in wave.get("tasks", []):
                if task.get("taskId") == task_id:
                    model = task.get("model", "sonnet")
                    return MODEL_BUDGETS.get(model, DEFAULT_BUDGET)
    except (json.JSONDecodeError, OSError):
        pass
    return DEFAULT_BUDGET


def _maybe_warn(msg, ppid):
    """Write to stderr at most once per WARN_INTERVAL seconds."""
    marker = TMP_DIR / f".context-warned-{ppid}"
    now = time.time()

    if marker.exists():
        try:
            last = float(marker.read_text().strip())
            if now - last < WARN_INTERVAL:
                return
        except (ValueError, OSError):
            pass

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(now))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    main()
