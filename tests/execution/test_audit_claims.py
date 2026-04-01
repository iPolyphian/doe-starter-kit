"""Tests for execution/audit_claims.py."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "execution"))

import audit_claims
from audit_claims import (
    AuditReport,
    Finding,
    Severity,
    parse_semver,
    minor_gap,
    parse_frontmatter,
    parse_completed_tasks,
    register,
)


# ── Severity / Finding ────────────────────────────────────────

def test_finding_severity_enum():
    """Severity enum must have PASS, WARN, FAIL values."""
    assert Severity.PASS.value == "PASS"
    assert Severity.WARN.value == "WARN"
    assert Severity.FAIL.value == "FAIL"


def test_audit_report_counts():
    """AuditReport pass/warn/fail_count must reflect added findings."""
    report = AuditReport()
    report.add(Finding(Severity.PASS, "test", "all good"))
    report.add(Finding(Severity.WARN, "test", "slight concern"))
    report.add(Finding(Severity.FAIL, "test", "broken"))

    assert report.pass_count == 1
    assert report.warn_count == 1
    assert report.fail_count == 1
    assert report.exit_code == 1


def test_audit_report_exit_code_zero_when_no_failures():
    """exit_code must be 0 when no FAIL findings exist."""
    report = AuditReport()
    report.add(Finding(Severity.PASS, "test", "ok"))
    assert report.exit_code == 0


# ── Severity classification (parse_semver / minor_gap) ───────

def test_parse_semver_basic():
    """parse_semver must parse standard vX.Y.Z strings."""
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert parse_semver("v0.11.4") == (0, 11, 4)


def test_parse_semver_invalid_returns_zeros():
    """parse_semver must return (0,0,0) for unrecognised strings."""
    assert parse_semver("not-a-version") == (0, 0, 0)


def test_minor_gap_calculation():
    """minor_gap must return the absolute minor version difference."""
    assert minor_gap("v0.5.0", "v0.8.0") == 3
    assert minor_gap("v1.0.0", "v1.0.0") == 0
    assert minor_gap("v0.10.0", "v0.8.0") == 2


# ── False positive handling (parse_frontmatter) ──────────────

def test_parse_frontmatter_returns_none_when_no_block(tmp_path):
    """parse_frontmatter must return None for files without front-matter."""
    md = tmp_path / "no_fm.md"
    md.write_text("# Just a heading\n\nSome content.", encoding="utf-8")
    assert parse_frontmatter(md) is None


def test_parse_frontmatter_parses_valid_block(tmp_path):
    """parse_frontmatter must parse a valid YAML-style front-matter block."""
    md = tmp_path / "with_fm.md"
    md.write_text(
        "---\nVersion: 1\nLast updated: 01/01/25\nApplies to: v0.5.0\nUpdated by: William\n---\n\n# Content",
        encoding="utf-8",
    )
    fm = parse_frontmatter(md)
    assert fm is not None
    assert fm.get("Version") == "1"
    assert fm.get("Last updated") == "01/01/25"


# ── Finding detection (parse_completed_tasks) ────────────────

def test_parse_completed_tasks_empty_file(tmp_path):
    """parse_completed_tasks must return empty list for file with no [x] items."""
    md = tmp_path / "todo.md"
    md.write_text("## Current\n\n1. [ ] pending task\n", encoding="utf-8")
    tasks = parse_completed_tasks(md)
    assert tasks == []


def test_parse_completed_tasks_finds_done_items(tmp_path):
    """parse_completed_tasks must find all [x] completed items."""
    md = tmp_path / "todo.md"
    md.write_text(
        "## Done\n\n"
        "1. [x] First feature → v0.1.0 *(completed 10:00 01/01/25)*\n"
        "2. [x] Second feature → v0.2.0 *(completed 11:00 02/01/25)*\n"
        "3. [ ] Not done\n",
        encoding="utf-8",
    )
    tasks = parse_completed_tasks(md)
    assert len(tasks) == 2
    assert tasks[0]["version"] == "v0.1.0"
    assert tasks[1]["version"] == "v0.2.0"


def test_parse_completed_tasks_detects_missing_timestamp(tmp_path):
    """parse_completed_tasks must include items even without timestamps."""
    md = tmp_path / "todo.md"
    md.write_text(
        "## Done\n\n1. [x] Some feature → v0.3.0\n",
        encoding="utf-8",
    )
    tasks = parse_completed_tasks(md)
    assert len(tasks) == 1
    assert tasks[0]["timestamp"] is None  # no timestamp


# ── register decorator ────────────────────────────────────────

def test_register_decorator_adds_to_checks():
    """@register should add the decorated function to the _CHECKS registry."""
    initial_count = len(audit_claims._CHECKS.get("test_scope_xyz", []))

    @register("test_scope_xyz", fast=True)
    def _dummy_check(report):
        pass

    after_count = len(audit_claims._CHECKS.get("test_scope_xyz", []))
    assert after_count == initial_count + 1
    assert _dummy_check._audit_scope == "test_scope_xyz"
    assert _dummy_check._audit_fast is True


# ── run_audit ─────────────────────────────────────────────────

def test_run_audit_returns_report():
    """run_audit must return an AuditReport instance."""
    report = audit_claims.run_audit(scope="universal", fast_only=True)
    assert isinstance(report, AuditReport)


def test_run_audit_json_serialisable():
    """to_json() must produce valid JSON."""
    import json
    report = audit_claims.run_audit(scope="universal", fast_only=True)
    data = json.loads(report.to_json())
    assert "summary" in data
    assert "findings" in data
