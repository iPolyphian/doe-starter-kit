#!/usr/bin/env python3
"""Bootstrap invariants from completed contracts.

One-time migration tool for existing DOE projects upgrading to v1.49+.
Parses completed contracts from todo.md and archive.md, filters to
infrastructure patterns, runs them against the current codebase, and
generates a candidate tests/invariants.txt.

Usage:
    python3 execution/bootstrap_invariants.py              # show report
    python3 execution/bootstrap_invariants.py --write      # append new invariants to file
    python3 execution/bootstrap_invariants.py --dry-run    # show what --write would add
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Contracts referencing these paths are invariant candidates
INFRA_PATHS = [
    "CLAUDE.md", "directives/", ".claude/agents/", ".claude/hooks/",
    ".claude/settings", "execution/", ".github/workflows/", ".github/pull_request",
    ".githooks/", "SYSTEM-MAP.md", "CUSTOMIZATION.md", "tests/",
]

# Skip patterns containing version numbers (ephemeral)
VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")


def _extract_verify_patterns(text: str) -> list[str]:
    """Extract Verify: patterns from completed [x] contract items."""
    patterns = []
    for line in text.splitlines():
        stripped = line.strip()
        # Must be a completed auto criterion with a Verify: pattern
        if not stripped.startswith("- [x] [auto]"):
            continue
        match = re.search(r"Verify:\s*(.+?)(?:\s*\[|\s*$)", stripped)
        if match:
            pattern = match.group(1).strip()
            # Clean trailing timestamps or comments
            pattern = re.sub(r"\s*\*\(completed.*$", "", pattern).strip()
            pattern = re.sub(r"\s*\*\(signed.*$", "", pattern).strip()
            if pattern:
                patterns.append(pattern)
    return patterns


def _references_infra(pattern: str) -> bool:
    """Check if a Verify: pattern references infrastructure files."""
    # For file: and html: patterns, extract the path
    if pattern.startswith("file:") or pattern.startswith("html:"):
        path_part = pattern.split(":", 1)[1].strip().split()[0]
        return any(path_part.startswith(p) or path_part == p.rstrip("/")
                    for p in INFRA_PATHS)
    # For run: patterns, check if command string mentions infra paths
    if pattern.startswith("run:"):
        cmd = pattern[4:].strip()
        return any(p.rstrip("/") in cmd for p in INFRA_PATHS)
    return False


def _is_version_specific(pattern: str) -> bool:
    """Check if a pattern contains version numbers (ephemeral)."""
    return bool(VERSION_RE.search(pattern))


def _run_pattern(pattern: str) -> bool:
    """Execute a Verify: pattern and return True if it passes."""
    try:
        if pattern.startswith("file:"):
            rest = pattern[5:].strip()
            if " exists" in rest:
                path = rest.replace(" exists", "").strip()
                target = (Path(os.path.expanduser(path)) if path.startswith("~")
                          else PROJECT_ROOT / path)
                return target.exists()
            elif " contains " in rest:
                parts = rest.split(" contains ", 1)
                path = parts[0].strip()
                needle = parts[1].strip()
                target = (Path(os.path.expanduser(path)) if path.startswith("~")
                          else PROJECT_ROOT / path)
                if target.exists():
                    return needle in target.read_text(encoding="utf-8")
                return False
        elif pattern.startswith("run:"):
            cmd = pattern[4:].strip()
            result = subprocess.run(
                cmd, shell=True, cwd=str(PROJECT_ROOT),
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        elif pattern.startswith("html:"):
            return True  # skip html: patterns (need BeautifulSoup)
    except (subprocess.TimeoutExpired, Exception):
        return False
    return False


def _load_existing_invariants() -> set[str]:
    """Load patterns already in tests/invariants.txt."""
    inv_file = PROJECT_ROOT / "tests" / "invariants.txt"
    if not inv_file.exists():
        return set()
    existing = set()
    for line in inv_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            existing.add(stripped)
    return existing


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap invariants from completed contracts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
One-time migration for existing DOE projects upgrading to v1.49+.
Run once to establish your invariant baseline, then the automated
quality gate handles everything going forward.

Steps:
  1. Run this script (no flags) to see the report
  2. Review TRIAGE items -- decide promote or discard
  3. Run with --write to append new invariants to tests/invariants.txt
  4. Commit tests/invariants.txt
  5. Done -- automation keeps it clean from here
        """,
    )
    parser.add_argument("--write", action="store_true",
                        help="Append new invariants to tests/invariants.txt")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what --write would add without writing")
    args = parser.parse_args()

    # Collect all Verify: patterns from completed contracts
    all_patterns = []
    sources = [
        PROJECT_ROOT / "tasks" / "todo.md",
        PROJECT_ROOT / "tasks" / "archive.md",
    ]

    for src in sources:
        if src.exists():
            text = src.read_text(encoding="utf-8")
            patterns = _extract_verify_patterns(text)
            all_patterns.extend(patterns)

    # Deduplicate (keep last occurrence -- later features are more current)
    seen = {}
    for p in all_patterns:
        seen[p] = True  # later entries overwrite earlier
    unique_patterns = list(seen.keys())

    if not unique_patterns:
        print("No completed contracts found in todo.md or archive.md.")
        print("This is normal for new projects -- invariants will grow via retro promotion.")
        return

    # Classify
    existing = _load_existing_invariants()
    promote = []    # infra, not version-specific, passes, not already in file
    triage = []     # infra, not version-specific, FAILS
    skip_version = []  # contains version number
    skip_noinfra = []  # doesn't reference infrastructure
    already = []    # already in invariants.txt

    for pattern in unique_patterns:
        if _is_version_specific(pattern):
            skip_version.append(pattern)
            continue
        if not _references_infra(pattern):
            skip_noinfra.append(pattern)
            continue
        if pattern in existing:
            already.append(pattern)
            continue
        # Run the pattern
        if _run_pattern(pattern):
            promote.append(pattern)
        else:
            triage.append(pattern)

    # Report
    total = len(unique_patterns)
    print(f"\n  Scanned {total} completed contracts from {len(sources)} file(s)\n")
    print(f"  PROMOTE     {len(promote):>3}  (infra, passes, new)")
    print(f"  TRIAGE      {len(triage):>3}  (infra, FAILS -- intentional change or real drift?)")
    print(f"  ALREADY     {len(already):>3}  (already in invariants.txt)")
    print(f"  SKIP (ver)  {len(skip_version):>3}  (version-specific, ephemeral)")
    print(f"  SKIP (non)  {len(skip_noinfra):>3}  (non-infrastructure)")

    if promote:
        print(f"\n  --- PROMOTE ({len(promote)}) ---")
        for p in promote:
            print(f"  + {p}")

    if triage:
        print(f"\n  --- TRIAGE ({len(triage)}) ---")
        print("  These failed -- decide: intentional change (discard) or drift (fix)?")
        for p in triage:
            print(f"  ? {p}")

    if args.dry_run or args.write:
        if not promote:
            print("\n  Nothing new to add.")
            return

        # Group by category for the output
        lines = ["\n# Bootstrapped from completed contracts"]
        for p in sorted(promote):
            lines.append(p)

        if args.dry_run:
            print("\n  --- Would append to tests/invariants.txt ---")
            for line in lines:
                print(f"  {line}")
        elif args.write:
            inv_file = PROJECT_ROOT / "tests" / "invariants.txt"
            with open(inv_file, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"\n  Appended {len(promote)} invariants to {inv_file}")
            print("  Review the file and commit when satisfied.")
    elif promote:
        print(f"\n  Run with --write to append {len(promote)} new invariants to tests/invariants.txt")
        print("  Run with --dry-run to preview first")


if __name__ == "__main__":
    main()
