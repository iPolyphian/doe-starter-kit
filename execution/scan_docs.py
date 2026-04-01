#!/usr/bin/env python3
"""
Scan DOE tutorial and reference docs against the current DOE kit version.

Compares the docs-manifest.json against the actual commands in
~/.claude/commands/ to find undocumented commands, stale doc versions,
and removed commands still referenced in docs.

Usage:
    python3 execution/scan_docs.py                  # Full scan report
    python3 execution/scan_docs.py --json            # Machine-readable output
    python3 execution/scan_docs.py --update-manifest # Bump all verifiedAt to current version
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "docs" / "docs-manifest.json"
COMMANDS_DIR = Path.home() / ".claude" / "commands"
DOE_KIT_DIR = Path.home() / "doe-starter-kit"


def get_doe_version():
    """Get the current DOE kit version from git describe --tags."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags"],
            cwd=DOE_KIT_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: read from manifest
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        return manifest.get("doeVersion", "unknown")
    return "unknown"


def load_manifest():
    """Load the docs manifest."""
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text())


def get_available_commands():
    """Scan ~/.claude/commands/ for all .md command files."""
    if not COMMANDS_DIR.exists():
        print(f"WARNING: Commands directory not found at {COMMANDS_DIR}", file=sys.stderr)
        return set()
    commands = set()
    for f in COMMANDS_DIR.iterdir():
        if f.suffix == ".md" and f.name != "README.md":
            commands.add(f.stem)
    return commands


def get_documented_commands(manifest):
    """Extract all command names from the 'covers' arrays across all doc sections."""
    documented = set()
    for section_key in ("tutorial", "reference"):
        section = manifest.get(section_key, {})
        for doc_file, meta in section.items():
            for topic in meta.get("covers", []):
                documented.add(topic)
    return documented


def get_stale_docs(manifest, current_version):
    """Find docs where verifiedAt is older than the current DOE kit version."""
    stale = []
    for section_key in ("tutorial", "reference"):
        section = manifest.get(section_key, {})
        for doc_file, meta in section.items():
            verified = meta.get("verifiedAt", "unknown")
            if verified != current_version:
                stale.append({
                    "section": section_key,
                    "file": doc_file,
                    "verifiedAt": verified,
                    "currentVersion": current_version,
                })
    return stale


def check_doc_files_exist(manifest):
    """Check that all files listed in the manifest actually exist on disk."""
    missing = []
    for section_key, base_dir in [
        ("tutorial", PROJECT_ROOT / "docs" / "tutorial"),
        ("reference", PROJECT_ROOT / "docs" / "reference"),
    ]:
        section = manifest.get(section_key, {})
        for doc_file in section:
            full_path = base_dir / doc_file
            if not full_path.exists():
                missing.append({
                    "section": section_key,
                    "file": doc_file,
                    "expectedPath": str(full_path),
                })
    return missing


def update_manifest(manifest, current_version):
    """Bump all verifiedAt versions and metadata to current."""
    manifest["doeVersion"] = current_version
    # Update lastFullScan to today
    from datetime import date
    manifest["lastFullScan"] = date.today().isoformat()

    for section_key in ("tutorial", "reference"):
        section = manifest.get(section_key, {})
        for doc_file in section:
            section[doc_file]["verifiedAt"] = current_version

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def run_scan(args):
    """Run the full doc scan and produce a report."""
    manifest = load_manifest()
    current_version = get_doe_version()
    manifest_version = manifest.get("doeVersion", "unknown")

    # Handle --update-manifest
    if args.update_manifest:
        manifest = update_manifest(manifest, current_version)
        if args.json:
            print(json.dumps({"action": "updated", "version": current_version}))
        else:
            print(f"Manifest updated: all docs now verified at {current_version}")
        return

    available_commands = get_available_commands()
    documented_topics = get_documented_commands(manifest)
    stale_docs = get_stale_docs(manifest, current_version)
    missing_files = check_doc_files_exist(manifest)

    # Commands that exist in ~/.claude/commands/ but aren't in any covers array
    undocumented = sorted(available_commands - documented_topics)

    # Topics in covers arrays that don't map to an actual command file
    # (Only check command-like topics, not conceptual ones)
    conceptual_topics = {
        "overview", "quick-start", "installation", "prerequisites",
        "claude-md-setup", "choose-setup", "recipe-book-example",
        "doe-architecture", "sessions", "commits", "state", "contracts",
        "self-annealing", "ai-concepts", "session-lifecycle", "daily-routine",
        "workflow-paths", "planning", "prompting", "feature-lifecycle",
        "recipe-book", "fitness-tracker", "events-board", "team-dashboard",
        "best-practices", "common-mistakes", "context-management",
        "what-claude-reads", "sync-pull-doe", "troubleshooting",
        "glossary-terms", "first-session", "configuration", "glossary",
        "state-management", "new-project", "claude-md", "state-md",
        "todo-md", "learnings-md", "roadmap-md", "directives",
        "execution-scripts", "hooks",
    }
    command_topics = documented_topics - conceptual_topics
    removed_commands = sorted(command_topics - available_commands)

    documented_command_count = len(command_topics & available_commands)
    total_commands = len(available_commands)

    # Build result
    result = {
        "currentVersion": current_version,
        "manifestVersion": manifest_version,
        "totalCommands": total_commands,
        "documentedCommands": documented_command_count,
        "undocumented": undocumented,
        "removedButDocumented": removed_commands,
        "staleDocs": stale_docs,
        "missingFiles": missing_files,
        "allUpToDate": (
            len(undocumented) == 0
            and len(removed_commands) == 0
            and len(stale_docs) == 0
            and len(missing_files) == 0
        ),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Human-readable report
    lines = []
    lines.append(f"DOE Docs Scan -- {current_version}")
    lines.append("=" * len(lines[0]))
    lines.append("")

    # Commands coverage
    lines.append("Commands coverage:")
    if total_commands > 0:
        mark = "+" if documented_command_count == total_commands else "!"
        lines.append(f"  {mark} {documented_command_count}/{total_commands} commands documented")
    else:
        lines.append("  ! No commands directory found")
    lines.append("")

    if undocumented:
        lines.append("  New (undocumented):")
        for cmd in undocumented:
            lines.append(f"    /{cmd} -- not found in any doc file")
        lines.append("")

    if removed_commands:
        lines.append("  Removed (still documented):")
        for cmd in removed_commands:
            lines.append(f"    /{cmd} -- documented but no command file exists")
        lines.append("")

    # Stale docs
    if stale_docs:
        lines.append("  Stale (doc version < kit version):")
        for entry in stale_docs:
            lines.append(
                f"    {entry['file']} -- verified at {entry['verifiedAt']}, "
                f"kit is {entry['currentVersion']}"
            )
        lines.append("")

    # Missing files
    if missing_files:
        lines.append("  Missing files (in manifest but not on disk):")
        for entry in missing_files:
            lines.append(f"    {entry['section']}/{entry['file']}")
        lines.append("")

    if result["allUpToDate"]:
        lines.append("All docs up to date.")
    else:
        issues = []
        if undocumented:
            issues.append(f"{len(undocumented)} undocumented")
        if removed_commands:
            issues.append(f"{len(removed_commands)} removed")
        if stale_docs:
            issues.append(f"{len(stale_docs)} stale")
        if missing_files:
            issues.append(f"{len(missing_files)} missing files")
        lines.append(f"Issues found: {', '.join(issues)}.")

    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Scan DOE docs against current kit version"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        help="Bump all verifiedAt versions to current DOE kit version",
    )
    args = parser.parse_args()
    run_scan(args)


if __name__ == "__main__":
    main()
