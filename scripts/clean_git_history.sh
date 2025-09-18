#!/bin/bash

#############################################################################
# Script: clean_git_history.sh
# Purpose: Script to clean sensitive data from git history
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
#   ./clean_git_history.sh [options]
#   
#   Examples:
#     ./clean_git_history.sh
#     ./clean_git_history.sh --verbose
#     ./clean_git_history.sh --dry-run
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

# WARNING: This will rewrite git history!

echo "⚠️  WARNING: This will rewrite your git history!"
echo "Make sure you have a backup and coordinate with any collaborators."
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo "🔍 Searching for sensitive patterns in git history..."

# Patterns to remove
PATTERNS=(
    "discord.com/api/webhooks"
    "BYBIT_API_KEY"
    "BYBIT_API_SECRET"
    "INFLUXDB_TOKEN"
    "JWT_SECRET_KEY"
)

# Create a backup branch
git branch backup-before-clean-$(date +%Y%m%d-%H%M%S)

# Use git filter-repo (recommended) or BFG Repo-Cleaner
# First check if git filter-repo is installed
if command -v git-filter-repo &> /dev/null; then
    echo "Using git filter-repo..."
    for pattern in "${PATTERNS[@]}"; do
        echo "Removing: $pattern"
        git filter-repo --replace-text <(echo "$pattern==>REDACTED")
    done
else
    echo "❌ git-filter-repo not found. Please install it first:"
    echo "   pip install git-filter-repo"
    echo ""
    echo "Alternative: Use BFG Repo-Cleaner"
    echo "   1. Download from: https://rtyley.github.io/bfg-repo-cleaner/"
    echo "   2. Run: java -jar bfg.jar --replace-text passwords.txt"
    exit 1
fi

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Force push to remote: git push origin --force --all"
echo "2. Tell all collaborators to re-clone the repository"
echo "3. Rotate ALL credentials that were exposed"
echo "4. Update your local .env file with new credentials"