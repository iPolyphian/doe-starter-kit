#!/usr/bin/env python3
"""
Compute session metrics, streaks, and stats for /wrap.

Deterministic script that gathers git metrics, computes streaks,
updates stats.json (v2), and outputs JSON to stdout.

Usage:
    python3 execution/wrap_stats.py \
      --since <first-session-commit-hash> \
      --session-start <ISO-timestamp> \
      --todo tasks/todo.md \
      --stats .claude/stats.json \
      [--dry-run]
"""

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Git helpers ──────────────────────────────────────────────

def run_git(*args, timeout: int = 10) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def gather_git_metrics(since: str) -> dict:
    metrics = {"commits": 0, "linesAdded": 0, "linesRemoved": 0,
               "filesTouched": 0, "commitLog": []}

    log_output = run_git("log", "--oneline", f"{since}^..HEAD")
    if not log_output:
        log_output = run_git("log", "--oneline", f"{since}..HEAD")
        if not log_output:
            log_output = run_git("log", "--oneline", "-1", since)
            if not log_output:
                return metrics

    metrics["commits"] = len([l for l in log_output.split("\n") if l.strip()])

    shortstat = run_git("diff", "--shortstat", f"{since}^..HEAD")
    if not shortstat:
        shortstat = run_git("diff", "--shortstat", f"{since}..HEAD")
    if shortstat:
        m = re.search(r"(\d+)\s+file", shortstat)
        if m: metrics["filesTouched"] = int(m.group(1))
        m = re.search(r"(\d+)\s+insertion", shortstat)
        if m: metrics["linesAdded"] = int(m.group(1))
        m = re.search(r"(\d+)\s+deletion", shortstat)
        if m: metrics["linesRemoved"] = int(m.group(1))

    fmt = run_git("log", "--format=%aI %s", "--reverse", f"{since}^..HEAD")
    if not fmt:
        fmt = run_git("log", "--format=%aI %s", "--reverse", f"{since}..HEAD")
    if fmt:
        for line in fmt.split("\n"):
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                metrics["commitLog"].append({"time": parts[0], "message": parts[1]})

    return metrics


# ── Todo parsing ─────────────────────────────────────────────

def count_steps_completed_since(todo_path: Path, session_start: str) -> int:
    """Count [x] steps completed after the session start time."""
    if not todo_path.exists():
        return 0
    try:
        start_dt = datetime.fromisoformat(session_start)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        start_dt = start_dt.astimezone(None)  # convert to local
    except (ValueError, TypeError):
        return 0
    count = 0
    for line in todo_path.read_text(encoding="utf-8").split("\n"):
        if re.match(r"^\s*(?:\d+\.\s*)?\[x\]", line, re.IGNORECASE):
            m = re.search(r"completed\s+(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{2})", line)
            if m:
                hh, mm = int(m.group(1)), int(m.group(2))
                dd, mo, yy = int(m.group(3)), int(m.group(4)), 2000 + int(m.group(5))
                try:
                    completed_dt = datetime(yy, mo, dd, hh, mm).astimezone(None)
                    if completed_dt >= start_dt:
                        count += 1
                except ValueError:
                    pass
    return count


# ── Streak & duration ────────────────────────────────────────

def compute_streak(stats: dict) -> int:
    streak_data = stats.get("streak", {})
    last_date_str = streak_data.get("lastSessionDate")
    current = streak_data.get("current", 0)
    today = datetime.now().date()

    if not last_date_str:
        return 1
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 1

    delta = (today - last_date).days
    if delta == 0:
        return current
    elif delta == 1:
        return current + 1
    return 1


def compute_session_duration(session_start: str) -> str:
    try:
        start = datetime.fromisoformat(session_start)
        now = datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        total_minutes = max(0, int((now - start).total_seconds() / 60))
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    except (ValueError, TypeError):
        return "0m"


# ── Stats v2 schema & migration ──────────────────────────────

def fresh_stats() -> dict:
    return {
        "version": 2,
        "lifetime": {
            "totalSessions": 0, "totalCommits": 0,
            "totalLinesAdded": 0, "totalLinesRemoved": 0,
            "firstSessionDate": None,
        },
        "streak": {"current": 0, "best": 0, "lastSessionDate": None},
        "recentSessions": [],
    }


def migrate_v1_to_v2(stats: dict) -> dict:
    lt = stats.get("lifetime", {})
    stats["version"] = 2
    stats["lifetime"] = {
        "totalSessions": lt.get("totalSessions", 0),
        "totalCommits": lt.get("totalCommits", 0),
        "totalLinesAdded": lt.get("totalLinesAdded", 0),
        "totalLinesRemoved": lt.get("totalLinesRemoved", 0),
        "firstSessionDate": lt.get("firstSessionDate"),
    }
    stats.pop("highScores", None)
    stats.pop("badges", None)
    for s in stats.get("recentSessions", []):
        for key in ["rawScore", "multiplier", "finalScore", "badgesEarned", "genre", "mood"]:
            s.pop(key, None)
    return stats


def load_stats(path: Path) -> dict:
    if not path.exists():
        return fresh_stats()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "version" not in data:
            return fresh_stats()
        if data["version"] == 1:
            data = migrate_v1_to_v2(data)
        return data
    except (json.JSONDecodeError, OSError):
        return fresh_stats()


# ── Leaderboard & stats update ───────────────────────────────

def build_leaderboard(stats: dict, current_metrics: dict) -> list:
    recent = stats.get("recentSessions", [])
    today_str = datetime.now().strftime("%Y-%m-%d")

    by_date = {}
    for s in recent:
        d = s.get("date", "")
        if d not in by_date:
            by_date[d] = {"sessions": [], "totalCommits": 0, "totalLines": 0,
                          "bestTitle": "", "streak": 0}
        e = by_date[d]
        e["sessions"].append(s)
        e["totalCommits"] += s.get("commits", 0)
        e["totalLines"] += s.get("linesAdded", 0)
        e["streak"] = max(e["streak"], s.get("streak", 0))
        if not e["bestTitle"]:
            e["bestTitle"] = s.get("title") or ""

    if today_str not in by_date:
        by_date[today_str] = {"sessions": [], "totalCommits": 0, "totalLines": 0,
                              "bestTitle": "Current session", "streak": 0}
    te = by_date[today_str]
    te["totalCommits"] += current_metrics.get("commits", 0)
    te["totalLines"] += current_metrics.get("linesAdded", 0)

    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    board = []
    for i in range(10):
        day_dt = today_dt - timedelta(days=i)
        day_str = day_dt.strftime("%Y-%m-%d")
        display = day_dt.strftime("%d/%m")
        if day_str in by_date:
            e = by_date[day_str]
            title = e["bestTitle"]
            count = len(e["sessions"]) + (1 if day_str == today_str else 0)
            if count > 1:
                title = f"{title} (+{count - 1} more)"
            board.append({"date": display, "commits": e["totalCommits"],
                          "lines": e["totalLines"], "streak": e["streak"], "title": title})
        else:
            board.append({"date": display, "commits": None, "streak": None, "title": "--"})
    return board


def update_stats(stats: dict, metrics: dict, streak: int, steps: int, duration: str) -> dict:
    today_str = datetime.now().strftime("%Y-%m-%d")

    lt = stats.setdefault("lifetime", {})
    lt["totalSessions"] = lt.get("totalSessions", 0) + 1
    lt["totalCommits"] = lt.get("totalCommits", 0) + metrics["commits"]
    lt["totalLinesAdded"] = lt.get("totalLinesAdded", 0) + metrics["linesAdded"]
    lt["totalLinesRemoved"] = lt.get("totalLinesRemoved", 0) + metrics["linesRemoved"]
    if not lt.get("firstSessionDate"):
        lt["firstSessionDate"] = today_str

    sk = stats.setdefault("streak", {})
    sk["current"] = streak
    sk["best"] = max(sk.get("best", 0), streak)
    sk["lastSessionDate"] = today_str

    record = {
        "date": today_str, "title": None, "summary": None,
        "commits": metrics["commits"], "linesAdded": metrics["linesAdded"],
        "linesRemoved": metrics["linesRemoved"], "filesTouched": metrics["filesTouched"],
        "stepsCompleted": steps, "sessionDuration": duration, "streak": streak,
    }
    recent = stats.setdefault("recentSessions", [])
    recent.insert(0, record)
    stats["recentSessions"] = recent[:20]
    return stats


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compute session metrics and stats.")
    parser.add_argument("--since", required=True, help="First session commit hash")
    parser.add_argument("--session-start", required=True, help="Session start ISO timestamp")
    parser.add_argument("--todo", default="tasks/todo.md", help="Path to todo.md")
    parser.add_argument("--stats", default=".claude/stats.json", help="Path to stats.json")
    parser.add_argument("--dry-run", action="store_true", help="Don't write stats.json")
    args = parser.parse_args()

    todo_path = PROJECT_ROOT / args.todo
    stats_path = PROJECT_ROOT / args.stats

    metrics = gather_git_metrics(args.since)
    steps = count_steps_completed_since(todo_path, args.session_start)
    stats = load_stats(stats_path)
    streak = compute_streak(stats)
    duration = compute_session_duration(args.session_start)
    leaderboard = build_leaderboard(stats, metrics)
    updated = update_stats(stats, metrics, streak, steps, duration)

    if not args.dry_run:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    output = {
        "metrics": {**metrics, "stepsCompleted": steps, "sessionDuration": duration},
        "streak": streak,
        "leaderboard": leaderboard,
        "stats": updated,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
