#!/usr/bin/env python3
"""DOE Feature Request — execution script for /request-doe-feature.

Handles deterministic operations for feature request triage:
  --scan-existing DESC    Scan ~/doe-starter-kit for overlap with described feature
  --search-duplicates Q   Search existing GitHub enhancement issues for duplicates
  --file JSON_PATH        File a GitHub issue from a structured JSON file
  --sanitise TEXT         Strip sensitive data from text before filing
  --categorise DESC       Auto-categorise into DOE areas (Commands, Execution, etc.)
  --fallback JSON_PATH    Save feature request locally when gh is unavailable

All subcommands output JSON to stdout. The script never makes judgment
calls — it returns data and Claude decides.

Usage:
  python3 execution/doe_feature_request.py --scan-existing "auto-categorise commands"
  python3 execution/doe_feature_request.py --search-duplicates "wave mode improvements"
  python3 execution/doe_feature_request.py --file .tmp/feature-request.json
  python3 execution/doe_feature_request.py --sanitise "text with sk-abc123 secrets"
  python3 execution/doe_feature_request.py --categorise "add new slash command for review"
  python3 execution/doe_feature_request.py --fallback .tmp/feature-request.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

UPSTREAM_REPO = "williamporter/doe-starter-kit"
DOE_KIT_PATH = Path.home() / "doe-starter-kit"
DEFAULT_LABELS = ["enhancement", "user-requested"]

# DOE areas for categorisation
DOE_AREAS = ["Commands", "Execution", "Directives", "Hooks", "Docs", "Structure"]

# Keyword hints for each DOE area (used by --categorise)
_AREA_KEYWORDS = {
    "Commands": [
        "command", "slash", "/crack", "/wrap", "/scope", "/audit", "/sync",
        "cli", "task", "run", "script", "invoke",
    ],
    "Execution": [
        "execution", "script", "python", "api", "import", "export", "data",
        "transform", "file", "build", "generate", "pipeline",
    ],
    "Directives": [
        "directive", "sop", "instruction", "rule", "policy", "guidance",
        "workflow", "process", "procedure", "markdown",
    ],
    "Hooks": [
        "hook", "pre-commit", "post", "trigger", "git", "auto", "lint",
        "check", "verify", "guard",
    ],
    "Docs": [
        "doc", "documentation", "tutorial", "guide", "readme", "changelog",
        "html", "page", "reference", "example",
    ],
    "Structure": [
        "structure", "directory", "folder", "layout", "architecture", "state",
        "config", "template", "scaffold", "skeleton",
    ],
}


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


def _check_gh_available():
    """Return True if gh CLI is installed and reachable."""
    _, rc = _run("gh --version")
    return rc == 0


# ---------------------------------------------------------------------------
# --scan-existing
# ---------------------------------------------------------------------------

def scan_existing(description):
    """Scan ~/doe-starter-kit for overlap with the described feature.

    Checks file names, CLAUDE.md, commands/, and directives/ for content
    related to the description. Returns a list of potentially overlapping
    files and features.
    """
    result = {
        "doe_kit_exists": DOE_KIT_PATH.is_dir(),
        "matches": [],
        "error": None,
    }

    if not DOE_KIT_PATH.is_dir():
        result["error"] = f"DOE kit not found at {DOE_KIT_PATH}"
        return result

    # Normalise description into search terms (words > 2 chars)
    terms = [w.lower() for w in re.split(r'\W+', description) if len(w) > 2]
    if not terms:
        result["error"] = "No usable search terms in description"
        return result

    matches = []

    # Paths to scan
    scan_targets = [
        (DOE_KIT_PATH / "CLAUDE.md", "CLAUDE.md"),
        *[
            (p, str(p.relative_to(DOE_KIT_PATH)))
            for p in sorted((DOE_KIT_PATH / "commands").glob("*"))
            if p.is_file()
        ],
        *[
            (p, str(p.relative_to(DOE_KIT_PATH)))
            for p in sorted((DOE_KIT_PATH / "directives").glob("*.md"))
            if p.is_file()
        ],
    ]

    # Also include top-level markdown files
    for p in sorted(DOE_KIT_PATH.glob("*.md")):
        if p.name != "CLAUDE.md":
            scan_targets.append((p, p.name))

    for filepath, label in scan_targets:
        if not filepath.exists():
            continue

        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        content_lower = content.lower()
        name_lower = filepath.name.lower()

        # Score: hits in filename, hits in content
        name_hits = sum(1 for t in terms if t in name_lower)
        content_hits = sum(1 for t in terms if t in content_lower)

        if name_hits > 0 or content_hits >= max(1, len(terms) // 2):
            relevance = name_hits * 5 + content_hits
            matches.append({
                "file": label,
                "name_hits": name_hits,
                "content_hits": content_hits,
                "relevance": relevance,
                "note": _summarise_overlap(content, terms),
            })

    # Sort by relevance descending, cap at 10
    matches.sort(key=lambda m: m["relevance"], reverse=True)
    result["matches"] = matches[:10]

    return result


def _summarise_overlap(content, terms):
    """Return the first line of content that contains any of the terms."""
    for line in content.splitlines():
        line_l = line.lower().strip()
        if any(t in line_l for t in terms) and len(line_l) > 5:
            return line.strip()[:120]
    return ""


# ---------------------------------------------------------------------------
# --search-duplicates
# ---------------------------------------------------------------------------

def search_duplicates(query):
    """Search existing GitHub enhancement issues for potential duplicates.

    Uses the enhancement label to restrict results to feature requests.
    Returns matching open issues from the upstream repo.
    """
    result = {
        "matches": [],
        "error": None,
    }

    if not _check_gh_available():
        print(
            "Warning: gh CLI is not available. Cannot search for duplicate issues.",
            file=sys.stderr
        )
        result["error"] = "gh CLI is not available"
        return result

    cmd = (
        f'gh issue list --repo {UPSTREAM_REPO} '
        f'--label enhancement '
        f'--search "{query}" '
        f'--json number,title,body --limit 5'
    )
    stdout, rc = _run(cmd)

    if rc != 0:
        print(
            "Warning: Could not search issues. Check gh auth and network.",
            file=sys.stderr
        )
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

# Patterns to strip from feature request text
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
    # IP addresses
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]'),
]


def sanitise(text):
    """Strip potential sensitive data from text before filing as a GitHub issue.

    Removes: API keys, .env secrets, absolute paths containing usernames,
    email addresses, and IP addresses.
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
# --categorise
# ---------------------------------------------------------------------------

def categorise(description):
    """Auto-categorise a feature description into a DOE area.

    DOE areas: Commands, Execution, Directives, Hooks, Docs, Structure.
    Returns the best-matching category and scores for all areas.
    """
    desc_lower = description.lower()
    words = set(re.split(r'\W+', desc_lower))

    scores = {}
    for area, keywords in _AREA_KEYWORDS.items():
        # Count keyword hits (substring match for compound words)
        score = sum(1 for kw in keywords if kw in desc_lower)
        scores[area] = score

    best_area = max(scores, key=lambda a: scores[a])
    # If all scores are zero, fall back to "Commands" as the most general
    if scores[best_area] == 0:
        best_area = "Commands"

    return {
        "category": best_area,
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# --file
# ---------------------------------------------------------------------------

def _build_issue_body(data):
    """Build a GitHub issue body from a structured feature request dict."""
    sections = []

    summary = data.get("summary", "").strip()
    if summary:
        sections.append(f"## Summary\n{summary}")

    motivation = data.get("motivation", "").strip()
    if motivation:
        sections.append(f"## Motivation\n{motivation}")

    proposed_solution = data.get("proposed_solution", "").strip()
    if proposed_solution:
        sections.append(f"## Proposed Solution\n{proposed_solution}")

    doe_area = data.get("doe_area", "").strip()
    if doe_area:
        sections.append(f"## DOE Area\n`{doe_area}`")

    alternatives = data.get("alternatives", "").strip()
    if alternatives:
        sections.append(f"## Alternatives Considered\n{alternatives}")

    examples = data.get("examples", "").strip()
    if examples:
        sections.append(f"## Examples / Mockups\n{examples}")

    user_description = data.get("user_description", "").strip()
    if user_description:
        sections.append(f"## User's Description\n{user_description}")

    doe_version = data.get("doe_version", "unknown")
    sections.append(
        f"---\n*Filed via `/request-doe-feature` from DOE Kit {doe_version}*"
    )

    return "\n\n".join(sections)


def file_issue(json_path):
    """File a GitHub issue from a structured feature request JSON file.

    The JSON may contain: title, summary, motivation, proposed_solution,
    doe_area, alternatives, examples, user_description, doe_version,
    quick_win (bool).

    If quick_win is true, adds the quick-win label.
    Falls back to --fallback if gh is unavailable.
    """
    result = {
        "filed": False,
        "issue_url": None,
        "fallback_file": None,
        "error": None,
    }

    # Load JSON
    path = Path(json_path)
    if not path.exists():
        result["error"] = f"JSON file not found: {json_path}"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["error"] = f"Could not read JSON file: {e}"
        return result

    title = data.get("title", "").strip()
    if not title:
        result["error"] = "JSON must contain a 'title' field"
        return result

    body = _build_issue_body(data)

    # Build label list
    labels = list(DEFAULT_LABELS)
    if data.get("quick_win"):
        labels.append("quick-win")

    # Check gh availability
    if not _check_gh_available():
        print(
            "Warning: gh CLI is not available. Saving feature request locally.",
            file=sys.stderr
        )
        fallback_path = _write_local_fallback(title, body, labels, data)
        result["fallback_file"] = fallback_path
        result["error"] = (
            f"gh CLI unavailable. Feature request saved locally to {fallback_path}"
        )
        return result

    # Build label flags
    label_parts = [f'--label "{lbl}"' for lbl in labels]
    label_str = " ".join(label_parts)

    cmd = (
        f'gh issue create --repo {UPSTREAM_REPO} '
        f'--title "{title}" '
        f'--body "{body}" '
        f'{label_str}'
    )
    stdout, rc = _run(cmd, timeout=30)

    if rc != 0:
        print(
            "Warning: gh issue create failed. Saving feature request locally.",
            file=sys.stderr
        )
        fallback_path = _write_local_fallback(title, body, labels, data)
        result["fallback_file"] = fallback_path
        result["error"] = (
            f"Failed to create issue. Feature request saved locally to {fallback_path}"
        )
        return result

    result["filed"] = True
    result["issue_url"] = stdout.strip()
    return result


# ---------------------------------------------------------------------------
# --fallback
# ---------------------------------------------------------------------------

def fallback(json_path):
    """Save a structured feature request to a local fallback file.

    Writes to .tmp/feature-requests/<title-slug>.json in the current
    working directory. Use this when gh is unavailable or as a draft step
    before filing.
    """
    result = {
        "saved": False,
        "fallback_file": None,
        "error": None,
    }

    path = Path(json_path)
    if not path.exists():
        result["error"] = f"JSON file not found: {json_path}"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["error"] = f"Could not read JSON file: {e}"
        return result

    title = data.get("title", "untitled").strip()
    labels = list(DEFAULT_LABELS)
    if data.get("quick_win"):
        labels.append("quick-win")

    body = _build_issue_body(data)
    fallback_path = _write_local_fallback(title, body, labels, data)

    result["saved"] = True
    result["fallback_file"] = fallback_path
    return result


def _slug(text):
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:60].strip('-')


def _write_local_fallback(title, body, labels, data=None):
    """Write feature request to .tmp/feature-requests/<slug>.json as fallback."""
    from datetime import datetime

    slug = _slug(title) or "feature-request"
    filename = f"{slug}.json"

    tmp_dir = Path.cwd() / ".tmp" / "feature-requests"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    filepath = tmp_dir / filename

    payload = {
        "title": title,
        "labels": labels,
        "body": body,
        "generated": datetime.now().isoformat(),
        "how_to_file": (
            f"1. Go to https://github.com/{UPSTREAM_REPO}/issues/new\n"
            f"2. Paste the title and body above\n"
            f"3. Add labels: {', '.join(labels)}\n"
            f"4. Submit"
        ),
    }
    if data:
        payload["source_data"] = data

    filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(filepath)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "DOE Feature Request — deterministic execution script. "
            "Handles scanning, deduplication, sanitisation, and filing "
            "of feature requests against the DOE starter kit."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--scan-existing", metavar="DESCRIPTION",
        help=(
            "Scan ~/doe-starter-kit for overlap with the described feature. "
            "Checks file names, CLAUDE.md, commands/, directives/."
        ),
    )
    group.add_argument(
        "--search-duplicates", metavar="QUERY",
        help=(
            "Search GitHub issues on williamporter/doe-starter-kit with the "
            "enhancement label for potential duplicates."
        ),
    )
    group.add_argument(
        "--file", metavar="JSON_PATH",
        help=(
            "File a GitHub issue from a structured JSON file. "
            "Adds enhancement and user-requested labels. "
            "If quick_win is true in the JSON, also adds quick-win label."
        ),
    )
    group.add_argument(
        "--sanitise", metavar="TEXT",
        help=(
            "Strip potential sensitive data (API keys, file paths containing "
            "usernames, email addresses, IP addresses) from text."
        ),
    )
    group.add_argument(
        "--categorise", metavar="DESCRIPTION",
        help=(
            "Auto-categorise into DOE areas: "
            f"{', '.join(DOE_AREAS)}. "
            "Returns the best-matching category."
        ),
    )
    group.add_argument(
        "--fallback", metavar="JSON_PATH",
        help=(
            "Save structured feature request to a local fallback file at "
            ".tmp/feature-requests/<title-slug>.json when gh is unavailable."
        ),
    )

    args = parser.parse_args()

    if args.scan_existing is not None:
        result = scan_existing(args.scan_existing)
    elif args.search_duplicates is not None:
        result = search_duplicates(args.search_duplicates)
    elif args.file is not None:
        result = file_issue(args.file)
    elif args.sanitise is not None:
        result = sanitise(args.sanitise)
    elif args.categorise is not None:
        result = categorise(args.categorise)
    elif args.fallback is not None:
        result = fallback(args.fallback)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
