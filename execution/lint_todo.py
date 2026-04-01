#!/usr/bin/env python3
"""Structural linter for tasks/todo.md.

Validates three rules in ## Current and ## Queue:
1. Every numbered step has a Contract: block
2. Every feature's last numbered step is Retro
3. [APP] features have at least one [manual] criterion

Called by pre-commit hook when todo.md is staged.
Skip with: SKIP_TODO_LINT=1
"""

import re
import sys
from pathlib import Path

STEP_RE = re.compile(r"^\s*\d+[a-d]?\.\s+\[[ x]\]\s+(.*)")
CONTRACT_RE = re.compile(r"^\s+Contract:\s*$")
FEATURE_RE = re.compile(r"^###\s+(.*)")
SECTION_RE = re.compile(r"^##\s+(\S+)")

SCOPE_SECTIONS = {"Current", "Queue"}


def lint_todo(path="tasks/todo.md"):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    errors = []

    in_scope = False
    feature_name = None
    feature_line = 0
    feature_is_app = False
    feature_has_manual = False
    steps = []  # (line_num, name, has_contract)
    pending_step = None  # (line_num, name) waiting for Contract:

    def flush_feature():
        nonlocal feature_name, steps, pending_step
        if pending_step:
            steps.append((*pending_step, False))
            pending_step = None
        if feature_name is None or not steps:
            return

        for line_num, name, has_contract in steps:
            # Completed retros with [quick:] or [full:] are exempt
            if "Retro" in name and ("[quick:" in name or "[full:" in name):
                continue
            if not has_contract:
                errors.append(f"Line {line_num}: Step has no Contract: block")

        _, last_name, _ = steps[-1]
        if "Retro" not in last_name:
            short = feature_name[:50]
            errors.append(f"Line {feature_line}: '{short}' -- last step is not Retro")

        if feature_is_app and not feature_has_manual:
            short = feature_name[:50]
            errors.append(f"Line {feature_line}: [APP] '{short}' has no [manual] criterion")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        sm = SECTION_RE.match(stripped)
        if sm:
            section = sm.group(1)
            if section in SCOPE_SECTIONS:
                flush_feature()
                feature_name = None
                steps = []
                in_scope = True
            elif in_scope:
                flush_feature()
                feature_name = None
                steps = []
                in_scope = False
            continue

        if not in_scope:
            continue

        fm = FEATURE_RE.match(stripped)
        if fm:
            flush_feature()
            feature_name = fm.group(1)
            feature_line = i
            feature_is_app = "[APP]" in feature_name
            feature_has_manual = False
            steps = []
            continue

        if feature_name is None:
            continue

        step_m = STEP_RE.match(line)
        if step_m:
            if pending_step:
                steps.append((*pending_step, False))
            pending_step = (i, step_m.group(1))
            continue

        if CONTRACT_RE.match(line) and pending_step:
            steps.append((*pending_step, True))
            pending_step = None
            continue

        if "[manual]" in stripped:
            feature_has_manual = True

    flush_feature()
    return errors


def main():
    path = "tasks/todo.md"
    if not Path(path).exists():
        print("tasks/todo.md not found")
        sys.exit(1)

    errors = lint_todo(path)
    if errors:
        print()
        print("\u2550\u2550\u2550 todo.md structure errors \u2550\u2550\u2550")
        print()
        for e in errors:
            print(f"  {e}")
        print()
        print("Skip with: SKIP_TODO_LINT=1 git commit -m '...'")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
