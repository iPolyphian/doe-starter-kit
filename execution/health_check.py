#!/usr/bin/env python3
"""Health check runner for DOE projects.

Runs two classes of checks:
  1. Universal checks — stub detection, TODO scanning, empty functions, not-implemented markers
     These are always WARN (informational), never FAIL.
  2. Project checks — loaded from tests/health.json, run via verify.py's run_criterion()
     These are PASS/FAIL.

Usage:
  python3 execution/health_check.py              # human-readable output
  python3 execution/health_check.py --json       # machine-parseable JSON
  python3 execution/health_check.py --quick      # universal checks only (no project checks)
"""

import json
import re
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


def _project_name():
    """Get project name from tests/config.json appPrefix or directory name."""
    config_path = ROOT / "tests" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            prefix = cfg.get("appPrefix", "")
            if prefix:
                return prefix.rstrip("-")
        except (json.JSONDecodeError, OSError):
            pass
    return ROOT.name


# ---------------------------------------------------------------------------
# Universal checks
# ---------------------------------------------------------------------------

def _js_files():
    """Return all .js files under src/js/."""
    src_js = ROOT / "src" / "js"
    if not src_js.exists():
        return []
    return list(src_js.rglob("*.js"))


def _strip_comments(text):
    """Strip // and /* */ comments from JS text (best-effort)."""
    # Remove block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove line comments
    text = re.sub(r"//[^\n]*", "", text)
    return text


def check_stubs():
    """Scan src/js/ for return null in non-trivial functions.

    A 'stub' is a function body that contains only `return null` (after stripping
    whitespace and comments). We skip single-expression arrow functions — those
    intentionally return null sometimes.
    """
    files = _js_files()
    hits = []

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip comment lines
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            # Look for return null; as the only statement hint in a block
            if re.search(r"\breturn\s+null\s*;", stripped):
                hits.append(f"{f.relative_to(ROOT)}:{i}")

    return hits


def check_todos():
    """Scan src/js/ for TODO and FIXME comments."""
    files = _js_files()
    hits = []

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            if re.search(r"//\s*(TODO|FIXME)\b", line, re.IGNORECASE):
                hits.append(f"{f.relative_to(ROOT)}:{i}")

    return hits


def check_empty_functions():
    """Scan src/js/ for empty function bodies: function name() {}."""
    files = _js_files()
    hits = []

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            # Match function foo() {} or function() {} (empty body on same line)
            if re.search(r"\bfunction\s*\w*\s*\([^)]*\)\s*\{\s*\}", stripped):
                hits.append(f"{f.relative_to(ROOT)}:{i}")

    return hits


def check_not_implemented():
    """Scan src/js/ for console.log('not implemented') patterns."""
    files = _js_files()
    hits = []

    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = raw.splitlines()
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if re.search(r"console\.log\s*\(\s*['\"]not implemented['\"]", stripped, re.IGNORECASE):
                hits.append(f"{f.relative_to(ROOT)}:{i}")

    return hits


def run_universal_checks():
    """Run all universal checks. Returns list of result dicts."""
    results = []

    # Stubs
    stub_hits = check_stubs()
    if stub_hits:
        results.append({
            "name": "No stubs detected",
            "status": "WARN",
            "detail": f"{len(stub_hits)} return null found: {', '.join(stub_hits[:5])}{'...' if len(stub_hits) > 5 else ''}",
        })
    else:
        results.append({"name": "No stubs detected", "status": "OK", "detail": ""})

    # TODOs
    todo_hits = check_todos()
    if todo_hits:
        results.append({
            "name": "No TODO/FIXME comments",
            "status": "WARN",
            "detail": f"{len(todo_hits)} found: {', '.join(todo_hits[:5])}{'...' if len(todo_hits) > 5 else ''}",
        })
    else:
        results.append({"name": "No TODO/FIXME comments", "status": "OK", "detail": ""})

    # Empty functions
    empty_hits = check_empty_functions()
    if empty_hits:
        results.append({
            "name": "No empty functions",
            "status": "WARN",
            "detail": f"{len(empty_hits)} found: {', '.join(empty_hits[:5])}{'...' if len(empty_hits) > 5 else ''}",
        })
    else:
        results.append({"name": "No empty functions", "status": "OK", "detail": ""})

    # Not implemented
    ni_hits = check_not_implemented()
    if ni_hits:
        results.append({
            "name": "No 'not implemented' markers",
            "status": "WARN",
            "detail": f"{len(ni_hits)} found: {', '.join(ni_hits[:5])}{'...' if len(ni_hits) > 5 else ''}",
        })
    else:
        results.append({"name": "No 'not implemented' markers", "status": "OK", "detail": ""})

    return results


# ---------------------------------------------------------------------------
# Project checks (tests/health.json)
# ---------------------------------------------------------------------------

def load_health_config():
    """Load tests/health.json. Returns None if missing or invalid."""
    path = ROOT / "tests" / "health.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e), "checks": []}


def run_project_checks():
    """Run project-specific checks from tests/health.json.

    Returns list of result dicts: {"name", "status", "detail"}.
    """
    # Import verify.py from execution/ (same package dir)
    sys.path.insert(0, str(ROOT / "execution"))
    try:
        import verify as _verify
        run_criterion = _verify.run_criterion
    except ImportError as e:
        return [{"name": "verify.py import", "status": "FAIL", "detail": str(e)}]

    config = load_health_config()
    if config is None:
        return [{"name": "tests/health.json", "status": "FAIL", "detail": "File not found"}]
    if "error" in config:
        return [{"name": "tests/health.json", "status": "FAIL", "detail": config["error"]}]

    results = []
    for check in config.get("checks", []):
        name = check.get("name", "unnamed")
        verify_text = check.get("verify", "")
        if not verify_text:
            results.append({"name": name, "status": "FAIL", "detail": "No verify pattern"})
            continue
        r = run_criterion(verify_text)
        results.append({
            "name": name,
            "status": r["status"],
            "detail": r.get("detail", ""),
        })

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

_ICON = {"OK": "\u2713", "WARN": "\u26a0", "PASS": "\u2713", "FAIL": "\u2717", "SKIP": "\u25cb"}


def _icon(status):
    return _ICON.get(status, "?")


def print_human(universal, project):
    """Print human-readable health check output."""
    print(f"Health Check \u2014 {_project_name()}")
    print("\u2550" * 40)

    print("Universal checks:")
    for r in universal:
        icon = _icon(r["status"])
        if r["status"] == "OK":
            print(f"  {icon} {r['name']}")
        else:
            print(f"  {icon} {r['detail']}")

    if project is not None:
        print()
        print("Project checks (tests/health.json):")
        for r in project:
            icon = _icon(r["status"])
            if r["detail"] and r["status"] != "PASS":
                print(f"  {icon} {r['name']} \u2014 {r['detail']}")
            else:
                print(f"  {icon} {r['name']}")

    # Summary
    all_results = universal + (project or [])
    n_ok = sum(1 for r in all_results if r["status"] in ("OK", "PASS"))
    n_warn = sum(1 for r in all_results if r["status"] == "WARN")
    n_fail = sum(1 for r in all_results if r["status"] == "FAIL")
    n_skip = sum(1 for r in all_results if r["status"] == "SKIP")

    parts = []
    if n_ok:
        parts.append(f"{n_ok} pass")
    if n_warn:
        parts.append(f"{n_warn} warn")
    if n_fail:
        parts.append(f"{n_fail} fail")
    if n_skip:
        parts.append(f"{n_skip} skip")

    print()
    print(f"Summary: {', '.join(parts)}")


def print_json_output(universal, project):
    """Print machine-parseable JSON output."""
    all_results = universal + (project or [])
    n_ok = sum(1 for r in all_results if r["status"] in ("OK", "PASS"))
    n_warn = sum(1 for r in all_results if r["status"] == "WARN")
    n_fail = sum(1 for r in all_results if r["status"] == "FAIL")
    n_skip = sum(1 for r in all_results if r["status"] == "SKIP")

    output = {
        "project": _project_name(),
        "summary": {
            "pass": n_ok,
            "warn": n_warn,
            "fail": n_fail,
            "skip": n_skip,
            "total": len(all_results),
        },
        "universal": universal,
        "project_checks": project,
    }
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    use_json = "--json" in args
    quick = "--quick" in args

    universal = run_universal_checks()
    project = None if quick else run_project_checks()

    if use_json:
        print_json_output(universal, project)
    else:
        print_human(universal, project)

    # Exit 1 if any FAIL
    all_results = universal + (project or [])
    if any(r["status"] == "FAIL" for r in all_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
