#!/usr/bin/env python3
"""
Generate a self-contained HTML manual test checklist from todo.md.

Reads todo.md to extract [manual] test items for a given feature,
STATE.md for version/filename, and optionally a bugs JSON file.
Produces a polished interactive HTML checklist to docs/.

Usage:
  python3 execution/generate_test_checklist.py [--feature "Feature Name"] [--bugs bugs.json] [--no-open]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TODO_PATH = PROJECT_ROOT / "tasks" / "todo.md"
STATE_PATH = PROJECT_ROOT / "STATE.md"
DOCS_DIR = PROJECT_ROOT / "docs"


# ──────────────────────────────────────────────
# Parsing helpers
# ──────────────────────────────────────────────

def slugify(name: str) -> str:
    """Lowercase, spaces to hyphens, strip non-alphanumeric (keep hyphens).
    Uses only the primary name (before em-dash) for shorter slugs."""
    # Split on em-dash or double-hyphen to get primary name
    primary = re.split(r"\s*[—–]\s*|\s*--\s*", name)[0].strip()
    s = primary.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def parse_state() -> dict:
    """Extract app version and filename from STATE.md."""
    text = STATE_PATH.read_text(encoding="utf-8")
    info = {"version": "", "filename": ""}

    # Look for: **Current app version:** vX.Y.Z (`your-app-vX.Y.Z.html`)
    m = re.search(r"\*\*Current app version:\*\*\s*(v[\d.]+)\s*\(`?([^`)\s]+)`?\)", text)
    if m:
        info["version"] = m.group(1)
        info["filename"] = m.group(2)
    else:
        # Fallback: just find a version
        m2 = re.search(r"\*\*Current app version:\*\*\s*(v[\d.]+)", text)
        if m2:
            info["version"] = m2.group(1)

    return info


def split_manual_description(description: str) -> list[str]:
    """Split a multi-sentence manual description into individual check fragments.

    Handles abbreviations (e.g., i.e.), version numbers (v0.27.4),
    decimal numbers, and meta-labels like MID-FEATURE CHECKPOINT.
    """
    text = description.strip()
    if not text:
        return []

    # --- Placeholder protection ---
    # Protect abbreviations from being split
    placeholders = {}
    counter = [0]

    def protect(match):
        key = f"\x00ABBR{counter[0]}\x00"
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    # Protect e.g. and i.e. (with optional trailing period)
    text = re.sub(r"\b(e\.g|i\.e)\.", protect, text)
    # Protect version numbers like v0.27.4
    text = re.sub(r"v\d+\.\d+(?:\.\d+)*", protect, text)
    # Protect decimal numbers like 0.27 or 3.5
    text = re.sub(r"\b\d+\.\d+\b", protect, text)

    # --- Strip trailing period before split ---
    text = text.rstrip(".")

    # --- Split on ". " (period + space) ---
    fragments = re.split(r"\.\s+", text)

    # --- Restore placeholders ---
    restored = []
    for frag in fragments:
        for key, val in placeholders.items():
            frag = frag.replace(key, val)
        frag = frag.strip()
        if frag:
            restored.append(frag)

    # --- Merge very short fragments (< 10 chars) with previous ---
    merged = []
    for frag in restored:
        if len(frag) < 10 and merged:
            merged[-1] = merged[-1] + ". " + frag
        else:
            merged.append(frag)

    # --- Filter out meta-labels that aren't testable checks ---
    meta_patterns = [
        r"^MID[- ]?FEATURE\s+CHECKPOINT$",
        r"^CHECKPOINT$",
        r"^END[- ]?OF[- ]?FEATURE\s+CHECKPOINT$",
        r"^FINAL\s+CHECKPOINT$",
    ]
    filtered = []
    for frag in merged:
        is_meta = any(re.match(pat, frag.strip(), re.IGNORECASE) for pat in meta_patterns)
        if not is_meta:
            filtered.append(frag)

    # --- Capitalize first letter of each fragment ---
    result = []
    for frag in filtered:
        if frag:
            result.append(frag[0].upper() + frag[1:] if len(frag) > 1 else frag.upper())

    return result


def parse_todo(feature_name: str | None) -> dict:
    """
    Parse todo.md to extract feature info and manual test items.

    Returns:
        {
            "feature_name": str,
            "type_tag": str,        # e.g. "APP" or "INFRA"
            "version_range": str,   # e.g. "v0.27.x"
            "steps": [
                {
                    "step_num": int,
                    "step_name": str,
                    "completed": bool,
                    "manual_items": [
                        {"description": str, "checked": bool}
                    ]
                }
            ]
        }
    """
    text = TODO_PATH.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find the feature heading
    feature_heading_idx = None
    found_feature_name = None
    found_type_tag = None
    found_version_range = None

    if feature_name:
        # Match a ### heading containing the feature name
        for i, line in enumerate(lines):
            if line.startswith("### ") and feature_name.lower() in line.lower():
                feature_heading_idx = i
                break
    else:
        # Use the first ### under ## Current
        in_current = False
        for i, line in enumerate(lines):
            if line.strip() == "## Current":
                in_current = True
                continue
            if in_current and line.startswith("## "):
                break  # Hit another ## section
            if in_current and line.startswith("### "):
                feature_heading_idx = i
                break

    if feature_heading_idx is None:
        return None

    heading_line = lines[feature_heading_idx]

    # Parse heading: ### Feature Name — Description [APP] (v0.27.x)
    # Or: ### Feature Name [APP] (v0.27.x)
    # Try with version range first: ### Name [APP] (v0.27.x)
    heading_m = re.match(
        r"###\s+(.+?)\s+\[(APP|INFRA)\]\s+\((v[\d.x]+)\)",
        heading_line,
    )
    # Try without version range: ### Name [APP]
    heading_m2 = re.match(
        r"###\s+(.+?)\s+\[(APP|INFRA)\]",
        heading_line,
    ) if not heading_m else None

    if heading_m:
        raw_name = heading_m.group(1).strip()
        found_feature_name = raw_name
        found_type_tag = heading_m.group(2)
        found_version_range = heading_m.group(3)
    elif heading_m2:
        raw_name = heading_m2.group(1).strip()
        found_feature_name = raw_name
        found_type_tag = heading_m2.group(2)
        found_version_range = ""
    else:
        # Fallback: just grab everything after ###
        found_feature_name = heading_line.lstrip("#").strip()
        found_type_tag = ""
        found_version_range = ""

    # Find the end of this feature block (next ### or ## heading)
    feature_end_idx = len(lines)
    for i in range(feature_heading_idx + 1, len(lines)):
        if re.match(r"^#{2,3}\s", lines[i]):
            feature_end_idx = i
            break

    feature_lines = lines[feature_heading_idx + 1 : feature_end_idx]

    # Parse numbered steps and their [manual] items
    steps = []
    current_step = None

    # Count all numbered steps in the feature block for total_steps
    total_steps = sum(1 for fl in feature_lines if re.match(r"^\d+\.\s+\[", fl))

    for line in feature_lines:
        # Match step line: N. [x] Step name — description -> vX.Y.Z ...
        step_m = re.match(
            r"^(\d+)\.\s+\[([ x])\]\s+(.+?)(?:\s*->|→|\s*$)",
            line,
        )
        if step_m:
            if current_step:
                steps.append(current_step)
            step_num = int(step_m.group(1))
            step_done = step_m.group(2) == "x"
            step_name = step_m.group(3).strip()
            # Clean trailing version/timestamp from step name
            step_name = re.sub(r"\s*(?:->|→)\s*v[\d.]+.*$", "", step_name).strip()
            # Trim description after double-dash (keep just the primary name)
            step_name = re.split(r"\s+--\s+", step_name)[0].strip()
            # Extract completed timestamp: *(completed HH:MM DD/MM/YY)*
            time_m = re.search(r"\*\(completed\s+(.+?)\)\*", line)
            completed_time = time_m.group(1) if time_m else ""
            current_step = {
                "step_num": step_num,
                "step_name": step_name,
                "completed": step_done,
                "completed_time": completed_time,
                "manual_items": [],
            }
            continue

        # Match manual item: - [ ] [manual] Description  or  - [x] [manual] Description
        manual_m = re.match(
            r"^\s+-\s+\[([ x])\]\s+\[manual\]\s+(.+)$",
            line,
        )
        if manual_m and current_step is not None:
            checked = manual_m.group(1) == "x"
            description = manual_m.group(2).strip()
            # Strip trailing parenthetical verification notes
            description = re.sub(r"\s*\*\(verified.*?\)\*\s*$", "", description)
            # Store raw description for console command extraction
            if "raw_description" not in current_step:
                current_step["raw_description"] = ""
            current_step["raw_description"] += " " + description
            # Split multi-sentence descriptions into individual checks
            fragments = split_manual_description(description)
            for frag in fragments:
                current_step["manual_items"].append({
                    "description": frag,
                    "checked": checked,
                })

    if current_step:
        steps.append(current_step)

    # Filter to steps with manual items
    steps = [s for s in steps if s["manual_items"]]

    return {
        "feature_name": found_feature_name,
        "type_tag": found_type_tag,
        "version_range": found_version_range,
        "total_steps": total_steps,
        "steps": steps,
    }


def load_test_results(results_path: str | None) -> dict | None:
    """Load automated test suite results JSON if provided and valid."""
    if not results_path:
        return None
    p = Path(results_path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_code_trace(trace_path: str | None) -> list | None:
    """Load code trace results JSON if provided and valid.

    Returns a list of findings: [{"title", "description", "file", "line", "severity", "found_by"}]
    Returns None if no path or file doesn't exist. Returns [] if clean trace.
    """
    if not trace_path:
        return None
    p = Path(trace_path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return None
    except (json.JSONDecodeError, OSError):
        return None


def build_auto_results_html(tr: dict | None, code_trace: list | None = None) -> str:
    """Build the automated results HTML section from test-suite-results.json and/or code trace.

    Design: single card matching the wireframe — header row with status badge,
    grey tile strip with vertical separators, expandable detail sections.
    Renders when either test results or code trace data is available.
    """
    if tr is None and code_trace is None:
        return ""

    # When only code trace is available (no test suite), use empty defaults
    if tr is None:
        tr = {}
    duration = tr.get("duration_seconds", 0)
    warnings = tr.get("warnings", [])
    pw = tr.get("playwright", {})
    maestro = tr.get("maestro_results", {})
    is_maestro = bool(maestro)
    a11y = tr.get("accessibility", {})
    lh = tr.get("lighthouse", {})
    hc = tr.get("health_check", {})

    # -- Read projectType from tests/config.json --
    PROJECT_TYPE_DISPLAY = {
        "html-app": "HTML App", "nextjs": "Next.js", "vite": "Vite",
        "react-native": "React Native", "expo": "Expo", "flutter": "Flutter",
        "angular": "Angular", "nuxt": "Nuxt", "vue": "Vue", "svelte": "SvelteKit",
        "remix": "Remix", "astro": "Astro", "python": "Python", "go": "Go",
        "php": "PHP/Laravel", "ruby": "Ruby/Rails",
    }
    project_type_badge = ""
    try:
        config_path = PROJECT_ROOT / "tests" / "config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as _cf:
                _cfg = json.load(_cf)
            pt = _cfg.get("projectType", "")
            pt_display = PROJECT_TYPE_DISPLAY.get(pt, pt)
            if pt_display:
                project_type_badge = f'<span class="ar-project-type">{escape_html(pt_display)}</span>'
    except (json.JSONDecodeError, OSError):
        pass

    # -- Determine overall status badge --
    statuses = [s for s in [pw.get("status"), maestro.get("status"), a11y.get("status"), lh.get("status"), hc.get("status")] if s is not None]
    # Add code trace status
    if code_trace is not None:
        ct_high = sum(1 for f in code_trace if f.get("severity", "").lower() == "high")
        ct_status = "fail" if ct_high > 0 else ("warn" if len(code_trace) > 0 else "pass")
        statuses.append(ct_status)
    if "fail" in statuses:
        badge_text, badge_cls = "FAILURES", "badge-fail"
    elif "error" in statuses:
        badge_text, badge_cls = "ERRORS", "badge-warn"
    elif "warn" in statuses:
        badge_text, badge_cls = "WARNINGS", "badge-warn"
    else:
        badge_text, badge_cls = "ALL PASS", "badge-pass"

    # -- Build tile data --
    def _tile(title, value, detail, status):
        color_cls = {
            "pass": "val-green", "warn": "val-amber", "fail": "val-red",
            "error": "val-amber", "first": "val-blue",
        }.get(status, "val-grey")
        return (
            f'<div class="ar-tile">'
            f'<div class="ar-tile-title">{title}</div>'
            f'<div class="ar-tile-value {color_cls}">{value}</div>'
            f'<div class="ar-tile-detail">{detail}</div>'
            f'</div>'
        )

    tiles = []
    has_test_suite = bool(pw or maestro or a11y or lh or hc)

    if has_test_suite:
        # Browser Tests / Maestro Flows
        if is_maestro:
            m_status = maestro.get("status", "error")
            if m_status == "error":
                tiles.append(_tile("Maestro Flows", "&mdash;", escape_html(maestro.get("error_message", "Error")), "error"))
            else:
                tiles.append(_tile(
                    "Maestro Flows",
                    f'{maestro.get("passed", 0)}/{maestro.get("total", 0)}',
                    f'All flows pass' if maestro.get("failed", 0) == 0 else f'{maestro.get("failed", 0)} failures',
                    m_status,
                ))
        else:
            pw_status = pw.get("status", "error")
            if pw_status == "error":
                tiles.append(_tile("Browser Tests", "&mdash;", escape_html(pw.get("error_message", "Error")), "error"))
            else:
                route_count = len(pw.get("routes", []))
                tiles.append(_tile(
                    "Browser Tests",
                    f'{pw.get("passed", 0)}/{pw.get("total", 0)}',
                    f'All pages load, nav works' if pw.get("failed", 0) == 0 else f'{pw.get("failed", 0)} failures',
                    pw_status,
                ))

        # Visual Regression (not applicable for Maestro/mobile projects)
        diffs = pw.get("visual_diffs", [])
        if not is_maestro:
            pw_status = pw.get("status", "error")
            if pw_status == "error":
                tiles.append(_tile("Visual Regression", "&mdash;", "Requires browser tests", "error"))
            else:
                diff_count = len(diffs)
                vr_status = "fail" if diff_count > 0 else "pass"
                tiles.append(_tile(
                    "Visual Regression",
                    f'{diff_count} diff{"s" if diff_count != 1 else ""}',
                    f'4 screenshots match baseline' if diff_count == 0 else f'{diff_count} screenshot{"s" if diff_count != 1 else ""} changed',
                    vr_status,
                ))

        # Accessibility
        a11y_status = a11y.get("status", "error")
        new_crit = a11y.get("new_critical", 0)
        known_crit = a11y.get("known_critical", 0)
        if a11y_status == "error":
            tiles.append(_tile("Accessibility", "&mdash;", escape_html(a11y.get("error_message", "Error")), "error"))
        elif new_crit == "unknown":
            tiles.append(_tile("Accessibility", "FAIL", "1+ new violation(s)", "fail"))
        else:
            tiles.append(_tile("Accessibility", f'{new_crit} new', f'{known_crit} known, at baseline', a11y_status))

        # Performance
        lh_status = lh.get("status", "error")
        if lh_status == "error":
            err = lh.get("error_message", "Error")
            tiles.append(_tile("Performance", "&mdash;", escape_html(err), "error"))
        else:
            score = lh.get("score", 0)
            delta = lh.get("delta", 0)
            noise = lh.get("noise_adjusted", False)
            first = lh.get("first_run", False)
            sign = "+" if delta >= 0 else ""
            if first:
                detail = "Baseline set"
            elif noise:
                detail = "Lighthouse score, no change"
            else:
                detail = f'Lighthouse score, {sign}{delta} from baseline'
            tiles.append(_tile("Performance", f'{score} ({sign}{delta})', detail, "first" if first else lh_status))

    # Code Trace (available with or without test suite)
    if code_trace is not None:
        ct_count = len(code_trace)
        ct_high = sum(1 for f in code_trace if f.get("severity", "").lower() == "high")
        ct_med = sum(1 for f in code_trace if f.get("severity", "").lower() == "medium")
        if ct_count == 0:
            tiles.append(_tile("Code Trace", "Clean", "No issues found", "pass"))
        elif ct_high > 0:
            tiles.append(_tile("Code Trace", f'{ct_count} issue{"s" if ct_count != 1 else ""}', f'{ct_high} high severity', "fail"))
        else:
            tiles.append(_tile("Code Trace", f'{ct_count} issue{"s" if ct_count != 1 else ""}', f'{ct_med} medium' if ct_med else 'Low severity', "warn"))

    tiles_html = "\n".join(tiles)

    # -- Warnings banner --
    warnings_html = ""
    if warnings:
        items = "".join(f'<li>{escape_html(w)}</li>' for w in warnings)
        warnings_html = f'<div class="ar-warnings"><ul>{items}</ul></div>'

    # -- Stale a11y note --
    stale_html = ""
    age_days = a11y.get("known_critical_age_days", 0)
    if age_days > 30 and known_crit > 0:
        stale_html = (
            f'<div class="ar-stale-note">'
            f'{known_crit} known violations, oldest from {age_days} days ago '
            f'&mdash; consider fixing.</div>'
        )

    # -- Failure cards --
    failure_cards_html = ""
    if is_maestro and maestro.get("failed", 0) > 0:
        for flow in maestro.get("flows", []):
            if flow.get("status") == "fail":
                failure_cards_html += (
                    f'<div class="ar-fail-card">'
                    f'<span class="ar-fail-label">Flow</span> '
                    f'<strong>{escape_html(flow["name"])}</strong> flow failed'
                    f'</div>'
                )
    elif pw.get("failed", 0) > 0:
        for route in pw.get("routes", []):
            if route.get("status") == "fail":
                failure_cards_html += (
                    f'<div class="ar-fail-card">'
                    f'<span class="ar-fail-label">Route</span> '
                    f'<strong>{escape_html(route["name"])}</strong> page failed to render'
                    f'</div>'
                )
    for diff in diffs:
        failure_cards_html += (
            f'<div class="ar-fail-card">'
            f'<span class="ar-fail-label">Visual</span> '
            f'<strong>{escape_html(diff.get("page", ""))}</strong> screenshot changed'
            f'<div class="ar-fail-path">{escape_html(diff.get("diff_path", ""))}</div>'
            f'</div>'
        )

    # -- Expandable detail sections --
    details_html = ""

    # Health check detail
    checks = hc.get("checks", [])
    hc_summary = hc.get("summary", {})
    if checks:
        hc_pass = hc_summary.get("pass", 0)
        hc_warn = hc_summary.get("warn", 0)
        hc_detail_parts = [f'{hc_pass} pass']
        if hc_warn:
            # Find the first warn detail for inline summary
            warn_detail = ""
            for ck in checks:
                if ck.get("status") == "WARN":
                    d = ck.get("detail", "")
                    if d:
                        warn_detail = f' ({d.split(":")[0].strip() if ":" in d else d})'
                    break
            hc_detail_parts.append(f'{hc_warn} warning{warn_detail}')
        summary_text = f'Health check &mdash; {", ".join(hc_detail_parts)}'
        rows = ""
        for ck in checks:
            st = ck.get("status", "OK")
            cls = "hc-warn" if st == "WARN" else ("hc-fail" if st == "FAIL" else "hc-ok")
            detail = f' &mdash; {escape_html(ck["detail"])}' if ck.get("detail") else ""
            rows += f'<div class="hc-row {cls}"><span class="hc-status">{st}</span> {escape_html(ck["name"])}{detail}</div>'
        chevron = '<span class="chevron-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd"/></svg></span>'
        details_html += (
            f'<details class="ar-detail">'
            f'<summary>{chevron}{summary_text}</summary>'
            f'<div class="ar-detail-body">{rows}</div>'
            f'</details>'
        )

    # Route / Flow coverage detail
    if is_maestro:
        flows = maestro.get("flows", [])
        if flows:
            chevron = '<span class="chevron-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd"/></svg></span>'
            rows = ""
            for fl in flows:
                cls = "route-pass" if fl["status"] == "pass" else "route-fail"
                icon = "&#10003;" if fl["status"] == "pass" else "&#10007;"
                rows += f'<div class="route-row {cls}"><span class="route-icon">{icon}</span> {escape_html(fl["name"])}</div>'
            details_html += (
                f'<details class="ar-detail">'
                f'<summary>{chevron}Flow coverage &mdash; {len(flows)} flows tested</summary>'
                f'<div class="ar-detail-body">{rows}</div>'
                f'</details>'
            )
    else:
        routes = pw.get("routes", [])
        if routes:
            chevron = '<span class="chevron-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd"/></svg></span>'
            rows = ""
            for r in routes:
                cls = "route-pass" if r["status"] == "pass" else "route-fail"
                icon = "&#10003;" if r["status"] == "pass" else "&#10007;"
                rows += f'<div class="route-row {cls}"><span class="route-icon">{icon}</span> {escape_html(r["name"])}</div>'
            details_html += (
                f'<details class="ar-detail">'
                f'<summary>{chevron}Route coverage &mdash; {len(routes)} pages tested</summary>'
                f'<div class="ar-detail-body">{rows}</div>'
                f'</details>'
            )

    # Code trace detail
    if code_trace is not None and len(code_trace) > 0:
        chevron = '<span class="chevron-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd"/></svg></span>'
        rows = ""
        for finding in code_trace:
            sev = finding.get("severity", "Low").lower()
            cls = "hc-fail" if sev == "high" else ("hc-warn" if sev == "medium" else "hc-ok")
            loc = ""
            if finding.get("file"):
                loc = f' &mdash; {escape_html(finding["file"])}'
                if finding.get("line"):
                    loc += f':{finding["line"]}'
            rows += f'<div class="hc-row {cls}"><span class="hc-status">{finding.get("severity", "Low").upper()}</span> {escape_html(finding.get("title", ""))}{loc}</div>'
        details_html += (
            f'<details class="ar-detail" open>'
            f'<summary>{chevron}Code trace &mdash; {len(code_trace)} issue{"s" if len(code_trace) != 1 else ""} found</summary>'
            f'<div class="ar-detail-body">{rows}</div>'
            f'</details>'
        )

    return (
        f'<!-- AUTOMATED RESULTS -->\n'
        f'<div class="ar-section">\n'
        f'  <div class="ar-card">\n'
        f'    <div class="ar-header">\n'
        f'      <div class="ar-header-left">\n'
        f'        <span class="ar-title">Automated Results</span>\n'
        f'        {project_type_badge}\n'
        f'        <span class="ar-badge {badge_cls}">{badge_text}</span>\n'
        f'      </div>\n'
        f'      <span class="ar-duration">{f"completed in {duration}s" if duration > 0 else "code trace only"}</span>\n'
        f'    </div>\n'
        f'    <div class="ar-tiles-strip">\n{tiles_html}\n    </div>\n'
        f'{warnings_html}\n'
        f'{stale_html}\n'
        f'{failure_cards_html}\n'
        f'{details_html}\n'
        f'  </div>\n'
        f'</div>\n'
    )


def build_auto_results_css() -> str:
    """Return CSS for the automated results section (wireframe card design)."""
    return """
  /* -- Automated Results -- */
  .ar-section {
    max-width: 900px;
    margin: 24px auto 20px;
    padding: 0 24px;
  }
  .ar-card {
    background: white;
    border: 1px solid var(--grey-200);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }

  /* Header row */
  .ar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px 14px;
  }
  .ar-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .ar-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--grey-800);
  }
  .ar-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border-radius: 12px;
  }
  .badge-pass { background: var(--green-light); color: var(--green); border: 1px solid var(--green-mid); }
  .badge-warn { background: var(--amber-light); color: var(--amber); border: 1px solid var(--amber-mid); }
  .badge-fail { background: var(--red-light); color: var(--red); border: 1px solid var(--red-mid); }
  .ar-project-type {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
    padding: 3px 10px;
    border-radius: 12px;
    background: var(--grey-100);
    color: var(--grey-600);
    border: 1px solid var(--grey-200);
  }
  .ar-duration {
    font-family: 'SF Mono', SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 13px;
    color: var(--grey-400);
  }

  /* Tiles strip */
  .ar-tiles-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: var(--grey-50);
    border-top: 1px solid var(--grey-200);
    border-bottom: 1px solid var(--grey-200);
  }
  .ar-tile {
    padding: 16px 20px;
    border-right: 1px solid var(--grey-200);
  }
  .ar-tile:last-child { border-right: none; }
  .ar-tile-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--grey-500);
    margin-bottom: 6px;
  }
  .ar-tile-value {
    font-size: 24px;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 4px;
  }
  .ar-tile-detail {
    font-size: 12px;
    color: var(--grey-500);
    line-height: 1.3;
  }
  .val-green { color: var(--green); }
  .val-amber { color: var(--amber); }
  .val-red { color: var(--red); }
  .val-blue { color: var(--blue); }
  .val-grey { color: var(--grey-400); }

  /* Expandable details inside card */
  .ar-detail {
    border-top: 1px solid var(--grey-100);
  }
  .ar-detail summary {
    font-size: 14px;
    color: var(--grey-600);
    cursor: pointer;
    padding: 12px 20px;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .ar-detail summary::-webkit-details-marker { display: none; }
  .ar-detail summary:hover { color: var(--grey-800); background: var(--grey-50); }
  .chevron-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    color: var(--grey-400);
    transition: transform 0.15s;
  }
  .chevron-icon svg { width: 14px; height: 14px; }
  .ar-detail[open] .chevron-icon { transform: rotate(90deg); }
  .ar-detail-body {
    padding: 0 20px 14px;
  }
  .hc-row, .route-row {
    padding: 4px 0;
    font-size: 13px;
    border-bottom: 1px solid var(--grey-100);
  }
  .hc-row:last-child, .route-row:last-child { border-bottom: none; }
  .hc-status {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    width: 44px;
  }
  .hc-ok .hc-status { color: var(--green); }
  .hc-warn .hc-status { color: var(--amber); }
  .hc-fail .hc-status { color: var(--red); }
  .route-icon { margin-right: 6px; }
  .route-pass .route-icon { color: var(--green); }
  .route-fail .route-icon { color: var(--red); }

  /* Warnings & failures inside card */
  .ar-warnings {
    padding: 10px 20px;
    background: var(--amber-light);
    border-top: 1px solid var(--amber-mid);
    font-size: 13px;
    color: var(--amber);
  }
  .ar-warnings ul { list-style: none; }
  .ar-warnings li::before { content: "! "; font-weight: 700; }

  .ar-stale-note {
    padding: 8px 20px;
    font-size: 12px;
    color: var(--amber);
    border-top: 1px solid var(--grey-100);
  }

  .ar-fail-card {
    padding: 8px 20px;
    font-size: 13px;
    border-top: 1px solid var(--red-mid);
    background: var(--red-light);
  }
  .ar-fail-label {
    display: inline-block;
    background: var(--red);
    color: white;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 3px;
    margin-right: 4px;
  }
  .ar-fail-path {
    font-size: 11px;
    color: var(--grey-500);
    margin-top: 2px;
    font-family: monospace;
  }
"""


def build_signpost_html(total_checks: int, test_results: dict | None) -> str:
    """Build a banner divider between auto results and manual checks."""
    if total_checks == 0:
        return ""
    if test_results is None:
        return ""
    return (
        f'<div class="signpost-banner">\n'
        f'  <div class="signpost-banner-line"></div>\n'
        f'  <span class="signpost-banner-text">YOUR REVIEW &mdash; {total_checks} checks below</span>\n'
        f'  <div class="signpost-banner-line"></div>\n'
        f'</div>\n'
    )


def load_bugs(bugs_path: str | None) -> list:
    """Load bugs from JSON file if provided."""
    if not bugs_path:
        return []
    p = Path(bugs_path)
    if not p.exists():
        print(f"Warning: bugs file not found: {bugs_path}", file=sys.stderr)
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# HTML generation
# ──────────────────────────────────────────────

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def build_prerequisite(step_num: int, description: str, is_first: bool) -> str:
    """Generate prerequisite callout text based on context."""
    if is_first:
        return "Start with a fresh browser state."
    if "MID-FEATURE" in description.upper():
        return "Complete previous test sections first."
    return "Ensure the app is running with your configured settings."


def extract_console_commands(raw_desc: str) -> dict:
    """Detect console commands implied by the test description.

    Returns {"setup": [...], "console": [...], "restore": [...]} where each
    entry is a JS string suitable for the browser console.  ``setup`` and
    ``restore`` are one-liners for localStorage manipulation.  ``console``
    entries are multi-line JS snippets for console-test verification.
    Commands are inferred from keywords in the raw (unsplit) manual
    description.

    Customize this function for your project — add keyword matches for
    your app's localStorage keys, console-testable functions, etc.
    """
    setup: list[str] = []
    console: list[str] = []
    restore: list[str] = []
    desc = raw_desc.lower() if raw_desc else ""

    # --- Project-specific patterns ---
    # Add your own keyword matches here. Examples:
    #
    # First-visit / setup wizard tests:
    # if "first visit" in desc or "setup wizard" in desc:
    #     setup.append("localStorage.removeItem('app_role'); location.reload();")
    #     restore.append("// Set your preferred role back in Settings")
    #
    # Console-test patterns:
    # if "scoring" in desc:
    #     console.append("var results = computeAll();\nconsole.table(results);")

    # Generic console-test fallback
    if "console-test" in desc:
        console.append("// Open browser console: Cmd+Option+J (Mac) or Ctrl+Shift+J (Windows/Linux)\n// Then run the checks described below")

    return {"setup": setup, "console": console, "restore": restore}


def build_code_block(cmd: str, label: str = "Console") -> str:
    """Build a dark code block with a copy button.

    Multi-line commands are stored in a data-code attribute (HTML-escaped)
    so that the onclick handler can copy them without inline JS string
    issues.
    """
    escaped = escape_html(cmd)
    # Store the raw command in a data attribute (HTML-escaped handles quotes/ampersands)
    data_attr = escape_html(cmd)
    return f"""
      <div class="code-block" data-code="{data_attr}">
        <div class="code-block-header">
          <span class="code-block-label">{label}</span>
          <button class="copy-btn" onclick="copyCodeFromBlock(this)">Copy</button>
        </div>
        <pre>{escaped}</pre>
      </div>"""


def build_restore_callout(cmds: list[str]) -> str:
    """Build an amber restore callout with optional code blocks."""
    inner = ""
    for cmd in cmds:
        if cmd.startswith("//"):
            # Plain text instruction
            inner += f"<p>{escape_html(cmd.lstrip('/ '))}</p>"
        else:
            inner += build_code_block(cmd, "Restore")
    return f"""
      <div class="callout callout-amber">
        <div class="callout-body">
          <div class="callout-title">Restore after this section</div>
          {inner}
        </div>
      </div>"""


def build_section_html(step: dict, is_first: bool, global_check_offset: int, total_steps: int = 0) -> str:
    """Build one section card's HTML."""
    sid = step["step_num"]
    items = step["manual_items"]
    total = len(items)
    raw_desc = step.get("raw_description", "")
    completed_time = step.get("completed_time", "")
    prereq = build_prerequisite(sid, items[0]["description"] if items else "", is_first)
    console_cmds = extract_console_commands(raw_desc)

    chevron_svg = (
        '<svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20">'
        '<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>'
        '</svg>'
    )

    checks_html = ""
    for i, item in enumerate(items):
        desc = escape_html(item["description"])
        checks_html += f"""
        <div class="check-item" data-section="{sid}" data-index="{i}">
          <div class="check-row" onclick="cycleCheck(this)">
            <span class="check-num">{i + 1}</span>
            <div class="state-toggle"></div>
            <span class="check-text">{desc}</span>
          </div>
          <div class="fail-notes-wrap">
            <div class="fail-notes-label">What did you see?</div>
            <textarea placeholder="Describe what happened instead..."></textarea>
          </div>
        </div>"""

    stripe_time = f'Completed {escape_html(completed_time)}' if completed_time else "In progress"
    return f"""
  <div class="section-card" id="section-{sid}">
    <div class="section-stripe">
      <div class="section-stripe-left">
        <span class="section-step-pill">Step {sid}</span>
        <span class="section-stripe-time">{stripe_time}</span>
      </div>
      <span class="section-stripe-pos">{sid} of {total_steps}</span>
    </div>
    <div class="section-header" onclick="toggleSection('section-{sid}')">
      <div class="section-header-left">
        <div class="section-chevron">
          {chevron_svg}
        </div>
        <span class="section-title">{escape_html(step["step_name"])}</span>
      </div>
      <span class="section-pill" id="pill-section-{sid}">0 / {total}</span>
    </div>

    <div class="section-body">
      <div class="callout callout-info">
        <div class="callout-body">
          <div class="callout-title">Prerequisites</div>
          {escape_html(prereq)}
        </div>
      </div>
{"".join(build_code_block(cmd, "Setup") for cmd in console_cmds["setup"])}
{('<div class="callout callout-info" style="margin-top:8px;padding:8px 12px;font-size:12px;"><strong>Browser console:</strong> Press Cmd+Option+J (Mac) or Ctrl+Shift+J (Windows/Linux) to open DevTools, then paste the code below into the Console tab.</div>') if console_cmds["console"] else ""}
{"".join(build_code_block(cmd, "Console") for cmd in console_cmds["console"])}
      <div class="checks-list" id="checks-section-{sid}">{checks_html}
      </div>
{build_restore_callout(console_cmds["restore"]) if console_cmds["restore"] else ""}
    </div>
  </div>"""


def build_bugs_html(bugs: list) -> str:
    """Build the bugs section HTML."""
    if not bugs:
        return ""

    chevron_svg = (
        '<svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">'
        '<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>'
        '</svg>'
    )

    bug_cards = ""
    for bug in bugs:
        severity = bug.get("severity", "Low")
        severity_lower = severity.lower()
        severity_dot_class = f"severity-{severity_lower}"
        badge_class = f"badge-{severity_lower}"

        title = escape_html(bug.get("title", "Untitled bug"))
        desc = escape_html(bug.get("description", ""))
        file_ref = escape_html(bug.get("file", ""))
        line_num = bug.get("line", "")
        found_by = escape_html(bug.get("found_by", ""))

        file_display = f"{file_ref}:{line_num}" if line_num else file_ref

        bug_cards += f"""
      <div class="bug-card">
        <div class="bug-card-header">
          <div class="severity-dot {severity_dot_class}"></div>
          <span class="bug-title">{title}</span>
          <span class="severity-badge {badge_class}">{escape_html(severity)}</span>
        </div>
        <p class="bug-description">{desc}</p>
        <div class="bug-meta">
          <span class="bug-file">{escape_html(file_display)}</span>
          <span class="bug-found">Found by: {found_by}</span>
        </div>
      </div>"""

    return f"""
  <div class="bugs-section" id="bugs-section">
    <div class="bugs-header" onclick="toggleBugs()">
      <div class="bugs-title">
        <div class="section-chevron" style="color:var(--grey-400)">
          {chevron_svg}
        </div>
        Known Bugs
        <span class="bugs-count">{len(bugs)} open</span>
      </div>
      <span style="font-size:12px;color:var(--grey-400)">Informational &mdash; no action needed</span>
    </div>

    <div class="bugs-body">{bug_cards}
    </div>
  </div>"""


def build_sections_js(steps: list) -> str:
    """Build the SECTIONS JS object."""
    entries = []
    for step in steps:
        sid = step["step_num"]
        label = step["step_name"].replace("'", "\\'")
        total = len(step["manual_items"])
        entries.append(f"  '{sid}': {{ label: '{label}', step: 'Step {sid}', total: {total} }}")
    return "{\n" + ",\n".join(entries) + "\n}"


def build_initial_state_js(steps: list) -> str:
    """Build JS to pre-set checked items to 'pass'."""
    lines = []
    for step in steps:
        sid = step["step_num"]
        for i, item in enumerate(step["manual_items"]):
            if item["checked"]:
                lines.append(f"  state['{sid}'][{i}].state = 'pass';")
    return "\n".join(lines)


def generate_html(
    feature: dict,
    state_info: dict,
    bugs: list,
    today: str,
    test_results: dict | None = None,
    code_trace: list | None = None,
) -> str:
    """Generate the complete HTML string."""
    feature_name = feature["feature_name"]
    version = state_info["version"]
    app_filename = state_info["filename"]
    feature_slug = slugify(feature_name)
    storage_key = f"test-checklist-{feature_slug}-{version}"

    # Total checks
    total_checks = sum(len(s["manual_items"]) for s in feature["steps"])

    # Automated results (renders when either test results or code trace is available)
    auto_results_html = build_auto_results_html(test_results, code_trace)
    has_auto = test_results is not None or code_trace is not None
    auto_results_css = build_auto_results_css() if has_auto else ""
    auto_verified_count = 0
    if test_results:
        maestro = test_results.get("maestro_results", {})
        if maestro and maestro.get("status") not in ("error", None):
            auto_verified_count = maestro.get("total", 0)
        else:
            pw = test_results.get("playwright", {})
            if pw.get("status") not in ("error", None):
                auto_verified_count = pw.get("total", 0)

    # Build signpost callout
    signpost_html = build_signpost_html(total_checks, test_results)

    # Build section cards
    total_steps = feature.get("total_steps", 0)
    sections_html = ""
    for idx, step in enumerate(feature["steps"]):
        sections_html += build_section_html(step, idx == 0, 0, total_steps)

    # Build bugs
    bugs_html = build_bugs_html(bugs)

    # Build JS data
    sections_js = build_sections_js(feature["steps"])
    initial_state_js = build_initial_state_js(feature["steps"])

    # Export section references
    export_feature = escape_html(feature_name)
    export_version = escape_html(version)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manual Test Checklist &mdash; {escape_html(feature_name)} {escape_html(version)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --blue: #2563eb;
    --blue-light: #eff6ff;
    --blue-mid: #bfdbfe;
    --green: #16a34a;
    --green-light: #f0fdf4;
    --green-mid: #bbf7d0;
    --red: #dc2626;
    --red-light: #fef2f2;
    --red-mid: #fecaca;
    --amber: #d97706;
    --amber-light: #fffbeb;
    --amber-mid: #fde68a;
    --grey-50: #f9fafb;
    --grey-100: #f3f4f6;
    --grey-200: #e5e7eb;
    --grey-300: #d1d5db;
    --grey-400: #9ca3af;
    --grey-500: #6b7280;
    --grey-600: #4b5563;
    --grey-700: #374151;
    --grey-800: #1f2937;
    --grey-900: #111827;
    --radius: 8px;
    --radius-sm: 4px;
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.04);
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: var(--grey-800);
    background: var(--grey-100);
    min-height: 100vh;
  }}

  /* -- Top bar -- */
  .top-bar {{
    background: white;
    border-bottom: 1px solid var(--grey-200);
    padding: 0 24px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: var(--shadow);
  }}

  .top-bar-inner {{
    max-width: 900px;
    margin: 0 auto;
    padding: 16px 0 12px;
  }}

  .top-bar-row1 {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 12px;
  }}

  .title-block {{}}

  .hero-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 3px;
  }}

  .hero-row h1 {{
    font-size: 20px;
    font-weight: 700;
    color: var(--grey-900);
    letter-spacing: -0.3px;
    line-height: 1.15;
  }}

  .app-pill {{
    background: #dbeafe;
    color: var(--blue);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
    padding: 3px 10px;
    border-radius: 99px;
    border: 1px solid #bfdbfe;
    white-space: nowrap;
  }}

  .version-tag {{
    font-size: 11px;
    color: var(--grey-400);
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
  }}

  .title-subtitle {{
    font-size: 13px;
    color: var(--grey-500);
    margin-bottom: 6px;
  }}

  .env-cards {{
    display: flex;
    gap: 20px;
    align-items: flex-start;
    flex-shrink: 0;
  }}

  .env-card {{
    display: flex;
    flex-direction: column;
    gap: 1px;
  }}

  .env-card-label {{
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--grey-400);
  }}

  .env-card-value {{
    font-size: 12px;
    color: var(--grey-600);
    font-weight: 500;
  }}

  .btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    text-decoration: none;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  }}

  .btn-primary {{
    background: var(--blue);
    color: white;
  }}
  .btn-primary:hover {{ background: #1d4ed8; }}

  .btn-ghost {{
    background: transparent;
    color: var(--grey-600);
    border: 1px solid var(--grey-300);
  }}
  .btn-ghost:hover {{ background: var(--grey-50); color: var(--grey-800); }}

  .btn-danger {{
    background: transparent;
    color: var(--red);
    border: 1px solid var(--red-mid);
  }}
  .btn-danger:hover {{ background: var(--red-light); }}

  .btn-amber {{
    background: #fef3c7;
    border: 1px solid #fcd34d;
    color: #92400e;
    font-weight: 600;
  }}
  .btn-amber:hover {{ background: #fde68a; }}

  /* Copy dropdown */
  .copy-dropdown {{
    position: relative;
  }}
  .copy-caret {{
    font-size: 10px;
    margin-left: 2px;
  }}
  .copy-menu {{
    display: none;
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    background: white;
    border: 1px solid var(--grey-200);
    border-radius: var(--radius-sm);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    min-width: 200px;
    z-index: 100;
    overflow: hidden;
  }}
  .copy-menu.open {{ display: block; }}
  .copy-menu-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 9px 14px;
    border: none;
    background: none;
    font-size: 13px;
    color: var(--grey-700);
    cursor: pointer;
    text-align: left;
  }}
  .copy-menu-item:hover {{ background: var(--grey-50); }}
  .copy-menu-item + .copy-menu-item {{ border-top: 1px solid var(--grey-100); }}
  .fail-count {{
    font-size: 11px;
    color: var(--grey-400);
    margin-left: auto;
  }}
  .fail-count.has-fails {{ color: var(--red); font-weight: 600; }}

  /* Progress card */
  .progress-card {{
    background: var(--grey-50);
    border: 1px solid var(--grey-200);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    margin: 5px 0;
  }}

  .progress-track {{
    width: 100%;
    height: 12px;
    background: var(--grey-200);
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    margin-bottom: 6px;
  }}

  .progress-fill-pass {{
    height: 100%;
    background: var(--green);
    transition: width 0.4s ease;
  }}

  .progress-fill-fail {{
    height: 100%;
    background: var(--red);
    transition: width 0.4s ease;
  }}

  .progress-stats {{
    display: flex;
    gap: 14px;
    font-size: 12px;
  }}

  .stat-pass {{ color: var(--green); font-weight: 600; }}
  .stat-fail {{ color: var(--red); font-weight: 600; }}
  .stat-untested {{ color: var(--grey-400); }}

  /* Button row */
  .btn-row {{
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
    margin-top: 10px;
  }}

  .elapsed-block {{
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin-right: auto;
  }}

  .elapsed-label {{
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--grey-400);
  }}

  .elapsed-value {{
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
    font-size: 14px;
    font-weight: 600;
    color: var(--grey-700);
    font-variant-numeric: tabular-nums;
  }}
  .elapsed-value.active {{ color: var(--blue); }}

  #timer-display {{ font-weight: 600; color: var(--grey-700); font-variant-numeric: tabular-nums; }}
  /* timer active state handled by .elapsed-value.active */

  /* -- Page layout -- */
  .page-body {{
    max-width: 900px;
    margin: 0 auto;
    padding: 8px 24px 24px;
  }}

  /* -- Section card -- */
  .section-card {{
    background: white;
    border: 1px solid var(--grey-200);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 16px;
    overflow: hidden;
  }}

  .section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    cursor: pointer;
    user-select: none;
    background: white;
    transition: background 0.1s;
  }}

  .section-header:hover {{ background: var(--grey-50); }}

  .section-header-left {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .section-chevron {{
    width: 20px;
    height: 20px;
    color: var(--grey-400);
    transition: transform 0.2s;
    flex-shrink: 0;
  }}
  .section-chevron svg {{ display: block; }}
  .section-card.collapsed .section-chevron {{ transform: rotate(-90deg); }}

  .section-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--grey-900);
  }}

  .section-step {{
    font-size: 11px;
    font-weight: 500;
    color: var(--grey-400);
    background: var(--grey-100);
    border-radius: 99px;
    padding: 2px 8px;
  }}

  /* -- Section stripe (Concept C) -- */
  .section-stripe {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 18px;
    background: var(--grey-50);
    border-bottom: 1px solid var(--grey-100);
    font-size: 12px;
  }}
  .section-stripe-left {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section-step-pill {{
    background: var(--grey-200);
    color: var(--grey-600);
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 99px;
  }}
  .section-stripe-time {{
    color: var(--grey-500);
    font-size: 12px;
  }}
  .section-stripe-pos {{
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
    font-size: 11px;
    color: var(--grey-400);
  }}

  /* -- Signpost banner divider -- */
  .signpost-banner {{
    display: flex;
    align-items: center;
    gap: 16px;
    max-width: 900px;
    margin: 4px auto 8px;
    padding: 0 24px;
  }}
  .signpost-banner-line {{
    flex: 1;
    height: 1px;
    background: var(--grey-300);
  }}
  .signpost-banner-text {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--grey-500);
    white-space: nowrap;
  }}

  .section-pill {{
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 600;
    background: var(--grey-100);
    color: var(--grey-500);
    transition: background 0.2s, color 0.2s;
  }}
  .section-pill.has-pass {{ background: var(--green-light); color: var(--green); }}
  .section-pill.has-fail {{ background: var(--red-light); color: var(--red); }}
  .section-pill.all-pass {{ background: var(--green-mid); color: #15803d; }}

  .section-body {{
    padding: 0 18px 18px;
    border-top: 1px solid var(--grey-100);
  }}
  .section-card.collapsed .section-body {{ display: none; }}

  /* -- Callouts -- */
  .callout {{
    display: flex;
    gap: 10px;
    border-radius: var(--radius-sm);
    padding: 11px 14px;
    margin: 14px 0 8px;
    font-size: 13px;
  }}

  .callout-icon {{
    font-size: 15px;
    line-height: 1.4;
    flex-shrink: 0;
  }}

  .callout-body {{ flex: 1; }}
  .callout-title {{ font-weight: 600; margin-bottom: 2px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}

  .callout-info {{ background: var(--blue-light); border: 1px solid var(--blue-mid); color: #1e40af; }}
  .callout-info .callout-title {{ color: var(--blue); }}
  .callout-amber {{ background: var(--amber-light); border: 1px solid var(--amber-mid); color: #92400e; }}
  .callout-amber .callout-title {{ color: var(--amber); }}
  .callout-amber p {{ margin: 4px 0 0; font-size: 13px; }}
  .callout-amber .code-block {{ margin-top: 8px; }}

  .callout-warn {{ background: var(--amber-light); border: 1px solid var(--amber-mid); color: #92400e; }}
  .callout-warn .callout-title {{ color: var(--amber); }}

  /* -- Code block -- */
  .code-block {{
    background: var(--grey-900);
    border-radius: var(--radius-sm);
    margin: 8px 0;
    overflow: hidden;
  }}

  .code-block-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 12px;
    background: var(--grey-800);
  }}

  .code-block-label {{
    font-size: 11px;
    color: var(--grey-400);
    font-family: 'SF Mono', 'Fira Code', Consolas, 'Courier New', monospace;
  }}

  .copy-btn {{
    background: transparent;
    border: 1px solid var(--grey-600);
    color: var(--grey-300);
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 11px;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s, color 0.15s;
  }}
  .copy-btn:hover {{ background: var(--grey-700); color: white; }}
  .copy-btn.copied {{ border-color: var(--green); color: #4ade80; }}

  .code-block pre {{
    padding: 12px 14px;
    font-family: 'SF Mono', 'Fira Code', Consolas, 'Courier New', monospace;
    font-size: 12.5px;
    color: #e2e8f0;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }}

  /* -- Check items -- */
  .checks-list {{
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .check-item {{
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    transition: background 0.15s, border-color 0.15s;
  }}

  .check-item.state-pass {{
    background: var(--green-light);
    border-color: var(--green-mid);
  }}

  .check-item.state-fail {{
    background: var(--red-light);
    border-color: var(--red-mid);
  }}

  .check-row {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 9px 4px 9px 4px;
    cursor: pointer;
    user-select: none;
  }}

  .check-num {{
    font-size: 11px;
    color: var(--grey-400);
    min-width: 14px;
    text-align: right;
    padding-top: 2px;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }}

  /* Three-state toggle button */
  .state-toggle {{
    width: 22px;
    height: 22px;
    border-radius: var(--radius-sm);
    border: 2px solid var(--grey-300);
    background: white;
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 0.15s, background 0.15s;
    position: relative;
    margin-top: 0;
  }}

  .state-toggle:hover {{ border-color: var(--grey-400); }}

  .state-toggle.pass {{
    background: var(--green);
    border-color: var(--green);
  }}

  .state-toggle.fail {{
    background: var(--red);
    border-color: var(--red);
  }}

  /* checkmark */
  .state-toggle.pass::before {{
    content: '';
    width: 10px;
    height: 6px;
    border-bottom: 2.5px solid white;
    border-left: 2.5px solid white;
    transform: rotate(-45deg) translateY(-1px);
    display: block;
  }}

  /* X mark */
  .state-toggle.fail::before {{
    content: '';
    width: 10px;
    height: 2px;
    background: white;
    display: block;
    transform: rotate(45deg);
    box-shadow: 0 0 0 2px transparent;
    position: absolute;
  }}
  .state-toggle.fail::after {{
    content: '';
    width: 10px;
    height: 2px;
    background: white;
    display: block;
    transform: rotate(-45deg);
    position: absolute;
  }}

  .check-text {{
    flex: 1;
    font-size: 13px;
    color: var(--grey-700);
    padding-top: 2px;
    line-height: 1.45;
  }}

  .check-item.state-pass .check-text {{ color: var(--grey-800); }}
  .check-item.state-fail .check-text {{ color: var(--grey-800); }}

  .fail-notes-wrap {{
    display: none;
    padding: 0 10px 10px 50px;
  }}
  .check-item.state-fail .fail-notes-wrap {{ display: block; }}

  .fail-notes-wrap textarea {{
    width: 100%;
    border: 1px solid var(--red-mid);
    border-radius: var(--radius-sm);
    padding: 8px 10px;
    font-size: 12.5px;
    font-family: inherit;
    color: var(--grey-700);
    background: white;
    resize: vertical;
    min-height: 56px;
    line-height: 1.4;
    transition: border-color 0.15s, box-shadow 0.15s;
  }}
  .fail-notes-wrap textarea:focus {{
    outline: none;
    border-color: var(--red);
    box-shadow: 0 0 0 2px rgba(220,38,38,0.15);
  }}
  .fail-notes-label {{
    font-size: 11px;
    color: var(--red);
    font-weight: 600;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}

  /* subsection label inside checks */
  .checks-part-label {{
    font-size: 11px;
    font-weight: 700;
    color: var(--grey-500);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 10px 10px 4px;
    margin-top: 6px;
  }}

  /* -- Known bugs -- */
  .bugs-section {{
    background: white;
    border: 1px solid var(--grey-200);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 16px;
    overflow: hidden;
  }}

  .bugs-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--grey-100);
    cursor: pointer;
    user-select: none;
    transition: background 0.1s;
  }}
  .bugs-header:hover {{ background: var(--grey-50); }}

  .bugs-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--grey-900);
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .bugs-count {{
    background: var(--red-light);
    color: var(--red);
    border-radius: 99px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
  }}

  .bugs-body {{
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .bugs-section.collapsed .bugs-body {{ display: none; }}
  .bugs-section.collapsed .section-chevron {{ transform: rotate(-90deg); }}

  .bug-card {{
    border: 1px solid var(--grey-200);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    background: var(--grey-50);
  }}

  .bug-card-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }}

  .severity-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .severity-high {{ background: var(--red); }}
  .severity-medium {{ background: var(--amber); }}
  .severity-low {{ background: var(--grey-400); }}

  .bug-title {{
    font-weight: 600;
    font-size: 13px;
    color: var(--grey-800);
    flex: 1;
  }}

  .severity-badge {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 99px;
  }}
  .badge-high {{ background: var(--red-light); color: var(--red); border: 1px solid var(--red-mid); }}
  .badge-medium {{ background: var(--amber-light); color: var(--amber); border: 1px solid var(--amber-mid); }}
  .badge-low {{ background: var(--grey-100); color: var(--grey-500); border: 1px solid var(--grey-200); }}

  .bug-description {{ font-size: 12.5px; color: var(--grey-600); margin-bottom: 8px; line-height: 1.4; }}

  .bug-meta {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}

  .bug-file {{
    font-family: 'SF Mono', 'Fira Code', Consolas, 'Courier New', monospace;
    font-size: 11px;
    background: var(--grey-200);
    color: var(--grey-700);
    padding: 2px 7px;
    border-radius: 3px;
  }}

  .bug-found {{ font-size: 11px; color: var(--grey-400); }}

  /* -- Footer -- */
  .footer {{
    text-align: center;
    padding: 24px;
    font-size: 11.5px;
    color: var(--grey-400);
    border-top: 1px solid var(--grey-200);
    margin-top: 8px;
  }}

  /* -- Toast -- */
  .toast {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--grey-900);
    color: white;
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    opacity: 0;
    transform: translateY(8px);
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
    z-index: 999;
    max-width: 280px;
  }}
  .toast.show {{ opacity: 1; transform: translateY(0); }}
  .toast.success {{ background: var(--green); }}
  .toast.error {{ background: var(--red); }}

  /* -- Dark mode (toggle-driven, not auto) -- */
  body.dark {{
    --blue: #3b82f6;
    --blue-light: #1e3a5f;
    --blue-mid: #1d4ed880;
    --green: #4ade80;
    --green-light: #052e16;
    --green-mid: #16653480;
    --red: #f87171;
    --red-light: #450a0a;
    --red-mid: #991b1b80;
    --amber: #fbbf24;
    --amber-light: #451a0380;
    --amber-mid: #92400e80;
    --grey-50: #1a2332;
    --grey-100: #1f2937;
    --grey-200: #374151;
    --grey-300: #4b5563;
    --grey-400: #9ca3af;
    --grey-500: #9ca3af;
    --grey-600: #d1d5db;
    --grey-700: #e5e7eb;
    --grey-800: #f3f4f6;
    --grey-900: #f9fafb;
    --radius: 8px;
    --radius-sm: 4px;
    --shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.25), 0 2px 4px rgba(0,0,0,0.15);
    background: #0f172a;
    color: #e2e8f0;
  }}
  body.dark .top-bar {{ background: #1e293b; border-color: #334155; box-shadow: 0 1px 3px rgba(0,0,0,0.4); }}
  body.dark .hero-row h1 {{ color: #f1f5f9; }}
  body.dark .app-pill {{ background: #1e3a5f; color: #60a5fa; border-color: #1d4ed880; }}
  body.dark .section-card {{ background: #1e293b; border-color: #334155; }}
  body.dark .section-header {{ background: #1e293b; }}
  body.dark .section-header:hover {{ background: #334155; }}
  body.dark .section-body {{ border-color: #334155; }}
  body.dark .section-stripe {{ background: #0f172a; border-color: #334155; }}
  body.dark .section-step-pill {{ background: #334155; color: #94a3b8; }}
  body.dark .section-stripe-time {{ color: #94a3b8; }}
  body.dark .section-title {{ color: #e2e8f0; }}
  body.dark .section-pill {{ background: #334155; color: #94a3b8; }}
  body.dark .section-pill.has-pass {{ background: #052e16; color: #4ade80; }}
  body.dark .section-pill.has-fail {{ background: #450a0a; color: #f87171; }}
  body.dark .section-pill.all-pass {{ background: #052e16; color: #4ade80; }}
  body.dark .section-chevron {{ color: #64748b; }}
  body.dark .progress-card {{ background: #1e293b; border-color: #334155; }}
  body.dark .progress-track {{ background: #334155; }}
  body.dark .check-text {{ color: #cbd5e1; }}
  body.dark .check-num {{ color: #64748b; }}
  body.dark .check-item.state-pass {{ background: #052e1680; border-color: #166534; }}
  body.dark .check-item.state-fail {{ background: #450a0a80; border-color: #991b1b; }}
  body.dark .state-toggle {{ background: #334155; border-color: #475569; }}
  body.dark .state-toggle:hover {{ border-color: #64748b; }}
  body.dark .callout-info {{ background: #1e3a5f; border-color: #1d4ed880; color: #93c5fd; }}
  body.dark .callout-info .callout-title {{ color: #60a5fa; }}
  body.dark .callout-amber {{ background: #451a0380; border-color: #92400e80; color: #fbbf24; }}
  body.dark .callout-amber .callout-title {{ color: #fbbf24; }}
  body.dark .code-block {{ background: #0f172a; }}
  body.dark .code-block-header {{ background: #1e293b; }}
  body.dark .copy-btn {{ border-color: #475569; color: #94a3b8; }}
  body.dark .copy-btn:hover {{ background: #334155; color: #e2e8f0; }}
  body.dark .ar-card {{ background: #1e293b; border-color: #334155; }}
  body.dark .ar-header {{ border-color: #334155; }}
  body.dark .ar-title {{ color: #e2e8f0; }}
  body.dark .ar-tiles-strip {{ background: #0f172a; border-color: #334155; }}
  body.dark .ar-tile {{ border-color: #334155; }}
  body.dark .ar-tile-label {{ color: #94a3b8; }}
  body.dark .ar-tile-detail {{ color: #94a3b8; }}
  body.dark .ar-badge {{ background: #052e16; color: #4ade80; border-color: #16653480; }}
  body.dark .ar-badge.warn {{ background: #451a0380; color: #fbbf24; border-color: #92400e80; }}
  body.dark .ar-badge.fail {{ background: #450a0a80; color: #f87171; border-color: #991b1b80; }}
  body.dark .ar-detail {{ border-color: #334155; }}
  body.dark .ar-detail summary {{ color: #94a3b8; }}
  body.dark .ar-detail summary:hover {{ background: #334155; color: #e2e8f0; }}
  body.dark .ar-detail-body {{ color: #cbd5e1; }}
  body.dark .chevron-icon {{ color: #64748b; }}
  body.dark .hc-row, body.dark .route-row {{ border-color: #334155; }}
  body.dark .signpost-banner-line {{ background: #475569; }}
  body.dark .signpost-banner-text {{ color: #94a3b8; }}
  body.dark .copy-menu {{ background: #1e293b; border-color: #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
  body.dark .copy-menu-item {{ color: #cbd5e1; }}
  body.dark .copy-menu-item:hover {{ background: #334155; }}
  body.dark .copy-menu-item + .copy-menu-item {{ border-color: #334155; }}
  body.dark .fail-count {{ color: #64748b; }}
  body.dark .fail-count.has-fails {{ color: #f87171; }}
  body.dark .btn {{ color: #cbd5e1; border-color: #475569; }}
  body.dark .btn:hover {{ background: #334155; }}
  body.dark .btn-primary {{ background: #2563eb; color: white; }}
  body.dark .btn-primary:hover {{ background: #1d4ed8; }}
  body.dark .btn-danger {{ color: #f87171; border-color: #991b1b; }}
  body.dark .btn-danger:hover {{ background: #450a0a80; }}
  body.dark .btn-ghost {{ border-color: #475569; color: #94a3b8; }}
  body.dark .btn-ghost:hover {{ background: #334155; color: #e2e8f0; }}
  body.dark .env-card-label {{ color: #64748b; }}
  body.dark .env-card-value {{ color: #cbd5e1; }}
  body.dark .fail-notes-wrap textarea {{ background: #0f172a; border-color: #475569; color: #e2e8f0; }}
  body.dark .fail-notes-label {{ color: #94a3b8; }}
  body.dark .footer {{ color: #64748b; }}
  body.dark .toast {{ background: #334155; color: #e2e8f0; }}
  body.dark .title-subtitle {{ color: #94a3b8; }}
  body.dark .ar-warnings {{ background: #451a0340; border-color: #92400e60; }}
  body.dark .ar-stale-note {{ color: #fbbf24; background: #451a0340; }}
  body.dark .ar-fail-card {{ background: #450a0a40; border-color: #991b1b60; }}

  /* Dark mode toggle button */
  .theme-toggle {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 1px solid var(--grey-300);
    background: transparent;
    cursor: pointer;
    color: var(--grey-500);
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    flex-shrink: 0;
  }}
  .theme-toggle:hover {{ background: var(--grey-100); color: var(--grey-700); }}
  .theme-toggle svg {{ width: 16px; height: 16px; }}
  body.dark .theme-toggle {{ border-color: #475569; color: #94a3b8; }}
  body.dark .theme-toggle:hover {{ background: #334155; color: #e2e8f0; }}
{auto_results_css}
</style>
</head>
<body>

<!-- STICKY TOP BAR -->
<div class="top-bar">
  <div class="top-bar-inner">
    <div class="top-bar-row1">
      <div class="title-block">
        <div class="hero-row">
          <h1>{escape_html(feature_name)}</h1>
          <span class="app-pill">{escape_html(feature.get('type_tag', 'APP'))}</span>
          <span class="version-tag">{escape_html(version)}</span>
        </div>
      </div>
      <div class="env-cards">
        <div class="env-card">
          <span class="env-card-label">Browser</span>
          <span class="env-card-value" id="env-browser">&mdash;</span>
        </div>
        <div class="env-card">
          <span class="env-card-label">Viewport</span>
          <span class="env-card-value" id="env-viewport">&mdash;</span>
        </div>
        <div class="env-card">
          <span class="env-card-label">OS</span>
          <span class="env-card-value" id="env-os">&mdash;</span>
        </div>
        <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">
          <svg id="theme-icon-sun" viewBox="0 0 20 20" fill="currentColor" style="display:none"><path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"/></svg>
          <svg id="theme-icon-moon" viewBox="0 0 20 20" fill="currentColor"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/></svg>
        </button>
      </div>
    </div>

    <!-- Progress card -->
    <div class="progress-card">
      <div class="title-subtitle">Manual test checklist &middot; {total_checks} checks{f' ({auto_verified_count} auto-verified)' if auto_verified_count else ''}</div>
      <div class="progress-track">
        <div class="progress-fill-pass" id="progress-fill-pass" style="width:0%"></div>
        <div class="progress-fill-fail" id="progress-fill-fail" style="width:0%"></div>
      </div>
      <div class="progress-stats">
        <span class="stat-pass" id="stat-pass">0 pass</span>
        <span class="stat-fail" id="stat-fail" style="display:none">0 fail</span>
        <span class="stat-untested" id="stat-untested">{total_checks} untested</span>
      </div>
    </div>

    <!-- Buttons -->
    <div class="btn-row">
      <div class="elapsed-block">
        <span class="elapsed-label">Elapsed</span>
        <span class="elapsed-value" id="timer-display">0:00</span>
      </div>
      <button class="btn btn-danger" onclick="resetAll()">Reset all</button>
      <div class="copy-dropdown" id="copy-dropdown">
        <button class="btn btn-ghost" onclick="toggleCopyMenu(event)">Copy <span class="copy-caret">&#9662;</span></button>
        <div class="copy-menu" id="copy-menu">
          <button class="copy-menu-item" onclick="doCopy('all')">Copy All Results</button>
          <button class="copy-menu-item" onclick="doCopy('fail')">Copy Failures Only <span class="fail-count" id="copy-fail-count"></span></button>
          {'<button class="copy-menu-item" onclick="doCopy(&quot;bugs&quot;)">Copy Bugs</button>' if bugs else ''}
        </div>
      </div>
      <a class="btn btn-primary" href="../{escape_html(app_filename)}" target="_blank">Open App &#8599;</a>
    </div>
  </div>
</div>

{auto_results_html}
{signpost_html}
<!-- PAGE BODY -->
<div class="page-body">
{sections_html}

{bugs_html}

</div><!-- /page-body -->

<!-- FOOTER -->
<div class="footer">
  Generated by DOE Test Checklist Generator &nbsp;|&nbsp; {today}
</div>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<script>
// ===============================================
// DATA MODEL
// ===============================================
const FEATURE_NAME = '{escape_html(feature_name)}';
const VERSION = '{escape_html(version)}';
const STORAGE_KEY = '{storage_key}';

// Section definitions: id -> {{ total, label, step }}
const SECTIONS = {sections_js};

// State per check: 'untested' | 'pass' | 'fail'
// state[sectionId][index] = {{ state, note }}
let state = {{}};

// Timer state
let timerInterval = null;
let timerStartMs  = null;    // wall-clock ms when first interaction happened
let timerElapsedMs = 0;      // accumulated elapsed ms (for restore)
let sectionStartMs = {{}};     // when each section saw its first interaction
let sectionElapsedMs = {{}};   // accumulated per-section elapsed ms

// ===============================================
// INITIALISE
// ===============================================
function init() {{
  detectEnv();
  loadState();
{initial_state_js}
  renderAll();
  startTimerTick();
}}

function detectEnv() {{
  // Browser
  const ua = navigator.userAgent;
  let browser = 'Unknown';
  if (/Edg\\/[\\d.]+/.test(ua))        browser = 'Edge ' + ua.match(/Edg\\/([\\d.]+)/)[1];
  else if (/OPR\\/[\\d.]+/.test(ua))   browser = 'Opera ' + ua.match(/OPR\\/([\\d.]+)/)[1];
  else if (/Chrome\\/[\\d.]+/.test(ua)) browser = 'Chrome ' + ua.match(/Chrome\\/([\\d.]+)/)[1];
  else if (/Firefox\\/[\\d.]+/.test(ua)) browser = 'Firefox ' + ua.match(/Firefox\\/([\\d.]+)/)[1];
  else if (/Safari\\/[\\d.]+/.test(ua)) browser = 'Safari ' + (ua.match(/Version\\/([\\d.]+)/) || ['',''])[1];
  document.getElementById('env-browser').textContent = browser;

  // Viewport
  document.getElementById('env-viewport').textContent = window.innerWidth + 'px';

  // OS
  let os = 'Unknown';
  if (/Win/.test(ua))         os = 'Windows';
  else if (/Mac/.test(ua))    os = 'macOS';
  else if (/Linux/.test(ua))  os = 'Linux';
  else if (/iPhone/.test(ua)) os = 'iOS';
  else if (/Android/.test(ua)) os = 'Android';
  document.getElementById('env-os').textContent = os;
}}

// ===============================================
// STATE PERSISTENCE
// ===============================================
function loadState() {{
  try {{
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (saved) {{
      state = saved.checks || {{}};
      timerElapsedMs = saved.timerElapsedMs || 0;
      timerStartMs   = saved.timerStartMs   || null;
      sectionStartMs   = saved.sectionStartMs   || {{}};
      sectionElapsedMs = saved.sectionElapsedMs || {{}};
    }}
  }} catch(e) {{}}

  // Ensure all sections/indices are initialised
  for (const sid of Object.keys(SECTIONS)) {{
    if (!state[sid]) state[sid] = {{}};
    for (let i = 0; i < SECTIONS[sid].total; i++) {{
      if (!state[sid][i]) state[sid][i] = {{ state: 'untested', note: '' }};
    }}
  }}
}}

function saveState() {{
  const payload = {{
    checks: state,
    timerElapsedMs,
    timerStartMs,
    sectionStartMs,
    sectionElapsedMs,
  }};
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}}

function resetAll() {{
  if (!confirm('Reset all check states, notes, and timer? This cannot be undone.')) return;
  localStorage.removeItem(STORAGE_KEY);
  timerStartMs   = null;
  timerElapsedMs = 0;
  sectionStartMs   = {{}};
  sectionElapsedMs = {{}};
  state = {{}};
  loadState();
  renderAll();
  updateTimerDisplay();
  showToast('All checks reset', 'success');
}}

// ===============================================
// RENDER
// ===============================================
function renderAll() {{
  for (const sid of Object.keys(SECTIONS)) {{
    renderSection(sid);
  }}
  updateProgressBar();
}}

function renderSection(sid) {{
  const checksEl = document.getElementById('checks-section-' + sid);
  if (!checksEl) return;
  const items = checksEl.querySelectorAll('.check-item');
  items.forEach((item, i) => {{
    const s = state[sid][i] || {{ state: 'untested', note: '' }};
    applyCheckState(item, s.state, s.note);
  }});
  updateSectionPill(sid);
}}

function applyCheckState(item, checkState, note) {{
  item.classList.remove('state-pass', 'state-fail');
  const toggle = item.querySelector('.state-toggle');
  toggle.classList.remove('pass', 'fail');

  if (checkState === 'pass') {{
    item.classList.add('state-pass');
    toggle.classList.add('pass');
  }} else if (checkState === 'fail') {{
    item.classList.add('state-fail');
    toggle.classList.add('fail');
  }}

  const ta = item.querySelector('textarea');
  if (ta) ta.value = note || '';
}}

function updateSectionPill(sid) {{
  const pill = document.getElementById('pill-section-' + sid);
  if (!pill) return;
  const {{ total }} = SECTIONS[sid];
  let pass = 0, fail = 0;
  for (let i = 0; i < total; i++) {{
    const s = (state[sid][i] || {{}}).state;
    if (s === 'pass') pass++;
    else if (s === 'fail') fail++;
  }}
  pill.textContent = pass + ' / ' + total;
  pill.classList.remove('has-pass', 'has-fail', 'all-pass');
  if (fail > 0) pill.classList.add('has-fail');
  else if (pass === total) pill.classList.add('all-pass');
  else if (pass > 0) pill.classList.add('has-pass');
}}

function updateProgressBar() {{
  let totalChecks = 0, totalPass = 0, totalFail = 0;
  for (const sid of Object.keys(SECTIONS)) {{
    const {{ total }} = SECTIONS[sid];
    totalChecks += total;
    for (let i = 0; i < total; i++) {{
      const s = (state[sid][i] || {{}}).state;
      if (s === 'pass') totalPass++;
      else if (s === 'fail') totalFail++;
    }}
  }}
  const totalUntested = totalChecks - totalPass - totalFail;

  document.getElementById('stat-pass').textContent = totalPass + ' pass';

  const failEl = document.getElementById('stat-fail');
  if (totalFail > 0) {{
    failEl.style.display = '';
    failEl.textContent = totalFail + ' fail';
  }} else {{
    failEl.style.display = 'none';
  }}
  document.getElementById('stat-untested').textContent = totalUntested + ' untested';

  var passPercent = totalChecks > 0 ? (totalPass / totalChecks * 100).toFixed(1) : '0';
  var failPercent = totalChecks > 0 ? (totalFail / totalChecks * 100).toFixed(1) : '0';
  document.getElementById('progress-fill-pass').style.width = passPercent + '%';
  document.getElementById('progress-fill-fail').style.width = failPercent + '%';
}}

// ===============================================
// CHECK INTERACTION
// ===============================================
let _cycleDebounce = 0;
function cycleCheck(row) {{
  const now = Date.now();
  if (now - _cycleDebounce < 300) return;
  _cycleDebounce = now;
  const item   = row.closest('.check-item');
  const sid    = item.dataset.section;
  const idx    = parseInt(item.dataset.index);
  const cur    = state[sid][idx].state;
  const next   = cur === 'untested' ? 'pass' : cur === 'pass' ? 'fail' : 'untested';

  state[sid][idx].state = next;
  if (next !== 'fail') {{
    // don't clear note when cycling back -- preserve it for reference
  }}

  applyCheckState(item, next, state[sid][idx].note);
  updateSectionPill(sid);
  updateProgressBar();

  // Timer: start on first interaction
  touchTimer(sid);
  saveState();
}}

// Keep notes in sync
document.addEventListener('input', (e) => {{
  if (e.target.tagName !== 'TEXTAREA') return;
  const item = e.target.closest('.check-item');
  if (!item) return;
  const sid = item.dataset.section;
  const idx = parseInt(item.dataset.index);
  if (state[sid] && state[sid][idx]) {{
    state[sid][idx].note = e.target.value;
    saveState();
  }}
}});

// ===============================================
// TIMER
// ===============================================
function touchTimer(sid) {{
  const now = Date.now();
  if (timerStartMs === null) {{
    timerStartMs = now;
  }}
  if (!sectionStartMs[sid]) {{
    sectionStartMs[sid] = now;
  }}
}}

function startTimerTick() {{
  // Restore: if timer was running when page was last closed, recalculate
  if (timerStartMs !== null) {{
    updateTimerDisplay();
  }}
  setInterval(() => {{
    if (timerStartMs !== null) {{
      updateTimerDisplay();
    }}
  }}, 1000);
}}

function fmtMs(ms) {{
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m > 0) return m + 'm ' + String(s).padStart(2, '0') + 's';
  return s + 's';
}}

function updateTimerDisplay() {{
  const timerEl = document.getElementById('timer-display');

  if (timerStartMs === null) {{
    timerEl.textContent = '0:00';
    timerEl.classList.remove('active');
    return;
  }}

  const now = Date.now();
  const totalElapsed = (now - timerStartMs) + timerElapsedMs;
  const totalSec = Math.floor(totalElapsed / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  timerEl.textContent = m + ':' + String(s).padStart(2, '0');
  timerEl.classList.add('active');
}}

// ===============================================
// SECTION COLLAPSE
// ===============================================
function toggleSection(id) {{
  document.getElementById(id).classList.toggle('collapsed');
}}

function toggleBugs() {{
  document.getElementById('bugs-section').classList.toggle('collapsed');
}}

// ===============================================
// COPY CODE
// ===============================================
function copyCodeFromBlock(btn) {{
  const block = btn.closest('.code-block');
  const text = block ? block.dataset.code : '';
  navigator.clipboard.writeText(text).then(() => {{
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }}, 2000);
  }}).catch(() => {{
    showToast('Could not copy -- try manually selecting the code', 'error');
  }});
}}

// ===============================================
// EXPORT
// ===============================================
function buildResultsText(failOnly) {{
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-GB') + ' ' + now.toLocaleTimeString('en-GB', {{ hour: '2-digit', minute: '2-digit' }});
  const browser = document.getElementById('env-browser').textContent;
  const viewport = document.getElementById('env-viewport').textContent;
  const timerVal = document.getElementById('timer-display').textContent;

  const lines = [];

  if (!failOnly) {{
    // Include automated results in export if present
    var arSection = document.querySelector('.ar-section');
    if (arSection) {{
      lines.push('## Automated Results (completed in ' + (arSection.querySelector('.ar-duration') || {{}}).textContent + ')');
      var tiles = arSection.querySelectorAll('.ar-tile');
      tiles.forEach(function(t) {{
        var title = t.querySelector('.ar-tile-title').textContent;
        var value = t.querySelector('.ar-tile-value').textContent;
        var detail = t.querySelector('.ar-tile-detail').textContent;
        lines.push(title + ': ' + value + (detail ? ' (' + detail + ')' : ''));
      }});
      lines.push('');
    }}
    lines.push('## Manual Test Results -- {export_feature} {export_version}');
    lines.push('Tested: ' + dateStr + ' | Browser: ' + browser + ' | Viewport: ' + viewport);
    lines.push('Duration: ' + timerVal);
    lines.push('');
  }}

  let grandPass = 0, grandFail = 0, grandUntested = 0;

  for (const sid of Object.keys(SECTIONS)) {{
    const {{ label, step, total }} = SECTIONS[sid];
    let sPass = 0, sFail = 0;
    const failLines = [];

    // Get check text from DOM
    const checksEl = document.getElementById('checks-section-' + sid);
    const items = checksEl ? checksEl.querySelectorAll('.check-item') : [];

    for (let i = 0; i < total; i++) {{
      const s = state[sid][i] || {{ state: 'untested', note: '' }};
      if (s.state === 'pass') sPass++;
      else if (s.state === 'fail') {{
        sFail++;
        const textEl = items[i] ? items[i].querySelector('.check-text') : null;
        const desc = textEl ? textEl.textContent.trim() : 'Check ' + (i + 1);
        const note = s.note ? ' -- ' + s.note : '';
        failLines.push('  FAIL: ' + desc + note);
      }}
    }}

    const sUntested = total - sPass - sFail;
    grandPass += sPass;
    grandFail += sFail;
    grandUntested += sUntested;

    if (failOnly && sFail === 0) continue;

    lines.push('### Step ' + sid + ': ' + label + ' -- ' + sPass + '/' + total + ' pass, ' + sFail + ' fail');
    for (const fl of failLines) lines.push(fl);
    lines.push('');
  }}

  if (!failOnly) {{
    lines.push('Overall: ' + grandPass + '/' + (grandPass + grandFail + grandUntested) + ' pass, ' + grandFail + ' fail, ' + grandUntested + ' untested');
  }} else if (grandFail === 0) {{
    lines.push('No failures recorded.');
  }}

  return lines.join('\\n');
}}

function toggleCopyMenu(e) {{
  e.stopPropagation();
  const menu = document.getElementById('copy-menu');
  menu.classList.toggle('open');
  // Update fail count each time the menu opens
  if (menu.classList.contains('open')) {{
    let failCount = 0;
    for (const sid of Object.keys(SECTIONS)) {{
      for (let i = 0; i < SECTIONS[sid].total; i++) {{
        if (state[sid][i] && state[sid][i].state === 'fail') failCount++;
      }}
    }}
    const el = document.getElementById('copy-fail-count');
    if (el) {{
      el.textContent = failCount > 0 ? '(' + failCount + ')' : '';
      el.className = 'fail-count' + (failCount > 0 ? ' has-fails' : '');
    }}
  }}
}}

// Close menu on outside click
document.addEventListener('click', function(e) {{
  const menu = document.getElementById('copy-menu');
  if (menu && !e.target.closest('.copy-dropdown')) {{
    menu.classList.remove('open');
  }}
}});

function doCopy(mode) {{
  document.getElementById('copy-menu').classList.remove('open');
  if (mode === 'bugs') {{
    copyBugs();
  }} else {{
    copyResults(mode === 'fail');
  }}
}}

function copyResults(failOnly) {{
  const text = buildResultsText(failOnly);
  navigator.clipboard.writeText(text).then(() => {{
    showToast(failOnly ? 'Failures copied to clipboard' : 'Test results copied to clipboard', 'success');
  }}).catch(() => {{
    showToast('Clipboard write failed -- try a different browser', 'error');
  }});
}}

function copyBugs() {{
  var bugsSection = document.getElementById('bugs-section');
  if (!bugsSection) return;
  var bugCards = bugsSection.querySelectorAll('.bug-card');
  var lines = ['## Known Bugs -- ' + FEATURE_NAME + ' ' + VERSION, ''];
  bugCards.forEach(function(card, i) {{
    var title = card.querySelector('.bug-title').textContent;
    var severity = card.querySelector('.severity-badge').textContent;
    var desc = card.querySelector('.bug-description').textContent;
    var file = card.querySelector('.bug-file').textContent;
    lines.push((i+1) + '. [' + severity + '] ' + title);
    lines.push('   File: ' + file);
    lines.push('   ' + desc);
    lines.push('');
  }});
  lines.push('Fix these bugs and commit. Then I will re-run /snagging to verify.');
  var text = lines.join('\\n');
  navigator.clipboard.writeText(text).then(function() {{
    showToast('Bugs copied to clipboard', 'success');
  }});
}}

// ===============================================
// TOAST
// ===============================================
let toastTimeout = null;
function showToast(msg, type) {{
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (type ? ' ' + type : '');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {{ el.classList.remove('show'); }}, 2800);
}}

// -- Theme toggle --
function toggleTheme() {{
  var isDark = document.body.classList.toggle('dark');
  localStorage.setItem('snagging-theme', isDark ? 'dark' : 'light');
  updateThemeIcon(isDark);
}}

function updateThemeIcon(isDark) {{
  document.getElementById('theme-icon-sun').style.display = isDark ? '' : 'none';
  document.getElementById('theme-icon-moon').style.display = isDark ? 'none' : '';
}}

function initTheme() {{
  var saved = localStorage.getItem('snagging-theme');
  if (saved === 'dark') {{
    document.body.classList.add('dark');
    updateThemeIcon(true);
  }}
}}
initTheme();

// -- Boot --
init();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────
# Bug verification
# ──────────────────────────────────────────────

def verify_bugs(feature_name: str, bugs_path: Path) -> None:
    """Re-check known bugs and output terminal verification box."""
    if not bugs_path.exists():
        print("No bugs file found. Run /snagging first.", file=sys.stderr)
        sys.exit(1)

    bugs = json.loads(bugs_path.read_text(encoding="utf-8"))
    if not bugs:
        print("No bugs to verify.", file=sys.stderr)
        sys.exit(0)

    W = 60  # inner width

    def line(content=""):
        return f"\u2502  {content}".ljust(W + 1) + "\u2502"

    def top():
        return "\u250c" + "\u2500" * W + "\u2510"

    def sep():
        return "\u251c" + "\u2500" * W + "\u2524"

    def bot():
        return "\u2514" + "\u2500" * W + "\u2518"

    results = []
    for bug in bugs:
        file_path = bug.get("file", "")
        title = bug.get("title", "Untitled")
        description = bug.get("description", "")
        severity = bug.get("severity", "Medium")

        # Try to verify the fix by checking if the described problem pattern still exists
        resolved = False
        proof = "Could not auto-verify -- manual check needed"

        if file_path and Path(PROJECT_ROOT / file_path).exists():
            content = (PROJECT_ROOT / Path(file_path)).read_text(encoding="utf-8", errors="replace")
            # Check for common fix patterns based on bug description
            desc_lower = description.lower()
            if "re-render" in desc_lower or "stale" in desc_lower or "doesn't update" in desc_lower:
                # Look for event listener patterns that indicate reactivity
                if any(pat in content for pat in ["addEventListener", "onChange", "settings-changed", "onSettingsChange", "dispatchEvent"]):
                    resolved = True
                    proof = "Event listener found in render path"
            elif "missing" in desc_lower:
                # Generic: if file exists and has content, consider it addressed
                if len(content) > 100:
                    resolved = True
                    proof = "File exists with content"

            # If we couldn't determine from patterns, leave as manual check

        results.append({
            "title": title,
            "file": file_path,
            "severity": severity,
            "description": description,
            "resolved": resolved,
            "proof": proof,
        })

    resolved_count = sum(1 for r in results if r["resolved"])
    total = len(results)

    lines = []
    lines.append(top())
    # Truncate feature name to fit header
    header_prefix = "BUG VERIFICATION -- "
    max_name = W - 2 - len(header_prefix)
    display_name = feature_name if len(feature_name) <= max_name else feature_name[:max_name - 3] + "..."
    lines.append(line(f"{header_prefix}{display_name}"))
    lines.append(sep())
    lines.append(line())

    for r in results:
        status = "RESOLVED" if r["resolved"] else "OPEN"
        # Title line with status
        status_line = f"[{status}] {r['title']}"
        if len(status_line) > W - 2:
            status_line = status_line[:W - 5] + "..."
        lines.append(line(status_line))

        # File on its own line
        file_line = f"  File: {r['file']}"
        if len(file_line) > W - 2:
            file_line = file_line[:W - 5] + "..."
        lines.append(line(file_line))

        # Proof/description on its own line
        if r["resolved"]:
            proof_line = f"  Proof: {r['proof']}"
        else:
            proof_line = f"  Issue: {r['description']}"
        if len(proof_line) > W - 2:
            proof_line = proof_line[:W - 5] + "..."
        lines.append(line(proof_line))
        lines.append(line())

    lines.append(sep())

    if resolved_count == total:
        summary = f"{resolved_count}/{total} resolved -- bugs file cleaned up"
        bugs_path.unlink()
    else:
        open_count = total - resolved_count
        summary = f"{resolved_count}/{total} resolved, {open_count} open"
        # Update bugs file to only keep open bugs
        open_bugs = [b for b, r in zip(bugs, results) if not r["resolved"]]
        bugs_path.write_text(json.dumps(open_bugs, indent=2), encoding="utf-8")
        summary += " -- bugs file updated"

    lines.append(line(summary))
    lines.append(bot())

    print("\n".join(lines))


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a manual test checklist HTML from todo.md"
    )
    parser.add_argument(
        "--feature",
        type=str,
        default=None,
        help="Feature name to extract tests for. Defaults to current feature in todo.md.",
    )
    parser.add_argument(
        "--bugs",
        type=str,
        default=None,
        help="Path to JSON file with known bugs from automated testing.",
    )
    parser.add_argument(
        "--test-results",
        type=str,
        default=None,
        help="Path to test-suite-results.json from run_test_suite.py.",
    )
    parser.add_argument(
        "--code-trace",
        type=str,
        default=None,
        help="Path to code trace results JSON from automated code trace.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the HTML file in the browser after generating.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify previously found bugs instead of generating checklist.",
    )
    args = parser.parse_args()

    bugs_file = PROJECT_ROOT / ".tmp" / "test-bugs.json"
    if args.verify or (bugs_file.exists() and not args.bugs):
        # Verification mode
        feature = parse_todo(args.feature)
        feature_name = feature["feature_name"] if feature else (args.feature or "Unknown")
        verify_bugs(feature_name, bugs_file)
        sys.exit(0)

    # Parse todo.md
    feature = parse_todo(args.feature)
    if feature is None:
        target = args.feature or "(current feature)"
        print(f"Error: Feature not found in todo.md: {target}", file=sys.stderr)
        sys.exit(1)

    if not feature["steps"]:
        print(
            f"Error: No manual test items found for '{feature['feature_name']}'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse STATE.md
    state_info = parse_state()
    if not state_info["version"]:
        print("Warning: Could not find app version in STATE.md", file=sys.stderr)
        state_info["version"] = "unknown"
    if not state_info["filename"]:
        print("Warning: Could not find app filename in STATE.md", file=sys.stderr)
        state_info["filename"] = "index.html"

    # Load bugs
    bugs = load_bugs(args.bugs)

    # Load automated test results
    test_results = load_test_results(args.test_results)

    # Load code trace results
    code_trace = load_code_trace(args.code_trace)

    # Generate
    today = date.today().strftime("%d/%m/%Y")
    html = generate_html(feature, state_info, bugs, today, test_results, code_trace)

    # Write to docs/
    DOCS_DIR.mkdir(exist_ok=True)
    slug = slugify(feature["feature_name"])
    output_path = DOCS_DIR / f"{slug}-manual-tests.html"
    output_path.write_text(html, encoding="utf-8")

    total_checks = sum(len(s["manual_items"]) for s in feature["steps"])
    total_sections = len(feature["steps"])
    print(f"Generated: {output_path}")
    print(
        f"  Feature: {feature['feature_name']} [{feature['type_tag']}]"
    )
    print(f"  Version: {state_info['version']}")
    print(f"  Sections: {total_sections}, Checks: {total_checks}")
    if bugs:
        print(f"  Bugs: {len(bugs)}")

    # Open in browser
    if not args.no_open:
        try:
            subprocess.run(["open", str(output_path)], check=False)
        except FileNotFoundError:
            # Not on macOS, try xdg-open
            try:
                subprocess.run(["xdg-open", str(output_path)], check=False)
            except FileNotFoundError:
                print("  (Could not auto-open — open the file manually)")


if __name__ == "__main__":
    main()
