#!/usr/bin/env python3
"""Generate a unified HQ dashboard: portfolio overview + per-project drill-down.

Usage:
    python3 ~/.claude/scripts/build_hq.py [--registry PATH] [--output PATH] [--theme light|dark|auto]
"""

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path


def esc(text):
    return html.escape(str(text))


# ── Color Palette ─────────────────────────────────────────────────────────────
PALETTE = [
    ("#4ade80", "#16a34a", "green"),
    ("#67e8f9", "#0891b2", "cyan"),
    ("#fbbf24", "#d97706", "amber"),
    ("#f87171", "#dc2626", "red"),
    ("#6c63ff", "#5046e5", "accent"),
]

def get_project_color(idx):
    return PALETTE[idx] if idx < len(PALETTE) else PALETTE[4]

def format_number(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)

def format_lines(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def format_date_short(d):
    return d.strftime("%-d %b")

def format_dow(d):
    return d.strftime("%a")

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def parse_duration_mins(dur_str):
    if not dur_str:
        return 0
    mins = 0
    h = re.search(r'(\d+)h', dur_str)
    m = re.search(r'(\d+)m', dur_str)
    if h: mins += int(h.group(1)) * 60
    if m: mins += int(m.group(1))
    return mins

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def delta_badge(current, previous):
    diff = current - previous
    if diff == 0:
        return ""
    cls = "up" if diff > 0 else "down"
    sign = "+" if diff > 0 else ""
    val = format_lines(diff) if abs(diff) >= 1000 else str(diff)
    return f'<span class="wsm-delta {cls}">{sign}{val}</span>'


# ── Session Type Detection ────────────────────────────────────────────────────
INFRA_KEYWORDS = ["doe", "infra", "audit", "test", "hook", "starter kit", "governance", "retro", "curation"]
PLANNING_KEYWORDS = ["scoped", "planned", "designed", "wireframe", "discussion", "strategic planning", "explored"]
KNOWN_FEATURES = [
    "Campaign Workbench", "Pulse", "CRM Evolution", "Entity Page Redesign",
    "List Page Redesign", "DOE Testing", "Filter", "Comparison",
    "Scenario Builder", "Swing Model", "Census", "Election History",
    "Supabase", "Bookmarks", "Session Archive", "HQ",
]

def detect_session_type(summary):
    lower = summary.lower() if summary else ""
    for kw in INFRA_KEYWORDS:
        if kw in lower:
            return "INFRA"
    for kw in PLANNING_KEYWORDS:
        if kw in lower:
            return "PLANNING"
    return "APP"

def extract_feature_name(summary):
    if not summary:
        return ""
    for feat in KNOWN_FEATURES:
        if feat.lower() in summary.lower():
            return feat
    ver_match = re.search(r'([A-Z][\w\s&+]+?)\s*\(v\d+\.\d+', summary)
    if ver_match:
        return ver_match.group(1).strip()
    skip = {"built", "added", "fixed", "completed", "updated", "ran", "designed"}
    words = summary.split()
    for i, w in enumerate(words):
        if w.lower() not in skip and len(w) > 0 and w[0].isupper() and i < 10:
            phrase = [w]
            for nw in words[i + 1:i + 4]:
                if len(nw) > 0 and (nw[0].isupper() or nw in ("&", "+", "and", "for", "with")):
                    phrase.append(nw)
                else:
                    break
            return " ".join(phrase)
    return ""

def extract_step_info(summary):
    if not summary:
        return ""
    m = re.search(r'[Ss]teps?\s+(\d+[\-\u2013]\d+/\d+|\d+/\d+)', summary)
    return m.group(0) if m else ""

def extract_version(sessions):
    for s in sessions[:5]:
        match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', s.get("summary", ""))
        if match:
            return f"v{match.group(1)}"
    return None

def extract_feature(sessions):
    if not sessions:
        return None
    summary = sessions[0].get("summary", "")
    for pattern in [
        r'(?:Built|Shipped|Completed|Started|Added|Designed|Created)\s+(.+?)(?:\s*[-\u2014]\s*|\s*\(|\s*v\d|\.\s|$)',
        r'^(.+?)(?:\s*[-\u2014]\s*|\s*:)',
    ]:
        match = re.search(pattern, summary)
        if match:
            feat = match.group(1).strip()
            return feat[:57] + "..." if len(feat) > 60 else feat
    first = summary.split(".")[0] if summary else None
    if first and len(first) > 60:
        first = first[:57] + "..."
    return first


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_projects(registry_path):
    if not os.path.isfile(registry_path):
        return None
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    projects = []
    for entry in registry.get("projects", []):
        path = entry.get("path", "")
        name = entry.get("displayName", entry.get("name", os.path.basename(path)))
        stats_path = os.path.join(path, ".claude", "stats.json")
        stats = None
        if os.path.isfile(stats_path):
            try:
                with open(stats_path, "r", encoding="utf-8") as sf:
                    stats = json.load(sf)
            except (json.JSONDecodeError, IOError):
                pass
        elif not os.path.isdir(path):
            continue
        projects.append({
            "name": name,
            "path": path,
            "slug": slugify(os.path.basename(path)),
            "archivePath": entry.get("archivePath", ""),
            "lastUpdated": entry.get("lastUpdated", ""),
            "stats": stats,
        })
    return projects


# ── Global Computation ────────────────────────────────────────────────────────

def compute_global_stats(projects):
    total_sessions = total_commits = total_added = total_removed = active_projects = 0
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    for p in projects:
        s = p.get("stats")
        if not s: continue
        lt = s.get("lifetime", {})
        total_sessions += lt.get("totalSessions", 0)
        total_commits += lt.get("totalCommits", 0)
        total_added += lt.get("totalLinesAdded", 0)
        total_removed += lt.get("totalLinesRemoved", 0)
        for sess in s.get("recentSessions", []):
            d = sess.get("date", "")
            if d:
                try:
                    if parse_date(d) >= week_ago:
                        active_projects += 1
                        break
                except ValueError:
                    pass
    return {"totalSessions": total_sessions, "totalCommits": total_commits,
            "totalLinesAdded": total_added, "netCode": total_added - total_removed,
            "activeProjects": active_projects}

def compute_all_day_sessions(projects):
    day_map = {}
    earliest = latest = None
    for idx, p in enumerate(projects):
        s = p.get("stats")
        if not s: continue
        for sess in s.get("recentSessions", []):
            d = sess.get("date", "")
            if not d: continue
            try:
                sd = parse_date(d)
            except ValueError:
                continue
            if earliest is None or sd < earliest: earliest = sd
            if latest is None or sd > latest: latest = sd
            day_map.setdefault(d, []).append({"project_name": p["name"], "project_idx": idx, "session": sess})
        fsd = s.get("lifetime", {}).get("firstSessionDate", "")
        if fsd:
            try:
                fd = parse_date(fsd)
                if earliest is None or fd < earliest: earliest = fd
            except ValueError:
                pass
    return day_map, earliest, latest

def compute_weeks_global(day_map, earliest, latest):
    if not earliest or not latest:
        return []
    weeks = []
    ws = get_week_start(earliest)
    while ws <= latest:
        week = {"start": ws, "end": ws + timedelta(days=6), "days": []}
        for i in range(7):
            d = ws + timedelta(days=i)
            week["days"].append({"date": d, "sessions": day_map.get(d.strftime("%Y-%m-%d"), [])})
        weeks.append(week)
        ws += timedelta(days=7)
    return weeks

def compute_week_stats_global(week, prev_week=None):
    ts = tc = tl = tr = 0
    active = set()
    for day in week["days"]:
        for e in day["sessions"]:
            ts += 1; tc += e["session"].get("commits", 0); tl += e["session"].get("linesAdded", 0)
            tr += e["session"].get("linesRemoved", 0)
            active.add(e["project_name"])
    ds = dc = dl = None
    if prev_week:
        ps = sum(len(d["sessions"]) for d in prev_week["days"])
        pc = sum(e["session"].get("commits", 0) for d in prev_week["days"] for e in d["sessions"])
        pl = sum(e["session"].get("linesAdded", 0) for d in prev_week["days"] for e in d["sessions"])
        ds, dc, dl = ts - ps, tc - pc, tl - pl
    most_active = None; max_c = 0; proj_counts = {}
    for day in week["days"]:
        for e in day["sessions"]:
            proj_counts[e["project_name"]] = proj_counts.get(e["project_name"], 0) + 1
    for pn, c in proj_counts.items():
        if c > max_c: max_c = c; most_active = pn
    bd = None; bds = 0; bdp = set()
    for day in week["days"]:
        if len(day["sessions"]) > bds:
            bds = len(day["sessions"]); bd = day["date"]; bdp = set(e["project_name"] for e in day["sessions"])
    return {"total_sessions": ts, "total_commits": tc, "total_lines_added": tl,
            "total_lines_removed": tr, "active_projects": sorted(active),
            "delta_sessions": ds, "delta_commits": dc,
            "delta_lines": dl, "most_active": most_active, "most_active_count": max_c,
            "biggest_day": bd, "biggest_day_sessions": bds, "biggest_day_projects": bdp}

def compute_project_status(project, today):
    s = project.get("stats")
    if not s: return "dormant", "No data"
    last_str = s.get("streak", {}).get("lastSessionDate", "")
    if not last_str:
        recent = s.get("recentSessions", [])
        if recent: last_str = recent[0].get("date", "")
    if not last_str: return "dormant", "No sessions"
    try:
        last = parse_date(last_str)
    except ValueError:
        return "dormant", "Unknown"
    days_ago = (today - last).days
    if days_ago <= 3: return "active", "last active today" if days_ago == 0 else f"last active {days_ago}d ago"
    if days_ago <= 14: return "idle", f"last active {days_ago}d ago"
    return "dormant", f"last active {days_ago}d ago"

def count_active_days(sessions):
    return len(set(s.get("date", "") for s in sessions if s.get("date")))


# ── Project-Level Computation ─────────────────────────────────────────────────

def group_sessions_by_date(sessions, total_sessions):
    by_date = {}
    for s in sessions:
        by_date.setdefault(s.get("date", ""), []).append(s)
    num = total_sessions
    result = []
    for date in sorted(by_date.keys(), reverse=True):
        for s in by_date[date]:
            s["_number"] = num; s["_type"] = detect_session_type(s.get("summary", ""))
            s["_feature"] = extract_feature_name(s.get("summary", ""))
            s["_step_info"] = extract_step_info(s.get("summary", ""))
            s["_duration_mins"] = parse_duration_mins(s.get("sessionDuration", ""))
            num -= 1
        result.append((date, by_date[date]))
    return result

def all_weeks_project(first_date_str, last_date_str):
    first_mon = get_week_start(parse_date(first_date_str))
    last_mon = get_week_start(parse_date(last_date_str))
    weeks = []
    mon = first_mon
    while mon <= last_mon:
        weeks.append((mon, mon + timedelta(days=6)))
        mon += timedelta(days=7)
    weeks.reverse()
    return weeks

def sessions_in_week(grouped, monday, sunday):
    result = []
    for date_str, sessions in grouped:
        d = parse_date(date_str)
        if monday <= d <= sunday: result.extend(sessions)
    return result

def days_in_week(grouped, monday, sunday):
    result = {}
    for date_str, sessions in grouped:
        d = parse_date(date_str)
        if monday <= d <= sunday: result[date_str] = sessions
    return result

def compute_week_stats_project(week_sessions):
    return {"sessions": len(week_sessions),
            "commits": sum(s.get("commits", 0) for s in week_sessions),
            "added": sum(s.get("linesAdded", 0) for s in week_sessions),
            "removed": sum(s.get("linesRemoved", 0) for s in week_sessions),
            "steps": sum(s.get("stepsCompleted", 0) for s in week_sessions),
            "files": sum(s.get("filesTouched", 0) for s in week_sessions)}

def generate_week_narrative(week_sessions, ws):
    if not week_sessions: return "No sessions this week."
    feats = set(s.get("_feature", "") for s in week_sessions if s.get("_feature"))
    feat_str = ", ".join(sorted(feats)[:5]) if feats else "general work"
    parts = [f"{ws['sessions']} sessions across {feat_str}."]
    if ws["steps"] > 0: parts.append(f"{ws['steps']} steps completed.")
    parts.append(f"{ws['commits']} commits, +{format_lines(ws['added'])} lines.")
    return " ".join(parts)

def compute_best_of(week_sessions, days_dict):
    best = {}
    if days_dict:
        biggest_date = max(days_dict, key=lambda d: len(days_dict[d]))
        bd = parse_date(biggest_date)
        day_added = sum(s.get("linesAdded", 0) for s in days_dict[biggest_date])
        best["biggest_day"] = f"{bd.strftime('%a %-d %b')} -- {len(days_dict[biggest_date])} sessions, +{format_lines(day_added)} lines"
    if week_sessions:
        longest = max(week_sessions, key=lambda s: s.get("_duration_mins", 0))
        if longest.get("_duration_mins", 0) > 0:
            feat = f" ({longest.get('_feature', '')})" if longest.get("_feature") else ""
            best["longest_session"] = f"#{longest['_number']} -- {longest.get('sessionDuration', '')}{feat}"
        most = max(week_sessions, key=lambda s: s.get("stepsCompleted", 0))
        if most.get("stepsCompleted", 0) > 0:
            feat = f" ({most.get('_feature', '')})" if most.get("_feature") else ""
            best["most_steps"] = f"#{most['_number']} -- {most['stepsCompleted']} steps{feat}"
    return best

def compute_swimlane(days_dict, monday):
    features = {}
    for date_str, sessions in sorted(days_dict.items()):
        day_idx = (parse_date(date_str) - monday).days
        for s in sessions:
            feat = s.get("_feature", "")
            if not feat: continue
            stype = s.get("_type", "APP")
            lower = (s.get("summary", "") or "").lower()
            if any(w in lower for w in ("shipped", "completed", "done")): bar = "shipped"
            elif stype == "PLANNING": bar = "planning"
            elif stype == "INFRA": bar = "infra"
            else: bar = "app"
            features.setdefault(feat, {})
            priority = {"shipped": 4, "app": 3, "infra": 2, "planning": 1}
            if priority.get(bar, 0) > priority.get(features[feat].get(day_idx, ""), 0):
                features[feat][day_idx] = bar
    return [{"name": n, "days": [dm.get(i, "") for i in range(7)]} for n, dm in features.items()]

def compute_scrubber_data(grouped, first_date_str, today_str):
    first = parse_date(first_date_str); today = parse_date(today_str)
    total_days = max((today - first).days, 1)
    date_counts = {ds: len(ss) for ds, ss in grouped}
    max_count = max(date_counts.values()) if date_counts else 1
    bars = []
    for ds, count in sorted(date_counts.items()):
        d = parse_date(ds)
        bars.append({"date": ds, "offset_pct": round(((d - first).days / total_days) * 100, 1),
                      "height_pct": round((count / max_count) * 100), "count": count,
                      "label": format_date_short(d)})
    return bars, total_days

def extract_version_milestones(grouped):
    milestones = {}
    for date_str, sessions in grouped:
        for s in sessions:
            summary = s.get("summary", "") or ""
            for m in re.finditer(r'\(v(\d+\.\d+)(?:\.\d+)?\)', summary):
                ver = m.group(1)
                prefix = summary[:m.start()].strip()
                feat_name = ""
                for feat in KNOWN_FEATURES:
                    if feat.lower() in prefix.lower(): feat_name = feat; break
                if ver not in milestones or feat_name: milestones[ver] = feat_name
    sorted_vers = sorted(milestones.keys(), key=lambda v: [int(x) for x in v.split(".")])
    return [(v, milestones[v]) for v in sorted_vers]

def check_wrap_exists(session_num, project_root):
    permanent = Path(project_root) / "docs" / "wraps" / f"session-{session_num}.html"
    if permanent.exists():
        return permanent
    # Fallback: check .tmp/wrap.html for current session
    tmp = Path(project_root) / ".tmp" / "wrap.html"
    if tmp.exists():
        return tmp
    return permanent  # return the expected path (won't exist, but keeps the logic working)


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = r"""  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg: #0a0a0f; --surface: #12121a; --surface2: #1a1a26; --border: #2a2a3a;
    --text: #e0e0e8; --text-dim: #8888a0; --accent: #6c63ff;
    --accent-glow: rgba(108, 99, 255, 0.15);
    --green: #4ade80; --green-dim: rgba(74, 222, 128, 0.1);
    --amber: #fbbf24; --amber-dim: rgba(251, 191, 36, 0.1);
    --red: #f87171; --cyan: #67e8f9;
  }
  body.light {
    --bg: #f0efe9; --surface: #f8f7f3; --surface2: #eae9e3; --border: #d5d4cc;
    --text: #1a1a2e; --text-dim: #6b6b80; --accent: #5046e5;
    --accent-glow: rgba(80, 70, 229, 0.08);
    --green: #16a34a; --green-dim: rgba(22, 163, 74, 0.08);
    --amber: #d97706; --amber-dim: rgba(217, 119, 6, 0.08);
    --red: #dc2626; --cyan: #0891b2;
  }

  body { background: var(--bg); color: var(--text); font-family: 'Inter', -apple-system, sans-serif; line-height: 1.6; min-height: 100vh; padding: 2rem; }
  .container { max-width: 900px; margin: 0 auto; }
  .view-container { display: none; }
  .view-container.active { display: block; }

  /* ── Header ── */
  .page-header { text-align: center; padding: 2.5rem 2rem 2rem; border: 1px solid var(--border); border-radius: 12px; background: linear-gradient(135deg, var(--surface) 0%, var(--bg) 100%); position: relative; overflow: hidden; margin-bottom: 2rem; }
  .page-header::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(ellipse at center, var(--accent-glow) 0%, transparent 70%); pointer-events: none; }
  .page-title { font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700; letter-spacing: 0.3em; text-transform: uppercase; color: var(--text); position: relative; margin-bottom: 0.3rem; }
  .page-subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--accent); letter-spacing: 0.1em; position: relative; }

  /* ── Back Nav ── */
  .back-nav { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
  .back-nav a { color: var(--accent); text-decoration: none; cursor: pointer; }
  .back-nav a:hover { text-decoration: underline; }
  .back-nav .sep { color: var(--text-dim); }
  .back-nav .current { color: var(--text); font-weight: 600; }

  /* ── Lifetime Stats ── */
  .lifetime-bar { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 2rem; }
  .lifetime-stat { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 0.8rem; text-align: center; }
  .lifetime-value { font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 700; color: var(--text); }
  .lifetime-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-top: 0.15rem; }

  /* ── Allocation Bar ── */
  .allocation-section { margin-bottom: 2rem; }
  .allocation-section-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.6rem; }
  .allocation-bar-container { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.2rem; }
  .allocation-bar { display: flex; height: 24px; border-radius: 6px; overflow: hidden; margin-bottom: 0.8rem; }
  .allocation-segment { height: 100%; transition: opacity 0.15s; cursor: default; }
  .allocation-segment:hover { opacity: 0.85; }
  .allocation-segment:first-child { border-radius: 6px 0 0 6px; }
  .allocation-segment:last-child { border-radius: 0 6px 6px 0; }
  .allocation-labels { display: flex; gap: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); }
  .alloc-label { display: flex; align-items: center; gap: 0.4rem; }
  .alloc-dot { width: 8px; height: 8px; border-radius: 2px; }
  .alloc-name { color: var(--text); font-weight: 500; }

  /* ── Week Navigation ── */
  .week-section { margin-bottom: 2rem; }
  .week-nav { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .week-label { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 600; color: var(--text); letter-spacing: 0.05em; }
  .week-label-sub { font-size: 0.75rem; font-weight: 400; color: var(--text-dim); margin-left: 0.6rem; }
  .week-arrows { display: flex; gap: 0.4rem; }
  .week-arrow { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--text-dim); cursor: pointer; font-size: 0.8rem; transition: all 0.15s; }
  .week-arrow:hover { border-color: var(--accent); color: var(--text); }
  .week-arrow.disabled { opacity: 0.3; pointer-events: none; }

  /* ── Week Summary ── */
  .week-summary { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }
  .week-summary-title { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); margin-bottom: 0.6rem; }
  .week-summary-text { font-size: 0.9rem; color: var(--text); line-height: 1.6; margin-bottom: 0.8rem; }
  .week-summary-metrics { display: flex; gap: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-dim); padding-top: 0.6rem; border-top: 1px solid var(--border); flex-wrap: wrap; }
  .week-summary-metrics .wsm-val { color: var(--text); font-weight: 600; }
  .week-summary-metrics .wsm-green { color: var(--green); }
  .wsm-delta { font-size: 0.65rem; font-weight: 600; padding: 0 0.3rem; border-radius: 3px; margin-left: 0.2rem; }
  .wsm-delta.up { color: var(--green); background: var(--green-dim); }
  .wsm-delta.down { color: var(--red); background: rgba(248, 113, 113, 0.1); }
  .week-best-of { display: flex; gap: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed var(--border); flex-wrap: wrap; }
  .best-item { display: flex; align-items: center; gap: 0.3rem; }
  .best-label { color: var(--amber); font-weight: 600; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .best-val { color: var(--text); }
  .week-comparison { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); margin-top: 0.3rem; }

  /* ── Day Strip ── */
  .week-strip { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 1rem; align-items: stretch; }
  .week-day { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px; display: flex; flex-direction: column; min-height: 160px; min-width: 0; overflow: hidden; cursor: default; transition: all 0.15s; position: relative; }
  .portfolio-view .week-day.has-sessions { cursor: default; }
  .project-view .week-day.has-sessions { cursor: pointer; }
  .project-view .week-day.has-sessions:hover { border-color: var(--accent); background: var(--surface2); }
  .week-day.today { border-color: var(--accent); }
  .week-day.selected { border-color: var(--accent); background: var(--accent-glow); box-shadow: 0 0 12px rgba(108, 99, 255, 0.15); }
  .week-day.rest-day { opacity: 0.4; }
  .wd-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .wd-dow { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); }
  .week-day.has-sessions .wd-dow { color: var(--text); }
  .wd-date { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--text-dim); }
  .week-day.today .wd-date { color: var(--accent); font-weight: 600; }
  .wd-badge { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--accent); background: var(--accent-glow); padding: 1px 5px; border-radius: 3px; margin-bottom: 6px; display: inline-block; align-self: flex-start; }
  .wd-metrics { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--text-dim); display: flex; gap: 6px; margin-bottom: 6px; }
  .wd-metrics .wdm-c { color: var(--text); }
  .wd-metrics .wdm-a { color: var(--green); }
  .wd-summary { font-size: 0.65rem; color: var(--text-dim); line-height: 1.4; flex: 1; overflow: hidden; }
  .wd-feature { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--accent); margin-top: 4px; }
  .wd-steps { display: flex; gap: 2px; margin-top: 4px; }
  .wd-step { width: 8px; height: 4px; border-radius: 2px; background: var(--border); }
  .wd-step.done { background: var(--green); }
  .wd-step.wip { background: var(--amber); }
  .wd-rest { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-dim); margin: auto 0; text-align: center; }

  /* Portfolio day: project dots + mini bar */
  .wd-projects { display: flex; gap: 4px; margin-bottom: 6px; }
  .wd-project-dot { width: 18px; height: 18px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-family: 'JetBrains Mono', monospace; font-size: 0.5rem; font-weight: 700; color: var(--bg); }
  body.light .wd-project-dot { color: #fff; }
  .wd-mini-bar { display: flex; height: 4px; border-radius: 2px; overflow: hidden; margin-top: auto; }
  .wd-mini-segment { height: 100%; }

  /* ── Swimlane ── */
  .swimlane-section { margin-bottom: 2rem; }
  .swimlane-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.6rem; }
  .swimlane { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; position: relative; }
  .sl-dow-row { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 0; margin-bottom: 4px; }
  .sl-dow-spacer { }
  .sl-dow { font-family: 'JetBrains Mono', monospace; font-size: 0.55rem; color: var(--text-dim); text-align: center; text-transform: uppercase; letter-spacing: 0.08em; border-left: 1px solid var(--border); }
  .swimlane-grid { display: grid; grid-template-columns: 140px repeat(7, 1fr); gap: 0; align-items: center; }
  .sl-project-name, .sl-feature-name { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text); font-weight: 500; padding-right: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sl-cell { height: 28px; position: relative; border-left: 1px solid var(--border); }
  .sl-bar { position: absolute; top: 4px; bottom: 4px; left: 4px; border-radius: 3px; opacity: 0.8; }
  .sl-bar.app { background: var(--green); }
  .sl-bar.infra { background: var(--cyan); }
  .sl-bar.planning { background: var(--amber); opacity: 0.5; }
  .sl-bar.shipped { background: var(--green); opacity: 1; }
  .sl-bar.shipped::after { content: '\2713'; position: absolute; right: 4px; top: 50%; transform: translateY(-50%); font-size: 0.55rem; color: var(--bg); font-weight: 700; }

  /* ── Scrubber ── */
  .scrubber-section { margin-bottom: 2rem; padding: 0.8rem 0; }
  .scrubber-track { position: relative; height: 36px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; cursor: pointer; }
  .scrubber-bar { position: absolute; bottom: 0; width: 5px; border-radius: 2px 2px 0 0; opacity: 0.6; background: var(--accent); }
  .scrubber-bar.active { opacity: 1; }
  .scrubber-viewport { position: absolute; top: 0; height: 100%; background: rgba(108, 99, 255, 0.08); border-left: 2px solid var(--accent); border-right: 2px solid var(--accent); cursor: grab; transition: left 0.15s ease; }
  .scrubber-viewport:hover { background: rgba(108, 99, 255, 0.12); }
  .scrubber-labels { display: flex; justify-content: space-between; margin-top: 0.3rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--text-dim); }
  .scrubber-milestone { position: absolute; top: 0; height: 100%; border-left: 1px dashed var(--accent); opacity: 0.4; pointer-events: none; }
  .scrubber-milestone-label { position: absolute; top: 2px; left: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.5rem; color: var(--accent); white-space: nowrap; pointer-events: none; }

  /* ── Section Label ── */
  .section-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 1rem; }

  /* ── Project Cards (Portfolio) ── */
  .project-cards-section { margin-bottom: 2rem; }
  .project-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.6rem; cursor: pointer; transition: all 0.15s; position: relative; overflow: hidden; }
  .project-card:hover { border-color: var(--accent); background: var(--surface2); }
  .project-card .card-chevron { position: absolute; right: 1.2rem; top: 1rem; color: var(--text-dim); font-size: 0.7rem; transition: transform 0.2s, opacity 0.15s; opacity: 0.4; }
  .project-card:hover .card-chevron { opacity: 1; }
  .project-card.expanded .card-chevron { transform: rotate(90deg); opacity: 1; }
  .project-detail { max-height: 0; overflow: hidden; transition: max-height 0.3s ease, padding 0.3s ease; border-top: 0px solid var(--border); margin-top: 0; }
  .project-card.expanded .project-detail { max-height: 500px; border-top: 1px solid var(--border); margin-top: 0.8rem; padding-top: 0.8rem; }
  .recent-activity-label { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: 0.4rem; }
  .recent-session { font-size: 0.8rem; color: var(--text); padding: 0.2rem 0; line-height: 1.5; }
  .recent-session .rs-num { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--accent); font-weight: 600; }
  .recent-session .rs-date { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-dim); margin-left: 0.3rem; }
  .project-top { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .project-name { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--text); }
  .status-badge { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; padding: 0.1rem 0.5rem; border-radius: 3px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
  .status-badge.active { color: var(--green); background: var(--green-dim); }
  .status-badge.idle { color: var(--amber); background: var(--amber-dim); }
  .status-badge.dormant { color: var(--red); background: rgba(248, 113, 113, 0.1); }
  .project-last-active { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); margin-left: auto; padding-right: 2rem; }
  .project-metrics { display: flex; gap: 1.2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); margin-bottom: 0.6rem; flex-wrap: wrap; }
  .pm-val { color: var(--text); font-weight: 500; }
  .pm-green { color: var(--green); }
  .pm-red { color: var(--red); }
  .wsm-red { color: var(--red); }
  .wsm-dim { color: var(--text-dim); font-size: 0.9em; }
  .project-feature-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.4rem; }
  .project-feature-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }
  .project-feature-name { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text); font-weight: 500; }
  .project-version .pv-ver { color: var(--accent); font-weight: 600; }
  .view-project-btn { display: inline-flex; align-items: center; gap: 0.4rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; color: var(--accent); background: var(--accent-glow); border: 1px solid var(--accent); padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; transition: all 0.15s; text-decoration: none; margin-top: 0.6rem; }
  .view-project-btn:hover { background: var(--accent); color: var(--bg); }

  /* ── Controls (Project view) ── */
  .controls { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .search-box { flex: 1; min-width: 200px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem 0.8rem; color: var(--text); font-family: 'Inter', sans-serif; font-size: 0.85rem; outline: none; }
  .search-box:focus { border-color: var(--accent); }
  .search-box::placeholder { color: var(--text-dim); }
  .filter-pills { display: flex; gap: 0.4rem; }
  .pill { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; padding: 0.35rem 0.7rem; border-radius: 4px; border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); cursor: pointer; transition: all 0.15s; }
  .pill:hover { border-color: var(--accent); color: var(--text); }
  .pill.active { background: var(--accent-glow); border-color: var(--accent); color: var(--accent); }

  /* ── Day Groups (Project view) ── */
  .day-group { margin-bottom: 2rem; scroll-margin-top: 70px; }
  .day-header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.8rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; }
  .day-header:hover { opacity: 0.8; }
  .day-date { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 600; color: var(--text); letter-spacing: 0.05em; }
  .day-stats { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); }
  .day-streak { margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--green); background: var(--green-dim); padding: 0.15rem 0.5rem; border-radius: 4px; }
  .day-collapse-icon { font-size: 0.7rem; color: var(--text-dim); transition: transform 0.2s; margin-right: 0.3rem; }
  .day-group.collapsed .day-collapse-icon { transform: rotate(-90deg); }
  .day-group-content { overflow: hidden; transition: max-height 0.3s ease; max-height: 5000px; }
  .day-group.collapsed .day-group-content { max-height: 0; }

  /* ── Session Cards (Project view) ── */
  .session-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.6rem; cursor: pointer; transition: all 0.15s; position: relative; overflow: hidden; }
  .session-card:hover { border-color: var(--accent); background: var(--surface2); }
  .wrap-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); margin-left: 0.3rem; vertical-align: middle; opacity: 0.6; }
  .session-card .card-chevron { position: absolute; right: 1.2rem; top: 1rem; color: var(--text-dim); font-size: 0.7rem; transition: transform 0.2s, opacity 0.15s; opacity: 0.4; }
  .session-card:hover .card-chevron { opacity: 1; }
  .session-card.expanded .card-chevron { transform: rotate(90deg); opacity: 1; }
  .session-detail { max-height: 0; overflow: hidden; transition: max-height 0.3s ease, padding 0.3s ease; border-top: 0px solid var(--border); margin-top: 0; }
  .session-card.expanded .session-detail { max-height: 500px; border-top: 1px solid var(--border); margin-top: 0.8rem; padding-top: 0.8rem; }
  .detail-block-label { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: 0.3rem; }
  .view-wrap-btn { display: inline-flex; align-items: center; gap: 0.4rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; color: var(--accent); background: var(--accent-glow); border: 1px solid var(--accent); padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; transition: all 0.15s; text-decoration: none; margin-top: 0.4rem; }
  .view-wrap-btn:hover { background: var(--accent); color: var(--bg); }
  .no-wrap-note { font-size: 0.7rem; color: var(--text-dim); font-style: italic; margin-top: 0.6rem; }
  .session-top { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.5rem; }
  .session-num { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent); background: var(--accent-glow); padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 600; }
  .session-duration { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); }
  .session-type { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; padding: 0.1rem 0.4rem; border-radius: 3px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
  .session-type.app { color: var(--green); background: var(--green-dim); }
  .session-type.infra { color: var(--cyan); background: rgba(103, 232, 249, 0.1); }
  .session-type.planning { color: var(--amber); background: var(--amber-dim); }
  .session-summary { font-size: 0.85rem; color: var(--text); line-height: 1.5; margin-bottom: 0.6rem; padding-right: 2rem; }
  .session-metrics { display: flex; gap: 1.2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); }
  .metric-val { color: var(--text); font-weight: 500; }
  .metric-added { color: var(--green); }
  .metric-removed { color: var(--red); }
  .session-feature { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); margin-left: auto; padding-right: 1.5rem; }
  .feature-name { color: var(--text); font-weight: 500; }
  .feature-step { color: var(--accent); }

  /* ── Milestones ── */
  .milestones { display: flex; gap: 0.5rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .milestone-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; padding: 0.2rem 0.6rem; border-radius: 4px; border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); }
  .milestone-tag .mt-ver { color: var(--accent); font-weight: 600; }
  .milestone-tag .mt-name { color: var(--text); }

  /* ── Keyboard nav ── */
  .project-card.kb-focus, .session-card.kb-focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }
  .day-group.kb-focus { outline: 2px solid var(--accent); outline-offset: 4px; border-radius: 8px; }
  .week-panel { display: none; }
  .week-panel.active { display: block; }
  .week-panel-lower { display: none; }
  .week-panel-lower.active { display: block; }

  /* ── Theme Toggle ── */
  .theme-toggle { position: fixed; top: 1rem; right: 1rem; width: 36px; height: 36px; border-radius: 50%; background: var(--surface); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; z-index: 200; transition: all 0.2s; }
  .theme-toggle:hover { border-color: var(--accent); color: var(--text); }

  /* ── Keyboard Help ── */
  .kb-help { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 300; align-items: center; justify-content: center; }
  .kb-help.visible { display: flex; }
  .kb-help-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem 2rem; max-width: 400px; width: 90%; }
  .kb-help-title { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 700; color: var(--text); margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.1em; }
  .kb-row { display: flex; justify-content: space-between; padding: 0.3rem 0; font-size: 0.8rem; }
  .kb-key { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--accent); background: var(--accent-glow); padding: 0.1rem 0.5rem; border-radius: 3px; font-weight: 600; }
  .kb-desc { color: var(--text-dim); }

  /* ── Footer ── */
  .archive-footer { border-top: 1px solid var(--border); padding-top: 1.5rem; margin-top: 2rem; text-align: center; font-size: 0.8rem; color: var(--text-dim); }
  .archive-footer strong { color: var(--accent); font-weight: 600; }

  @media (max-width: 700px) {
    .lifetime-bar { grid-template-columns: repeat(3, 1fr); }
    .week-strip { grid-template-columns: repeat(4, 1fr); }
    .allocation-labels { flex-wrap: wrap; }
    .sl-dow-row, .swimlane-grid { grid-template-columns: 100px repeat(7, 1fr); }
    .controls { flex-direction: column; }
    .session-metrics { flex-wrap: wrap; gap: 0.6rem; }
    .project-top { flex-direction: column; align-items: flex-start; gap: 0.4rem; }
    .project-last-active { margin-left: 0; }
  }"""


# ── Portfolio View Renderers ──────────────────────────────────────────────────

def render_portfolio_header(global_stats, num_projects, total_days):
    ps = "project" if num_projects == 1 else "projects"
    return f"""  <div class="page-header">
    <div class="page-title">HQ</div>
    <div class="page-subtitle">{num_projects} {ps} &mdash; {global_stats['totalSessions']} sessions across {total_days} days</div>
  </div>"""

def render_portfolio_lifetime(gs):
    return f"""  <div class="lifetime-bar">
    <div class="lifetime-stat"><div class="lifetime-value">{format_number(gs['totalSessions'])}</div><div class="lifetime-label">Total Sessions</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{format_number(gs['totalCommits'])}</div><div class="lifetime-label">Total Commits</div></div>
    <div class="lifetime-stat"><div class="lifetime-value" style="color: var(--green)">{format_number(gs['totalLinesAdded'])}</div><div class="lifetime-label">Lines Added</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{format_number(gs['netCode'])}</div><div class="lifetime-label">Net Code</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{gs['activeProjects']}</div><div class="lifetime-label">Active Projects</div></div>
  </div>"""

def render_allocation_bar(projects):
    total = sum((p.get("stats") or {}).get("lifetime", {}).get("totalSessions", 0) for p in projects)
    if total == 0: total = 1
    segs = []; labs = []
    for idx, p in enumerate(projects):
        count = (p.get("stats") or {}).get("lifetime", {}).get("totalSessions", 0)
        pct = max(1, round(count / total * 100)) if count > 0 else 0
        _, _, vn = get_project_color(idx)
        segs.append(f'        <div class="allocation-segment" style="width: {pct}%; background: var(--{vn});" title="{esc(p["name"])}: {pct}%"></div>')
        labs.append(f'        <span class="alloc-label"><span class="alloc-dot" style="background: var(--{vn});"></span><span class="alloc-name">{esc(p["name"])}</span> <span>{count} sessions ({pct}%)</span></span>')
    return f"""  <div class="allocation-section">
    <div class="allocation-section-label">Time Allocation</div>
    <div class="allocation-bar-container">
      <div class="allocation-bar">\n{chr(10).join(segs)}\n      </div>
      <div class="allocation-labels">\n{chr(10).join(labs)}\n      </div>
    </div>
  </div>"""

def render_portfolio_week_strip(week, projects, today):
    parts = []
    for day_info in week["days"]:
        d = day_info["date"]; sessions = day_info["sessions"]; is_today = d == today
        if not sessions:
            tc = " today" if is_today else ""
            parts.append(f'      <div class="week-day rest-day{tc}"><div class="wd-header"><span class="wd-dow">{format_dow(d)}</span><span class="wd-date">{format_date_short(d)}</span></div><div class="wd-rest">--</div></div>')
        else:
            tc = " today" if is_today else ""
            n = len(sessions); lines = sum(e["session"].get("linesAdded", 0) for e in sessions)
            seen = {}
            for e in sessions:
                if e["project_idx"] not in seen: seen[e["project_idx"]] = e["project_name"]
            dots = "".join(f'<span class="wd-project-dot" style="background: var(--{get_project_color(pi)[2]});" title="{esc(pn)}">{pn[0].upper()}</span>' for pi, pn in sorted(seen.items()))
            proj_counts = {}
            for e in sessions: proj_counts[e["project_idx"]] = proj_counts.get(e["project_idx"], 0) + 1
            mini = "".join(f'<div class="wd-mini-segment" style="width: {max(1, round(c / n * 100))}%; background: var(--{get_project_color(pi)[2]});"></div>' for pi, c in sorted(proj_counts.items()))
            sl = "session" if n == 1 else "sessions"
            parts.append(f'      <div class="week-day has-sessions{tc}"><div class="wd-header"><span class="wd-dow">{format_dow(d)}</span><span class="wd-date">{format_date_short(d)}</span></div><div class="wd-projects">{dots}</div><div class="wd-badge">{n} {sl}</div><div class="wd-metrics"><span class="wdm-a">+{format_number(lines)}</span></div><div class="wd-mini-bar">{mini}</div></div>')
    return "\n".join(parts)

def render_portfolio_week_summary(ws, week):
    today = datetime.now().date()
    is_current = week["start"] <= today <= week["end"]
    title = "This Week" if is_current else f"Week of {format_date_short(week['start'])}"
    active = ws["active_projects"]
    # Build a richer narrative from session summaries
    all_summaries = []
    for d in week["days"]:
        for e in d["sessions"]:
            s = e["session"].get("summary", "")
            if s: all_summaries.append(s)
    if not active:
        narrative = "No sessions this week."
    else:
        # Extract key activities from summaries
        activities = []
        for s in all_summaries[:6]:
            # Take first clause/sentence, truncate
            short = s.split(".")[0].split(" — ")[0].split(" - ")[0]
            if len(short) > 80: short = short[:77] + "..."
            if short and short not in activities: activities.append(short)
        proj_prefix = f"{', '.join(active)}: " if len(active) > 1 else f"{active[0]}: " if active[0] != "Unknown" else ""
        if activities:
            narrative = proj_prefix + "; ".join(activities[:3]) + "."
        else:
            narrative = f"{'Active across ' + ', '.join(active) if len(active) > 1 else 'Focused on ' + active[0]}. {ws['total_sessions']} sessions, {ws['total_commits']} commits."
    metrics = []
    for label, val, dv in [("sessions", ws["total_sessions"], ws["delta_sessions"]), ("commits", ws["total_commits"], ws["delta_commits"])]:
        s = f'<span class="wsm-val">{val}</span> {label}'
        if dv and dv != 0:
            cls = "up" if dv > 0 else "down"; sign = "+" if dv > 0 else ""
            s += f' <span class="wsm-delta {cls}">{sign}{dv}</span>'
        metrics.append(f"<span>{s}</span>")
    net = ws["total_lines_added"] - ws["total_lines_removed"]
    net_sign = "+" if net >= 0 else ""
    ls = f'<span class="wsm-green">+{format_number(ws["total_lines_added"])}</span> / <span class="wsm-red">-{format_number(ws["total_lines_removed"])}</span> lines <span class="wsm-dim">(net {net_sign}{format_number(net)})</span>'
    metrics.append(f'<span>{ls}</span>')
    best_parts = []
    if ws["most_active"]:
        best_parts.append(f'<span class="best-item"><span class="best-label">Most active</span> <span class="best-val">{esc(ws["most_active"])} ({ws["most_active_count"]})</span></span>')
    if ws["biggest_day"] and ws["biggest_day_sessions"] > 0:
        bd = ws["biggest_day"]; np_ = len(ws["biggest_day_projects"])
        best_parts.append(f'<span class="best-item"><span class="best-label">Biggest day</span> <span class="best-val">{format_dow(bd)} {format_date_short(bd)} &mdash; {ws["biggest_day_sessions"]} sessions</span></span>')
    best_html = f'\n      <div class="week-best-of">{" ".join(best_parts)}</div>' if best_parts else ""
    return f"""      <div class="week-summary-title">{esc(title)}</div>
      <div class="week-summary-text">{narrative}</div>
      <div class="week-summary-metrics">{" ".join(metrics)}</div>{best_html}"""

def render_portfolio_swimlane(week, projects):
    dow_html = "\n".join(f'        <div class="sl-dow">{format_dow(d["date"])}</div>' for d in week["days"])
    max_s = 1
    for d in week["days"]:
        pc = {}
        for e in d["sessions"]: pc[e["project_idx"]] = pc.get(e["project_idx"], 0) + 1
        for c in pc.values():
            if c > max_s: max_s = c
    rows = []
    for idx, p in enumerate(projects):
        _, _, vn = get_project_color(idx)
        cells = []
        for d in week["days"]:
            count = sum(1 for e in d["sessions"] if e["project_idx"] == idx)
            if count == 0:
                cells.append('        <div class="sl-cell"></div>')
            else:
                wp = count / max_s; right = max(4, int((1 - wp) * 80)); op = max(0.5, min(1.0, 0.4 + wp * 0.6))
                cells.append(f'        <div class="sl-cell"><div class="sl-bar" style="background: var(--{vn}); left: 4px; right: {right}%; opacity: {op:.1f};"></div></div>')
        rows.append(f'      <div class="swimlane-grid">\n        <div class="sl-project-name">{esc(p["name"])}</div>\n{chr(10).join(cells)}\n      </div>')
    return f"""      <div class="sl-dow-row">
        <div class="sl-dow-spacer"></div>
{dow_html}
      </div>
{chr(10).join(rows)}"""

def render_portfolio_scrubber(day_map, earliest, latest, projects, weeks, cidx):
    if not earliest or not latest: return ""
    td = (latest - earliest).days + 1
    if td <= 0: return ""
    max_sd = max((len(day_map.get((earliest + timedelta(days=i)).strftime("%Y-%m-%d"), [])) for i in range(td)), default=1) or 1
    bars = []
    for i in range(td):
        d = earliest + timedelta(days=i); ds = d.strftime("%Y-%m-%d"); entries = day_map.get(ds, [])
        if not entries: continue
        lp = (i / td) * 100; hp = max(10, int((len(entries) / max_sd) * 90))
        pc = {}
        for e in entries: pc[e["project_idx"]] = pc.get(e["project_idx"], 0) + 1
        cb = 0
        for pi in sorted(pc.keys()):
            sh = int((pc[pi] / len(entries)) * hp); sh = max(sh, 3)
            _, _, vn = get_project_color(pi)
            bot = f" bottom: {cb}%;" if cb > 0 else ""
            bars.append(f'      <div class="scrubber-bar" style="left: {lp:.1f}%; height: {sh}%;{bot} background: var(--{vn});"></div>')
            cb += sh
    vw = max(5, 100 / max(1, len(weeks))); vl = cidx * vw
    labels = [format_date_short(earliest), format_date_short(earliest + timedelta(days=td // 2)), format_date_short(latest)]
    return f"""  <div class="scrubber-section">
    <div class="scrubber-track" id="p-scrubber-track">
{chr(10).join(bars)}
      <div class="scrubber-viewport" id="p-scrubber-vp" style="left: {vl:.1f}%; width: {vw:.1f}%;"></div>
    </div>
    <div class="scrubber-labels"><span>{esc(labels[0])}</span><span>{esc(labels[1])}</span><span>{esc(labels[2])}</span></div>
  </div>"""

def render_project_card(project, idx, today):
    name = project["name"]; slug = project["slug"]
    s = project.get("stats"); status, last_text = compute_project_status(project, today)
    sessions = (s.get("lifetime", {}).get("totalSessions", 0)) if s else 0
    commits = (s.get("lifetime", {}).get("totalCommits", 0)) if s else 0
    lines_added = (s.get("lifetime", {}).get("totalLinesAdded", 0)) if s else 0
    lines_removed = (s.get("lifetime", {}).get("totalLinesRemoved", 0)) if s else 0
    streak = (s.get("streak", {}).get("current", 0)) if s else 0
    recent = (s.get("recentSessions", [])) if s else []
    active_days = count_active_days(recent)
    feature = extract_feature(recent) if recent else None
    version = extract_version(recent) if recent else None
    feat_html = f'    <div class="project-feature-row"><span class="project-feature-label">Current:</span> <span class="project-feature-name">{esc(feature)}</span></div>' if feature else ""
    ver_html = f'    <div class="project-version"><span class="pv-ver">{esc(version)}</span></div>' if version else ""

    # Recent sessions (last 3) for expandable detail
    recent_parts = []
    for i, sess in enumerate(recent[:3]):
        sess_num = sessions - i
        d = sess.get("date", ""); summary = sess.get("summary", "")
        if summary and len(summary) > 100: summary = summary[:97] + "..."
        try:
            sd = parse_date(d); date_fmt = f"{format_dow(sd)} {format_date_short(sd)}"
        except (ValueError, TypeError):
            date_fmt = d
        recent_parts.append(f'      <div class="recent-session"><span class="rs-num">#{sess_num}</span> <span class="rs-date">{esc(date_fmt)}</span> &mdash; {esc(summary)}</div>')
    recent_html = "\n".join(recent_parts) if recent_parts else '      <div class="recent-session" style="color: var(--text-dim);">No recent session data</div>'

    return f"""    <div class="project-card" onclick="toggleCard(this)">
      <span class="card-chevron">&#9656;</span>
      <div class="project-top">
        <span class="project-name">{esc(name)}</span>
        <span class="status-badge {status}">{status.title()}</span>
        <span class="project-last-active">{esc(last_text)}</span>
      </div>
      <div class="project-metrics">
        <span><span class="pm-val">{sessions}</span> sessions</span>
        <span><span class="pm-val">{commits}</span> commits</span>
        <span class="pm-green">+{format_number(lines_added)}</span> / <span class="pm-red">-{format_number(lines_removed)}</span> lines
        <span><span class="pm-val">{active_days}</span> days active</span>
        <span>Streak: <span class="pm-val">{streak}</span></span>
      </div>
{feat_html}
{ver_html}

      <div class="project-detail">
        <div class="recent-activity-label">Recent Activity</div>
{recent_html}
        <a class="view-project-btn" href="#project/{slug}" onclick="event.stopPropagation(); navigateTo('project/{slug}');">View Sessions &#8594;</a>
      </div>
    </div>"""


# ── Project Drill-Down Renderers ──────────────────────────────────────────────

def render_project_header(project):
    s = project.get("stats") or {}
    lt = s.get("lifetime", {}); streak = s.get("streak", {})
    total = lt.get("totalSessions", 0)
    first = lt.get("firstSessionDate", "")
    day_span = (datetime.now().date() - parse_date(first)).days + 1 if first else 0
    return f"""  <div class="back-nav">
    <a href="#portfolio" onclick="navigateTo('portfolio'); return false;">HQ</a>
    <span class="sep">/</span>
    <span class="current">{esc(project['name'])}</span>
  </div>
  <div class="page-header">
    <div class="page-title">{esc(project['name'])}</div>
    <div class="page-subtitle">{total} sessions across {day_span} days</div>
  </div>"""

def render_project_lifetime(lt, streak):
    ts = lt.get("totalSessions", 0); tc = lt.get("totalCommits", 0)
    added = lt.get("totalLinesAdded", 0); removed = lt.get("totalLinesRemoved", 0)
    net = added - removed; sv = streak.get("current", 0)
    return f"""  <div class="lifetime-bar">
    <div class="lifetime-stat"><div class="lifetime-value">{ts}</div><div class="lifetime-label">Sessions</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{tc}</div><div class="lifetime-label">Commits</div></div>
    <div class="lifetime-stat"><div class="lifetime-value" style="color: var(--green)">{format_lines(added)}</div><div class="lifetime-label">Lines Added</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{format_lines(net)}</div><div class="lifetime-label">Net Code</div></div>
    <div class="lifetime-stat"><div class="lifetime-value">{sv}</div><div class="lifetime-label">Day Streak</div></div>
  </div>"""

def render_project_milestones(milestones):
    if not milestones: return ""
    tags = []
    for ver, name in milestones:
        if name:
            tags.append(f'    <div class="milestone-tag"><span class="mt-ver">v{esc(ver)}</span> <span class="mt-name">{esc(name)}</span></div>')
        else:
            tags.append(f'    <div class="milestone-tag"><span class="mt-ver">v{esc(ver)}</span></div>')
    return f'  <div class="milestones">\n{chr(10).join(tags)}\n  </div>'

def render_project_week_summary(ws, prev_stats, week_sessions, days_dict, week_idx, total_weeks):
    label = "This week" if week_idx == 0 else "Week summary"
    narrative = generate_week_narrative(week_sessions, ws)
    best = compute_best_of(week_sessions, days_dict)
    metrics = []
    if prev_stats:
        metrics.append(f'<span><span class="wsm-val">{ws["sessions"]}</span> sessions {delta_badge(ws["sessions"], prev_stats["sessions"])}</span>')
        metrics.append(f'<span><span class="wsm-val">{ws["commits"]}</span> commits {delta_badge(ws["commits"], prev_stats["commits"])}</span>')
        wnet = ws["added"] - ws["removed"]; wns = "+" if wnet >= 0 else ""
        metrics.append(f'<span><span class="wsm-green">+{format_lines(ws["added"])}</span> / <span class="wsm-red">-{format_lines(ws["removed"])}</span> lines <span class="wsm-dim">(net {wns}{format_lines(wnet)})</span></span>')
        metrics.append(f'<span><span class="wsm-val">{ws["steps"]}</span> steps {delta_badge(ws["steps"], prev_stats["steps"])}</span>')
    else:
        metrics.append(f'<span><span class="wsm-val">{ws["sessions"]}</span> sessions</span>')
        metrics.append(f'<span><span class="wsm-val">{ws["commits"]}</span> commits</span>')
        wnet = ws["added"] - ws["removed"]; wns = "+" if wnet >= 0 else ""
        metrics.append(f'<span><span class="wsm-green">+{format_lines(ws["added"])}</span> / <span class="wsm-red">-{format_lines(ws["removed"])}</span> lines <span class="wsm-dim">(net {wns}{format_lines(wnet)})</span></span>')
        metrics.append(f'<span><span class="wsm-val">{ws["steps"]}</span> steps</span>')
    comparison = ""
    if prev_stats and prev_stats["sessions"] > 0:
        comparison = f'      <div class="week-comparison">vs previous week: {prev_stats["sessions"]} sessions, {prev_stats["commits"]} commits, +{format_lines(prev_stats["added"])} lines</div>'
    best_items = []
    for key, lbl in [("biggest_day", "Biggest day"), ("longest_session", "Longest session"), ("most_steps", "Most steps")]:
        if best.get(key):
            best_items.append(f'<span class="best-item"><span class="best-label">{lbl}</span> <span class="best-val">{esc(best[key])}</span></span>')
    best_html = f'      <div class="week-best-of">{" ".join(best_items)}</div>' if best_items else ""
    return f"""    <div class="week-summary">
      <div class="week-summary-title">{esc(label)}</div>
      <div class="week-summary-text">{esc(narrative)}</div>
      <div class="week-summary-metrics">{chr(10).join("        " + m for m in metrics)}</div>
{comparison}
{best_html}
    </div>"""

def render_project_day_strip(monday, days_dict, today_str, slug=""):
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cells = []
    for i in range(7):
        day = monday + timedelta(days=i); ds = day.strftime("%Y-%m-%d")
        dow = dow_names[i]; dl = format_date_short(day)
        sessions = days_dict.get(ds, []); is_today = ds == today_str
        if not sessions:
            cls = f"week-day rest-day{' today' if is_today else ''}"
            cells.append(f'      <div class="{cls}"><div class="wd-header"><span class="wd-dow">{dow}</span><span class="wd-date">{dl}</span></div><div class="wd-rest">--</div></div>')
        else:
            cls = f"week-day has-sessions{' today' if is_today else ''}"
            n = len(sessions); tc = sum(s.get("commits", 0) for s in sessions); ta = sum(s.get("linesAdded", 0) for s in sessions)
            tr = sum(s.get("linesRemoved", 0) for s in sessions)
            summ = sessions[0].get("summary", "") or ""; summ = summ[:120] + "..." if len(summ) > 120 else summ
            feat = next((s.get("_feature", "") for s in sessions if s.get("_feature")), "")
            ts = sum(s.get("stepsCompleted", 0) for s in sessions)
            step_html = ""
            if ts > 0:
                blocks = '<div class="wd-step done"></div>' * ts + '<div class="wd-step wip"></div>'
                step_html = f'<div class="wd-steps">{blocks}</div>'
            badge = f"{n} session" if n == 1 else f"{n} sessions"
            feat_div = f'<div class="wd-feature">{esc(feat)}</div>' if feat else ""
            cells.append(f'      <div class="{cls}" data-date="{ds}" onclick="scrollToDay_{slug}(\'{ds}\')"><div class="wd-header"><span class="wd-dow">{dow}</span><span class="wd-date">{dl}</span></div><div class="wd-badge">{badge}</div><div class="wd-metrics"><span class="wdm-c">{tc}c</span><span class="wdm-a">+{format_lines(ta)}</span><span style="color:var(--red)">-{format_lines(tr)}</span></div><div class="wd-summary">{esc(summ)}</div>{feat_div}{step_html}</div>')
    return f'    <div class="week-strip">\n{chr(10).join(cells)}\n    </div>'

def render_project_swimlane(swimlane_data, monday):
    if not swimlane_data: return ""
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_cells = ['        <div class="sl-dow-spacer"></div>'] + [f'        <div class="sl-dow">{d}</div>' for d in dow_names]
    rows = []
    for feat in swimlane_data:
        cells = [f'        <div class="sl-feature-name">{esc(feat["name"])}</div>']
        for dv in feat["days"]:
            if dv:
                cells.append(f'        <div class="sl-cell"><div class="sl-bar {dv}" style="left:5%; right:5%;"></div></div>')
            else:
                cells.append('        <div class="sl-cell"></div>')
        rows.append(f'      <div class="swimlane-grid">\n{chr(10).join(cells)}\n      </div>')
    return f"""  <div class="swimlane-section">
    <div class="swimlane-label">Features this week</div>
    <div class="swimlane">
      <div class="sl-dow-row">\n{chr(10).join(dow_cells)}\n      </div>
{chr(10).join(rows)}
    </div>
  </div>"""

def render_session_card(session, project_path):
    num = session["_number"]; stype = session["_type"]; dur = esc(session.get("sessionDuration", ""))
    summary = esc(session.get("summary", "")); commits = session.get("commits", 0)
    added = session.get("linesAdded", 0); removed = session.get("linesRemoved", 0)
    files = session.get("filesTouched", 0); steps = session.get("stepsCompleted", 0)
    feature = session.get("_feature", ""); step_info = session.get("_step_info", "")
    wrap_path = check_wrap_exists(num, project_path)
    has_wrap = wrap_path.exists()
    wrap_dot = '<span class="wrap-dot" title="Wrap page available"></span>' if has_wrap else ""
    feat_html = ""
    if feature or step_info:
        parts = []
        if feature: parts.append(f'<span class="feature-name">{esc(feature)}</span>')
        if step_info: parts.append(f'<span class="feature-step">{esc(step_info)}</span>')
        feat_html = f'        <span class="session-feature">{" ".join(parts)}</span>'
    mi = [f'<span class="metric-item"><span class="metric-val">{commits}</span> commits</span>',
          f'<span class="metric-item"><span class="metric-added">+{added:,}</span></span>',
          f'<span class="metric-item"><span class="metric-removed">-{removed:,}</span></span>',
          f'<span class="metric-item"><span class="metric-val">{files}</span> files</span>']
    if steps > 0:
        mi.append(f'<span class="metric-item"><span class="metric-val">{steps}</span> {"step" if steps == 1 else "steps"}</span>')
    if has_wrap:
        abs_wrap = f"file://{wrap_path}"
        wrap_html = f'      <a class="view-wrap-btn" href="{abs_wrap}" onclick="event.stopPropagation()">View Wrap &#8594;</a>'
    else:
        wrap_html = '      <div class="no-wrap-note">No wrap page saved for this session</div>'
    full_summary = esc(session.get("summary", ""))
    return f"""    <div class="session-card" onclick="toggleCard(this)">
      <span class="card-chevron">&#9654;</span>
      <div class="session-top">
        <span class="session-num">#{num}</span>
        <span class="session-duration">{dur}</span>
        <span class="session-type {stype.lower()}">{esc(stype)}</span>
        {wrap_dot}
{feat_html}
      </div>
      <div class="session-summary">{summary}</div>
      <div class="session-metrics">{chr(10).join("        " + m for m in mi)}</div>
      <div class="session-detail">
        <div class="detail-block-label">Full summary</div>
        <div class="detail-block-content" style="margin-bottom: 0.6rem; font-size: 0.8rem; line-height: 1.6;">{full_summary}</div>
{wrap_html}
      </div>
    </div>"""

def render_day_group(date_str, sessions, collapsed, project_path):
    d = parse_date(date_str); day_label = d.strftime("%A, %-d %B %Y")
    n = len(sessions); tc = sum(s.get("commits", 0) for s in sessions); tl = sum(s.get("linesAdded", 0) for s in sessions)
    tr = sum(s.get("linesRemoved", 0) for s in sessions)
    streak_val = sessions[0].get("streak", 0) if sessions else 0
    cards = "\n".join(render_session_card(s, project_path) for s in sessions)
    streak_html = f'      <span class="day-streak">Streak: {streak_val}</span>' if streak_val > 0 else ""
    cc = " collapsed" if collapsed else ""
    return f"""  <div class="day-group{cc}" id="day-{date_str}">
    <div class="day-header" onclick="toggleDayGroup(this.parentElement)">
      <span class="day-collapse-icon">&#9660;</span>
      <span class="day-date">{esc(day_label)}</span>
      <span class="day-stats">{n} sessions -- {tc} commits -- +{tl:,} / -{tr:,} lines</span>
{streak_html}
    </div>
    <div class="day-group-content">
{cards}
    </div>
  </div>"""

def render_project_scrubber(scrubber_bars, total_days, first_date_str, today_str, current_monday, current_sunday, slug):
    first = parse_date(first_date_str); today = parse_date(today_str)
    vp_left = max(0, ((current_monday - first).days / max(total_days, 1)) * 100)
    vp_right = min(100, ((current_sunday - first).days / max(total_days, 1)) * 100)
    vp_width = vp_right - vp_left
    bars = []
    for bar in scrubber_bars:
        bd = parse_date(bar["date"]); active = " active" if current_monday <= bd <= current_sunday else ""
        bars.append(f'      <div class="scrubber-bar{active}" style="left: {bar["offset_pct"]}%; height: {bar["height_pct"]}%; width: 5px;" title="{bar["label"]} -- {bar["count"]}" data-date="{bar["date"]}"></div>')
    mid = first + timedelta(days=max(total_days, 1) // 2)
    labels = [format_date_short(first), format_date_short(mid), format_date_short(today)]
    return f"""  <div class="scrubber-section">
    <div class="scrubber-track" id="scrubber-{slug}">
{chr(10).join(bars)}
      <div class="scrubber-viewport" style="left: {round(vp_left, 1)}%; width: {round(vp_width, 1)}%;"></div>
    </div>
    <div class="scrubber-labels"><span>{esc(labels[0])}</span><span>{esc(labels[1])}</span><span>{esc(labels[2])}</span></div>
  </div>"""

def render_project_controls():
    return """  <div class="controls">
    <input type="text" class="search-box" id="search-box" placeholder="Search sessions... (summary, commits, features)">
    <div class="filter-pills">
      <span class="pill active" data-filter="all">All</span>
      <span class="pill" data-filter="app">APP</span>
      <span class="pill" data-filter="infra">INFRA</span>
      <span class="pill" data-filter="planning">Planning</span>
    </div>
  </div>"""


# ── JavaScript ────────────────────────────────────────────────────────────────

JS_TEMPLATE = r"""
// ── Router ──
function navigateTo(route) {
  location.hash = '#' + route;
}

function handleRoute() {
  var hash = location.hash.replace(/^#\/?/, '') || 'portfolio';
  document.querySelectorAll('.view-container').forEach(function(v) { v.classList.remove('active'); });
  if (hash.startsWith('project/')) {
    var slug = hash.replace('project/', '');
    var el = document.getElementById('view-' + slug);
    if (el) { el.classList.add('active'); }
    else { document.getElementById('view-portfolio').classList.add('active'); }
  } else {
    document.getElementById('view-portfolio').classList.add('active');
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', handleRoute);
handleRoute();

// ── Theme ──
(function() {
  THEME_INIT
  var btn = document.getElementById('theme-toggle');
  btn.addEventListener('click', function() {
    document.body.classList.toggle('light');
    btn.textContent = document.body.classList.contains('light') ? '\u2600' : '\u263E';
  });
})();

// ── Shared ──
function toggleCard(card) { card.classList.toggle('expanded'); }
function toggleDayGroup(group) { group.classList.toggle('collapsed'); }

// ── Portfolio Week Navigation ──
var pWeekIdx = P_CURRENT_WEEK_IDX;
var pWeekData = P_WEEK_DATA;

function renderPortfolioWeek(idx) {
  if (idx < 0 || idx >= pWeekData.length) return;
  pWeekIdx = idx;
  var w = pWeekData[idx];
  document.getElementById('p-week-label').innerHTML = w.label;
  document.getElementById('p-week-strip').innerHTML = w.stripHtml;
  document.getElementById('p-week-summary').innerHTML = w.summaryHtml;
  document.getElementById('p-swimlane').innerHTML = w.swimlaneHtml;
  var prev = document.getElementById('p-prev-week');
  var next = document.getElementById('p-next-week');
  if (idx <= 0) prev.classList.add('disabled'); else prev.classList.remove('disabled');
  if (idx >= pWeekData.length - 1) next.classList.add('disabled'); else next.classList.remove('disabled');
  var vp = document.getElementById('p-scrubber-vp');
  if (vp) { var pct = 100 / pWeekData.length; vp.style.left = (idx * pct) + '%'; vp.style.width = pct + '%'; }
}

document.getElementById('p-prev-week').addEventListener('click', function() { renderPortfolioWeek(pWeekIdx - 1); });
document.getElementById('p-next-week').addEventListener('click', function() { renderPortfolioWeek(pWeekIdx + 1); });
var pst = document.getElementById('p-scrubber-track');
if (pst) pst.addEventListener('click', function(e) {
  var pct = (e.clientX - this.getBoundingClientRect().left) / this.offsetWidth;
  renderPortfolioWeek(Math.max(0, Math.min(pWeekData.length - 1, Math.floor(pct * pWeekData.length))));
});

// ── Project Week Navigation (per-project) ──
PROJECT_WEEK_JS

// ── Search & Filter ──
document.addEventListener('input', function(e) {
  if (e.target.classList.contains('search-box')) applyFilters(e.target);
});
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('pill')) {
    var parent = e.target.closest('.filter-pills');
    parent.querySelectorAll('.pill').forEach(function(p) { p.classList.remove('active'); });
    e.target.classList.add('active');
    var sb = e.target.closest('.controls').querySelector('.search-box');
    applyFilters(sb);
  }
});
function applyFilters(searchBox) {
  var query = searchBox.value.toLowerCase();
  var controls = searchBox.closest('.controls');
  var activePill = controls.querySelector('.pill.active');
  var filter = activePill ? activePill.getAttribute('data-filter') : 'all';
  var view = searchBox.closest('.view-container');
  view.querySelectorAll('.session-card').forEach(function(card) {
    var summary = card.querySelector('.session-summary');
    var typeEl = card.querySelector('.session-type');
    var text = (summary ? summary.textContent : '').toLowerCase();
    var type = (typeEl ? typeEl.textContent : '').toLowerCase();
    card.style.display = ((!query || text.indexOf(query) !== -1) && (filter === 'all' || type === filter)) ? '' : 'none';
  });
  view.querySelectorAll('.day-group').forEach(function(g) {
    g.style.display = g.querySelectorAll('.session-card:not([style*="display: none"])').length > 0 ? '' : 'none';
  });
}

// ── Keyboard ──
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT') return;
  var help = document.getElementById('kb-help');
  if (e.key === '?') { e.preventDefault(); help.classList.toggle('visible'); return; }
  if (e.key === 'Escape') { help.classList.remove('visible'); return; }
  if (e.key === 't' || e.key === 'T') { if (!help.classList.contains('visible')) document.getElementById('theme-toggle').click(); return; }
  if (e.key === 'ArrowLeft') { e.preventDefault(); var pv = document.getElementById('view-portfolio'); if (pv.classList.contains('active')) renderPortfolioWeek(pWeekIdx - 1); return; }
  if (e.key === 'ArrowRight') { e.preventDefault(); var pv2 = document.getElementById('view-portfolio'); if (pv2.classList.contains('active')) renderPortfolioWeek(pWeekIdx + 1); return; }
  if (e.key === 'b' || e.key === 'B') { navigateTo('portfolio'); return; }
});
"""


# ── Page Assembly ─────────────────────────────────────────────────────────────

def build_portfolio_view(projects, day_map, earliest, latest, weeks, current_week_idx, today):
    global_stats = compute_global_stats(projects)
    total_days = len(set(day_map.keys()))

    # Pre-render week data for JS
    week_data_js = []
    for i, week in enumerate(weeks):
        prev = weeks[i - 1] if i > 0 else None
        ws = compute_week_stats_global(week, prev)
        start_str = format_date_short(week["start"]); end_str = format_date_short(week["end"])
        year = week["end"].strftime("%Y")
        label = f'{start_str} &ndash; {end_str} {year} <span class="week-label-sub">Week {i + 1} of {len(weeks)}</span>'
        week_data_js.append({
            "label": label,
            "stripHtml": render_portfolio_week_strip(week, projects, today),
            "summaryHtml": render_portfolio_week_summary(ws, week),
            "swimlaneHtml": render_portfolio_swimlane(week, projects),
        })

    cw = weeks[current_week_idx] if weeks else None
    pw = weeks[current_week_idx - 1] if current_week_idx > 0 and weeks else None
    cws = compute_week_stats_global(cw, pw) if cw else None
    if cw:
        wl = f'{format_date_short(cw["start"])} &ndash; {format_date_short(cw["end"])} {cw["end"].strftime("%Y")} <span class="week-label-sub">Week {current_week_idx + 1} of {len(weeks)}</span>'
    else:
        wl = "No data"
    init_strip = render_portfolio_week_strip(cw, projects, today) if cw else ""
    init_summary = render_portfolio_week_summary(cws, cw) if cws else ""
    init_swimlane = render_portfolio_swimlane(cw, projects) if cw else ""
    pd = ' disabled' if current_week_idx <= 0 else ''
    nd = ' disabled' if current_week_idx >= len(weeks) - 1 else ''

    cards = "\n".join(render_project_card(p, i, today) for i, p in enumerate(projects))
    scrubber = render_portfolio_scrubber(day_map, earliest, latest, projects, weeks, current_week_idx)

    html_parts = [
        render_portfolio_header(global_stats, len(projects), total_days),
        render_portfolio_lifetime(global_stats),
        render_allocation_bar(projects),
        f"""  <div class="week-section">
    <div class="week-nav">
      <div class="week-arrows"><div class="week-arrow{pd}" id="p-prev-week">&larr;</div></div>
      <div class="week-label" id="p-week-label">{wl}</div>
      <div class="week-arrows"><div class="week-arrow{nd}" id="p-next-week">&rarr;</div></div>
    </div>
    <div class="week-summary" id="p-week-summary">{init_summary}</div>
    <div class="week-strip" id="p-week-strip">{init_strip}</div>
  </div>""",
        f"""  <div class="swimlane-section">
    <div class="swimlane-label">Project Activity</div>
    <div class="swimlane" id="p-swimlane">{init_swimlane}</div>
  </div>""",
        scrubber,
        f'  <div class="project-cards-section">\n    <div class="section-label">Projects</div>\n{cards}\n  </div>',
    ]

    return "\n\n".join(html_parts), week_data_js


def build_project_view(project):
    s = project.get("stats")
    if not s:
        return f'<div class="page-header"><div class="page-title">{esc(project["name"])}</div><div class="page-subtitle">No session data</div></div>'

    lt = s.get("lifetime", {}); streak = s.get("streak", {})
    recent = s.get("recentSessions", [])
    total_sessions = lt.get("totalSessions", 0)
    first_date = lt.get("firstSessionDate", "") or datetime.now().strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")
    project_path = project["path"]
    slug = project["slug"]

    grouped = group_sessions_by_date(recent, total_sessions)
    weeks = all_weeks_project(first_date, today_str)
    milestones = extract_version_milestones(grouped)
    scrubber_bars, total_days = compute_scrubber_data(grouped, first_date, today_str)

    # Build week panels
    week_panels = []
    week_panels_lower = []
    weeks_js_data = []
    for wi, (monday, sunday) in enumerate(weeks):
        ws = sessions_in_week(grouped, monday, sunday)
        wd = days_in_week(grouped, monday, sunday)
        wstat = compute_week_stats_project(ws)
        prev_stat = None
        if wi + 1 < len(weeks):
            pm, ps_ = weeks[wi + 1]
            prev_stat = compute_week_stats_project(sessions_in_week(grouped, pm, ps_))

        if monday.month == sunday.month:
            wl = f"{monday.strftime('%-d')} - {sunday.strftime('%-d %B %Y')}"
        else:
            wl = f"{monday.strftime('%-d %B')} - {sunday.strftime('%-d %B %Y')}"
        wn = len(weeks) - wi

        summary_card = render_project_week_summary(wstat, prev_stat, ws, wd, wi, len(weeks))
        day_strip = render_project_day_strip(monday, wd, today_str, slug)
        sl_data = compute_swimlane(wd, monday)
        swimlane = render_project_swimlane(sl_data, monday)

        day_groups = []
        for ds in sorted(wd.keys(), reverse=True):
            day_groups.append(render_day_group(ds, wd[ds], wi > 0, project_path))
        if not ws:
            day_groups.append('  <div style="text-align: center; padding: 2rem; color: var(--text-dim);">No sessions this week</div>')

        active = "active" if wi == 0 else ""
        panel_upper = f'  <div class="week-panel {active}" id="week-{slug}-{wi}">\n{summary_card}\n{day_strip}\n  </div>'
        panel_lower = f'  <div class="week-panel-lower {active}" id="week-lower-{slug}-{wi}">\n{swimlane}\n{chr(10).join(day_groups)}\n  </div>'
        week_panels.append(panel_upper)
        week_panels_lower.append(panel_lower)

        first = parse_date(first_date)
        vpl = max(0, ((monday - first).days / max(total_days, 1)) * 100)
        vpr = min(100, ((sunday - first).days / max(total_days, 1)) * 100)
        weeks_js_data.append({"monday": monday.strftime("%Y-%m-%d"), "sunday": sunday.strftime("%Y-%m-%d"),
                              "vpLeft": round(vpl, 1), "vpWidth": round(vpr - vpl, 1),
                              "label": wl, "weekNum": wn, "totalWeeks": len(weeks)})

    header = render_project_header(project)
    lifetime_bar = render_project_lifetime(lt, streak)
    milestones_html = render_project_milestones(milestones)
    scrubber = render_project_scrubber(scrubber_bars, total_days, first_date, today_str, weeks[0][0], weeks[0][1], slug) if weeks else ""
    controls = render_project_controls()
    wl_init = f"{esc(weeks_js_data[0]['label'])} <span class='week-label-sub' id='wk-sub-{slug}'>Week {weeks_js_data[0]['weekNum']} of {weeks_js_data[0]['totalWeeks']}</span>" if weeks_js_data else ""

    content = f"""{header}

{lifetime_bar}

{milestones_html}

{controls}

  <div class="week-section">
    <div class="week-nav">
      <div class="week-arrows"><div class="week-arrow" id="prev-{slug}">&larr;</div></div>
      <div class="week-label" id="wk-label-{slug}">{wl_init}</div>
      <div class="week-arrows"><div class="week-arrow disabled" id="next-{slug}">&rarr;</div></div>
    </div>
{chr(10).join(week_panels)}
{scrubber}
{chr(10).join(week_panels_lower)}
  </div>

  <div class="archive-footer">
    <div>Built with <strong>DOE</strong> &mdash; Directive, Orchestration, Execution</div>
    <div style="margin-top: 0.3rem; font-size: 0.7rem;">Showing {len(recent)} recent sessions. Lifetime: {total_sessions} sessions.</div>
    <div style="margin-top: 0.5rem; font-size: 0.65rem; font-family: 'JetBrains Mono', monospace; opacity: 0.5;">Press ? for keyboard shortcuts &bull; B to go back</div>
  </div>"""

    return content, weeks_js_data


def build_html(projects, registry_path, theme):
    today = datetime.now().date()
    day_map, earliest, latest = compute_all_day_sessions(projects)
    weeks = compute_weeks_global(day_map, earliest, latest)

    cidx = len(weeks) - 1
    for i, w in enumerate(weeks):
        if w["start"] <= today <= w["end"]: cidx = i; break

    portfolio_html, p_week_data = build_portfolio_view(projects, day_map, earliest, latest, weeks, cidx, today)

    # Build each project view
    project_views = []
    project_week_js_parts = []
    for p in projects:
        result = build_project_view(p)
        if isinstance(result, tuple):
            content, wjs = result
            slug = p["slug"]
            project_views.append(f'<div class="view-container project-view" id="view-{slug}">\n<div class="container">\n{content}\n</div>\n</div>')
            # Generate per-project week nav JS
            wjs_json = json.dumps(wjs, ensure_ascii=False)
            project_week_js_parts.append(f"""
(function() {{
  var data = {wjs_json};
  var idx = 0;
  function show(i) {{
    if (i < 0 || i >= data.length) return;
    idx = i;
    var view = document.getElementById('view-{slug}');
    view.querySelectorAll('.week-panel').forEach(function(p) {{ p.classList.remove('active'); }});
    view.querySelectorAll('.week-panel-lower').forEach(function(p) {{ p.classList.remove('active'); }});
    var panel = document.getElementById('week-{slug}-' + i);
    if (panel) panel.classList.add('active');
    var panelLower = document.getElementById('week-lower-{slug}-' + i);
    if (panelLower) panelLower.classList.add('active');
    var lbl = document.getElementById('wk-label-{slug}');
    if (lbl) lbl.innerHTML = data[i].label + ' <span class="week-label-sub">Week ' + data[i].weekNum + ' of ' + data[i].totalWeeks + '</span>';
    var prev = document.getElementById('prev-{slug}');
    var next = document.getElementById('next-{slug}');
    if (prev) {{ if (i >= data.length - 1) prev.classList.add('disabled'); else prev.classList.remove('disabled'); }}
    if (next) {{ if (i <= 0) next.classList.add('disabled'); else next.classList.remove('disabled'); }}
    var vp = view.querySelector('.scrubber-viewport');
    if (vp) {{ vp.style.left = data[i].vpLeft + '%'; vp.style.width = data[i].vpWidth + '%'; }}
  }}
  document.getElementById('prev-{slug}').addEventListener('click', function() {{ show(idx + 1); }});
  document.getElementById('next-{slug}').addEventListener('click', function() {{ show(idx - 1); }});
}})();
window.scrollToDay_{slug} = function(date) {{
  var view = document.getElementById('view-{slug}');
  view.querySelectorAll('.week-day.selected').forEach(function(d) {{ d.classList.remove('selected'); }});
  var clicked = view.querySelector('.week-day[data-date="' + date + '"]');
  if (clicked) clicked.classList.add('selected');
  var target = document.getElementById('day-' + date);
  if (target) {{ target.classList.remove('collapsed'); target.scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }}
}};""")
        else:
            project_views.append(f'<div class="view-container project-view" id="view-{p["slug"]}">\n<div class="container">\n{result}\n</div>\n</div>')

    # Theme init JS
    if theme == "light":
        theme_js = "document.body.classList.add('light');"
    elif theme == "dark":
        theme_js = "// dark by default"
    else:
        theme_js = "if (new Date().getHours() >= 6 && new Date().getHours() < 18) document.body.classList.add('light');"

    p_week_json = json.dumps(p_week_data, ensure_ascii=False)
    js = JS_TEMPLATE.replace("THEME_INIT", theme_js)
    js = js.replace("P_CURRENT_WEEK_IDX", str(cidx))
    js = js.replace("P_WEEK_DATA", p_week_json)
    js = js.replace("PROJECT_WEEK_JS", "\n".join(project_week_js_parts))

    # Keyboard help
    kb = """<div class="kb-help" id="kb-help">
  <div class="kb-help-panel">
    <div class="kb-help-title">Keyboard Shortcuts</div>
    <div class="kb-row"><span class="kb-key">&larr; &rarr;</span> <span class="kb-desc">Navigate weeks</span></div>
    <div class="kb-row"><span class="kb-key">B</span> <span class="kb-desc">Back to portfolio</span></div>
    <div class="kb-row"><span class="kb-key">T</span> <span class="kb-desc">Toggle theme</span></div>
    <div class="kb-row"><span class="kb-key">?</span> <span class="kb-desc">Show / hide help</span></div>
    <div class="kb-row"><span class="kb-key">Esc</span> <span class="kb-desc">Close</span></div>
  </div>
</div>"""

    footer = f"""  <div class="archive-footer">
    <div>Built with <strong>DOE</strong> &mdash; Directive, Orchestration, Execution</div>
    <div style="margin-top: 0.3rem; font-size: 0.7rem;">{len(projects)} projects from {esc(registry_path)}</div>
    <div style="margin-top: 0.5rem; font-size: 0.65rem; font-family: 'JetBrains Mono', monospace; opacity: 0.5;">Press ? for keyboard shortcuts</div>
  </div>"""

    body_cls = ""
    if theme == "light": body_cls = ' class="light"'
    elif theme == "dark": body_cls = ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HQ</title>
<style>
{CSS}
</style>
</head>
<body{body_cls}>
<button class="theme-toggle" id="theme-toggle" title="Toggle theme">&#9790;</button>

{kb}

<div class="view-container portfolio-view active" id="view-portfolio">
<div class="container">

{portfolio_html}

{footer}

</div>
</div>

{chr(10).join(project_views)}

<script>
{js}
</script>
</body>
</html>
"""


def render_error_page(message):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>HQ</title>
<style>{CSS}</style></head><body>
<div class="container"><div class="page-header"><div class="page-title">HQ</div><div class="page-subtitle">{esc(message)}</div></div></div>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate HQ dashboard HTML")
    parser.add_argument("--registry", default=os.path.expanduser("~/.claude/project-registry.json"))
    parser.add_argument("--output", default=os.path.expanduser("~/.claude/docs/hq.html"))
    parser.add_argument("--theme", choices=["light", "dark", "auto"], default="auto")
    args = parser.parse_args()

    registry_path = os.path.abspath(args.registry)
    output_path = os.path.abspath(args.output)
    projects = load_projects(registry_path)

    if projects is None:
        html_out = render_error_page("No projects registered. Run /wrap in a project first.")
    elif len(projects) == 0:
        html_out = render_error_page("Registry is empty. No valid projects found.")
    else:
        html_out = build_html(projects, registry_path, args.theme)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(output_path)


if __name__ == "__main__":
    main()
