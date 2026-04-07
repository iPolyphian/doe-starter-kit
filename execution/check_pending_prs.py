#!/usr/bin/env python3
"""Pre-commit check: validate ## Pending PRs in todo.md against GitHub.

Blocks if todo.md lists a PR that is no longer open (merged/closed).
Warns if an open PR is missing from todo.md.
Skips gracefully if `gh` is unavailable or network fails.

Called from .githooks/pre-commit when tasks/todo.md is staged.
Skip with: SKIP_PENDING_PR_CHECK=1 git commit ...
"""

import re
import subprocess
import json
import sys
from pathlib import Path


def get_open_prs():
    """Query GitHub for open PRs. Returns dict of {number: title} or None on failure."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number,title"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        prs = json.loads(result.stdout)
        return {pr["number"]: pr["title"] for pr in prs}
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return None


def get_todo_pr_numbers():
    """Parse ### #N headings from ## Pending PRs section in todo.md."""
    todo = Path("tasks/todo.md")
    if not todo.exists():
        return []
    text = todo.read_text()

    # Extract section between ## Pending PRs and the next ## heading
    match = re.search(r'^## Pending PRs\s*\n(.*?)(?=^## |\Z)', text,
                      re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    return [int(m) for m in re.findall(r'^### #(\d+)', section, re.MULTILINE)]


def main():
    open_prs = get_open_prs()
    if open_prs is None:
        # Network/gh unavailable — skip silently
        return 0

    todo_prs = get_todo_pr_numbers()
    open_numbers = set(open_prs.keys())
    todo_numbers = set(todo_prs)

    errors = []
    warnings = []

    # Stale entries: in todo.md but not open on GitHub
    stale = todo_numbers - open_numbers
    for n in sorted(stale):
        errors.append(f"  PR #{n} is no longer open -- remove from Pending PRs")

    # Missing entries: open on GitHub but not in todo.md
    missing = open_numbers - todo_numbers
    for n in sorted(missing):
        title = open_prs[n]
        warnings.append(f"  PR #{n} ({title}) is open but not in Pending PRs")

    if errors:
        print("", file=sys.stderr)
        print("═══ Pending PRs out of sync ═══", file=sys.stderr)
        print("", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        if warnings:
            print("", file=sys.stderr)
            for w in warnings:
                print(f"⚠ {w}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Skip with: SKIP_PENDING_PR_CHECK=1 git commit ...", file=sys.stderr)
        return 1

    if warnings:
        for w in warnings:
            print(f"⚠ {w}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
