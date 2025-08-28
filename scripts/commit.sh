#!/bin/bash

#############################################################################
# Script: commit.sh
# Purpose: Create Git commits with virtuoso_dev attribution
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2024-08-15
# Modified: 2024-08-28
#############################################################################
#
# Description:
#   Creates Git commits with automatic "Developed by virtuoso_dev" attribution
#   appended to the commit message. Useful for maintaining consistent commit
#   attribution across the development team.
#
# Usage:
#   ./scripts/commit.sh "Your commit message"
#
# Arguments:
#   message    Commit message (required, in quotes)
#
# Examples:
#   ./scripts/commit.sh "Add new trading feature"
#   ./scripts/commit.sh "Fix dashboard performance issue"
#
# Exit Codes:
#   0 - Commit created successfully
#   1 - Missing commit message
#   2 - Git commit failed
#
# Notes:
#   - Commit message is required and should be descriptive
#   - Attribution is automatically appended
#   - Ensure changes are staged before running
#
#############################################################################

if [ -z "$1" ]; then
    echo "Usage: $0 \"Commit message\""
    exit 1
fi

git commit -m "$1

Developed by virtuoso_dev"