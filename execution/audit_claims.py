#!/usr/bin/env python3
"""
Audit DOE project claims for false positives.

Checks governed documents, task tracking, and roadmap for things claimed
as done without proof. Universal checks work in any DOE project;
project-specific checks are clearly separated.

Usage:
    python3 execution/audit_claims.py              # Full audit
    python3 execution/audit_claims.py --scope universal  # Universal only
    python3 execution/audit_claims.py --hook             # Fast checks (for pre-commit)
    python3 execution/audit_claims.py --json             # Machine-readable output
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP = PROJECT_ROOT / ".tmp"


# ══════════════════════════════════════════════════════════════
# Data types
# ══════════════════════════════════════════════════════════════

class Severity(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class Finding:
    severity: Severity
    check: str
    message: str
    file: str = ""
    line: int = 0


@dataclass
class AuditReport:
    findings: list = field(default_factory=list)

    def add(self, finding: Finding):
        self.findings.append(finding)

    @property
    def pass_count(self):
        return sum(1 for f in self.findings if f.severity == Severity.PASS)

    @property
    def warn_count(self):
        return sum(1 for f in self.findings if f.severity == Severity.WARN)

    @property
    def fail_count(self):
        return sum(1 for f in self.findings if f.severity == Severity.FAIL)

    @property
    def exit_code(self):
        return 1 if self.fail_count > 0 else 0

    def print_report(self):
        print()
        print("══ DOE Claim Audit ═════════════════════════════════════════")
        print()
        version = discover_version()
        print(f"  Current app version: {version or 'unknown'}")
        gov_docs = find_governed_docs()
        names = ", ".join(p.name for p in gov_docs) if gov_docs else "none"
        print(f"  Governed docs found: {len(gov_docs)} ({names})")
        print()

        current_check = None
        for f in self.findings:
            if f.check != current_check:
                current_check = f.check
                label = current_check.replace("_", " ").title()
                print(f"── {label} {'─' * (55 - len(label))}")
            sev = f.severity.value
            pad = " " * (4 - len(sev))
            loc = ""
            if f.file and f.line:
                loc = f" ({f.file}:{f.line})"
            elif f.file:
                loc = f" ({f.file})"
            print(f"  {sev}{pad}  {f.message}{loc}")
        print()
        print("═" * 60)
        print(f"  Summary: {self.pass_count} PASS · {self.warn_count} WARN · {self.fail_count} FAIL")
        print("═" * 60)
        print()

    def to_json(self):
        return json.dumps({
            "version": discover_version(),
            "summary": {
                "pass": self.pass_count,
                "warn": self.warn_count,
                "fail": self.fail_count,
            },
            "findings": [
                {
                    "severity": f.severity.value,
                    "check": f.check,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                }
                for f in self.findings
            ],
        }, indent=2)

    def save_to_tmp(self):
        TMP.mkdir(exist_ok=True)
        out = TMP / "last-audit.txt"
        import io
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        self.print_report()
        sys.stdout = old_stdout
        out.write_text(buf.getvalue(), encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# Check registry
# ══════════════════════════════════════════════════════════════

_CHECKS: dict[str, list] = {"universal": []}


def register(scope: str, fast: bool = False):
    """Decorator to register a check function."""
    def decorator(fn):
        fn._audit_scope = scope
        fn._audit_fast = fast
        if scope not in _CHECKS:
            _CHECKS[scope] = []
        _CHECKS[scope].append(fn)
        return fn
    return decorator


# ══════════════════════════════════════════════════════════════
# Version discovery (project-agnostic)
# ══════════════════════════════════════════════════════════════

def discover_version() -> Optional[str]:
    """Find the current app version from STATE.md or fallbacks."""
    # Try STATE.md first
    state = PROJECT_ROOT / "STATE.md"
    if state.exists():
        text = state.read_text(encoding="utf-8")
        m = re.search(r"\*\*Current app version:\*\*\s*(v\d+\.\d+\.\d+)", text)
        if m:
            return m.group(1)

    # Fallback: latest [x] version in todo.md
    todo = PROJECT_ROOT / "tasks" / "todo.md"
    if todo.exists():
        text = todo.read_text(encoding="utf-8")
        versions = re.findall(r"\[x\].*?→\s*(v\d+\.\d+\.\d+)", text)
        if versions:
            return versions[-1]

    # Fallback: latest Complete entry in ROADMAP.md
    roadmap = PROJECT_ROOT / "ROADMAP.md"
    if roadmap.exists():
        text = roadmap.read_text(encoding="utf-8")
        m = re.search(r"###\s+.+?\((v\d+\.\d+\.\d+)\)", text)
        if m:
            return m.group(1)

    return None


def parse_semver(v: str) -> tuple:
    """Parse 'v0.11.4' into (0, 11, 4)."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def minor_gap(a: str, b: str) -> int:
    """Minor version difference between two semver strings."""
    sa = parse_semver(a)
    sb = parse_semver(b)
    return abs(sa[1] - sb[1])


# ══════════════════════════════════════════════════════════════
# File finders
# ══════════════════════════════════════════════════════════════

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_FM_FIELDS = {"Version", "Last updated", "Applies to", "Updated by"}


def parse_frontmatter(path: Path) -> Optional[dict]:
    """Parse YAML-style front-matter from a markdown file. Returns dict or None."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    result = {}
    for line in block.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def find_governed_docs() -> list[Path]:
    """Find markdown files with front-matter blocks in the project root."""
    docs = []
    for md in sorted(PROJECT_ROOT.glob("*.md")):
        if md.name.startswith("."):
            continue
        fm = parse_frontmatter(md)
        if fm is not None:
            docs.append(md)
    return docs


def find_governed_doc_registry() -> list[dict]:
    """Parse the governed doc registry from the governance directive."""
    directive = PROJECT_ROOT / "directives" / "documentation-governance.md"
    if not directive.exists():
        return []
    text = directive.read_text(encoding="utf-8")
    entries = []
    in_table = False
    for line in text.split("\n"):
        if "| Document |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2:
                path_match = re.search(r"`([^`]+)`", cells[1])
                if path_match:
                    entries.append({
                        "name": cells[0],
                        "path": path_match.group(1),
                    })
        elif in_table:
            break
    return entries


def find_todo_files() -> list[Path]:
    """Return task tracking files that exist."""
    paths = []
    for name in ["tasks/todo.md", "tasks/archive.md"]:
        p = PROJECT_ROOT / name
        if p.exists():
            paths.append(p)
    return paths


# ══════════════════════════════════════════════════════════════
# Task parsing
# ══════════════════════════════════════════════════════════════

_TASK_DONE_RE = re.compile(
    r"^[\s]*(?:\d+\.\s*)?\[x\]\s*(.+)",
    re.IGNORECASE,
)
_VERSION_TAG_RE = re.compile(r"(?:→|->)\s*(v\d+\.\d+\.\d+)")
_TIMESTAMP_RE = re.compile(r"\*\(completed\s+(\d{2}:\d{2}\s+\d{2}/\d{2}/\d{2})\)\*")
_TIMESTAMP_DATE_ONLY_RE = re.compile(r"\*\(completed\s+(\d{2}/\d{2}/\d{2})\)\*")


def parse_completed_tasks(path: Path) -> list[dict]:
    """Parse all [x] completed items from a task file."""
    tasks = []
    text = path.read_text(encoding="utf-8")
    current_heading = ""
    for i, line in enumerate(text.split("\n"), 1):
        # Track ### headings to detect [INFRA] vs [APP] sections
        if line.startswith("### "):
            current_heading = line
        m = _TASK_DONE_RE.match(line)
        if not m:
            continue
        task_text = m.group(1)
        version_m = _VERSION_TAG_RE.search(task_text)
        ts_m = _TIMESTAMP_RE.search(task_text) or _TIMESTAMP_DATE_ONLY_RE.search(task_text)

        # Extract a short name (everything before → / -> or *( )
        name = re.split(r"(?:→|->|\*)", task_text)[0].strip().rstrip("—").strip()

        tasks.append({
            "line": i,
            "text": task_text.strip(),
            "name": name,
            "version": version_m.group(1) if version_m else None,
            "timestamp": ts_m.group(1) if ts_m else None,
            "infra": "[INFRA]" in current_heading,
        })
    return tasks


# ══════════════════════════════════════════════════════════════
# UNIVERSAL CHECKS
# ══════════════════════════════════════════════════════════════

@register("universal", fast=True)
def check_frontmatter(report: AuditReport):
    """Governed doc front-matter exists and is well-formed."""
    found_docs = find_governed_docs()
    for doc in found_docs:
        fm = parse_frontmatter(doc)
        missing = _FM_FIELDS - set(fm.keys())
        if missing:
            report.add(Finding(
                Severity.FAIL, "front_matter",
                f"{doc.name} — missing fields: {', '.join(sorted(missing))}",
                file=doc.name, line=1,
            ))
        else:
            date_str = fm.get("Last updated", "")
            if not re.match(r"\d{2}/\d{2}/\d{2}$", date_str):
                report.add(Finding(
                    Severity.WARN, "front_matter",
                    f"{doc.name} — 'Last updated' not in DD/MM/YY format: '{date_str}'",
                    file=doc.name, line=1,
                ))
            applies = fm.get("Applies to", "")
            if not re.match(r"v\d+\.\d+\.\d+$", applies):
                report.add(Finding(
                    Severity.WARN, "front_matter",
                    f"{doc.name} — 'Applies to' not in vX.Y.Z format: '{applies}'",
                    file=doc.name, line=1,
                ))
            if not missing and re.match(r"\d{2}/\d{2}/\d{2}$", date_str) and re.match(r"v\d+\.\d+\.\d+$", applies):
                report.add(Finding(
                    Severity.PASS, "front_matter",
                    f"{doc.name} — all fields present, well-formed",
                    file=doc.name,
                ))

    registry = find_governed_doc_registry()
    found_names = {d.name for d in found_docs}
    for entry in registry:
        path_str = entry["path"]
        if path_str not in found_names:
            full = PROJECT_ROOT / path_str
            if full.exists():
                report.add(Finding(
                    Severity.WARN, "front_matter",
                    f"{path_str} — listed in governance registry but has no front-matter block",
                    file=path_str, line=1,
                ))
            else:
                report.add(Finding(
                    Severity.FAIL, "front_matter",
                    f"{path_str} — listed in governance registry but file does not exist",
                    file=path_str,
                ))


@register("universal", fast=True)
def check_staleness(report: AuditReport):
    """Governed doc 'Applies to' vs current app version."""
    current = discover_version()
    if not current:
        report.add(Finding(
            Severity.WARN, "staleness",
            "Cannot determine current app version — skipping staleness check",
        ))
        return

    found_docs = find_governed_docs()
    for doc in found_docs:
        fm = parse_frontmatter(doc)
        applies = fm.get("Applies to", "")
        if not re.match(r"v\d+\.\d+\.\d+$", applies):
            continue
        gap = minor_gap(applies, current)
        if gap > 1:
            report.add(Finding(
                Severity.WARN, "staleness",
                f"{doc.name} — Applies to {applies}, current is {current} ({gap} minor versions behind)",
                file=doc.name,
            ))
        else:
            report.add(Finding(
                Severity.PASS, "staleness",
                f"{doc.name} — Applies to {applies} ({gap} minor behind {current})",
                file=doc.name,
            ))


@register("universal", fast=True)
def check_task_format(report: AuditReport):
    """All [x] items have timestamps and version tags."""
    todo_files = find_todo_files()
    for path in todo_files:
        rel = path.relative_to(PROJECT_ROOT)
        tasks = parse_completed_tasks(path)
        if not tasks:
            continue

        no_timestamp = [t for t in tasks if not t["timestamp"]]
        # [INFRA] tasks don't bump app version — skip version tag check
        no_version = [t for t in tasks if not t["version"] and not t.get("infra")]
        good = [t for t in tasks if t["timestamp"] and (t["version"] or t.get("infra"))]

        if no_timestamp:
            for t in no_timestamp:
                report.add(Finding(
                    Severity.FAIL, "task_format",
                    f"[x] without timestamp: \"{t['name']}\"",
                    file=str(rel), line=t["line"],
                ))

        if no_version:
            for t in no_version:
                report.add(Finding(
                    Severity.WARN, "task_format",
                    f"[x] without version tag: \"{t['name']}\"",
                    file=str(rel), line=t["line"],
                ))

        if good:
            report.add(Finding(
                Severity.PASS, "task_format",
                f"{rel} — {len(good)}/{len(tasks)} items have timestamps + versions",
                file=str(rel),
            ))


# ══════════════════════════════════════════════════════════════
# Roadmap parsing
# ══════════════════════════════════════════════════════════════

_ROADMAP_COMPLETE_RE = re.compile(
    r"^###\s+(.+?)\s+\((v\d+\.\d+\.\d+)\)\s*[—–-]\s*(.+)$"
)


def parse_roadmap_complete() -> list[dict]:
    """Parse entries from ROADMAP.md ## Complete section."""
    roadmap = PROJECT_ROOT / "ROADMAP.md"
    if not roadmap.exists():
        return []
    text = roadmap.read_text(encoding="utf-8")
    entries = []
    in_complete = False
    for i, line in enumerate(text.split("\n"), 1):
        if re.match(r"^##\s+Complete", line):
            in_complete = True
            continue
        if in_complete and re.match(r"^##\s+", line):
            break
        if in_complete:
            m = _ROADMAP_COMPLETE_RE.match(line)
            if m:
                entries.append({
                    "name": m.group(1).strip(),
                    "version": m.group(2),
                    "date": m.group(3).strip(),
                    "line": i,
                })
    return entries


# ══════════════════════════════════════════════════════════════
# Git helpers
# ══════════════════════════════════════════════════════════════

def is_git_repo() -> bool:
    """Check if we're inside a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, check=True, cwd=PROJECT_ROOT,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def git_log_grep(pattern: str) -> list[str]:
    """Search git log for commits matching pattern. Returns commit subjects."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", f"--grep={pattern}"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=5,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []


@register("universal", fast=False)
def check_roadmap_consistency(report: AuditReport):
    """Items in ROADMAP.md 'Complete' have matching evidence in todo/archive."""
    complete_entries = parse_roadmap_complete()
    if not complete_entries:
        report.add(Finding(
            Severity.PASS, "roadmap_consistency",
            "No entries in ROADMAP.md ## Complete (or no ROADMAP.md)",
        ))
        return

    all_tasks = []
    for path in find_todo_files():
        all_tasks.extend(parse_completed_tasks(path))
    task_text_blob = " ".join(t["text"].lower() for t in all_tasks)

    heading_blob = ""
    for path in find_todo_files():
        text = path.read_text(encoding="utf-8")
        headings = re.findall(r"^###\s+(.+)$", text, re.MULTILINE)
        heading_blob += " ".join(h.lower() for h in headings) + " "

    matched = 0
    for entry in complete_entries:
        name_lower = entry["name"].lower()
        version = entry["version"]
        has_version = version.lower() in task_text_blob
        name_words = re.findall(r"\w+", name_lower)
        key_phrase = " ".join(name_words[:3]) if len(name_words) >= 3 else name_lower
        has_name = key_phrase in task_text_blob or key_phrase in heading_blob

        if has_version or has_name:
            matched += 1
        else:
            report.add(Finding(
                Severity.FAIL, "roadmap_consistency",
                f"'{entry['name']}' ({version}) — no matching evidence in task tracker",
                file="ROADMAP.md", line=entry["line"],
            ))

    if matched == len(complete_entries):
        report.add(Finding(
            Severity.PASS, "roadmap_consistency",
            f"{matched}/{len(complete_entries)} Complete entries have matching task evidence",
        ))
    elif matched > 0:
        report.add(Finding(
            Severity.PASS, "roadmap_consistency",
            f"{matched}/{len(complete_entries)} Complete entries have matching task evidence",
        ))


@register("universal", fast=True)
def check_active_wave(report: AuditReport):
    """Warn if a multi-agent wave is active (results may be incomplete)."""
    waves_dir = TMP / "waves"
    if not waves_dir.is_dir():
        return  # No waves directory — single-terminal mode, skip silently

    for wave_file in sorted(waves_dir.glob("*.json")):
        try:
            data = json.loads(wave_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("status") == "active":
            wave_id = data.get("waveId", wave_file.stem)
            task_count = len(data.get("tasks", []))
            report.add(Finding(
                Severity.WARN, "active_wave",
                f"Wave '{wave_id}' is active ({task_count} tasks) — audit results may be incomplete until merge",
                file=f".tmp/waves/{wave_file.name}",
            ))
            return

    # If waves dir exists but no active wave, all clear
    report.add(Finding(
        Severity.PASS, "active_wave",
        "No active wave — audit results are complete",
    ))


@register("universal", fast=False)
def check_orphan_claims(report: AuditReport):
    """Done items without corresponding git commits."""
    if not is_git_repo():
        report.add(Finding(
            Severity.WARN, "orphan_claims",
            "Not a git repository — skipping commit evidence check",
        ))
        return

    all_tasks = []
    for path in find_todo_files():
        rel = str(path.relative_to(PROJECT_ROOT))
        for t in parse_completed_tasks(path):
            t["source_file"] = rel
            all_tasks.append(t)

    if not all_tasks:
        return

    with_evidence = 0
    without_evidence = []

    for t in all_tasks:
        if not t["version"]:
            continue
        commits = git_log_grep(t["version"])
        if commits:
            with_evidence += 1
        else:
            name_words = t["name"].split()[:3]
            if len(name_words) >= 2:
                fallback = " ".join(name_words)
                commits = git_log_grep(fallback)
                if commits:
                    with_evidence += 1
                    continue
            without_evidence.append(t)

    versioned = [t for t in all_tasks if t["version"]]
    if without_evidence:
        for t in without_evidence[:5]:
            report.add(Finding(
                Severity.WARN, "orphan_claims",
                f"No commit evidence for \"{t['name']}\" ({t['version']})",
                file=t["source_file"], line=t["line"],
            ))
        if len(without_evidence) > 5:
            report.add(Finding(
                Severity.WARN, "orphan_claims",
                f"...and {len(without_evidence) - 5} more without commit evidence",
            ))

    report.add(Finding(
        Severity.PASS, "orphan_claims",
        f"{with_evidence}/{len(versioned)} versioned tasks have git commit evidence",
    ))


# ══════════════════════════════════════════════════════════════
# PROJECT-SPECIFIC CHECKS
# Add your own checks below using @register("yourproject", fast=True/False)
# Example:
#
# @register("myapp", fast=True)
# def check_build_version(report: AuditReport):
#     """Verify build artifact version matches STATE.md."""
#     ...
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════

def run_audit(scope: str = "all", fast_only: bool = False) -> AuditReport:
    """Execute registered checks and return report."""
    report = AuditReport()
    scopes = list(_CHECKS.keys()) if scope == "all" else [scope]
    for s in scopes:
        if s not in _CHECKS:
            continue
        for check_fn in _CHECKS[s]:
            if fast_only and not check_fn._audit_fast:
                continue
            check_fn(report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Audit DOE project claims for false positives")
    parser.add_argument("--scope", choices=["all", "universal"], default="all",
                        help="Which checks to run (default: all)")
    parser.add_argument("--hook", action="store_true",
                        help="Fast checks only (for pre-commit hook)")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    report = run_audit(scope=args.scope, fast_only=args.hook)

    if args.json_output:
        print(report.to_json())
    else:
        report.print_report()

    report.save_to_tmp()
    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
