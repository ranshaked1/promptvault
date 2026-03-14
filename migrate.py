#!/usr/bin/env python3
"""
Claude Asset Migration Tool
Reads the scan registry and generates a migration plan to consolidate
everything into ~/Claude/. Can also execute the migration (move + symlink).

Usage:
    python migrate.py plan          # Show what would be done (dry run)
    python migrate.py execute       # Actually move files and create symlinks
    python migrate.py verify        # Check that symlinks and paths are valid
"""

import json
import os
import sys
import shutil
import datetime
import platform
from pathlib import Path

CLAUDE_HOME = Path.home() / "Claude"
REGISTRY_FILE = Path(__file__).parent / "registry.json"

# ── Folder structure inside ~/Claude/ ────────────────────────────────────────

FOLDERS = {
    "projects":   "projects",       # Automation repos and projects
    "configs":    "configs",        # Config backups / managed configs
    "mcp":        "mcp-servers",    # MCP server references
    "skills":     "skills",         # Custom skills
    "hooks":      "hooks",          # Hook scripts
    "scripts":    "scripts",        # Standalone scripts & utilities
    "prompts":    "prompts",        # Saved prompts and templates
    "backups":    "backups",        # Config backups from ~/.claude/backups
}

# ── Assets that MUST stay at their original path ─────────────────────────────
# These are read by Claude Code / Claude Desktop from hardcoded locations.
# Strategy: move real files to ~/Claude/, symlink back to original location.

SYMLINK_ASSETS = {
    # original path → subfolder inside ~/Claude/
    "~/.claude":            "configs/claude-code",
    "~/.claude.json":       "configs/claude-code/.claude.json",
}

# macOS-only symlink targets
SYMLINK_ASSETS_MAC = {
    "~/Library/Application Support/Claude": "configs/claude-desktop",
}

# ── Assets that can be moved directly (no symlink needed) ────────────────────
# These are standalone projects with no fixed-path dependency.

DIRECT_MOVE_PATTERNS = {
    # home-level directories that look like Claude projects
    "project_directory": "projects",
    "git_repo":          "projects",
}


def expand(p):
    return Path(os.path.expanduser(p)).resolve()


def load_registry():
    if not REGISTRY_FILE.exists():
        print(f"  ERROR: No registry found at {REGISTRY_FILE}")
        print(f"  Run 'python scanner.py' first to scan your system.")
        sys.exit(1)
    return json.loads(REGISTRY_FILE.read_text())


def build_migration_plan():
    """Analyze registry and build a list of migration actions."""
    registry = load_registry()
    actions = []

    # 1. Create folder structure
    for label, folder in FOLDERS.items():
        target = CLAUDE_HOME / folder
        if not target.exists():
            actions.append({
                "action": "mkdir",
                "target": str(target),
                "description": f"Create {folder}/ directory",
            })

    # 2. Symlink assets (must stay at original path but live in ~/Claude/)
    symlinks = {**SYMLINK_ASSETS}
    if platform.system() == "Darwin":
        symlinks.update(SYMLINK_ASSETS_MAC)

    for original, dest_sub in symlinks.items():
        orig_path = expand(original)
        dest_path = CLAUDE_HOME / dest_sub

        if not orig_path.exists():
            continue

        if orig_path.is_symlink():
            # Already a symlink — check if it points to our target
            current_target = orig_path.resolve()
            if current_target == dest_path.resolve():
                actions.append({
                    "action": "skip",
                    "source": str(orig_path),
                    "target": str(dest_path),
                    "description": f"Already symlinked: {original} → {dest_sub}",
                })
            else:
                actions.append({
                    "action": "relink",
                    "source": str(orig_path),
                    "target": str(dest_path),
                    "description": f"Update symlink: {original} → {dest_sub} (currently points to {current_target})",
                })
        else:
            actions.append({
                "action": "move_and_symlink",
                "source": str(orig_path),
                "target": str(dest_path),
                "symlink_at": str(orig_path),
                "description": f"Move {original} → ~/Claude/{dest_sub}, symlink back",
                "is_dir": orig_path.is_dir(),
            })

    # 3. Direct-move projects found scattered in home directory
    seen_paths = set()
    for asset in registry.get("assets", []):
        path = asset.get("path", "")
        atype = asset.get("type", "")
        name = asset.get("name", "")

        # Skip if inside ~/Claude/ already, or inside ~/.claude/
        if str(CLAUDE_HOME) in path or "/.claude" in path:
            continue

        # Skip the promptvault repo itself (it will become ~/Claude/)
        if "promptvault" in path:
            continue

        if path in seen_paths:
            continue
        seen_paths.add(path)

        # Home-level project directories (like ~/ai-cost-tracker)
        p = Path(path)
        if p == Path.home():
            continue
        if atype in ("project_directory", "git_repo") and p.exists():
            dest = CLAUDE_HOME / "projects" / p.name
            actions.append({
                "action": "move_project",
                "source": path,
                "target": str(dest),
                "description": f"Move project {p.name}/ → ~/Claude/projects/{p.name}/",
                "is_git": atype == "git_repo",
                "details": asset.get("details", {}),
            })

    # 4. Handle settings.json path references that need updating
    actions.append({
        "action": "note",
        "description": (
            "After migration, paths in settings.json (hook scripts, etc.) "
            "will still work because symlinks preserve the original paths. "
            "No config edits needed."
        ),
    })

    return actions


def print_plan(actions):
    """Display the migration plan in a human-readable format."""
    print("=" * 70)
    print("  Claude Asset Migration Plan")
    print("  Target: ~/Claude/")
    print("=" * 70)

    action_groups = {
        "mkdir": [],
        "move_and_symlink": [],
        "move_project": [],
        "relink": [],
        "skip": [],
        "note": [],
    }

    for a in actions:
        group = a["action"]
        if group in action_groups:
            action_groups[group].append(a)
        else:
            action_groups.setdefault("other", []).append(a)

    if action_groups["mkdir"]:
        print("\n  ── CREATE DIRECTORIES ──")
        for a in action_groups["mkdir"]:
            print(f"    MKDIR  {a['target']}")

    if action_groups["move_and_symlink"]:
        print("\n  ── MOVE + SYMLINK (configs that must stay accessible at original path) ──")
        for a in action_groups["move_and_symlink"]:
            print(f"    MOVE   {a['source']}")
            print(f"       →   {a['target']}")
            print(f"    LINK   {a['symlink_at']} → {a['target']}")
            print()

    if action_groups["move_project"]:
        print("\n  ── MOVE PROJECTS ──")
        for a in action_groups["move_project"]:
            git_tag = " [git repo]" if a.get("is_git") else ""
            print(f"    MOVE   {a['source']}{git_tag}")
            print(f"       →   {a['target']}")
            remote = a.get("details", {}).get("remote_url")
            if remote:
                print(f"           remote: {remote}")
            print()

    if action_groups["skip"]:
        print("\n  ── ALREADY DONE ──")
        for a in action_groups["skip"]:
            print(f"    OK     {a['description']}")

    if action_groups["note"]:
        print("\n  ── NOTES ──")
        for a in action_groups["note"]:
            print(f"    NOTE   {a['description']}")

    # Summary
    move_count = len(action_groups["move_and_symlink"]) + len(action_groups["move_project"])
    print(f"\n{'=' * 70}")
    print(f"  Summary: {len(action_groups['mkdir'])} dirs to create, "
          f"{move_count} items to move, "
          f"{len(action_groups['skip'])} already done")
    print(f"{'=' * 70}")


def execute_plan(actions, dry_run=False):
    """Execute the migration actions."""
    print("\n  Executing migration...\n")
    errors = []

    for a in actions:
        action = a["action"]
        desc = a.get("description", "")

        if action == "note" or action == "skip":
            print(f"  SKIP  {desc}")
            continue

        if action == "mkdir":
            target = Path(a["target"])
            print(f"  MKDIR {target}")
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)

        elif action == "move_and_symlink":
            src = Path(a["source"])
            dst = Path(a["target"])
            print(f"  MOVE  {src} → {dst}")

            if not dry_run:
                try:
                    # Ensure parent exists
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    # Move
                    if dst.exists():
                        print(f"  WARN  Target already exists: {dst}, skipping")
                        continue
                    shutil.move(str(src), str(dst))
                    # Create symlink at original location
                    os.symlink(str(dst), str(src))
                    print(f"  LINK  {src} → {dst}")
                except Exception as e:
                    print(f"  ERROR {e}")
                    errors.append(str(e))

        elif action == "move_project":
            src = Path(a["source"])
            dst = Path(a["target"])
            print(f"  MOVE  {src} → {dst}")

            if not dry_run:
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        print(f"  WARN  Target already exists: {dst}, skipping")
                        continue
                    shutil.move(str(src), str(dst))
                    print(f"  OK    Moved {src.name}")
                except Exception as e:
                    print(f"  ERROR {e}")
                    errors.append(str(e))

        elif action == "relink":
            src = Path(a["source"])
            dst = Path(a["target"])
            print(f"  RELINK {src} → {dst}")
            if not dry_run:
                try:
                    os.unlink(str(src))
                    os.symlink(str(dst), str(src))
                except Exception as e:
                    print(f"  ERROR {e}")
                    errors.append(str(e))

    if errors:
        print(f"\n  Completed with {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    else:
        print(f"\n  Migration complete! Your Claude hub is at: {CLAUDE_HOME}")

    return errors


def verify():
    """Verify that all symlinks are valid and the structure is correct."""
    print("=" * 60)
    print("  Verifying ~/Claude/ structure")
    print("=" * 60)

    issues = []

    # Check folder structure
    for label, folder in FOLDERS.items():
        target = CLAUDE_HOME / folder
        status = "OK" if target.exists() else "MISSING"
        print(f"  {status:8s} {folder}/")
        if not target.exists():
            issues.append(f"Missing directory: {folder}")

    # Check symlinks
    print()
    symlinks = {**SYMLINK_ASSETS}
    if platform.system() == "Darwin":
        symlinks.update(SYMLINK_ASSETS_MAC)

    for original, dest_sub in symlinks.items():
        orig_path = expand(original)
        dest_path = CLAUDE_HOME / dest_sub

        if orig_path.is_symlink():
            actual_target = orig_path.resolve()
            if actual_target == dest_path.resolve():
                print(f"  OK       {original} → {dest_sub}")
            else:
                print(f"  WRONG    {original} → {actual_target} (expected {dest_path})")
                issues.append(f"Symlink mismatch: {original}")
        elif orig_path.exists():
            print(f"  NOT LINK {original} (exists but is not a symlink)")
            issues.append(f"Not symlinked: {original}")
        else:
            print(f"  ABSENT   {original} (not found)")

    print(f"\n{'=' * 60}")
    if issues:
        print(f"  {len(issues)} issue(s) found:")
        for i in issues:
            print(f"    - {i}")
    else:
        print("  All checks passed!")
    print("=" * 60)
    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command>")
        print()
        print("Commands:")
        print("  plan      Show migration plan (dry run, changes nothing)")
        print("  execute   Execute the migration (move files + create symlinks)")
        print("  verify    Verify that the migration was successful")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "plan":
        actions = build_migration_plan()
        print_plan(actions)
        print("\n  To execute this plan, run: python migrate.py execute")

    elif cmd == "execute":
        actions = build_migration_plan()
        print_plan(actions)
        print()
        confirm = input("  Proceed with migration? (yes/no): ").strip().lower()
        if confirm in ("yes", "y"):
            execute_plan(actions)
        else:
            print("  Aborted.")

    elif cmd == "verify":
        verify()

    else:
        print(f"  Unknown command: {cmd}")
        print("  Use: plan, execute, or verify")
        sys.exit(1)


if __name__ == "__main__":
    main()
