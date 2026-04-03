#!/usr/bin/env python3
"""DOE Init Wizard -- conversational project scaffolding.

Usage:
    python3 doe_init.py --kit-dir /path/to/doe-starter-kit

Called by setup.sh. Asks what you're building, detects existing frameworks,
and outputs a config dict for subsequent installation steps.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ── Box-drawing helpers (W=60, matches /stand-up, /crack-on, /wrap) ──────

W = 60  # inner width (─ count between │ borders)


MAX_CONTENT = W - 2  # max chars before truncation (58)


def line(content=""):
    """Standard bordered content line. All rows use this -- never construct manually."""
    if len(content) > MAX_CONTENT:
        content = content[:MAX_CONTENT - 3] + "..."
    return f"│  {content}".ljust(W + 1) + "│"


def header(left, right=""):
    """Header row with optional right-aligned text."""
    if right:
        inner = f"{left}{right:>{W - 2 - len(left)}}"
    else:
        inner = left
    return line(inner)


def top():
    return "┌" + "─" * W + "┐"


def sep():
    return "├" + "─" * W + "┤"


def bot():
    return "└" + "─" * W + "┘"


def print_card(rows):
    """Print a complete bordered card."""
    print("\n".join(rows))
    print()


def ask(prompt, valid=None, default=None):
    """Prompt user for input. Validates against valid options if provided."""
    while True:
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if not raw and default is not None:
            return default
        if valid is None:
            return raw
        if raw in valid:
            return raw
        print(f"  Please enter one of: {', '.join(valid)}")


def ask_yn(prompt, default="n"):
    """Yes/no prompt. Returns bool."""
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    raw = ask(f"{prompt} {suffix} ", valid=["y", "n", "Y", "N", ""], default=default)
    return raw.lower() in ("y", "")  if default == "y" else raw.lower() == "y"


# ── Framework detection ──────────────────────────────────────────────────

# Detection patterns: check for marker files and content.
# Matches scaffold.json detect fields -- hardcoded here for Step 0,
# reads from scaffold.json once templates exist (Step 1+).
DETECT_PATTERNS = {
    "nextjs": {
        "files": ["package.json"],
        "package_contains": "next",
        "name": "Next.js",
    },
    "vite": {
        "files": ["package.json"],
        "package_contains": "vite",
        "name": "Vite/React",
    },
    "python": {
        "files": ["pyproject.toml", "requirements.txt"],
        "name": "Python",
    },
    "go": {
        "files": ["go.mod"],
        "name": "Go",
    },
    "flutter": {
        "files": ["pubspec.yaml"],
        "name": "Flutter",
    },
    "static": {
        "files": ["index.html"],
        "name": "Static HTML",
    },
}

# Project type → framework options (ordered, first is recommended)
FRAMEWORK_OPTIONS = {
    "web": [
        ("nextjs", "Next.js *", "Server rendering, Vercel-native"),
        ("vite", "Vite/React", "Lightweight SPA, fast dev server"),
        ("static", "Static HTML", "No framework, just files"),
    ],
    "api": [
        ("python", "Python *", "FastAPI/Flask, simple and fast"),
        ("go", "Go", "Compiled, concurrent, small binary"),
    ],
    "mobile": [
        ("flutter", "Flutter *", "Cross-platform, single codebase"),
    ],
    "cli": [
        ("python", "Python *", "Scripting, quick iteration"),
        ("go", "Go", "Compiled binary, no runtime"),
    ],
    "static_site": [
        ("static", "Static HTML *", "No framework, just files"),
    ],
}

PROJECT_TYPES = [
    ("web", "Web app"),
    ("api", "API / backend"),
    ("mobile", "Mobile app"),
    ("cli", "CLI tool / library"),
    ("static_site", "Static site / docs"),
]


# Framework → default project type (used when framework is auto-detected)
FRAMEWORK_PROJECT_TYPE = {
    "nextjs": "web",
    "vite": "web",
    "python": "api",
    "go": "api",
    "flutter": "mobile",
    "static": "web",
}


def detect_framework(project_dir):
    """Detect framework from existing project files. Returns (key, name) or (None, None)."""
    for key, pattern in DETECT_PATTERNS.items():
        for f in pattern["files"]:
            fpath = project_dir / f
            if fpath.exists():
                # If we need to check package.json content
                if "package_contains" in pattern and f == "package.json":
                    try:
                        text = fpath.read_text()
                        if pattern["package_contains"] not in text:
                            continue
                    except Exception:
                        continue
                return key, pattern["name"]
    return None, None


def detect_project_state(project_dir):
    """Detect what exists in the project directory."""
    has_git = (project_dir / ".git").exists()
    is_empty = not any(project_dir.iterdir()) if project_dir.exists() else True
    framework_key, framework_name = detect_framework(project_dir)
    return {
        "has_git": has_git,
        "is_empty": is_empty,
        "framework_key": framework_key,
        "framework_name": framework_name,
    }


# ── Wizard cards ─────────────────────────────────────────────────────────

def card_welcome(kit_version, project_dir, state):
    """Card 0: Welcome / detection."""
    rows = [top()]
    rows.append(header(f"DOE Starter Kit v{kit_version}"))
    rows.append(sep())
    rows.append(line(f"Project directory: {project_dir}"))

    # Detection summary
    detections = []
    if state["framework_name"]:
        detections.append(state["framework_name"])
    if state["has_git"]:
        detections.append(".git")

    if state["is_empty"]:
        rows.append(line("Detected: empty directory"))
        rows.append(line(""))
        rows.append(line("Setting up a new project from scratch."))
    elif detections:
        rows.append(line(f"Detected: {', '.join(detections)}"))
        rows.append(line(""))
        rows.append(line("Adding DOE alongside your existing code."))
        rows.append(line("Existing files will not be overwritten."))
    else:
        rows.append(line("Detected: existing files (no framework recognised)"))
        rows.append(line(""))
        rows.append(line("Adding DOE alongside your existing code."))
        rows.append(line("Existing files will not be overwritten."))

    rows.append(bot())
    print_card(rows)


def card_project_type():
    """Card 1: What are you building? Returns project type key."""
    rows = [top()]
    rows.append(line("What are you building?"))
    rows.append(sep())
    for i, (key, label) in enumerate(PROJECT_TYPES, 1):
        rows.append(line(f"[{i}] {label}"))
    rows.append(bot())
    print_card(rows)

    valid = [str(i) for i in range(1, len(PROJECT_TYPES) + 1)]
    choice = ask("> ", valid=valid)
    idx = int(choice) - 1
    return PROJECT_TYPES[idx][0]


def card_framework(project_type):
    """Card 2: Framework selection. Returns framework key."""
    options = FRAMEWORK_OPTIONS.get(project_type, FRAMEWORK_OPTIONS["web"])

    rows = [top()]
    rows.append(header("FRAMEWORK", "recommended: *"))
    rows.append(sep())
    for i, (key, label, desc) in enumerate(options, 1):
        # Truncate if needed to fit W
        text = f"[{i}] {label:15s} {desc}"
        if len(text) > W - 2:
            text = text[:W - 5] + "..."
        rows.append(line(text))
    rows.append(bot())
    print_card(rows)

    valid = [str(i) for i in range(1, len(options) + 1)]
    choice = ask("> ", valid=valid, default="1")
    idx = int(choice) - 1
    return options[idx][0]


def card_framework_confirm(framework_name):
    """Card 2 alt: Confirm auto-detected framework. Returns True to accept, False to override."""
    rows = [top()]
    rows.append(line("FRAMEWORK"))
    rows.append(sep())
    rows.append(line(f"Detected: {framework_name}"))
    rows.append(line(""))
    rows.append(line("Setting up DOE for this framework."))
    rows.append(line("Enter 'n' to choose a different framework."))
    rows.append(bot())
    print_card(rows)

    choice = ask("Accept? [Y/n] ", valid=["y", "n", "Y", "N", ""], default="y")
    return choice.lower() != "n"


def card_setup():
    """Card 3: Solo or team. Returns collaboration mode dict."""
    rows = [top()]
    rows.append(line("SETUP"))
    rows.append(sep())
    rows.append(line("Is this just you, or does a team contribute?"))
    rows.append(line(""))
    rows.append(line("[1] Just me"))
    rows.append(line("[2] Team"))
    rows.append(bot())
    print_card(rows)

    choice = ask("> ", valid=["1", "2"], default="1")

    if choice == "1":
        return {"mode": "solo", "github_users": [], "security_owner": ""}

    # Team follow-up
    print()
    users_raw = ask("  GitHub usernames (comma-separated): ")
    users = [u.strip() for u in users_raw.split(",") if u.strip()]
    if not users:
        users = ["you"]

    security_owner = ask(f"  Who owns security reviews? (default: {users[0]}): ",
                         default=users[0])

    return {"mode": "team", "github_users": users, "security_owner": security_owner}


def card_data():
    """Card 4: Data questions (sequential). Returns (has_database, has_personal_data)."""
    # First question: user data
    rows = [top()]
    rows.append(line("DATA"))
    rows.append(sep())
    rows.append(line("Will your app store user data?"))
    rows.append(line("(accounts, preferences, content they create)"))
    rows.append(bot())
    print_card(rows)

    has_database = ask_yn("> ")

    if not has_database:
        return False, False

    # Second question: personal data (only if user data = yes)
    rows = [top()]
    rows.append(line("COMPLIANCE"))
    rows.append(sep())
    rows.append(line("Will it handle personal data?"))
    rows.append(line("(names, emails, addresses, opinions, health)"))
    rows.append(line(""))
    rows.append(line("This adds GDPR compliance directives and a"))
    rows.append(line("DPIA template. Required before collecting"))
    rows.append(line("personal data."))
    rows.append(bot())
    print_card(rows)

    has_personal_data = ask_yn("> ")

    return True, has_personal_data


def card_confirmation(config):
    """Card 5: Confirmation before writing. Returns True to proceed."""
    framework_name = DETECT_PATTERNS.get(config["framework"], {}).get("name", config["framework"])
    collab = config["collaboration_mode"]
    parts = [framework_name]
    if config["project_type"]:
        parts.append(config["project_type"].replace("_", " "))
    parts.append(collab)
    if config["has_database"]:
        parts.append("database")

    summary = ", ".join(parts)
    if len(summary) > W - 16:
        summary = summary[:W - 19] + "..."

    # Compute file counts based on active layers
    layers = ["universal"]
    if config["project_type"] in ("web", "static_site"):
        layers.append("public_facing")
    if config["has_database"]:
        layers.append("data_handling")
    if config["has_personal_data"]:
        layers.append("regulated")

    rows = [top()]
    rows.append(header(f"DOE INIT -- {summary}"))
    rows.append(sep())
    rows.append(line("Will create:"))
    rows.append(line("  CLAUDE.md          Framework-aware config"))
    rows.append(line("  ROADMAP.md         Product roadmap"))
    rows.append(line("  directives/        Methodology + security"))
    rows.append(line("  execution/         Verification scripts"))
    rows.append(line("  .github/workflows/ CI + auto-rebase"))
    rows.append(line("  .githooks/         Pre-commit hooks"))
    rows.append(line("  .claude/settings   Hook configuration"))
    rows.append(line("  .claude/agents/    Adversarial review agents"))
    rows.append(line("  tasks/             todo.md + archive.md"))
    rows.append(line("  STATE.md           Session state tracker"))
    rows.append(line("  SECURITY.md        Security policy"))

    if config["has_database"]:
        rows.append(line("  .env.example       Database + app keys"))

    if config["has_personal_data"]:
        rows.append(line("  data-governance.md GDPR compliance"))
        rows.append(line("  legal-framework.md Legal requirements"))

    # "Will not touch" for existing projects
    if not config.get("is_empty", True):
        rows.append(line(""))
        rows.append(line("Will not touch:"))
        rows.append(line("  Your existing source code and config"))

    rows.append(sep())
    rows.append(line("Proceed? [Y/n]"))
    rows.append(bot())
    print_card(rows)

    choice = ask("", valid=["y", "n", "Y", "N", ""], default="y")
    return choice.lower() != "n"


def card_done(kit_version, project_dir, config, file_count):
    """Card 7: Done."""
    framework_name = DETECT_PATTERNS.get(config["framework"], {}).get("name", config["framework"])

    rows = [top()]
    rows.append(header(f"DONE -- DOE v{kit_version}"))
    rows.append(sep())
    rows.append(line(f"{file_count} files installed in {project_dir}"))
    rows.append(line(""))
    rows.append(line("Next steps:"))

    step_num = 1
    # Show framework init command for new projects
    if config.get("is_empty", True):
        init_cmd = get_init_command(config["framework"])
        if init_cmd:
            rows.append(line(f"  {step_num}. Run: {init_cmd}"))
            step_num += 1

    rows.append(line(f"  {step_num}. Run: claude"))
    step_num += 1
    rows.append(line(f"  {step_num}. Type: /stand-up"))

    if config["collaboration_mode"] == "solo":
        rows.append(line(""))
        rows.append(line("Upgrade to team mode anytime:"))
        kit_dir = config.get("kit_dir", "~/doe-starter-kit")
        rows.append(line(f"  bash {kit_dir}/setup.sh --team"))

    rows.append(bot())
    print_card(rows)


def get_init_command(framework):
    """Get the recommended framework init command."""
    commands = {
        "nextjs": "npx create-next-app .",
        "vite": "npm create vite@latest .",
        "python": "pip install fastapi uvicorn",
        "go": "go mod init",
        "flutter": "flutter create .",
    }
    return commands.get(framework)


# ── Version stamping ─────────────────────────────────────────────────────

def write_doe_version(project_dir, config, kit_version):
    """Write .doe-version file with config choices."""
    lines = [
        kit_version,
        config["framework"],
        config["collaboration_mode"],
    ]

    # Active layers
    if config["has_database"]:
        lines.append("data_handling")
    if config["has_personal_data"]:
        lines.append("regulated")

    version_file = project_dir / ".doe-version"
    version_file.write_text("\n".join(lines) + "\n")


# ── CLAUDE.md generator ─────────────────────────────────────────────────

def get_active_layers(config):
    """Determine which capability layers are active based on config."""
    layers = ["universal"]
    if config.get("project_type") in ("web", "static_site"):
        layers.append("public_facing")
    if config.get("has_database"):
        layers.append("data_handling")
    if config.get("has_personal_data"):
        layers.append("regulated")
    return layers


def generate_trigger_table(manifest, active_layers, framework):
    """Generate filtered trigger table from manifest triggers list.

    Includes a trigger only if:
    (a) its layer is in active_layers, AND
    (b) no 'frameworks' restriction, or framework is in the list.
    """
    lines = ["## Triggers"]
    for trigger in manifest.get("triggers", []):
        trigger_layer = trigger.get("layer", "universal")
        if trigger_layer not in active_layers:
            continue
        fw_restrict = trigger.get("frameworks")
        if fw_restrict and framework not in fw_restrict:
            continue
        situation = trigger["situation"]
        directive = trigger["directive"]
        lines.append(f"- {situation} -> `directives/{directive}`")
    return "\n".join(lines) + "\n"


def generate_claude_md(config, kit_dir):
    """Generate a complete CLAUDE.md from config + templates + manifest.

    Concatenation order:
    1. _base/claude_sections/00_header.md
    2. _base/claude_sections/10_methodology.md
    3. Framework claude_section.md
    4. _base/claude_sections/20_structure.md
    5. Layer claude_section.md files (public_facing, data_handling, regulated)
    6. _base/claude_sections/90_context.md
    7. Generated trigger table (filtered from manifest.json)
    """
    templates_dir = kit_dir / "templates"
    claude_sections = templates_dir / "_base" / "claude_sections"
    framework = config["framework"]
    active_layers = get_active_layers(config)

    parts = []

    # 1. Header
    parts.append((claude_sections / "00_header.md").read_text())

    # 2. Methodology
    parts.append((claude_sections / "10_methodology.md").read_text())

    # 3. Framework section
    fw_section = templates_dir / framework / "claude_section.md"
    if fw_section.exists():
        parts.append(fw_section.read_text())

    # 4. Directory structure
    parts.append((claude_sections / "20_structure.md").read_text())

    # 5. Layer sections (skip universal -- those are the base sections)
    layer_order = ["public_facing", "data_handling", "regulated"]
    for layer in layer_order:
        if layer in active_layers:
            layer_section = templates_dir / "_layers" / layer / "claude_section.md"
            if layer_section.exists():
                parts.append(layer_section.read_text())

    # 6. Context rules
    parts.append((claude_sections / "90_context.md").read_text())

    # 7. Trigger table (filtered)
    manifest_path = kit_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    parts.append(generate_trigger_table(manifest, active_layers, framework))

    return "\n".join(parts)


# ── Capability layer installer ───────────────────────────────────────────

def install_layer_files(config, kit_dir, project_dir):
    """Install DOE files based on config and manifest.

    Two destinations:
    - Per-project: directives, execution, hooks, root files -> project_dir
    - Global: commands -> ~/.claude/commands/, scripts -> ~/.claude/scripts/

    Shows INSTALLING progress card. Returns total file count.
    """
    manifest = json.loads((kit_dir / "manifest.json").read_text())
    active_layers = get_active_layers(config)
    templates_dir = kit_dir / "templates"
    total = 0

    def copy_to_project(src, rel_dest):
        """Copy src to project_dir/rel_dest. Skip if dest exists."""
        nonlocal total
        dst = project_dir / rel_dest
        if dst.exists() or not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        total += 1
        return True

    def copy_to_global(src, dst):
        """Copy src to global destination. Overwrites."""
        nonlocal total
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        total += 1
        return True

    rows = [top()]
    rows.append(line("INSTALLING"))
    rows.append(sep())

    # 1. CLAUDE.md (generated, always written)
    claude_md = generate_claude_md(config, kit_dir)
    (project_dir / "CLAUDE.md").write_text(claude_md)
    total += 1
    rows.append(line("CLAUDE.md .......................... done"))

    # 2. Directives (per active layer from manifest)
    dir_count = 0
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("directives", []):
            src = kit_dir / "directives" / name
            if copy_to_project(src, f"directives/{name}"):
                dir_count += 1
    # Directive directories (referenced as dirs in triggers)
    for dir_name in ["adversarial-review", "best-practices"]:
        dir_src = kit_dir / "directives" / dir_name
        if dir_src.is_dir():
            for f in dir_src.iterdir():
                if f.is_file():
                    if copy_to_project(f, f"directives/{dir_name}/{f.name}"):
                        dir_count += 1
    rows.append(line(f"directives/ ({dir_count} files) ........... done"))

    # 3. Execution scripts (per active layer)
    exec_count = 0
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("execution", []):
            src = kit_dir / "execution" / name
            if copy_to_project(src, f"execution/{name}"):
                exec_count += 1
    rows.append(line(f"execution/ ({exec_count} scripts) ........... done"))

    # 4. Git hooks (.githooks/)
    hook_count = 0
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("hooks", []):
            src = kit_dir / ".githooks" / name
            if copy_to_project(src, f".githooks/{name}"):
                hook_count += 1
    rows.append(line(f".githooks/ ({hook_count} hooks) ............. done"))

    # 5. Claude Code hooks (.claude/hooks/)
    claude_hooks_src = kit_dir / ".claude" / "hooks"
    ch_count = 0
    if claude_hooks_src.is_dir():
        for f in claude_hooks_src.iterdir():
            if f.is_file():
                if copy_to_project(f, f".claude/hooks/{f.name}"):
                    ch_count += 1
    if ch_count:
        rows.append(line(f".claude/hooks/ ({ch_count} hooks) .......... done"))

    # 5b. Claude Code agents (.claude/agents/)
    agents_src = kit_dir / ".claude" / "agents"
    agent_count = 0
    if agents_src.is_dir():
        for f in agents_src.iterdir():
            if f.is_file():
                if copy_to_project(f, f".claude/agents/{f.name}"):
                    agent_count += 1
    if agent_count:
        rows.append(line(f".claude/agents/ ({agent_count} agents) ....... done"))

    # 5c. Claude Code project settings (.claude/settings.json)
    settings_src = kit_dir / ".claude" / "settings.json"
    settings_dst = project_dir / ".claude" / "settings.json"
    if settings_src.exists() and not settings_dst.exists():
        settings_dst.parent.mkdir(parents=True, exist_ok=True)
        kit_settings = json.loads(settings_src.read_text())
        # Copy hooks config only — strip kit-specific keys like enabledPlugins
        project_settings = {"hooks": kit_settings.get("hooks", {})}
        settings_dst.write_text(json.dumps(project_settings, indent=2) + "\n")
        total += 1
        rows.append(line(".claude/settings.json .............. done"))

    # 6. Root-level security + layer files (SECURITY.md, etc.)
    root_count = 0
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("files", []):
            src = kit_dir / name
            if copy_to_project(src, name):
                root_count += 1
    if root_count:
        rows.append(line(f"security files ({root_count}) .............. done"))

    # 7. Base template files (STATE.md, learnings.md, ROADMAP.md, tasks/)
    base_dir = templates_dir / "_base"
    tmpl_count = 0
    for name in ["STATE.md", "learnings.md", "ROADMAP.md"]:
        src = base_dir / name
        if copy_to_project(src, name):
            tmpl_count += 1
    for name in ["todo.md", "archive.md"]:
        src = base_dir / "tasks" / name
        if copy_to_project(src, f"tasks/{name}"):
            tmpl_count += 1
    rows.append(line(f"starter files ({tmpl_count}) ............... done"))

    # 8. Framework-specific files (.gitignore, .env.example)
    fw_dir = templates_dir / config["framework"]
    fw_count = 0
    for name in [".gitignore", ".env.example"]:
        src = fw_dir / name
        if copy_to_project(src, name):
            fw_count += 1
    if fw_count:
        rows.append(line(f"framework config ({fw_count}) ............. done"))

    # 9. Global commands -> ~/.claude/commands/
    cmd_count = 0
    commands_dir = Path.home() / ".claude" / "commands"
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("commands", []):
            src = kit_dir / "global-commands" / name
            if copy_to_global(src, commands_dir / name):
                cmd_count += 1
    rows.append(line(f"~/.claude/commands/ ({cmd_count}) .......... done"))

    # 10. Global scripts -> ~/.claude/scripts/
    scripts_dir = Path.home() / ".claude" / "scripts"
    script_count = 0
    for name in manifest.get("global_scripts", []):
        # Check global-scripts/ first, fall back to execution/
        src = kit_dir / "global-scripts" / name
        if not src.exists():
            src = kit_dir / "execution" / name
        if copy_to_global(src, scripts_dir / name):
            script_count += 1
    if script_count:
        rows.append(line(f"~/.claude/scripts/ ({script_count}) .......... done"))

    rows.append(sep())
    rows.append(line(f"{total} files installed"))
    rows.append(bot())
    print_card(rows)

    return total


# ── CI + git + collaboration setup ──────────────────────────────────────

def setup_ci_git_collaboration(config, kit_dir, project_dir):
    """Step 4: CI workflows, git config, collaboration-aware file generation.

    - Copies .github/ files (doe-ci.yml, auto-rebase.yml, claude.yml,
      PR template, dependabot.yml) from manifest
    - Generates CODEOWNERS (solo = single user, team = security owner paths)
    - Generates CONTRIBUTING.md (team mode only)
    - Initialises git repo if not already one
    - Sets git config core.hooksPath .githooks
    - Prints branch protection instructions card
    """
    manifest = json.loads((kit_dir / "manifest.json").read_text())
    active_layers = get_active_layers(config)
    gh_count = 0
    extra_count = 0

    # ── Copy .github/ files from manifest (skip CODEOWNERS -- generated below)
    for layer_name in active_layers:
        layer_data = manifest["layers"].get(layer_name, {})
        for name in layer_data.get("github", []):
            if name == "CODEOWNERS":
                continue
            src = kit_dir / ".github" / name
            dst = project_dir / ".github" / name
            if not dst.exists() and src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                gh_count += 1

    # ── Generate CODEOWNERS
    codeowners_path = project_dir / ".github" / "CODEOWNERS"
    if not codeowners_path.exists():
        codeowners_path.parent.mkdir(parents=True, exist_ok=True)
        if config["collaboration_mode"] == "team":
            users = config["github_users"]
            sec = config["security_owner"]
            co_lines = [
                "# Default owners",
                "* " + " ".join(f"@{u}" for u in users),
                "",
                "# Security-sensitive paths require security owner review",
                f".githooks/ @{sec}",
                f".github/workflows/ @{sec}",
                f"CLAUDE.md @{sec}",
                f"directives/ @{sec}",
            ]
        else:
            co_lines = [
                "# Default owner",
                "* @you",
            ]
        codeowners_path.write_text("\n".join(co_lines) + "\n")
        gh_count += 1

    # ── Generate CONTRIBUTING.md (team only)
    if config["collaboration_mode"] == "team":
        contributing_path = project_dir / "CONTRIBUTING.md"
        if not contributing_path.exists():
            sec = config["security_owner"]
            contributing_path.write_text(
                "# Contributing\n\n"
                "## Getting Started\n\n"
                "1. Clone the repository\n"
                "2. Run `bash ~/doe-starter-kit/setup.sh`\n"
                "3. Run `claude` and type `/stand-up`\n\n"
                "## Branch Workflow\n\n"
                "- Feature branches from `main`\n"
                "- One commit per step, push after each\n"
                "- PR at feature completion (retro step)\n"
                "- CI must pass before merge\n\n"
                "## Security\n\n"
                f"Security-sensitive paths require review from @{sec}.\n"
                "See SECURITY.md for reporting.\n"
            )
            extra_count += 1

    # ── Initialise git if needed
    has_git = (project_dir / ".git").exists()
    if not has_git:
        result = subprocess.run(
            ["git", "init"], cwd=project_dir, capture_output=True,
        )
        if result.returncode != 0:
            print(f"  Warning: git init failed (exit {result.returncode})")
            has_git = False

    # ── Set git hooks path
    result = subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks"],
        cwd=project_dir, capture_output=True,
    )
    hooks_set = result.returncode == 0

    # ── Print setup card with branch protection instructions
    rows = [top()]
    rows.append(line("GIT + CI"))
    rows.append(sep())
    if not has_git:
        rows.append(line("Initialized git repository"))
    if hooks_set:
        rows.append(line("git hooks path -> .githooks/"))
    else:
        rows.append(line("Warning: could not set git hooks path"))
    rows.append(line(f".github/ -- {gh_count} files installed"))
    if extra_count:
        rows.append(line(f"CONTRIBUTING.md created"))
    rows.append(line(""))
    rows.append(line("Set branch protection on GitHub:"))
    rows.append(line("  Settings > Branches > Add rule"))
    rows.append(line("  Pattern: main"))
    rows.append(line("  [x] Require pull request before merging"))
    rows.append(line("  [x] Require status checks (CI Result)"))
    if config["collaboration_mode"] == "team":
        rows.append(line("  [x] Require code owner reviews"))
    rows.append(bot())
    print_card(rows)

    return gh_count + extra_count


# ── Kit version ──────────────────────────────────────────────────────────

def get_kit_version(kit_dir):
    """Read kit version from git tag or fallback."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=kit_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except Exception:
        pass
    return "0.0.0"


# ── Main wizard flow ─────────────────────────────────────────────────────

def run_wizard(kit_dir, project_dir):
    """Run the full init wizard. Returns config dict."""
    kit_version = get_kit_version(kit_dir)
    state = detect_project_state(project_dir)

    # Card 0: Welcome
    card_welcome(kit_version, project_dir, state)

    # Card 1: Project type (skip if framework auto-detected)
    project_type = None
    if state["framework_key"]:
        # Auto-detected -- infer project type from framework
        project_type = FRAMEWORK_PROJECT_TYPE.get(state["framework_key"], "web")
    else:
        project_type = card_project_type()

    # Card 2: Framework (skip if auto-detected, confirm otherwise)
    framework = None
    if state["framework_key"]:
        accepted = card_framework_confirm(state["framework_name"])
        if accepted:
            framework = state["framework_key"]
        else:
            # User wants to override -- always ask project type so they
            # aren't stuck with the inferred type (e.g. mobile only has Flutter)
            project_type = card_project_type()
            framework = card_framework(project_type)
    else:
        framework = card_framework(project_type)

    # Card 3: Solo/team
    collab = card_setup()

    # Card 4: Data questions
    has_database, has_personal_data = card_data()

    # Build config dict
    config = {
        "project_type": project_type,
        "framework": framework,
        "collaboration_mode": collab["mode"],
        "github_users": collab["github_users"],
        "security_owner": collab["security_owner"],
        "has_database": has_database,
        "has_personal_data": has_personal_data,
        "detected_framework": state["framework_key"],
        "project_dir": str(project_dir),
        "kit_dir": str(kit_dir),
        "is_empty": state["is_empty"],
    }

    # Card 5: Confirmation
    if not card_confirmation(config):
        print("Aborted. No files were written.")
        sys.exit(0)

    # Write .doe-version
    write_doe_version(project_dir, config, kit_version)

    # Save config for subsequent steps
    config_path = project_dir / ".tmp" / "doe-init-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    # Install files
    file_count = install_layer_files(config, kit_dir, project_dir)

    # CI + git + collaboration setup
    ci_count = setup_ci_git_collaboration(config, kit_dir, project_dir)

    # Card 7: Done
    card_done(kit_version, project_dir, config, file_count=file_count + ci_count)

    return config


def main():
    parser = argparse.ArgumentParser(description="DOE Init Wizard")
    parser.add_argument("--kit-dir", type=Path, default=None,
                        help="Path to doe-starter-kit directory")
    args = parser.parse_args()

    # Resolve kit directory
    if args.kit_dir:
        kit_dir = args.kit_dir.resolve()
    else:
        # Fallback: resolve from script location (execution/ -> kit root)
        kit_dir = Path(__file__).resolve().parent.parent

    if not kit_dir.exists():
        print(f"Error: kit directory not found: {kit_dir}")
        sys.exit(1)

    # Project directory is cwd
    project_dir = Path.cwd()

    run_wizard(kit_dir, project_dir)


if __name__ == "__main__":
    main()
