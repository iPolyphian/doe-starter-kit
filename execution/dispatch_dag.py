#!/usr/bin/env python3
"""DAG Executor for DOE parallel dispatch.

Parses Depends: and Owns: metadata from tasks/todo.md, builds a dependency
graph, validates it, and dispatches steps to parallel `claude -w` sessions
with mechanical collision prevention via pre-commit hooks.

Usage:
    python3 execution/dispatch_dag.py --help          # show help
    python3 execution/dispatch_dag.py --validate      # validate DAG (no execution)
    python3 execution/dispatch_dag.py --graph         # show wave graph
    python3 execution/dispatch_dag.py --dispatch      # dispatch next wave
    python3 execution/dispatch_dag.py --status        # show current progress
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = PROJECT_ROOT / "tasks" / "todo.md"
STATE_DIR = PROJECT_ROOT / ".tmp" / "dag"

# Shared files that no parallel agent may own
SHARED_FILES = {"CLAUDE.md", "STATE.md", "tasks/todo.md", "learnings.md"}

MAX_RETRIES = 3


# ── ANSI helpers ─────────────────────────────────────────────

def _fmt(text: str, code: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

def _green(t): return _fmt(t, "32")
def _yellow(t): return _fmt(t, "33")
def _red(t): return _fmt(t, "31")
def _bold(t): return _fmt(t, "1")
def _dim(t): return _fmt(t, "2")
def _cyan(t): return _fmt(t, "36")


# ── Parsing ──────────────────────────────────────────────────

_STEP_RE = re.compile(r"^(\d+)\.\s+\[([ x])\]\s+(.+?)(?:\s*->\s*(v[\d.]+))?$")
_DEPENDS_RE = re.compile(r"^\s+Depends:\s*(.+)$", re.IGNORECASE)
_OWNS_RE = re.compile(r"^\s+Owns:\s*(.+)$", re.IGNORECASE)
_CONTRACT_RE = re.compile(r"^\s+Contract:", re.IGNORECASE)
_VERIFY_RE = re.compile(r"Verify:\s+(run:\s+.+|file:\s+.+|html:\s+.+)")
_FEATURE_RE = re.compile(r"^###\s+(.+?)(?:\s+\[(?:APP|INFRA)\])?\s+\(v[\d.x]+\)")
_CURRENT_RE = re.compile(r"^##\s+Current")


class Step:
    """A single step in the dependency graph."""

    def __init__(self, number: int, done: bool, description: str, version: str = ""):
        self.number = number
        self.done = done
        self.description = description
        self.version = version
        self.depends_raw = ""
        self.depends_on: list[int] = []
        self.owns: list[str] = []
        self.contracts: list[str] = []

    def __repr__(self):
        status = "x" if self.done else " "
        return f"Step({self.number}, [{status}], {self.description[:40]})"


def parse_depends(raw: str) -> list[int]:
    """Parse a Depends: line into a list of step numbers.

    Supports formats:
        Depends: Step 0
        Depends: Steps 0-5
        Depends: Steps 0, 2, 4
        Depends: Steps 0-3, 5
        Depends: none
        Depends: all
    """
    raw = raw.strip().lower()
    if raw in ("none", ""):
        return []
    if raw == "all":
        return [-1]  # sentinel: depends on everything

    numbers = set()
    # Find ranges like "0-5"
    for m in re.finditer(r"(\d+)\s*-\s*(\d+)", raw):
        start, end = int(m.group(1)), int(m.group(2))
        numbers.update(range(start, end + 1))
    # Find standalone numbers (not part of a range)
    cleaned = re.sub(r"\d+\s*-\s*\d+", "", raw)
    for m in re.finditer(r"(\d+)", cleaned):
        numbers.add(int(m.group(1)))

    return sorted(numbers)


def parse_owns(raw: str) -> list[str]:
    """Parse an Owns: line into a list of file paths."""
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_current_feature() -> tuple[str, list[Step]]:
    """Parse the ## Current section of todo.md for steps with metadata."""
    if not TASKS_FILE.exists():
        print(_red("Error: tasks/todo.md not found"), file=sys.stderr)
        sys.exit(1)

    text = TASKS_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find ## Current section
    in_current = False
    feature_name = ""
    steps: list[Step] = []
    current_step: Step | None = None

    for line in lines:
        stripped = line.strip()

        if _CURRENT_RE.match(stripped):
            in_current = True
            continue

        if in_current and stripped.startswith("## ") and not _CURRENT_RE.match(stripped):
            break  # left ## Current

        if not in_current:
            continue

        # Feature heading
        fm = _FEATURE_RE.match(stripped)
        if fm:
            feature_name = fm.group(1).strip()
            continue

        # Step line
        sm = _STEP_RE.match(stripped)
        if sm:
            if current_step is not None:
                steps.append(current_step)
            num = int(sm.group(1))
            done = sm.group(2) == "x"
            desc = sm.group(3).strip()
            ver = sm.group(4) or ""
            current_step = Step(num, done, desc, ver)
            continue

        # Metadata lines (only if we have a current step)
        if current_step is not None:
            dm = _DEPENDS_RE.match(line)
            if dm:
                current_step.depends_raw = dm.group(1).strip()
                current_step.depends_on = parse_depends(dm.group(1))
                continue

            om = _OWNS_RE.match(line)
            if om:
                current_step.owns = parse_owns(om.group(1))
                continue

            vm = _VERIFY_RE.search(line)
            if vm:
                current_step.contracts.append(vm.group(1))
                continue

    if current_step is not None:
        steps.append(current_step)

    # Resolve "all" dependency sentinel
    all_nums = {s.number for s in steps}
    for s in steps:
        if s.depends_on == [-1]:
            s.depends_on = sorted(all_nums - {s.number})

    return feature_name, steps


# ── Validation ───────────────────────────────────────────────

def validate_dag(steps: list[Step]) -> list[str]:
    """Validate the dependency graph. Returns a list of issues (empty = valid)."""
    issues = []
    step_map = {s.number: s for s in steps}
    all_nums = set(step_map.keys())

    # 1. Check for references to non-existent steps
    for s in steps:
        for dep in s.depends_on:
            if dep not in all_nums:
                issues.append(f"Step {s.number} depends on non-existent Step {dep}")

    # 2. Check for cycles using DFS
    visited = set()
    rec_stack = set()

    def has_cycle(n: int) -> bool:
        visited.add(n)
        rec_stack.add(n)
        for dep in step_map.get(n, Step(n, False, "")).depends_on:
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in rec_stack:
                issues.append(f"Cycle detected involving Step {n} -> Step {dep}")
                return True
        rec_stack.discard(n)
        return False

    for s in steps:
        if s.number not in visited:
            has_cycle(s.number)

    # 3. Check for Owns: overlap between potentially parallel steps
    waves = compute_waves(steps)
    for wave_num, wave_steps in enumerate(waves):
        if len(wave_steps) < 2:
            continue
        # Check all pairs in this wave for file overlap
        for i, s1 in enumerate(wave_steps):
            for s2 in wave_steps[i + 1:]:
                overlap = set(s1.owns) & set(s2.owns)
                if overlap:
                    files = ", ".join(sorted(overlap))
                    issues.append(
                        f"Owns overlap in Wave {wave_num}: "
                        f"Step {s1.number} and Step {s2.number} both own: {files}"
                    )

    # 4. Check no incomplete step in a multi-step wave owns shared files
    # Completed steps and solo-wave steps are exempt (they ran/will run alone)
    for wave_num, wave_steps in enumerate(waves):
        if len(wave_steps) < 2:
            continue
        for s in wave_steps:
            if s.done:
                continue
            shared_owned = set(s.owns) & SHARED_FILES
            if shared_owned:
                files = ", ".join(sorted(shared_owned))
                issues.append(
                    f"Step {s.number} (Wave {wave_num}) owns shared file(s): {files} "
                    f"-- shared files are off-limits to parallel agents"
                )

    return issues


def compute_waves(steps: list[Step]) -> list[list[Step]]:
    """Compute parallel waves from the dependency graph.

    A wave is a set of steps whose dependencies are ALL satisfied
    (completed or in a prior wave). Steps within a wave can run in parallel.
    """
    step_map = {s.number: s for s in steps}
    remaining = {s.number for s in steps if not s.done}
    completed = {s.number for s in steps if s.done}
    waves = []

    while remaining:
        # Find steps whose dependencies are all in completed
        ready = set()
        for num in remaining:
            s = step_map[num]
            deps = set(s.depends_on)
            if deps <= completed:
                ready.add(num)

        if not ready:
            # Deadlock -- remaining steps have unsatisfiable dependencies
            stuck = sorted(remaining)
            stuck_steps = [step_map[n] for n in stuck]
            waves.append(stuck_steps)  # report them as a "stuck" wave
            break

        wave = sorted(ready)
        waves.append([step_map[n] for n in wave])
        completed.update(ready)
        remaining -= ready

    return waves


# ── Graph display ────────────────────────────────────────────

def show_graph(feature_name: str, steps: list[Step]):
    """Display the dependency graph as waves."""
    waves = compute_waves(steps)
    done_count = sum(1 for s in steps if s.done)
    total = len(steps)

    print()
    print(_bold(f"  DAG: {feature_name}"))
    print(_dim(f"  {done_count}/{total} steps complete"))
    print()

    # Show completed steps first
    completed = [s for s in steps if s.done]
    if completed:
        print(_dim("  Completed:"))
        for s in completed:
            print(_dim(f"    [{s.number}] {s.description[:50]}"))
        print()

    # Show each wave
    for i, wave in enumerate(waves):
        parallel_tag = _cyan(" (parallel)") if len(wave) > 1 else ""
        print(f"  Wave {i}{parallel_tag}:")
        for s in wave:
            deps_str = ""
            if s.depends_on:
                deps_str = _dim(f" <- [{', '.join(str(d) for d in s.depends_on)}]")
            owns_str = ""
            if s.owns:
                short_owns = [Path(o).name for o in s.owns[:3]]
                if len(s.owns) > 3:
                    short_owns.append(f"+{len(s.owns) - 3}")
                owns_str = _dim(f" owns: {', '.join(short_owns)}")

            status = _green("[x]") if s.done else "[ ]"
            print(f"    {status} Step {s.number}: {s.description[:40]}{deps_str}{owns_str}")
        print()


# ── Pre-commit hook generation ───────────────────────────────

_HOOK_TEMPLATE = textwrap.dedent("""\
    #!/bin/bash
    # Auto-generated pre-commit hook for DAG executor.
    # Enforces file ownership: only files in the Owns: list may be modified.
    # This is mechanical enforcement -- the agent cannot bypass it.

    ALLOWED_FILES=({allowed_files})

    changed=$(git diff --cached --name-only)

    violations=""
    for f in $changed; do
        allowed=false
        for a in "${{ALLOWED_FILES[@]}}"; do
            if [[ "$f" == "$a" ]]; then
                allowed=true
                break
            fi
        done
        if [ "$allowed" = false ]; then
            violations="$violations\\n  $f"
        fi
    done

    if [ -n "$violations" ]; then
        echo "DAG OWNERSHIP VIOLATION"
        echo "This worktree is restricted to the following files:"
        for a in "${{ALLOWED_FILES[@]}}"; do
            echo "  $a"
        done
        echo ""
        echo "Attempted to commit changes to files outside the Owns: list:"
        echo -e "$violations"
        echo ""
        echo "If you need these files, report NEEDS_CONTEXT to the executor."
        exit 1
    fi
""")


def generate_pre_commit_hook(step: Step) -> str:
    """Generate a pre-commit hook that enforces the step's Owns: list."""
    allowed = " ".join(f'"{f}"' for f in step.owns)
    return _HOOK_TEMPLATE.format(allowed_files=allowed)


# ── Dispatch ─────────────────────────────────────────────────

def ensure_state_dir():
    """Create .tmp/dag/ for tracking dispatch state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_step_state(step_num: int) -> dict:
    """Read state for a specific step."""
    state_file = STATE_DIR / f"step-{step_num}.json"
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {"step": step_num, "status": "pending", "retries": 0, "worktree": None}


def save_step_state(step_num: int, state: dict):
    """Save state for a specific step."""
    ensure_state_dir()
    state_file = STATE_DIR / f"step-{step_num}.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def create_worktree(step: Step, feature_name: str) -> str:
    """Create a git worktree for a step. Returns the worktree path."""
    safe_name = re.sub(r"[^a-z0-9-]", "-", feature_name.lower())[:30]
    branch_name = f"feature/{safe_name}/step-{step.number}"
    worktree_path = str(PROJECT_ROOT / ".tmp" / "worktrees" / f"step-{step.number}")

    # Clean up existing worktree if present
    if Path(worktree_path).exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            cwd=PROJECT_ROOT, capture_output=True,
        )

    # Get current branch
    current = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    ).stdout.strip()

    # Create worktree with new branch from current
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, worktree_path, current],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        # Branch may already exist -- try without -b
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            capture_output=True, cwd=PROJECT_ROOT,
        )
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, worktree_path, current],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            print(_red(f"Failed to create worktree: {result.stderr}"), file=sys.stderr)
            return ""

    # Install pre-commit hook in worktree
    hooks_dir = Path(worktree_path) / ".git" / "hooks"
    # Worktree .git is a file pointing to the main repo -- find actual hooks location
    git_dir_file = Path(worktree_path) / ".git"
    if git_dir_file.is_file():
        # .git is a file with "gitdir: path/to/worktree/git/dir"
        gitdir = git_dir_file.read_text().strip().replace("gitdir: ", "")
        hooks_dir = Path(gitdir) / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_content = generate_pre_commit_hook(step)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(hook_content, encoding="utf-8")
    hook_path.chmod(0o755)

    return worktree_path


def dispatch_step(step: Step, feature_name: str, plan_file: str = "") -> dict:
    """Dispatch a single step to a `claude -w` session.

    Returns the updated step state dict.
    """
    state = get_step_state(step.number)

    if state["status"] == "complete":
        return state

    # Create worktree
    worktree_path = create_worktree(step, feature_name)
    if not worktree_path:
        state["status"] = "failed"
        state["error"] = "worktree creation failed"
        save_step_state(step.number, state)
        return state

    state["worktree"] = worktree_path
    state["status"] = "running"
    save_step_state(step.number, state)

    # Build the prompt for the agent
    contracts_text = "\n".join(f"  - {c}" for c in step.contracts)
    owns_text = ", ".join(step.owns) if step.owns else "(no files listed)"

    prompt = textwrap.dedent(f"""\
        You are executing Step {step.number} of the {feature_name} feature.

        TASK: {step.description}

        FILES YOU OWN (only edit these): {owns_text}

        CONTRACTS (all must pass):
        {contracts_text}

        RULES:
        - Only edit files in your Owns: list. The pre-commit hook will reject other files.
        - Shared files (CLAUDE.md, STATE.md, todo.md, learnings.md) are off-limits.
        - Report STATUS: DONE when contracts pass.
        - Report STATUS: NEEDS_CONTEXT if you need a file you don't own.
        - Report STATUS: BLOCKED if you hit an unresolvable issue.
        - Maximum {MAX_RETRIES} retry attempts if contracts fail.
    """)

    if plan_file and Path(plan_file).exists():
        prompt += f"\nPlan reference: {plan_file}\n"

    # Dispatch using claude -w (worktree mode)
    print(f"  Dispatching Step {step.number} to worktree: {worktree_path}")
    print(f"  Branch: feature/{re.sub(r'[^a-z0-9-]', '-', feature_name.lower())[:30]}/step-{step.number}")

    try:
        result = subprocess.run(
            ["claude", "-w", worktree_path, "--print", "--prompt", prompt],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
            timeout=600,  # 10 minute timeout per step
        )

        if result.returncode == 0:
            state["status"] = "complete"
            state["output"] = result.stdout[-2000:]  # keep last 2000 chars
        else:
            state["retries"] = state.get("retries", 0) + 1
            if state["retries"] >= MAX_RETRIES:
                state["status"] = "failed"
                state["error"] = f"Failed after {MAX_RETRIES} retries"
            else:
                state["status"] = "retry"
                state["error"] = result.stderr[-500:]
    except subprocess.TimeoutExpired:
        state["status"] = "timeout"
        state["error"] = "Step timed out after 600s"
    except FileNotFoundError:
        state["status"] = "failed"
        state["error"] = "claude CLI not found -- install Claude Code first"

    save_step_state(step.number, state)
    return state


def dispatch_wave(wave: list[Step], feature_name: str, plan_file: str = ""):
    """Dispatch all steps in a wave (parallel)."""
    import concurrent.futures

    print(_bold(f"\n  Dispatching wave ({len(wave)} steps in parallel)..."))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(wave)) as executor:
        futures = {
            executor.submit(dispatch_step, step, feature_name, plan_file): step
            for step in wave
        }

        for future in concurrent.futures.as_completed(futures):
            step = futures[future]
            try:
                state = future.result()
                status_str = state["status"]
                if status_str == "complete":
                    print(f"    {_green('DONE')} Step {step.number}: {step.description[:40]}")
                elif status_str == "retry":
                    print(f"    {_yellow('RETRY')} Step {step.number}: {state.get('error', '')[:60]}")
                else:
                    print(f"    {_red(status_str.upper())} Step {step.number}: {state.get('error', '')[:60]}")
            except Exception as e:
                print(f"    {_red('ERROR')} Step {step.number}: {e}")


# ── Merge ────────────────────────────────────────────────────

def merge_wave(wave: list[Step], feature_name: str) -> bool:
    """Merge all completed step branches back into the feature branch.

    Returns True if merge succeeded, False if conflicts detected.
    """
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    ).stdout.strip()

    safe_name = re.sub(r"[^a-z0-9-]", "-", feature_name.lower())[:30]
    success = True

    for step in wave:
        state = get_step_state(step.number)
        if state["status"] != "complete":
            continue

        branch_name = f"feature/{safe_name}/step-{step.number}"

        # Merge step branch into feature branch
        result = subprocess.run(
            ["git", "merge", "--no-ff", "-m",
             f"Merge Step {step.number}: {step.description[:50]}",
             branch_name],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )

        if result.returncode != 0:
            print(_red(f"  Merge conflict for Step {step.number}: {result.stderr[:200]}"))
            # Abort the merge
            subprocess.run(
                ["git", "merge", "--abort"],
                capture_output=True, cwd=PROJECT_ROOT,
            )
            success = False
        else:
            print(f"  {_green('Merged')} Step {step.number}")

    return success


def run_integration_contracts(steps: list[Step]) -> list[str]:
    """Run integration contracts after wave merge.

    Integration contracts verify cross-step interactions on the merged result.
    Returns list of failures.
    """
    failures = []

    # Run each completed step's contracts against the merged codebase
    for step in steps:
        if not step.done and get_step_state(step.number).get("status") != "complete":
            continue

        for contract in step.contracts:
            if contract.startswith("run:"):
                cmd = contract[4:].strip()
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    cwd=PROJECT_ROOT, timeout=30,
                )
                if result.returncode != 0:
                    failures.append(
                        f"Step {step.number} integration contract failed: {cmd[:60]}"
                    )
            elif contract.startswith("file:"):
                parts = contract[5:].strip()
                if "contains" in parts:
                    filepath, _, needle = parts.partition("contains")
                    filepath = filepath.strip()
                    needle = needle.strip()
                    full_path = PROJECT_ROOT / filepath
                    if not full_path.exists():
                        failures.append(f"Step {step.number}: {filepath} not found")
                    elif needle not in full_path.read_text(encoding="utf-8"):
                        failures.append(f"Step {step.number}: {filepath} missing '{needle}'")
                elif "exists" in parts:
                    filepath = parts.replace("exists", "").strip()
                    if not (PROJECT_ROOT / filepath).exists():
                        failures.append(f"Step {step.number}: {filepath} not found")

    return failures


# ── Cleanup ──────────────────────────────────────────────────

def cleanup_worktrees():
    """Remove all DAG worktrees and state."""
    worktrees_dir = PROJECT_ROOT / ".tmp" / "worktrees"
    if worktrees_dir.exists():
        # Remove each worktree properly
        for wt in worktrees_dir.iterdir():
            if wt.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(wt)],
                    capture_output=True, cwd=PROJECT_ROOT,
                )
        # Clean up any remaining files
        if worktrees_dir.exists():
            shutil.rmtree(worktrees_dir, ignore_errors=True)

    if STATE_DIR.exists():
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    # Prune worktree references
    subprocess.run(
        ["git", "worktree", "prune"],
        capture_output=True, cwd=PROJECT_ROOT,
    )

    print(_green("  Cleaned up worktrees and DAG state"))


# ── Status display ───────────────────────────────────────────

def show_status(feature_name: str, steps: list[Step]):
    """Show current dispatch status."""
    print()
    print(_bold(f"  DAG Status: {feature_name}"))
    print()

    for s in steps:
        state = get_step_state(s.number)
        status = state["status"]

        if s.done:
            icon = _green("[x]")
            status_str = _green("complete")
        elif status == "complete":
            icon = _green("[x]")
            status_str = _green("complete (pending merge)")
        elif status == "running":
            icon = _yellow("[~]")
            status_str = _yellow("running")
        elif status == "retry":
            icon = _yellow("[!]")
            retries = state.get("retries", 0)
            status_str = _yellow(f"retry {retries}/{MAX_RETRIES}")
        elif status == "failed":
            icon = _red("[X]")
            status_str = _red(f"failed: {state.get('error', '')[:40]}")
        elif status == "timeout":
            icon = _red("[T]")
            status_str = _red("timed out")
        else:
            icon = "[ ]"
            status_str = _dim("pending")

        print(f"  {icon} Step {s.number}: {s.description[:35]}  {status_str}")

    print()


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DAG executor for DOE parallel dispatch. "
                    "Parses Depends:/Owns: metadata from todo.md, "
                    "validates the dependency graph, and dispatches "
                    "steps to parallel claude -w sessions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate the DAG (check for cycles, Owns overlap, shared file conflicts)",
    )
    parser.add_argument(
        "--graph", action="store_true",
        help="Show the dependency graph as parallel waves",
    )
    parser.add_argument(
        "--dispatch", action="store_true",
        help="Dispatch the next wave of steps",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current dispatch progress",
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Remove all worktrees and DAG state",
    )
    parser.add_argument(
        "--plan", metavar="FILE",
        help="Path to the plan file for context",
    )
    args = parser.parse_args()

    if not any([args.validate, args.graph, args.dispatch, args.status, args.cleanup]):
        parser.print_help()
        return

    if args.cleanup:
        cleanup_worktrees()
        return

    feature_name, steps = parse_current_feature()

    if not steps:
        print(_yellow("No steps found in ## Current section of todo.md"))
        return

    if args.validate:
        issues = validate_dag(steps)
        print()
        print(_bold(f"  Validating DAG: {feature_name}"))
        print(f"  Steps: {len(steps)}")
        print(f"  Completed: {sum(1 for s in steps if s.done)}")
        print()

        # Show Owns summary
        for s in steps:
            owns_str = ", ".join(s.owns) if s.owns else _dim("(none)")
            deps_str = ", ".join(str(d) for d in s.depends_on) if s.depends_on else _dim("none")
            print(f"  Step {s.number}: Depends: [{deps_str}]  Owns: [{owns_str}]")

        print()

        if issues:
            print(_red(f"  {len(issues)} validation issue(s):"))
            for issue in issues:
                print(f"    {_red('!')} {issue}")
            sys.exit(1)
        else:
            print(_green("  Validation passed -- no cycles, no Owns overlap, no shared file conflicts"))

    elif args.graph:
        show_graph(feature_name, steps)

    elif args.dispatch:
        # Validate first
        issues = validate_dag(steps)
        if issues:
            print(_red("  DAG validation failed -- fix issues before dispatching:"))
            for issue in issues:
                print(f"    {_red('!')} {issue}")
            sys.exit(1)

        waves = compute_waves(steps)
        if not waves:
            print(_green("  All steps complete -- nothing to dispatch"))
            return

        # Dispatch first wave
        wave = waves[0]
        plan_file = args.plan or ""

        dispatch_wave(wave, feature_name, plan_file)

        # Check results
        all_complete = all(
            get_step_state(s.number)["status"] == "complete"
            for s in wave
        )

        if all_complete and len(wave) > 1:
            print(_bold("\n  Wave complete -- merging..."))
            success = merge_wave(wave, feature_name)

            if success:
                print(_bold("\n  Running integration contracts..."))
                failures = run_integration_contracts(steps)
                if failures:
                    print(_red(f"\n  {len(failures)} integration contract(s) failed:"))
                    for f in failures:
                        print(f"    {_red('!')} {f}")
                else:
                    print(_green("\n  Integration contracts passed"))
            else:
                print(_red("\n  Merge failed -- resolve conflicts manually"))
        elif all_complete:
            print(_green("\n  Step complete"))
        else:
            print(_yellow("\n  Some steps need attention -- run --status for details"))

    elif args.status:
        show_status(feature_name, steps)


if __name__ == "__main__":
    main()
