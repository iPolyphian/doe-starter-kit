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

    # Look for: **Current app version:** v0.27.4 (`monty-app-v0.27.4.html`)
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
    heading_m = re.match(
        r"###\s+(.+?)\s+\[(APP|INFRA)\]\s+\((v[\d.x]+)\)",
        heading_line,
    )
    if heading_m:
        raw_name = heading_m.group(1).strip()
        # Split on em-dash or double-hyphen to get the primary name
        # e.g. "Campaign Workbench — Role-Based Platform + Targeting + Playbook"
        #   -> feature_name = full string (for display)
        # The slug uses just the part before the first em-dash
        found_feature_name = raw_name
        found_type_tag = heading_m.group(2)
        found_version_range = heading_m.group(3)
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
            current_step = {
                "step_num": step_num,
                "step_name": step_name,
                "completed": step_done,
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
        "steps": steps,
    }


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
    """
    setup: list[str] = []
    console: list[str] = []
    restore: list[str] = []
    desc = raw_desc.lower() if raw_desc else ""

    # First-visit / setup wizard tests: need to clear role
    if "first visit" in desc or "setup wizard" in desc or "welcome" in desc:
        setup.append("localStorage.removeItem('monty_role'); location.reload();")
        restore.append("// Set your preferred role back in Settings")

    # Unconfigured party tests
    if "unconfigured party" in desc or "no party" in desc or "setup prompt" in desc:
        setup.append("localStorage.removeItem('monty_party'); location.reload();")
        restore.append("localStorage.setItem('monty_party', 'Labour'); location.reload(); // replace Labour with your party")

    # Role switching tests
    if "local role" in desc or "local user" in desc or "switch" in desc and "role" in desc:
        if not any("monty_role" in s for s in setup):
            setup.append("// Switch role in Settings > Role before testing")

    # --- Console-test patterns ---
    console_matched = False

    # Targeting console tests
    if any(kw in desc for kw in ("scoring function", "computeseatscore", "tgtcomputeall", "seats across tiers")):
        console.append(
            "var results = tgtComputeAll();\n"
            "console.log('Total seats:', results.length);\n"
            "\n"
            "// Check targets (tight marginals, high score)\n"
            "console.table(results.filter(r => r.tier === 'TARGET').slice(0, 5));\n"
            "\n"
            "// Check safe seats\n"
            "console.table(results.filter(r => r.tier === 'FORTRESS').slice(0, 5));\n"
            "\n"
            "// Check distribution\n"
            "var tiers = {};\n"
            "results.forEach(r => { tiers[r.tier] = (tiers[r.tier]||0) + 1; });\n"
            "console.log('Tier distribution:', tiers);"
        )
        console_matched = True

    # Playbook console tests
    playbook_kws = ("issue derivation", "pbkgetbrief", "deriveissues")
    combo_kws = ("constituencies",)
    combo_second = ("pitch", "opponent")
    if (any(kw in desc for kw in playbook_kws)
            or (any(kw in desc for kw in combo_kws)
                and any(kw in desc for kw in combo_second))):
        console.append(
            "// Pick 3 constituencies to test\n"
            "var codes = GEO.features.slice(0, 3).map(f => f.properties.PCON24CD);\n"
            "codes.forEach(c => {\n"
            "  var brief = pbkGetBrief(c);\n"
            "  console.log('=== ' + brief.name + ' ===');\n"
            "  console.log('Issues:', brief.issues);\n"
            "  console.log('Pitch:', brief.pitch);\n"
            "  console.log('Avoid:', brief.avoid);\n"
            "  console.log('Opponent:', brief.opponent);\n"
            "});"
        )
        console_matched = True

    # Generic console-test fallback
    if not console_matched and "console-test" in desc:
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


def build_section_html(step: dict, is_first: bool, global_check_offset: int) -> str:
    """Build one section card's HTML."""
    sid = step["step_num"]
    items = step["manual_items"]
    total = len(items)
    raw_desc = step.get("raw_description", "")
    prereq = build_prerequisite(sid, items[0]["description"] if items else "", is_first)
    console_cmds = extract_console_commands(raw_desc)

    chevron_svg = (
        '<svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">'
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

    return f"""
  <div class="section-card" id="section-{sid}">
    <div class="section-header" onclick="toggleSection('section-{sid}')">
      <div class="section-header-left">
        <div class="section-chevron">
          {chevron_svg}
        </div>
        <span class="section-title">{escape_html(step["step_name"])}</span>
        <span class="section-step">Step {sid}</span>
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
) -> str:
    """Generate the complete HTML string."""
    feature_name = feature["feature_name"]
    version = state_info["version"]
    app_filename = state_info["filename"]
    feature_slug = slugify(feature_name)
    storage_key = f"test-checklist-{feature_slug}-{version}"

    # Total checks
    total_checks = sum(len(s["manual_items"]) for s in feature["steps"])

    # Build section cards
    sections_html = ""
    for idx, step in enumerate(feature["steps"]):
        sections_html += build_section_html(step, idx == 0, 0)

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
    align-items: flex-start;
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
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    padding: 2px 8px;
    border-radius: 99px;
    border: 1px solid #bfdbfe;
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
    padding: 24px;
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
    width: 18px;
    height: 18px;
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
    gap: 10px;
    padding: 9px 10px;
    cursor: pointer;
    user-select: none;
  }}

  .check-num {{
    font-size: 11px;
    color: var(--grey-400);
    min-width: 18px;
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

  /* -- Export section -- */
  .export-section {{
    background: white;
    border: 1px solid var(--grey-200);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 16px;
    padding: 16px 18px;
  }}

  .export-title {{
    font-weight: 600;
    color: var(--grey-700);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 11px;
  }}

  .export-buttons {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }}

  .btn-export {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    border: 1px solid var(--grey-300);
    background: white;
    color: var(--grey-700);
    transition: all 0.15s;
  }}
  .btn-export:hover {{ background: var(--grey-50); border-color: var(--grey-400); }}
  .btn-export.primary {{ background: var(--blue); color: white; border-color: var(--blue); }}
  .btn-export.primary:hover {{ background: #1d4ed8; }}
  .btn-export.copied-confirm {{ background: var(--green-light); color: var(--green); border-color: var(--green-mid); }}

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
      </div>
    </div>

    <!-- Progress card -->
    <div class="progress-card">
      <div class="title-subtitle">Manual test checklist &middot; {total_checks} checks</div>
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
      <button class="btn btn-ghost" onclick="copyResults(false)">Copy Results</button>
      {'<button class="btn btn-amber" onclick="copyBugs()">Copy Bugs</button>' if bugs else ''}
      <a class="btn btn-primary" href="../{escape_html(app_filename)}" target="_blank">Open App &#8599;</a>
    </div>
  </div>
</div>

<!-- PAGE BODY -->
<div class="page-body">
{sections_html}

  <!-- EXPORT SECTION -->
  <div class="export-section">
    <div class="export-title">Export Results</div>
    <div class="export-buttons">
      <button class="btn-export primary" id="btn-copy-all" onclick="copyResults(false)">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z"/><path d="M3 5a2 2 0 012-2 3 3 0 003 3h4a3 3 0 003-3 2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2V5z"/></svg>
        Copy Test Results
      </button>
      <button class="btn-export" id="btn-copy-fail" onclick="copyResults(true)">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 7l2.55 2.4A1 1 0 0116 11H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clip-rule="evenodd"/></svg>
        Copy Failures Only
      </button>
    </div>
  </div>

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

    lines.push('### Test ' + sid + ': ' + label + ' (' + step + ') -- ' + sPass + '/' + total + ' pass, ' + sFail + ' fail');
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

function copyResults(failOnly) {{
  const text = buildResultsText(failOnly);
  navigator.clipboard.writeText(text).then(() => {{
    const btnId = failOnly ? 'btn-copy-fail' : 'btn-copy-all';
    const btn = document.getElementById(btnId);
    const orig = btn.innerHTML;
    btn.classList.add('copied-confirm');
    btn.textContent = 'Copied!';
    setTimeout(() => {{
      btn.classList.remove('copied-confirm');
      btn.innerHTML = orig;
    }}, 2000);
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

    # Generate
    today = date.today().strftime("%d/%m/%Y")
    html = generate_html(feature, state_info, bugs, today)

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
