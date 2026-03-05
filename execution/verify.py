#!/usr/bin/env python3
"""Shared verification engine for DOE contract criteria.

Parses and executes Verify: patterns from todo.md contracts and wave JSON.
Four executable patterns:
  - run: <shell command>       -- execute, check exit code 0
  - file: <path> exists        -- check file existence
  - file: <path> contains <s>  -- check file content for substring
  - html: <path> has <sel>     -- parse HTML, check CSS selector

Usage:
  python3 execution/verify.py --self-test          # run internal tests
  python3 execution/verify.py --check-step N       # verify step N from todo.md
  python3 execution/verify.py --check-criteria 'file: foo.txt exists'  # verify one criterion
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def find_project_root():
    """Walk up from cwd to find tasks/todo.md."""
    p = Path.cwd()
    while p != p.parent:
        if (p / "tasks" / "todo.md").exists():
            return p
        p = p.parent
    return Path.cwd()


ROOT = find_project_root()


def load_config():
    """Load tests/config.json, returning defaults if missing."""
    config_path = ROOT / "tests" / "config.json"
    defaults = {"buildCommand": "", "testTimeout": 30, "projectType": "", "dependencies": []}
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            defaults.update(cfg)
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def parse_verify_pattern(text):
    """Parse a Verify: pattern string into a structured dict.

    Returns: {"type": "run"|"file_exists"|"file_contains"|"html_has", ...}
             or {"type": "invalid", "raw": text} if no pattern matches.
    """
    text = text.strip()

    # run: <command>
    m = re.match(r"^run:\s+(.+)$", text)
    if m:
        return {"type": "run", "command": m.group(1)}

    # file: <path> contains <string>
    m = re.match(r"^file:\s+(.+?)\s+contains\s+(.+)$", text)
    if m:
        return {"type": "file_contains", "path": m.group(1), "substring": m.group(2)}

    # file: <path> exists
    m = re.match(r"^file:\s+(.+?)\s+exists$", text)
    if m:
        return {"type": "file_exists", "path": m.group(1)}

    # html: <path> has <selector>
    m = re.match(r"^html:\s+(.+?)\s+has\s+(.+)$", text)
    if m:
        return {"type": "html_has", "path": m.group(1), "selector": m.group(2)}

    return {"type": "invalid", "raw": text}


def resolve_path(p, base=None):
    """Resolve a path relative to a base directory (default: project root), expanding ~."""
    expanded = os.path.expanduser(p)
    path = Path(expanded)
    if path.is_absolute():
        return path
    return (base or ROOT) / path


def run_criterion(criterion, working_dir=None):
    """Execute a single verification criterion.

    Args:
        criterion: either a string (Verify: pattern) or a dict with 'verify' key.
        working_dir: optional path (str or Path) for resolving relative file paths
                     and running commands. Defaults to project root. Used by wave
                     agents to verify files in worktree context.

    Returns:
        {"status": "PASS"|"FAIL"|"SKIP", "detail": str}
    """
    config = load_config()
    timeout = config.get("testTimeout", 30)
    base = Path(working_dir) if working_dir else ROOT

    # Accept both string and dict forms
    if isinstance(criterion, dict):
        verify_text = criterion.get("verify", criterion.get("raw", ""))
    else:
        verify_text = str(criterion)

    parsed = parse_verify_pattern(verify_text)

    if parsed["type"] == "invalid":
        return {"status": "FAIL", "detail": f"Invalid pattern: {verify_text}"}

    if parsed["type"] == "run":
        return _run_command(parsed["command"], timeout, cwd=base)

    if parsed["type"] == "file_exists":
        path = resolve_path(parsed["path"], base=base)
        if path.exists():
            return {"status": "PASS", "detail": f"{parsed['path']} exists"}
        return {"status": "FAIL", "detail": f"{parsed['path']} not found"}

    if parsed["type"] == "file_contains":
        path = resolve_path(parsed["path"], base=base)
        if not path.exists():
            return {"status": "FAIL", "detail": f"{parsed['path']} not found"}
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if parsed["substring"] in content:
                return {"status": "PASS", "detail": f"{parsed['path']} contains '{parsed['substring']}'"}
            return {"status": "FAIL", "detail": f"{parsed['path']} does not contain '{parsed['substring']}'"}
        except OSError as e:
            return {"status": "FAIL", "detail": f"Cannot read {parsed['path']}: {e}"}

    if parsed["type"] == "html_has":
        return _check_html(parsed["path"], parsed["selector"], base=base)

    return {"status": "FAIL", "detail": f"Unknown pattern type: {parsed['type']}"}


def _run_command(command, timeout, cwd=None):
    """Execute a shell command and check exit code."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"status": "PASS", "detail": f"Command succeeded: {command}"}
        stderr = result.stderr.strip()[:200] if result.stderr else ""
        return {"status": "FAIL", "detail": f"Exit code {result.returncode}: {command}" + (f"\n  {stderr}" if stderr else "")}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "detail": f"Timeout after {timeout}s: {command}"}
    except OSError as e:
        return {"status": "FAIL", "detail": f"Cannot execute: {e}"}


def _check_html(path_str, selector, base=None):
    """Parse HTML and check for a CSS selector."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"status": "SKIP", "detail": "beautifulsoup4 not installed -- skipping html: check"}

    path = resolve_path(path_str, base=base)
    if not path.exists():
        return {"status": "FAIL", "detail": f"{path_str} not found"}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        matches = soup.select(selector)
        if matches:
            return {"status": "PASS", "detail": f"{path_str} has {selector} ({len(matches)} match{'es' if len(matches) != 1 else ''})"}
        return {"status": "FAIL", "detail": f"{path_str} does not have {selector}"}
    except Exception as e:
        return {"status": "FAIL", "detail": f"HTML parse error: {e}"}


def run_all_criteria(criteria, working_dir=None):
    """Execute a list of criteria and return results.

    Args:
        criteria: list of strings or dicts with 'verify' key.
        working_dir: optional path for resolving relative paths (worktree context).

    Returns:
        list of {"status", "detail", "criterion"} dicts.
    """
    results = []
    for c in criteria:
        result = run_criterion(c, working_dir=working_dir)
        result["criterion"] = c if isinstance(c, str) else c.get("verify", c.get("text", str(c)))
        results.append(result)
    return results


def run_build_step(working_dir=None):
    """Run the build command from tests/config.json if configured."""
    config = load_config()
    build_cmd = config.get("buildCommand", "")
    if not build_cmd:
        return None
    timeout = config.get("testTimeout", 30) * 2  # Build gets double timeout
    base = Path(working_dir) if working_dir else ROOT
    result = _run_command(build_cmd, timeout, cwd=base)
    return result


def parse_todo_contract(step_number=None):
    """Parse contract criteria from todo.md for a given step.

    Args:
        step_number: int, the step number to find. If None, finds first unchecked step.

    Returns:
        list of {"text": str, "type": "auto"|"manual", "verify": str, "checked": bool}
    """
    todo_path = ROOT / "tasks" / "todo.md"
    if not todo_path.exists():
        return []

    lines = todo_path.read_text().splitlines()
    in_current = False
    target_idx = None

    for i, line in enumerate(lines):
        if line.strip().startswith("## Current"):
            in_current = True
            continue
        if in_current and line.strip().startswith("## "):
            break
        if not in_current:
            continue

        if step_number is not None:
            m = re.match(r"(\d+)\.\s+\[[ x]\]", line.strip())
            if m and int(m.group(1)) == step_number:
                target_idx = i
                break
        else:
            if re.match(r"\d+\.\s+\[ \]", line.strip()):
                target_idx = i
                break

    if target_idx is None:
        return []

    # Extract contract block
    criteria = []
    found_contract = False

    for j in range(target_idx + 1, len(lines)):
        line = lines[j]
        stripped = line.strip()

        if re.match(r"\d+\.\s+\[", stripped):
            break

        if stripped.lower().startswith("contract:"):
            found_contract = True
            continue

        if found_contract:
            m = re.match(r"-\s+\[([ x])\]\s+\[(auto|manual)\]\s+(.*)", stripped)
            if m:
                checked = m.group(1) == "x"
                ctype = m.group(2)
                text = m.group(3)
                # Extract Verify: pattern if present
                vm = re.match(r".*?Verify:\s+(.+)$", text)
                verify = vm.group(1) if vm else ""
                criteria.append({
                    "text": text,
                    "type": ctype,
                    "verify": verify,
                    "checked": checked,
                })
            elif stripped and not stripped.startswith("-"):
                break

    return criteria


def parse_wave_criteria(criteria_list):
    """Parse acceptance criteria from wave JSON format.

    Handles both old flat-string format and new structured format.

    Args:
        criteria_list: list of strings or dicts

    Returns:
        list of {"text": str, "type": "auto"|"manual", "verify": str}
    """
    results = []
    for item in criteria_list:
        if isinstance(item, dict):
            results.append({
                "text": item.get("text", ""),
                "type": item.get("type", "auto"),
                "verify": item.get("verify", ""),
            })
        else:
            # Old flat-string format -- auto-promote
            text = str(item)
            vm = re.match(r".*?Verify:\s+(.+)$", text)
            results.append({
                "text": text,
                "type": "auto",
                "verify": vm.group(1) if vm else text,
            })
    return results


def validate_pattern(verify_text):
    """Check if a Verify: pattern is a valid executable form.

    Returns: (valid: bool, message: str)
    """
    parsed = parse_verify_pattern(verify_text)
    if parsed["type"] == "invalid":
        return False, f"Invalid pattern: {verify_text}"
    return True, f"Valid {parsed['type']} pattern"


def self_test():
    """Run internal verification of all pattern types."""
    print("Running verify.py self-test...\n")
    failures = 0
    total = 0

    def check(name, result, expected_status):
        nonlocal failures, total
        total += 1
        status = result["status"]
        ok = status == expected_status
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}: {status} -- {result['detail'][:80]}")
        if not ok:
            failures += 1

    # Pattern parsing
    assert parse_verify_pattern("run: echo hello")["type"] == "run"
    assert parse_verify_pattern("file: foo.txt exists")["type"] == "file_exists"
    assert parse_verify_pattern("file: foo.txt contains bar")["type"] == "file_contains"
    assert parse_verify_pattern("html: index.html has .cls")["type"] == "html_has"
    assert parse_verify_pattern("not a pattern")["type"] == "invalid"
    print("  [PASS] Pattern parsing (5 cases)")
    total += 1

    # run: pattern
    check("run: echo hello", run_criterion("run: echo hello"), "PASS")
    check("run: false", run_criterion("run: false"), "FAIL")

    # file: exists
    check("file: exists (this file)", run_criterion("file: execution/verify.py exists"), "PASS")
    check("file: exists (missing)", run_criterion("file: nonexistent-file.xyz exists"), "FAIL")

    # file: contains
    check("file: contains (match)", run_criterion("file: execution/verify.py contains def self_test"), "PASS")
    check("file: contains (no match)", run_criterion("file: execution/verify.py contains \x00NEVER_IN_FILE\x00"), "FAIL")

    # html: has (if beautifulsoup4 available)
    html_result = run_criterion("html: nonexistent.html has .foo")
    if html_result["status"] == "SKIP":
        print(f"  [SKIP] html: pattern -- beautifulsoup4 not installed")
        total += 1
    else:
        check("html: missing file", html_result, "FAIL")

    # Pattern validation
    valid, _ = validate_pattern("run: echo ok")
    assert valid, "run: should be valid"
    valid, _ = validate_pattern("garbage text")
    assert not valid, "garbage should be invalid"
    print("  [PASS] Pattern validation (2 cases)")
    total += 1

    # String and dict input forms
    check("dict input", run_criterion({"verify": "run: echo dict_ok"}), "PASS")

    print(f"\n  {total - failures}/{total} passed")
    return 1 if failures > 0 else 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test())

    if "--check-step" in sys.argv:
        idx = sys.argv.index("--check-step")
        if idx + 1 >= len(sys.argv):
            print("Usage: --check-step N", file=sys.stderr)
            sys.exit(2)
        step_num = int(sys.argv[idx + 1])
        criteria = parse_todo_contract(step_num)
        if not criteria:
            print(f"No contract found for step {step_num}")
            sys.exit(2)

        auto_criteria = [c for c in criteria if c["type"] == "auto" and c["verify"]]
        if not auto_criteria:
            print(f"No [auto] criteria with Verify: patterns for step {step_num}")
            sys.exit(0)

        # Run build step first
        build = run_build_step()
        if build and build["status"] == "FAIL":
            print(f"Build failed: {build['detail']}")
            sys.exit(1)

        results = run_all_criteria([c["verify"] for c in auto_criteria])
        any_fail = False
        for r in results:
            print(f"  [{r['status']}] {r['criterion']}")
            if r["detail"] and r["status"] != "PASS":
                print(f"        {r['detail']}")
            if r["status"] == "FAIL":
                any_fail = True

        sys.exit(1 if any_fail else 0)

    if "--check-criteria" in sys.argv:
        idx = sys.argv.index("--check-criteria")
        if idx + 1 >= len(sys.argv):
            print("Usage: --check-criteria '<pattern>'", file=sys.stderr)
            sys.exit(2)
        pattern = sys.argv[idx + 1]
        result = run_criterion(pattern)
        print(f"[{result['status']}] {result['detail']}")
        sys.exit(0 if result["status"] == "PASS" else 1)

    print(__doc__)
    sys.exit(0)


if __name__ == "__main__":
    main()
