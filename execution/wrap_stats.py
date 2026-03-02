#!/usr/bin/env python3
"""
Compute session wrap-up scoring, badges, streaks, and stats.

Deterministic script that gathers git metrics, parses task completion,
computes scores and badges, updates the persistent stats.json, and
outputs a full JSON report to stdout.

Usage:
    python3 execution/wrap_stats.py \\
      --since <first-session-commit-hash> \\
      --session-start <ISO-timestamp> \\
      --todo tasks/todo.md \\
      --stats .claude/stats.json \\
      [--dry-run]
"""

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════
# Data types
# ══════════════════════════════════════════════════════════════

@dataclass
class CommitEntry:
    time: str  # ISO timestamp
    message: str


@dataclass
class GitMetrics:
    commits: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    files_touched: int = 0
    commit_log: list = field(default_factory=list)
    first_commit_time: Optional[str] = None
    last_commit_time: Optional[str] = None
    night_owl: bool = False
    early_bird: bool = False
    feature_completed: bool = False
    modified_files: list = field(default_factory=list)


@dataclass
class SessionMetrics:
    git: GitMetrics = field(default_factory=GitMetrics)
    steps_completed: int = 0
    learnings_logged: int = 0
    failures: int = 0
    recoveries: int = 0
    session_duration: str = "0m"


# ══════════════════════════════════════════════════════════════
# Stats.json schema
# ══════════════════════════════════════════════════════════════

def fresh_stats() -> dict:
    """Return a blank stats.json structure."""
    return {
        "version": 1,
        "lifetime": {
            "totalSessions": 0,
            "totalCommits": 0,
            "totalLinesAdded": 0,
            "totalLinesRemoved": 0,
            "totalFilesTouched": 0,
            "totalStepsCompleted": 0,
            "totalLearningsLogged": 0,
            "totalBadgesEarned": 0,
            "firstSessionDate": None,
        },
        "streak": {
            "current": 0,
            "best": 0,
            "lastSessionDate": None,
        },
        "highScores": {
            "bestSessionScore": 0,
            "bestSessionDate": None,
            "bestSessionTitle": None,
            "bestRawScore": 0,
            "bestMultiplier": 1.0,
        },
        "badges": {"allTimeEarned": {}},
        "recentSessions": [],
    }


def load_stats(path: Path) -> dict:
    """Load stats.json, returning fresh structure if missing or corrupt."""
    if not path.exists():
        return fresh_stats()
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        # Validate minimum structure
        if not isinstance(data, dict) or "version" not in data:
            return fresh_stats()
        return data
    except (json.JSONDecodeError, OSError):
        return fresh_stats()


# ══════════════════════════════════════════════════════════════
# Git helpers
# ══════════════════════════════════════════════════════════════

def run_git(*args, timeout: int = 10) -> Optional[str]:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def gather_git_metrics(since: str) -> GitMetrics:
    """Gather all git metrics from the commit range since^..HEAD."""
    metrics = GitMetrics()

    # Count commits
    log_output = run_git("log", "--oneline", f"{since}^..HEAD")
    if log_output is None or log_output == "":
        # Try without ^ (since might be the very first commit)
        log_output = run_git("log", "--oneline", f"{since}..HEAD")
        if log_output is None or log_output == "":
            # Maybe since IS head — try just that one commit
            log_output = run_git("log", "--oneline", "-1", since)
            if log_output is None or log_output == "":
                return metrics  # Empty session

    commit_lines = [line for line in log_output.split("\n") if line.strip()]
    metrics.commits = len(commit_lines)

    # Shortstat for insertions/deletions/files
    shortstat = run_git("diff", "--shortstat", f"{since}^..HEAD")
    if shortstat is None:
        shortstat = run_git("diff", "--shortstat", f"{since}..HEAD")
    if shortstat:
        metrics.files_touched, metrics.lines_added, metrics.lines_removed = (
            parse_shortstat(shortstat)
        )

    # Commit times and messages
    format_output = run_git("log", "--format=%aI %s", "--reverse", f"{since}^..HEAD")
    if format_output is None:
        format_output = run_git("log", "--format=%aI %s", "--reverse", f"{since}..HEAD")
    if format_output:
        for line in format_output.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Split on first space after the ISO timestamp
            # ISO timestamps look like: 2026-03-02T14:30:00+00:00
            parts = line.split(" ", 1)
            if len(parts) == 2:
                ts, msg = parts[0], parts[1]
                metrics.commit_log.append(CommitEntry(time=ts, message=msg))

        if metrics.commit_log:
            metrics.first_commit_time = metrics.commit_log[0].time
            metrics.last_commit_time = metrics.commit_log[-1].time

    # Detect night owl (00:00-05:00) and early bird (05:00-07:00)
    for entry in metrics.commit_log:
        hour = parse_hour_from_iso(entry.time)
        if hour is not None:
            if 0 <= hour < 5:
                metrics.night_owl = True
            elif 5 <= hour < 7:
                metrics.early_bird = True

    # Check for feature completion in commit messages
    feature_patterns = [
        r"feature done",
        r"retro",
        r"housekeeping",
    ]
    for entry in metrics.commit_log:
        msg_lower = entry.message.lower()
        for pattern in feature_patterns:
            if re.search(pattern, msg_lower):
                metrics.feature_completed = True
                break

    # Get list of modified files (for learnings detection)
    name_output = run_git("diff", "--name-only", f"{since}^..HEAD")
    if name_output is None:
        name_output = run_git("diff", "--name-only", f"{since}..HEAD")
    if name_output:
        metrics.modified_files = [
            f for f in name_output.split("\n") if f.strip()
        ]

    return metrics


def parse_shortstat(stat: str) -> tuple:
    """Parse git shortstat output into (files_changed, insertions, deletions)."""
    files = 0
    added = 0
    removed = 0

    m = re.search(r"(\d+)\s+file", stat)
    if m:
        files = int(m.group(1))

    m = re.search(r"(\d+)\s+insertion", stat)
    if m:
        added = int(m.group(1))

    m = re.search(r"(\d+)\s+deletion", stat)
    if m:
        removed = int(m.group(1))

    return files, added, removed


def parse_hour_from_iso(iso_str: str) -> Optional[int]:
    """Extract the local hour from an ISO timestamp string."""
    try:
        # Handle various ISO formats
        dt = datetime.fromisoformat(iso_str)
        return dt.hour
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════
# Todo parsing
# ══════════════════════════════════════════════════════════════

_TASK_DONE_RE = re.compile(
    r"^[\s]*(?:\d+\.\s*)?\[x\]\s*(.+)",
    re.IGNORECASE,
)
_TIMESTAMP_RE = re.compile(
    r"\*\(completed\s+(?:\d{2}:\d{2}\s+)?(\d{2}/\d{2}/\d{2})\)\*"
)


def count_steps_completed_today(todo_path: Path) -> int:
    """Count [x] items in todo.md with timestamps matching today's date."""
    if not todo_path.exists():
        return 0

    today = datetime.now()
    today_str = today.strftime("%d/%m/%y")  # DD/MM/YY

    text = todo_path.read_text(encoding="utf-8")
    count = 0

    for line in text.split("\n"):
        m = _TASK_DONE_RE.match(line)
        if not m:
            continue
        task_text = m.group(1)
        ts_m = _TIMESTAMP_RE.search(task_text)
        if ts_m and ts_m.group(1) == today_str:
            count += 1

    return count


def check_feature_completed_in_todo(todo_path: Path) -> bool:
    """Check if any feature in todo.md has all steps marked [x]."""
    if not todo_path.exists():
        return False

    text = todo_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find feature blocks: ### heading followed by numbered steps
    in_feature = False
    has_steps = False
    all_done = True

    for line in lines:
        # New feature heading
        if re.match(r"^###\s+", line):
            # Check if previous feature was fully complete
            if in_feature and has_steps and all_done:
                return True
            in_feature = True
            has_steps = False
            all_done = True
            continue

        # Section heading breaks feature block
        if re.match(r"^##\s+", line):
            if in_feature and has_steps and all_done:
                return True
            in_feature = False
            continue

        if in_feature:
            # Numbered step
            step_m = re.match(r"^\s*\d+\.\s+\[([ x])\]", line, re.IGNORECASE)
            if step_m:
                has_steps = True
                if step_m.group(1).lower() != "x":
                    all_done = False

    # Check last feature block
    if in_feature and has_steps and all_done:
        return True

    return False


def check_first_step_today(todo_path: Path) -> bool:
    """Check if step 1 of any feature was completed today (FIRST BLOOD badge)."""
    if not todo_path.exists():
        return False

    today = datetime.now()
    today_str = today.strftime("%d/%m/%y")

    text = todo_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    for line in lines:
        # Look for step 1 completed today
        m = re.match(r"^\s*1\.\s+\[x\]\s*(.+)", line, re.IGNORECASE)
        if m:
            task_text = m.group(1)
            ts_m = _TIMESTAMP_RE.search(task_text)
            if ts_m and ts_m.group(1) == today_str:
                return True

    return False


# ══════════════════════════════════════════════════════════════
# Streak computation
# ══════════════════════════════════════════════════════════════

def compute_streak(stats: dict) -> int:
    """Compute the current streak value based on lastSessionDate."""
    streak_data = stats.get("streak", {})
    last_date_str = streak_data.get("lastSessionDate")
    current = streak_data.get("current", 0)

    today = datetime.now().date()

    if last_date_str is None:
        return 1

    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 1

    delta = (today - last_date).days

    if delta == 0:
        # Same day — don't double-count
        return current
    elif delta == 1:
        # Consecutive day
        return current + 1
    else:
        # Gap of 2+ days
        return 1


# ══════════════════════════════════════════════════════════════
# Multiplier computation (linear interpolation)
# ══════════════════════════════════════════════════════════════

# Milestone table: (days, multiplier)
_MILESTONES = [
    (1, 1.0),
    (2, 1.1),
    (3, 1.2),
    (4, 1.3),
    (5, 1.5),
    (7, 1.75),
    (10, 2.0),
    (14, 2.5),
    (21, 3.0),
]


def compute_multiplier(streak: int) -> float:
    """Compute streak multiplier via linear interpolation between milestones."""
    if streak <= 0:
        return 1.0
    if streak >= 21:
        return 3.0

    # Find the two milestones to interpolate between
    for i in range(len(_MILESTONES) - 1):
        day_lo, mult_lo = _MILESTONES[i]
        day_hi, mult_hi = _MILESTONES[i + 1]

        if day_lo <= streak <= day_hi:
            if day_lo == day_hi:
                return mult_lo
            # Linear interpolation
            t = (streak - day_lo) / (day_hi - day_lo)
            return mult_lo + t * (mult_hi - mult_lo)

    return 3.0


# ══════════════════════════════════════════════════════════════
# Score computation
# ══════════════════════════════════════════════════════════════

def compute_raw_score(metrics: SessionMetrics) -> int:
    """Compute the raw (pre-multiplier) session score."""
    g = metrics.git
    score = (
        (g.commits * 10)
        + (math.floor(g.lines_added / 100) * 15)
        + (math.floor(g.lines_removed / 100) * 10)
        + (g.files_touched * 5)
        + (metrics.steps_completed * 25)
        + (metrics.learnings_logged * 20)
        + (metrics.recoveries * 15)
        + (50 if g.feature_completed else 0)
    )
    return score


def compute_final_score(raw: int, multiplier: float) -> int:
    """Apply multiplier and floor."""
    return math.floor(raw * multiplier)


# ══════════════════════════════════════════════════════════════
# Badge evaluation
# ══════════════════════════════════════════════════════════════

def evaluate_badges(
    metrics: SessionMetrics,
    streak: int,
    final_score: int,
    stats: dict,
    first_step_today: bool,
) -> list:
    """Evaluate all badge conditions and return list of earned badge names."""
    g = metrics.git
    lifetime = stats.get("lifetime", {})
    high_scores = stats.get("highScores", {})
    recent = stats.get("recentSessions", [])

    # Collect badges already earned today (once-per-day rule)
    today_str = datetime.now().strftime("%Y-%m-%d")
    badges_earned_today = set()
    for session in recent:
        if session.get("date") == today_str:
            for b in session.get("badgesEarned", []):
                badges_earned_today.add(b)

    # All badge conditions: (name, condition)
    candidates = []

    if g.lines_added >= 500:
        candidates.append("BRICKLAYER")
    if g.lines_added >= 1000:
        candidates.append("NOVELIST")
    if g.commits >= 15:
        candidates.append("MACHINE GUN")
    if g.files_touched >= 8:
        candidates.append("OCTOPUS")
    if g.lines_added + g.lines_removed < 20:
        candidates.append("SURGICAL")
    if g.commits == 1 and g.files_touched == 1:
        candidates.append("SNIPER")
    if g.lines_removed > g.lines_added:
        candidates.append("DEMOLITION")
    if metrics.steps_completed >= 3:
        candidates.append("SPEEDRUN")
    if g.feature_completed:
        candidates.append("CLOSER")
    if first_step_today:
        candidates.append("FIRST BLOOD")
    if metrics.failures >= 1 and metrics.recoveries >= metrics.failures:
        candidates.append("PHOENIX")
    if metrics.learnings_logged >= 3:
        candidates.append("SCHOLAR")
    if streak >= 3:
        candidates.append("STREAK\u00d73")
    if streak >= 7:
        candidates.append("STREAK\u00d77")
    if lifetime.get("totalSessions", 0) + 1 >= 10:
        candidates.append("CENTURION")
    if final_score > high_scores.get("bestSessionScore", 0):
        candidates.append("HIGH ROLLER")
    if g.night_owl:
        candidates.append("NIGHT OWL")
    if g.early_bird:
        candidates.append("EARLY BIRD")

    # Marathon: session duration >= 4 hours based on commit timestamps
    if g.first_commit_time and g.last_commit_time:
        try:
            first_dt = datetime.fromisoformat(g.first_commit_time)
            last_dt = datetime.fromisoformat(g.last_commit_time)
            duration_hours = (last_dt - first_dt).total_seconds() / 3600
            if duration_hours >= 4:
                candidates.append("MARATHON")
        except (ValueError, TypeError):
            pass

    if metrics.failures == 0 and g.commits >= 5:
        candidates.append("ZERO DEFECT")

    # Apply once-per-day rule
    awarded = []
    for badge in candidates:
        if badge not in badges_earned_today:
            awarded.append(badge)

    return awarded


# ══════════════════════════════════════════════════════════════
# Mood determination
# ══════════════════════════════════════════════════════════════

def determine_mood(metrics: SessionMetrics) -> str:
    """Determine session mood based on metrics."""
    g = metrics.git

    # Check config/docs ratio for housekeeping detection
    doc_extensions = {".md", ".json", ".yml", ".yaml"}
    if g.modified_files:
        doc_count = sum(
            1 for f in g.modified_files
            if Path(f).suffix.lower() in doc_extensions
        )
        doc_ratio = doc_count / len(g.modified_files) if g.modified_files else 0
        if doc_ratio > 0.5:
            return "housekeeping"

    # Check order matters — more specific first
    if metrics.failures == 1 and metrics.recoveries == 1 and g.commits <= 3:
        return "quick_patch"

    if g.lines_added >= 1000:
        return "factory_floor"

    if metrics.failures > 0 and metrics.recoveries >= metrics.failures:
        return "hard_fought"

    if metrics.failures > 0:
        return "got_there"

    if metrics.failures == 0 and g.commits >= 5:
        return "smooth_sailing"

    if metrics.failures == 0 and g.commits < 5:
        return "clean_quiet"

    return "clean_quiet"


# ══════════════════════════════════════════════════════════════
# Genre determination
# ══════════════════════════════════════════════════════════════

def determine_genre(metrics: SessionMetrics) -> str:
    """Determine session genre (first match wins)."""
    g = metrics.git

    # 1. star_wars — big session
    if g.feature_completed or g.lines_added >= 500 or g.commits >= 10:
        return "star_wars"

    # 2. noir — lots of failures, many recovered
    if metrics.failures >= 3 and metrics.recoveries >= 2:
        return "noir"

    # 3. heist — clean multi-step
    if metrics.steps_completed >= 3 and metrics.failures == 0:
        return "heist"

    # 4. fantasy — heavy code output
    if g.lines_added >= 800:
        return "fantasy"

    # 5. haiku — minimal changes
    if g.lines_added + g.lines_removed < 20:
        return "haiku"

    # 6. horror — net deletion
    if g.lines_removed > g.lines_added:
        return "horror"

    # 7. short_film — single commit
    if g.commits == 1:
        return "short_film"

    # 8. war — many files
    if g.files_touched >= 8:
        return "war"

    # 9. sports — at least one failure recovered
    if metrics.failures >= 1 and metrics.recoveries >= 1:
        return "sports"

    # 10. action — default
    return "action"


# ══════════════════════════════════════════════════════════════
# Session duration
# ══════════════════════════════════════════════════════════════

def compute_session_duration(session_start: str) -> str:
    """Compute duration from session start to now, formatted as 'Xh Ym'."""
    try:
        start = datetime.fromisoformat(session_start)
        now = datetime.now(timezone.utc)

        # Make both offset-aware for comparison
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        delta = now - start
        total_minutes = max(0, int(delta.total_seconds() / 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "0m"


# ══════════════════════════════════════════════════════════════
# High score check
# ══════════════════════════════════════════════════════════════

def check_high_score(final_score: int, stats: dict) -> tuple:
    """Check if this is a new high score. Returns (is_high_score, previous_best_dict)."""
    high_scores = stats.get("highScores", {})
    best = high_scores.get("bestSessionScore", 0)

    previous_best = None
    if best > 0:
        previous_best = {
            "score": best,
            "date": high_scores.get("bestSessionDate"),
            "title": high_scores.get("bestSessionTitle"),
        }

    return final_score > best, previous_best


# ══════════════════════════════════════════════════════════════
# Leaderboard & today's sessions
# ══════════════════════════════════════════════════════════════

def get_today_sessions(stats: dict) -> list:
    """Get all sessions from today's date (before the current session is added)."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = stats.get("recentSessions", [])
    return [s for s in recent if s.get("date") == today_str]


def build_leaderboard(stats: dict, today_score: int) -> list:
    """Build a 10-entry leaderboard: today + 9 preceding days, consolidated per day."""
    recent = stats.get("recentSessions", [])
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Consolidate sessions by date
    by_date = {}
    for session in recent:
        date = session.get("date", "")
        if date not in by_date:
            by_date[date] = {
                "sessions": [],
                "total_score": 0,
                "best_score": 0,
                "best_title": "",
                "streak": 0,
            }
        entry = by_date[date]
        score = session.get("finalScore", 0)
        entry["sessions"].append(session)
        entry["total_score"] += score
        entry["streak"] = max(entry["streak"], session.get("streak", 0))
        if score > entry["best_score"]:
            entry["best_score"] = score
            entry["best_title"] = session.get("title", "")

    # Add today's score to today's entry
    if today_str not in by_date:
        by_date[today_str] = {
            "sessions": [],
            "total_score": 0,
            "best_score": 0,
            "best_title": "Current session",
            "streak": 0,
        }
    by_date[today_str]["total_score"] += today_score

    # Build 10-day range: today + 9 preceding days
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    leaderboard = []
    for i in range(10):
        day_dt = today_dt - timedelta(days=i)
        day_str = day_dt.strftime("%Y-%m-%d")
        display_date = day_dt.strftime("%d/%m")

        if day_str in by_date:
            entry = by_date[day_str]
            title = entry["best_title"]
            session_count = len(entry["sessions"])
            if day_str == today_str:
                session_count += 1
            if session_count > 1:
                title = f"{title} (+{session_count - 1} more)"

            leaderboard.append({
                "date": display_date,
                "score": entry["total_score"],
                "streak": entry["streak"],
                "title": title,
            })
        else:
            leaderboard.append({
                "date": display_date,
                "score": None,
                "streak": None,
                "title": "--",
            })

    return leaderboard


# ══════════════════════════════════════════════════════════════
# Stats update
# ══════════════════════════════════════════════════════════════

def update_stats(
    stats: dict,
    metrics: SessionMetrics,
    streak: int,
    raw_score: int,
    multiplier: float,
    final_score: int,
    badges: list,
    genre: str,
    mood: str,
    is_high_score: bool,
) -> dict:
    """Update stats.json with this session's data. Returns the updated dict."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    g = metrics.git

    # Lifetime counters
    lt = stats.setdefault("lifetime", {})
    lt["totalSessions"] = lt.get("totalSessions", 0) + 1
    lt["totalCommits"] = lt.get("totalCommits", 0) + g.commits
    lt["totalLinesAdded"] = lt.get("totalLinesAdded", 0) + g.lines_added
    lt["totalLinesRemoved"] = lt.get("totalLinesRemoved", 0) + g.lines_removed
    lt["totalFilesTouched"] = lt.get("totalFilesTouched", 0) + g.files_touched
    lt["totalStepsCompleted"] = lt.get("totalStepsCompleted", 0) + metrics.steps_completed
    lt["totalLearningsLogged"] = lt.get("totalLearningsLogged", 0) + metrics.learnings_logged
    lt["totalBadgesEarned"] = lt.get("totalBadgesEarned", 0) + len(badges)

    if lt.get("firstSessionDate") is None:
        lt["firstSessionDate"] = today_str

    # Streak
    sk = stats.setdefault("streak", {})
    sk["current"] = streak
    sk["best"] = max(sk.get("best", 0), streak)
    sk["lastSessionDate"] = today_str

    # High scores
    if is_high_score:
        hs = stats.setdefault("highScores", {})
        hs["bestSessionScore"] = final_score
        hs["bestSessionDate"] = today_str
        hs["bestSessionTitle"] = None  # Title assigned by wrap prompt, not this script
        hs["bestRawScore"] = raw_score
        hs["bestMultiplier"] = multiplier

    # Badge counters
    all_time = stats.setdefault("badges", {}).setdefault("allTimeEarned", {})
    for badge in badges:
        all_time[badge] = all_time.get(badge, 0) + 1

    # Session record
    session_record = {
        "date": today_str,
        "title": None,  # Title assigned by wrap prompt
        "commits": g.commits,
        "linesAdded": g.lines_added,
        "linesRemoved": g.lines_removed,
        "filesTouched": g.files_touched,
        "stepsCompleted": metrics.steps_completed,
        "rawScore": raw_score,
        "multiplier": multiplier,
        "finalScore": final_score,
        "streak": streak,
        "badgesEarned": badges,
        "genre": genre,
        "mood": mood,
        "sessionDuration": metrics.session_duration,
    }

    recent = stats.setdefault("recentSessions", [])
    recent.insert(0, session_record)
    # Keep max 20
    stats["recentSessions"] = recent[:20]

    return stats


# ══════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Compute session wrap-up scoring, badges, streaks, and stats."
    )
    parser.add_argument(
        "--since", required=True,
        help="First session commit hash (git range: since^..HEAD)",
    )
    parser.add_argument(
        "--session-start", required=True,
        help="Session start time as ISO timestamp",
    )
    parser.add_argument(
        "--todo", default="tasks/todo.md",
        help="Path to todo.md (relative to project root)",
    )
    parser.add_argument(
        "--stats", default=".claude/stats.json",
        help="Path to stats.json (relative to project root)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute everything but don't write stats.json",
    )
    args = parser.parse_args()

    # Resolve paths relative to project root
    todo_path = PROJECT_ROOT / args.todo
    stats_path = PROJECT_ROOT / args.stats

    # ── 1. Gather git metrics ────────────────────────────────
    git_metrics = gather_git_metrics(args.since)

    # ── 2. Count steps completed today ───────────────────────
    steps_completed = count_steps_completed_today(todo_path)

    # Also check feature completion from todo.md
    if not git_metrics.feature_completed:
        git_metrics.feature_completed = check_feature_completed_in_todo(todo_path)

    # Count learnings: check if learnings.md was modified in the range
    learnings_logged = 0
    if "learnings.md" in git_metrics.modified_files:
        learnings_logged = 1  # At minimum, 1 if the file was touched

    # Build session metrics
    session = SessionMetrics(
        git=git_metrics,
        steps_completed=steps_completed,
        learnings_logged=learnings_logged,
        failures=0,
        recoveries=0,
    )

    # ── 3. Read stats.json ───────────────────────────────────
    stats = load_stats(stats_path)

    # ── 4. Compute streak ────────────────────────────────────
    streak = compute_streak(stats)

    # ── 5. Compute multiplier ────────────────────────────────
    multiplier = compute_multiplier(streak)

    # ── 6. Compute score ─────────────────────────────────────
    raw_score = compute_raw_score(session)
    final_score = compute_final_score(raw_score, multiplier)

    # ── 7. Award badges ──────────────────────────────────────
    first_step_today = check_first_step_today(todo_path)
    badges = evaluate_badges(session, streak, final_score, stats, first_step_today)

    # ── 8. Check high score ──────────────────────────────────
    is_high_score, previous_best = check_high_score(final_score, stats)

    # ── 9. Session duration ──────────────────────────────────
    session.session_duration = compute_session_duration(args.session_start)

    # ── 10. Mood ─────────────────────────────────────────────
    mood = determine_mood(session)

    # ── 11. Genre ────────────────────────────────────────────
    genre = determine_genre(session)

    # ── 12. Gather context before updating stats ─────────────
    today_sessions = get_today_sessions(stats)
    leaderboard = build_leaderboard(stats, final_score)

    # ── 13. Update stats.json (unless dry-run) ───────────────
    updated_stats = update_stats(
        stats, session, streak, raw_score, multiplier,
        final_score, badges, genre, mood, is_high_score,
    )

    if not args.dry_run:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(
            json.dumps(updated_stats, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ── 14. Output JSON ──────────────────────────────────────
    output = {
        "metrics": {
            "commits": git_metrics.commits,
            "linesAdded": git_metrics.lines_added,
            "linesRemoved": git_metrics.lines_removed,
            "filesTouched": git_metrics.files_touched,
            "stepsCompleted": steps_completed,
            "learningsLogged": learnings_logged,
            "failures": session.failures,
            "recoveries": session.recoveries,
            "featureCompleted": git_metrics.feature_completed,
            "nightOwl": git_metrics.night_owl,
            "earlyBird": git_metrics.early_bird,
            "sessionDuration": session.session_duration,
            "commitLog": [
                {"time": e.time, "message": e.message}
                for e in git_metrics.commit_log
            ],
        },
        "scoring": {
            "rawScore": raw_score,
            "multiplier": round(multiplier, 2),
            "finalScore": final_score,
            "streak": streak,
            "isHighScore": is_high_score,
            "previousBest": previous_best,
        },
        "badges": badges,
        "genre": genre,
        "mood": mood,
        "todaySessions": today_sessions,
        "leaderboard": leaderboard,
        "stats": updated_stats,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
