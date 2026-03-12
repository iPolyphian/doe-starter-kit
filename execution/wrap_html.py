#!/usr/bin/env python3
"""Generate a session wrap-up HTML page from JSON data.

Usage:
    python3 execution/wrap_html.py --json '{"title": "...", ...}' --output .tmp/wrap.html
    echo '{"title": "..."}' | python3 execution/wrap_html.py
"""

import argparse
import html
import json
import os
import re
import sys


def esc(text):
    """HTML-escape a string."""
    return html.escape(str(text))


def render_title_card(data):
    project = esc(data.get("projectName", ""))
    title = esc(data.get("title", ""))
    return f"""  <div class="report-label">Session Report</div>
  <div class="title-card">
    <div class="project-name">{project}</div>
    <div class="episode">{title}</div>
  </div>"""


def _platform_badge(platform):
    if not platform:
        return ""
    p = platform.lower()
    if p == "win32":
        return '<span class="badge badge-platform-win">PC</span>'
    elif p == "darwin":
        return '<span class="badge badge-platform-mac">Mac</span>'
    elif p == "linux":
        return '<span class="badge badge-platform-linux">Linux</span>'
    return f'<span class="badge badge-platform-linux">{esc(platform)}</span>'


def _model_badge(model):
    if not model:
        return ""
    m = model.lower()
    if "opus" in m:
        return '<span class="badge badge-model-opus">Opus</span>'
    elif "sonnet" in m:
        return '<span class="badge badge-model-sonnet">Sonnet</span>'
    elif "haiku" in m:
        return '<span class="badge badge-model-haiku">Haiku</span>'
    return f'<span class="badge badge-model-sonnet">{esc(model)}</span>'


def _tag_badge(tag):
    if not tag:
        return ""
    t = tag.upper()
    css_map = {
        "BUILD": "badge-tag-build",
        "PLAN": "badge-tag-plan",
        "DEBUG": "badge-tag-debug",
        "HOUSEKEEPING": "badge-tag-housekeeping",
        "RESEARCH": "badge-tag-research",
    }
    css = css_map.get(t, "badge-tag-housekeeping")
    return f'<span class="badge {css}">{esc(t)}</span>'


def render_session_stats_bar(data):
    footer = data.get("footer", {})
    if not footer:
        return ""
    session = esc(footer.get("session", ""))
    streak = esc(footer.get("streak", ""))
    lifetime = esc(footer.get("lifetimeCommits", ""))

    platform_html = _platform_badge(data.get("platform"))
    model_html = _model_badge(data.get("model"))
    tag_html = _tag_badge(data.get("tag"))

    badges = " ".join(b for b in [platform_html, model_html, tag_html] if b)
    badges_html = f'<span class="badge-group">{badges}</span>' if badges else ""

    return f"""  <div class="session-stats-bar">
    <span>Session #{session}</span>
    <span>Streak: {streak} days</span>
    <span>Lifetime: {lifetime} commits</span>
    {badges_html}
  </div>"""


def render_narrative(data):
    summary = data.get("summary", "")
    breakdowns = data.get("breakdowns", [])
    # Fallback: old-style narrative array
    if not summary and not breakdowns:
        lines = data.get("narrative", [])
        if not lines:
            return ""
        summary = " ".join(lines)

    # Build summary paragraph
    summary_html = f'    <p class="summary-lead">{esc(summary)}</p>' if summary else ""

    # Build breakdown sections
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

    # Vibe sits inline on the header
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


def render_stats(data):
    m = data.get("metrics", {})
    if not m:
        return ""
    commits = m.get("commits", 0)
    added = m.get("linesAdded", 0)
    removed = m.get("linesRemoved", 0)
    files = m.get("filesTouched", 0)
    steps = m.get("stepsCompleted", 0)
    duration = esc(m.get("sessionDuration", ""))
    agents = m.get("agentsSpawned", 0)

    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4CA;</span>
      <span class="section-title">Metrics</span>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{esc(commits)}</div>
        <div class="stat-label">Commits</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{esc(added)}</div>
        <div class="stat-label">Lines Added</div>
        <div class="stat-sub">-{esc(removed)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{esc(files)}</div>
        <div class="stat-label">Files Touched</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{esc(steps)}</div>
        <div class="stat-label">Steps Done</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{duration}</div>
        <div class="stat-label">Duration</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{esc(agents)}</div>
        <div class="stat-label">Agents Spawned</div>
      </div>
    </div>
  </div>"""


def _parse_dur_mins(dur_str):
    """Parse a duration string like '15m' or '1h 30m' into total minutes."""
    mins = 0
    h_match = re.search(r'(\d+)h', dur_str)
    m_match = re.search(r'(\d+)m', dur_str)
    if h_match:
        mins += int(h_match.group(1)) * 60
    if m_match:
        mins += int(m_match.group(1))
    return mins


def render_timeline(data):
    items = data.get("timeline", [])
    if not items:
        return ""

    # Calculate total duration in minutes for percentage
    total_mins = 0
    for item in items:
        dur_str = item.get("dur", "")
        if dur_str:
            total_mins += _parse_dur_mins(dur_str)

    rows = []
    for item in items:
        t = esc(item.get("time", ""))
        desc = esc(item.get("desc", ""))
        dur = item.get("dur", "")
        item_type = item.get("type", "")
        css_class = item_type if item_type in ("start", "major", "fix") else ""

        # Calculate percentage
        dur_display = esc(dur)
        if dur and total_mins > 0:
            mins = _parse_dur_mins(dur)
            pct = round(mins / total_mins * 100)
            if pct > 0:
                dur_display = f"{esc(dur)} ({pct}%)"

        rows.append(
            f'    <div class="timeline-item {css_class}">'
            f'<span class="timeline-time">{t}</span>'
            f'<span class="timeline-desc">{desc}</span>'
            f'<span class="timeline-dur">{dur_display}</span>'
            f"</div>"
        )

    # Total session duration
    session_dur = data.get("metrics", {}).get("sessionDuration", "")
    if session_dur:
        rows.append(
            f'    <div class="timeline-total">'
            f'Total: {esc(session_dur)}'
            f'</div>'
        )

    inner = "\n".join(rows)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x23F1;&#xFE0F;</span>
      <span class="section-title">Timeline</span>
    </div>
    <div class="timeline">
{inner}
    <div class="timeline-legend">
      <span class="legend-item"><span class="legend-dot start"></span> Session start</span>
      <span class="legend-item"><span class="legend-dot major"></span> Major change</span>
      <span class="legend-item"><span class="legend-dot fix"></span> Fix</span>
      <span class="legend-item"><span class="legend-dot normal"></span> Normal</span>
    </div>
    </div>
  </div>"""


def render_commits(data):
    m = data.get("metrics", {})
    commit_log = m.get("commitLog", [])
    if not commit_log:
        return ""

    groups = data.get("commitGroups")

    if groups:
        # Build a lookup from hash to commit
        commit_map = {c.get("hash", ""): c for c in commit_log}

        sections = []
        for group in groups:
            name = esc(group.get("name", "Other"))
            hashes = group.get("commits", [])
            count = len(hashes)

            rows = []
            for h in hashes:
                c = commit_map.get(h, {})
                msg = esc(c.get("message", ""))
                ctype = c.get("type", "normal")
                css = "commit-test" if ctype in ("test", "fix") else "commit-msg"
                rows.append(
                    f'      <li class="commit-item">'
                    f'<span class="commit-hash">{esc(h)}</span>'
                    f'<span class="{css}">{msg}</span>'
                    f'</li>'
                )
            inner_rows = "\n".join(rows)
            sections.append(
                f'    <div class="commit-group">'
                f'<div class="commit-group-header">{name} <span class="commit-group-count">({count})</span></div>'
                f'<ul class="commit-list">\n{inner_rows}\n</ul>'
                f'</div>'
            )
        inner = "\n".join(sections)
    else:
        # Flat list fallback
        rows = []
        for c in commit_log:
            h = esc(c.get("hash", ""))
            msg = esc(c.get("message", ""))
            ctype = c.get("type", "normal")
            css = "commit-test" if ctype in ("test", "fix") else "commit-msg"
            rows.append(
                f'    <li class="commit-item">'
                f'<span class="commit-hash">{h}</span>'
                f'<span class="{css}">{msg}</span>'
                f'</li>'
            )
        inner = f'<ul class="commit-list">\n' + "\n".join(rows) + '\n</ul>'

    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4DD;</span>
      <span class="section-title">Commits</span>
    </div>
{inner}
  </div>"""


def render_today_sessions(data):
    sessions = data.get("todaySessions", [])
    if not sessions:
        return ""
    rows = []
    for s in sessions:
        num = esc(s.get("number", ""))
        dur = esc(s.get("duration", ""))
        summary = esc(s.get("summary", ""))
        rows.append(
            f'    <div class="today-session-item">'
            f'<span class="today-session-num">#{num}</span>'
            f'<span class="today-session-dur">{dur}</span>'
            f'<span class="today-session-summary">{summary}</span>'
            f'</div>'
        )
    inner = "\n".join(rows)
    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x1F4C5;</span>
      <span class="section-title">Today&#39;s Sessions</span>
    </div>
    <div class="today-sessions">
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
        # Fallback: old "context" field renders as-is
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


def render_awaiting_signoff(data):
    items = data.get("awaitingSignOff", [])
    if not items:
        return ""

    cards = []
    for item in items:
        feature = esc(item.get("feature", ""))
        summary = esc(item.get("summary", ""))
        count = item.get("manualItems", 0)
        groups = item.get("groups", [])

        # Build grouped checklist
        groups_html = ""
        if groups:
            group_parts = []
            for g in groups:
                name = esc(g.get("name", ""))
                gitems = g.get("items", [])
                items_html = "\n".join(
                    f'          <li class="signoff-item">{esc(i)}</li>' for i in gitems
                )
                group_parts.append(
                    f'      <div class="signoff-group">'
                    f'<div class="signoff-group-name">{name}'
                    f'<span class="signoff-group-count">{len(gitems)}</span></div>'
                    f'<ul class="signoff-checklist">\n{items_html}\n</ul>'
                    f'</div>'
                )
            groups_html = "\n".join(group_parts)

        summary_html = f'<div class="signoff-summary">{summary}</div>' if summary else ""

        cards.append(
            f'    <details class="signoff-card">\n'
            f'      <summary class="signoff-card-header">\n'
            f'        <span class="signoff-feature">{feature}</span>\n'
            f'        <span class="signoff-count">{count} items</span>\n'
            f'      </summary>\n'
            f'      {summary_html}\n'
            f'{groups_html}\n'
            f'    </details>'
        )

    inner = "\n".join(cards)
    total_features = len(items)
    total_items = sum(i.get("manualItems", 0) for i in items)

    return f"""  <div class="section">
    <div class="section-header">
      <span class="section-icon">&#x270D;&#xFE0F;</span>
      <span class="section-title">Awaiting Sign-off</span>
      <span class="signoff-badge">{total_features} features &middot; {total_items} manual items</span>
    </div>
{inner}
  </div>"""


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
        # Detail rows for warnings/failures
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


def render_footer(data):
    return """  <div class="footer">
    <div class="footer-meta">Built with <strong>DOE</strong> &mdash; Directive, Orchestration, Execution</div>
  </div>"""


def render_next_up(data):
    text = data.get("nextUp", "")
    if not text:
        return ""
    return f"""  <div class="next-up">
    <div class="next-up-title">Next Up</div>
    <div class="next-up-desc">{esc(text)}</div>
  </div>"""


BADGE_CSS = r"""
  .badge { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 10px; letter-spacing: 0.05em; text-transform: uppercase; }
  .badge-group { display: inline-flex; gap: 0.4rem; align-items: center; }
  .badge-platform-win { color: #0078D4; background: rgba(0, 120, 212, 0.12); }
  .badge-platform-mac { color: #555; background: rgba(85, 85, 85, 0.12); }
  .badge-platform-linux { color: #E95420; background: rgba(233, 84, 32, 0.12); }
  .badge-model-opus { color: #7C3AED; background: rgba(124, 58, 237, 0.12); }
  .badge-model-sonnet { color: #D97706; background: rgba(217, 119, 6, 0.12); }
  .badge-model-haiku { color: #0D9488; background: rgba(13, 148, 136, 0.12); }
  .badge-tag-build { color: #16a34a; background: rgba(22, 163, 74, 0.12); }
  .badge-tag-plan { color: #2563eb; background: rgba(37, 99, 235, 0.12); }
  .badge-tag-debug { color: #dc2626; background: rgba(220, 38, 38, 0.12); }
  .badge-tag-housekeeping { color: #6b7280; background: rgba(107, 114, 128, 0.12); }
  .badge-tag-research { color: #7c3aed; background: rgba(124, 58, 237, 0.12); }"""

TOGGLE_CSS = r"""
  .theme-toggle { position: fixed; top: 1rem; right: 1rem; display: flex; align-items: center; gap: 0.3rem; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 0.3rem 0.5rem; cursor: pointer; z-index: 100; user-select: none; }
  .toggle-option { font-size: 0.9rem; }
  .toggle-switch { width: 28px; height: 16px; background: var(--border); border-radius: 8px; position: relative; transition: background 0.2s; }
  .toggle-switch::after { content: ''; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px; border-radius: 50%; background: var(--text); transition: transform 0.2s; }
  body.light .toggle-switch::after { transform: translateX(0); }
  body:not(.light) .toggle-switch::after { transform: translateX(12px); }
  .theme-auto-label { position: fixed; top: 3rem; right: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--text-dim); text-align: center; z-index: 100; cursor: pointer; }
  .theme-auto-label:hover { color: var(--accent); }"""

TOGGLE_JS = r"""<script>
(function() {
  var KEY = 'doe-theme';
  var toggle = document.getElementById('themeToggle');
  var label = document.getElementById('themeAutoLabel');
  var mode = localStorage.getItem(KEY) || 'auto';

  function getAutoTheme() {
    var h = new Date().getHours();
    return (h >= 6 && h < 18) ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.body.classList.toggle('light', theme === 'light');
  }

  function update() {
    if (mode === 'auto') {
      applyTheme(getAutoTheme());
      label.textContent = 'Auto';
    } else {
      applyTheme(mode);
      label.textContent = 'Reset to auto';
    }
  }

  toggle.addEventListener('click', function() {
    if (mode === 'auto') {
      mode = getAutoTheme() === 'light' ? 'dark' : 'light';
    } else {
      mode = mode === 'light' ? 'dark' : 'light';
    }
    localStorage.setItem(KEY, mode);
    update();
  });

  label.addEventListener('click', function(e) {
    e.stopPropagation();
    mode = 'auto';
    localStorage.removeItem(KEY);
    update();
  });

  if (mode === 'auto') {
    applyTheme(getAutoTheme());
  } else {
    applyTheme(mode);
  }
  label.textContent = mode === 'auto' ? 'Auto' : 'Reset to auto';
})();
</script>"""

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

  body.light {
    --bg: #f0efe9;
    --surface: #f8f7f3;
    --surface2: #eae9e3;
    --border: #d5d4cc;
    --text: #1a1a2e;
    --text-dim: #6b6b80;
    --accent: #5046e5;
    --accent-glow: rgba(80, 70, 229, 0.08);
    --green: #16a34a;
    --green-dim: rgba(22, 163, 74, 0.08);
    --amber: #d97706;
    --amber-dim: rgba(217, 119, 6, 0.08);
    --red: #dc2626;
    --cyan: #0891b2;
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
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
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

  .commit-list { list-style: none; }
  .commit-item { display: flex; align-items: baseline; gap: 0.8rem; padding: 0.4rem 0; font-size: 0.85rem; border-bottom: 1px solid rgba(42, 42, 58, 0.5); }
  .commit-item:last-child { border-bottom: none; }
  .commit-hash { font-family: 'JetBrains Mono', monospace; color: var(--accent); font-size: 0.75rem; flex-shrink: 0; }
  .commit-msg { color: var(--text); }
  .commit-test { color: var(--text-dim); font-style: italic; }

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
  .next-up-desc { font-size: 0.9rem; color: var(--text); line-height: 1.6; }

  .timeline-total { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-dim); text-align: right; padding-top: 0.5rem; margin-top: 0.5rem; border-top: 1px solid var(--border); }
  .timeline-legend { display: flex; gap: 1.2rem; margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid var(--border); }
  .legend-item { display: flex; align-items: center; gap: 0.4rem; font-size: 0.7rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }
  .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
  .legend-dot.start { background: var(--accent); }
  .legend-dot.major { background: var(--green); }
  .legend-dot.fix { background: var(--amber); }
  .legend-dot.normal { background: var(--border); }

  .commit-group { margin-bottom: 1rem; }
  .commit-group:last-child { margin-bottom: 0; }
  .commit-group-header { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600; color: var(--accent); margin-bottom: 0.4rem; padding-bottom: 0.3rem; border-bottom: 1px solid var(--border); }
  .commit-group-count { font-weight: 400; color: var(--text-dim); }

  .signoff-card { background: var(--surface); border: 1px solid var(--amber); border-radius: 8px; margin-bottom: 0.8rem; }
  .signoff-card:last-child { margin-bottom: 0; }
  .signoff-card-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.2rem; cursor: pointer; list-style: none; }
  .signoff-card-header::-webkit-details-marker { display: none; }
  .signoff-card-header::before { content: '\25B6'; font-size: 0.6rem; color: var(--text-dim); margin-right: 0.6rem; transition: transform 0.2s; }
  .signoff-card[open] > .signoff-card-header::before { transform: rotate(90deg); }
  .signoff-feature { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 600; color: var(--text); flex: 1; }
  .signoff-count { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--amber); background: var(--amber-dim); padding: 0.15rem 0.5rem; border-radius: 4px; flex-shrink: 0; }
  .signoff-summary { font-size: 0.8rem; color: var(--text-dim); line-height: 1.5; padding: 0 1.2rem 0.8rem; border-bottom: 1px solid var(--border); }
  .signoff-group { padding: 0.6rem 1.2rem; }
  .signoff-group:last-child { padding-bottom: 1rem; }
  .signoff-group-name { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.4rem; }
  .signoff-group-count { font-size: 0.6rem; font-weight: 400; color: var(--amber); background: var(--amber-dim); padding: 0.05rem 0.35rem; border-radius: 3px; }
  .signoff-checklist { list-style: none; padding: 0; margin: 0; }
  .signoff-item { font-size: 0.8rem; color: var(--text-dim); line-height: 1.6; padding: 0.15rem 0 0.15rem 1.2rem; position: relative; }
  .signoff-item::before { content: '\25A1'; position: absolute; left: 0; color: var(--amber); font-size: 0.7rem; }
  .signoff-badge { margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--amber); }

  .today-sessions { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem 1.2rem; }
  .today-session-item { display: flex; align-items: baseline; gap: 0.8rem; padding: 0.4rem 0; font-size: 0.85rem; border-bottom: 1px solid rgba(42, 42, 58, 0.5); }
  .today-session-item:last-child { border-bottom: none; }
  .today-session-num { font-family: 'JetBrains Mono', monospace; color: var(--accent); font-size: 0.75rem; flex-shrink: 0; width: 2.5rem; }
  .today-session-dur { font-family: 'JetBrains Mono', monospace; color: var(--text-dim); font-size: 0.75rem; flex-shrink: 0; width: 4rem; }
  .today-session-summary { color: var(--text); flex: 1; }"""


def build_html(data):
    """Build the complete HTML string from the data dict."""
    theme = data.get("theme", "dark")
    body_class = ' class="light"' if theme == "light" else ""
    episode = esc(data.get("episode", ""))
    title = esc(data.get("title", ""))

    sections = [
        render_title_card(data),
        render_session_stats_bar(data),
        render_narrative(data),       # includes vibe at bottom
        render_timeline(data),
        render_stats(data),
        render_commits(data),
        render_decisions_learnings(data),
        render_checks(data),
        render_awaiting_signoff(data),
        render_today_sessions(data),
        render_next_up(data),
        render_footer(data),
    ]
    body = "\n".join(s for s in sections if s)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Session {episode} — {title}</title>
<style>
{CSS}
{BADGE_CSS}
{TOGGLE_CSS}
</style>
</head>
<body{body_class}>
<div class="theme-toggle" id="themeToggle">
  <span class="toggle-option">&#x2600;&#xFE0F;</span>
  <span class="toggle-switch"></span>
  <span class="toggle-option">&#x1F319;</span>
</div>
<div class="theme-auto-label" id="themeAutoLabel">Auto</div>
<div class="container">
{body}
</div>
{TOGGLE_JS}
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate session wrap-up HTML")
    parser.add_argument("--json", dest="json_str", help="JSON data as a string argument")
    parser.add_argument("--theme", choices=["light", "dark"], default="dark", help="Color theme")
    parser.add_argument("--output", default=".tmp/wrap.html", help="Output HTML file path (default: .tmp/wrap.html)")
    args = parser.parse_args()

    if args.json_str:
        data = json.loads(args.json_str)
    else:
        data = json.load(sys.stdin)

    data["theme"] = args.theme

    html_out = build_html(data)

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(out_path)


if __name__ == "__main__":
    main()
