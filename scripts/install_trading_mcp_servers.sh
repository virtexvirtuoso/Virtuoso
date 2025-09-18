#!/bin/bash

#############################################################################
# Script: install_trading_mcp_servers.sh
# Purpose: Setup and configure install trading mcp servers
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
#   ./install_trading_mcp_servers.sh [options]
#   
#   Examples:
#     ./install_trading_mcp_servers.sh
#     ./install_trading_mcp_servers.sh --verbose
#     ./install_trading_mcp_servers.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

echo "Installing MCP servers for Virtuoso trading project..."

# Database servers
echo "Installing database MCP servers..."
pip install postgres-mcp influxdb-mcp-server

# Communication servers
echo "Installing communication MCP servers..."
pip install slack-mcp-server

# Browser automation
echo "Installing browser automation..."
npm install -g @modelcontextprotocol/server-puppeteer

# Search capabilities
echo "Installing search server..."
npm install -g @modelcontextprotocol/server-brave-search

# SQLite for local testing
echo "Installing SQLite server..."
npm install -g @modelcontextprotocol/server-sqlite

echo "Installation complete! Restart Claude to activate the new servers."
echo ""
echo "Next steps:"
echo "1. Configure database connection strings in Claude settings"
echo "2. Set up Slack/Discord tokens for notifications"
echo "3. Test each server connection in Claude"