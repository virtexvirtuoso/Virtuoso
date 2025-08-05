#!/bin/bash
# Fix Claude Code "Missing API key" issue in SSH sessions
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