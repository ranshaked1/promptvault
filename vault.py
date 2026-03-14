#!/usr/bin/env python3
"""
Claude Vault CLI — manage your centralized Claude assets.

Usage:
    python vault.py scan              # Scan system and update registry
    python vault.py list [category]   # List assets (optionally filter by category)
    python vault.py search <query>    # Search assets by name or path
    python vault.py status            # Dashboard summary
    python vault.py migrate plan      # Show migration plan
    python vault.py migrate execute   # Execute migration
    python vault.py migrate verify    # Verify migration
    python vault.py tree              # Show ~/Claude/ folder tree
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

VAULT_DIR = Path(__file__).parent.resolve()
REGISTRY_FILE = VAULT_DIR / "registry.json"


def load_registry():
    if not REGISTRY_FILE.exists():
        return None
    return json.loads(REGISTRY_FILE.read_text())


def cmd_scan():
    """Run the scanner."""
    subprocess.run([sys.executable, str(VAULT_DIR / "scanner.py")])


def cmd_list(category=None):
    """List all assets, optionally filtered by category."""
    reg = load_registry()
    if not reg:
        print("  No registry found. Run: python vault.py scan")
        return

    assets = reg["assets"]
    if category:
        assets = [a for a in assets if a.get("category") == category]
        if not assets:
            print(f"  No assets found in category '{category}'")
            print(f"  Available: {', '.join(sorted(reg.get('category_summary', {}).keys()))}")
            return

    # Group by category
    groups = {}
    for a in assets:
        cat = a.get("category", "other")
        groups.setdefault(cat, []).append(a)

    for cat in sorted(groups.keys()):
        items = groups[cat]
        print(f"\n  [{cat.upper()}] ({len(items)})")
        print(f"  {'─' * 50}")
        for a in items:
            name = a["name"]
            path = a["path"]
            modified = a.get("modified", "")[:10]
            atype = a.get("type", "")
            size = a.get("size_bytes")
            size_str = f" ({_human_size(size)})" if size else ""
            print(f"    {name}")
            print(f"      {path}{size_str}  [{atype}]  {modified}")


def cmd_search(query):
    """Search assets by name or path."""
    reg = load_registry()
    if not reg:
        print("  No registry found. Run: python vault.py scan")
        return

    query_lower = query.lower()
    matches = [
        a for a in reg["assets"]
        if query_lower in a["name"].lower() or query_lower in a["path"].lower()
    ]

    if not matches:
        print(f"  No assets matching '{query}'")
        return

    print(f"  Found {len(matches)} match(es) for '{query}':\n")
    for a in matches:
        print(f"    {a['name']}")
        print(f"      Path:     {a['path']}")
        print(f"      Category: {a.get('category', '?')}")
        print(f"      Type:     {a.get('type', '?')}")
        if a.get("details"):
            for k, v in a["details"].items():
                print(f"      {k}: {v}")
        print()


def cmd_status():
    """Show a summary dashboard."""
    reg = load_registry()
    claude_home = Path.home() / "Claude"

    print("=" * 60)
    print("  Claude Vault — Status Dashboard")
    print("=" * 60)

    if reg:
        scan_time = reg.get("last_scan", "never")[:19].replace("T", " ")
        print(f"\n  Last scan:      {scan_time}")
        print(f"  Platform:       {reg.get('platform', '?')}")
        print(f"  Total assets:   {reg.get('total_assets', 0)}")
        print(f"\n  Categories:")
        for cat, count in sorted(reg.get("category_summary", {}).items(), key=lambda x: -x[1]):
            bar = "█" * count
            print(f"    {cat:20s} {count:3d}  {bar}")
    else:
        print("\n  No registry found. Run: python vault.py scan")

    # Check ~/Claude/ structure
    print(f"\n  Claude Home:    {claude_home}")
    if claude_home.exists():
        print("  Structure:")
        for item in sorted(claude_home.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                count = sum(1 for _ in item.iterdir()) if item.is_dir() else 0
                print(f"    📁 {item.name}/ ({count} items)")
            else:
                print(f"    📄 {item.name}")
    else:
        print("  Not created yet. Run: python vault.py migrate plan")

    # Check symlinks
    symlink_checks = [
        ("~/.claude", "Claude Code config"),
        ("~/.claude.json", "Claude Code JSON"),
    ]
    if sys.platform == "darwin":
        symlink_checks.append(
            ("~/Library/Application Support/Claude", "Claude Desktop")
        )

    print(f"\n  Symlinks:")
    for path_str, label in symlink_checks:
        p = Path(os.path.expanduser(path_str))
        if p.is_symlink():
            target = os.readlink(str(p))
            print(f"    ✓  {label}: {path_str} → {target}")
        elif p.exists():
            print(f"    ○  {label}: {path_str} (not symlinked yet)")
        else:
            print(f"    ✗  {label}: {path_str} (not found)")

    print("=" * 60)


def cmd_tree():
    """Show the ~/Claude/ folder tree."""
    claude_home = Path.home() / "Claude"
    if not claude_home.exists():
        print(f"  {claude_home} does not exist yet.")
        print("  Run: python vault.py migrate plan")
        return

    print(f"\n  {claude_home}/")
    _print_tree(claude_home, prefix="  ")


def _print_tree(directory, prefix="", max_depth=3, depth=0):
    if depth >= max_depth:
        return
    entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name))
    for i, entry in enumerate(entries):
        if entry.name.startswith(".git") and entry.name != ".gitignore":
            continue
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        suffix = "/" if entry.is_dir() else ""
        symlink = f" → {os.readlink(str(entry))}" if entry.is_symlink() else ""
        print(f"{prefix}{connector}{entry.name}{suffix}{symlink}")
        if entry.is_dir() and not entry.is_symlink():
            ext = "    " if is_last else "│   "
            _print_tree(entry, prefix=prefix + ext, max_depth=max_depth, depth=depth + 1)


def cmd_migrate(subcmd):
    """Proxy to migrate.py."""
    migrate_script = VAULT_DIR / "migrate.py"
    subprocess.run([sys.executable, str(migrate_script), subcmd])


def _human_size(size):
    if size is None:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "scan":
        cmd_scan()
    elif cmd == "list":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(cat)
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("  Usage: python vault.py search <query>")
            sys.exit(1)
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "status":
        cmd_status()
    elif cmd == "tree":
        cmd_tree()
    elif cmd == "migrate":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else "plan"
        cmd_migrate(subcmd)
    else:
        print(f"  Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
