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


def detect_project_type() -> str:
    """Detect the project framework type.

    Priority: tests/config.json projectType > file-based auto-detection > html-app.
    Writes detected type back to config.json for subsequent runs.
    """
    config_path = PROJECT_ROOT / "tests" / "config.json"
    config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Check explicit config first
    project_type = config.get("projectType", "")
    if project_type and project_type != "html-app":
        return project_type

    if project_type == "html-app":
        return "html-app"

    # Auto-detect from project files
    # Order: unambiguous file markers first, then package.json dep checks
    # (more specific before less specific)
    detected = "html-app"

    if (PROJECT_ROOT / "pubspec.yaml").exists():
        detected = "flutter"
    elif (PROJECT_ROOT / "angular.json").exists():
        detected = "angular"
    elif (PROJECT_ROOT / "composer.json").exists():
        detected = "php"
    elif (PROJECT_ROOT / "Gemfile").exists():
        detected = "ruby"
    elif (PROJECT_ROOT / "go.mod").exists():
        detected = "go"
    elif (PROJECT_ROOT / "app.json").exists():
        try:
            with open(PROJECT_ROOT / "app.json") as f:
                app_data = json.load(f)
            if "expo" in app_data:
                detected = "expo"
        except (json.JSONDecodeError, OSError):
            pass
    elif (PROJECT_ROOT / "package.json").exists():
        try:
            with open(PROJECT_ROOT / "package.json") as f:
                pkg = json.load(f)
            deps = pkg.get("dependencies", {})
            all_deps = {}
            all_deps.update(deps)
            all_deps.update(pkg.get("devDependencies", {}))
            if "react-native" in all_deps:
                detected = "react-native"
            elif "next" in all_deps:
                detected = "nextjs"
            elif "nuxt" in all_deps:
                detected = "nuxt"
            elif "@remix-run/react" in deps:
                detected = "remix"
            elif "svelte" in all_deps or "@sveltejs/kit" in all_deps:
                detected = "svelte"
            elif "astro" in deps:
                detected = "astro"
            elif "vue" in deps:
                detected = "vue"
            elif "vite" in all_deps:
                detected = "vite"
        except (json.JSONDecodeError, OSError):
            pass
    elif any((PROJECT_ROOT / f).exists() for f in ("pyproject.toml", "requirements.txt", "manage.py")):
        detected = "python"

    # Write back to config so subsequent runs skip detection
    config["projectType"] = detected
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    return detected


def get_server_config() -> dict:
    """Get server configuration based on projectType in tests/config.json.

    Returns a dict with build, serve, port keys (and optionally mobile: True).
    """
    config_path = PROJECT_ROOT / "tests" / "config.json"
    config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    project_type = config.get("projectType", "html-app")

    configs = {
        "nextjs":   {"build": config.get("buildCommand", "npm run build"), "serve": config.get("startCommand", "npm start -- -p {port}"), "port": config.get("port", 3000)},
        "vite":     {"build": config.get("buildCommand", "npm run build"), "serve": config.get("startCommand", "npx vite preview --port {port}"), "port": config.get("port", 4173)},
        "angular":  {"build": config.get("buildCommand", "npx ng build"), "serve": config.get("startCommand", "npx serve dist/ -p {port} --no-clipboard"), "port": config.get("port", 4200)},
        "nuxt":     {"build": config.get("buildCommand", "npx nuxt build"), "serve": config.get("startCommand", "node .output/server/index.mjs"), "port": config.get("port", 3000)},
        "vue":      {"build": config.get("buildCommand", "npm run build"), "serve": config.get("startCommand", "npx serve dist/ -p {port} --no-clipboard"), "port": config.get("port", 5173)},
        "svelte":   {"build": config.get("buildCommand", "npm run build"), "serve": config.get("startCommand", "npm run preview -- --port {port}"), "port": config.get("port", 4173)},
        "remix":    {"build": config.get("buildCommand", "npx remix build"), "serve": config.get("startCommand", "npx remix-serve build/server/index.js"), "port": config.get("port", 3000)},
        "astro":    {"build": config.get("buildCommand", "npx astro build"), "serve": config.get("startCommand", "npx serve dist/ -p {port} --no-clipboard"), "port": config.get("port", 4321)},
        "php":      {"build": None, "serve": config.get("startCommand", "php -S localhost:{port} -t public"), "port": config.get("port", 8000)},
        "ruby":     {"build": None, "serve": config.get("startCommand", "bundle exec rails server -p {port}"), "port": config.get("port", 3000)},
        "go":       {"build": config.get("buildCommand", "go build -o .tmp/app ."), "serve": config.get("startCommand", ".tmp/app"), "port": config.get("port", 8080)},
        "python":   {"build": None, "serve": config.get("startCommand", "python3 manage.py runserver {port}"), "port": config.get("port", 8000)},
    }

    if project_type in configs:
        return configs[project_type]
    elif project_type in ("react-native", "expo", "flutter"):
        return {"build": None, "serve": None, "port": None, "mobile": True}
    else:
        # html-app (default)
        return {
            "build": None,
            "serve": "npx serve . -p {port} --no-clipboard",
            "port": 8080,
        }


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


def start_server(server_config: dict | None = None) -> subprocess.Popen | None:
    """Start the dev/preview server and return the process.

    Uses server_config's serve command and port if provided,
    otherwise falls back to npx serve on the default PORT.
    """
    port = server_config["port"] if server_config and server_config.get("port") else PORT
    serve_cmd = (
        server_config["serve"] if server_config and server_config.get("serve")
        else f"npx serve . -p {port} --no-clipboard"
    )
    kill_port(port)
    # Format port into serve command and split for Popen
    cmd_str = serve_cmd.format(port=port)
    proc = subprocess.Popen(
        cmd_str.split(),
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_port(port, SERVER_TIMEOUT):
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

def run_maestro() -> dict:
    """Run Maestro flows and return parsed results."""
    # Look for .maestro/ directory
    maestro_dir = PROJECT_ROOT / ".maestro"
    if not maestro_dir.exists():
        return {"status": "error", "total": 0, "passed": 0, "failed": 0,
                "flows": [], "error_message": "No .maestro/ directory found"}

    # Find all .yaml flow files
    flows = list(maestro_dir.glob("*.yaml"))
    if not flows:
        return {"status": "error", "total": 0, "passed": 0, "failed": 0,
                "flows": [], "error_message": "No .yaml flows in .maestro/"}

    # Run maestro test and parse results
    # Maestro outputs JUnit XML — parse it
    try:
        result = subprocess.run(
            ["maestro", "test", str(maestro_dir), "--format", "junit",
             "--output", str(TMP_DIR / "maestro-results.xml")],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
            timeout=180,
        )
        # Parse JUnit XML results
        xml_path = TMP_DIR / "maestro-results.xml"
        if xml_path.exists():
            return _parse_maestro_xml(xml_path, flows)
        else:
            # Fall back to exit code
            status = "pass" if result.returncode == 0 else "fail"
            return {"status": status, "total": len(flows),
                    "passed": len(flows) if status == "pass" else 0,
                    "failed": 0 if status == "pass" else len(flows),
                    "flows": [{"name": f.stem, "status": status} for f in flows],
                    "error_message": None}
    except FileNotFoundError:
        return {"status": "error", "total": 0, "passed": 0, "failed": 0,
                "flows": [], "error_message": "Maestro CLI not found. Run --bootstrap"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "total": 0, "passed": 0, "failed": 0,
                "flows": [], "error_message": "Maestro timed out after 180s"}


def _parse_maestro_xml(xml_path, flows):
    """Parse Maestro JUnit XML output into unified result dict."""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        total = int(root.attrib.get("tests", len(flows)))
        failed = int(root.attrib.get("failures", 0)) + int(root.attrib.get("errors", 0))
        passed = total - failed

        flow_results = []
        for tc in root.iter("testcase"):
            name = tc.attrib.get("name", "unknown")
            has_failure = tc.find("failure") is not None or tc.find("error") is not None
            flow_results.append({"name": name, "status": "fail" if has_failure else "pass"})

        return {"status": "fail" if failed > 0 else "pass", "total": total,
                "passed": passed, "failed": failed, "flows": flow_results,
                "error_message": None}
    except Exception as e:
        return {"status": "error", "total": len(flows), "passed": 0, "failed": 0,
                "flows": [], "error_message": f"Could not parse Maestro XML: {e}"}


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
    parser = argparse.ArgumentParser(
        description="DOE Quality Stack test suite orchestrator. "
        "Runs Playwright, Lighthouse, and health checks against your project.",
    )
    parser.add_argument("--update-baselines", action="store_true", help="Update all baselines")
    parser.add_argument("--update-visual", action="store_true", help="Update visual baselines only")
    parser.add_argument("--update-lighthouse", action="store_true", help="Update Lighthouse baseline only")
    parser.add_argument("--update-a11y", action="store_true", help="Update a11y baseline only")
    parser.add_argument("--bootstrap", action="store_true", help="Install dependencies and create initial baselines")
    args = parser.parse_args()

    # Detect project type early (before bootstrap, so config is available)
    project_type = detect_project_type()
    server_config = get_server_config()
    port = server_config.get("port") or PORT

    # Mobile projects -- run Maestro flows
    if server_config.get("mobile"):
        print(f"Mobile project detected ({project_type}) -- running Maestro flows")
        start_time = time.time()
        TMP_DIR.mkdir(parents=True, exist_ok=True)

        # Check if maestro CLI is installed
        maestro_installed = shutil.which("maestro") is not None
        if not maestro_installed:
            print("Error: Maestro CLI not found. Run --bootstrap to install.", file=sys.stderr)
            maestro_results = {"status": "error", "total": 0, "passed": 0, "failed": 0,
                               "flows": [], "error_message": "Maestro CLI not found. Run --bootstrap"}
        else:
            maestro_results = run_maestro()

        health_results = run_health_check()
        duration = round(time.time() - start_time)

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
            "project_type": project_type,
            "warnings": [],
            "maestro_results": maestro_results,
            "lighthouse": _error_result("lighthouse", "Not applicable for mobile projects"),
            "health_check": health_results,
        }
        RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))
        sys.exit(0)

    # Bootstrap mode: install deps, Playwright browser, and create baselines
    if args.bootstrap:
        print("Bootstrapping Quality Stack...")

        if project_type in ("react-native", "expo", "flutter"):
            # Mobile bootstrap: install Maestro CLI and create template flows
            print(f"  Mobile project ({project_type}) -- setting up Maestro...")
            if shutil.which("maestro"):
                print("  Maestro CLI already installed.")
            else:
                print("  Installing Maestro CLI...")
                subprocess.run(
                    ["bash", "-c", 'curl -Ls "https://get.maestro.mobile.dev" | bash'],
                    cwd=str(PROJECT_ROOT), timeout=120,
                )
            maestro_dir = PROJECT_ROOT / ".maestro"
            if not maestro_dir.exists():
                print("  Creating .maestro/ with template flows...")
                maestro_dir.mkdir(parents=True, exist_ok=True)
                template_flow = maestro_dir / "app-launch.yaml"
                template_flow.write_text(
                    "appId: com.example.app\n"
                    "---\n"
                    "- launchApp\n"
                    "- assertVisible: \".*\"\n",
                    encoding="utf-8",
                )
            else:
                print("  .maestro/ directory already exists.")
            print("  Bootstrap complete. Run again without --bootstrap to execute tests.")
            sys.exit(0)

        # Non-Node projects: minimal bootstrap (baselines only, no npm)
        if project_type in ("php", "ruby", "go", "python"):
            print(f"  Non-Node project ({project_type}) -- creating baselines only...")
            BASELINES_DIR.mkdir(parents=True, exist_ok=True)
            if not LIGHTHOUSE_BASELINE.exists():
                LIGHTHOUSE_BASELINE.write_text('{"score": 0, "first_run": true}\n', encoding="utf-8")
            if not A11Y_BASELINE.exists():
                A11Y_BASELINE.write_text('{"known_violations": [], "total_known_critical": 0}\n', encoding="utf-8")
            print("  Bootstrap complete. Run again without --bootstrap to execute tests.")
            sys.exit(0)

        # Web bootstrap: install Playwright and create baselines
        pkg_json = PROJECT_ROOT / "package.json"
        if not pkg_json.exists():
            print("  Creating package.json...")
            subprocess.run(["npm", "init", "-y"], cwd=str(PROJECT_ROOT), capture_output=True)
        print("  Installing dependencies...")
        subprocess.run(
            ["npm", "install", "--save-dev", "@playwright/test", "@axe-core/playwright", "serve"],
            cwd=str(PROJECT_ROOT), timeout=120,
        )
        print("  Installing Chromium browser...")
        subprocess.run(
            ["npx", "playwright", "install", "chromium"],
            cwd=str(PROJECT_ROOT), timeout=120,
        )
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        if not LIGHTHOUSE_BASELINE.exists():
            LIGHTHOUSE_BASELINE.write_text('{"score": 0, "first_run": true}\n', encoding="utf-8")
        if not A11Y_BASELINE.exists():
            A11Y_BASELINE.write_text('{"known_violations": [], "total_known_critical": 0}\n', encoding="utf-8")
        print("  Bootstrap complete. Run again without --bootstrap to execute tests.")
        sys.exit(0)

    # Check Playwright is installed
    pw_bin = PROJECT_ROOT / "node_modules" / ".bin" / "playwright"
    if not pw_bin.exists():
        print(
            "Quality Stack not bootstrapped. Run:\n"
            "  python3 execution/run_test_suite.py --bootstrap\n"
            "to install dependencies and create baselines.",
            file=sys.stderr,
        )
        sys.exit(2)

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

    # 4. Run build step if needed (nextjs, vite)
    if server_config.get("build"):
        print(f"Running build: {server_config['build']}...")
        build_result = subprocess.run(
            server_config["build"].split(),
            cwd=str(PROJECT_ROOT),
            timeout=300,
        )
        if build_result.returncode != 0:
            error_msg = f"Build command failed: {server_config['build']}"
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

    # 5. Start server
    print(f"Starting server on port {port}...")
    server = start_server(server_config)
    if server is None:
        error_msg = f"Server failed to start on port {port}"
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
        # URL construction: html-app uses path-based routing, frameworks use root
        if project_type != "html-app":
            url = f"http://localhost:{port}"
        else:
            app_prefix = get_app_prefix()
            url = f"http://localhost:{port}/{app_prefix}-{version}"

        # 6. Handle baseline updates (server must be running)
        if update_mode:
            if update_mode in ("all", "visual"):
                update_visual()
            if update_mode in ("all", "lighthouse"):
                update_lighthouse_baseline(url)
            if update_mode in ("all", "a11y"):
                update_a11y_baseline()

        # 7. Parallel execution: Playwright + Lighthouse
        print(f"Running tests against {url}...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            pw_future = executor.submit(run_playwright)
            lh_future = executor.submit(run_lighthouse, url)
            playwright_results = pw_future.result()
            lighthouse_results = lh_future.result()

        # 8. Health check (sequential, fast)
        health_results = run_health_check()

        # 9. Build a11y results from Playwright + baselines
        a11y_info = get_a11y_info()
        a11y_results = build_a11y_results(playwright_results, a11y_info)

        # 10. Baseline improvement detection
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

        # 11. All routes failed warning
        if playwright_results.get("_all_routes_failed"):
            warnings.append(
                "All routes failed -- APP_PATH may not match current version"
            )

        # 12. First Lighthouse run -- write baseline
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
        # 13. Always kill server
        stop_server(server)


if __name__ == "__main__":
    main()
