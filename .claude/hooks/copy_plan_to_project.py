"""Hook: Auto-copy plans written to ~/.claude/plans/ into the project's .claude/plans/ directory."""
import json, shutil, sys
from pathlib import Path

PROJECT_PLANS = Path(__file__).resolve().parent.parent / "plans"

def main():
    event = json.load(sys.stdin)
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    path = tool_input.get("file_path", "") or tool_input.get("path", "")

    home_plans = str(Path.home() / ".claude" / "plans")
    if tool_name in ("write", "edit") and path.startswith(home_plans) and path.endswith(".md"):
        src = Path(path)
        if src.exists():
            PROJECT_PLANS.mkdir(parents=True, exist_ok=True)
            dest = PROJECT_PLANS / src.name
            shutil.copy2(str(src), str(dest))
            print(json.dumps({
                "message": f"Auto-copied plan to project: .claude/plans/{src.name}"
            }))
        else:
            print(json.dumps({}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
