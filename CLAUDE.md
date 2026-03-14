# Project Memory

## User Environment
- User: ranshaked
- OS: macOS
- Home directory: /Users/ranshaked

## Filesystem MCP Server
- Configured with: `claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /Users/ranshaked/Documents /Users/ranshaked`
- Accessible directories:
  - /Users/ranshaked/Documents
  - /Users/ranshaked (entire home directory)
- Use MCP filesystem tools (not local paths like /home/user/) to access user's files outside the project directory
