#!/usr/bin/env python3
"""Check plan freshness: version conflicts, dead file references, CLAUDE.md drift, plan age.

Called automatically by PostToolUse hook when any .claude/plans/*.md is read.
Also callable directly: python3 execution/check_plan_freshness.py <plan-path>
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TODO_PATH = Path("tasks/todo.md")
STATE_PATH = Path("STATE.md")
KIT_DIR = Path.home() / "doe-starter-kit"

# Known file renames. Script checks if contracts reference the old name
# when the new name exists. Add entries when files are renamed.
KNOWN_RENAMES = {
    ".github/workflows/test.yml": ".github/workflows/doe-ci.yml",
}


def find_feature_for_plan(plan_name):
    """Find the feature in todo.md that references this plan file. Returns (name, section, start_line)."""
    if not TODO_PATH.exists():
        return None, None, None
    lines = TODO_PATH.read_text(encoding="utf-8").splitlines()
    section = None
    feature = None
    feature_line = 0
    for i, line in enumerate(lines):
        sm = re.match(r"^## (\S+)", line)
        if sm:
            section = sm.group(1)
            continue
        fm = re.match(r"^### (.+)", line)
        if fm:
            feature = fm.group(1)
            feature_line = i
            continue
        if plan_name in line and feature:
            return feature, section, feature_line
    return None, None, None


def extract_version(feature_name):
    """Extract (major, minor) from 'Feature [INFRA] (v1.51.x)'."""
    m = re.search(r"\(v(\d+)\.(\d+)\.", feature_name)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def get_kit_version():
    """Current kit tag as (major, minor)."""
    try:
        r = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(KIT_DIR), capture_output=True, text=True, timeout=5,
        )
        m = re.match(r"v(\d+)\.(\d+)", r.stdout.strip())
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)
    except Exception:
        return None, None


def get_app_version():
    """Current app version from STATE.md as (major, minor)."""
    try:
        m = re.search(r"Current app version:\s*v(\d+)\.(\d+)", STATE_PATH.read_text())
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)
    except Exception:
        return None, None


def extract_file_refs(feature_name):
    """Extract file paths from Verify: patterns in a feature's contracts."""
    if not TODO_PATH.exists():
        return []
    lines = TODO_PATH.read_text(encoding="utf-8").splitlines()
    in_feature = False
    prefix = feature_name.split("[")[0].strip()
    refs = []

    for line in lines:
        if re.match(r"^### " + re.escape(prefix), line):
            in_feature = True
            continue
        if in_feature and (re.match(r"^### ", line) or re.match(r"^## ", line)):
            break
        if not in_feature:
            continue

        # file: <path> exists
        m = re.search(r"Verify:\s*file:\s*(.+?)\s+exists\s*$", line)
        if m:
            refs.append(("exists", m.group(1).strip()))
            continue
        # file: <path> contains <string>
        m = re.search(r"Verify:\s*file:\s*(.+?)\s+contains\s+(.+)", line)
        if m:
            refs.append(("contains", m.group(1).strip(), m.group(2).strip()))

    return refs


def expand(p):
    """Expand ~ to home directory."""
    return str(Path(p).expanduser()) if p.startswith("~") else p


def check_freshness(plan_path):
    """Run all freshness checks. Returns list of (severity, message)."""
    plan_path = Path(plan_path)
    if not plan_path.exists():
        return [("ERROR", f"Plan file not found: {plan_path}")]

    plan_name = plan_path.name
    feature, section, _ = find_feature_for_plan(plan_name)
    if not feature:
        return []  # Not referenced in todo.md — archived or informational plan

    warnings = []

    # --- Version conflict ---
    major, minor = extract_version(feature)
    if major is not None:
        file_refs = extract_file_refs(feature)
        is_kit = any("doe-starter-kit" in str(r) for r in file_refs)

        if is_kit:
            cur_major, cur_minor = get_kit_version()
            label = "kit"
        else:
            cur_major, cur_minor = get_app_version()
            label = "app"

        if cur_major is not None and (major, minor) <= (cur_major, cur_minor):
            warnings.append(
                ("VERSION", f"v{major}.{minor}.x planned but {label} is v{cur_major}.{cur_minor} -- version taken")
            )

    # --- Renamed file references (all features -- catches stale paths regardless of section) ---
    file_refs = extract_file_refs(feature)
    for ref in file_refs:
        raw_path = ref[1]
        for old, new in KNOWN_RENAMES.items():
            if old in raw_path:
                warnings.append(("RENAMED", f"{old} -> {new} (update contract)"))
                break

    # --- Dead file references (only for Current features -- Queue files don't exist yet) ---
    if section == "Current":
        missing_count = 0
        for ref in file_refs:
            path = expand(ref[1])
            if not Path(path).exists():
                if missing_count < 5:  # Cap output
                    warnings.append(("MISSING", f"{ref[1]} -- not found"))
                missing_count += 1
        if missing_count > 5:
            warnings.append(("MISSING", f"...and {missing_count - 5} more missing files"))

    # --- CLAUDE.md drift (check for any feature -- CLAUDE.md exists regardless of build state) ---
    for ref in file_refs:
        if ref[0] == "contains" and "CLAUDE.md" in ref[1]:
            path = expand(ref[1])
            if Path(path).exists():
                content = Path(path).read_text(encoding="utf-8")
                if ref[2] not in content:
                    warnings.append(
                        ("DRIFT", f'CLAUDE.md no longer contains "{ref[2]}" -- may have moved to a directive')
                    )

    # --- Plan age ---
    plan_text = plan_path.read_text(encoding="utf-8")
    latest = None
    for m in re.finditer(r"(\d{2}/\d{2}/\d{2})", plan_text):
        try:
            d = datetime.strptime(m.group(1), "%d/%m/%y")
            if latest is None or d > latest:
                latest = d
        except ValueError:
            pass
    if latest:
        age = (datetime.now() - latest).days
        if age > 14:
            warnings.append(("AGE", f"last updated {latest.strftime('%d/%m/%y')} ({age} days ago) -- review recommended"))

    return warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: check_plan_freshness.py <plan-file-path>")
        sys.exit(1)

    warnings = check_freshness(sys.argv[1])
    if warnings:
        name = Path(sys.argv[1]).name
        print(f"\nPlan freshness ({name}):")
        for sev, msg in warnings:
            print(f"  {sev}: {msg}")
        print()
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
