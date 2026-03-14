#!/usr/bin/env python3
"""
Claude Asset Scanner
Scans the local system for all Claude-related files, configs, projects, and tools.
Works on both macOS and Linux.
Outputs a structured inventory to registry.json.
"""

import json
import os
import sys
import platform
import datetime
import subprocess
from pathlib import Path


IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
HOME = Path.home()

# ── Known locations where Claude assets live ─────────────────────────────────

KNOWN_PATHS_COMMON = {
    "claude_code_home": "~/.claude",
    "claude_code_settings": "~/.claude/settings.json",
    "claude_code_projects": "~/.claude/projects",
    "claude_code_credentials": "~/.claude/.credentials",
    "claude_code_skills": "~/.claude/skills",
    "claude_code_plugins": "~/.claude/plugins",
    "claude_code_backups": "~/.claude/backups",
    "claude_json": "~/.claude.json",
    "vscode_extensions": "~/.vscode/extensions",
}

KNOWN_PATHS_MAC = {
    "claude_desktop_config": "~/Library/Application Support/Claude/claude_desktop_config.json",
    "claude_desktop_app_data": "~/Library/Application Support/Claude",
    "claude_desktop_logs": "~/Library/Logs/Claude",
    "vscode_global_storage": "~/Library/Application Support/Code/User/globalStorage",
    "cursor_config": "~/Library/Application Support/Cursor/User",
    "cursor_mcp": "~/Library/Application Support/Cursor/User/globalStorage/anysphere.cursor-mcp",
}

KNOWN_PATHS_LINUX = {
    "vscode_global_storage": "~/.config/Code/User/globalStorage",
    "cursor_config": "~/.config/Cursor/User",
}

# File/dir names that indicate a Claude-managed project
CLAUDE_INDICATORS = [
    "CLAUDE.md", ".claude", "claude_desktop_config.json",
    "mcp_settings.json", ".mcp.json", "mcp.json",
]

# Keywords for matching file/directory names
CLAUDE_KEYWORDS = [
    "claude", "anthropic", "mcp-server", "mcp_server", "mcpserver",
]

MCP_PATTERNS = ["mcp-server-", "@modelcontextprotocol", "mcp_server_"]

# Directories to search for scattered projects
PROJECT_SEARCH_DIRS = [
    "~/Projects", "~/Documents", "~/Developer", "~/Desktop",
    "~/repos", "~/code", "~/src", "~/github", "~/work",
]


def expand(p):
    return Path(os.path.expanduser(p)).resolve()


def safe_stat(p):
    try:
        return p.stat()
    except (PermissionError, OSError):
        return None


def detect_category(path_str, name):
    lp, ln = path_str.lower(), name.lower()
    if any(p in lp or p in ln for p in MCP_PATTERNS):
        return "mcp_server"
    if "skill" in ln or "/skills/" in lp:
        return "skill"
    if ln in ("claude_desktop_config.json", "settings.json", ".credentials", ".claude.json"):
        return "config"
    if "config" in lp and ln.endswith((".json", ".yaml", ".toml")):
        return "config"
    if "hook" in ln or "/hooks/" in lp:
        return "hook"
    if "plugin" in ln or "/plugins/" in lp:
        return "config"
    if ln == "claude.md" or (ln == ".claude" and os.path.isdir(path_str)):
        return "project"
    if "prompt" in ln:
        return "prompt"
    if ln.endswith((".py", ".js", ".ts", ".sh")):
        return "script"
    return "other"


def _asset(name, path, asset_type, category, source, **extra):
    """Build a standardized asset dict."""
    p = Path(path)
    st = safe_stat(p)
    entry = {
        "name": name,
        "path": str(p),
        "type": asset_type,
        "category": category,
        "source": source,
    }
    if st:
        entry["size_bytes"] = st.st_size if p.is_file() else None
        entry["modified"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat()
    entry.update(extra)
    return entry


# ── Scanners ─────────────────────────────────────────────────────────────────

def scan_known_paths():
    paths = {**KNOWN_PATHS_COMMON}
    if IS_MAC:
        paths.update(KNOWN_PATHS_MAC)
    if IS_LINUX:
        paths.update(KNOWN_PATHS_LINUX)

    results = []
    for label, path_str in paths.items():
        fp = expand(path_str)
        if fp.exists():
            results.append(_asset(
                label, fp,
                "directory" if fp.is_dir() else "file",
                detect_category(str(fp), label),
                "known_path",
            ))
    return results


def scan_claude_desktop_mcp():
    """Extract MCP server entries from Claude Desktop config."""
    config_path = expand("~/Library/Application Support/Claude/claude_desktop_config.json")
    if not config_path.exists():
        return []

    results = []
    try:
        config = json.loads(config_path.read_text())
        for name, srv in config.get("mcpServers", {}).items():
            results.append(_asset(
                f"mcp:{name}", str(config_path),
                "mcp_server_entry", "mcp_server", "claude_desktop_config",
                details={"command": srv.get("command", ""), "args": srv.get("args", []),
                         "env_keys": list(srv.get("env", {}).keys())},
            ))
    except (json.JSONDecodeError, PermissionError):
        pass
    return results


def scan_dot_claude():
    """Deep scan of ~/.claude/ for skills, hooks, plugins, configs."""
    dot_claude = expand("~/.claude")
    if not dot_claude.exists():
        return []

    results = []
    for item in dot_claude.rglob("*"):
        if item.is_file() and ".git" not in item.parts:
            rel = item.relative_to(dot_claude)
            results.append(_asset(
                str(rel), item, "file",
                detect_category(str(item), item.name),
                "dot_claude",
            ))
    return results


def scan_home_for_claude_projects():
    """Walk home + common dirs looking for Claude-related projects & files."""
    results = []
    search_dirs = [expand(d) for d in PROJECT_SEARCH_DIRS] + [HOME]
    visited = set()

    for search_dir in search_dirs:
        if not search_dir.exists() or str(search_dir) in visited:
            continue
        visited.add(str(search_dir))

        is_home = (search_dir == HOME)
        max_depth = 2 if is_home else 4

        for root, dirs, files in os.walk(search_dir):
            depth = len(Path(root).relative_to(search_dir).parts)
            if depth >= max_depth:
                dirs.clear()
                continue

            dirs[:] = [
                d for d in dirs
                if not (d.startswith(".") and d != ".claude")
                and d not in ("node_modules", "__pycache__", "venv", ".venv",
                              "env", ".git", "dist", "build", "Claude")
            ]

            # Check for indicator files/dirs (skip home dir itself)
            root_path = Path(root)
            if root_path != HOME:
                for indicator in CLAUDE_INDICATORS:
                    if indicator in files or indicator in dirs:
                        results.append(_asset(
                            root_path.name, root, "project_directory", "project",
                            "filesystem_scan", indicator=indicator,
                        ))
                        break

            # Check for claude-related file names
            for fname in files:
                if any(kw in fname.lower() for kw in CLAUDE_KEYWORDS):
                    fpath = Path(root) / fname
                    results.append(_asset(
                        fname, fpath, "file",
                        detect_category(str(fpath), fname),
                        "filesystem_scan",
                    ))

            # Check for claude-related directory names
            for dname in list(dirs):
                if any(kw in dname.lower() for kw in CLAUDE_KEYWORDS):
                    dpath = Path(root) / dname
                    results.append(_asset(
                        dname, dpath, "directory",
                        detect_category(str(dpath), dname),
                        "filesystem_scan",
                    ))

    return results


def scan_npm_global():
    """Find Claude/MCP npm packages."""
    results = []
    try:
        out = subprocess.run(
            ["npm", "list", "-g", "--json", "--depth=0"],
            capture_output=True, text=True, timeout=15,
        )
        if out.stdout:
            deps = json.loads(out.stdout).get("dependencies", {})
            for pkg, info in deps.items():
                if any(p in pkg.lower() for p in MCP_PATTERNS + CLAUDE_KEYWORDS):
                    results.append(_asset(
                        pkg, info.get("resolved", "npm-global"),
                        "npm_package",
                        "mcp_server" if "mcp" in pkg.lower() else "tool",
                        "npm_global",
                        details={"version": info.get("version")},
                    ))
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return results


def scan_pip():
    """Find Claude/MCP pip packages."""
    results = []
    for pip_cmd in ["pip3", "pip"]:
        try:
            out = subprocess.run(
                [pip_cmd, "list", "--format=json"],
                capture_output=True, text=True, timeout=15,
            )
            if out.stdout:
                for pkg in json.loads(out.stdout):
                    name = pkg.get("name", "")
                    if any(kw in name.lower() for kw in CLAUDE_KEYWORDS + ["mcp"]):
                        results.append(_asset(
                            name, pip_cmd, "python_package",
                            "mcp_server" if "mcp" in name.lower() else "tool",
                            "pip",
                            details={"version": pkg.get("version")},
                        ))
            break  # Use first pip that works
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            continue
    return results


def scan_brew():
    """Find Claude/MCP homebrew packages (macOS only)."""
    if not IS_MAC:
        return []
    results = []
    try:
        out = subprocess.run(
            ["brew", "list", "--formula", "-1"],
            capture_output=True, text=True, timeout=15,
        )
        for line in out.stdout.strip().splitlines():
            if any(kw in line.lower() for kw in CLAUDE_KEYWORDS + ["mcp"]):
                results.append(_asset(
                    line.strip(), "homebrew", "brew_package", "tool", "brew",
                ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return results


def scan_git_repos_with_claude():
    """Find git repos containing Claude indicators."""
    results = []
    search_dirs = [expand(d) for d in PROJECT_SEARCH_DIRS]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for root, dirs, files in os.walk(search_dir):
            depth = len(Path(root).relative_to(search_dir).parts)
            if depth >= 3:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in ("node_modules", "__pycache__")]

            try:
                entries = os.listdir(root)
            except PermissionError:
                continue

            if ".git" in entries:
                has_claude = any(ind in entries for ind in CLAUDE_INDICATORS)
                if has_claude:
                    remote_url = None
                    try:
                        r = subprocess.run(
                            ["git", "-C", root, "remote", "get-url", "origin"],
                            capture_output=True, text=True, timeout=5,
                        )
                        remote_url = r.stdout.strip() if r.returncode == 0 else None
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                    results.append(_asset(
                        Path(root).name, root, "git_repo", "project", "git_scan",
                        details={"remote_url": remote_url,
                                 "has_claude_md": "CLAUDE.md" in entries,
                                 "has_dot_claude": ".claude" in entries},
                    ))
                dirs.clear()

    return results


# ── Main ─────────────────────────────────────────────────────────────────────

def deduplicate(assets):
    seen = set()
    unique = []
    for a in assets:
        key = a["path"] + ":" + a["name"]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def run_full_scan(output_file=None):
    if output_file is None:
        output_file = Path(__file__).parent / "registry.json"

    print("=" * 60)
    print("  Claude Asset Scanner")
    print(f"  Platform: {'macOS' if IS_MAC else 'Linux' if IS_LINUX else platform.system()}")
    print(f"  Home: {HOME}")
    print("=" * 60)

    all_assets = []
    scanners = [
        ("Known Claude paths", scan_known_paths),
        ("Claude Desktop MCP servers", scan_claude_desktop_mcp),
        ("~/.claude/ deep scan", scan_dot_claude),
        ("Home directory projects", scan_home_for_claude_projects),
        ("npm global packages", scan_npm_global),
        ("pip packages", scan_pip),
        ("Homebrew packages", scan_brew),
        ("Git repos with Claude content", scan_git_repos_with_claude),
    ]

    for label, fn in scanners:
        print(f"\n  Scanning: {label}...", end=" ", flush=True)
        try:
            results = fn()
            all_assets.extend(results)
            print(f"found {len(results)}")
        except Exception as e:
            print(f"ERROR: {e}")

    all_assets = deduplicate(all_assets)

    cats = {}
    for a in all_assets:
        c = a.get("category", "other")
        cats[c] = cats.get(c, 0) + 1

    registry = {
        "version": "1.0.0",
        "last_scan": datetime.datetime.now().isoformat(),
        "platform": platform.system(),
        "home": str(HOME),
        "total_assets": len(all_assets),
        "category_summary": cats,
        "assets": all_assets,
    }

    with open(output_file, "w") as f:
        json.dump(registry, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"  Scan complete: {len(all_assets)} assets found")
    print(f"  Registry saved to: {output_file}")
    print(f"\n  Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:20s} {count}")
    print("=" * 60)

    return registry


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    run_full_scan(out)
