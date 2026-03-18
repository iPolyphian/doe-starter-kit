#!/usr/bin/env python3
"""Wrapper for Verify: patterns in todo.md contracts.

Usage: python3 execution/verify_tests.py --suite app|accessibility|visual
Exits 0 if all tests pass, 1 if any fail, 2 if tool error.
"""

import json
import subprocess
import sys


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--suite":
        print(
            "Usage: python3 execution/verify_tests.py --suite app|accessibility|visual",
            file=sys.stderr,
        )
        sys.exit(2)

    suite = sys.argv[2]
    valid = {"app", "accessibility", "visual"}
    if suite not in valid:
        print(
            f"Invalid suite: {suite}. Must be one of: {', '.join(sorted(valid))}",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        result = subprocess.run(
            ["npx", "playwright", "test", f"tests/{suite}.spec.js", "--reporter=json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        try:
            data = json.loads(result.stdout)
            unexpected = data.get("stats", {}).get("unexpected", 0)
            if unexpected > 0:
                print(f"FAIL: {unexpected} unexpected result(s) in {suite}")
                sys.exit(1)
            expected = data.get("stats", {}).get("expected", 0)
            print(f"PASS: {expected} tests in {suite} passed")
            sys.exit(0)
        except json.JSONDecodeError:
            print("Error: Could not parse Playwright JSON output", file=sys.stderr)
            if result.returncode != 0:
                print(
                    f"Playwright exited with code {result.returncode}",
                    file=sys.stderr,
                )
                sys.exit(1)
            sys.exit(2)
    except FileNotFoundError:
        print(
            "Error: Playwright not found. Run: npx playwright install",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print(f"Error: {suite} tests timed out after 120s", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
