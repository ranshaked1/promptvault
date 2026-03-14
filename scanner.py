#!/usr/bin/env python3
"""
Claude Asset Scanner
Scans the local system for all Claude-related files, configs, projects, and tools.
Outputs a structured inventory to asset_registry.json.
"""

import json
import os
import sys
import datetime
import hashlib
import subprocess
from pathlib import Path


# Known locations where Claude assets live
KNOWN_PATHS = {
    # Claude Desktop
    "claude_desktop_config": "~/Library/Application Support/Claude/claude_desktop_config.json",
    "claude_desktop_logs": "~/Library/Logs/Claude",
    "claude_desktop_app_data": "~/Library/Application Support/Claude",
    # Claude Code CLI
    "claude_code_home": "~/.claude",
    "claude_code_settings": "~/.claude/settings.json",
    "claude_code_projects": "~/.claude/projects",
    "claude_code_credentials": "~/.claude/.credentials",
    "claude_code_todos": "~/.claude/todos",
    # VS Code extensions for Claude
    "vscode_extensions": "~/.vscode/extensions",
    "vscode_global_storage": "~/Library/Application Support/Code/User/globalStorage",
    # Cursor (Claude-enabled)
    "cursor_config": "~/Library/Application Support/Cursor/User",
    # Common project locations
    "home_projects": "~/Projects",
    "home_documents": "~/Documents",
    "home_developer": "~/Developer",
    "home_desktop": "~/Desktop",
    "home_repos": "~/repos",
    "home_code": "~/code",
    "home_src": "~/src",
    "home_github": "~/github",
    # NPM global packages (MCP servers often installed here)
    "npm_global": "/usr/local/lib/node_modules",
    "npm_global_alt": "~/.npm-global/lib/node_modules",
    "nvm_default": "~/.nvm/versions/node",
    # Python packages (MCP servers / tools)
    "pip_user_packages": "~/.local/lib",
    "pipx_apps": "~/.local/pipx/venvs",
    # Homebrew
    "homebrew_cellar": "/opt/homebrew/Cellar",
    "homebrew_cellar_intel": "/usr/local/Cellar",
}

# File patterns that indicate Claude-related content
CLAUDE_INDICATORS = [
    "CLAUDE.md",
    ".claude",
    "claude_desktop_config.json",
    "mcp_settings.json",
    "claude-mcp",
    ".mcp.json",
    "mcp.json",
]

# Keywords to search in file names / directory names
CLAUDE_KEYWORDS = [
    "claude",
    "anthropic",
    "mcp-server",
    "mcp_server",
    "mcpserver",
    "promptvault",
]

# MCP-specific patterns
MCP_PATTERNS = [
    "mcp-server-",
    "@modelcontextprotocol",
    "mcp_server_",
]


def expand_path(p):
    return Path(os.path.expanduser(p)).resolve()


def file_hash(filepath, block_size=65536):
    """Quick hash for deduplication."""
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            block = f.read(block_size)
            while block:
                sha.update(block)
                block = f.read(block_size)
        return sha.hexdigest()[:12]
    except (PermissionError, OSError):
        return None


def detect_category(path_str, name):
    """Classify an asset into a category based on its path and name."""
    lower_path = path_str.lower()
    lower_name = name.lower()

    if any(p in lower_path or p in lower_name for p in MCP_PATTERNS):
        return "mcp_server"
    if "skill" in lower_name or "skill" in lower_path:
        return "skill"
    if lower_name in ("claude_desktop_config.json", "settings.json", ".credentials"):
        return "cli_config"
    if any(lower_name.endswith(ext) for ext in (".json", ".yaml", ".toml")) and "config" in lower_path:
        return "cli_config"
    if "hook" in lower_name or "hook" in lower_path:
        return "hook"
    if lower_name == "claude.md" or lower_name == ".claude":
        return "project"
    if "prompt" in lower_name:
        return "prompt"
    if any(lower_name.endswith(ext) for ext in (".py", ".js", ".ts", ".sh")):
        return "automation"
    return "other"


def scan_known_paths():
    """Check all known Claude-related paths."""
    results = []
    for label, path_str in KNOWN_PATHS.items():
        full_path = expand_path(path_str)
        if full_path.exists():
            results.append({
                "name": label,
                "path": str(full_path),
                "type": "directory" if full_path.is_dir() else "file",
                "category": detect_category(str(full_path), label),
                "source": "known_path",
                "exists": True,
                "size_bytes": full_path.stat().st_size if full_path.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(
                    full_path.stat().st_mtime
                ).isoformat() if full_path.exists() else None,
            })
    return results


def scan_claude_desktop_config():
    """Parse Claude Desktop config for MCP servers."""
    results = []
    config_path = expand_path("~/Library/Application Support/Claude/claude_desktop_config.json")
    if not config_path.exists():
        return results

    try:
        with open(config_path) as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})
        for name, server_config in mcp_servers.items():
            command = server_config.get("command", "")
            args = server_config.get("args", [])
            results.append({
                "name": f"mcp:{name}",
                "path": str(config_path),
                "type": "mcp_server_entry",
                "category": "mcp_server",
                "source": "claude_desktop_config",
                "details": {
                    "command": command,
                    "args": args,
                    "env": list(server_config.get("env", {}).keys()),
                },
            })
    except (json.JSONDecodeError, PermissionError):
        pass
    return results


def scan_claude_code_config():
    """Parse Claude Code settings and project configs."""
    results = []
    settings_path = expand_path("~/.claude/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                settings = json.load(f)
            results.append({
                "name": "claude_code_settings",
                "path": str(settings_path),
                "type": "config_file",
                "category": "cli_config",
                "source": "claude_code",
                "details": {
                    "keys": list(settings.keys()),
                },
            })
        except (json.JSONDecodeError, PermissionError):
            pass

    # Scan project-specific configs
    projects_dir = expand_path("~/.claude/projects")
    if projects_dir.exists():
        for project_path in projects_dir.rglob("*"):
            if project_path.is_file():
                results.append({
                    "name": f"project_config:{project_path.name}",
                    "path": str(project_path),
                    "type": "project_config",
                    "category": "project",
                    "source": "claude_code_projects",
                    "size_bytes": project_path.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(
                        project_path.stat().st_mtime
                    ).isoformat(),
                })

    return results


def scan_filesystem_for_claude_files(search_dirs=None, max_depth=4):
    """Walk common directories looking for Claude-related files and projects."""
    results = []
    if search_dirs is None:
        home = Path.home()
        search_dirs = [
            home / "Projects",
            home / "Documents",
            home / "Developer",
            home / "Desktop",
            home / "repos",
            home / "code",
            home / "src",
            home / "github",
            home / "work",
            home,  # shallow scan of home
        ]

    visited = set()
    for search_dir in search_dirs:
        search_dir = Path(search_dir)
        if not search_dir.exists() or str(search_dir) in visited:
            continue
        visited.add(str(search_dir))

        is_home = search_dir == Path.home()
        effective_depth = 2 if is_home else max_depth

        for root, dirs, files in os.walk(search_dir):
            depth = len(Path(root).relative_to(search_dir).parts)
            if depth >= effective_depth:
                dirs.clear()
                continue

            # Skip hidden dirs, node_modules, etc. (except .claude)
            dirs[:] = [
                d for d in dirs
                if not (d.startswith(".") and d != ".claude")
                and d not in ("node_modules", "__pycache__", "venv", ".venv", "env", ".git", "dist", "build")
            ]

            # Check for Claude indicator files
            for indicator in CLAUDE_INDICATORS:
                if indicator in files or indicator in dirs:
                    results.append({
                        "name": Path(root).name,
                        "path": str(Path(root)),
                        "type": "project_directory",
                        "category": "project",
                        "source": "filesystem_scan",
                        "indicator": indicator,
                        "modified": datetime.datetime.fromtimestamp(
                            Path(root).stat().st_mtime
                        ).isoformat(),
                    })
                    break

            # Check for Claude-related filenames
            for fname in files:
                lower_fname = fname.lower()
                if any(kw in lower_fname for kw in CLAUDE_KEYWORDS):
                    fpath = Path(root) / fname
                    results.append({
                        "name": fname,
                        "path": str(fpath),
                        "type": "file",
                        "category": detect_category(str(fpath), fname),
                        "source": "filesystem_scan",
                        "size_bytes": fpath.stat().st_size if fpath.exists() else None,
                        "modified": datetime.datetime.fromtimestamp(
                            fpath.stat().st_mtime
                        ).isoformat() if fpath.exists() else None,
                    })

            # Check directory names
            for dname in list(dirs):
                lower_dname = dname.lower()
                if any(kw in lower_dname for kw in CLAUDE_KEYWORDS):
                    dpath = Path(root) / dname
                    results.append({
                        "name": dname,
                        "path": str(dpath),
                        "type": "directory",
                        "category": detect_category(str(dpath), dname),
                        "source": "filesystem_scan",
                        "modified": datetime.datetime.fromtimestamp(
                            dpath.stat().st_mtime
                        ).isoformat() if dpath.exists() else None,
                    })

    return results


def scan_npm_global_for_mcp():
    """Find MCP servers installed globally via npm."""
    results = []
    try:
        output = subprocess.run(
            ["npm", "list", "-g", "--json", "--depth=0"],
            capture_output=True, text=True, timeout=15
        )
        if output.stdout:
            data = json.loads(output.stdout)
            deps = data.get("dependencies", {})
            for pkg_name, pkg_info in deps.items():
                if any(p in pkg_name for p in MCP_PATTERNS + CLAUDE_KEYWORDS):
                    results.append({
                        "name": pkg_name,
                        "path": pkg_info.get("resolved", "npm-global"),
                        "type": "npm_package",
                        "category": "mcp_server" if "mcp" in pkg_name.lower() else "tool",
                        "source": "npm_global",
                        "details": {
                            "version": pkg_info.get("version"),
                        },
                    })
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return results


def scan_pip_for_claude():
    """Find Claude/MCP related Python packages."""
    results = []
    try:
        output = subprocess.run(
            ["pip3", "list", "--format=json"],
            capture_output=True, text=True, timeout=15
        )
        if output.stdout:
            packages = json.loads(output.stdout)
            for pkg in packages:
                name = pkg.get("name", "")
                if any(kw in name.lower() for kw in CLAUDE_KEYWORDS + ["mcp"]):
                    results.append({
                        "name": name,
                        "path": "pip3",
                        "type": "python_package",
                        "category": "mcp_server" if "mcp" in name.lower() else "tool",
                        "source": "pip",
                        "details": {
                            "version": pkg.get("version"),
                        },
                    })
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return results


def scan_git_repos():
    """Find git repos that have Claude-related content."""
    results = []
    home = Path.home()
    search_dirs = [
        home / "Projects",
        home / "Documents",
        home / "Developer",
        home / "repos",
        home / "code",
        home / "src",
        home / "github",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for root, dirs, files in os.walk(search_dir):
            depth = len(Path(root).relative_to(search_dir).parts)
            if depth >= 3:
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]

            if ".git" in os.listdir(root):
                # Check if this repo has Claude-related files
                has_claude = any(
                    ind in files or ind in os.listdir(root)
                    for ind in CLAUDE_INDICATORS
                )
                if has_claude:
                    # Get remote URL
                    remote_url = None
                    try:
                        result = subprocess.run(
                            ["git", "-C", root, "remote", "get-url", "origin"],
                            capture_output=True, text=True, timeout=5
                        )
                        remote_url = result.stdout.strip() if result.returncode == 0 else None
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                    results.append({
                        "name": Path(root).name,
                        "path": str(root),
                        "type": "git_repo",
                        "category": "project",
                        "source": "git_scan",
                        "details": {
                            "remote_url": remote_url,
                            "has_claude_md": "CLAUDE.md" in files,
                            "has_dot_claude": ".claude" in os.listdir(root),
                        },
                        "modified": datetime.datetime.fromtimestamp(
                            Path(root).stat().st_mtime
                        ).isoformat(),
                    })
                dirs.clear()  # Don't recurse into git repos

    return results


def deduplicate(assets):
    """Remove duplicate entries based on path."""
    seen = set()
    unique = []
    for asset in assets:
        key = asset.get("path", "") + ":" + asset.get("name", "")
        if key not in seen:
            seen.add(key)
            unique.append(asset)
    return unique


def run_full_scan(output_file=None):
    """Run all scanners and produce a unified registry."""
    if output_file is None:
        output_file = Path(__file__).parent / "asset_registry.json"

    print("=" * 60)
    print("  Claude Asset Scanner")
    print("=" * 60)

    all_assets = []

    scanners = [
        ("Known Claude paths", scan_known_paths),
        ("Claude Desktop config (MCP servers)", scan_claude_desktop_config),
        ("Claude Code config & projects", scan_claude_code_config),
        ("Filesystem (Claude files & projects)", scan_filesystem_for_claude_files),
        ("npm global packages", scan_npm_global_for_mcp),
        ("pip packages", scan_pip_for_claude),
        ("Git repos with Claude content", scan_git_repos),
    ]

    for label, scanner_fn in scanners:
        print(f"\n  Scanning: {label}...", end=" ", flush=True)
        try:
            results = scanner_fn()
            all_assets.extend(results)
            print(f"found {len(results)} item(s)")
        except Exception as e:
            print(f"ERROR: {e}")

    all_assets = deduplicate(all_assets)

    # Build category summary
    category_counts = {}
    for asset in all_assets:
        cat = asset.get("category", "other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    registry = {
        "version": "1.0.0",
        "last_scan": datetime.datetime.now().isoformat(),
        "scan_host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "total_assets": len(all_assets),
        "category_summary": category_counts,
        "assets": all_assets,
    }

    with open(output_file, "w") as f:
        json.dump(registry, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"  Scan complete: {len(all_assets)} assets found")
    print(f"  Registry saved to: {output_file}")
    print(f"\n  Category breakdown:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat:20s} {count}")
    print(f"{'=' * 60}")

    return registry


if __name__ == "__main__":
    output = None
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
    run_full_scan(output)
