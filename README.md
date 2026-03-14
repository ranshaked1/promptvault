# Claude Vault

Centralized management system for all your Claude-related assets: projects, configs, MCP servers, skills, hooks, and scripts.

This repo **is** your `~/Claude/` folder — the single source of truth for everything Claude on your machine.

## Quick Start

```bash
# 1. Scan your system to find all Claude assets
python vault.py scan

# 2. See what was found
python vault.py status

# 3. Preview the migration plan (dry run, changes nothing)
python vault.py migrate plan

# 4. Execute the migration (moves files + creates symlinks)
python vault.py migrate execute

# 5. Verify everything works
python vault.py migrate verify
```

## Folder Structure

```
~/Claude/                          ← this repo (promptvault)
├── projects/                      ← your automation repos & projects
│   ├── ai-cost-tracker/
│   └── cal-daily-report/
├── configs/                       ← Claude configs (symlinked from original locations)
│   ├── claude-code/               ← symlinked from ~/.claude/
│   └── claude-desktop/            ← symlinked from ~/Library/.../Claude/
├── mcp-servers/                   ← MCP server references & notes
├── skills/                        ← custom skills
├── hooks/                         ← hook scripts
├── scripts/                       ← standalone utility scripts
├── prompts/                       ← saved prompts & templates
├── backups/                       ← config backups
├── scanner.py                     ← system scanner
├── migrate.py                     ← migration tool
├── vault.py                       ← CLI manager
└── registry.json                  ← auto-generated asset inventory
```

## Commands

| Command | Description |
|---------|-------------|
| `python vault.py scan` | Scan system for Claude assets, update registry |
| `python vault.py list [category]` | List all assets (filter: config, project, mcp_server, skill, hook, script, tool) |
| `python vault.py search <query>` | Search assets by name or path |
| `python vault.py status` | Summary dashboard |
| `python vault.py tree` | Show ~/Claude/ folder tree |
| `python vault.py migrate plan` | Preview migration (dry run) |
| `python vault.py migrate execute` | Execute migration |
| `python vault.py migrate verify` | Verify symlinks and structure |

## How Symlinks Work

Some files **must** stay at their original path because Claude reads them from fixed locations:

- `~/.claude/` → Claude Code looks here for settings, skills, hooks
- `~/.claude.json` → Claude Code root config
- `~/Library/Application Support/Claude/` → Claude Desktop config (macOS)

The migration tool **moves** the real files into `~/Claude/configs/` and leaves a **symlink** at the original location. Claude still reads from the same path — it just follows the symlink transparently. Nothing breaks.

## Re-scanning

Run `python vault.py scan` anytime to discover new assets. The registry updates automatically. Use it after installing new MCP servers, creating new projects, or adding skills.
