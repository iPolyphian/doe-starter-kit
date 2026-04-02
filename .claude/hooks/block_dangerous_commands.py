"""Hook: Block dangerous bash commands."""
import json, sys

DANGEROUS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "DROP TABLE", "DROP DATABASE", "TRUNCATE",
    "DISABLE ROW LEVEL SECURITY",
    "supabase db reset",
    "deleteMany()", ".delete()",
    "emptyBucket",
    ":(){ :|:& };:", "fork bomb",
    "> /dev/sda", "mkfs.", "dd if=",
    # gh pr merge — moved to confirm_pr_merge.py (user can approve per-merge)
    "SKIP_REVIEW_GATE",  # Review gate bypass must be set by the human, not the AI
    "SKIP_CONTRACT_CHECK",  # Contract check bypass must be set by the human
    "SKIP_SIGNOFF_CHECK",  # Sign-off check bypass must be set by the human
]

def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "")
    for pattern in DANGEROUS:
        if pattern.lower() in command.lower():
            print(json.dumps({
                "decision": "block",
                "reason": f"GUARDRAIL: Blocked dangerous command containing '{pattern}'."
            }))
            return
    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
