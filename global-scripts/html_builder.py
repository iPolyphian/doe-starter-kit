"""
DOE HTML Report Builder -- shared visual language for all DOE report generators.

Single source for colour tokens, CSS reset, page scaffold, and component library.
All DOE HTML generators import from here instead of reimplementing styles.

Canonical source: wireframes at .tmp/builder-wireframes-docs.html (signed off v1.53.0)

Usage:
    from html_builder import page_scaffold, card, badge, metric_grid, progress_bar
    html = page_scaffold('My Report', body_html, css=my_extra_css)
"""

from html import escape as _esc

# ── Colour Tokens ───────────────────────────────────────────────────────────
# Flat dict for programmatic access (inline styles, Python-side colour logic).
# These match the :root CSS variables in base_css(). For dark mode, use CSS
# variables in templates -- the browser resolves them automatically.

DOE_COLORS = {
    'bg': '#FFFFFF',
    'bg_sidebar': '#FAFAFA',
    'surface': '#FFFFFF',
    'surface2': '#F8FAFC',
    'border': '#E2E8F0',
    'text': '#1E293B',
    'text_dim': '#64748B',
    'text_muted': '#94A3B8',
    'accent': '#6366F1',
    'accent_light': 'rgba(99, 102, 241, 0.08)',
    'accent_mid': 'rgba(99, 102, 241, 0.15)',
    'green': '#10B981',
    'green_bg': '#F0FDF4',
    'green_border': '#BBF7D0',
    'green_dim': 'rgba(16, 185, 129, 0.10)',
    'amber': '#F59E0B',
    'amber_bg': '#FFFBEB',
    'amber_border': '#FDE68A',
    'amber_dim': 'rgba(245, 158, 11, 0.10)',
    'blue': '#3B82F6',
    'blue_bg': '#EFF6FF',
    'blue_border': '#BFDBFE',
    'blue_dim': 'rgba(59, 130, 246, 0.10)',
    'rose': '#F43F5E',
    'rose_bg': '#FFF1F2',
    'rose_border': '#FECDD3',
    'rose_dim': 'rgba(244, 63, 94, 0.10)',
    'code_bg': '#0F172A',
    'code_text': '#CBD5E1',
    'shadow_sm': '0 1px 3px rgba(0,0,0,0.04)',
    'shadow_md': '0 4px 12px rgba(0,0,0,0.08)',
}


# ── CSS ─────────────────────────────────────────────────────────────────────

def base_css():
    """Shared CSS: tokens (light + dark), reset, layout, and all component styles.

    Generators add report-specific CSS via the ``css`` parameter of page_scaffold().
    """
    return """\
/* DOE HTML Builder — base styles */

/* ── Tokens ──────────────────────────────────────────────── */
:root {
  --bg: #FFFFFF;
  --bg-sidebar: #FAFAFA;
  --surface: #FFFFFF;
  --surface2: #F8FAFC;
  --border: #E2E8F0;
  --text: #1E293B;
  --text-dim: #64748B;
  --text-muted: #94A3B8;
  --accent: #6366F1;
  --accent-light: rgba(99, 102, 241, 0.08);
  --accent-mid: rgba(99, 102, 241, 0.15);
  --green: #10B981;
  --green-bg: #F0FDF4;
  --green-border: #BBF7D0;
  --green-dim: rgba(16, 185, 129, 0.10);
  --amber: #F59E0B;
  --amber-bg: #FFFBEB;
  --amber-border: #FDE68A;
  --amber-dim: rgba(245, 158, 11, 0.10);
  --blue: #3B82F6;
  --blue-bg: #EFF6FF;
  --blue-border: #BFDBFE;
  --blue-dim: rgba(59, 130, 246, 0.10);
  --rose: #F43F5E;
  --rose-bg: #FFF1F2;
  --rose-border: #FECDD3;
  --rose-dim: rgba(244, 63, 94, 0.10);
  --code-bg: #0F172A;
  --code-text: #CBD5E1;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}
[data-theme="dark"] {
  --bg: #0B1120;
  --bg-sidebar: #0F172A;
  --surface: #1E293B;
  --surface2: #1E293B;
  --border: #334155;
  --text: #E2E8F0;
  --text-dim: #94A3B8;
  --text-muted: #64748B;
  --accent: #818CF8;
  --accent-light: rgba(129, 140, 248, 0.10);
  --accent-mid: rgba(129, 140, 248, 0.18);
  --green: #34D399;
  --green-bg: rgba(16, 185, 129, 0.10);
  --green-border: rgba(16, 185, 129, 0.25);
  --green-dim: rgba(52, 211, 153, 0.12);
  --amber: #FBBF24;
  --amber-bg: rgba(245, 158, 11, 0.10);
  --amber-border: rgba(245, 158, 11, 0.25);
  --amber-dim: rgba(251, 191, 36, 0.12);
  --blue: #60A5FA;
  --blue-bg: rgba(59, 130, 246, 0.10);
  --blue-border: rgba(59, 130, 246, 0.25);
  --blue-dim: rgba(96, 165, 250, 0.12);
  --rose: #FB7185;
  --rose-bg: rgba(244, 63, 94, 0.10);
  --rose-border: rgba(244, 63, 94, 0.25);
  --rose-dim: rgba(251, 113, 133, 0.12);
  --code-bg: #0F172A;
  --code-text: #CBD5E1;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.2);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.3);
}

/* ── Reset & Base ────────────────────────────────────────── */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  font-size: 15px;
  line-height: 1.7;
  min-height: 100vh;
  transition: background 0.3s, color 0.3s;
}

/* ── Layout ──────────────────────────────────────────────── */
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 24px 60px;
}
.page-label {
  font-size: 12px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--accent); margin-bottom: 6px;
}
.page-title {
  font-size: 32px; font-weight: 700; line-height: 1.2;
  margin-bottom: 6px;
}
.page-title-dim { color: var(--text-dim); font-weight: 400; }
.page-subtitle {
  color: var(--text-dim); font-size: 15px; line-height: 1.7;
  margin-bottom: 12px;
}
.badge-row {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 32px;
}
.section { margin-bottom: 36px; }
.section-title {
  font-size: 22px; font-weight: 600; line-height: 1.3;
  margin-bottom: 6px;
}
.section-subtitle {
  font-size: 17px; font-weight: 600; line-height: 1.4;
  margin-bottom: 4px;
}
.section-desc {
  color: var(--text-dim); font-size: 14px; margin-bottom: 16px;
}
.divider { border: none; border-top: 1px solid var(--border); margin: 36px 0; }

/* ── Stats Bar ───────────────────────────────────────────── */
.stats-bar {
  display: flex; gap: 16px; flex-wrap: wrap;
  color: var(--text-dim);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  margin-bottom: 32px;
}
.stats-bar span { display: inline-flex; align-items: center; gap: 4px; }

/* ── Badge ───────────────────────────────────────────────── */
.badge {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 12px;
  text-transform: uppercase; letter-spacing: 0.04em;
  display: inline-flex; align-items: center;
}
.badge-pass { color: var(--green); background: var(--green-dim); }
.badge-fail { color: var(--rose); background: var(--rose-dim); }
.badge-warn { color: var(--amber); background: var(--amber-dim); }
.badge-info { color: var(--blue); background: var(--blue-dim); }
.badge-accent { color: var(--accent); background: var(--accent-light); }
.badge-dim { color: var(--text-dim); background: var(--surface2); }

/* ── Card ────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
}
.card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}
.card-header {
  display: flex; align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-title { font-weight: 600; font-size: 15px; }
.card-meta { color: var(--text-dim); font-size: 13px; }
.card-body { color: var(--text-dim); font-size: 14px; line-height: 1.7; }
.card-collapsible .card-header {
  cursor: pointer; user-select: none; margin-bottom: 0;
}
.card-collapsible .card-header:hover .card-title { color: var(--accent); }
.card-collapsible .card-chevron {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); font-size: 12px;
  transition: transform 0.25s ease;
  flex-shrink: 0;
}
.card-collapsible.collapsed .card-chevron { transform: rotate(-90deg); }
.card-collapsible .card-collapse-body {
  overflow: hidden;
  transition: max-height 0.3s ease, opacity 0.25s ease, margin-top 0.25s ease;
  max-height: 1500px;
  opacity: 1;
  margin-top: 12px;
}
.card-collapsible.collapsed .card-collapse-body {
  max-height: 0; opacity: 0; margin-top: 0;
}

/* ── Metric Grid ─────────────────────────────────────────── */
.metric-grid {
  display: grid; gap: 12px; margin-bottom: 20px;
}
.metric-grid-2 { grid-template-columns: repeat(2, 1fr); }
.metric-grid-3 { grid-template-columns: repeat(3, 1fr); }
.metric-grid-4 { grid-template-columns: repeat(4, 1fr); }
.metric-grid-5 { grid-template-columns: repeat(5, 1fr); }
.metric-grid-6 { grid-template-columns: repeat(6, 1fr); }
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 16px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.metric-card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}
.metric-value {
  font-size: 24px; font-weight: 700;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  line-height: 1.2;
}
.metric-label {
  font-size: 11px; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-top: 4px; font-weight: 500;
}
@media (max-width: 700px) {
  .metric-grid-4, .metric-grid-5, .metric-grid-6 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .metric-grid-2, .metric-grid-3 { grid-template-columns: repeat(2, 1fr); }
}

/* ── Progress Bar ────────────────────────────────────────── */
.progress { margin-bottom: 12px; }
.progress-label {
  display: flex; justify-content: space-between;
  font-size: 13px; margin-bottom: 8px; font-weight: 500;
}
.progress-track {
  width: 100%; height: 14px;
  background: var(--border);
  border-radius: 7px; overflow: hidden; display: flex;
}
.progress-fill { height: 100%; transition: width 0.4s ease; }
.progress-fill.pass { background: var(--green); }
.progress-fill.fail { background: var(--rose); }
.progress-fill.warn { background: var(--amber); }
.progress-fill.accent { background: var(--accent); }
.progress-stats {
  display: flex; gap: 16px;
  font-size: 13px; color: var(--text-dim); margin-top: 8px;
}

/* ── Step Indicators ─────────────────────────────────────── */
.step-card {
  position: relative;
  padding-left: 44px;
  margin-bottom: 16px;
}
.step-card::before {
  content: attr(data-step);
  position: absolute; left: 0; top: 20px;
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.step-card .card { margin-bottom: 0; }
.step-card::after {
  content: '';
  position: absolute; left: 13px; top: 52px; bottom: -16px;
  width: 2px; background: var(--accent); opacity: 0.2;
}
.step-card:last-child::after { display: none; }

/* ── Table ───────────────────────────────────────────────── */
.table {
  width: 100%; border-collapse: collapse; font-size: 14px;
}
.table th {
  text-align: left; font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-dim); padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}
.table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}
.table tr:last-child td { border-bottom: none; }
.table tr:hover td { background: var(--surface2); }
.table .mono {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}

/* ── Pill / Tag ──────────────────────────────────────────── */
.pill {
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 12px;
  display: inline-flex; align-items: center; gap: 4px;
}
.pill-green { color: var(--green); background: var(--green-dim); }
.pill-accent { color: var(--accent); background: var(--accent-light); }
.pill-amber { color: var(--amber); background: var(--amber-dim); }
.pill-blue { color: var(--blue); background: var(--blue-dim); }
.pill-rose { color: var(--rose); background: var(--rose-dim); }

/* ── Check Row ───────────────────────────────────────────── */
.check-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 0; font-size: 14px;
}
.check-icon {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 6px;
  flex-shrink: 0;
}
.check-pass { color: var(--green); background: var(--green-dim); }
.check-warn { color: var(--amber); background: var(--amber-dim); }
.check-fail { color: var(--rose); background: var(--rose-dim); }

/* ── Callout ─────────────────────────────────────────────── */
.callout {
  padding: 14px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px; line-height: 1.7;
  border-left: 3px solid;
}
.callout-tip {
  background: var(--green-bg);
  border-color: var(--green);
  color: var(--text);
}
.callout-tip .callout-label { color: var(--green); }
.callout-info {
  background: var(--blue-bg);
  border-color: var(--blue);
  color: var(--text);
}
.callout-info .callout-label { color: var(--blue); }
.callout-warning {
  background: var(--amber-bg);
  border-color: var(--amber);
  color: var(--text);
}
.callout-warning .callout-label { color: var(--amber); }
.callout-error {
  background: var(--rose-bg);
  border-color: var(--rose);
  color: var(--text);
}
.callout-error .callout-label { color: var(--rose); }
.callout-label {
  font-weight: 700; font-size: 12px;
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 4px;
}

/* ── Timeline ────────────────────────────────────────────── */
.timeline { position: relative; padding-left: 28px; }
.timeline::before {
  content: ''; position: absolute;
  left: 7px; top: 6px; bottom: 6px;
  width: 2px; background: var(--border);
}
.timeline-item { position: relative; margin-bottom: 14px; font-size: 14px; }
.timeline-item:last-child { margin-bottom: 0; }
.timeline-item::before {
  content: ''; position: absolute;
  left: -22px; top: 8px;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--accent);
}
.timeline-item.green::before { background: var(--green); }
.timeline-item.amber::before { background: var(--amber); }
.timeline-item.rose::before { background: var(--rose); }
.timeline-item-time {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px; color: var(--text-dim);
}
.timeline-item-duration {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px; color: var(--text-dim);
  background: var(--surface2);
  padding: 2px 6px; border-radius: 4px;
  margin-left: 6px;
}
.timeline-legend {
  display: flex; gap: 16px; flex-wrap: wrap;
  padding-top: 14px; margin-top: 14px;
  border-top: 1px solid var(--border);
  font-size: 12px; color: var(--text-dim);
}
.timeline-legend-item {
  display: flex; align-items: center; gap: 6px;
}
.timeline-legend-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}

/* ── Allocation Bar ──────────────────────────────────────── */
.allocation-bar {
  display: flex; height: 28px;
  border-radius: 8px; overflow: hidden; margin-bottom: 8px;
}
.allocation-segment { height: 100%; transition: opacity 0.15s; }

/* ── Bar Chart ───────────────────────────────────────────── */
.bar-row {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 10px; font-size: 14px;
}
.bar-label {
  flex: 0 0 180px; text-align: right;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.bar-track {
  flex: 1; height: 22px; border-radius: 6px;
  background: var(--surface2); overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 6px;
  background: var(--accent); transition: width 0.4s ease;
}
.bar-count {
  flex: 0 0 50px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px; font-weight: 600; color: var(--text-dim);
}

/* ── Decision / Learning Items ───────────────────────────── */
.dl-item {
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}
.dl-item:last-child { border-bottom: none; }
.dl-item-title {
  font-weight: 600; font-size: 14px;
  margin-bottom: 4px;
  display: flex; align-items: center; gap: 8px;
}
.dl-item-row {
  display: flex; gap: 10px;
  font-size: 14px; color: var(--text-dim);
  margin-bottom: 2px;
}
.dl-item-label {
  font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--text-muted);
  flex-shrink: 0; min-width: 80px;
}
.dl-sub-detail {
  padding-left: 16px; margin-top: 4px;
}
.dl-sub-line {
  display: flex; gap: 8px;
  font-size: 13px; color: var(--text-dim); line-height: 1.6;
}
.dl-sub-label {
  font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--text-muted);
  flex-shrink: 0; min-width: 72px; padding-top: 1px;
}

/* ── Item List ───────────────────────────────────────────── */
.item-list { list-style: none; }
.item-list li {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; font-size: 14px; line-height: 1.7;
  border-bottom: 1px solid var(--border);
}
.item-list li:last-child { border-bottom: none; }

/* ── Next Card ───────────────────────────────────────────── */
.next-card {
  background: var(--accent-light);
  border: 1px solid var(--accent-mid);
  border-radius: 12px;
  padding: 20px;
}
.next-card-title {
  font-weight: 600; font-size: 15px;
  color: var(--accent); margin-bottom: 4px;
}
.next-card-body {
  font-size: 14px; color: var(--text-dim);
}

/* ── Signpost Banner ─────────────────────────────────────── */
.signpost {
  position: relative;
  text-align: center;
  margin: 32px 0 24px;
  padding: 16px 0;
}
.signpost::before {
  content: '';
  position: absolute; top: 50%; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--amber), transparent);
}
.signpost-text {
  position: relative;
  display: inline-block;
  background: var(--bg);
  padding: 6px 20px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--amber);
}

/* ── Bug Card ────────────────────────────────────────────── */
.bug-card {
  background: var(--rose-bg);
  border: 1px solid var(--rose-border);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 10px;
}
.bug-card-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.bug-card-title { font-size: 14px; font-weight: 600; color: var(--rose); }

/* ── Elapsed Timer ───────────────────────────────────────── */
.elapsed {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px; font-weight: 500;
  color: var(--text-dim);
  display: inline-flex; align-items: center; gap: 6px;
}
.elapsed-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── Env Strip ───────────────────────────────────────────── */
.env-strip {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 12px; margin-bottom: 24px;
}
.env-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
}
.env-card:hover { border-color: var(--accent); }
.env-card-label {
  font-size: 11px; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 2px; font-weight: 500;
}
.env-card-value {
  font-size: 14px; font-weight: 600;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

/* ── Sign-off ────────────────────────────────────────────── */
.signoff-feature {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  background: var(--surface);
}
.signoff-feature-name {
  font-weight: 600; font-size: 15px;
  margin-bottom: 4px;
}
.signoff-feature-desc {
  font-size: 14px; color: var(--text-dim);
  margin-bottom: 10px;
}
.signoff-checklist { list-style: none; padding: 0; }
.signoff-checklist li {
  font-size: 14px; padding: 4px 0;
  display: flex; align-items: center; gap: 8px;
}
.signoff-check {
  width: 16px; height: 16px;
  border: 2px solid var(--border);
  border-radius: 4px;
  flex-shrink: 0;
}

/* ── Manual Check Items ──────────────────────────────────── */
.manual-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.manual-item:last-child { border-bottom: none; }
.state-toggle {
  width: 24px; height: 24px;
  border: 2px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
  transition: all 0.15s;
  margin-top: 2px;
}
.state-toggle:hover { border-color: var(--text-dim); }
.state-toggle.pass {
  background: var(--green); border-color: var(--green);
}
.state-toggle.pass::before {
  content: '';
  position: absolute; top: 4px; left: 7px;
  width: 6px; height: 10px;
  border: solid white; border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.state-toggle.fail {
  background: var(--rose); border-color: var(--rose);
}
.state-toggle.fail::before,
.state-toggle.fail::after {
  content: '';
  position: absolute; top: 4px; left: 9px;
  width: 2px; height: 12px;
  background: white;
}
.state-toggle.fail::before { transform: rotate(45deg); }
.state-toggle.fail::after { transform: rotate(-45deg); }
.manual-item-content { flex: 1; }
.manual-item-title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.manual-item-desc { font-size: 13px; color: var(--text-dim); }

/* ── Code Block ──────────────────────────────────────────── */
.code-block {
  background: var(--code-bg);
  padding: 16px 20px;
  border-radius: 8px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  color: var(--code-text);
  overflow-x: auto;
  line-height: 1.6;
}

/* ── Footer ──────────────────────────────────────────────── */
.page-footer {
  text-align: center;
  padding: 32px 0 16px;
  border-top: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 700px) {
  .env-strip { grid-template-columns: 1fr; }
  .bar-label { flex: 0 0 120px; font-size: 13px; }
}
@media (max-width: 480px) {
  .container { padding: 24px 16px 40px; }
  .page-title { font-size: 24px; }
  .section-title { font-size: 18px; }
}
"""


def theme_toggle_css():
    """CSS for the light/dark mode toggle widget. Include separately if needed."""
    return """\
/* ── Theme Toggle ────────────────────────────────────────── */
.theme-toggle {
  position: fixed; top: 16px; right: 16px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 24px; padding: 5px 10px;
  display: flex; align-items: center; gap: 6px;
  cursor: pointer; z-index: 1000; font-size: 13px; user-select: none;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
}
.theme-toggle:hover { border-color: var(--accent); box-shadow: var(--shadow-md); }
.toggle-option { font-size: 14px; line-height: 1; }
.toggle-switch {
  width: 32px; height: 18px; border-radius: 9px;
  background: var(--border); position: relative; transition: background 0.2s;
}
.toggle-switch::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--accent); transition: transform 0.2s;
}
[data-theme="dark"] .toggle-switch::after { transform: translateX(14px); }
"""


def theme_toggle_js():
    """JavaScript for theme toggle. Call after the toggle HTML is in the DOM."""
    return """\
(function() {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;
  const html = document.documentElement;
  const saved = localStorage.getItem('doe-theme');
  if (saved) html.setAttribute('data-theme', saved);
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    html.setAttribute('data-theme', 'dark');
  toggle.addEventListener('click', function() {
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('doe-theme', next);
  });
})();
"""


def collapsible_js():
    """JavaScript for collapsible cards. Include when using collapsible=True."""
    return """\
document.querySelectorAll('.card-collapsible .card-header').forEach(function(h) {
  h.addEventListener('click', function() {
    h.closest('.card-collapsible').classList.toggle('collapsed');
  });
});
"""


# ── Page Scaffold ───────────────────────────────────────────────────────────

def page_scaffold(title, body, *, css='', js='', theme_toggle=True):
    """Build a complete HTML document.

    Args:
        title: Page title (shown in browser tab).
        body: HTML string for the page body.
        css: Additional CSS to include after base styles.
        js: Additional JavaScript to include before </body>.
        theme_toggle: Include light/dark mode toggle widget and JS.

    Returns:
        Complete HTML document as a string.
    """
    toggle_css = theme_toggle_css() if theme_toggle else ''
    toggle_html = (
        '<div class="theme-toggle" id="themeToggle" title="Toggle theme">'
        '<span class="toggle-option">&#9728;&#65039;</span>'
        '<span class="toggle-switch"></span>'
        '<span class="toggle-option">&#127769;</span>'
        '</div>'
    ) if theme_toggle else ''
    toggle_js = theme_toggle_js() if theme_toggle else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<style>
{base_css()}
{toggle_css}
{css}
</style>
</head>
<body>
{toggle_html}
{body}
<script>
{toggle_js}
{js}
</script>
</body>
</html>"""


# ── Component Functions ─────────────────────────────────────────────────────
# Parameters named "text", "title", "label", "name", "desc" are auto-escaped.
# Parameters named "body" or documented as "HTML" accept raw HTML.
# Use esc() explicitly for data-derived strings in raw-HTML parameters.

class _RawHTML:
    """Wrapper to mark a string as pre-escaped HTML for data_table cells."""
    __slots__ = ('html',)
    def __init__(self, html):
        self.html = html
    def __str__(self):
        return self.html


def raw(html):
    """Mark an HTML string as safe for insertion into data_table cells.

    Use this when a cell should contain pre-built HTML (e.g. a badge):
        data_table(['Name', 'Status'], [['foo', raw(badge('PASS', 'pass'))]])
    """
    return _RawHTML(html)


def esc(text):
    """HTML-escape text. Use for any user-supplied or data-derived strings."""
    return _esc(str(text))


def badge(text, variant='info'):
    """Status badge pill.

    Variants: pass, fail, warn, info, accent, dim.
    """
    return f'<span class="badge badge-{esc(variant)}">{esc(text)}</span>'


def card(body, *, title='', meta='', collapsible=False, collapsed=False):
    """Bordered card with optional header.

    Args:
        body: HTML content for the card body.
        title: Card title (plain text, escaped).
        meta: Right-side metadata (plain text, escaped).
        collapsible: Make the card collapsible with click-to-toggle.
        collapsed: Start collapsed (only if collapsible=True).
    """
    cls = 'card'
    if collapsible:
        cls += ' card-collapsible'
        if collapsed:
            cls += ' collapsed'

    header = ''
    if title or meta:
        chevron = '<span class="card-chevron">&#9660;</span>' if collapsible else ''
        meta_html = f'<span class="card-meta">{esc(meta)}</span>' if meta else ''
        header = (
            f'<div class="card-header">'
            f'<span class="card-title">{esc(title)}</span>'
            f'{meta_html}'
            f'{chevron}'
            f'</div>'
        )

    if collapsible:
        return (
            f'<div class="{cls}">'
            f'{header}'
            f'<div class="card-collapse-body"><div class="card-body">{body}</div></div>'
            f'</div>'
        )

    return (
        f'<div class="{cls}">'
        f'{header}'
        f'<div class="card-body">{body}</div>'
        f'</div>'
    )


def metric_grid(metrics, columns=3):
    """Grid of metric cards.

    Args:
        metrics: List of (value, label) or (value, label, color) tuples.
            color is a CSS colour string applied to the value.
        columns: Number of grid columns (2-6).
    """
    cards = []
    for m in metrics:
        val, label = m[0], m[1]
        color = m[2] if len(m) > 2 else None
        style = f' style="color: {esc(color)};"' if color else ''
        cards.append(
            f'<div class="metric-card">'
            f'<div class="metric-value"{style}>{esc(val)}</div>'
            f'<div class="metric-label">{esc(label)}</div>'
            f'</div>'
        )
    return (
        f'<div class="metric-grid metric-grid-{columns}">'
        f'{"".join(cards)}'
        f'</div>'
    )


def progress_bar(label, value, total, *, variant='pass', right_label=None, stats=None,
                 segments=None):
    """Progress bar with label.

    Args:
        label: Left label text.
        value: Filled amount.
        total: Total amount (for calculating percentage).
        variant: Fill colour variant (pass/fail/warn/accent).
        right_label: Right-side label text. Defaults to "value / total".
        stats: List of stat strings shown below the bar.
        segments: List of (value, variant) for multi-segment bars. Overrides
            value/variant if provided.
    """
    pct = (value / total * 100) if total > 0 else 0
    right = right_label or f'{value} / {total}'

    if segments:
        fills = ''.join(
            f'<div class="progress-fill {esc(v)}" style="width:{(n/total*100) if total else 0:.1f}%"></div>'
            for n, v in segments
        )
    else:
        fills = f'<div class="progress-fill {esc(variant)}" style="width:{pct:.1f}%"></div>'

    stats_html = ''
    if stats:
        stats_html = '<div class="progress-stats">' + ''.join(
            f'<span>{esc(s)}</span>' for s in stats
        ) + '</div>'

    return (
        f'<div class="progress">'
        f'<div class="progress-label"><span>{esc(label)}</span>'
        f'<span style="color: var(--text-dim);">{esc(right)}</span></div>'
        f'<div class="progress-track">{fills}</div>'
        f'{stats_html}'
        f'</div>'
    )


def data_table(headers, rows, *, mono_cols=None):
    """Striped data table.

    Args:
        headers: List of column header strings.
        rows: List of row tuples/lists (each matching headers length).
            Cell values are escaped by default. To include raw HTML in a
            cell, pass it through ``raw()``.
        mono_cols: Set of column indices that should use monospace font.
    """
    mono = mono_cols or set()
    th = ''.join(f'<th>{esc(h)}</th>' for h in headers)
    trs = []
    for row in rows:
        tds = []
        for i, cell in enumerate(row):
            cls = ' class="mono"' if i in mono else ''
            # Cells wrapped in _RawHTML are inserted as-is; all others are escaped
            content = str(cell) if isinstance(cell, _RawHTML) else esc(cell)
            tds.append(f'<td{cls}>{content}</td>')
        trs.append(f'<tr>{"".join(tds)}</tr>')
    return (
        f'<table class="table">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(trs)}</tbody>'
        f'</table>'
    )


def section(title, body, *, subtitle='', desc=''):
    """Section wrapper with heading.

    Args:
        title: Section title (plain text).
        body: HTML content.
        subtitle: Optional subtitle below title.
        desc: Optional description paragraph.
    """
    sub = f'<div class="section-subtitle">{esc(subtitle)}</div>' if subtitle else ''
    d = f'<p class="section-desc">{esc(desc)}</p>' if desc else ''
    return (
        f'<div class="section">'
        f'<div class="section-title">{esc(title)}</div>'
        f'{sub}{d}'
        f'{body}'
        f'</div>'
    )


def pill(text, variant='accent'):
    """Small coloured tag. Variants: green, accent, amber, blue, rose."""
    return f'<span class="pill pill-{esc(variant)}">{esc(text)}</span>'


def check_row(text, status='pass'):
    """Status check row. Status: pass, warn, fail.

    Args:
        text: Row content. Accepts raw HTML (e.g. for embedded badges).
            Use esc() on data-derived strings.
        status: Badge variant (pass/warn/fail).
    """
    labels = {'pass': 'PASS', 'warn': 'WARN', 'fail': 'FAIL'}
    return (
        f'<div class="check-row">'
        f'<span class="check-icon check-{esc(status)}">{labels.get(status, status.upper())}</span>'
        f'<span>{text}</span>'
        f'</div>'
    )


def callout(body, variant='info', *, label=''):
    """Bordered callout box. Variants: tip, info, warning, error."""
    default_labels = {'tip': 'Tip', 'info': 'Info', 'warning': 'Warning', 'error': 'Error'}
    lbl = label or default_labels.get(variant, variant.title())
    return (
        f'<div class="callout callout-{esc(variant)}">'
        f'<div class="callout-label">{esc(lbl)}</div>'
        f'{body}'
        f'</div>'
    )


def timeline(items):
    """Vertical timeline.

    Args:
        items: List of dicts with keys: time, text (both escaped), and
            optional color (green/amber/rose) and duration.
    """
    _TIMELINE_COLORS = {'green', 'amber', 'rose'}
    parts = []
    for item in items:
        color = item.get('color', '')
        color_cls = f' {color}' if color in _TIMELINE_COLORS else ''
        dur = (
            f'<span class="timeline-item-duration">{esc(item["duration"])}</span>'
            if item.get('duration') else ''
        )
        parts.append(
            f'<div class="timeline-item{color_cls}">'
            f'<div class="timeline-item-time">{esc(item["time"])}{dur}</div>'
            f'<div>{esc(item["text"])}</div>'
            f'</div>'
        )
    return f'<div class="timeline">{"".join(parts)}</div>'


def timeline_legend(items):
    """Legend for timeline colours.

    Args:
        items: List of (color_css, label) tuples.
    """
    parts = []
    for color, label in items:
        parts.append(
            f'<div class="timeline-legend-item">'
            f'<span class="timeline-legend-dot" style="background:{esc(color)};"></span>'
            f'{esc(label)}'
            f'</div>'
        )
    return f'<div class="timeline-legend">{"".join(parts)}</div>'


def stats_bar(items):
    """Inline stats row.

    Args:
        items: List of strings or (icon, text) tuples.
    """
    parts = []
    for item in items:
        if isinstance(item, tuple):
            parts.append(f'<span>{item[0]} {esc(item[1])}</span>')
        else:
            parts.append(f'<span>{esc(item)}</span>')
    return f'<div class="stats-bar">{"".join(parts)}</div>'


def item_list(items):
    """Bordered item list.

    Args:
        items: List of HTML strings (each becomes an <li>).
    """
    lis = ''.join(f'<li>{item}</li>' for item in items)
    return f'<ul class="item-list">{lis}</ul>'


def dl_item(title, rows, *, pills=None):
    """Decision/learning item with label/value rows.

    Args:
        title: Item title (plain text).
        rows: List of (label, value_html) tuples.
        pills: Optional list of (text, variant) tuples shown before the title.
    """
    pill_html = ''
    if pills:
        pill_html = ' '.join(pill(t, v) for t, v in pills)

    row_html = ''.join(
        f'<div class="dl-item-row">'
        f'<span class="dl-item-label">{esc(label)}</span>'
        f'<span>{value}</span>'
        f'</div>'
        for label, value in rows
    )
    return (
        f'<div class="dl-item">'
        f'<div class="dl-item-title">{pill_html} {esc(title)}</div>'
        f'{row_html}'
        f'</div>'
    )


def next_card(title, body):
    """Highlighted "what's next" card."""
    return (
        f'<div class="next-card">'
        f'<div class="next-card-title">{esc(title)}</div>'
        f'<div class="next-card-body">{body}</div>'
        f'</div>'
    )


def bar_chart(rows, *, label_width=180):
    """Horizontal bar chart.

    Args:
        rows: List of (label, value, max_value) or (label, value, max_value, color).
        label_width: CSS width for labels in px.
    """
    parts = []
    for r in rows:
        label, value, max_val = r[0], r[1], r[2]
        color = r[3] if len(r) > 3 else None
        pct = (value / max_val * 100) if max_val > 0 else 0
        bg = f'background:{esc(color)};' if color else ''
        parts.append(
            f'<div class="bar-row">'
            f'<span class="bar-label" style="flex:0 0 {label_width}px;">{esc(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="{bg}width:{pct:.1f}%"></div></div>'
            f'<span class="bar-count">{esc(str(value))}</span>'
            f'</div>'
        )
    return ''.join(parts)


def allocation_bar(segments):
    """Segmented allocation bar.

    Args:
        segments: List of (width_pct, color_css) tuples.
    """
    parts = []
    for pct, color in segments:
        parts.append(
            f'<div class="allocation-segment" '
            f'style="width:{pct}%;background:{esc(color)};"></div>'
        )
    return f'<div class="allocation-bar">{"".join(parts)}</div>'


def signpost(text):
    """Horizontal rule with centered label."""
    return (
        f'<div class="signpost">'
        f'<span class="signpost-text">{esc(text)}</span>'
        f'</div>'
    )


def bug_card(title, body, *, header_right=''):
    """Error/bug highlight card (rose background).

    Args:
        title: Card title (escaped).
        body: Card content (raw HTML).
        header_right: Right-side header content (raw HTML, e.g. a badge).
    """
    right = f'<span>{header_right}</span>' if header_right else ''
    return (
        f'<div class="bug-card">'
        f'<div class="bug-card-header">'
        f'<span class="bug-card-title">{esc(title)}</span>'
        f'{right}'
        f'</div>'
        f'<div class="card-body">{body}</div>'
        f'</div>'
    )


def elapsed_timer(text):
    """Animated elapsed time display with pulsing dot."""
    return (
        f'<span class="elapsed">'
        f'<span class="elapsed-dot"></span> {esc(text)}'
        f'</span>'
    )


def env_strip(envs):
    """Environment card strip.

    Args:
        envs: List of (label, value) tuples.
    """
    cards = []
    for label, value in envs:
        cards.append(
            f'<div class="env-card">'
            f'<div class="env-card-label">{esc(label)}</div>'
            f'<div class="env-card-value">{esc(value)}</div>'
            f'</div>'
        )
    return (
        f'<div class="env-strip">'
        f'{"".join(cards)}'
        f'</div>'
    )


def signoff_feature(name, desc, checklist):
    """Sign-off feature block with checklist.

    Args:
        name: Feature name.
        desc: Feature description.
        checklist: List of checklist item strings.
    """
    items = ''.join(
        f'<li><span class="signoff-check"></span>{esc(item)}</li>'
        for item in checklist
    )
    return (
        f'<div class="signoff-feature">'
        f'<div class="signoff-feature-name">{esc(name)}</div>'
        f'<div class="signoff-feature-desc">{esc(desc)}</div>'
        f'<ul class="signoff-checklist">{items}</ul>'
        f'</div>'
    )


def code_block(code):
    """Monospace code block with dark background."""
    return f'<pre class="code-block">{esc(code)}</pre>'


def page_footer(text='DOE Report'):
    """Centred page footer."""
    return f'<div class="page-footer">{esc(text)}</div>'


def divider():
    """Horizontal divider line."""
    return '<hr class="divider">'


def step_card(step_num, body):
    """Numbered step card with connector line.

    Args:
        step_num: Step number (shown in circle).
        body: HTML content (typically a card()).
    """
    return (
        f'<div class="step-card" data-step="{esc(str(step_num))}">'
        f'{body}'
        f'</div>'
    )


def badge_row(*badges_html):
    """Row of badges. Pass pre-built badge() HTML strings."""
    return f'<div class="badge-row">{"".join(badges_html)}</div>'


def page_header(label, title, subtitle='', dim_title=''):
    """Page header with label, title, and optional subtitle.

    Args:
        label: Small uppercase label above title.
        title: Main page title.
        subtitle: Description below title.
        dim_title: Dimmed suffix appended to title.
    """
    dim = f' <span class="page-title-dim">{esc(dim_title)}</span>' if dim_title else ''
    sub = f'<p class="page-subtitle">{esc(subtitle)}</p>' if subtitle else ''
    return (
        f'<div class="page-label">{esc(label)}</div>'
        f'<h1 class="page-title">{esc(title)}{dim}</h1>'
        f'{sub}'
    )


def container(body):
    """Centred content container (max-width 900px)."""
    return f'<div class="container">{body}</div>'


def manual_item(title, desc='', *, state=''):
    """Manual check item with pass/fail toggle.

    Args:
        title: Item title.
        desc: Item description.
        state: 'pass', 'fail', or '' (unchecked).
    """
    state_cls = f' {state}' if state in ('pass', 'fail') else ''
    desc_html = f'<div class="manual-item-desc">{esc(desc)}</div>' if desc else ''
    return (
        f'<div class="manual-item">'
        f'<div class="state-toggle{state_cls}"></div>'
        f'<div class="manual-item-content">'
        f'<div class="manual-item-title">{esc(title)}</div>'
        f'{desc_html}'
        f'</div>'
        f'</div>'
    )
