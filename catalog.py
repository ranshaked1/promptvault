#!/usr/bin/env python3
"""
Claude Asset Catalog Generator
Reads registry.json + descriptions.json and generates MY_ASSETS.md — a
human-readable overview of everything you have, with one-sentence descriptions.

Auto-detects descriptions from README files and package.json when possible.
User-provided descriptions in descriptions.json always take priority.
"""

import json
import os
import datetime
from pathlib import Path

VAULT_DIR = Path(__file__).parent.resolve()
REGISTRY_FILE = VAULT_DIR / "registry.json"
DESCRIPTIONS_FILE = VAULT_DIR / "descriptions.json"
CATALOG_FILE = VAULT_DIR / "MY_ASSETS.md"


def load_descriptions():
    """Load user-provided descriptions."""
    if DESCRIPTIONS_FILE.exists():
        data = json.loads(DESCRIPTIONS_FILE.read_text())
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def save_descriptions(descs):
    """Save descriptions back, preserving the comment."""
    data = {
        "_comment": (
            "User-editable descriptions for Claude assets. "
            "Add a key matching the asset name or path, with a one-sentence description. "
            "These persist across scans and are used to generate MY_ASSETS.md."
        ),
    }
    data.update(descs)
    DESCRIPTIONS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def auto_describe_project(path):
    """Try to auto-detect a project description from its files."""
    p = Path(path)
    if not p.is_dir():
        return None

    # Try README
    for readme in ("README.md", "README.txt", "README", "readme.md"):
        readme_path = p / readme
        if readme_path.exists():
            try:
                text = readme_path.read_text(errors="ignore")
                # Get first non-empty, non-heading line
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("="):
                        # Truncate to one sentence
                        sentence = line.split(". ")[0].rstrip(".")
                        if len(sentence) > 15:
                            return sentence + "."
            except (PermissionError, OSError):
                pass

    # Try package.json description
    pkg_path = p / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            desc = pkg.get("description")
            if desc:
                return desc
        except (json.JSONDecodeError, PermissionError):
            pass

    # Try pyproject.toml or setup.py (basic)
    pyproject = p / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text()
            for line in text.splitlines():
                if line.strip().startswith("description"):
                    val = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    if val:
                        return val
        except (PermissionError, OSError):
            pass

    return None


def auto_describe_asset(asset):
    """Generate a description based on asset type and category."""
    cat = asset.get("category", "other")
    atype = asset.get("type", "")
    name = asset.get("name", "")
    path = asset.get("path", "")

    # Try project auto-detection
    if atype in ("project_directory", "git_repo"):
        desc = auto_describe_project(path)
        if desc:
            return desc

    # MCP servers
    if cat == "mcp_server":
        details = asset.get("details", {})
        cmd = details.get("command", "")
        if "npx" in cmd:
            return f"MCP server running via npx ({name.replace('mcp:', '')})."
        return f"MCP server providing tools to Claude ({name.replace('mcp:', '')})."

    # Skills
    if cat == "skill":
        return f"Claude Code skill: {name}."

    # Hooks
    if cat == "hook":
        return f"Claude Code hook script: {name}."

    # Configs
    if cat == "config":
        if "desktop" in name.lower() or "desktop" in path.lower():
            return "Claude Desktop application configuration."
        if "settings" in name.lower():
            return "Claude Code settings and preferences."
        return f"Configuration file for Claude tools."

    # npm/pip packages
    if atype == "npm_package":
        version = asset.get("details", {}).get("version", "")
        return f"npm package ({version})."
    if atype == "python_package":
        version = asset.get("details", {}).get("version", "")
        return f"Python package ({version})."

    return None


def get_description(asset, user_descs):
    """Get description for an asset: user-provided > auto-detected > None."""
    name = asset.get("name", "")
    path = asset.get("path", "")

    # Check user descriptions (match by name or path basename)
    for key, desc in user_descs.items():
        if key == name or key == Path(path).name or key in path:
            return desc

    # Auto-detect
    return auto_describe_asset(asset)


def generate_catalog():
    """Generate MY_ASSETS.md from registry + descriptions."""
    if not REGISTRY_FILE.exists():
        print("  No registry found. Run: python vault.py scan")
        return

    registry = json.loads(REGISTRY_FILE.read_text())
    user_descs = load_descriptions()
    assets = registry.get("assets", [])

    # Group by category, but only include meaningful assets
    # (skip individual config files inside ~/.claude/ that are noise)
    SKIP_SOURCES = {"dot_claude"}  # too granular
    SKIP_NAMES = {"shell-snapshots", "backups", "session-env", "projects"}
    SHOW_CATEGORIES = {"project", "mcp_server", "skill", "hook", "script", "tool"}

    # Always show projects, mcp_servers, skills, hooks, scripts, tools
    # For configs, only show top-level ones
    filtered = []
    seen_paths = set()
    for a in assets:
        cat = a.get("category", "other")
        source = a.get("source", "")
        path = a.get("path", "")

        if path in seen_paths:
            continue

        # Skip noise (shell snapshots, internal backups, etc.)
        name = a.get("name", "")
        if any(skip in name for skip in SKIP_NAMES):
            continue
        if "snapshot" in name.lower() or "backup" in name.lower():
            continue
        # Skip ~/.claude itself showing as a project (it's a config dir, not a project)
        if name == ".claude":
            continue

        if cat in SHOW_CATEGORIES:
            seen_paths.add(path)
            filtered.append(a)
        elif cat == "config" and source != "dot_claude":
            seen_paths.add(path)
            filtered.append(a)

    # Group
    groups = {}
    for a in filtered:
        cat = a.get("category", "other")
        groups.setdefault(cat, []).append(a)

    # Category display order and labels
    cat_labels = {
        "project": ("Projects", "Repos and automation projects"),
        "mcp_server": ("MCP Servers", "Model Context Protocol servers providing tools to Claude"),
        "skill": ("Skills", "Custom Claude Code skills"),
        "hook": ("Hooks", "Scripts that run on Claude Code events"),
        "script": ("Scripts", "Standalone utility scripts"),
        "tool": ("Tools", "Installed CLI tools and packages"),
        "config": ("Configurations", "Settings and config files"),
    }
    cat_order = ["project", "mcp_server", "skill", "hook", "script", "tool", "config"]

    # Track which assets have no description (for user to fill in)
    undescribed = []

    # Build markdown
    lines = [
        "# My Claude Assets",
        "",
        f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "A complete inventory of my Claude-related projects, tools, and configurations.",
        "Edit `descriptions.json` to update descriptions, then run `python vault.py catalog` to regenerate.",
        "",
        "---",
        "",
    ]

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    for cat in cat_order:
        if cat in groups:
            label = cat_labels.get(cat, (cat, ""))[0]
            lines.append(f"| {label} | {len(groups[cat])} |")
    lines.append("")

    # Sections
    for cat in cat_order:
        if cat not in groups:
            continue

        label, subtitle = cat_labels.get(cat, (cat, ""))
        items = groups[cat]

        lines.append(f"## {label}")
        lines.append(f"*{subtitle}*")
        lines.append("")

        for a in sorted(items, key=lambda x: x["name"].lower()):
            name = a["name"]
            path = a["path"]
            desc = get_description(a, user_descs)
            modified = a.get("modified", "")[:10]

            lines.append(f"### {name}")
            if desc:
                lines.append(f"{desc}")
            else:
                lines.append(f"*(no description — add one in `descriptions.json`)*")
                undescribed.append(name)
            lines.append(f"- **Path:** `{path}`")
            if modified:
                lines.append(f"- **Last modified:** {modified}")
            details = a.get("details", {})
            if details:
                for k, v in details.items():
                    if v and k not in ("env_keys",):
                        lines.append(f"- **{k}:** {v}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated by Claude Vault (`python vault.py catalog`)*")

    catalog_text = "\n".join(lines) + "\n"
    CATALOG_FILE.write_text(catalog_text)

    print(f"  Catalog written to: {CATALOG_FILE}")
    print(f"  {len(filtered)} assets documented")

    if undescribed:
        print(f"\n  {len(undescribed)} asset(s) have no description.")
        print(f"  Add descriptions in descriptions.json for:")
        for name in undescribed[:10]:
            print(f"    - {name}")
        if len(undescribed) > 10:
            print(f"    ... and {len(undescribed) - 10} more")

    return catalog_text


if __name__ == "__main__":
    generate_catalog()
