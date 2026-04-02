"""Hook: Force a confirmation step before any PR merge.

Claude CAN merge PRs, but the hook forces a two-step flow:
1. First attempt hits the block -- Claude must stop and ask the user
2. User confirms -- Claude reruns with ALLOW_MERGE=1

This means Claude can never merge as a silent side-effect of a larger
task. The block forces the conversation to happen.
"""
import json
import sys


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "")

    if "gh pr merge" not in command:
        print(json.dumps({"decision": "allow"}))
        return

    if "ALLOW_MERGE=1" in command:
        print(json.dumps({"decision": "allow"}))
        return

    print(json.dumps({
        "decision": "block",
        "reason": (
            "GUARDRAIL: PR merge requires user confirmation. "
            "Show a bordered card with PR details (number, title, branch, "
            "checks) and ask the user: 'Shall I merge this?' "
            "Only proceed with ALLOW_MERGE=1 after they confirm."
        ),
    }))


if __name__ == "__main__":
    main()
