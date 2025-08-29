#!/bin/bash

# Notion MCP Server Setup Script
# This script helps configure the Notion MCP server for Claude

echo "=================================="
echo "   Notion MCP Server Setup"
echo "=================================="
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js first."
    exit 1
fi

# Check if Notion MCP server is installed
echo "1. Checking Notion MCP server installation..."
if npm list -g @notionhq/notion-mcp-server 2>/dev/null | grep -q notion-mcp-server; then
    echo "✅ Notion MCP server is already installed"
else
    echo "📦 Installing Notion MCP server globally..."
    npm install -g @notionhq/notion-mcp-server
    if [ $? -eq 0 ]; then
        echo "✅ Notion MCP server installed successfully"
    else
        echo "❌ Failed to install Notion MCP server"
        exit 1
    fi
fi

echo ""
echo "2. Notion API Token Setup"
echo "========================="
echo ""
echo "To get your Notion API token:"
echo "  1. Go to https://www.notion.so/my-integrations"
echo "  2. Click '+ New integration'"
echo "  3. Give it a name (e.g., 'Claude MCP')"
echo "  4. Select the workspace you want to connect"
echo "  5. Click 'Submit'"
echo "  6. Copy the 'Internal Integration Token' (starts with 'secret_')"
echo ""
echo "  7. Share pages with your integration:"
echo "     - Open any Notion page you want Claude to access"
echo "     - Click '...' menu → 'Add connections'"
echo "     - Search for and select your integration"
echo ""

# Ask for Notion token
read -p "Enter your Notion Integration Token (or press Enter to skip): " NOTION_TOKEN

if [ -z "$NOTION_TOKEN" ]; then
    echo ""
    echo "⚠️  No token provided. You'll need to add it manually later."
    NOTION_TOKEN="YOUR_NOTION_TOKEN_HERE"
else
    echo "✅ Token received"
fi

echo ""
echo "3. Claude Configuration"
echo "======================="
echo ""
echo "Add this to your Claude MCP settings:"
echo ""
echo "Method 1: Using Claude's MCP menu"
echo "  1. In Claude desktop app, go to Settings"
echo "  2. Click on 'MCP Servers' or 'Developer' section"
echo "  3. Add a new server with:"
echo "     - Name: notion"
echo "     - Command: npx"
echo "     - Arguments: @notionhq/notion-mcp-server"
echo "     - Environment variable: NOTION_TOKEN=$NOTION_TOKEN"
echo ""
echo "Method 2: Using command line (if supported):"
echo "  claude mcp add notion"
echo ""

# Create a test command
echo "4. Testing the Setup"
echo "==================="
echo ""
echo "Once configured, restart Claude and test with:"
echo "  'List my Notion pages' - to see available pages"
echo "  'Read page [page_name]' - to read a specific page"
echo ""

# Save configuration for reference
CONFIG_FILE="$HOME/.notion_mcp_config"
echo "# Notion MCP Configuration" > "$CONFIG_FILE"
echo "NOTION_TOKEN=$NOTION_TOKEN" >> "$CONFIG_FILE"
echo "# Integration created on: $(date)" >> "$CONFIG_FILE"
echo ""
echo "Configuration saved to: $CONFIG_FILE"

echo ""
echo "=================================="
echo "   Setup Instructions Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Add the configuration to Claude (see Method 1 above)"
echo "2. Restart Claude desktop app"
echo "3. The Notion tools should now be available"
echo ""
echo "If you encounter issues:"
echo "- Ensure your Notion token starts with 'secret_'"
echo "- Make sure you've shared pages with your integration"
echo "- Check that Claude has been restarted after configuration"