#!/usr/bin/env python3
"""DOE Bug Reporter — execution script for /report-doe-bug.

Handles deterministic operations for bug triage:
  --environment           Capture DOE version, OS, Node, Python, shell
  --version-check         Compare local DOE version to latest upstream release
  --check-gh              Verify gh CLI is installed and authenticated
  --scan-tutorials WORDS  Scan tutorial HTML files for keyword matches
  --search-duplicates Q   Search existing GitHub issues for duplicates
  --sanitise TEXT         Strip sensitive data from text before filing

All subcommands output JSON to stdout. The script never makes judgment
calls — it returns data and Claude decides.

Usage:
  python3 execution/doe_bug_report.py --environment
  python3 execution/doe_bug_report.py --version-check
  python3 execution/doe_bug_report.py --check-gh
  python3 execution/doe_bug_report.py --scan-tutorials "snagging error"
  python3 execution/doe_bug_report.py --search-duplicates "health check fails"
  python3 execution/doe_bug_report.py --sanitise "text with sk-abc123 secrets"
"""

import argparse
import glob as globmod
import json
import os
import platform
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

UPSTREAM_REPO = "williamporter/doe-starter-kit"
DOE_KIT_PATH = Path.home() / "doe-starter-kit"
DEFAULT_LABELS = ["bug", "user-reported"]


def _run(cmd, cwd=None, timeout=15):
    """Run a shell command and return (stdout, returncode)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd, timeout=timeout
        )
        return r.stdout.strip(), r.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1


# ---------------------------------------------------------------------------
# --environment
# ---------------------------------------------------------------------------

def capture_environment():
    """Capture DOE kit version, OS, Node, Python, shell info."""
    env = {
        "os": platform.system(),
        "os_version": platform.release(),
        "python_version": platform.python_version(),
        "shell": os.environ.get("SHELL", "unknown"),
        "doe_kit_path": str(DOE_KIT_PATH),
        "doe_kit_exists": DOE_KIT_PATH.is_dir(),
        "doe_version": None,
        "node_version": None,
        "gh_version": None,
        "git_branch": None,
    }

    # DOE kit version
    if DOE_KIT_PATH.is_dir():
        ver, rc = _run("git describe --tags --abbrev=0", cwd=DOE_KIT_PATH)
        if rc == 0 and ver:
            env["doe_version"] = ver

    # Node version
    node_ver, rc = _run("node --version")
    if rc == 0 and node_ver:
        env["node_version"] = node_ver

    # gh version
    gh_ver, rc = _run("gh --version")
    if rc == 0 and gh_ver:
        # First line: "gh version X.Y.Z ..."
        env["gh_version"] = gh_ver.split("\n")[0]

    # Current git branch (of the user's project, not DOE kit)
    branch, rc = _run("git branch --show-current")
    if rc == 0 and branch:
        env["git_branch"] = branch

    return env


# ---------------------------------------------------------------------------
# --check-gh
# ---------------------------------------------------------------------------

def check_gh():
    """Check if gh CLI is installed and authenticated."""
    result = {
        "installed": False,
        "authenticated": False,
        "can_reach_repo": False,
        "message": "",
    }

    # Is gh installed?
    _, rc = _run("gh --version")
    if rc != 0:
        result["message"] = "gh CLI is not installed. Install from https://cli.github.com/"
        return result
    result["installed"] = True

    # Is gh authenticated?
    status, rc = _run("gh auth status")
    if rc != 0:
        result["message"] = "gh CLI is not authenticated. Run: gh auth login"
        return result
    result["authenticated"] = True

    # Can we reach the upstream repo?
    _, rc = _run(f"gh repo view {UPSTREAM_REPO} --json name -q .name")
    if rc != 0:
        result["message"] = (
            f"Cannot access {UPSTREAM_REPO}. "
            "Check your network connection and gh permissions."
        )
        return result
    result["can_reach_repo"] = True
    result["message"] = "gh CLI is ready"

    return result


# ---------------------------------------------------------------------------
# --version-check
# ---------------------------------------------------------------------------

def _parse_changelog_between(changelog_path, local_ver, latest_ver):
    """Extract changelog entries between two version tags.

    Returns a list of {version, date, entries} dicts for versions
    newer than local_ver up to and including latest_ver.
    """
    if not changelog_path.exists():
        return []

    text = changelog_path.read_text(encoding="utf-8")
    # Match lines like: ## [v1.40.0] — 2026-03-18
    header_re = re.compile(r"^##\s+\[v?([\d.]+)\]\s*[-—]\s*(.+)$", re.MULTILINE)

    sections = []
    matches = list(header_re.finditer(text))
    for i, m in enumerate(matches):
        ver = m.group(1)
        date = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append({"version": ver, "date": date, "body": body})

    # Strip leading 'v' for comparison
    local_clean = local_ver.lstrip("v")
    latest_clean = latest_ver.lstrip("v")

    # Filter to versions newer than local, up to latest
    def _ver_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return (0,)

    local_t = _ver_tuple(local_clean)
    latest_t = _ver_tuple(latest_clean)

    relevant = []
    for s in sections:
        s_t = _ver_tuple(s["version"])
        if local_t < s_t <= latest_t:
            relevant.append(s)

    return relevant


def check_version():
    """Compare local DOE version to latest upstream release.

    Returns:
      - local_version: user's current DOE kit tag
      - latest_version: latest upstream release tag
      - is_behind: True if local < latest
      - changelog_entries: entries between local and latest (if behind)
    """
    result = {
        "local_version": None,
        "latest_version": None,
        "is_behind": False,
        "changelog_entries": [],
        "error": None,
    }

    # Get local version
    if not DOE_KIT_PATH.is_dir():
        result["error"] = f"DOE kit not found at {DOE_KIT_PATH}"
        return result

    local_ver, rc = _run("git describe --tags --abbrev=0", cwd=DOE_KIT_PATH)
    if rc != 0 or not local_ver:
        result["error"] = "Could not determine local DOE kit version"
        return result
    result["local_version"] = local_ver

    # Get latest upstream release via gh
    latest_ver, rc = _run(
        f"gh release view --repo {UPSTREAM_REPO} --json tagName -q .tagName"
    )
    if rc != 0 or not latest_ver:
        result["error"] = (
            "Could not fetch latest upstream version. "
            "Check gh auth and network."
        )
        return result
    result["latest_version"] = latest_ver

    # Compare versions
    def _ver_tuple(v):
        try:
            return tuple(int(x) for x in v.lstrip("v").split("."))
        except ValueError:
            return (0,)

    local_t = _ver_tuple(local_ver)
    latest_t = _ver_tuple(latest_ver)
    result["is_behind"] = local_t < latest_t

    # If behind, parse CHANGELOG for relevant entries
    if result["is_behind"]:
        changelog_path = DOE_KIT_PATH / "CHANGELOG.md"
        entries = _parse_changelog_between(changelog_path, local_ver, latest_ver)
        result["changelog_entries"] = entries

    return result


# ---------------------------------------------------------------------------
# --scan-tutorials
# ---------------------------------------------------------------------------

class _HeadingExtractor(HTMLParser):
    """Extract h1/h2/h3 headings and their surrounding text from HTML."""

    def __init__(self):
        super().__init__()
        self._in_heading = False
        self._heading_tag = None
        self._current_text = []
        self.headings = []  # [{tag, text, pos}]

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3"):
            self._in_heading = True
            self._heading_tag = tag
            self._current_text = []

    def handle_endtag(self, tag):
        if tag == self._heading_tag and self._in_heading:
            self._in_heading = False
            text = " ".join("".join(self._current_text).split())
            if text:
                self.headings.append({
                    "tag": self._heading_tag,
                    "text": text,
                })
            self._heading_tag = None

    def handle_data(self, data):
        if self._in_heading:
            self._current_text.append(data)


def scan_tutorials(keywords):
    """Scan tutorial HTML files for keyword matches in headings.

    Returns ranked list of {page, section, relevance} matches.
    """
    # Scans docs/tutorial/*.html in the DOE starter kit
    tutorial_dir = DOE_KIT_PATH / "docs" / "tutorial"
    result = {
        "tutorial_dir_exists": tutorial_dir.is_dir(),
        "matches": [],
        "error": None,
    }

    if not tutorial_dir.is_dir():
        result["error"] = f"Tutorial directory not found: {tutorial_dir}"
        return result

    # Normalise keywords for matching
    kw_lower = [w.lower() for w in keywords.split() if len(w) > 2]
    if not kw_lower:
        result["error"] = "No usable keywords provided"
        return result

    html_files = sorted(tutorial_dir.glob("*.html"))
    matches = []

    for html_file in html_files:
        try:
            content = html_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        parser = _HeadingExtractor()
        parser.feed(content)

        page_name = html_file.stem
        content_lower = content.lower()

        # Score each heading by keyword overlap
        for heading in parser.headings:
            h_lower = heading["text"].lower()
            # Count keyword hits in heading text
            heading_hits = sum(1 for kw in kw_lower if kw in h_lower)
            # Count keyword hits in full page content (weaker signal)
            page_hits = sum(1 for kw in kw_lower if kw in content_lower)

            if heading_hits > 0 or page_hits >= len(kw_lower):
                relevance = heading_hits * 3 + page_hits
                matches.append({
                    "page": page_name,
                    "file": html_file.name,
                    "section": heading["text"],
                    "heading_level": heading["tag"],
                    "relevance": relevance,
                })

        # Also add a page-level match if keywords appear frequently
        if not any(m["page"] == page_name for m in matches):
            page_hits = sum(1 for kw in kw_lower if kw in content_lower)
            if page_hits >= max(1, len(kw_lower) // 2):
                matches.append({
                    "page": page_name,
                    "file": html_file.name,
                    "section": parser.headings[0]["text"] if parser.headings else page_name,
                    "heading_level": "page",
                    "relevance": page_hits,
                })

    # Sort by relevance descending, take top 5
    matches.sort(key=lambda m: m["relevance"], reverse=True)
    result["matches"] = matches[:5]

    return result


# ---------------------------------------------------------------------------
# --search-duplicates
# ---------------------------------------------------------------------------

def search_duplicates(query):
    """Search existing GitHub issues for potential duplicates.

    Returns matching open issues from the upstream repo.
    """
    result = {
        "matches": [],
        "error": None,
    }

    cmd = (
        f'gh issue list --repo {UPSTREAM_REPO} '
        f'--search "{query}" --state open '
        f'--json number,title,url,labels,createdAt --limit 5'
    )
    stdout, rc = _run(cmd)

    if rc != 0:
        result["error"] = "Could not search issues. Check gh auth and network."
        return result

    try:
        issues = json.loads(stdout) if stdout else []
        result["matches"] = issues
    except json.JSONDecodeError:
        result["error"] = "Failed to parse issue search results"

    return result


# ---------------------------------------------------------------------------
# --sanitise
# ---------------------------------------------------------------------------

# Patterns to strip from bug report text
_SANITISE_PATTERNS = [
    # API keys: sk-..., pk_..., key_..., token_..., secret_...
    (r'\b(sk-[a-zA-Z0-9]{10,})\b', '[REDACTED_API_KEY]'),
    (r'\b(pk_[a-zA-Z0-9]{10,})\b', '[REDACTED_API_KEY]'),
    (r'\b(key_[a-zA-Z0-9]{10,})\b', '[REDACTED_API_KEY]'),
    (r'\b(token_[a-zA-Z0-9_]{10,})\b', '[REDACTED_TOKEN]'),
    (r'\b(secret_[a-zA-Z0-9_]{10,})\b', '[REDACTED_SECRET]'),
    # Bearer tokens
    (r'(Bearer\s+[a-zA-Z0-9._\-]{20,})', '[REDACTED_BEARER_TOKEN]'),
    # .env style KEY=VALUE patterns (only when KEY looks like a secret)
    (r'\b[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|AUTH)[A-Z_]*\s*=\s*\S+',
     '[REDACTED_ENV_VAR]'),
    # Absolute home directory paths (replace with ~)
    (r'/Users/[a-zA-Z0-9._-]+/', '~/'),
    (r'/home/[a-zA-Z0-9._-]+/', '~/'),
    # Windows user paths
    (r'C:\\Users\\[a-zA-Z0-9._-]+\\', '~\\\\'),
    # Email addresses
    (r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[REDACTED_EMAIL]'),
]


def sanitise(text):
    """Strip sensitive data from text before filing as a GitHub issue.

    Removes: API keys, .env secrets, absolute paths, email addresses.
    Preserves: DOE kit paths (converted to ~/doe-starter-kit/...).
    """
    result = {
        "sanitised": text,
        "redactions": 0,
    }

    sanitised = text
    total_redactions = 0

    for pattern, replacement in _SANITISE_PATTERNS:
        sanitised, count = re.subn(pattern, replacement, sanitised)
        total_redactions += count

    result["sanitised"] = sanitised
    result["redactions"] = total_redactions

    return result


# ---------------------------------------------------------------------------
# --file-issue
# ---------------------------------------------------------------------------

ISSUE_TEMPLATE = """## Summary
{summary}

## Component
`{component}`

## Environment
| Field | Value |
|-------|-------|
| DOE Kit Version | {doe_version} |
| Project Type | {project_type} |
| OS | {os} {os_version} |
| Node | {node_version} |
| Python | {python_version} |
| Shell | {shell} |

## Steps to Reproduce
{steps}

## Error Output
```
{error_output}
```

## Expected vs Actual
**Expected:** {expected}
**Actual:** {actual}

## What Was Tried
{what_was_tried}

## Claude's Analysis
{claude_analysis}

## User's Description
{user_description}

## Severity
{severity}

## Reproducibility
{reproducibility}

---
*Filed via `/report-doe-bug` from DOE Kit {doe_version}*"""

DUPLICATE_COMMENT_TEMPLATE = """### Additional report

**User's version:** {doe_version}
**Project type:** {project_type}
**Severity:** {severity}
**Their description:** {user_description}
**Environment:** {os}, Python {python_version}, Node {node_version}

---
*+1 via `/report-doe-bug`*"""


def file_issue(title, body, labels):
    """File a GitHub issue on the upstream DOE repo.

    Returns the issue URL on success, or writes a local fallback file.
    """
    result = {
        "filed": False,
        "issue_url": None,
        "fallback_file": None,
        "error": None,
    }

    # Check gh availability first
    gh_status = check_gh()
    if not gh_status["can_reach_repo"]:
        # Write local fallback
        fallback = _write_local_fallback(title, body, labels)
        result["fallback_file"] = fallback
        result["error"] = (
            f"Cannot reach {UPSTREAM_REPO}. "
            f"Bug report saved locally to {fallback}"
        )
        return result

    # Build label flags
    label_parts = []
    for label in labels:
        label_parts.append(f'--label "{label}"')
    label_str = " ".join(label_parts)

    # File the issue
    cmd = (
        f'gh issue create --repo {UPSTREAM_REPO} '
        f'--title "{title}" '
        f'--body "{body}" '
        f'{label_str}'
    )
    stdout, rc = _run(cmd, timeout=30)

    if rc != 0:
        # Fallback to local file
        fallback = _write_local_fallback(title, body, labels)
        result["fallback_file"] = fallback
        result["error"] = (
            f"Failed to create issue. "
            f"Bug report saved locally to {fallback}"
        )
        return result

    result["filed"] = True
    result["issue_url"] = stdout.strip()
    return result


def _write_local_fallback(title, body, labels):
    """Write bug report to a local .tmp/ markdown file as fallback."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"doe-bug-report-{timestamp}.md"

    # Find project root or use cwd
    tmp_dir = Path.cwd() / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    filepath = tmp_dir / filename

    content = f"# DOE Bug Report\n\n"
    content += f"**Title:** {title}\n"
    content += f"**Labels:** {', '.join(labels)}\n"
    content += f"**Generated:** {datetime.now().isoformat()}\n\n"
    content += f"---\n\n{body}\n\n---\n\n"
    content += f"## How to file manually\n\n"
    content += f"1. Go to https://github.com/{UPSTREAM_REPO}/issues/new\n"
    content += f"2. Copy the title and body above\n"
    content += f"3. Add labels: {', '.join(labels)}\n"
    content += f"4. Submit\n"

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# ---------------------------------------------------------------------------
# --add-comment
# ---------------------------------------------------------------------------

def add_comment(issue_number, body):
    """Add a structured duplicate comment, reaction, and auto-escalate priority.

    When a duplicate is found:
    1. Post the structured comment
    2. Add a +1 reaction (for sorting by most-affected)
    3. Count existing comments and escalate priority labels:
       - 2+ duplicate comments → priority:high
       - 5+ duplicate comments → priority:critical
    """
    result = {
        "commented": False,
        "reaction_added": False,
        "priority_escalated": None,
        "total_reports": 0,
        "error": None,
    }

    # 1. Post the comment
    cmd = (
        f'gh issue comment {issue_number} --repo {UPSTREAM_REPO} '
        f'--body "{body}"'
    )
    _, rc = _run(cmd, timeout=30)

    if rc != 0:
        result["error"] = f"Failed to add comment to issue #{issue_number}"
        return result
    result["commented"] = True

    # 2. Add +1 reaction for sorting
    reaction_cmd = (
        f'gh api repos/{UPSTREAM_REPO}/issues/{issue_number}/reactions '
        f'-f content="+1" --silent'
    )
    _, rc = _run(reaction_cmd, timeout=15)
    result["reaction_added"] = (rc == 0)

    # 3. Count duplicate comments and auto-escalate priority
    count_cmd = (
        f'gh api repos/{UPSTREAM_REPO}/issues/{issue_number}/comments '
        f'--jq "length"'
    )
    count_str, rc = _run(count_cmd, timeout=15)
    if rc == 0 and count_str.strip().isdigit():
        comment_count = int(count_str.strip())
        # Count comments that contain our marker (duplicate reports)
        report_cmd = (
            f'gh api repos/{UPSTREAM_REPO}/issues/{issue_number}/comments '
            f'--jq \'[.[] | select(.body | contains("+1 via"))] | length\''
        )
        report_str, rc2 = _run(report_cmd, timeout=15)
        if rc2 == 0 and report_str.strip().isdigit():
            report_count = int(report_str.strip())
        else:
            report_count = comment_count  # fallback: treat all as reports

        # +1 for the original issue author
        result["total_reports"] = report_count + 1

        # Escalate priority labels
        new_priority = None
        if report_count >= 5:
            new_priority = "priority:critical"
        elif report_count >= 2:
            new_priority = "priority:high"

        if new_priority:
            # Remove old priority labels first
            for old in ["priority:high", "priority:critical"]:
                if old != new_priority:
                    _run(
                        f'gh issue edit {issue_number} --repo {UPSTREAM_REPO} '
                        f'--remove-label "{old}"',
                        timeout=15,
                    )
            # Add new priority label
            _, rc = _run(
                f'gh issue edit {issue_number} --repo {UPSTREAM_REPO} '
                f'--add-label "{new_priority}"',
                timeout=15,
            )
            if rc == 0:
                result["priority_escalated"] = new_priority

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DOE Bug Reporter — deterministic execution script"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--environment", action="store_true",
                       help="Capture environment info")
    group.add_argument("--version-check", action="store_true",
                       help="Compare local DOE version to latest upstream")
    group.add_argument("--check-gh", action="store_true",
                       help="Verify gh CLI availability and auth")
    group.add_argument("--scan-tutorials", metavar="KEYWORDS",
                       help="Scan tutorial HTML for keyword matches")
    group.add_argument("--search-duplicates", metavar="QUERY",
                       help="Search existing issues for duplicates")
    group.add_argument("--sanitise", metavar="TEXT",
                       help="Strip sensitive data from text")
    group.add_argument("--file-issue", nargs=3, metavar=("TITLE", "BODY", "LABELS"),
                       help="File a GitHub issue (labels comma-separated)")
    group.add_argument("--add-comment", nargs=2, metavar=("NUMBER", "BODY"),
                       help="Add a comment to an existing issue")

    args = parser.parse_args()

    if args.environment:
        result = capture_environment()
    elif args.version_check:
        result = check_version()
    elif args.check_gh:
        result = check_gh()
    elif args.scan_tutorials is not None:
        result = scan_tutorials(args.scan_tutorials)
    elif args.search_duplicates is not None:
        result = search_duplicates(args.search_duplicates)
    elif args.sanitise is not None:
        result = sanitise(args.sanitise)
    elif args.file_issue is not None:
        title, body, labels_str = args.file_issue
        labels = [l.strip() for l in labels_str.split(",")]
        result = file_issue(title, body, labels)
    elif args.add_comment is not None:
        number, body = args.add_comment
        result = add_comment(number, body)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
