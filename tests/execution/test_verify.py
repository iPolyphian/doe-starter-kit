"""Tests for execution/verify.py — all four Verify: pattern types."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "execution"))

import verify


# ── parse_verify_pattern ─────────────────────────────────────

def test_parse_run_pattern():
    """run: <command> must parse to type 'run' with command field."""
    parsed = verify.parse_verify_pattern("run: echo hello")
    assert parsed["type"] == "run"
    assert parsed["command"] == "echo hello"


def test_parse_file_exists_pattern():
    """file: <path> exists must parse to type 'file_exists'."""
    parsed = verify.parse_verify_pattern("file: some/path.txt exists")
    assert parsed["type"] == "file_exists"
    assert parsed["path"] == "some/path.txt"


def test_parse_file_contains_pattern():
    """file: <path> contains <string> must parse to type 'file_contains'."""
    parsed = verify.parse_verify_pattern("file: some/path.txt contains hello world")
    assert parsed["type"] == "file_contains"
    assert parsed["path"] == "some/path.txt"
    assert parsed["substring"] == "hello world"


def test_parse_html_has_pattern():
    """html: <path> has <selector> must parse to type 'html_has'."""
    parsed = verify.parse_verify_pattern("html: index.html has .my-class")
    assert parsed["type"] == "html_has"
    assert parsed["path"] == "index.html"
    assert parsed["selector"] == ".my-class"


def test_parse_invalid_pattern():
    """Unrecognised text must return type 'invalid'."""
    parsed = verify.parse_verify_pattern("not a valid pattern")
    assert parsed["type"] == "invalid"


# ── run_criterion: file: <path> exists ───────────────────────

def test_file_exists_pattern(tmp_path):
    """file: <path> exists returns PASS when file is present."""
    f = tmp_path / "test.txt"
    f.write_text("content", encoding="utf-8")

    result = verify.run_criterion(f"file: {f} exists")
    assert result["status"] == "PASS", f"Expected PASS, got {result}"


def test_file_exists_pattern_missing(tmp_path):
    """file: <path> exists returns FAIL when file is absent."""
    result = verify.run_criterion(f"file: {tmp_path / 'nonexistent.txt'} exists")
    assert result["status"] == "FAIL"


# ── run_criterion: file: <path> contains <string> ────────────

def test_file_contains_pattern(tmp_path):
    """file: <path> contains <string> returns PASS when substring found."""
    f = tmp_path / "test.txt"
    f.write_text("hello world foo", encoding="utf-8")

    result = verify.run_criterion(f"file: {f} contains hello world")
    assert result["status"] == "PASS", f"Expected PASS, got {result}"


def test_file_contains_pattern_no_match(tmp_path):
    """file: <path> contains <string> returns FAIL when substring absent."""
    f = tmp_path / "test.txt"
    f.write_text("hello world foo", encoding="utf-8")

    result = verify.run_criterion(f"file: {f} contains NOTHERE")
    assert result["status"] == "FAIL"


def test_file_contains_pattern_missing_file(tmp_path):
    """file: <path> contains returns FAIL when file is absent."""
    result = verify.run_criterion(f"file: {tmp_path / 'nofile.txt'} contains anything")
    assert result["status"] == "FAIL"


# ── run_criterion: run: <command> ────────────────────────────

def test_run_pattern_success():
    """run: <command> returns PASS for zero-exit command."""
    result = verify.run_criterion("run: echo ok")
    assert result["status"] == "PASS"


def test_run_pattern_failure():
    """run: <command> returns FAIL for non-zero exit."""
    result = verify.run_criterion("run: false")
    assert result["status"] == "FAIL"


# ── run_criterion: html: <path> has <selector> ───────────────

def test_html_has_pattern(tmp_path):
    """html: <path> has <selector> returns PASS when selector matches, or SKIP if bs4 absent."""
    html = tmp_path / "test.html"
    html.write_text("<html><body><div class='target'>hi</div></body></html>", encoding="utf-8")

    result = verify.run_criterion(f"html: {html} has .target")
    assert result["status"] in ("PASS", "SKIP"), (
        f"Expected PASS or SKIP (bs4 may be absent), got {result}"
    )


def test_html_has_pattern_no_match(tmp_path):
    """html: <path> has <selector> returns FAIL when selector absent (or SKIP if bs4 absent)."""
    html = tmp_path / "test.html"
    html.write_text("<html><body><p>hello</p></body></html>", encoding="utf-8")

    result = verify.run_criterion(f"html: {html} has .absent-class")
    assert result["status"] in ("FAIL", "SKIP"), (
        f"Expected FAIL or SKIP (bs4 may be absent), got {result}"
    )


# ── validate_pattern ─────────────────────────────────────────

def test_validate_pattern_valid():
    """validate_pattern returns True for all valid forms."""
    for pattern in [
        "run: echo ok",
        "file: foo.txt exists",
        "file: foo.txt contains bar",
        "html: index.html has .cls",
    ]:
        valid, _ = verify.validate_pattern(pattern)
        assert valid, f"Expected valid pattern: {pattern}"


def test_validate_pattern_invalid():
    """validate_pattern returns False for garbage text."""
    valid, _ = verify.validate_pattern("this is not a verify pattern")
    assert not valid


# ── run_criterion: dict input form ───────────────────────────

def test_run_criterion_accepts_dict():
    """run_criterion should accept dict with 'verify' key."""
    result = verify.run_criterion({"verify": "run: echo dict_ok"})
    assert result["status"] == "PASS"


# ── run_all_criteria ─────────────────────────────────────────

def test_run_all_criteria_returns_list():
    """run_all_criteria should return a list with a result per criterion."""
    criteria = ["run: echo a", "run: echo b"]
    results = verify.run_all_criteria(criteria)
    assert len(results) == 2
    assert all(r["status"] == "PASS" for r in results)
