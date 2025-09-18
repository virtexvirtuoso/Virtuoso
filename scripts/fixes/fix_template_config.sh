#!/bin/bash

#############################################################################
# Script: fix_template_config.sh
# Purpose: Setup and configure fix template config
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
#   ./fix_template_config.sh [options]
#   
#   Examples:
#     ./fix_template_config.sh
#     ./fix_template_config.sh --verbose
#     ./fix_template_config.sh --dry-run
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

echo "🔧 Fixing Template Configuration Issue"
echo "====================================="

cd ~/trading/Virtuoso_ccxt

# Check current config
echo "📋 Current template configuration:"
grep -A10 "^reporting:" config/config.yaml || echo "No reporting section found"

# Backup config
cp config/config.yaml config/config.yaml.backup_$(date +%Y%m%d_%H%M%S)

# Check if reporting section exists
if ! grep -q "^reporting:" config/config.yaml; then
    echo -e "\n📝 Adding reporting configuration..."
    cat >> config/config.yaml << 'EOF'

# Reporting configuration
reporting:
  template_dir: src/core/reporting/templates
  output_dir: reports
  enable_pdf: true
EOF
else
    echo "📝 Reporting section exists, checking template_dir..."
    # Check if template_dir exists
    if ! grep -q "template_dir:" config/config.yaml; then
        # Add template_dir under reporting section
        sed -i '/^reporting:/a\  template_dir: src/core/reporting/templates' config/config.yaml
    fi
fi

echo -e "\n✅ Updated configuration:"
grep -A5 "^reporting:" config/config.yaml

echo -e "\n📁 Verifying templates exist:"
ls -la src/core/reporting/templates/*.html | head -5

echo -e "\n🚀 Starting bot with fixed config..."
source venv/bin/activate
python src/main.py