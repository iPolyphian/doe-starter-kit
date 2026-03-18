#!/usr/bin/env python3
"""Test suite orchestrator for snagging integration.

Manages server lifecycle, runs Playwright + Lighthouse in parallel,
collects results into a unified JSON for the snagging checklist generator.

Usage:
  python3 execution/run_test_suite.py                  # Run full suite
  python3 execution/run_test_suite.py --update-baselines  # Update all baselines + re-run
  python3 execution/run_test_suite.py --update-visual     # Update visual baselines only + re-run
  python3 execution/run_test_suite.py --update-lighthouse  # Update Lighthouse baseline only + re-run
  python3 execution/run_test_suite.py --update-a11y       # Update a11y baseline only + re-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = PROJECT_ROOT / "STATE.md"
BASELINES_DIR = PROJECT_ROOT / "tests" / "baselines"
TMP_DIR = PROJECT_ROOT / ".tmp"
RESULTS_PATH = TMP_DIR / "test-suite-results.json"
LIGHTHOUSE_BASELINE = BASELINES_DIR / "lighthouse.json"
A11Y_BASELINE = BASELINES_DIR / "a11y-known.json"

PORT = 8080
SERVER_TIMEOUT = 10
PLAYWRIGHT_TIMEOUT = 90
LIGHTHOUSE_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_app_prefix() -> str:
    """Get app filename prefix from tests/config.json or STATE.md.

    Fallback chain: config.json appPrefix > STATE.md filename parsing > directory name.
    """
    config_path = PROJECT_ROOT / "tests" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            prefix = cfg.get("appPrefix", "")
            if prefix:
                return prefix
        except (json.JSONDecodeError, OSError):
            pass
    # Parse from STATE.md filename pattern (e.g. "my-app-v0.27.5.html")
    if STATE_PATH.exists():
        text = STATE_PATH.read_text(encoding="utf-8")
        m = re.search(r"`([a-zA-Z0-9_-]+)-v[\d.]+\.html`", text)
        if m:
            return m.group(1)
    return PROJECT_ROOT.name


def get_version() -> str | None:
    """Read current app version from STATE.md."""
    text = STATE_PATH.read_text(encoding="utf-8")
    m = re.search(r"\*\*Current app version:\*\*\s*(v[\d.]+)", text)
    return m.group(1) if m else None


def check_app_path(version: str) -> list[str]:
    """Check if APP_PATH in test files matches the current version."""
    warnings = []
    app_prefix = get_app_prefix()
    expected = f"/{app_prefix}-{version}"
    for spec in ["app.spec.js", "accessibility.spec.js", "visual.spec.js"]:
        spec_path = PROJECT_ROOT / "tests" / spec
        if spec_path.exists():
            text = spec_path.read_text(encoding="utf-8")
            m = re.search(r"APP_PATH\s*=\s*['\"](.+?)['\"]", text)
            if m and m.group(1) != expected:
                warnings.append(
                    f"APP_PATH mismatch in {spec}: tests use '{m.group(1)}', "
                    f"STATE.md says {version} (expected '{expected}')"
                )
    return warnings


def kill_port(port: int) -> None:
    """Kill any process on the given port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            for pid in result.stdout.strip().split("\n"):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass
            time.sleep(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def wait_for_port(port: int, timeout: int = 10) -> bool:
    """Wait until port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def start_server() -> subprocess.Popen | None:
    """Start npx serve and return the process."""
    kill_port(PORT)
    proc = subprocess.Popen(
        ["npx", "serve", ".", "-p", str(PORT), "--no-clipboard"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_port(PORT, SERVER_TIMEOUT):
        proc.terminate()
        return None
    return proc


def stop_server(proc: subprocess.Popen | None) -> None:
    """Terminate the server process."""
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _error_result(section: str, msg: str) -> dict:
    """Build an error result dict for a given section."""
    if section == "playwright":
        return {
            "status": "error", "total": 0, "passed": 0, "failed": 0,
            "routes": [], "visual_diffs": [], "error_message": msg,
        }
    if section == "lighthouse":
        return {
            "status": "error", "score": None, "baseline": None,
            "delta": None, "raw_delta": None, "noise_adjusted": False,
            "first_run": False, "error_message": msg,
        }
    if section == "accessibility":
        return {
            "status": "error", "new_critical": 0, "known_critical": 0,
            "known_critical_age_days": 0, "details": [], "error_message": msg,
        }
    # health_check
    return {
        "status": "error",
        "summary": {"pass": 0, "warn": 0, "fail": 0, "total": 0},
        "checks": [], "error_message": msg,
    }


# ---------------------------------------------------------------------------
# Tool runners
# ---------------------------------------------------------------------------

def run_playwright() -> dict:
    """Run Playwright tests and return parsed results."""
    try:
        result = subprocess.run(
            ["npx", "playwright", "test", "--reporter=json"],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
            timeout=PLAYWRIGHT_TIMEOUT,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return _error_result(
                "playwright",
                f"Could not parse Playwright JSON (exit code {result.returncode})",
            )

        stats = data.get("stats", {})
        total = stats.get("expected", 0) + stats.get("unexpected", 0) + stats.get("flaky", 0)
        passed = stats.get("expected", 0)
        failed = stats.get("unexpected", 0)

        # Extract routes from specs titled "{Label} page renders"
        routes = []
        _extract_routes(data.get("suites", []), routes)

        # Check for visual diffs
        visual_diffs = []
        test_results_dir = PROJECT_ROOT / "test-results"
        if test_results_dir.exists():
            for f in test_results_dir.rglob("*-diff.png"):
                visual_diffs.append({
                    "page": f.stem.replace("-diff", ""),
                    "diff_path": str(f.relative_to(PROJECT_ROOT)),
                })

        status = "pass" if failed == 0 else "fail"
        all_routes_failed = routes and all(r["status"] == "fail" for r in routes)

        return {
            "status": status,
            "total": total, "passed": passed, "failed": failed,
            "routes": routes, "visual_diffs": visual_diffs,
            "error_message": None,
            "_all_routes_failed": all_routes_failed,
        }

    except FileNotFoundError:
        return _error_result("playwright", "Run: npx playwright install")
    except subprocess.TimeoutExpired:
        return _error_result("playwright", f"Timed out after {PLAYWRIGHT_TIMEOUT}s")


def _extract_routes(suites: list, routes: list) -> None:
    """Recursively extract route test results from Playwright suites."""
    for suite in suites:
        for spec in suite.get("specs", []):
            title = spec.get("title", "")
            if title.endswith(" page renders"):
                label = title.replace(" page renders", "").strip()
                status = "pass" if all(
                    t.get("status") == "expected"
                    for t in spec.get("tests", [])
                ) else "fail"
                routes.append({"name": label, "status": status})
        # Recurse into nested suites
        _extract_routes(suite.get("suites", []), routes)


def run_lighthouse(url: str) -> dict:
    """Run Lighthouse and return parsed results."""
    lighthouse_json = TMP_DIR / "lighthouse.json"
    try:
        subprocess.run(
            [
                "npx", "lighthouse@11", url,
                "--output=json",
                f"--output-path={lighthouse_json}",
                "--chrome-flags=--headless",
                "--quiet",
            ],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
            timeout=LIGHTHOUSE_TIMEOUT,
        )
        if not lighthouse_json.exists():
            return _error_result("lighthouse", "Lighthouse did not produce output")

        lh_data = json.loads(lighthouse_json.read_text(encoding="utf-8"))
        score = round(
            lh_data.get("categories", {}).get("performance", {}).get("score", 0) * 100
        )

        # Compare with baseline
        baseline_score = None
        first_run = False
        if LIGHTHOUSE_BASELINE.exists():
            bl = json.loads(LIGHTHOUSE_BASELINE.read_text(encoding="utf-8"))
            baseline_score = bl.get("performance")
        else:
            first_run = True

        if baseline_score is not None:
            raw_delta = score - baseline_score
            if abs(raw_delta) <= 5:
                delta, noise_adjusted = 0, True
            else:
                delta, noise_adjusted = raw_delta, False

            if abs(raw_delta) > 10:
                status = "fail"
            elif abs(raw_delta) > 5:
                status = "warn"
            else:
                status = "pass"
        else:
            raw_delta, delta, noise_adjusted = 0, 0, False
            status = "pass"

        return {
            "status": status, "score": score,
            "baseline": baseline_score, "delta": delta,
            "raw_delta": raw_delta, "noise_adjusted": noise_adjusted,
            "first_run": first_run, "error_message": None,
        }

    except FileNotFoundError:
        return _error_result("lighthouse", "Lighthouse not found. Run: npm install -g lighthouse")
    except subprocess.TimeoutExpired:
        return _error_result("lighthouse", f"Timed out after {LIGHTHOUSE_TIMEOUT}s")
    except (json.JSONDecodeError, KeyError) as e:
        return _error_result("lighthouse", f"Could not parse Lighthouse output: {e}")


def run_health_check() -> dict:
    """Run health check and return results."""
    health_script = PROJECT_ROOT / "execution" / "health_check.py"
    if not health_script.exists():
        return _error_result("health_check", "health_check.py not found")

    try:
        result = subprocess.run(
            [sys.executable, str(health_script), "--quick", "--json"],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        data = json.loads(result.stdout)
        summary = data.get("summary", {})
        checks = []
        for item in data.get("universal", []) or []:
            checks.append({
                "name": item.get("name", ""),
                "status": item.get("status", "OK"),
                "detail": item.get("detail", ""),
            })

        has_warn = summary.get("warn", 0) > 0
        has_fail = summary.get("fail", 0) > 0
        status = "fail" if has_fail else ("warn" if has_warn else "pass")

        return {
            "status": status, "summary": summary,
            "checks": checks, "error_message": None,
        }
    except Exception as e:
        return _error_result("health_check", str(e))


# ---------------------------------------------------------------------------
# A11y results assembly
# ---------------------------------------------------------------------------

def get_a11y_info() -> dict | None:
    """Read a11y baseline info."""
    if not A11Y_BASELINE.exists():
        return None
    data = json.loads(A11Y_BASELINE.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    today = datetime.now(timezone.utc).date()
    max_age_days = 0
    for v in violations:
        first_seen = v.get("first_seen")
        if first_seen:
            try:
                fs_date = datetime.strptime(first_seen, "%Y-%m-%d").date()
                max_age_days = max(max_age_days, (today - fs_date).days)
            except ValueError:
                pass
    return {
        "known_critical": len(violations),
        "known_critical_age_days": max_age_days,
        "violations": violations,
    }


def build_a11y_results(pw: dict, a11y_info: dict | None) -> dict:
    """Build accessibility section from Playwright results + baselines."""
    if pw.get("status") == "error":
        return {
            "status": "error",
            "new_critical": 0,
            "known_critical": a11y_info["known_critical"] if a11y_info else 0,
            "known_critical_age_days": a11y_info["known_critical_age_days"] if a11y_info else 0,
            "details": [],
            "error_message": pw.get("error_message"),
        }

    if a11y_info is None:
        return {
            "status": "pass", "new_critical": 0,
            "known_critical": 0, "known_critical_age_days": 0,
            "details": [], "error_message": None,
        }

    # Playwright passed = all a11y tests passed = no new violations
    if pw.get("failed", 0) == 0:
        return {
            "status": "warn" if a11y_info["known_critical"] > 0 else "pass",
            "new_critical": 0,
            "known_critical": a11y_info["known_critical"],
            "known_critical_age_days": a11y_info["known_critical_age_days"],
            "details": [
                {"page": v["page"], "critical": 1, "baseline": 1}
                for v in a11y_info["violations"]
            ],
            "error_message": None,
        }

    # Some tests failed -- can't determine exact a11y status
    return {
        "status": "fail", "new_critical": "unknown",
        "known_critical": a11y_info["known_critical"],
        "known_critical_age_days": a11y_info["known_critical_age_days"],
        "details": [], "error_message": None,
    }


# ---------------------------------------------------------------------------
# Baseline updates
# ---------------------------------------------------------------------------

def update_visual() -> None:
    """Update visual regression screenshots."""
    print("Updating visual regression baselines...")
    subprocess.run(
        ["npx", "playwright", "test", "tests/visual.spec.js", "--update-snapshots"],
        cwd=str(PROJECT_ROOT), timeout=60,
    )


def update_lighthouse_baseline(url: str) -> None:
    """Run Lighthouse and save current score as baseline."""
    print("Updating Lighthouse baseline...")
    lh = run_lighthouse(url)
    if lh.get("score") is not None:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        LIGHTHOUSE_BASELINE.write_text(
            json.dumps({"performance": lh["score"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  Lighthouse baseline updated to {lh['score']}")
    else:
        print(f"  Could not update: {lh.get('error_message')}")


def update_a11y_baseline() -> None:
    """Sync a11y-known.json with KNOWN_CRITICAL_BASELINE from test file."""
    print("Updating a11y baselines...")
    spec_path = PROJECT_ROOT / "tests" / "accessibility.spec.js"
    if not spec_path.exists():
        print("  accessibility.spec.js not found")
        return

    text = spec_path.read_text(encoding="utf-8")
    m = re.search(r"KNOWN_CRITICAL_BASELINE\s*=\s*\{([^}]+)\}", text)
    if not m:
        print("  Could not find KNOWN_CRITICAL_BASELINE in test file")
        return

    entries = re.findall(r"(\w+):\s*(\d+)", m.group(1))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load existing to preserve first_seen dates
    existing = {}
    if A11Y_BASELINE.exists():
        data = json.loads(A11Y_BASELINE.read_text(encoding="utf-8"))
        for v in data.get("violations", []):
            existing[v["page"]] = v

    violations = []
    for page, count in entries:
        if int(count) > 0:
            if page in existing:
                violations.append(existing[page])
            else:
                violations.append({
                    "rule": "select-name", "page": page,
                    "first_seen": today, "nodes": int(count),
                })

    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    A11Y_BASELINE.write_text(
        json.dumps({"violations": violations}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  A11y baseline updated: {len(violations)} known violations")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run test suite for snagging integration")
    parser.add_argument("--update-baselines", action="store_true", help="Update all baselines")
    parser.add_argument("--update-visual", action="store_true", help="Update visual baselines only")
    parser.add_argument("--update-lighthouse", action="store_true", help="Update Lighthouse baseline only")
    parser.add_argument("--update-a11y", action="store_true", help="Update a11y baseline only")
    args = parser.parse_args()

    start_time = time.time()
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Determine update mode
    update_mode = None
    if args.update_baselines:
        update_mode = "all"
    elif args.update_visual:
        update_mode = "visual"
    elif args.update_lighthouse:
        update_mode = "lighthouse"
    elif args.update_a11y:
        update_mode = "a11y"

    # 1. Clean stale state
    test_results_dir = PROJECT_ROOT / "test-results"
    if test_results_dir.exists():
        shutil.rmtree(test_results_dir)
    for stale in [TMP_DIR / "playwright-results.json", TMP_DIR / "lighthouse.json"]:
        stale.unlink(missing_ok=True)

    # 2. Version check
    version = get_version()
    if not version:
        print("Error: Could not find app version in STATE.md", file=sys.stderr)
        sys.exit(1)

    warnings = check_app_path(version)

    # 3. Check for tests directory
    tests_dir = PROJECT_ROOT / "tests"
    if not tests_dir.exists():
        error_msg = "No tests directory"
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0, "warnings": [error_msg],
            "playwright": _error_result("playwright", error_msg),
            "accessibility": _error_result("accessibility", error_msg),
            "lighthouse": _error_result("lighthouse", error_msg),
            "health_check": _error_result("health_check", error_msg),
        }
        RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))
        sys.exit(1)

    # 4. Start server
    print(f"Starting server on port {PORT}...")
    server = start_server()
    if server is None:
        error_msg = f"Server failed to start on port {PORT}"
        print(f"Error: {error_msg}", file=sys.stderr)
        health_results = run_health_check()
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.time() - start_time),
            "warnings": warnings + [error_msg],
            "playwright": _error_result("playwright", error_msg),
            "accessibility": _error_result("accessibility", error_msg),
            "lighthouse": _error_result("lighthouse", error_msg),
            "health_check": health_results,
        }
        RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))
        sys.exit(1)

    try:
        app_prefix = get_app_prefix()
        url = f"http://localhost:{PORT}/{app_prefix}-{version}"

        # 5. Handle baseline updates (server must be running)
        if update_mode:
            if update_mode in ("all", "visual"):
                update_visual()
            if update_mode in ("all", "lighthouse"):
                update_lighthouse_baseline(url)
            if update_mode in ("all", "a11y"):
                update_a11y_baseline()

        # 6. Parallel execution: Playwright + Lighthouse
        print(f"Running tests against {url}...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            pw_future = executor.submit(run_playwright)
            lh_future = executor.submit(run_lighthouse, url)
            playwright_results = pw_future.result()
            lighthouse_results = lh_future.result()

        # 7. Health check (sequential, fast)
        health_results = run_health_check()

        # 8. Build a11y results from Playwright + baselines
        a11y_info = get_a11y_info()
        a11y_results = build_a11y_results(playwright_results, a11y_info)

        # 9. Baseline improvement detection
        if (
            a11y_info
            and a11y_results.get("new_critical") == 0
            and a11y_results.get("known_critical", 0) > 0
        ):
            # Check if KNOWN_CRITICAL_BASELINE sum is less than baseline file sum
            spec_path = PROJECT_ROOT / "tests" / "accessibility.spec.js"
            if spec_path.exists():
                text = spec_path.read_text(encoding="utf-8")
                m = re.search(r"KNOWN_CRITICAL_BASELINE\s*=\s*\{([^}]+)\}", text)
                if m:
                    test_total = sum(int(c) for _, c in re.findall(r"(\w+):\s*(\d+)", m.group(1)))
                    baseline_total = a11y_info["known_critical"]
                    if test_total < baseline_total:
                        warnings.append(
                            f"A11y violations reduced from {baseline_total} to {test_total} "
                            f"-- run --update-a11y to update baseline"
                        )

        # 10. All routes failed warning
        if playwright_results.get("_all_routes_failed"):
            warnings.append(
                "All routes failed -- APP_PATH may not match current version"
            )

        # 11. First Lighthouse run -- write baseline
        if lighthouse_results.get("first_run") and lighthouse_results.get("score") is not None:
            BASELINES_DIR.mkdir(parents=True, exist_ok=True)
            LIGHTHOUSE_BASELINE.write_text(
                json.dumps({"performance": lighthouse_results["score"]}, indent=2) + "\n",
                encoding="utf-8",
            )
            lighthouse_results["baseline"] = lighthouse_results["score"]
            warnings.append(
                f"First Lighthouse run -- baseline set to {lighthouse_results['score']}"
            )

        # Clean internal keys
        playwright_results.pop("_all_routes_failed", None)

        duration = round(time.time() - start_time)
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
            "warnings": warnings,
            "playwright": playwright_results,
            "accessibility": a11y_results,
            "lighthouse": lighthouse_results,
            "health_check": health_results,
        }

        RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))

    finally:
        # 12. Always kill server
        stop_server(server)


if __name__ == "__main__":
    main()
