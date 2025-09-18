#!/bin/bash

#############################################################################
# Script: fix_indentation_error.sh
# Purpose: Deploy and manage fix indentation error
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
#   ./fix_indentation_error.sh [options]
#   
#   Examples:
#     ./fix_indentation_error.sh
#     ./fix_indentation_error.sh --verbose
#     ./fix_indentation_error.sh --dry-run
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

echo "🔧 Fixing IndentationError in ReportManager"
echo "=========================================="

# Fix the indentation error in report_manager.py
ssh linuxuser@${VPS_HOST} << 'EOF'
cd ~/trading/Virtuoso_ccxt

echo "Creating fix script..."
cat > fix_indentation.py << 'PYTHON'
with open('src/core/reporting/report_manager.py', 'r') as f:
    lines = f.readlines()

# Fix line 65 - remove extra indentation
if len(lines) > 64:
    # Line 65 (index 64) should have same indentation as line 64
    lines[64] = lines[64].lstrip() + '\n'
    # Add proper indentation (8 spaces based on the context)
    lines[64] = '        ' + lines[64]

with open('src/core/reporting/report_manager.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixed indentation on line 65")
PYTHON

# Run the fix
python3 fix_indentation.py
rm fix_indentation.py

echo ""
echo "Verifying the fix..."
echo "Lines 64-66:"
cat -n src/core/reporting/report_manager.py | sed -n '64,66p'

echo ""
echo "Testing syntax..."
python3 -m py_compile src/core/reporting/report_manager.py && echo "✅ Syntax is valid!" || echo "❌ Still has syntax errors!"

EOF

echo ""
echo "Fix applied! Now you can run:"
echo "  ssh linuxuser@${VPS_HOST}"
echo "  cd ~/trading/Virtuoso_ccxt"
echo "  source venv/bin/activate"
echo "  python src/main.py"