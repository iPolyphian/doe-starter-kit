#!/usr/bin/env python3
"""Stamp tutorial HTML files with a new DOE Starter Kit version number."""

import argparse
import re
import sys
from pathlib import Path


def stamp_version(version: str, root: Path) -> tuple[int, int]:
    """Replace version strings in all tutorial HTML files.

    Returns (files_updated, total_replacements).
    """
    tutorial_dir = root / "docs" / "tutorial"
    if not tutorial_dir.exists():
        print(f"Error: tutorial directory not found: {tutorial_dir}", file=sys.stderr)
        sys.exit(1)

    html_files = list(tutorial_dir.glob("*.html"))
    if not html_files:
        print(f"Warning: no HTML files found in {tutorial_dir}")
        return 0, 0

    patterns = [
        # Footer and hero badge: "DOE Starter Kit v1.2.3"
        (re.compile(r"DOE Starter Kit v\d+\.\d+\.\d+"), f"DOE Starter Kit {version}"),
        # Terminal mockup: "latest: v1.2.3"
        (re.compile(r"latest: v\d+\.\d+\.\d+"), f"latest: {version}"),
    ]

    files_updated = 0
    total_replacements = 0

    for html_file in sorted(html_files):
        original = html_file.read_text(encoding="utf-8")
        updated = original
        file_replacements = 0

        for pattern, replacement in patterns:
            # Count only matches whose text will actually change
            for m in pattern.finditer(updated):
                if m.group() != replacement:
                    file_replacements += 1
            updated = pattern.sub(replacement, updated)

        if file_replacements > 0:
            html_file.write_text(updated, encoding="utf-8")
            files_updated += 1
            total_replacements += file_replacements

    return files_updated, total_replacements


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stamp tutorial HTML files with a new version number."
    )
    parser.add_argument("version", help="Version string, e.g. v1.37.0")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override base directory (default: parent of this script's directory)",
    )
    args = parser.parse_args()

    # Validate version format
    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.version):
        print(
            f"Error: version must match vX.Y.Z format, got: {args.version}",
            file=sys.stderr,
        )
        sys.exit(1)

    root = args.root if args.root is not None else Path(__file__).resolve().parent.parent

    files_updated, total_replacements = stamp_version(args.version, root)

    print(
        f"Done: {files_updated} file(s) updated, {total_replacements} replacement(s) made "
        f"({args.version})"
    )


if __name__ == "__main__":
    main()
