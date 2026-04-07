#!/usr/bin/env python3
"""DOE Init Wizard -- conversational project scaffolding.

Usage:
    python3 doe_init.py --kit-dir /path/to/doe-starter-kit

Called by setup.sh. Asks what you're building, detects existing frameworks,
and outputs a config dict for subsequent installation steps.
"""

import argparse
import json
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


# ── Unified Framework Registry ───────────────────────────────────────────
#
# Single source of truth for all frameworks. Replaces the former separate
# DETECT_PATTERNS, FRAMEWORK_OPTIONS, FRAMEWORK_PROJECT_TYPE, and
# get_init_command() dicts. Tier 1 = full template dir. Tier 2 = _generic.
#
# Keys: name (display), desc (one-liner), types (project types this applies
# to), tier (1=full template, 2=generic), template (template dir name),
# detect (optional, marker files for auto-detection), init_cmd (optional,
# framework init command), recommended_for (optional, types where this is
# the default recommendation).

FRAMEWORKS = {
    # ── Tier 1: Full template support (existing 6) ──────────────────────
    "nextjs": {
        "name": "Next.js", "desc": "Server rendering, Vercel-native",
        "types": ["web", "api"], "tier": 1, "template": "nextjs",
        "detect": {"files": ["package.json"], "package_contains": "next"},
        "init_cmd": "npx create-next-app .",
        "recommended_for": ["web"],
    },
    "vite": {
        "name": "Vite/React", "desc": "Lightweight SPA, fast dev server",
        "types": ["web"], "tier": 1, "template": "vite",
        "detect": {"files": ["package.json"], "package_contains": "vite"},
        "init_cmd": "npm create vite@latest .",
    },
    "static": {
        "name": "Static HTML", "desc": "No framework, just files",
        "types": ["web", "static_site"], "tier": 1, "template": "static",
        "detect": {"files": ["index.html"]},
        "recommended_for": ["static_site"],
    },
    "python": {
        "name": "Python", "desc": "FastAPI/Flask, simple and fast",
        "types": ["api", "cli"], "tier": 1, "template": "python",
        "detect": {"files": ["pyproject.toml", "requirements.txt"]},
        "init_cmd": "pip install fastapi uvicorn",
        "recommended_for": ["api", "cli"],
    },
    "go": {
        "name": "Go", "desc": "Compiled, concurrent, small binary",
        "types": ["api", "cli"], "tier": 1, "template": "go",
        "detect": {"files": ["go.mod"]},
        "init_cmd": "go mod init",
    },
    "flutter": {
        "name": "Flutter", "desc": "Cross-platform, single codebase",
        "types": ["mobile"], "tier": 1, "template": "flutter",
        "detect": {"files": ["pubspec.yaml"]},
        "init_cmd": "flutter create .",
        "recommended_for": ["mobile"],
    },
    # ── Tier 2: Web ─────────────────────────────────────────────────────
    "sveltekit": {
        "name": "SvelteKit", "desc": "Compiled, fast, Svelte-based",
        "types": ["web"], "tier": 2, "template": "_generic",
        "init_cmd": "npx sv create .",
    },
    "astro": {
        "name": "Astro", "desc": "Content-focused, island architecture",
        "types": ["web", "static_site"], "tier": 2, "template": "_generic",
        "init_cmd": "npm create astro@latest .",
    },
    "remix": {
        "name": "Remix", "desc": "Full-stack React, nested routes",
        "types": ["web"], "tier": 2, "template": "_generic",
        "init_cmd": "npx create-remix@latest .",
    },
    "nuxt": {
        "name": "Nuxt", "desc": "Vue framework, server rendering",
        "types": ["web"], "tier": 2, "template": "_generic",
        "init_cmd": "npx nuxi init .",
    },
    "angular": {
        "name": "Angular", "desc": "Enterprise SPA, TypeScript-first",
        "types": ["web"], "tier": 2, "template": "_generic",
        "init_cmd": "npx @angular/cli new . --skip-git",
    },
    "django": {
        "name": "Django", "desc": "Batteries-included Python web",
        "types": ["web", "api"], "tier": 2, "template": "_generic",
        "init_cmd": "pip install django && django-admin startproject app .",
    },
    "rails": {
        "name": "Ruby on Rails", "desc": "Convention over configuration",
        "types": ["web", "api"], "tier": 2, "template": "_generic",
        "init_cmd": "rails new . --skip-git",
    },
    "laravel": {
        "name": "Laravel", "desc": "PHP framework, elegant syntax",
        "types": ["web", "api"], "tier": 2, "template": "_generic",
        "init_cmd": "composer create-project laravel/laravel .",
    },
    # ── Tier 2: API / backend ───────────────────────────────────────────
    "node_express": {
        "name": "Node/Express", "desc": "Minimal Node.js web framework",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "npm init -y && npm install express",
    },
    "node_hono": {
        "name": "Node/Hono", "desc": "Ultrafast, edge-ready, Web Standard",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "npm create hono@latest .",
    },
    "rust_axum": {
        "name": "Rust/Axum", "desc": "Async Rust, Tokio-based",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "cargo init",
    },
    "ruby_rails": {
        "name": "Rails API", "desc": "Rails in API-only mode",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "rails new . --api --skip-git",
    },
    "java_spring": {
        "name": "Java/Spring Boot", "desc": "Enterprise Java, opinionated",
        "types": ["api"], "tier": 2, "template": "_generic",
    },
    "dotnet_api": {
        "name": "C#/.NET", "desc": "Cross-platform, high performance",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "dotnet new webapi",
    },
    "elixir_phoenix": {
        "name": "Elixir/Phoenix", "desc": "Functional, real-time, BEAM VM",
        "types": ["api"], "tier": 2, "template": "_generic",
        "init_cmd": "mix phx.new . --no-ecto",
    },
    # ── Tier 2: Mobile ──────────────────────────────────────────────────
    "swiftui_ios": {
        "name": "SwiftUI (iOS)", "desc": "Native iOS, declarative UI",
        "types": ["mobile"], "tier": 2, "template": "_generic",
    },
    "kotlin_android": {
        "name": "Kotlin (Android)", "desc": "Native Android, Jetpack Compose",
        "types": ["mobile"], "tier": 2, "template": "_generic",
    },
    "react_native": {
        "name": "React Native/Expo", "desc": "Cross-platform, React-based",
        "types": ["mobile"], "tier": 2, "template": "_generic",
        "init_cmd": "npx create-expo-app .",
    },
    "dotnet_maui": {
        "name": ".NET MAUI", "desc": "Cross-platform, C#, Xamarin successor",
        "types": ["mobile"], "tier": 2, "template": "_generic",
        "init_cmd": "dotnet new maui",
    },
    # ── Tier 2: CLI ─────────────────────────────────────────────────────
    "rust_cli": {
        "name": "Rust", "desc": "Fast CLI, single binary",
        "types": ["cli"], "tier": 2, "template": "_generic",
        "init_cmd": "cargo init",
    },
    "node_ts_cli": {
        "name": "Node/TypeScript", "desc": "TypeScript CLI, npm distribution",
        "types": ["cli"], "tier": 2, "template": "_generic",
        "init_cmd": "npm init -y && npm install typescript tsx",
    },
    "bash_cli": {
        "name": "Bash/Shell", "desc": "Shell scripts, no compilation",
        "types": ["cli"], "tier": 2, "template": "_generic",
    },
    "c_cpp_cli": {
        "name": "C/C++", "desc": "Systems programming, compiled",
        "types": ["cli"], "tier": 2, "template": "_generic",
    },
    # ── Tier 2: Desktop ─────────────────────────────────────────────────
    "electron": {
        "name": "Electron", "desc": "Cross-platform desktop, web tech",
        "types": ["desktop"], "tier": 2, "template": "_generic",
        "init_cmd": "npm init -y && npm install electron",
    },
    "tauri": {
        "name": "Tauri", "desc": "Lightweight desktop, Rust + web frontend",
        "types": ["desktop"], "tier": 2, "template": "_generic",
        "init_cmd": "npm create tauri-app@latest .",
    },
    "swiftui_desktop": {
        "name": "SwiftUI (macOS)", "desc": "Native macOS, declarative UI",
        "types": ["desktop"], "tier": 2, "template": "_generic",
    },
    "qt": {
        "name": "Qt", "desc": "Cross-platform C++/Python, mature toolkit",
        "types": ["desktop"], "tier": 2, "template": "_generic",
    },
    "dotnet_wpf": {
        "name": ".NET WPF/WinForms", "desc": "Windows-native desktop",
        "types": ["desktop"], "tier": 2, "template": "_generic",
    },
    # ── Tier 2: Browser extension ───────────────────────────────────────
    "chrome_ext": {
        "name": "Chrome Extension", "desc": "Manifest V3, Chrome Web Store",
        "types": ["browser_extension"], "tier": 2, "template": "_generic",
    },
    "firefox_ext": {
        "name": "Firefox WebExtension", "desc": "Cross-browser extension API",
        "types": ["browser_extension"], "tier": 2, "template": "_generic",
    },
    # ── Tier 2: Package / library ───────────────────────────────────────
    "npm_package": {
        "name": "npm package", "desc": "JavaScript/TypeScript library",
        "types": ["package"], "tier": 2, "template": "_generic",
        "init_cmd": "npm init -y",
    },
    "pypi_package": {
        "name": "PyPI package", "desc": "Python library, pip installable",
        "types": ["package"], "tier": 2, "template": "_generic",
    },
    "cargo_crate": {
        "name": "Cargo crate", "desc": "Rust library, crates.io",
        "types": ["package"], "tier": 2, "template": "_generic",
        "init_cmd": "cargo init --lib",
    },
    # ── Special: "Other" escape hatch ───────────────────────────────────
    "_other": {
        "name": "Other", "desc": "I'll describe my stack",
        "types": ["*"], "tier": 2, "template": "_generic",
    },
}


# ── Computed shims (backwards compatibility) ─────────────────────────────
# These reproduce the exact shapes of the former standalone dicts so that
# existing code (detect_framework, card_framework, tests) keeps working.

DETECT_PATTERNS = {}
for _k, _v in FRAMEWORKS.items():
    _det = _v.get("detect")
    if _det and _det.get("files"):
        _entry = {"files": _det["files"], "name": _v["name"]}
        if "package_contains" in _det:
            _entry["package_contains"] = _det["package_contains"]
        DETECT_PATTERNS[_k] = _entry

FRAMEWORK_OPTIONS = {}
for _k, _v in FRAMEWORKS.items():
    if _v["tier"] > 1 or _k == "_other":
        continue
    for _t in _v["types"]:
        _star = " *" if _t in _v.get("recommended_for", []) else ""
        _entry = (_k, f"{_v['name']}{_star}", _v["desc"])
        FRAMEWORK_OPTIONS.setdefault(_t, []).append(_entry)

PROJECT_TYPES = [
    ("web", "Web app"),
    ("api", "API / backend"),
    ("mobile", "Mobile app"),
    ("cli", "CLI tool / library"),
    ("static_site", "Static site / docs"),
    ("desktop", "Desktop app"),
    ("browser_extension", "Browser extension"),
    ("package", "Library / package"),
    ("monorepo", "Monorepo / multi-project"),
    ("hardware_iot", "Hardware / IoT / embedded"),
    ("other", "Other (I'll describe it)"),
]

# Types with zero dedicated frameworks -- skip card_framework, prompt free-text
_FREE_TEXT_TYPES = {"monorepo", "hardware_iot"}

FRAMEWORK_PROJECT_TYPE = {}
for _k, _v in FRAMEWORKS.items():
    if "*" not in _v["types"]:
        FRAMEWORK_PROJECT_TYPE[_k] = _v["types"][0]


# ── Framework detection ──────────────────────────────────────────────────


def load_detect_patterns(kit_dir):
    """Load detection patterns from scaffold.json files in each template directory.

    Returns a dict matching the shape of DETECT_PATTERNS, or empty dict if
    no scaffold.json files are found. This is a Tier 1 override -- scaffold.json
    is the source of truth when present; the registry-computed DETECT_PATTERNS
    is the fallback.
    """
    patterns = {}
    templates_dir = kit_dir / "templates" if kit_dir else None
    if templates_dir and templates_dir.is_dir():
        for d in sorted(templates_dir.iterdir()):
            scaffold = d / "scaffold.json"
            if scaffold.is_file():
                try:
                    data = json.loads(scaffold.read_text())
                    detect = data.get("detect", {})
                    entry = {"files": detect.get("files", []), "name": data.get("framework_name", d.name)}
                    if "package_contains" in detect:
                        entry["package_contains"] = detect["package_contains"]
                    patterns[d.name] = entry
                except (json.JSONDecodeError, KeyError):
                    continue
    return patterns


# Alias: fallback when scaffold.json files aren't available
_FALLBACK_DETECT_PATTERNS = DETECT_PATTERNS


def detect_framework(project_dir, detect_patterns=None):
    """Detect framework from existing project files. Returns (key, name) or (None, None).

    If detect_patterns is provided, uses those; otherwise falls back to the
    module-level DETECT_PATTERNS (computed from the FRAMEWORKS registry).
    """
    patterns = detect_patterns or DETECT_PATTERNS
    for key, pattern in patterns.items():
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


def detect_project_state(project_dir, detect_patterns=None):
    """Detect what exists in the project directory."""
    has_git = (project_dir / ".git").exists()
    is_empty = not any(project_dir.iterdir()) if project_dir.exists() else True
    framework_key, framework_name = detect_framework(project_dir, detect_patterns)
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
    """Card 1: What are you building? Returns (key, custom_text) tuple."""
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
    key = PROJECT_TYPES[idx][0]

    if key == "other":
        custom = ask("  Describe your project type: ")
        return key, custom
    return key, ""


def _build_framework_options(project_type, show_all=False):
    """Build the framework options list from the registry.

    Returns list of (key, display_label, description) tuples.
    When show_all=True, returns ALL frameworks grouped by type.
    When False, returns frameworks matching project_type + _other.
    """
    if show_all:
        # Group by primary type, Tier 1 first within each group
        type_order = [k for k, _ in PROJECT_TYPES if k not in ("other",)]
        groups = {}
        for fk, fv in FRAMEWORKS.items():
            if fk == "_other":
                continue
            primary = fv["types"][0]
            groups.setdefault(primary, []).append((fk, fv))
        result = []
        for t in type_order:
            items = groups.get(t, [])
            if not items:
                continue
            # Sort: Tier 1 first, then Tier 2, alphabetical within tier
            items.sort(key=lambda x: (x[1]["tier"], x[1]["name"]))
            type_label = dict(PROJECT_TYPES).get(t, t)
            result.append(("__header__", type_label, ""))
            for fk, fv in items:
                star = " *" if project_type in fv.get("recommended_for", []) else ""
                result.append((fk, f"{fv['name']}{star}", fv["desc"]))
        result.append(("_other", "Other", "I'll describe my stack"))
        return result

    # Type-filtered view
    result = []
    for fk, fv in FRAMEWORKS.items():
        if fk == "_other":
            continue
        if project_type not in fv["types"] and "*" not in fv["types"]:
            continue
        star = " *" if project_type in fv.get("recommended_for", []) else ""
        result.append((fk, f"{fv['name']}{star}", fv["desc"]))
    # Sort: Tier 1 recommended first, then Tier 1 others, then Tier 2
    def sort_key(item):
        fv = FRAMEWORKS.get(item[0], {})
        is_rec = 0 if project_type in fv.get("recommended_for", []) else 1
        return (fv.get("tier", 2), is_rec, fv.get("name", ""))
    result.sort(key=sort_key)
    result.append(("_other", "Other", "I'll describe my stack"))
    return result


def card_framework(project_type, show_all=False):
    """Card 2: Framework selection. Returns (key, custom_text) tuple.

    show_all=True shows all frameworks grouped by type (used for detection
    override). Default shows type-filtered list with [0] Show all option.
    """
    options = _build_framework_options(project_type, show_all=show_all)

    rows = [top()]
    rows.append(header("FRAMEWORK", "recommended: *"))
    rows.append(sep())
    num = 1
    num_map = {}  # number -> (key, name, desc)
    for key, label, desc in options:
        if key == "__header__":
            rows.append(line(f"  -- {label} --"))
            continue
        if show_all:
            text = f"[{num}] {label}"
        else:
            text = f"[{num}] {label:15s} {desc}"
        if len(text) > MAX_CONTENT:
            text = text[:MAX_CONTENT - 3] + "..."
        rows.append(line(text))
        num_map[str(num)] = (key, label, desc)
        num += 1

    if not show_all:
        rows.append(line(""))
        rows.append(line("[0] Show all frameworks"))

    rows.append(bot())
    print_card(rows)

    valid_nums = list(num_map.keys())
    if not show_all:
        valid_nums.append("0")
    choice = ask("> ", valid=valid_nums, default="1")

    if choice == "0":
        return card_framework(project_type, show_all=True)

    key = num_map[choice][0]
    if key == "_other":
        custom = ask("  Describe your framework/stack: ")
        return "_other", custom
    return key, ""


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


def card_platform_targets():
    """Card: Platform targets for desktop/mobile. Returns list of platform strings."""
    platforms = [
        ("macos", "macOS"),
        ("windows", "Windows"),
        ("linux", "Linux"),
        ("ios", "iOS"),
        ("android", "Android"),
        ("web", "Web"),
    ]
    rows = [top()]
    rows.append(line("PLATFORM TARGETS"))
    rows.append(sep())
    rows.append(line("Which platforms are you targeting?"))
    rows.append(line("(comma-separated, e.g. 1,3,5)"))
    rows.append(line(""))
    for i, (key, label) in enumerate(platforms, 1):
        rows.append(line(f"[{i}] {label}"))
    rows.append(line(f"[{len(platforms) + 1}] All"))
    rows.append(bot())
    print_card(rows)

    raw = ask("> ", default=str(len(platforms) + 1))
    nums = [n.strip() for n in raw.split(",")]
    all_num = str(len(platforms) + 1)
    if all_num in nums:
        return [k for k, _ in platforms]
    result = []
    for n in nums:
        try:
            idx = int(n) - 1
            if 0 <= idx < len(platforms):
                result.append(platforms[idx][0])
        except ValueError:
            continue
    return result if result else [platforms[0][0]]  # default to first if empty


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


def _resolve_framework_name(config):
    """Get display name for the framework from config."""
    fw = config["framework"]
    if fw == "_other":
        return config.get("framework_custom") or "Custom"
    return FRAMEWORKS.get(fw, {}).get("name", fw)


def _resolve_type_name(config):
    """Get display name for the project type from config."""
    pt = config["project_type"]
    if pt == "other":
        return config.get("project_type_custom") or "Custom"
    return dict(PROJECT_TYPES).get(pt, pt).replace("_", " ")


def card_confirmation(config):
    """Card 5: Confirmation before writing. Returns True to proceed."""
    framework_name = _resolve_framework_name(config)
    collab = config["collaboration_mode"]
    parts = [framework_name]
    type_name = _resolve_type_name(config)
    if type_name:
        parts.append(type_name)
    parts.append(collab)
    if config["has_database"]:
        parts.append("database")
    targets = config.get("platform_targets", [])
    if targets:
        parts.append(", ".join(targets))

    summary = ", ".join(parts)
    if len(summary) > W - 16:
        summary = summary[:W - 19] + "..."

    # Compute file counts based on active layers
    layers = get_active_layers(config)

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
    framework_name = _resolve_framework_name(config)

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
    """Get the recommended framework init command from the registry."""
    return FRAMEWORKS.get(framework, {}).get("init_cmd")


# ── Version stamping ─────────────────────────────────────────────────────

def write_doe_version(project_dir, config, kit_version):
    """Write .doe-version file with config choices in key=value format."""
    lines = [
        f"version={kit_version}",
        f"project_type={config['project_type']}",
        f"framework={config['framework']}",
        f"collaboration={config['collaboration_mode']}",
    ]
    if config.get("project_type_custom"):
        lines.append(f"project_type_custom={config['project_type_custom']}")
    if config.get("framework_custom"):
        lines.append(f"framework_custom={config['framework_custom']}")

    active = get_active_layers(config)
    non_universal = [l for l in active if l != "universal"]
    if non_universal:
        lines.append(f"layers={','.join(non_universal)}")

    targets = config.get("platform_targets", [])
    if targets:
        lines.append(f"platform_targets={','.join(targets)}")

    version_file = project_dir / ".doe-version"
    version_file.write_text("\n".join(lines) + "\n")


# ── CLAUDE.md generator ─────────────────────────────────────────────────

def get_active_layers(config):
    """Determine which capability layers are active based on config."""
    layers = ["universal"]
    if config.get("project_type") in ("web", "static_site", "browser_extension"):
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
        # Paths already qualified (e.g. .claude/plans/) keep their prefix
        if directive.startswith(".claude/") or directive.startswith("execution/"):
            lines.append(f"- {situation} -> `{directive}`")
        else:
            lines.append(f"- {situation} -> `directives/{directive}`")
    return "\n".join(lines) + "\n"


def generate_claude_md(config, kit_dir):
    """Generate a complete CLAUDE.md from config + templates + manifest.

    Concatenation order:
    1. _base/claude_sections/00_header.md
    2. _base/claude_sections/10_methodology.md
    2b. _base/claude_sections/15_commands.md (universal DOE commands)
    3. Framework claude_section.md (framework-specific commands)
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

    # 2b. Common commands (universal DOE commands)
    commands_section = claude_sections / "15_commands.md"
    if commands_section.exists():
        parts.append(commands_section.read_text())

    # 3. Framework section (Tier 1 from template, Tier 2 generated dynamically)
    fw_section = templates_dir / framework / "claude_section.md"
    if fw_section.exists():
        parts.append(fw_section.read_text())
    elif framework == "_other":
        custom = config.get("framework_custom", "Custom stack")
        parts.append(f"## Framework\n\n{custom}\n\nCustom stack -- refer to project README for build commands and directory structure.\n")
    else:
        fw_data = FRAMEWORKS.get(framework, {})
        parts.append(f"## Framework: {fw_data.get('name', framework)}\n\n{fw_data.get('desc', '')}.\n")

    # 3b. Platform targets (if set)
    targets = config.get("platform_targets", [])
    if targets:
        target_str = ", ".join(targets)
        parts.append(f"## Platform Targets\n\nTarget platforms: {target_str}. Build and test for all listed platforms.\n")

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
        # Remove read-only destination before copying (shutil.copy2
        # preserves source permissions, so previous installs may
        # have left read-only files that can't be overwritten)
        if dst.exists():
            dst.chmod(0o644)
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
    # guard_kit_writes.py is kit-contributor-only -- skip for user projects
    skip_hooks = {"guard_kit_writes.py"}
    if claude_hooks_src.is_dir():
        for f in claude_hooks_src.iterdir():
            if f.is_file() and f.name not in skip_hooks:
                if copy_to_project(f, f".claude/hooks/{f.name}"):
                    ch_count += 1
    if ch_count:
        rows.append(line(f".claude/hooks/ ({ch_count} hooks) .......... done"))

    # 5b. Claude Code stats (.claude/stats.json)
    stats_src = kit_dir / ".claude" / "stats.json"
    if copy_to_project(stats_src, ".claude/stats.json"):
        rows.append(line(".claude/stats.json ................. done"))

    # 5c. Claude Code plans (.claude/plans/)
    plans_src = kit_dir / ".claude" / "plans"
    plan_count = 0
    if plans_src.is_dir():
        for f in plans_src.iterdir():
            if f.is_file():
                if copy_to_project(f, f".claude/plans/{f.name}"):
                    plan_count += 1
    if plan_count:
        rows.append(line(f".claude/plans/ ({plan_count} plans) .......... done"))

    # 5d. Claude Code agents (.claude/agents/)
    agents_src = kit_dir / ".claude" / "agents"
    agent_count = 0
    if agents_src.is_dir():
        for f in agents_src.iterdir():
            if f.is_file():
                if copy_to_project(f, f".claude/agents/{f.name}"):
                    agent_count += 1
    if agent_count:
        rows.append(line(f".claude/agents/ ({agent_count} agents) ....... done"))

    # 5e. Claude Code project settings (.claude/settings.json)
    settings_src = kit_dir / ".claude" / "settings.json"
    settings_dst = project_dir / ".claude" / "settings.json"
    if settings_src.exists() and not settings_dst.exists():
        settings_dst.parent.mkdir(parents=True, exist_ok=True)
        kit_settings = json.loads(settings_src.read_text())
        # Copy hooks config only -- strip kit-specific keys (enabledPlugins)
        # and kit-contributor-only hooks (guard_kit_writes.py)
        project_hooks = {}
        for event, matchers in kit_settings.get("hooks", {}).items():
            filtered = []
            for matcher_block in matchers:
                hook_list = matcher_block.get("hooks", [])
                cleaned = [h for h in hook_list if "guard_kit_writes" not in h.get("command", "")]
                if cleaned:
                    filtered.append({**matcher_block, "hooks": cleaned})
            if filtered:
                project_hooks[event] = filtered
        project_settings = {"hooks": project_hooks}
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

    # 7b. tests/config.json (framework-aware health check config)
    tests_config = project_dir / "tests" / "config.json"
    if not tests_config.exists():
        tests_config.parent.mkdir(parents=True, exist_ok=True)
        # Map wizard framework to health_check.py SCAN_PROFILES key
        fw_to_profile = {
            "nextjs": "nextjs", "vite": "vite", "flutter": "flutter",
            "static": "html-app", "python": "html-app", "go": "html-app",
        }
        # Read build command from scaffold.json (with _generic fallback)
        fw_template = config["framework"]
        scaffold_path = templates_dir / fw_template / "scaffold.json"
        if not scaffold_path.exists():
            scaffold_path = templates_dir / "_generic" / "scaffold.json"
        build_cmd = ""
        if scaffold_path.exists():
            try:
                scaffold = json.loads(scaffold_path.read_text())
                build_cmd = scaffold.get("build_command") or ""
            except (json.JSONDecodeError, OSError):
                pass
        test_config = {
            "buildCommand": build_cmd,
            "testTimeout": 30,
            "projectType": fw_to_profile.get(config["framework"], "html-app"),
            "routeMode": "hash",
            "dependencies": [],
            "appPrefix": "",
            "routes": [],
            "initScript": "",
        }
        tests_config.write_text(json.dumps(test_config, indent=2) + "\n")
        total += 1
        rows.append(line("tests/config.json ................. done"))

    # 8. Framework-specific files (.gitignore, .env.example)
    fw_dir = templates_dir / config["framework"]
    if not fw_dir.is_dir():
        fw_dir = templates_dir / "_generic"
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

    # 11. Universal CLAUDE.md -> ~/.claude/CLAUDE.md (first-time only)
    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if not global_claude_md.exists():
        src = kit_dir / "universal-claude-md-template.md"
        if src.exists():
            global_claude_md.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, global_claude_md)
            total += 1
            rows.append(line("~/.claude/CLAUDE.md ................ done"))

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
    had_git = (project_dir / ".git").exists()
    if not had_git:
        result = subprocess.run(
            ["git", "init"], cwd=project_dir, capture_output=True,
        )
        if result.returncode != 0:
            print(f"  Warning: git init failed (exit {result.returncode})")

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
    if not had_git:
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
    detect_patterns = load_detect_patterns(kit_dir) or _FALLBACK_DETECT_PATTERNS
    state = detect_project_state(project_dir, detect_patterns)

    # Card 0: Welcome
    card_welcome(kit_version, project_dir, state)

    # Card 1: Project type (skip if framework auto-detected)
    project_type = None
    project_type_custom = ""
    if state["framework_key"]:
        # Auto-detected -- infer project type from framework
        project_type = FRAMEWORK_PROJECT_TYPE.get(state["framework_key"], "web")
    else:
        project_type, project_type_custom = card_project_type()

    # Card 2: Framework
    framework = None
    framework_custom = ""
    if state["framework_key"]:
        accepted = card_framework_confirm(state["framework_name"])
        if accepted:
            framework = state["framework_key"]
        else:
            # User declined detection -- show full list, keep inferred type
            framework, framework_custom = card_framework(project_type, show_all=True)
    elif project_type == "other" or project_type in _FREE_TEXT_TYPES:
        # "Other" type or type with no dedicated frameworks -- free-text directly
        custom = ask("  Describe your framework/stack: ")
        framework, framework_custom = "_other", custom
    else:
        framework, framework_custom = card_framework(project_type)

    # Card 2b: Platform targets (desktop/mobile only)
    platform_targets = []
    if project_type in ("desktop", "mobile"):
        platform_targets = card_platform_targets()

    # Card 3: Solo/team
    collab = card_setup()

    # Card 4: Data questions
    has_database, has_personal_data = card_data()

    # Build config dict
    config = {
        "project_type": project_type,
        "project_type_custom": project_type_custom,
        "framework": framework,
        "framework_custom": framework_custom,
        "collaboration_mode": collab["mode"],
        "github_users": collab["github_users"],
        "security_owner": collab["security_owner"],
        "has_database": has_database,
        "has_personal_data": has_personal_data,
        "platform_targets": platform_targets,
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
