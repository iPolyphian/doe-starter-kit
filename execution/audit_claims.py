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
import os
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
            "retro": name.lower().startswith("retro"),
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
        # [INFRA] tasks and retro steps don't bump app version — skip version tag check
        def _has_version_exemption(t):
            return t.get("infra") or t.get("retro")
        no_version = [t for t in tasks if not t["version"] and not _has_version_exemption(t)]
        good = [t for t in tasks if t["timestamp"] and (t["version"] or _has_version_exemption(t))]

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


@register("universal", fast=True)
def check_manual_signoff(report: AuditReport):
    """Features in ## Done must not have unchecked [manual] contracts."""
    todo = PROJECT_ROOT / "tasks" / "todo.md"
    if not todo.exists():
        return
    text = todo.read_text(encoding="utf-8")

    in_done = False
    current_feature = None
    unchecked = []
    for i, line in enumerate(text.split("\n"), 1):
        if re.match(r"^##\s+Done", line):
            in_done = True
            continue
        if in_done and re.match(r"^##\s+", line):
            break
        if not in_done:
            continue
        if line.startswith("### "):
            current_feature = line.strip().lstrip("# ").strip()
        if re.search(r"\[ \]\s*\[manual\]", line):
            unchecked.append({
                "feature": current_feature or "Unknown",
                "line": i,
            })

    if unchecked:
        features = {}
        for u in unchecked:
            features.setdefault(u["feature"], {"count": 0, "line": u["line"]})
            features[u["feature"]]["count"] += 1
        for feat, info in features.items():
            report.add(Finding(
                Severity.WARN, "manual_signoff",
                f"{feat} -- {info['count']} unchecked [manual] contract(s) in Done",
                file="tasks/todo.md", line=info["line"],
            ))
    else:
        report.add(Finding(
            Severity.PASS, "manual_signoff",
            "No unchecked [manual] contracts in ## Done",
            file="tasks/todo.md",
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
# CFA CHECKS (10-17)
# ══════════════════════════════════════════════════════════════

@register("universal", fast=True)
def check_router_coverage(report: AuditReport):
    """CLAUDE.md triggers cover all directive files in directives/."""
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    directives_dir = PROJECT_ROOT / "directives"

    if not claude_md.exists() or not directives_dir.exists():
        report.add(Finding(Severity.WARN, "router_coverage",
                           "CLAUDE.md or directives/ not found — skipping"))
        return

    triggers_text = claude_md.read_text(encoding="utf-8")
    all_directives = [
        p for p in directives_dir.rglob("*.md")
        if not p.name.startswith("_")
    ]

    covered = []
    uncovered = []
    for d in sorted(all_directives):
        rel = str(d.relative_to(PROJECT_ROOT))
        if rel in triggers_text or d.stem in triggers_text or d.name in triggers_text:
            covered.append(rel)
        else:
            uncovered.append(rel)

    total = len(all_directives)
    if total == 0:
        report.add(Finding(Severity.PASS, "router_coverage", "no directive files found"))
        return

    pct = len(covered) / total * 100
    for u in uncovered:
        report.add(Finding(Severity.WARN, "router_coverage",
                           f"no trigger found: {u}", file=u))
    if pct >= 80:
        report.add(Finding(Severity.PASS, "router_coverage",
                           f"{len(covered)}/{total} directives routed ({pct:.0f}%)"))
    else:
        report.add(Finding(Severity.WARN, "router_coverage",
                           f"only {pct:.0f}% of directives routed ({len(covered)}/{total})"))


@register("universal", fast=True)
def check_rule_completeness(report: AuditReport):
    """Core Behaviour rules in CLAUDE.md have corresponding directive coverage."""
    claude_md = PROJECT_ROOT / "CLAUDE.md"

    if not claude_md.exists():
        report.add(Finding(Severity.WARN, "rule_completeness", "CLAUDE.md not found"))
        return

    text = claude_md.read_text(encoding="utf-8")
    rules = re.findall(r"^\d+\.\s+\*\*(.+?)\.\*\*", text, re.MULTILINE)

    if not rules:
        report.add(Finding(Severity.WARN, "rule_completeness",
                           "no Core Behaviour rules found in CLAUDE.md"))
        return

    rules_with_pointers = 0
    for rule in rules:
        rule_section = text[text.find(rule):text.find(rule) + 200]
        if "directives/" in rule_section or "->" in rule_section:
            rules_with_pointers += 1
        else:
            report.add(Finding(Severity.WARN, "rule_completeness",
                               f"no directive pointer: {rule[:70]}",
                               file="CLAUDE.md"))

    pct = rules_with_pointers / len(rules) * 100
    if pct >= 80:
        report.add(Finding(Severity.PASS, "rule_completeness",
                           f"{rules_with_pointers}/{len(rules)} rules have directive pointers ({pct:.0f}%)"))
    else:
        report.add(Finding(Severity.WARN, "rule_completeness",
                           f"only {pct:.0f}% rules have directive pointers ({rules_with_pointers}/{len(rules)})"))


@register("universal", fast=True)
def check_scale_consistency(report: AuditReport):
    """Directives mentioning scale modes use consistent section headings."""
    directives_dir = PROJECT_ROOT / "directives"

    if not directives_dir.exists():
        report.add(Finding(Severity.WARN, "scale_consistency", "directives/ not found"))
        return

    scale_terms = ["solo", "informal parallel", "formal parallel", "wave", "dag"]
    expected_headings = {"solo", "informal parallel", "formal parallel"}

    files_with_scale = []
    inconsistent = []

    for d in sorted(directives_dir.rglob("*.md")):
        text = d.read_text(encoding="utf-8").lower()
        mentions = [t for t in scale_terms if t in text]
        if len(mentions) >= 2:
            files_with_scale.append(d.name)
            headings = set()
            for h in expected_headings:
                if f"## {h}" in text or f"### {h}" in text:
                    headings.add(h)
            if headings and headings != expected_headings:
                missing_h = expected_headings - headings
                inconsistent.append((d.name, missing_h))

    for name, missing_h in inconsistent:
        report.add(Finding(Severity.WARN, "scale_consistency",
                           f"{name}: missing scale headings {missing_h}",
                           file=f"directives/{name}"))

    if not inconsistent:
        report.add(Finding(Severity.PASS, "scale_consistency",
                           f"{len(files_with_scale)} scale files use consistent headings"))


@register("universal", fast=False)
def check_dag_validation(report: AuditReport):
    """dispatch_dag.py --validate passes cleanly."""
    executor = PROJECT_ROOT / "execution" / "dispatch_dag.py"

    if not executor.exists():
        report.add(Finding(Severity.WARN, "dag_validation",
                           "execution/dispatch_dag.py not found — skipping"))
        return

    try:
        result = subprocess.run(
            [sys.executable, str(executor), "--validate"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30,
        )
        if result.returncode == 0:
            report.add(Finding(Severity.PASS, "dag_validation", "DAG validation passed"))
        else:
            report.add(Finding(Severity.WARN, "dag_validation",
                               "DAG validation found issues",
                               file="execution/dispatch_dag.py"))
    except subprocess.TimeoutExpired:
        report.add(Finding(Severity.WARN, "dag_validation", "DAG validation timed out"))
    except OSError as e:
        report.add(Finding(Severity.WARN, "dag_validation", f"cannot run DAG validator: {e}"))


@register("universal", fast=True)
def check_directive_schema(report: AuditReport):
    """Directive files follow the required schema: Goal section, When to Use trigger."""
    directives_dir = PROJECT_ROOT / "directives"

    if not directives_dir.exists():
        report.add(Finding(Severity.WARN, "directive_schema", "directives/ not found"))
        return

    required_patterns = {
        "Goal": re.compile(r"^##\s+Goal", re.MULTILINE | re.IGNORECASE),
        "When to Use": re.compile(r"^##\s+When to Use", re.MULTILINE | re.IGNORECASE),
    }
    _SCHEMA_SKIP = {"spec-reviewer.md", "code-quality-reviewer.md", "implementer-prompt.md"}

    total = 0
    issue_count = 0

    for d in sorted(directives_dir.rglob("*.md")):
        if d.name.startswith("_") or d.name in _SCHEMA_SKIP:
            continue
        total += 1
        text = d.read_text(encoding="utf-8")
        rel = str(d.relative_to(PROJECT_ROOT))
        for section_name, pattern in required_patterns.items():
            if not pattern.search(text):
                issue_count += 1
                report.add(Finding(Severity.WARN, "directive_schema",
                                   f"missing '## {section_name}' section",
                                   file=rel))

    if issue_count == 0:
        report.add(Finding(Severity.PASS, "directive_schema",
                           f"all {total} directives have Goal + When to Use sections"))


@register("universal", fast=True)
def check_cross_reference_consistency(report: AuditReport):
    """Directive cross-references and CLAUDE.md triggers point to real files."""
    # Collect forward-reference exempt files from uncompleted todo.md steps
    exempt_files: set = set()
    step_re = re.compile(r"^\d+\.\s+\[[ x]\]")
    owns_re = re.compile(r"^\s+Owns:\s*(.+)$", re.IGNORECASE)
    todo = PROJECT_ROOT / "tasks" / "todo.md"
    if todo.exists():
        todo_text = todo.read_text(encoding="utf-8")
        in_uncompleted = False
        for line in todo_text.splitlines():
            step_match = step_re.match(line.strip())
            if step_match:
                in_uncompleted = "[ ]" in line
            if in_uncompleted:
                owns_match = owns_re.match(line)
                if owns_match:
                    for f in owns_match.group(1).split(","):
                        exempt_files.add(f.strip())

    issue_count = 0
    ref_pattern = re.compile(r"`((?:directives|execution|\.claude)/[^`]+)`")

    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text(encoding="utf-8")
        for ref in ref_pattern.findall(text):
            full = PROJECT_ROOT / ref
            expanded = Path(os.path.expanduser(ref))
            if not full.exists() and not expanded.exists() and ref not in exempt_files:
                issue_count += 1
                report.add(Finding(Severity.WARN, "cross_reference_consistency",
                                   f"missing file referenced in CLAUDE.md: {ref}",
                                   file="CLAUDE.md"))

    directives_dir = PROJECT_ROOT / "directives"
    if directives_dir.exists():
        for d in sorted(directives_dir.rglob("*.md")):
            text = d.read_text(encoding="utf-8")
            rel = str(d.relative_to(PROJECT_ROOT))
            for ref in ref_pattern.findall(text):
                full = PROJECT_ROOT / ref
                expanded = Path(os.path.expanduser(ref))
                if not full.exists() and not expanded.exists() and ref not in exempt_files:
                    issue_count += 1
                    report.add(Finding(Severity.WARN, "cross_reference_consistency",
                                       f"missing file: {ref}",
                                       file=rel))

    if issue_count == 0:
        report.add(Finding(Severity.PASS, "cross_reference_consistency",
                           "all cross-references resolve"))


@register("universal", fast=True)
def check_agent_definition_integrity(report: AuditReport):
    """Agent files in .claude/agents/ have required frontmatter and read-only tool lists."""
    agents_dir = PROJECT_ROOT / ".claude" / "agents"

    if not agents_dir.exists():
        report.add(Finding(Severity.WARN, "agent_definition_integrity",
                           ".claude/agents/ not found — skipping"))
        return

    agent_files = sorted(agents_dir.glob("*.md"))
    issue_count = 0

    for af in agent_files:
        text = af.read_text(encoding="utf-8")
        name = af.stem
        tools_match = re.search(r"^tools:\s*(.+)$", text, re.MULTILINE)
        if not tools_match:
            issue_count += 1
            report.add(Finding(Severity.WARN, "agent_definition_integrity",
                               f"{name}: missing tools: line in frontmatter",
                               file=str(af.relative_to(PROJECT_ROOT))))
            continue

        tools = [t.strip() for t in tools_match.group(1).split(",")]
        # Read-only agents must not have Edit or Write
        if name in ("Finder", "Adversarial", "Referee", "ReadOnly"):
            if "Edit" in tools or "Write" in tools:
                issue_count += 1
                report.add(Finding(Severity.WARN, "agent_definition_integrity",
                                   f"{name}: has Edit/Write — should be read-only",
                                   file=str(af.relative_to(PROJECT_ROOT))))

    if issue_count == 0:
        report.add(Finding(Severity.PASS, "agent_definition_integrity",
                           f"all {len(agent_files)} agent definitions are consistent"))


@register("universal", fast=False)
def check_plan_vs_actual(report: AuditReport):
    """For completed features, plan deliverables exist on disk."""
    roadmap = PROJECT_ROOT / "ROADMAP.md"
    plans_dir = PROJECT_ROOT / ".claude" / "plans"

    if not roadmap.exists() or not plans_dir.exists():
        report.add(Finding(Severity.PASS, "plan_vs_actual",
                           "no ROADMAP.md or .claude/plans/ — nothing to check"))
        return

    roadmap_text = roadmap.read_text(encoding="utf-8")
    complete_match = re.search(
        r"^## Complete\b.*?\n(.*?)(?=^## |\Z)",
        roadmap_text, re.MULTILINE | re.DOTALL,
    )
    if not complete_match:
        report.add(Finding(Severity.PASS, "plan_vs_actual",
                           "no ## Complete section in ROADMAP.md"))
        return

    complete_text = complete_match.group(1)
    completed_features = re.findall(r"^###\s+(.+?)(?:\s+\(|$)", complete_text, re.MULTILINE)

    issue_count = 0
    checked = 0

    for feature in completed_features:
        safe_name = re.sub(r"[^a-z0-9-]", "-", feature.lower().strip())
        candidates = list(plans_dir.glob(f"*{safe_name[:20]}*"))
        if not candidates:
            continue
        checked += 1
        plan_file = candidates[0]
        plan_text = plan_file.read_text(encoding="utf-8")
        file_refs = re.findall(
            r"`((?:execution|directives|\.claude|src)/[^`]+\.\w+)`", plan_text
        )
        missing = [f for f in file_refs if not (PROJECT_ROOT / f).exists()]
        for m in missing:
            issue_count += 1
            report.add(Finding(Severity.WARN, "plan_vs_actual",
                               f"{feature}: deliverable missing: {m}",
                               file=plan_file.name))

    if issue_count == 0:
        report.add(Finding(Severity.PASS, "plan_vs_actual",
                           f"checked {checked} completed feature plans — all deliverables exist"))


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
