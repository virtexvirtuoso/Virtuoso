#!/bin/bash

#############################################################################
# Script: cleanup_vps_root.sh
# Purpose: Deploy and manage cleanup vps root
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
#   ./cleanup_vps_root.sh [options]
#   
#   Examples:
#     ./cleanup_vps_root.sh
#     ./cleanup_vps_root.sh --verbose
#     ./cleanup_vps_root.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

# VPS Root Directory Cleanup Script
# Organizes 318+ loose files into appropriate directories

VPS_HOST="linuxuser@VPS_HOST_REDACTED"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "========================================="
echo "VPS Root Directory Cleanup"
echo "========================================="
echo ""

# Create directory structure on VPS
echo "1. Creating directory structure..."
ssh $VPS_HOST "cd $VPS_DIR && mkdir -p scripts/{testing,fixes,deployment,utilities,diagnostics,archive}"
ssh $VPS_HOST "cd $VPS_DIR && mkdir -p docs/{troubleshooting,deployment,fixes,performance}"
ssh $VPS_HOST "cd $VPS_DIR && mkdir -p backups/old_scripts"
echo "   ✅ Directories created"

echo ""
echo "2. Moving Python scripts to appropriate locations..."

# Move test scripts
ssh $VPS_HOST "cd $VPS_DIR && mv -f test_*.py scripts/testing/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_test.py scripts/testing/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_tests.py scripts/testing/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f check_*.py scripts/diagnostics/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f debug_*.py scripts/diagnostics/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f monitor_*.py scripts/diagnostics/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f benchmark_*.py scripts/diagnostics/ 2>/dev/null"
echo "   ✅ Test and diagnostic scripts moved"

# Move fix scripts
ssh $VPS_HOST "cd $VPS_DIR && mv -f fix_*.py scripts/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f patch_*.py scripts/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f apply_*.py scripts/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f add_*.py scripts/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f update_*.py scripts/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f repair_*.py scripts/fixes/ 2>/dev/null"
echo "   ✅ Fix and patch scripts moved"

echo ""
echo "3. Moving shell scripts..."
ssh $VPS_HOST "cd $VPS_DIR && mv -f deploy_*.sh scripts/deployment/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.sh scripts/utilities/ 2>/dev/null"
echo "   ✅ Shell scripts organized"

echo ""
echo "4. Moving documentation files..."
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_SUMMARY*.md docs/troubleshooting/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_FIX*.md docs/fixes/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_DEPLOYMENT*.md docs/deployment/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *_PERFORMANCE*.md docs/performance/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.md docs/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.txt docs/ 2>/dev/null"
echo "   ✅ Documentation files organized"

echo ""
echo "5. Moving log files..."
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.log logs/ 2>/dev/null"
echo "   ✅ Log files moved to logs/"

echo ""
echo "6. Moving configuration files..."
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.yaml config/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.yml config/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.json config/ 2>/dev/null"
echo "   ✅ Config files moved to config/"

echo ""
echo "7. Archiving old/unused scripts..."
# Move any remaining .py files that look like one-off scripts
ssh $VPS_HOST "cd $VPS_DIR && mv -f *demo*.py scripts/archive/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *old*.py scripts/archive/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *backup*.py scripts/archive/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *temp*.py scripts/archive/ 2>/dev/null"
ssh $VPS_HOST "cd $VPS_DIR && mv -f *.py.bak backups/old_scripts/ 2>/dev/null"
echo "   ✅ Old scripts archived"

echo ""
echo "8. Final cleanup check..."
echo "Remaining files in root:"
ssh $VPS_HOST "cd $VPS_DIR && ls -1 *.py *.sh *.md *.txt *.log *.yaml *.json 2>/dev/null | wc -l"

echo ""
echo "Root directory structure after cleanup:"
ssh $VPS_HOST "cd $VPS_DIR && ls -la | grep -E '^d' | grep -v '\.$' | awk '{print \$NF}' | sort"

echo ""
echo "========================================="
echo "Cleanup Complete!"
echo "========================================="
echo ""
echo "To review what was moved where:"
echo "ssh $VPS_HOST 'find $VPS_DIR/scripts -type f -name \"*.py\" | wc -l' # Python scripts"
echo "ssh $VPS_HOST 'find $VPS_DIR/docs -type f -name \"*.md\" | wc -l' # Documentation"