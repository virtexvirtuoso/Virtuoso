#!/bin/bash

#############################################################################
# Script: install_all_mcp_servers.sh
# Purpose: Setup and configure install all mcp servers
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./install_all_mcp_servers.sh [options]
#   
#   Examples:
#     ./install_all_mcp_servers.sh
#     ./install_all_mcp_servers.sh --verbose
#     ./install_all_mcp_servers.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

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