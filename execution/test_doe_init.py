#!/usr/bin/env python3
"""Integration tests for DOE Init Wizard.

Tests doe init across 6 frameworks (Next.js, Python, Go, Flutter, Vite,
Static HTML) for both new-project (empty directory) and existing-project paths.
Verifies CLAUDE.md generation, file installation, manifest consistency,
.doe-version stamping, collaboration modes, and capability layers.
"""

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from doe_init import (
    detect_framework,
    generate_claude_md,
    get_active_layers,
    install_layer_files,
    setup_ci_git_collaboration,
    write_doe_version,
    DETECT_PATTERNS,
    FRAMEWORK_PROJECT_TYPE,
    FRAMEWORKS,
    PROJECT_TYPES,
)

KIT_DIR = Path(__file__).resolve().parent.parent
ACTUAL_KIT = Path.home() / "doe-starter-kit"
TIER1_FRAMEWORKS = ["nextjs", "python", "go", "flutter", "vite", "static"]

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}" + (f" -- {detail}" if detail else ""))


def make_config(framework, collab="solo", database=False, personal=False,
                is_empty=True, project_type=None, framework_custom="",
                project_type_custom="", platform_targets=None):
    if project_type is None:
        project_type = FRAMEWORK_PROJECT_TYPE.get(framework, "web")
    return {
        "project_type": project_type,
        "project_type_custom": project_type_custom,
        "framework": framework,
        "framework_custom": framework_custom,
        "collaboration_mode": collab,
        "github_users": ["alice", "bob"] if collab == "team" else [],
        "security_owner": "alice" if collab == "team" else "",
        "has_database": database,
        "has_personal_data": personal,
        "platform_targets": platform_targets or [],
        "detected_framework": None,
        "project_dir": "",
        "kit_dir": str(KIT_DIR),
        "is_empty": is_empty,
    }


def run_silent(func, *args, **kwargs):
    """Run a function while suppressing stdout (bordered cards)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        return func(*args, **kwargs)


# Sandbox global writes: patch Path.home() so install_layer_files
# writes commands/scripts to a temp dir instead of ~/.claude/
_sandbox_dir = tempfile.mkdtemp(prefix="doe-test-home-")
_real_home = Path.home()


def _fake_home():
    return Path(_sandbox_dir)


def run_sandboxed(func, *args, **kwargs):
    """Run with stdout suppressed AND global writes sandboxed."""
    buf = io.StringIO()
    with patch.object(Path, "home", staticmethod(_fake_home)):
        with redirect_stdout(buf):
            return func(*args, **kwargs)


# ── Test 1: Framework detection ──────────────────────────────────────────

print("Test 1: Framework detection")

# Next.js
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "package.json").write_text('{"dependencies":{"next":"14"}}')
    k, _ = detect_framework(Path(d))
    check("detect nextjs", k == "nextjs", f"got {k}")

# Vite
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "package.json").write_text('{"dependencies":{"vite":"5"}}')
    k, _ = detect_framework(Path(d))
    check("detect vite", k == "vite", f"got {k}")

# Python
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "pyproject.toml").write_text("[project]\nname='x'\n")
    k, _ = detect_framework(Path(d))
    check("detect python", k == "python", f"got {k}")

# Go
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "go.mod").write_text("module example.com/x\ngo 1.21\n")
    k, _ = detect_framework(Path(d))
    check("detect go", k == "go", f"got {k}")

# Flutter
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "pubspec.yaml").write_text("name: x\n")
    k, _ = detect_framework(Path(d))
    check("detect flutter", k == "flutter", f"got {k}")

# Static HTML
with tempfile.TemporaryDirectory() as d:
    (Path(d) / "index.html").write_text("<html></html>")
    k, _ = detect_framework(Path(d))
    check("detect static", k == "static", f"got {k}")

# Empty directory -- no framework detected
with tempfile.TemporaryDirectory() as d:
    k, _ = detect_framework(Path(d))
    check("detect empty directory", k is None, f"got {k}")


# ── Test 2: New project (empty directory) per framework ──────────────────

print("Test 2: New project (empty directory) -- 6 frameworks")

for fw in TIER1_FRAMEWORKS:
    with tempfile.TemporaryDirectory() as d:
        project_dir = Path(d)
        config = make_config(fw, is_empty=True)
        config["project_dir"] = str(project_dir)

        # CLAUDE.md generation
        try:
            claude_md = generate_claude_md(config, KIT_DIR)
            check(f"{fw}: CLAUDE.md generated", len(claude_md) > 100)
            check(f"{fw}: has triggers", "## Triggers" in claude_md)
            check(f"{fw}: has architecture", "Directive" in claude_md)
        except Exception as e:
            check(f"{fw}: CLAUDE.md generation", False, str(e))
            continue

        # File installation
        try:
            count = run_sandboxed(install_layer_files, config, KIT_DIR,
                               project_dir)
            check(f"{fw}: install count > 0", count > 0, f"count={count}")
        except Exception as e:
            check(f"{fw}: install_layer_files", False, str(e))
            continue

        # Key outputs
        check(f"{fw}: CLAUDE.md exists",
              (project_dir / "CLAUDE.md").exists())
        check(f"{fw}: directives/ exists",
              (project_dir / "directives").is_dir())
        check(f"{fw}: execution/ exists",
              (project_dir / "execution").is_dir())
        check(f"{fw}: .githooks/ exists",
              (project_dir / ".githooks").is_dir())
        check(f"{fw}: STATE.md exists",
              (project_dir / "STATE.md").exists())
        check(f"{fw}: tasks/todo.md exists",
              (project_dir / "tasks" / "todo.md").exists())

        # .doe-version
        write_doe_version(project_dir, config, "1.52.5")
        dv = project_dir / ".doe-version"
        check(f"{fw}: .doe-version exists", dv.exists())
        if dv.exists():
            content = dv.read_text()
            check(f"{fw}: version in .doe-version", "1.52.5" in content)
            check(f"{fw}: framework in .doe-version", fw in content)


# ── Test 3: Existing project (no overwrite) ──────────────────────────────

print("Test 3: Existing project -- files not overwritten")

SENTINEL = "ORIGINAL -- DO NOT OVERWRITE"

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("nextjs", is_empty=False)
    config["project_dir"] = str(project_dir)

    # First install populates everything
    run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)

    # Plant sentinel in an existing directive
    directive = project_dir / "directives" / "planning-rules.md"
    check("existing: directive was installed", directive.exists())
    directive.write_text(SENTINEL)

    # Plant sentinel in STATE.md
    (project_dir / "STATE.md").write_text(SENTINEL)

    # Plant sentinel in CLAUDE.md to verify it gets overwritten
    (project_dir / "CLAUDE.md").write_text(SENTINEL)

    # Re-run install -- existing files should NOT be overwritten
    run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)

    check("existing: directive preserved",
          directive.read_text() == SENTINEL)
    check("existing: STATE.md preserved",
          (project_dir / "STATE.md").read_text() == SENTINEL)
    # CLAUDE.md IS always overwritten (generated fresh each time)
    check("existing: CLAUDE.md regenerated",
          (project_dir / "CLAUDE.md").read_text() != SENTINEL)


# ── Test 4: Team mode (CODEOWNERS + CONTRIBUTING) ────────────────────────

print("Test 4: Team mode")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("nextjs", collab="team")
    config["project_dir"] = str(project_dir)

    run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)
    run_sandboxed(setup_ci_git_collaboration, config, KIT_DIR, project_dir)

    co = project_dir / ".github" / "CODEOWNERS"
    check("team: CODEOWNERS exists", co.exists())
    if co.exists():
        text = co.read_text()
        check("team: CODEOWNERS has @alice", "@alice" in text)
        check("team: CODEOWNERS has @bob", "@bob" in text)
        check("team: security paths", ".githooks/" in text)

    contrib = project_dir / "CONTRIBUTING.md"
    check("team: CONTRIBUTING.md exists", contrib.exists())
    if contrib.exists():
        check("team: CONTRIBUTING mentions security",
              "@alice" in contrib.read_text())

    # CI workflows copied
    check("team: doe-ci.yml",
          (project_dir / ".github" / "workflows" / "doe-ci.yml").exists())


# ── Test 5: Solo mode ────────────────────────────────────────────────────

print("Test 5: Solo mode")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("python", collab="solo")
    config["project_dir"] = str(project_dir)

    run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)
    run_sandboxed(setup_ci_git_collaboration, config, KIT_DIR, project_dir)

    co = project_dir / ".github" / "CODEOWNERS"
    check("solo: CODEOWNERS exists", co.exists())
    if co.exists():
        check("solo: CODEOWNERS has @you", "@you" in co.read_text())

    check("solo: no CONTRIBUTING.md",
          not (project_dir / "CONTRIBUTING.md").exists())

    check("solo: doe-ci.yml",
          (project_dir / ".github" / "workflows" / "doe-ci.yml").exists())


# ── Test 6: Manifest consistency ─────────────────────────────────────────

print("Test 6: Manifest consistency")

manifest = json.loads((KIT_DIR / "manifest.json").read_text())


def kit_file_exists(rel_path):
    """Check if a kit file exists in either the project or actual kit."""
    if (KIT_DIR / rel_path).exists():
        return True
    if ACTUAL_KIT.exists() and (ACTUAL_KIT / rel_path).exists():
        return True
    return False


for layer_name, layer_data in manifest["layers"].items():
    for name in layer_data.get("directives", []):
        check(f"manifest: directives/{name}",
              kit_file_exists(f"directives/{name}"),
              f"layer={layer_name}")

    for name in layer_data.get("execution", []):
        check(f"manifest: execution/{name}",
              kit_file_exists(f"execution/{name}"),
              f"layer={layer_name}")

    for name in layer_data.get("hooks", []):
        check(f"manifest: .githooks/{name}",
              kit_file_exists(f".githooks/{name}"),
              f"layer={layer_name}")

    for name in layer_data.get("commands", []):
        check(f"manifest: global-commands/{name}",
              kit_file_exists(f"global-commands/{name}"),
              f"layer={layer_name}")

    for name in layer_data.get("github", []):
        if name == "CODEOWNERS":
            continue  # Generated, not copied from kit
        check(f"manifest: .github/{name}",
              kit_file_exists(f".github/{name}"),
              f"layer={layer_name}")


# ── Test 7: Regulated layer ──────────────────────────────────────────────

print("Test 7: Regulated layer (personal data)")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("nextjs", database=True, personal=True)
    config["project_dir"] = str(project_dir)

    layers = get_active_layers(config)
    check("regulated: has universal", "universal" in layers)
    check("regulated: has public_facing", "public_facing" in layers)
    check("regulated: has data_handling", "data_handling" in layers)
    check("regulated: has regulated", "regulated" in layers)

    run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)

    check("regulated: data-governance.md",
          (project_dir / "data-governance.md").exists())
    check("regulated: legal-framework.md",
          (project_dir / "legal-framework.md").exists())
    check("regulated: data-compliance directive",
          (project_dir / "directives" / "data-compliance.md").exists())

    # CLAUDE.md should have regulated triggers
    claude_md = (project_dir / "CLAUDE.md").read_text()
    check("regulated: CLAUDE.md has compliance trigger",
          "data-compliance" in claude_md)


# ── Test 8: "Other" framework ───────────────────────────────────────────

print("Test 8: Other framework (Tier 2 fallback)")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("_other", project_type="other",
                         framework_custom="Tauri + Svelte",
                         project_type_custom="macOS menu bar app")
    config["project_dir"] = str(project_dir)

    # CLAUDE.md should contain custom framework text
    claude_md = generate_claude_md(config, KIT_DIR)
    check("other_fw: CLAUDE.md generated", len(claude_md) > 100)
    check("other_fw: custom text in CLAUDE.md", "Tauri + Svelte" in claude_md)

    # Install should fall back to _generic
    count = run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)
    check("other_fw: install count > 0", count > 0, f"count={count}")
    check("other_fw: CLAUDE.md exists", (project_dir / "CLAUDE.md").exists())

    # .doe-version should record custom text in key=value format
    write_doe_version(project_dir, config, "1.54.0")
    dv = project_dir / ".doe-version"
    check("other_fw: .doe-version exists", dv.exists())
    if dv.exists():
        content = dv.read_text()
        check("other_fw: version in .doe-version", "version=1.54.0" in content)
        check("other_fw: framework in .doe-version", "framework=_other" in content)
        check("other_fw: custom in .doe-version",
              "framework_custom=Tauri + Svelte" in content)


# ── Test 9: "Other" project type ────────────────────────────────────────

print("Test 9: Other project type")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("python", project_type="other",
                         project_type_custom="embedded firmware")
    config["project_dir"] = str(project_dir)

    # CLAUDE.md should generate without error
    try:
        claude_md = generate_claude_md(config, KIT_DIR)
        check("other_type: CLAUDE.md generated", len(claude_md) > 100)
    except Exception as e:
        check("other_type: CLAUDE.md generation", False, str(e))

    # .doe-version should record custom type
    write_doe_version(project_dir, config, "1.54.0")
    dv = project_dir / ".doe-version"
    if dv.exists():
        content = dv.read_text()
        check("other_type: project_type in .doe-version",
              "project_type=other" in content)
        check("other_type: custom type in .doe-version",
              "project_type_custom=embedded firmware" in content)


# ── Test 10: Platform targets ───────────────────────────────────────────

print("Test 10: Platform targets")

with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("electron", project_type="desktop",
                         platform_targets=["macos", "windows"])
    config["project_dir"] = str(project_dir)

    claude_md = generate_claude_md(config, KIT_DIR)
    check("platforms: Platform Targets in CLAUDE.md",
          "Platform Targets" in claude_md)
    check("platforms: macos in CLAUDE.md", "macos" in claude_md)
    check("platforms: windows in CLAUDE.md", "windows" in claude_md)

    # .doe-version should record targets
    write_doe_version(project_dir, config, "1.54.0")
    dv = project_dir / ".doe-version"
    if dv.exists():
        content = dv.read_text()
        check("platforms: targets in .doe-version",
              "platform_targets=macos,windows" in content)

    # No targets = no section
    config2 = make_config("nextjs", platform_targets=[])
    claude_md2 = generate_claude_md(config2, KIT_DIR)
    check("platforms: no section when empty",
          "Platform Targets" not in claude_md2)


# ── Test 11: New project types ──────────────────────────────────────────

print("Test 11: New project types")

type_keys = [k for k, _ in PROJECT_TYPES]
check("types: has 11 entries", len(PROJECT_TYPES) == 11,
      f"got {len(PROJECT_TYPES)}")
check("types: desktop in list", "desktop" in type_keys)
check("types: browser_extension in list", "browser_extension" in type_keys)
check("types: package in list", "package" in type_keys)
check("types: other in list", "other" in type_keys)

# Tier 2 framework falls back to _generic
with tempfile.TemporaryDirectory() as d:
    project_dir = Path(d)
    config = make_config("electron", project_type="desktop")
    config["project_dir"] = str(project_dir)

    claude_md = generate_claude_md(config, KIT_DIR)
    check("types: Electron in CLAUDE.md", "Electron" in claude_md)

    count = run_sandboxed(install_layer_files, config, KIT_DIR, project_dir)
    check("types: desktop install > 0", count > 0)

# browser_extension gets public_facing layer
config_ext = make_config("chrome_ext", project_type="browser_extension")
layers = get_active_layers(config_ext)
check("types: browser_ext has public_facing", "public_facing" in layers)


# ── Test 12: Registry regression guard ──────────────────────────────────

print("Test 12: Registry regression")

# DETECT_PATTERNS must still have exactly the original 6 entries
original_keys = {"nextjs", "vite", "python", "go", "flutter", "static"}
check("regression: DETECT_PATTERNS count", len(DETECT_PATTERNS) == 6,
      f"got {len(DETECT_PATTERNS)}")
check("regression: DETECT_PATTERNS keys",
      set(DETECT_PATTERNS.keys()) == original_keys,
      f"got {set(DETECT_PATTERNS.keys())}")

# Each original entry has correct name
check("regression: nextjs name", DETECT_PATTERNS["nextjs"]["name"] == "Next.js")
check("regression: vite name", DETECT_PATTERNS["vite"]["name"] == "Vite/React")
check("regression: python name", DETECT_PATTERNS["python"]["name"] == "Python")
check("regression: go name", DETECT_PATTERNS["go"]["name"] == "Go")
check("regression: flutter name", DETECT_PATTERNS["flutter"]["name"] == "Flutter")
check("regression: static name", DETECT_PATTERNS["static"]["name"] == "Static HTML")

# FRAMEWORK_PROJECT_TYPE original 6 must still be correct
check("regression: FPT nextjs", FRAMEWORK_PROJECT_TYPE["nextjs"] == "web")
check("regression: FPT python", FRAMEWORK_PROJECT_TYPE["python"] == "api")
check("regression: FPT go", FRAMEWORK_PROJECT_TYPE["go"] == "api")
check("regression: FPT flutter", FRAMEWORK_PROJECT_TYPE["flutter"] == "mobile")
check("regression: FPT vite", FRAMEWORK_PROJECT_TYPE["vite"] == "web")
check("regression: FPT static", FRAMEWORK_PROJECT_TYPE["static"] == "web")


# ── Test 13: Registry consistency ───────────────────────────────────────

print("Test 13: Registry consistency")

valid_type_keys = {k for k, _ in PROJECT_TYPES} | {"*"}
required_keys = {"name", "desc", "types", "tier", "template"}

for fk, fv in FRAMEWORKS.items():
    # Required keys present
    missing = required_keys - set(fv.keys())
    check(f"registry: {fk} has required keys", not missing,
          f"missing: {missing}")
    # types values are valid
    for t in fv.get("types", []):
        check(f"registry: {fk} type '{t}' valid", t in valid_type_keys,
              f"not in PROJECT_TYPES")
    # template dir exists or is _generic
    tmpl = fv.get("template", "")
    if tmpl == "_generic":
        check(f"registry: {fk} template _generic exists",
              (ACTUAL_KIT / "templates" / "_generic").is_dir()
              if ACTUAL_KIT.exists() else True)
    else:
        check(f"registry: {fk} template '{tmpl}' exists",
              kit_file_exists(f"templates/{tmpl}/scaffold.json"),
              f"Tier {fv.get('tier')} but no template dir")

check("registry: 35+ entries", len(FRAMEWORKS) >= 35,
      f"got {len(FRAMEWORKS)}")
check("registry: has _other", "_other" in FRAMEWORKS)


# ── Cleanup ──────────────────────────────────────────────────────────────

import shutil
shutil.rmtree(_sandbox_dir, ignore_errors=True)


# ── Summary ──────────────────────────────────────────────────────────────

print()
total = passed + failed
if failed == 0:
    print(f"ALL PASS ({passed}/{total} checks)")
else:
    print(f"FAILED: {failed}/{total} checks")
    sys.exit(1)
