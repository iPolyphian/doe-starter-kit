#!/usr/bin/env python3
"""Snagging orchestrator — runs agent-verify contract checks and collects results.

This script orchestrates the pre-merge verification gate:
1. Reads todo.md to find the current feature's contract criteria
2. Runs each [auto] Verify: pattern
3. Writes pass/fail results to .tmp/snagging-contracts.json
4. Results are consumed by generate_test_checklist.py for HTML rendering
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def find_current_feature(todo_path="tasks/todo.md"):
    """Extract current feature name and its contract criteria from todo.md."""
    text = Path(todo_path).read_text()
    # Find ## Current section
    current_match = re.search(r'## Current\s*\n\s*### (.+)', text)
    if not current_match:
        return None, []

    feature_name = current_match.group(1).strip()

    # Extract all [auto] Verify: patterns
    criteria = []
    for match in re.finditer(r'- \[[ x]\] \[auto\] (.+?)\.?\s*Verify:\s*(.+)', text):
        criteria.append({
            "description": match.group(1).strip(),
            "verify": match.group(2).strip(),
            "status": "pending"
        })

    return feature_name, criteria


def run_verify(verify_pattern):
    """Execute a single Verify: pattern and return pass/fail."""
    pattern = verify_pattern.strip()

    if pattern.startswith("run:"):
        cmd = pattern[4:].strip()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    elif pattern.startswith("file:"):
        rest = pattern[5:].strip()
        if " exists" in rest:
            path = rest.replace(" exists", "").strip()
            path = path.replace("~", str(Path.home()))
            return Path(path).exists()
        elif " contains " in rest:
            parts = rest.split(" contains ", 1)
            path = parts[0].strip().replace("~", str(Path.home()))
            substring = parts[1].strip()
            try:
                return substring in Path(path).read_text()
            except FileNotFoundError:
                return False

    return False


def main():
    """Run agent-verify contract checks for the current feature."""
    feature_name, criteria = find_current_feature()

    if not feature_name:
        print("No current feature found in todo.md")
        sys.exit(1)

    if not criteria:
        print(f"No [auto] criteria found for {feature_name}")
        sys.exit(0)

    print(f"Running contract verification for: {feature_name}")
    print(f"Found {len(criteria)} [auto] criteria\n")

    results = []
    passed = 0
    failed = 0

    for c in criteria:
        success = run_verify(c["verify"])
        c["status"] = "pass" if success else "fail"
        results.append(c)
        if success:
            passed += 1
            print(f"  PASS  {c['description']}")
        else:
            failed += 1
            print(f"  FAIL  {c['description']}")

    print(f"\nResults: {passed} pass, {failed} fail out of {len(criteria)}")

    # Write results for generate_test_checklist.py
    output = {
        "feature": feature_name,
        "total": len(criteria),
        "passed": passed,
        "failed": failed,
        "criteria": results
    }

    output_path = Path(".tmp/snagging-contracts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults written to {output_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
