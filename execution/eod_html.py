#!/usr/bin/env python3
"""Generate an end-of-day HTML report from JSON data.

Aggregates all sessions from a single day into one report.

Usage:
    python3 execution/eod_html.py --json '{"projectName": "...", ...}' --output .tmp/eod.html
    echo '{"projectName": "..."}' | python3 execution/eod_html.py
"""

import argparse
import html
import json
import os
import sys


def esc(text):
    """HTML-escape a string."""
    return html.escape(str(text))


def render_title_card(data):
    project = esc(data.get("projectName", ""))
    return f"""  <div class="report-label">End of Day Report</div>
  <div class="title-card">
    <div class="project-name">{project}</div>
  </div>"""


def render_session_stats_bar(data):
    streak = data.get("streak", 0)
    date_str = data.get("date", "")
    # Parse DD/MM/YY and format as "Friday 6th March"
    from datetime import datetime
    now = datetime.now()
    pretty_date = date_str
    try:
        dt = datetime.strptime(date_str, "%d/%m/%y")
        day = dt.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        pretty_date = f"{dt.strftime('%A')} {day}{suffix} {dt.strftime('%B')}"
    except (ValueError, TypeError):
        pass
    time_now = now.strftime("%H:%M")
    return f"""  <div class="session-stats-bar">
    <span>{esc(pretty_date)}</span>
    <span>{time_now}</span>
    <span>{esc(streak)} Day streak</span>
  </div>"""


def render_summary(data):
    summary = data.get("summary", "")
    breakdowns = data.get("breakdowns", [])
    # Handle old-style list format
    if isinstance(summary, list):
        summary = " ".join(summary)
    if not summary and not breakdowns:
        return ""

    summary_html = f'    <p class="summary-lead">{esc(summary)}</p>' if summary else ""

    breakdown_html = ""
    if breakdowns:
        parts = []
        for b in breakdowns:
            heading = esc(b.get("heading", ""))
            bullets = b.get("bullets", [])
            bullet_items = "\n".join(f'        <li>{esc(item)}</li>' for item in bullets)
            parts.append(
                f'    <div class="breakdown-group">\n'
                f'      <div class="breakdown-heading">{heading}</div>\n'
                f'      <ul class="breakdown-bullets">\n{bullet_items}\n      </ul>\n'
                f'    </div>'
            )
        breakdown_html = "\n".join(parts)

    vibe = data.get("vibe")
    vibe_html = ""
    if vibe:
        emoji = vibe.get("emoji", "")
        text = esc(vibe.get("text", ""))
        vibe_html = f'<span class="vibe-inline">Vibe: {emoji} {text}</span>'

    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4CB;</span>
      <span class="section-title">Summary</span>
      {vibe_html}
    </div>
    <div class="summary">
{summary_html}
{breakdown_html}
    </div>
  </div>"""


def render_session_timeline(data):
    items = data.get("sessionTimeline", [])
    if not items:
        return ""

    rows = []
    for item in items:
        num = esc(item.get("number", ""))
        start = esc(item.get("start", ""))
        summary = esc(item.get("summary", ""))
        duration = esc(item.get("duration", ""))
        pct = item.get("pct", 0)

        dur_display = f"{duration} ({pct}%)" if pct else duration

        rows.append(
            f'    <div class="timeline-item major">'
            f'<span class="timeline-time">{start}</span>'
            f'<span class="timeline-desc">#{num} &mdash; {summary}</span>'
            f'<span class="timeline-dur">{dur_display}</span>'
            f'</div>'
        )

    # Total line
    total_dur = data.get("metrics", {}).get("totalDuration", "")
    if total_dur:
        rows.append(
            f'    <div class="timeline-total">'
            f'Total: {esc(total_dur)}'
            f'</div>'
        )

    inner = "\n".join(rows)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x23F1;&#xFE0F;</span>
      <span class="section-title">Daily Timeline</span>
    </div>
    <div class="timeline">
{inner}
    <div class="timeline-legend">
      <span class="legend-item"><span class="legend-dot major"></span> Each dot represents one session</span>
    </div>
    </div>
  </div>"""


def render_metrics(data):
    m = data.get("metrics", {})
    if not m:
        return ""
    sessions = m.get("sessions", 0)
    total_dur = esc(m.get("totalDuration", ""))
    commits = m.get("commits", 0)
    added = m.get("linesAdded", 0)
    removed = m.get("linesRemoved", 0)
    files = m.get("filesTouched", 0)
    steps = m.get("stepsCompleted", 0)
    features = m.get("featuresCompleted", 0)
    agents = m.get("agentsSpawned", 0)
    avg_session = esc(m.get("avgSession", ""))

    cards = [
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(sessions)}</div>
        <div class="stat-label">Sessions</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{total_dur}</div>
        <div class="stat-label">Total Time</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{avg_session}</div>
        <div class="stat-label">Avg Session</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(commits)}</div>
        <div class="stat-label">Commits</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(added)}</div>
        <div class="stat-label">Lines Added</div>
        <div class="stat-sub">-{esc(removed)}</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(files)}</div>
        <div class="stat-label">Files Touched</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(steps)}</div>
        <div class="stat-label">Steps Done</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(features)}</div>
        <div class="stat-label">Features Shipped</div>
      </div>""",
        f"""      <div class="stat-card">
        <div class="stat-value">{esc(agents)}</div>
        <div class="stat-label">Agents Spawned</div>
      </div>""",
    ]

    inner = "\n".join(cards)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4CA;</span>
      <span class="section-title">Metrics</span>
    </div>
    <div class="stats-grid">
{inner}
    </div>
  </div>"""


def render_commit_breakdown(data):
    items = data.get("commitBreakdown", [])
    if not items:
        return ""

    rows = []
    for item in items:
        name = esc(item.get("name", ""))
        count = item.get("count", 0)
        pct = item.get("pct", 0)
        rows.append(
            f'    <div class="breakdown-item">'
            f'<span class="breakdown-name">{name}</span>'
            f'<span class="breakdown-bar" style="width: {pct}%"></span>'
            f'<span class="breakdown-stat">{count} commits ({pct}%)</span>'
            f'</div>'
        )

    inner = "\n".join(rows)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4DD;</span>
      <span class="section-title">Commit Breakdown</span>
    </div>
    <div class="breakdown">
{inner}
    </div>
  </div>"""


def _render_insight_item(item, dot_class, item_kind="decision"):
    """Render a decision or learning item.

    Decisions use Problem/Solution labels. Learnings use Discovery/Change labels.
    Supports string (backward compat) or rich object format.
    """
    if isinstance(item, dict):
        title = esc(item.get("title", ""))
        problem = esc(item.get("problem", ""))
        solution = esc(item.get("solution", ""))
        context = esc(item.get("context", ""))
        detail_html = ""
        if problem and solution:
            if item_kind == "learning":
                detail_html = (
                    f'<div class="insight-details">'
                    f'<div class="insight-detail">'
                    f'<span class="insight-label discovery">Discovery</span> {problem}'
                    f'</div>'
                    f'<div class="insight-detail">'
                    f'<span class="insight-label change">Change</span> {solution}'
                    f'</div>'
                    f'</div>'
                )
            else:
                detail_html = (
                    f'<div class="insight-details">'
                    f'<div class="insight-detail">'
                    f'<span class="insight-label problem">Problem</span> {problem}'
                    f'</div>'
                    f'<div class="insight-detail">'
                    f'<span class="insight-label solution">Solution</span> {solution}'
                    f'</div>'
                    f'</div>'
                )
        elif context:
            detail_html = f'<div class="insight-context">{context}</div>'
        return (
            f'    <div class="insight-item">'
            f'<span class="{dot_class}"></span>'
            f'<div class="insight-content">'
            f'<div class="insight-title">{title}</div>'
            f'{detail_html}'
            f'</div></div>'
        )
    return (
        f'    <div class="insight-item">'
        f'<span class="{dot_class}"></span>'
        f'<div class="insight-content">'
        f'<div class="insight-title">{esc(item)}</div>'
        f'</div></div>'
    )


def render_decisions_learnings(data):
    decisions = data.get("decisions", [])
    learnings = data.get("learnings", [])
    if isinstance(decisions, str):
        decisions = []
    if isinstance(learnings, str):
        learnings = []
    if not decisions and not learnings:
        return ""
    parts = []
    if decisions:
        rows = "\n".join(_render_insight_item(d, "decision-dot", "decision") for d in decisions)
        parts.append(f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x2696;&#xFE0F;</span>
      <span class="section-title">Decisions</span>
    </div>
{rows}
  </div>""")
    if learnings:
        rows = "\n".join(_render_insight_item(l, "learning-dot", "learning") for l in learnings)
        parts.append(f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4A1;</span>
      <span class="section-title">Learnings</span>
    </div>
{rows}
  </div>""")
    return "\n".join(parts)


def render_checks(data):
    checks = data.get("checks")
    if not checks:
        return ""
    audit = checks.get("audit", {})
    doe = checks.get("doeKit", {})
    rows = []
    # Audit row
    p = audit.get("pass", 0)
    w = audit.get("warn", 0)
    f = audit.get("fail", 0)
    if p or w or f:
        badge = f'<span class="check-pass">PASS {p}</span>'
        if w > 0:
            badge += f' <span class="check-warn">WARN {w}</span>'
        if f > 0:
            badge += f' <span class="check-fail">FAIL {f}</span>'
        rows.append(f'    <div class="check-row">{badge} <span class="check-label">Claim Audit</span></div>')
        for detail in audit.get("details", []):
            detail_text = esc(detail)
            if w > 0 and f == 0:
                rows.append(f'    <div class="check-row"><span class="check-warn">{detail_text}</span></div>')
            elif f > 0:
                rows.append(f'    <div class="check-row"><span class="check-fail">{detail_text}</span></div>')
    # DOE Kit row
    version = esc(doe.get("version", ""))
    synced = doe.get("synced", True)
    if version:
        if synced:
            rows.append(
                f'    <div class="check-row"><span class="check-pass">SYNCED</span> '
                f'<span class="check-label">DOE Kit</span> '
                f'<span class="check-value">{version}</span></div>'
            )
        else:
            rows.append(
                f'    <div class="check-row"><span class="check-warn">{version}*</span> '
                f'<span class="check-label">DOE Kit</span> '
                f'<span class="check-value">not synced</span></div>'
            )
    if not rows:
        return ""
    inner = "\n".join(rows)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x2705;</span>
      <span class="section-title">Checks</span>
    </div>
    <div class="checks">
{inner}
    </div>
  </div>"""


def render_next_up(data):
    text = data.get("nextUp", "")
    if not text:
        return ""
    return f"""  <div class="next-up">
    <div class="next-up-title">Next Up</div>
    <div class="next-up-desc">{esc(text)}</div>
  </div>"""


def render_footer(data):
    return """  <div class="footer">
    <div class="footer-meta">Built with <strong>DOE</strong> &mdash; Directive, Orchestration, Execution</div>
  </div>"""


CSS = r"""  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a26;
    --border: #2a2a3a;
    --text: #e0e0e8;
    --text-dim: #8888a0;
    --accent: #6c63ff;
    --accent-glow: rgba(108, 99, 255, 0.15);
    --green: #4ade80;
    --green-dim: rgba(74, 222, 128, 0.1);
    --amber: #fbbf24;
    --amber-dim: rgba(251, 191, 36, 0.1);
    --red: #f87171;
    --cyan: #67e8f9;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    padding: 2rem;
  }

  .container { max-width: 800px; margin: 0 auto; }

  .report-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-dim);
    text-align: center;
    margin: 0 0 1.5rem;
    position: relative;
  }
  .report-label::before, .report-label::after {
    content: '';
    position: absolute;
    top: 50%;
    width: 30%;
    height: 1px;
    background: var(--border);
  }
  .report-label::before { left: 0; }
  .report-label::after { right: 0; }

  .title-card {
    text-align: center;
    padding: 3rem 2rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: linear-gradient(135deg, var(--surface) 0%, var(--bg) 100%);
    position: relative;
    overflow: hidden;
  }

  .session-stats-bar {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--green);
    padding: 1rem 0 1.2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 5px;
  }

  .title-card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at center, var(--accent-glow) 0%, transparent 70%);
    pointer-events: none;
  }

  .project-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.8rem; font-weight: 700;
    letter-spacing: 0.6em; text-transform: uppercase;
    color: var(--text); margin-bottom: 0.5rem; position: relative;
  }

  .episode {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem; color: var(--accent);
    letter-spacing: 0.15em; text-transform: uppercase; position: relative;
  }

  .summary { padding: 0; }
  .summary p { color: var(--text); font-size: 0.95rem; line-height: 1.8; margin-bottom: 0.5rem; }
  .summary p:last-child { margin-bottom: 0; }
  .summary-lead { font-size: 0.95rem; color: var(--text); line-height: 1.8; padding-bottom: 1rem; }
  .breakdown-group { margin-bottom: 0.6rem; margin-top: 0.6rem; }
  .breakdown-group:last-child { margin-bottom: 0; }
  .breakdown-heading { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); margin-bottom: 0.3rem; }
  .breakdown-bullets { list-style: none; padding: 0; margin: 0; }
  .breakdown-bullets li { font-size: 0.85rem; color: var(--text-dim); line-height: 1.6; padding-left: 1rem; position: relative; }
  .breakdown-bullets li::before { content: '\2022'; position: absolute; left: 0; color: var(--border); }

  .section { margin-bottom: 2rem; }
  .section-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }
  .section-icon { font-size: 1.1rem; }
  .section-title { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: var(--text-dim); }

  .vibe-inline { margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-dim); letter-spacing: 0.05em; }

  .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 0.5rem; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }
  .stat-value { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: var(--text); }
  .stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-top: 0.2rem; }
  .stat-sub { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--green); margin-top: 0.2rem; }

  .timeline { position: relative; padding-left: 1.5rem; }
  .timeline::before { content: ''; position: absolute; left: 0.35rem; top: 0.5rem; bottom: 0.5rem; width: 2px; background: var(--border); }
  .timeline-item { position: relative; padding: 0.5rem 0 0.5rem 1rem; display: flex; align-items: baseline; gap: 1rem; }
  .timeline-item::before { content: ''; position: absolute; left: -1.2rem; top: 0.85rem; width: 8px; height: 8px; border-radius: 50%; background: var(--border); border: 2px solid var(--bg); }
  .timeline-item.start::before { background: var(--accent); }
  .timeline-item.major::before { background: var(--green); }
  .timeline-item.fix::before { background: var(--amber); }
  .timeline-time { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-dim); flex-shrink: 0; width: 3rem; }
  .timeline-desc { font-size: 0.85rem; color: var(--text); flex: 1; }
  .timeline-dur { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); flex-shrink: 0; text-align: right; min-width: 5rem; }

  .timeline-total { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-dim); text-align: right; padding-top: 0.5rem; margin-top: 0.5rem; border-top: 1px solid var(--border); }
  .timeline-legend { display: flex; gap: 1.2rem; margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid var(--border); }
  .legend-item { display: flex; align-items: center; gap: 0.4rem; font-size: 0.7rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }
  .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
  .legend-dot.major { background: var(--green); }

  .breakdown { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.2rem; }
  .breakdown-item { display: flex; align-items: center; gap: 0.8rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(42, 42, 58, 0.5); }
  .breakdown-item:last-child { border-bottom: none; }
  .breakdown-name { font-size: 0.85rem; color: var(--text); flex-shrink: 0; min-width: 10rem; }
  .breakdown-bar { height: 4px; background: var(--accent); border-radius: 2px; flex-shrink: 0; }
  .breakdown-stat { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); flex-shrink: 0; white-space: nowrap; margin-left: auto; }

  .insight-item { display: flex; align-items: flex-start; gap: 0.8rem; padding: 0.6rem 0; border-bottom: 1px solid rgba(42, 42, 58, 0.5); }
  .insight-item:last-child { border-bottom: none; }
  .insight-content { flex: 1; }
  .insight-title { font-size: 0.85rem; font-weight: 500; color: var(--text); line-height: 1.4; }
  .insight-context { font-size: 0.8rem; color: var(--text-dim); line-height: 1.6; margin-top: 0.3rem; }
  .insight-details { padding: 0.3rem 0 0 0; margin-top: 0.3rem; display: flex; flex-direction: column; gap: 0.4rem; }
  .insight-detail { font-size: 0.8rem; color: var(--text); line-height: 1.5; display: flex; align-items: baseline; gap: 0.6rem; }
  .insight-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.1rem 0.45rem; border-radius: 3px; flex-shrink: 0; }
  .insight-label.problem { color: var(--amber); background: var(--amber-dim); }
  .insight-label.solution { color: var(--green); background: var(--green-dim); }
  .insight-label.discovery { color: var(--accent); background: var(--accent-glow); }
  .insight-label.change { color: var(--cyan); background: rgba(103, 232, 249, 0.1); }
  .learning-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex-shrink: 0; margin-top: 0.55rem; }
  .decision-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); flex-shrink: 0; margin-top: 0.55rem; }

  .checks { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.2rem; }
  .check-row { display: flex; align-items: center; gap: 0.8rem; padding: 0.3rem 0; font-size: 0.85rem; }
  .check-pass { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--green); background: var(--green-dim); padding: 0.15rem 0.5rem; border-radius: 4px; }
  .check-warn { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--amber); background: var(--amber-dim); padding: 0.15rem 0.5rem; border-radius: 4px; }
  .check-fail { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--red); background: rgba(248, 113, 113, 0.1); padding: 0.15rem 0.5rem; border-radius: 4px; }
  .check-label { color: var(--text-dim); }
  .check-value { color: var(--text); }

  .footer { border-top: 1px solid var(--border); padding-top: 1.5rem; margin-top: 2rem; text-align: center; }
  .footer-checks { display: flex; justify-content: center; gap: 1.5rem; margin-bottom: 0.8rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--green); }
  .footer-meta { font-size: 0.8rem; color: var(--text-dim); }
  .footer-meta strong { color: var(--accent); font-weight: 600; }

  .next-up { background: var(--accent-glow); border: 1px solid rgba(108, 99, 255, 0.3); border-radius: 8px; padding: 1rem 1.5rem; margin-top: 1.5rem; }
  .next-up-title { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--accent); margin-bottom: 0.4rem; }
  .next-up-desc { font-size: 0.9rem; color: var(--text); line-height: 1.6; }"""


def build_html(data):
    """Build the complete HTML string from the data dict."""
    project = esc(data.get("projectName", ""))
    date = esc(data.get("date", ""))

    sections = [
        render_title_card(data),
        render_session_stats_bar(data),
        render_summary(data),
        render_session_timeline(data),
        render_metrics(data),
        render_commit_breakdown(data),
        render_decisions_learnings(data),
        render_checks(data),
        render_next_up(data),
        render_footer(data),
    ]
    body = "\n".join(s for s in sections if s)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project} &mdash; EOD Report {date}</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate end-of-day HTML report")
    parser.add_argument("--json", dest="json_str", help="JSON data as a string argument")
    parser.add_argument("--output", default=".tmp/eod.html", help="Output HTML file path (default: .tmp/eod.html)")
    args = parser.parse_args()

    if args.json_str:
        data = json.loads(args.json_str)
    else:
        data = json.load(sys.stdin)

    html_out = build_html(data)

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(out_path)


if __name__ == "__main__":
    main()
