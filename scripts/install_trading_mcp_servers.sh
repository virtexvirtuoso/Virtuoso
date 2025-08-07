#!/bin/bash

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