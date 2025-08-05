#!/bin/bash

# Install all official MCP demonstration servers globally
# These will be available for all projects

# Use the full path to claude
CLAUDE_CMD="/Users/ffv_macmini/.claude/local/claude"

echo "Installing all official MCP servers globally..."
echo "================================================"

# Everything - Reference/test server with prompts, resources, and tools
echo "Installing Everything server..."
"$CLAUDE_CMD" mcp add --scope user everything npx @modelcontextprotocol/server-everything

# Fetch - Web content fetching and conversion for efficient LLM usage
echo "Installing Fetch server..."
"$CLAUDE_CMD" mcp add --scope user fetch npx @modelcontextprotocol/server-fetch

# Filesystem - Secure file operations with configurable access controls
# Using home directory as default, can be modified per project
echo "Installing Filesystem server..."
"$CLAUDE_CMD" mcp add --scope user filesystem npx @modelcontextprotocol/server-filesystem "$HOME"

# Git - Tools to read, search, and manipulate Git repositories
echo "Installing Git server..."
"$CLAUDE_CMD" mcp add --scope user git npx @modelcontextprotocol/server-git

# Memory - Knowledge graph-based persistent memory system
echo "Installing Memory server..."
"$CLAUDE_CMD" mcp add --scope user memory npx @modelcontextprotocol/server-memory

# Sequential Thinking - Dynamic and reflective problem-solving through thought sequences
echo "Installing Sequential Thinking server..."
"$CLAUDE_CMD" mcp add --scope user sequential-thinking npx @modelcontextprotocol/server-sequential-thinking

# Time - Time and timezone conversion capabilities
echo "Installing Time server..."
"$CLAUDE_CMD" mcp add --scope user time npx @modelcontextprotocol/server-time

echo "================================================"
echo "All MCP servers installed globally!"
echo ""
echo "Please restart Claude Code for the changes to take effect."
echo ""
echo "Note: The Filesystem server is configured with your home directory."
echo "You can modify access paths per project as needed."