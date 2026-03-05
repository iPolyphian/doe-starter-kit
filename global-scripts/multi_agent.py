#!/usr/bin/env python3
"""Multi-agent coordination for parallel Claude Code sessions.

Manages waves, task claiming, session registry, and status tracking
for running 2-4 terminals simultaneously on the same project.

All coordination state lives in .tmp/waves/ (ephemeral).

Usage:
    python3 ~/.claude/scripts/multi_agent.py --init-wave wave-1.json
    python3 ~/.claude/scripts/multi_agent.py --claim
    python3 ~/.claude/scripts/multi_agent.py --complete <taskId> [--tokens N] [--commits N]
    python3 ~/.claude/scripts/multi_agent.py --status [--json]
    python3 ~/.claude/scripts/multi_agent.py --dashboard [--json]
    python3 ~/.claude/scripts/multi_agent.py --preview [FILE] [--json]
    python3 ~/.claude/scripts/multi_agent.py --abandon <taskId>
    python3 ~/.claude/scripts/multi_agent.py --heartbeat
    python3 ~/.claude/scripts/multi_agent.py --reclaim [--json]
    python3 ~/.claude/scripts/multi_agent.py --merge [--json]
    python3 ~/.claude/scripts/multi_agent.py --summary [--json]
    python3 ~/.claude/scripts/multi_agent.py --log [--json]
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root (handles worktree context automatically)
sys.path.insert(0, str(Path(__file__).parent))
from doe_utils import resolve_project_root

MAIN_ROOT, WORKTREE_ROOT = resolve_project_root()
PROJECT_ROOT = MAIN_ROOT  # Wave state always resolves from main root
WAVES_DIR = PROJECT_ROOT / ".tmp" / "waves"
CLAIMS_FILE = WAVES_DIR / "claims.json"
SESSIONS_FILE = WAVES_DIR / "sessions.json"
STATS_FILE = PROJECT_ROOT / ".claude" / "stats.json"

WIP_LIMIT = 2  # max tasks per terminal
STALE_THRESHOLD = 300  # seconds (5 minutes)
WAVE_COST_WARN = 4.00  # £ — warn if total wave cost exceeds this
TOKEN_WARN = {"haiku": 50_000, "sonnet": 150_000, "opus": 300_000}  # per-task thresholds


# ══════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════

def now_iso():
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


HEARTBEAT_LOG_INTERVAL = 600  # seconds — log heartbeat events every 10 min, not every 2

_session_override = None


def get_session_id():
    """Session ID — explicit override, session-id file, or PID-based fallback."""
    return _session_override or f"terminal-{os.getpid()}"


def _detect_default_branch():
    """Auto-detect the default branch (master or main)."""
    # Try remote HEAD first
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    if result.returncode == 0:
        # refs/remotes/origin/main -> main
        return result.stdout.strip().split("/")[-1]
    # Fallback: check if master exists, else main
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "master"],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    return "master" if result.returncode == 0 else "main"


def _compute_duration(start_iso, end_iso):
    """Human-readable duration between two ISO timestamps. Returns str like '42m' or '1h 15m'."""
    try:
        fmt = "%Y-%m-%dT%H:%M:%S+00:00"
        start = datetime.strptime(start_iso, fmt)
        end = datetime.strptime(end_iso, fmt)
        delta = int((end - start).total_seconds())
        if delta < 0:
            return "?"
        hours, remainder = divmod(delta, 3600)
        minutes = remainder // 60
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "?"


# ══════════════════════════════════════════════════════════════
# Atomic file operations (fcntl.flock)
# ══════════════════════════════════════════════════════════════

def atomic_read(filepath):
    """Read a JSON file with shared lock."""
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def atomic_write(filepath, data):
    """Write a JSON file with exclusive lock."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Create file if it doesn't exist
    if not filepath.exists():
        filepath.write_text("{}", encoding="utf-8")
    with open(filepath, "r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def atomic_modify(filepath, modify_func):
    """Lock, read, modify, write, unlock a JSON file. Returns modified data."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not filepath.exists():
        filepath.write_text("{}", encoding="utf-8")
    with open(filepath, "r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            data = json.load(f)
            modified = modify_func(data)
            f.seek(0)
            json.dump(modified, f, indent=2)
            f.truncate()
            return modified
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def append_log(wave_id, event):
    """Append an event to the wave log (append-only)."""
    log_path = WAVES_DIR / f"{wave_id}-log.json"
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"waveId": wave_id, "events": []}, indent=2),
                            encoding="utf-8")

    def _append(data):
        data.setdefault("events", []).append(event)
        return data

    atomic_modify(log_path, _append)


# ══════════════════════════════════════════════════════════════
# Wave discovery
# ══════════════════════════════════════════════════════════════

RESERVED_FILES = {"claims.json", "sessions.json"}


def _wave_sort_key(path):
    """Extract numeric index from wave filename for correct sort order."""
    m = re.search(r"wave-(\d+)", path.name)
    return int(m.group(1)) if m else path.stat().st_mtime


def find_active_wave():
    """Find the active wave file. Returns (path, data) or (None, None)."""
    if not WAVES_DIR.exists():
        return None, None
    waves = list(WAVES_DIR.glob("*.json"))
    # Exclude log files, claims, sessions
    waves = [w for w in waves
             if not w.name.endswith("-log.json") and w.name not in RESERVED_FILES and not w.name.startswith(".")]
    waves.sort(key=_wave_sort_key)
    for wave_path in reversed(waves):  # newest first
        data = atomic_read(wave_path)
        if data.get("status") == "active":
            return wave_path, data
    return None, None


def find_latest_wave():
    """Find the latest wave file (any status). Returns (path, data) or (None, None)."""
    if not WAVES_DIR.exists():
        return None, None
    waves = list(WAVES_DIR.glob("*.json"))
    waves = [w for w in waves
             if not w.name.endswith("-log.json") and w.name not in RESERVED_FILES and not w.name.startswith(".")]
    waves.sort(key=_wave_sort_key)
    for wave_path in reversed(waves):  # newest first
        data = atomic_read(wave_path)
        if "waveId" in data and "tasks" in data:
            return wave_path, data
    return None, None


# ══════════════════════════════════════════════════════════════
# Worktree management
# ══════════════════════════════════════════════════════════════

WORKTREE_DIR = PROJECT_ROOT / ".claude" / "worktrees"


def create_worktree(wave_id, task_id):
    """Create a git worktree for a task. Returns (worktree_path, branch_name)."""
    worktree_path = WORKTREE_DIR / task_id
    branch_name = f"{wave_id}/{task_id}"

    if worktree_path.exists():
        return str(worktree_path), branch_name

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # Try creating with new branch
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return str(worktree_path), branch_name

    # Branch might already exist (retry from abandoned task) — attach to existing
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return str(worktree_path), branch_name

    print(f"ERROR: Failed to create worktree: {result.stderr.strip()}")
    sys.exit(1)


def remove_worktree(task_id, delete_branch=False):
    """Remove a git worktree. Optionally delete the branch too."""
    worktree_path = WORKTREE_DIR / task_id

    if worktree_path.exists():
        result = subprocess.run(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"WARN: Failed to remove worktree: {result.stderr.strip()}")

    # Prune stale worktree references
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )

    if delete_branch:
        # Find the branch name — check all waves for this task
        wave_path, wave_data = find_active_wave()
        if wave_data:
            branch_name = f"{wave_data['waveId']}/{task_id}"
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True,
            )


# ══════════════════════════════════════════════════════════════
# --init-wave
# ══════════════════════════════════════════════════════════════

def cmd_init_wave(wave_file_arg):
    """Initialize a new wave from a JSON definition file."""
    wave_file = Path(wave_file_arg)
    if not wave_file.exists():
        print(f"ERROR: Wave file not found: {wave_file}")
        sys.exit(1)

    WAVES_DIR.mkdir(parents=True, exist_ok=True)

    # Abort existing active wave if any
    old_path, old_wave = find_active_wave()
    if old_wave:
        old_id = old_wave["waveId"]
        print(f"  Aborting existing wave '{old_id}'")
        old_wave["status"] = "aborted"
        atomic_write(old_path, old_wave)
        append_log(old_id, {
            "timestamp": now_iso(),
            "type": "abort",
            "reason": f"Replaced by new wave init",
        })

    # Read wave definition
    wave_data = json.loads(wave_file.read_text(encoding="utf-8"))
    wave_id = wave_data["waveId"]

    # Validate minimal structure
    if "tasks" not in wave_data or not wave_data["tasks"]:
        print("ERROR: Wave file must contain a non-empty 'tasks' array")
        sys.exit(1)

    for task in wave_data["tasks"]:
        if "taskId" not in task:
            print("ERROR: Every task must have a 'taskId'")
            sys.exit(1)

    # Set all tasks to pending, mark wave active
    for task in wave_data["tasks"]:
        task["status"] = "pending"
    wave_data["status"] = "active"
    wave_data.setdefault("createdAt", now_iso())

    # Write coordination files
    dest = WAVES_DIR / f"{wave_id}.json"
    atomic_write(dest, wave_data)
    atomic_write(CLAIMS_FILE, {"waveId": wave_id, "claims": {}})
    atomic_write(SESSIONS_FILE, {"sessions": []})

    log_path = WAVES_DIR / f"{wave_id}-log.json"
    if not log_path.exists():
        log_path.write_text(
            json.dumps({"waveId": wave_id, "events": []}, indent=2),
            encoding="utf-8",
        )

    n = len(wave_data["tasks"])
    print(f"Wave '{wave_id}' initialized with {n} tasks")
    print(f"  Location: {WAVES_DIR.relative_to(PROJECT_ROOT)}/")
    print(f"  Files: {wave_id}.json, claims.json, sessions.json, {wave_id}-log.json")
    for task in wave_data["tasks"]:
        model = task.get("model", "default")
        size = task.get("size", "?")
        print(f"  ○ {task['taskId']}  [{model}]  [{size}]")


# ══════════════════════════════════════════════════════════════
# --claim
# ══════════════════════════════════════════════════════════════

def cmd_claim(as_json=False, parent_pid=None):
    """Claim the next available task for this session."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found. Run --init-wave first.")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    sid = get_session_id()

    # Register session if not already registered
    def _register(sessions):
        existing = [s for s in sessions.get("sessions", []) if s["sessionId"] == sid]
        if not existing:
            sessions.setdefault("sessions", []).append({
                "sessionId": sid,
                "pid": os.getpid(),
                "startedAt": now_iso(),
                "lastHeartbeat": now_iso(),
                "worktree": None,
                "branch": None,
                "claimedTask": None,
                "model": None,
                "status": "active",
                "tokensUsed": 0,
            })
        else:
            # Update heartbeat on claim
            existing[0]["lastHeartbeat"] = now_iso()
            existing[0]["status"] = "active"
        return sessions

    atomic_modify(SESSIONS_FILE, _register)

    # Read claims to check completed tasks and WIP
    claims = atomic_read(CLAIMS_FILE)
    completed_tasks = {
        tid for tid, c in claims.get("claims", {}).items()
        if c.get("status") == "completed"
    }
    my_active = sum(
        1 for c in claims.get("claims", {}).values()
        if c.get("sessionId") == sid and c.get("status") == "in_progress"
    )

    if my_active >= WIP_LIMIT:
        print(f"WIP limit reached ({WIP_LIMIT} tasks in progress). Complete a task first.")
        sys.exit(0)

    # Claim first available task (atomic)
    claimed_task = None

    def _claim(claims_data):
        nonlocal claimed_task
        for task in wave_data.get("tasks", []):
            tid = task["taskId"]
            existing = claims_data.get("claims", {}).get(tid, {})

            # Skip if already claimed or completed
            if existing.get("status") in ("in_progress", "completed"):
                continue

            # Check dependencies
            deps = task.get("dependsOn", [])
            if deps and not all(d in completed_tasks for d in deps):
                continue

            # Claim it
            claims_data.setdefault("claims", {})[tid] = {
                "sessionId": sid,
                "claimedAt": now_iso(),
                "status": "in_progress",
            }
            claimed_task = task
            break
        return claims_data

    atomic_modify(CLAIMS_FILE, _claim)

    if not claimed_task:
        # Distinguish: all done vs all blocked
        all_statuses = {
            tid: claims.get("claims", {}).get(tid, {}).get("status", "pending")
            for tid in [t["taskId"] for t in wave_data.get("tasks", [])]
        }
        if all(s == "completed" for s in all_statuses.values()):
            print("All tasks completed. Run --merge to finish the wave.")
        elif all(s in ("completed", "in_progress") for s in all_statuses.values()):
            print("All tasks claimed. Nothing available.")
        else:
            print("No tasks available (dependencies not met or all claimed).")
        sys.exit(0)

    # Create worktree for the claimed task
    wt_path, branch = create_worktree(wave_id, claimed_task["taskId"])

    # Update session with claimed task info + worktree
    def _update_session(sessions):
        for s in sessions.get("sessions", []):
            if s["sessionId"] == sid:
                s["claimedTask"] = claimed_task["taskId"]
                s["model"] = claimed_task.get("model")
                s["worktree"] = wt_path
                s["branch"] = branch
                break
        return sessions

    atomic_modify(SESSIONS_FILE, _update_session)

    # Log event
    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "claim",
        "taskId": claimed_task["taskId"],
        "sessionId": sid,
        "worktree": wt_path,
        "branch": branch,
    })

    # Write session ID to a PID-specific file in PROJECT_ROOT.
    # Hooks use os.getppid() (= Claude Code PID) to find their terminal's file.
    # Bash tool's $PPID is the same Claude Code PID, passed via --parent-pid.
    ppid = parent_pid or os.getppid()
    session_id_file = PROJECT_ROOT / ".tmp" / f".session-id-{ppid}"
    session_id_file.parent.mkdir(parents=True, exist_ok=True)
    session_id_file.write_text(sid)

    # Output
    if as_json:
        result = {**claimed_task, "worktree": wt_path, "branch": branch}
        print(json.dumps(result, indent=2))
    else:
        print(f"Claimed: {claimed_task['taskId']}")
        print(f"  Description: {claimed_task.get('description', '—')}")
        print(f"  Model: {claimed_task.get('model', 'default')}")
        print(f"  Size: {claimed_task.get('size', '?')}")
        print(f"  Worktree: {wt_path}")
        print(f"  Branch: {branch}")
        if claimed_task.get("acceptanceCriteria"):
            print("  Acceptance criteria:")
            for ac in claimed_task["acceptanceCriteria"]:
                print(f"    - {ac}")
        if claimed_task.get("owns"):
            print(f"  Owns: {', '.join(claimed_task['owns'])}")
        if claimed_task.get("reads"):
            print(f"  Reads: {', '.join(claimed_task['reads'])}")


# ══════════════════════════════════════════════════════════════
# --complete
# ══════════════════════════════════════════════════════════════

def cmd_complete(task_id, tokens=0, commits=0, skip_verify=False):
    """Mark a task as completed."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    sid = get_session_id()

    # Verify task exists in wave
    tasks = wave_data.get("tasks", [])
    task_ids = [t["taskId"] for t in tasks]
    if task_id not in task_ids:
        print(f"ERROR: Task '{task_id}' not found in wave '{wave_id}'")
        print(f"  Available: {', '.join(task_ids)}")
        sys.exit(1)

    # Verification gate
    if not skip_verify:
        task = next(t for t in tasks if t["taskId"] == task_id)
        criteria = task.get("acceptanceCriteria", [])
        auto_criteria = []
        for ac in criteria:
            if isinstance(ac, dict):
                if ac.get("type", "auto") == "auto" and ac.get("verify"):
                    auto_criteria.append(ac["verify"])
                # Skip manual criteria
            elif isinstance(ac, str):
                # Skip criteria prefixed with "manual:"
                if not ac.strip().lower().startswith("manual:"):
                    auto_criteria.append(ac)

        if auto_criteria:
            # Resolve worktree path for file verification:
            # Check claims for this task's worktree, fall back to WORKTREE_ROOT
            claims = atomic_read(CLAIMS_FILE)
            claim = claims.get("claims", {}).get(task_id, {})
            verify_root = claim.get("worktree") or str(WORKTREE_ROOT)

            try:
                # Try importing from main project root first, then worktree
                for import_root in [str(PROJECT_ROOT), verify_root]:
                    if import_root not in sys.path:
                        sys.path.insert(0, import_root)
                from execution.verify import run_all_criteria, run_build_step
                build = run_build_step(working_dir=verify_root)
                if build and build["status"] == "FAIL":
                    print(f"VERIFICATION BLOCKED: Build failed — {build['detail']}")
                    print("  Fix the build or use --skip-verify to bypass")
                    sys.exit(1)
                results = run_all_criteria(auto_criteria, working_dir=verify_root)
                failures = [r for r in results if r["status"] == "FAIL"]
                for r in results:
                    print(f"  [{r['status']}] {r['criterion']}")
                if failures:
                    print(f"\nVERIFICATION BLOCKED: {len(failures)}/{len(results)} criteria failed")
                    print("  Fix failures or use --skip-verify to bypass")
                    sys.exit(1)
                print(f"  Verification: {len(results)}/{len(results)} passed\n")
            except ImportError:
                print("  WARN: execution/verify.py not found — skipping verification")

    # Mark complete (atomic)
    def _complete(claims_data):
        claim = claims_data.get("claims", {}).get(task_id)
        if not claim:
            print(f"ERROR: Task '{task_id}' has no claim record")
            sys.exit(1)
        if claim.get("status") == "completed":
            print(f"Task '{task_id}' is already completed")
            sys.exit(0)
        if claim.get("sessionId") != sid:
            print(f"ERROR: Task '{task_id}' is claimed by {claim['sessionId']}, not {sid}")
            sys.exit(1)
        claim["status"] = "completed"
        claim["completedAt"] = now_iso()
        return claims_data

    atomic_modify(CLAIMS_FILE, _complete)

    # Update session
    def _update(sessions):
        for s in sessions.get("sessions", []):
            if s["sessionId"] == sid:
                s["claimedTask"] = None
                s["tokensUsed"] = s.get("tokensUsed", 0) + tokens
                break
        return sessions

    atomic_modify(SESSIONS_FILE, _update)

    # Remove worktree (keep branch for merging)
    remove_worktree(task_id, delete_branch=False)

    # Log event
    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "complete",
        "taskId": task_id,
        "sessionId": sid,
        "commits": commits,
        "tokensUsed": tokens,
    })

    print(f"Task '{task_id}' marked as completed")
    print(f"  Worktree removed. Branch '{wave_id}/{task_id}' preserved for merge.")


# ══════════════════════════════════════════════════════════════
# --abandon
# ══════════════════════════════════════════════════════════════

def cmd_abandon(task_id):
    """Abandon a claimed task. Releases claim, removes worktree and branch."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    sid = get_session_id()

    # Verify task exists
    task_ids = [t["taskId"] for t in wave_data.get("tasks", [])]
    if task_id not in task_ids:
        print(f"ERROR: Task '{task_id}' not found in wave '{wave_id}'")
        sys.exit(1)

    # Release claim (atomic)
    def _abandon(claims_data):
        claim = claims_data.get("claims", {}).get(task_id)
        if not claim:
            print(f"ERROR: Task '{task_id}' has no claim record")
            sys.exit(1)
        if claim.get("sessionId") != sid:
            print(f"ERROR: Task '{task_id}' is claimed by {claim['sessionId']}, not {sid}")
            sys.exit(1)
        claim["status"] = "abandoned"
        claim["abandonedAt"] = now_iso()
        return claims_data

    atomic_modify(CLAIMS_FILE, _abandon)

    # Update session
    def _update(sessions):
        for s in sessions.get("sessions", []):
            if s["sessionId"] == sid:
                s["claimedTask"] = None
                s["worktree"] = None
                s["branch"] = None
                break
        return sessions

    atomic_modify(SESSIONS_FILE, _update)

    # Remove worktree AND branch (work is being discarded)
    remove_worktree(task_id, delete_branch=True)

    # Log event
    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "abandon",
        "taskId": task_id,
        "sessionId": sid,
    })

    print(f"Task '{task_id}' abandoned")
    print(f"  Worktree and branch removed. Task is available for reclaim.")


# ══════════════════════════════════════════════════════════════
# --fail
# ══════════════════════════════════════════════════════════════

def cmd_fail(task_id, reason=""):
    """Mark a claimed task as failed. Keeps worktree and branch for debugging.

    NOTE: Failed tasks are intentionally retryable — another terminal can re-claim
    them via --claim (status "failed" is not in the skip list). This allows retry
    after transient failures without manual intervention.
    """
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    sid = get_session_id()

    # Verify task exists
    task_ids = [t["taskId"] for t in wave_data.get("tasks", [])]
    if task_id not in task_ids:
        print(f"ERROR: Task '{task_id}' not found in wave '{wave_id}'")
        sys.exit(1)

    # Mark failed (atomic)
    def _fail(claims_data):
        claim = claims_data.get("claims", {}).get(task_id)
        if not claim:
            print(f"ERROR: Task '{task_id}' has no claim record")
            sys.exit(1)
        if claim.get("sessionId") != sid:
            print(f"ERROR: Task '{task_id}' is claimed by {claim['sessionId']}, not {sid}")
            sys.exit(1)
        claim["status"] = "failed"
        claim["failedAt"] = now_iso()
        if reason:
            claim["failReason"] = reason
        return claims_data

    atomic_modify(CLAIMS_FILE, _fail)

    # Update session
    def _update(sessions):
        for s in sessions.get("sessions", []):
            if s["sessionId"] == sid:
                s["claimedTask"] = None
                break
        return sessions

    atomic_modify(SESSIONS_FILE, _update)

    # Keep worktree and branch for debugging — don't remove

    # Log event
    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "fail",
        "taskId": task_id,
        "sessionId": sid,
        "reason": reason,
    })

    print(f"Task '{task_id}' marked as failed")
    if reason:
        print(f"  Reason: {reason}")
    print(f"  Worktree and branch preserved for debugging.")


# ══════════════════════════════════════════════════════════════
# --heartbeat
# ══════════════════════════════════════════════════════════════

def cmd_heartbeat():
    """Update this session's lastHeartbeat timestamp. Lightweight — just one atomic write."""
    if not SESSIONS_FILE.exists():
        return  # No wave active, nothing to update

    sid = get_session_id()

    def _heartbeat(sessions):
        for s in sessions.get("sessions", []):
            if s["sessionId"] == sid:
                s["lastHeartbeat"] = now_iso()
                s["status"] = "active"
                break
        return sessions

    atomic_modify(SESSIONS_FILE, _heartbeat)

    # Log heartbeat event (thinned — only every 10 minutes)
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        return
    wave_id = wave_data["waveId"]
    log_path = WAVES_DIR / f"{wave_id}-log.json"
    if log_path.exists():
        log_data = atomic_read(log_path)
        events = log_data.get("events", [])
        # Find last heartbeat from this session
        last_hb = None
        for evt in reversed(events):
            if evt.get("type") == "heartbeat" and evt.get("sessionId") == sid:
                last_hb = evt.get("timestamp", "")
                break
        if last_hb:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S+00:00"
                elapsed = (datetime.now(timezone.utc) -
                           datetime.strptime(last_hb, fmt).replace(tzinfo=timezone.utc)
                           ).total_seconds()
                if elapsed < HEARTBEAT_LOG_INTERVAL:
                    return  # Too soon, skip logging
            except (ValueError, TypeError):
                pass  # Can't parse — log anyway
    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "heartbeat",
        "sessionId": sid,
    })


# ══════════════════════════════════════════════════════════════
# --reclaim
# ══════════════════════════════════════════════════════════════

def cmd_reclaim(as_json=False):
    """Detect stale sessions and release their claims for re-claiming."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    now = datetime.now(timezone.utc)
    sessions = atomic_read(SESSIONS_FILE)

    # Find stale sessions
    stale_sessions = []
    for s in sessions.get("sessions", []):
        last_hb = s.get("lastHeartbeat", "")
        if not last_hb:
            continue
        try:
            hb_time = datetime.fromisoformat(last_hb)
            if hb_time.tzinfo is None:
                hb_time = hb_time.replace(tzinfo=timezone.utc)
            if (now - hb_time).total_seconds() > STALE_THRESHOLD:
                stale_sessions.append(s)
        except (ValueError, TypeError):
            continue

    if not stale_sessions:
        if as_json:
            print(json.dumps({"reclaimed": [], "message": "No stale sessions"}))
        else:
            print("No stale sessions found. All terminals are healthy.")
        return

    # Release claims from stale sessions — capture task→session mapping for logging
    reclaimed = []       # list of task IDs
    reclaim_map = {}     # taskId → stale sessionId (captured before modification)

    def _release_stale(claims_data):
        for s in stale_sessions:
            sid = s["sessionId"]
            for tid, claim in claims_data.get("claims", {}).items():
                if claim.get("sessionId") == sid and claim.get("status") == "in_progress":
                    reclaim_map[tid] = sid
                    claim["status"] = "pending"
                    claim["releasedAt"] = now_iso()
                    claim["releasedFrom"] = sid
                    reclaimed.append(tid)
        return claims_data

    atomic_modify(CLAIMS_FILE, _release_stale)

    # Mark stale sessions as dead and clear their task assignments
    def _mark_dead(sessions_data):
        for s in sessions_data.get("sessions", []):
            if any(st["sessionId"] == s["sessionId"] for st in stale_sessions):
                s["status"] = "dead"
                s["claimedTask"] = None
        return sessions_data

    atomic_modify(SESSIONS_FILE, _mark_dead)

    # Remove worktrees for reclaimed tasks (keep branch — new session continues from it)
    for tid in reclaimed:
        remove_worktree(tid, delete_branch=False)

    # Log events — use pre-captured mapping (not re-read from modified file)
    for tid in reclaimed:
        append_log(wave_id, {
            "timestamp": now_iso(),
            "type": "reclaim",
            "taskId": tid,
            "staleSession": reclaim_map.get(tid, "unknown"),
            "reclaimedBy": get_session_id(),
        })

    if as_json:
        print(json.dumps({
            "reclaimed": reclaimed,
            "staleSessions": [s["sessionId"] for s in stale_sessions],
        }, indent=2))
    else:
        print(f"Reclaimed {len(reclaimed)} task(s) from {len(stale_sessions)} stale session(s):")
        for tid in reclaimed:
            print(f"  ○ {tid} — now available for claiming")
        print()
        print("Stale sessions marked as dead:")
        for s in stale_sessions:
            print(f"  ✗ {s['sessionId']} (last heartbeat: {s.get('lastHeartbeat', '?')})")


# ══════════════════════════════════════════════════════════════
# --merge
# ══════════════════════════════════════════════════════════════

def cmd_merge(as_json=False):
    """Merge completed tasks back to master sequentially."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        print("ERROR: No active wave found")
        sys.exit(1)

    wave_id = wave_data["waveId"]
    tasks = wave_data.get("tasks", [])
    claims = atomic_read(CLAIMS_FILE)

    # Build merge order — only completed tasks, in wave definition order
    merge_queue = []
    skipped = []
    for task in tasks:
        tid = task["taskId"]
        claim = claims.get("claims", {}).get(tid, {})
        status = claim.get("status", "pending")
        branch = f"{wave_id}/{tid}"

        if status == "completed":
            # Check branch actually exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                merge_queue.append({"taskId": tid, "branch": branch, "task": task})
            else:
                skipped.append((tid, "branch not found (already merged?)"))
        else:
            skipped.append((tid, f"status: {status}"))

    if not merge_queue:
        msg = "No completed tasks with branches to merge."
        if skipped:
            msg += "\n  Skipped:"
            for tid, reason in skipped:
                msg += f"\n    {tid}: {reason}"
        print(msg)
        sys.exit(0)

    # Ensure we're on master
    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    ).stdout.strip()

    default_branch = _detect_default_branch()
    if current_branch != default_branch:
        result = subprocess.run(
            ["git", "checkout", default_branch],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: Could not checkout {default_branch}: {result.stderr.strip()}")
            sys.exit(1)

    # Check for uncommitted changes
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if status_result.stdout.strip():
        print("ERROR: Working tree has uncommitted changes. Commit or stash first.")
        sys.exit(1)

    # Sequential merge
    merged = []
    failed = None
    audit_script = PROJECT_ROOT / "execution" / "audit_claims.py"

    print(f"Merging {len(merge_queue)} task(s) from wave '{wave_id}'")
    if skipped:
        for tid, reason in skipped:
            print(f"  Skip: {tid} ({reason})")
    print()

    # Collect criteria from all tasks for regression checks
    def _get_auto_criteria(task):
        criteria = []
        for ac in task.get("acceptanceCriteria", []):
            if isinstance(ac, dict) and ac.get("type", "auto") == "auto" and ac.get("verify"):
                criteria.append(ac["verify"])
            elif isinstance(ac, str):
                criteria.append(ac)
        return criteria

    def _run_pre_merge_baseline(already_merged_tasks):
        """Run criteria from already-merged tasks as baseline."""
        all_criteria = []
        for t in already_merged_tasks:
            all_criteria.extend(_get_auto_criteria(t))
        if not all_criteria:
            return {}
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from execution.verify import run_all_criteria
            results = run_all_criteria(all_criteria)
            return {r["criterion"]: r["status"] for r in results}
        except ImportError:
            return {}

    for item in merge_queue:
        tid = item["taskId"]
        branch = item["branch"]
        task = item["task"]
        print(f"  Merging: {tid} ({branch})")

        # Pre-merge baseline: run criteria from already-merged tasks
        pre_merge = _run_pre_merge_baseline([m_item["task"] for m_item in merge_queue if m_item["taskId"] in merged])

        result = subprocess.run(
            ["git", "merge", branch, "--no-ff",
             "-m", f"Merge {tid} from {wave_id}"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )

        if result.returncode != 0:
            # Conflict — abort the merge and stop
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True,
            )
            failed = {
                "taskId": tid,
                "branch": branch,
                "error": result.stdout.strip() + "\n" + result.stderr.strip(),
            }
            print(f"  CONFLICT merging {tid}. Merge aborted.")
            print(f"  {result.stdout.strip()}")
            break

        print(f"  Merged: {tid}")

        # Post-merge regression check: re-run pre-merge criteria
        if pre_merge:
            try:
                from execution.verify import run_all_criteria
                post_results = run_all_criteria(list(pre_merge.keys()))
                regressions = []
                for r in post_results:
                    pre_status = pre_merge.get(r["criterion"], "SKIP")
                    if pre_status == "PASS" and r["status"] == "FAIL":
                        regressions.append(r)
                if regressions:
                    print(f"  REGRESSION after merging {tid}:")
                    for reg in regressions:
                        print(f"    [FAIL] {reg['criterion']}")
                        print(f"           {reg['detail']}")
                    print(f"  {len(regressions)} regression(s) detected — was PASS before merge")
                else:
                    print(f"  Regression check: {len(post_results)} criteria OK")
            except ImportError:
                pass

        # Run audit if available
        if audit_script.exists():
            audit_result = subprocess.run(
                ["python3", str(audit_script), "--hook"],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True,
            )
            if audit_result.returncode != 0:
                print(f"  AUDIT WARN after merging {tid}:")
                for line in audit_result.stdout.strip().split("\n"):
                    print(f"    {line}")

        # Delete the merged branch
        subprocess.run(
            ["git", "branch", "-d", branch],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )

        # Remove any lingering worktree
        remove_worktree(tid, delete_branch=False)

        # Log merge event
        append_log(wave_id, {
            "timestamp": now_iso(),
            "type": "merge",
            "taskId": tid,
            "branch": branch,
            "conflicts": 0,
        })

        merged.append(tid)

    print()

    # Summary
    if failed:
        print(f"Result: {len(merged)} merged, 1 conflict ({failed['taskId']})")
        print(f"  Fix the conflict manually, then re-run --merge to continue.")
        if as_json:
            print(json.dumps({
                "status": "conflict",
                "merged": merged,
                "failed": failed,
                "remaining": [i["taskId"] for i in merge_queue
                              if i["taskId"] not in merged
                              and i["taskId"] != failed["taskId"]],
            }, indent=2))
        sys.exit(1)

    # All merged — mark wave as completed
    wave_data["status"] = "completed"
    wave_data["completedAt"] = now_iso()
    atomic_write(wave_path, wave_data)

    # Compute wave stats from log
    log_path = WAVES_DIR / f"{wave_id}-log.json"
    log_events = atomic_read(log_path).get("events", []) if log_path.exists() else []
    total_commits = sum(e.get("commits", 0) for e in log_events if e.get("type") == "complete")
    total_conflicts = sum(e.get("conflicts", 0) for e in log_events if e.get("type") == "merge")
    wave_duration = _compute_duration(wave_data.get("createdAt", ""), now_iso())

    append_log(wave_id, {
        "timestamp": now_iso(),
        "type": "wave_complete",
        "merged": merged,
        "duration": wave_duration,
        "totalCommits": total_commits,
        "totalConflicts": total_conflicts,
    })

    # Clean up wave state files and per-terminal session/heartbeat markers
    for f in (CLAIMS_FILE, SESSIONS_FILE):
        if f.exists():
            f.unlink()
    # Clean up PID-specific marker files (pattern: .session-id-*, .last-heartbeat-*, etc.)
    tmp_dir = PROJECT_ROOT / ".tmp"
    if tmp_dir.exists():
        for pattern in (".session-id-*", ".last-heartbeat-*",
                        ".context-usage-*.json", ".context-warned-*"):
            for marker in tmp_dir.glob(pattern):
                marker.unlink(missing_ok=True)

    print(f"All {len(merged)} tasks merged. Wave '{wave_id}' completed.")
    print(f"  Branches cleaned up. Wave state files removed.")

    # Auto-print cost summary after merge
    print()
    summary = _build_summary(wave_id, wave_data)
    if summary:
        _print_summary(summary)
        _aggregate_to_stats(summary)
    print(f"  Next: version bump, changelog, and housekeeping commit.")

    if as_json:
        result = {"status": "complete", "merged": merged, "waveId": wave_id}
        if summary:
            result["costSummary"] = summary
        print(json.dumps(result, indent=2))


# ══════════════════════════════════════════════════════════════
# --summary
# ══════════════════════════════════════════════════════════════

def _build_summary(wave_id, wave_data):
    """Build cost summary from wave log + wave task definitions. Returns dict or None."""
    log_path = WAVES_DIR / f"{wave_id}-log.json"
    if not log_path.exists():
        return None

    log_data = atomic_read(log_path)
    events = log_data.get("events", [])

    # Gather actual token usage and commit counts from complete events
    task_tokens = {}  # taskId → tokens
    total_commits = 0
    total_conflicts = 0
    for evt in events:
        if evt.get("type") == "complete":
            task_tokens[evt["taskId"]] = evt.get("tokensUsed", 0)
            total_commits += evt.get("commits", 0)
        elif evt.get("type") == "merge":
            total_conflicts += evt.get("conflicts", 0)

    # Compute duration from wave creation to completion (or now)
    start = wave_data.get("createdAt", "")
    end = wave_data.get("completedAt", "") or now_iso()
    duration = _compute_duration(start, end)

    # Build per-task cost breakdown
    tasks = wave_data.get("tasks", [])
    task_costs = []
    by_model = {}  # model → {"tokens": N, "cost": N, "tasks": N}
    total_tokens = 0
    total_cost = 0.0
    warnings = []

    for task in tasks:
        tid = task["taskId"]
        model = (task.get("model") or "sonnet").lower()
        size = (task.get("size") or "M").upper()
        actual_tokens = task_tokens.get(tid, 0)
        est_tokens = TOKEN_ESTIMATES.get((model, size), 50_000)
        cost_per_m = COST_PER_M_TOKENS.get(model, 2.40)

        # Use actual tokens if available, otherwise estimate
        tokens = actual_tokens if actual_tokens > 0 else est_tokens
        source = "actual" if actual_tokens > 0 else "estimated"
        cost = tokens / 1_000_000 * cost_per_m

        total_tokens += tokens
        total_cost += cost

        # Per-model aggregation
        if model not in by_model:
            by_model[model] = {"tokens": 0, "cost": 0.0, "tasks": 0}
        by_model[model]["tokens"] += tokens
        by_model[model]["cost"] += cost
        by_model[model]["tasks"] += 1

        task_costs.append({
            "taskId": tid,
            "model": model,
            "size": size,
            "tokens": tokens,
            "source": source,
            "cost": round(cost, 4),
        })

        # Per-task threshold alerts
        threshold = TOKEN_WARN.get(model)
        if threshold and actual_tokens > threshold:
            warnings.append(
                f"WARN: {tid} ({model}) used {actual_tokens:,} tokens "
                f"(threshold: {threshold:,})"
            )

    # Wave-level cost alert
    if total_cost > WAVE_COST_WARN:
        warnings.append(
            f"WARN: Wave total £{total_cost:.2f} exceeds threshold £{WAVE_COST_WARN:.2f}"
        )

    return {
        "waveId": wave_id,
        "timestamp": now_iso(),
        "duration": duration,
        "taskCount": len(tasks),
        "totalCommits": total_commits,
        "totalConflicts": total_conflicts,
        "totalTokens": total_tokens,
        "totalCostGBP": round(total_cost, 2),
        "byModel": {m: {"tokens": d["tokens"], "costGBP": round(d["cost"], 2),
                         "tasks": d["tasks"]} for m, d in by_model.items()},
        "tasks": task_costs,
        "warnings": warnings,
    }


def _print_summary(summary):
    """Print a formatted cost summary to stdout."""
    W = 58  # inner width (characters between | and |)

    def row(text):
        print(f"| {text.ljust(W - 2)} |")

    def sep():
        print("+" + "-" * W + "+")

    sep()
    row("Wave Summary")
    sep()
    row(f"Wave: {summary['waveId']}   Duration: {summary.get('duration', '?')}")
    row(f"Tasks: {summary['taskCount']}   "
        f"Commits: {summary.get('totalCommits', 0)}   "
        f"Conflicts: {summary.get('totalConflicts', 0)}")
    row(f"Tokens: {summary['totalTokens']:,}   "
        f"Cost: GBP {summary['totalCostGBP']:.2f}")
    sep()

    # Per-task breakdown
    for tc in summary["tasks"]:
        tag = "~" if tc["source"] == "estimated" else "*"
        row(f"{tag} {tc['taskId']:<22} {tc['model']:<7} "
            f"{tc['tokens']:>8,} tok  GBP {tc['cost']:.2f}")

    # Per-model subtotals
    if len(summary["byModel"]) > 1:
        sep()
        for model, data in summary["byModel"].items():
            row(f"{model:<10} {data['tasks']} task(s)  "
                f"{data['tokens']:>8,} tok  GBP {data['costGBP']:.2f}")

    # Warnings
    if summary["warnings"]:
        sep()
        for w in summary["warnings"]:
            text = w if len(w) <= W - 2 else w[:W - 5] + "..."
            row(text)

    sep()
    row("* = actual tokens   ~ = estimated")
    sep()


def _aggregate_to_stats(summary):
    """Append wave cost summary to .claude/stats.json."""
    if not STATS_FILE.exists():
        return

    try:
        stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    tracking = stats.setdefault("costTracking", {
        "totalWaves": 0,
        "totalTokens": 0,
        "totalCostGBP": 0.0,
        "waves": [],
    })

    tracking["totalWaves"] += 1
    tracking["totalTokens"] += summary["totalTokens"]
    tracking["totalCostGBP"] = round(
        tracking["totalCostGBP"] + summary["totalCostGBP"], 2
    )
    tracking["waves"].append({
        "waveId": summary["waveId"],
        "date": summary["timestamp"][:10],
        "tasks": summary["taskCount"],
        "tokens": summary["totalTokens"],
        "costGBP": summary["totalCostGBP"],
    })

    # Keep only last 20 wave entries
    tracking["waves"] = tracking["waves"][-20:]

    STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")


def cmd_summary(as_json=False):
    """Show cost summary for the latest wave."""
    wave_path, wave_data = find_latest_wave()
    if not wave_data:
        print("No wave found.")
        return

    wave_id = wave_data["waveId"]
    summary = _build_summary(wave_id, wave_data)

    if not summary:
        print(f"No log found for wave '{wave_id}'.")
        return

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        _print_summary(summary)


def cmd_log(as_json=False):
    """Show the event trail for the latest wave."""
    wave_path, wave_data = find_latest_wave()
    if not wave_data:
        print("No wave found.")
        return

    wave_id = wave_data["waveId"]
    log_path = WAVES_DIR / f"{wave_id}-log.json"
    if not log_path.exists():
        print(f"No log found for wave '{wave_id}'.")
        return

    log_data = atomic_read(log_path)
    events = log_data.get("events", [])

    if as_json:
        print(json.dumps(log_data, indent=2))
        return

    print(f"Wave log: {wave_id} ({len(events)} events)")
    print()

    icons = {
        "claim": ">>", "complete": "OK", "abandon": "--",
        "reclaim": "<<", "merge": "^^", "abort": "XX",
        "heartbeat": "..", "wave_complete": "**", "failed": "!!",
    }

    for evt in events:
        etype = evt.get("type", "?")
        icon = icons.get(etype, "  ")
        ts = evt.get("timestamp", "?")
        # Show just HH:MM:SS from ISO timestamp
        time_short = ts[11:19] if len(ts) >= 19 else ts

        parts = [f"[{time_short}] {icon} {etype}"]
        if evt.get("taskId"):
            parts.append(evt["taskId"])
        if evt.get("sessionId"):
            parts.append(f"by {evt['sessionId']}")
        if evt.get("commits"):
            parts.append(f"{evt['commits']} commits")
        if evt.get("tokensUsed"):
            parts.append(f"{evt['tokensUsed']:,} tok")
        if evt.get("conflicts"):
            parts.append(f"{evt['conflicts']} conflicts")
        if evt.get("duration"):
            parts.append(evt["duration"])
        if evt.get("merged"):
            parts.append(f"merged: {', '.join(evt['merged'])}")
        if evt.get("reason"):
            parts.append(evt["reason"])

        print("  ".join(parts))


# ══════════════════════════════════════════════════════════════
# --status
# ══════════════════════════════════════════════════════════════

def cmd_status(as_json=False):
    """Show current wave status."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        if as_json:
            print(json.dumps({"status": "no_active_wave"}))
        else:
            print("No active wave. Use --init-wave to start one.")
        return

    claims = atomic_read(CLAIMS_FILE)
    sessions = atomic_read(SESSIONS_FILE)

    wave_id = wave_data["waveId"]
    tasks = wave_data.get("tasks", [])
    now = datetime.now(timezone.utc)

    # Build task status list
    task_statuses = []
    counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}

    for task in tasks:
        tid = task["taskId"]
        claim = claims.get("claims", {}).get(tid, {})
        status = claim.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
        task_statuses.append({
            "taskId": tid,
            "description": task.get("description", ""),
            "status": status,
            "claimedBy": claim.get("sessionId"),
            "model": task.get("model"),
            "size": task.get("size"),
            "versionTag": task.get("versionTag"),
        })

    # Session status with stale detection
    session_statuses = []
    for s in sessions.get("sessions", []):
        is_stale = False
        last_hb = s.get("lastHeartbeat", "")
        if last_hb:
            try:
                hb_str = last_hb.replace("+00:00", "+00:00")
                hb_time = datetime.fromisoformat(hb_str)
                if hb_time.tzinfo is None:
                    hb_time = hb_time.replace(tzinfo=timezone.utc)
                is_stale = (now - hb_time).total_seconds() > STALE_THRESHOLD
            except (ValueError, TypeError):
                pass
        session_statuses.append({**s, "isStale": is_stale})

    total_tokens = sum(s.get("tokensUsed", 0) for s in sessions.get("sessions", []))

    result = {
        "waveId": wave_id,
        "feature": wave_data.get("feature", ""),
        "status": wave_data.get("status"),
        "totalTasks": len(tasks),
        "tasksCompleted": counts["completed"],
        "tasksInProgress": counts["in_progress"],
        "tasksFailed": counts["failed"],
        "tasksPending": counts["pending"],
        "tasks": task_statuses,
        "sessions": session_statuses,
        "totalTokensUsed": total_tokens,
    }

    if as_json:
        print(json.dumps(result, indent=2))
        return

    # Human-readable output
    total = len(tasks)
    done = counts["completed"]
    bar_len = 10
    filled = round(done / total * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"Wave: {wave_id} — {wave_data.get('feature', '')}")
    print(f"Progress: {bar} {done}/{total} tasks")
    print()

    icons = {"pending": "○", "in_progress": "●", "completed": "✓", "failed": "✗"}
    for ts in task_statuses:
        icon = icons.get(ts["status"], "?")
        who = f"  [{ts['claimedBy']}]" if ts["claimedBy"] else ""
        model = ts.get("model") or ""
        size = ts.get("size") or ""
        print(f"  {icon} {ts['taskId']:<30} {ts['status']:<12} {model:<8} {size}{who}")

    if session_statuses:
        print()
        for ss in session_statuses:
            stale = " STALE" if ss.get("isStale") else ""
            task = ss.get("claimedTask") or "idle"
            tokens = ss.get("tokensUsed", 0)
            print(f"  Session {ss['sessionId']}{stale}  task={task}  tokens={tokens:,}")


# ══════════════════════════════════════════════════════════════
# --validate
# ══════════════════════════════════════════════════════════════

# Rough token estimates per model/size for cost projection
TOKEN_ESTIMATES = {
    # (model, size) → estimated tokens
    ("haiku", "S"): 15_000,
    ("haiku", "M"): 30_000,
    ("haiku", "L"): 60_000,
    ("sonnet", "S"): 20_000,
    ("sonnet", "M"): 50_000,
    ("sonnet", "L"): 120_000,
    ("opus", "S"): 25_000,
    ("opus", "M"): 60_000,
    ("opus", "L"): 150_000,
}

# Cost per 1M tokens (input+output blended estimate, GBP)
COST_PER_M_TOKENS = {
    "haiku": 0.65,
    "sonnet": 2.40,
    "opus": 12.00,
}


def cmd_validate(wave_file_arg, as_json=False):
    """Validate a wave file before launching. Delegates to _analyze_wave for checks."""
    wave_file = Path(wave_file_arg)
    if not wave_file.exists():
        print(f"ERROR: Wave file not found: {wave_file}")
        sys.exit(1)

    wave_data = json.loads(wave_file.read_text(encoding="utf-8"))
    tasks = wave_data.get("tasks", [])

    if not tasks:
        print("ERROR: Wave file has no tasks")
        sys.exit(1)

    # Use shared analysis
    analysis = _analyze_wave(wave_data)
    blocks = analysis["blocks"]
    warns = analysis["warnings"]
    task_costs = analysis["taskCosts"]
    total_cost = analysis["totalCost"]

    if as_json:
        print(json.dumps({
            "valid": analysis["ready"],
            "blocks": [f[1] for f in blocks],
            "warnings": [f[1] for f in warns],
            "taskCount": len(tasks),
            "costEstimate": {
                "total": f"£{total_cost:.2f}",
                "tasks": task_costs,
            },
        }, indent=2))
        return

    # Human-readable
    print(f"Validating: {wave_file.name} — {len(tasks)} tasks\n")

    if blocks:
        for _, msg in blocks:
            print(f"  BLOCK  {msg}")
        print()

    if warns:
        for _, msg in warns:
            print(f"  WARN   {msg}")
        print()

    # Cost table
    print("  Cost estimate:")
    for tc in task_costs:
        print(f"    {tc['taskId']:<30} {tc['model']:<8} {tc['size']:<4} ~{tc['estTokens']:>7,} tok  ~£{tc['estCost']:.2f}")
    print(f"    {'─' * 60}")
    print(f"    {'Total':<44} ~£{total_cost:.2f}")
    print()

    if blocks:
        print(f"  RESULT: BLOCKED — {len(blocks)} issue(s) must be fixed before launch")
        sys.exit(1)
    elif warns:
        print(f"  RESULT: PASS with {len(warns)} warning(s)")
    else:
        print("  RESULT: PASS — all checks clean")


# ══════════════════════════════════════════════════════════════
# --preview (shared analysis + bordered preview card)
# ══════════════════════════════════════════════════════════════

def _analyze_wave(wave_data):
    """Analyze a wave for conflicts, cost, and readiness. Returns structured dict."""
    tasks = wave_data.get("tasks", [])
    task_ids = {t["taskId"] for t in tasks}
    findings = []  # (severity, message)

    # 1. File ownership conflicts
    ownership = {}  # file_pattern → [taskId, ...]
    for task in tasks:
        for f in task.get("owns", []):
            ownership.setdefault(f, []).append(task["taskId"])

    for file_pat, owners in ownership.items():
        if len(owners) > 1:
            findings.append(("BLOCK", f"File ownership conflict: '{file_pat}' owned by {', '.join(owners)}"))

    # 2. Read overlaps (informational — shared reads are safe)
    reads = {}  # file_pattern → [taskId, ...]
    for task in tasks:
        for f in task.get("reads", []):
            reads.setdefault(f, []).append(task["taskId"])
    read_overlaps = {fp: readers for fp, readers in reads.items() if len(readers) > 1}

    # 3. Dependency checks
    for task in tasks:
        for dep in task.get("dependsOn", []):
            if dep not in task_ids:
                findings.append(("BLOCK", f"Task '{task['taskId']}' depends on unknown task '{dep}'"))

    # Circular dependency detection (DFS)
    dep_graph = {t["taskId"]: t.get("dependsOn", []) for t in tasks}
    visited = set()
    in_stack = set()

    def _has_cycle(node):
        if node in in_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in dep_graph.get(node, []):
            if _has_cycle(dep):
                return True
        in_stack.discard(node)
        return False

    for tid in task_ids:
        visited.clear()
        in_stack.clear()
        if _has_cycle(tid):
            findings.append(("BLOCK", f"Circular dependency detected involving '{tid}'"))
            break

    # 4. Model appropriateness
    for task in tasks:
        model = (task.get("model") or "").lower()
        size = (task.get("size") or "").upper()
        tid = task["taskId"]
        if not model:
            findings.append(("WARN", f"Task '{tid}' has no model specified"))
        if not size:
            findings.append(("WARN", f"Task '{tid}' has no size specified"))
        if model == "haiku" and size == "L":
            findings.append(("WARN", f"Task '{tid}': haiku on L task — may exceed context"))
        if model == "opus" and size == "S":
            findings.append(("WARN", f"Task '{tid}': opus on S task — consider sonnet"))

    # 5. Missing fields + contract validation
    for task in tasks:
        tid = task["taskId"]
        if not task.get("description"):
            findings.append(("WARN", f"Task '{tid}' has no description"))
        if not task.get("owns"):
            findings.append(("WARN", f"Task '{tid}' has no file ownership declared"))
        if not task.get("acceptanceCriteria"):
            findings.append(("WARN", f"Task '{tid}' has no acceptance criteria"))
        else:
            # Validate and auto-promote acceptance criteria
            promoted = []
            for i, ac in enumerate(task["acceptanceCriteria"]):
                if isinstance(ac, str):
                    # Detect manual criteria by prefix
                    if ac.strip().lower().startswith("manual:"):
                        promoted.append({"text": ac, "type": "manual", "verify": ""})
                    else:
                        # Auto-promote flat string to structured object
                        promoted.append({"text": ac, "type": "auto", "verify": ac})
                elif isinstance(ac, dict):
                    promoted.append(ac)
                else:
                    findings.append(("WARN", f"Task '{tid}' criterion {i}: unexpected format"))
                    continue

                # Validate executable patterns for auto criteria only
                entry = promoted[-1]
                if entry.get("type", "auto") == "auto":
                    verify_str = entry.get("verify", "")
                    if not verify_str:
                        findings.append(("BLOCK", f"Task '{tid}' [auto] criterion {i}: missing Verify: pattern"))
                    else:
                        valid_patterns = [
                            r"^run:\s+.+$",
                            r"^file:\s+.+\s+exists$",
                            r"^file:\s+.+\s+contains\s+.+$",
                            r"^html:\s+.+\s+has\s+.+$",
                        ]
                        if not any(re.match(p, verify_str.strip()) for p in valid_patterns):
                            findings.append(("BLOCK", f"Task '{tid}' [auto] criterion {i}: invalid Verify: pattern '{verify_str}'"))

            # Write promoted criteria back
            task["acceptanceCriteria"] = promoted

    # 6. Cost estimate
    total_cost = 0.0
    task_costs = []
    for task in tasks:
        model = (task.get("model") or "sonnet").lower()
        size = (task.get("size") or "M").upper()
        est_tokens = TOKEN_ESTIMATES.get((model, size), 50_000)
        cost_per_m = COST_PER_M_TOKENS.get(model, 2.40)
        cost = est_tokens / 1_000_000 * cost_per_m
        total_cost += cost
        task_costs.append({
            "taskId": task["taskId"],
            "model": model,
            "size": size,
            "estTokens": est_tokens,
            "estCost": round(cost, 2),
        })

    blocks = [f for f in findings if f[0] == "BLOCK"]
    warns = [f for f in findings if f[0] == "WARN"]
    merge_order = [t["taskId"] for t in tasks]

    return {
        "blocks": blocks,
        "warnings": warns,
        "ownership": ownership,
        "readOverlaps": read_overlaps,
        "taskCosts": task_costs,
        "totalCost": total_cost,
        "mergeOrder": merge_order,
        "ready": len(blocks) == 0,
    }


def cmd_preview(wave_file_arg=None, as_json=False):
    """Preview a wave before launching. Shows tasks, overlap check, cost, merge order."""
    if wave_file_arg:
        wave_file = Path(wave_file_arg)
        if not wave_file.exists():
            print(f"ERROR: Wave file not found: {wave_file}")
            sys.exit(1)
        wave_data = json.loads(wave_file.read_text(encoding="utf-8"))
    else:
        # Auto-detect: prefer active wave, fall back to latest
        _, wave_data = find_active_wave()
        if not wave_data:
            _, wave_data = find_latest_wave()
        if not wave_data:
            print("ERROR: No wave file found. Create one with /hq --plan")
            sys.exit(1)

    tasks = wave_data.get("tasks", [])
    if not tasks:
        print("ERROR: Wave has no tasks")
        sys.exit(1)

    analysis = _analyze_wave(wave_data)
    wave_id = wave_data.get("waveId", "unknown")

    if as_json:
        result = {
            "mode": "preview",
            "waveId": wave_id,
            "feature": wave_data.get("feature", ""),
            "status": wave_data.get("status", "unknown"),
            "taskCount": len(tasks),
            "tasks": [],
            "overlapCheck": {
                "conflicts": [
                    {"file": fp, "owners": owners}
                    for fp, owners in analysis["ownership"].items()
                    if len(owners) > 1
                ],
                "sharedReads": [
                    {"file": fp, "readers": readers}
                    for fp, readers in analysis["readOverlaps"].items()
                ],
            },
            "blocks": [f[1] for f in analysis["blocks"]],
            "warnings": [f[1] for f in analysis["warnings"]],
            "costEstimate": {
                "totalGBP": f"\u00a3{analysis['totalCost']:.2f}",
                "totalTokens": sum(tc["estTokens"] for tc in analysis["taskCosts"]),
                "tasks": analysis["taskCosts"],
            },
            "mergeOrder": analysis["mergeOrder"],
            "ready": analysis["ready"],
        }
        for task in tasks:
            result["tasks"].append({
                "taskId": task["taskId"],
                "description": task.get("description", ""),
                "model": task.get("model", "sonnet"),
                "size": task.get("size", "M"),
                "versionTag": task.get("versionTag"),
                "owns": task.get("owns", []),
                "reads": task.get("reads", []),
            })
        print(json.dumps(result, indent=2))
        return

    # ── Bordered card output ──
    lines = []
    lines.append(f"  TASKS ({len(tasks)})")

    for i, task in enumerate(tasks, 1):
        model = task.get("model", "sonnet")
        size = task.get("size", "M")
        ver = task.get("versionTag", "")
        ver_str = f"  {ver}" if ver else ""
        lines.append(f"  {i}. {task['taskId']}  {model}  {size}{ver_str}")
        owns = task.get("owns", [])
        if owns:
            lines.append(f"     OWNS: {', '.join(owns)}")
        reads = task.get("reads", [])
        if reads:
            lines.append(f"     READS: {', '.join(reads)}")
        if i < len(tasks):
            lines.append("")

    lines.append("")
    lines.append("  OVERLAP CHECK")
    conflicts = [
        (fp, owners) for fp, owners in analysis["ownership"].items()
        if len(owners) > 1
    ]
    if conflicts:
        for fp, owners in conflicts:
            lines.append(f"  \u274c CONFLICT: '{fp}' owned by {', '.join(owners)}")
    else:
        lines.append("  \u2713 No file ownership conflicts")

    if analysis["readOverlaps"]:
        for fp, readers in analysis["readOverlaps"].items():
            names = " + ".join(readers)
            lines.append(f"  \u26a0\ufe0f  {names} READ {fp} (read-only \u2014 safe)")

    lines.append("")
    lines.append("  COST ESTIMATE")
    total_tokens = sum(tc["estTokens"] for tc in analysis["taskCosts"])
    lines.append(f"  {len(tasks)} tasks \u2248 {total_tokens:,} tokens \u2248 \u00a3{analysis['totalCost']:.2f}")

    if analysis["warnings"]:
        lines.append("")
        lines.append("  WARNINGS")
        for _, msg in analysis["warnings"]:
            lines.append(f"  \u26a0\ufe0f  {msg}")

    if analysis["blocks"]:
        lines.append("")
        lines.append("  BLOCKERS")
        for _, msg in analysis["blocks"]:
            lines.append(f"  \u274c {msg}")

    lines.append("")
    lines.append("  MERGE ORDER")
    arrow = " \u2192 "
    lines.append(f"  {arrow.join(analysis['mergeOrder'])}")

    lines.append("")
    if analysis["ready"]:
        lines.append("  READY? Run /hq --launch to start.")
    else:
        n = len(analysis["blocks"])
        lines.append(f"  BLOCKED \u2014 {n} issue(s) must be fixed before launch.")

    # Render bordered card
    header = f"  HQ PREVIEW \u00b7 {wave_id}"
    max_w = max(len(header), max(len(line) for line in lines)) + 4
    print("\u250c" + "\u2500" * max_w + "\u2510")
    print("\u2502" + header.ljust(max_w) + "\u2502")
    print("\u251c" + "\u2500" * max_w + "\u2524")
    for line in lines:
        print("\u2502" + line.ljust(max_w) + "\u2502")
    print("\u2514" + "\u2500" * max_w + "\u2518")


# ══════════════════════════════════════════════════════════════
# --dashboard
# ══════════════════════════════════════════════════════════════

def cmd_dashboard(as_json=False):
    """Dashboard output for /hq command. Superset of --status with cost, merge order, conflicts."""
    wave_path, wave_data = find_active_wave()
    if not wave_data:
        result = {"mode": "no_wave"}
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print("No active wave.")
        return

    claims = atomic_read(CLAIMS_FILE)
    sessions = atomic_read(SESSIONS_FILE)

    wave_id = wave_data["waveId"]
    tasks = wave_data.get("tasks", [])
    now = datetime.now(timezone.utc)

    # ── Task statuses ──
    task_statuses = []
    counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}

    for task in tasks:
        tid = task["taskId"]
        claim = claims.get("claims", {}).get(tid, {})
        status = claim.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
        task_statuses.append({
            "taskId": tid,
            "description": task.get("description", ""),
            "status": status,
            "claimedBy": claim.get("sessionId"),
            "model": task.get("model"),
            "size": task.get("size"),
            "versionTag": task.get("versionTag"),
            "owns": task.get("owns", []),
            "dependsOn": task.get("dependsOn", []),
        })

    # ── Session statuses with stale detection ──
    session_statuses = []
    for s in sessions.get("sessions", []):
        is_stale = False
        heartbeat_ago = None
        last_hb = s.get("lastHeartbeat", "")
        if last_hb:
            try:
                hb_time = datetime.fromisoformat(last_hb)
                if hb_time.tzinfo is None:
                    hb_time = hb_time.replace(tzinfo=timezone.utc)
                delta = (now - hb_time).total_seconds()
                is_stale = delta > STALE_THRESHOLD
                if delta < 60:
                    heartbeat_ago = f"{int(delta)}s ago"
                else:
                    heartbeat_ago = f"{int(delta // 60)}m ago"
            except (ValueError, TypeError):
                pass
        session_statuses.append({
            **s,
            "isStale": is_stale,
            "heartbeatAgo": heartbeat_ago,
        })

    # ── File ownership conflicts ──
    ownership = {}
    for task in tasks:
        for f in task.get("owns", []):
            ownership.setdefault(f, []).append(task["taskId"])
    conflicts = [
        {"file": fp, "owners": owners}
        for fp, owners in ownership.items() if len(owners) > 1
    ]

    # ── Cost estimate ──
    total_cost = 0.0
    task_costs = []
    for task in tasks:
        model = (task.get("model") or "sonnet").lower()
        size = (task.get("size") or "M").upper()
        est_tokens = TOKEN_ESTIMATES.get((model, size), 50_000)
        cost_per_m = COST_PER_M_TOKENS.get(model, 2.40)
        cost = est_tokens / 1_000_000 * cost_per_m
        total_cost += cost
        task_costs.append({
            "taskId": task["taskId"],
            "model": model,
            "size": size,
            "estTokens": est_tokens,
            "estCost": round(cost, 2),
        })

    # ── Merge order (task order from wave definition) ──
    merge_order = [t["taskId"] for t in tasks]

    # ── Tokens used ──
    total_tokens = sum(s.get("tokensUsed", 0) for s in sessions.get("sessions", []))
    active_sessions = [s for s in session_statuses if not s.get("isStale")]
    mode = "multi-terminal" if len(active_sessions) > 1 else "single-terminal"

    total = len(tasks)
    done = counts["completed"]

    result = {
        "mode": "active",
        "waveId": wave_id,
        "feature": wave_data.get("feature", ""),
        "waveStatus": wave_data.get("status"),
        "terminalMode": mode,
        "activeSessions": len(active_sessions),
        "totalTasks": total,
        "tasksCompleted": done,
        "tasksInProgress": counts["in_progress"],
        "tasksFailed": counts["failed"],
        "tasksPending": counts["pending"],
        "tasks": task_statuses,
        "sessions": session_statuses,
        "conflicts": conflicts,
        "costEstimate": {
            "totalGBP": f"£{total_cost:.2f}",
            "totalTokens": sum(tc["estTokens"] for tc in task_costs),
            "tasks": task_costs,
        },
        "actualTokensUsed": total_tokens,
        "mergeOrder": merge_order,
    }

    if as_json:
        print(json.dumps(result, indent=2))
        return

    # Human-readable dashboard
    bar_len = 10
    filled = round(done / total * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"HQ — Wave: {wave_id} · {wave_data.get('feature', '')}")
    print(f"Mode: {mode} ({len(active_sessions)} active)")
    print(f"Status: {bar} {done}/{total} tasks — "
          f"{counts['in_progress']} in progress · {counts['pending']} pending")
    print()

    # Terminals
    if session_statuses:
        print("Terminals:")
        for ss in session_statuses:
            icon = "○" if ss.get("isStale") else "●"
            task = ss.get("claimedTask") or "idle"
            model = ss.get("model") or ""
            hb = ss.get("heartbeatAgo") or "?"
            tokens = ss.get("tokensUsed", 0)
            stale = " STALE" if ss.get("isStale") else ""
            print(f"  {icon} {ss['sessionId']:<18} {task:<25} {model:<8} ♥ {hb:<10} {tokens:>6,} tok{stale}")
        print()

    # Tasks
    print("Tasks:")
    icons = {"pending": "⚪", "in_progress": "🔵", "completed": "🟢", "failed": "🔴"}
    for ts in task_statuses:
        icon = icons.get(ts["status"], "?")
        who = f"→ {ts['claimedBy']}" if ts["claimedBy"] else ""
        model = ts.get("model") or ""
        size = ts.get("size") or ""
        ver = ts.get("versionTag") or ""
        print(f"  {icon} {ts['taskId']:<25} {who:<20} {model:<4} {ver:<10} {ts['status']}")
    print()

    # Conflicts
    if conflicts:
        print("Conflicts:")
        for c in conflicts:
            print(f"  ⚠️  {c['file']} — owned by {', '.join(c['owners'])}")
        print()
    else:
        print("Conflicts: None detected")

    # Cost
    print(f"Cost estimate: ~{sum(tc['estTokens'] for tc in task_costs):,} tokens (~{result['costEstimate']['totalGBP']})")
    if total_tokens:
        print(f"Tokens used so far: {total_tokens:,}")

    # Merge order
    print(f"Merge order: {' → '.join(merge_order)}")


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Multi-agent wave coordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init-wave", dest="wave_file", metavar="FILE",
                       help="Initialize wave from JSON definition file")
    group.add_argument("--claim", action="store_true",
                       help="Claim next available task for this session")
    group.add_argument("--complete", dest="task_id", metavar="TASK_ID",
                       help="Mark a claimed task as completed")
    group.add_argument("--status", action="store_true",
                       help="Show current wave status")
    group.add_argument("--dashboard", action="store_true",
                       help="Dashboard output for /hq (superset of --status)")
    group.add_argument("--abandon", dest="abandon_id", metavar="TASK_ID",
                       help="Abandon a claimed task (releases claim, removes worktree+branch)")
    group.add_argument("--fail", dest="fail_id", metavar="TASK_ID",
                       help="Mark a task as failed (keeps worktree+branch for debugging)")
    group.add_argument("--heartbeat", action="store_true",
                       help="Update this session's heartbeat timestamp")
    group.add_argument("--reclaim", action="store_true",
                       help="Reclaim tasks from stale sessions")
    group.add_argument("--merge", action="store_true",
                       help="Merge completed tasks to master sequentially")
    group.add_argument("--validate", dest="validate_file", metavar="FILE",
                       help="Validate a wave file before launching")
    group.add_argument("--preview", nargs="?", const="__auto__", dest="preview_file",
                       metavar="FILE",
                       help="Preview a wave before launching (auto-detects if no file given)")
    group.add_argument("--summary", action="store_true",
                       help="Show cost summary for the latest wave")
    group.add_argument("--log", action="store_true",
                       help="Show event trail for the latest wave")

    parser.add_argument("--reason", dest="fail_reason", metavar="TEXT",
                        help="Reason for failure (used with --fail)")
    parser.add_argument("--session", dest="session_id", metavar="ID",
                        help="Override session ID (default: terminal-{PID})")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (for --status, --claim)")
    parser.add_argument("--tokens", type=int, default=0,
                        help="Token count to record (for --complete)")
    parser.add_argument("--commits", type=int, default=0,
                        help="Commit count to record (for --complete)")
    parser.add_argument("--parent-pid", dest="parent_pid", type=int, metavar="PID",
                        help="Claude Code PID for per-terminal session-id files (pass $PPID)")
    parser.add_argument("--skip-verify", dest="skip_verify", action="store_true",
                        help="Skip verification gate on --complete (for docs-only changes)")
    parser.add_argument("--project-root", dest="project_root", metavar="DIR",
                        help="Override project root (default: current directory)")

    args = parser.parse_args()

    if args.project_root:
        global PROJECT_ROOT, MAIN_ROOT, WORKTREE_ROOT, WAVES_DIR, CLAIMS_FILE, SESSIONS_FILE, STATS_FILE, WORKTREE_DIR
        PROJECT_ROOT = Path(args.project_root).resolve()
        MAIN_ROOT = PROJECT_ROOT
        WORKTREE_ROOT = Path.cwd()  # Keep actual cwd as worktree root
        WAVES_DIR = PROJECT_ROOT / ".tmp" / "waves"
        CLAIMS_FILE = WAVES_DIR / "claims.json"
        SESSIONS_FILE = WAVES_DIR / "sessions.json"
        STATS_FILE = PROJECT_ROOT / ".claude" / "stats.json"
        WORKTREE_DIR = PROJECT_ROOT / ".claude" / "worktrees"

    global _session_override
    if args.session_id:
        _session_override = args.session_id
    elif args.parent_pid:
        # Read session ID from PID-specific file (written by --claim --parent-pid)
        # This makes --complete, --fail, --abandon resolve the correct session
        sid_file = PROJECT_ROOT / ".tmp" / f".session-id-{args.parent_pid}"
        if sid_file.exists():
            try:
                sid = sid_file.read_text().strip()
                if sid:
                    _session_override = sid
            except OSError:
                pass

    if args.wave_file:
        cmd_init_wave(args.wave_file)
    elif args.claim:
        cmd_claim(as_json=args.json, parent_pid=args.parent_pid)
    elif args.task_id:
        cmd_complete(args.task_id, tokens=args.tokens, commits=args.commits, skip_verify=args.skip_verify)
    elif args.status:
        cmd_status(as_json=args.json)
    elif args.dashboard:
        cmd_dashboard(as_json=args.json)
    elif args.abandon_id:
        cmd_abandon(args.abandon_id)
    elif args.fail_id:
        cmd_fail(args.fail_id, reason=getattr(args, "fail_reason", "") or "")
    elif args.heartbeat:
        cmd_heartbeat()
    elif args.reclaim:
        cmd_reclaim(as_json=args.json)
    elif args.merge:
        cmd_merge(as_json=args.json)
    elif args.validate_file:
        cmd_validate(args.validate_file, as_json=args.json)
    elif args.preview_file:
        file_arg = None if args.preview_file == "__auto__" else args.preview_file
        cmd_preview(file_arg, as_json=args.json)
    elif args.summary:
        cmd_summary(as_json=args.json)
    elif args.log:
        cmd_log(as_json=args.json)


if __name__ == "__main__":
    main()
