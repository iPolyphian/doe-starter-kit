#!/usr/bin/env python3
"""Run quality gate checks and write checkpoint markers.

Usage:
  python3 execution/quality_gate.py --checkpoint   # Mid-feature (every 4 steps)
  python3 execution/quality_gate.py --pre-retro    # Before retro step

The pre-commit hook blocks commits when these gates haven't been run:
  - Checkpoint: when 4+ steps completed since last checkpoint
  - Pre-retro: when all steps in ## Current are [x]

Markers are written to .tmp/ and include the feature name so they
auto-invalidate when the feature changes.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

CHECKPOINT_SCENARIOS = [
    "cross_reference_consistency",
    "directive_schema",
    "agent_definition_integrity",
]

PRE_RETRO_SCENARIOS = [
    "router_coverage",
    "rule_completeness",
    "scale_consistency",
    "dag_validation",
    "directive_schema",
    "cross_reference_consistency",
    "agent_definition_integrity",
    "plan_vs_actual",
    "invariant_regression",
    "completed_feature_hygiene",
]


def get_current_feature():
    """Return the feature name from ## Current, or empty string."""
    text = Path("tasks/todo.md").read_text(encoding="utf-8")
    in_current = False
    for line in text.splitlines():
        if line.strip().startswith("## Current"):
            in_current = True
            continue
        if in_current and line.strip().startswith("### "):
            # Extract name before [APP/INFRA] tag
            name = line.strip()[4:]
            return re.sub(r"\s*\[.*", "", name).strip()
        if in_current and line.strip().startswith("## "):
            break
    return ""


def count_completed_steps():
    """Count [x] steps in ## Current."""
    text = Path("tasks/todo.md").read_text(encoding="utf-8")
    in_current = False
    count = 0
    for line in text.splitlines():
        if line.strip().startswith("## Current"):
            in_current = True
            continue
        if in_current and line.strip().startswith("## "):
            break
        if in_current and re.match(r"\s*\d+[a-d]?\.\s+\[x\]", line):
            count += 1
    return count


def run_scenarios(scenarios):
    """Run methodology test scenarios. Returns True if all pass."""
    args = ["python3", "execution/test_methodology.py"]
    for s in scenarios:
        args.extend(["--scenario", s])
    result = subprocess.run(args, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run quality gate checks")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--checkpoint", action="store_true",
                       help="Mid-feature checkpoint (every 4 steps)")
    group.add_argument("--pre-retro", action="store_true",
                       help="Pre-retro gate (before retro step)")
    args = parser.parse_args()

    feature = get_current_feature()
    if not feature:
        print("No active feature in ## Current.")
        sys.exit(1)

    if args.checkpoint:
        scenarios = CHECKPOINT_SCENARIOS
        marker_path = Path(".tmp/.quality-gate")
    else:
        scenarios = PRE_RETRO_SCENARIOS
        marker_path = Path(".tmp/.pre-retro-gate")

    print(f"Quality gate for: {feature}")
    print(f"Running {len(scenarios)} scenarios...\n")

    if not run_scenarios(scenarios):
        print("\nQuality gate FAILED. Fix issues before continuing.")
        sys.exit(1)

    # Write marker: feature_name:step_count
    step_count = count_completed_steps()
    Path(".tmp").mkdir(exist_ok=True)
    marker_path.write_text(f"{feature}:{step_count}")
    print(f"\nQuality gate passed. Marker: {marker_path} = {feature}:{step_count}")


if __name__ == "__main__":
    main()
