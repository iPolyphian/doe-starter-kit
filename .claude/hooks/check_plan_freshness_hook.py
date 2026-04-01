"""PostToolUse hook: Run plan freshness check when .claude/plans/*.md files are read.

Fires on every Read of a plan file. Checks version conflicts, dead file references,
CLAUDE.md drift, and plan age. Outputs warnings inline so they can't be missed.
"""
import json
import subprocess
import sys
from pathlib import Path


def main():
    event = json.load(sys.stdin)
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    path = tool_input.get("file_path", "")

    # Only trigger on Read of .claude/plans/*.md files
    if tool_name != "read" or ".claude/plans/" not in path or not path.endswith(".md"):
        print(json.dumps({}))
        return

    # Resolve to absolute path
    plan_path = Path(path)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path

    if not plan_path.exists():
        print(json.dumps({}))
        return

    # Run the freshness check script
    try:
        result = subprocess.run(
            ["python3", "execution/check_plan_freshness.py", str(plan_path)],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and output:
            print(json.dumps({"message": output}))
        else:
            print(json.dumps({}))
    except Exception:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
