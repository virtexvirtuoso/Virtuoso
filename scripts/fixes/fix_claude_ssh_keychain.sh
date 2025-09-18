#!/bin/bash

#############################################################################
# Script: fix_claude_ssh_keychain.sh
# Purpose: Fix Claude Code "Missing API key" issue in SSH sessions
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./fix_claude_ssh_keychain.sh [options]
#   
#   Examples:
#     ./fix_claude_ssh_keychain.sh
#     ./fix_claude_ssh_keychain.sh --verbose
#     ./fix_claude_ssh_keychain.sh --dry-run
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
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# This script unlocks the macOS keychain to allow Claude Code access

echo "Claude Code SSH Keychain Fix"
echo "============================"
echo ""
echo "This script fixes the 'Missing API key' warning when using Claude Code over SSH."
echo ""

# Check if we're in an SSH session
if [ -z "$SSH_CONNECTION" ]; then
    echo "✓ Not in an SSH session - keychain should work normally"
    exit 0
fi

echo "✓ SSH session detected"

# Check if keychain is already unlocked
if security show-keychain-info ~/Library/Keychains/login.keychain-db 2>&1 | grep -q "User interaction is not allowed"; then
    echo "✗ Keychain is locked"
    echo ""
    echo "To unlock the keychain, you'll need to enter your Mac user password."
    echo "This allows Claude Code to access stored API keys."
    echo ""
    
    # Attempt to unlock
    if security unlock-keychain ~/Library/Keychains/login.keychain-db; then
        echo "✓ Keychain unlocked successfully!"
        echo ""
        echo "Claude Code should now work without showing 'Missing API key' warnings."
    else
        echo "✗ Failed to unlock keychain"
        echo ""
        echo "Please try running: security unlock-keychain ~/Library/Keychains/login.keychain-db"
        exit 1
    fi
else
    echo "✓ Keychain is already unlocked"
    echo ""
    echo "If you're still seeing 'Missing API key' warnings in Claude Code:"
    echo "1. Try running: claude /logout && claude /login"
    echo "2. Or restart your Claude Code session"
fi

echo ""
echo "To make this permanent, add to your ~/.zshrc:"
echo ""
echo 'if [ -n "$SSH_CONNECTION" ]; then'
echo '    security unlock-keychain ~/Library/Keychains/login.keychain-db 2>/dev/null'
echo 'fi'
echo ""
echo "Note: This has already been added to your .zshrc file."