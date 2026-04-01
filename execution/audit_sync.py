#!/usr/bin/env python3
"""Audit project DOE files against the starter kit.

Compares syncable directories and flags universal files that exist in
the project but not in the kit. Runs as a pre-flight check before
/sync-doe to prevent accidental omissions.

Usage:
  python3 execution/audit_sync.py              # summary
  python3 execution/audit_sync.py --verbose    # show file-level detail
  python3 execution/audit_sync.py --json       # machine-readable output
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Project-specific patterns -- files containing these are NOT universal
PROJECT_PATTERNS = re.compile(
    r"\b(monty|constituency|constituencies|pcon\d{2}|pulse|broker|pleasantly"
    r"|restore.britain|albion.labs|election|mp[_\s]interest|census"
    r"|council.control|swing.model|voting.record|canvass|briefing.pack"
    r"|candidate.vett|scenario.builder|ward.level)\b",
    re.IGNORECASE,
)

# Files that are always project-specific by nature (skip without scanning)
ALWAYS_PROJECT_SPECIFIC = {
    "build.py",
    "test_build.py",
    "lighthouse.sh",
    "curated_votes.json",
}

# Files that need stripping before sync (universal structure, project content)
NEEDS_STRIPPING = {
    "build_session_archive.py",
}

# Kit-only files (exist in kit, not expected in project)
KIT_ONLY = {
    "stamp_tutorial_version.py",
}

# Directories to compare: (project_path, kit_path, description)
KIT_ROOT = Path.home() / "doe-starter-kit"


def get_sync_pairs(project_root):
    """Return list of (project_dir, kit_dir, label) to compare."""
    p = Path(project_root)
    k = KIT_ROOT
    pairs = [
        (p / "execution", k / "execution", "execution/", True),
        (p / ".githooks", k / ".githooks", ".githooks/", True),
        (p / ".claude" / "hooks", k / ".claude" / "hooks", ".claude/hooks/", True),
        (p / ".claude" / "agents", k / ".claude" / "agents", ".claude/agents/", True),
        (p / ".claude" / "commands", k / "global-commands", "commands/", False),
        (p / "directives", k / "directives", "directives/", True),
        (p / "tests" / "execution", k / "tests" / "execution", "tests/execution/", True),
    ]
    # check_kit_only=False for commands: global commands install to ~/.claude/commands/,
    # not the project's .claude/commands/. Kit-only commands are expected.
    return pairs


def list_files(directory):
    """List all files in a directory (non-recursive for flat dirs, recursive for nested)."""
    if not directory.exists():
        return set()
    files = set()
    for f in directory.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            files.add(str(f.relative_to(directory)))
    return files


def has_project_references(filepath):
    """Check if a file contains project-specific references."""
    try:
        text = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        return bool(PROJECT_PATTERNS.search(text))
    except Exception:
        return False


def files_differ(path_a, path_b):
    """Check if two files have different content."""
    try:
        return path_a.read_bytes() != path_b.read_bytes()
    except Exception:
        return True


def audit(project_root, verbose=False):
    """Run the full sync audit. Returns findings dict."""
    if not KIT_ROOT.exists():
        return {"error": "Kit not found at ~/doe-starter-kit"}

    pairs = get_sync_pairs(project_root)
    findings = {
        "missing_from_kit": [],  # universal files in project, not in kit
        "needs_stripping": [],   # universal structure but has project content
        "project_specific": [],  # correctly not in kit
        "kit_only": [],          # in kit, not in project
        "diverged": [],          # in both, content differs
        "in_sync": [],           # in both, identical
    }

    for proj_dir, kit_dir, label, check_kit_only in pairs:
        proj_files = list_files(proj_dir)
        kit_files = list_files(kit_dir)

        # Files only in project
        for f in sorted(proj_files - kit_files):
            filepath = proj_dir / f
            name = filepath.name

            if name in ALWAYS_PROJECT_SPECIFIC:
                findings["project_specific"].append(f"{label}{f}")
                continue

            if name in KIT_ONLY:
                continue

            if name in NEEDS_STRIPPING:
                findings["needs_stripping"].append(f"{label}{f}")
                continue

            if has_project_references(filepath):
                findings["project_specific"].append(f"{label}{f}")
            else:
                findings["missing_from_kit"].append(f"{label}{f}")

        # Files only in kit
        if check_kit_only:
            for f in sorted(kit_files - proj_files):
                name = Path(f).name
                if name not in KIT_ONLY:
                    findings["kit_only"].append(f"{label}{f}")

        # Files in both
        for f in sorted(proj_files & kit_files):
            proj_path = proj_dir / f
            kit_path = kit_dir / f
            if files_differ(proj_path, kit_path):
                findings["diverged"].append(f"{label}{f}")
            else:
                findings["in_sync"].append(f"{label}{f}")

    return findings


def print_summary(findings):
    """Print a human-readable summary."""
    missing = findings.get("missing_from_kit", [])
    diverged = findings.get("diverged", [])
    kit_only = findings.get("kit_only", [])
    project_specific = findings.get("project_specific", [])
    in_sync = findings.get("in_sync", [])

    needs_strip = findings.get("needs_stripping", [])
    total_issues = len(missing) + len(needs_strip) + len(diverged) + len(kit_only)

    if total_issues == 0:
        print("All DOE files in sync. Nothing to do.")
        return

    print()
    print(f"{'=' * 50}")
    print(f"  SYNC AUDIT — {total_issues} item(s) need attention")
    print(f"{'=' * 50}")

    if missing:
        print(f"\n  MISSING FROM KIT ({len(missing)} universal files):")
        for f in missing:
            print(f"    + {f}")

    if needs_strip:
        print(f"\n  NEEDS STRIPPING ({len(needs_strip)} universal structure, project content):")
        for f in needs_strip:
            print(f"    * {f}")

    if diverged:
        print(f"\n  DIVERGED ({len(diverged)} files differ):")
        for f in diverged:
            print(f"    ~ {f}")

    if kit_only:
        print(f"\n  KIT ONLY ({len(kit_only)} files not in project):")
        for f in kit_only:
            print(f"    ? {f}")

    print(f"\n  In sync: {len(in_sync)} | Project-specific: {len(project_specific)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Audit project DOE files against kit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all categories")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--project", default=".", help="Project root (default: cwd)")
    args = parser.parse_args()

    project_root = Path(args.project).resolve()

    if not KIT_ROOT.exists():
        print("Error: ~/doe-starter-kit not found")
        sys.exit(1)

    findings = audit(project_root)

    if "error" in findings:
        print(f"Error: {findings['error']}")
        sys.exit(1)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print_summary(findings)

    # Exit 1 if there are items needing attention
    missing = findings.get("missing_from_kit", [])
    if missing:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
