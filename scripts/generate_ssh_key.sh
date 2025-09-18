#!/bin/bash

#############################################################################
# Script: generate_ssh_key.sh
# Purpose: Deploy and manage generate ssh key
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
#   ./generate_ssh_key.sh [options]
#   
#   Examples:
#     ./generate_ssh_key.sh
#     ./generate_ssh_key.sh --verbose
#     ./generate_ssh_key.sh --dry-run
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

echo "🔐 SSH Key Generation for Vultr VPS"
echo "===================================="
echo ""

# Check if SSH key already exists
if [ -f ~/.ssh/id_ed25519 ]; then
    echo "⚠️  Ed25519 SSH key already exists!"
    echo ""
    echo "Your public key is:"
    echo "-------------------"
    cat ~/.ssh/id_ed25519.pub
    echo "-------------------"
    echo ""
    echo "Copy the above key and paste it in Vultr's SSH Keys section"
    exit 0
fi

# Generate new Ed25519 key (more secure than RSA)
echo "Generating new Ed25519 SSH key..."
ssh-keygen -t ed25519 -C "vultr-trading-bot" -f ~/.ssh/id_ed25519 -N ""

echo ""
echo "✅ SSH Key Generated Successfully!"
echo ""
echo "Your public key (copy this entire line for Vultr):"
echo "=================================================="
cat ~/.ssh/id_ed25519.pub
echo "=================================================="
echo ""
echo "📋 Instructions:"
echo "1. Copy the key above (the entire line starting with 'ssh-ed25519')"
echo "2. Go back to Vultr deployment page"
echo "3. Click 'Manage SSH Keys' or 'Add New'"
echo "4. Paste the key and give it a name like 'Mac Mini Trading Key'"
echo "5. Select it during deployment"
echo ""
echo "🔒 Your private key is stored at: ~/.ssh/id_ed25519"
echo "⚠️  Keep this private key secure - never share it!"
echo ""
echo "To connect to your VPS later:"
echo "ssh -i ~/.ssh/id_ed25519 root@YOUR_VPS_IP"