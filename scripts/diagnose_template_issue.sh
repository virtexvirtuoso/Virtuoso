#!/bin/bash

#############################################################################
# Script: diagnose_template_issue.sh
# Purpose: Deploy and manage diagnose template issue
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
#   ./diagnose_template_issue.sh [options]
#   
#   Examples:
#     ./diagnose_template_issue.sh
#     ./diagnose_template_issue.sh --verbose
#     ./diagnose_template_issue.sh --dry-run
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

echo "🔍 Diagnosing Template Configuration Issue"
echo "=========================================="

cd ~/trading/Virtuoso_ccxt

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\n${BLUE}1. Checking ReportManager code:${NC}"
echo "-----------------------------------"
echo "Lines 60-110 of report_manager.py:"
cat -n src/core/reporting/report_manager.py | sed -n '60,110p'

echo -e "\n${BLUE}2. Checking how SignalGenerator calls ReportManager:${NC}"
echo "------------------------------------------------------"
grep -B10 -A5 "ReportManager(config)" src/signal_generation/signal_generator.py

echo -e "\n${BLUE}3. Analyzing config structure:${NC}"
echo "--------------------------------"
python3 << 'PYTHON_EOF'
import yaml
import json
import os

print("Loading config.yaml...")
try:
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print("\nFull reporting config:")
    print(json.dumps(config.get('reporting', {}), indent=2))
    
    print("\nChecking specific keys:")
    reporting = config.get('reporting', {})
    print(f"  template_dir: {reporting.get('template_dir')}")
    print(f"  template_directory: {reporting.get('template_directory')}")
    
    print("\nChecking if paths exist:")
    for key in ['template_dir', 'template_directory']:
        path = reporting.get(key)
        if path:
            exists = os.path.exists(path)
            print(f"  {key} = '{path}' -> Exists: {exists}")
            if exists:
                print(f"    Contents: {os.listdir(path)[:5]}...")
                
except Exception as e:
    print(f"Error loading config: {e}")
PYTHON_EOF

echo -e "\n${BLUE}4. Checking ReportManager __init__ method:${NC}"
echo "-------------------------------------------"
grep -A30 "def __init__" src/core/reporting/report_manager.py | grep -n "."

echo -e "\n${BLUE}5. Checking SignalGenerator config handling:${NC}"
echo "----------------------------------------------"
echo "How SignalGenerator loads config:"
grep -B20 -A10 "class SignalGenerator" src/signal_generation/signal_generator.py | grep -E "(config =|self.config|config\[|config\.get)"

echo -e "\n${BLUE}6. Checking what config SignalGenerator passes:${NC}"
echo "--------------------------------------------------"
python3 << 'PYTHON_EOF'
# Let's simulate what SignalGenerator does
import yaml

with open('config/config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)

print("SignalGenerator might be passing:")
print("1. Full config:", 'reporting' in full_config)
print("2. Just reporting section:", type(full_config.get('reporting', {})))

# Check if it's a nested access issue
if 'reporting' in full_config:
    reporting_config = full_config['reporting']
    print("\nIf passing full config, ReportManager gets:")
    print(f"  config.get('reporting') = {type(reporting_config)}")
    print(f"  config.get('reporting').get('template_dir') = {reporting_config.get('template_dir')}")
    
print("\nIf passing just reporting section, ReportManager gets:")
print(f"  config.get('template_dir') = {full_config.get('reporting', {}).get('template_dir')}")
PYTHON_EOF

echo -e "\n${BLUE}7. Quick fix test:${NC}"
echo "-------------------"
echo "Testing if the issue is nested config access..."

# Create a test script
cat > test_config_access.py << 'EOF'
import yaml

with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test different ways ReportManager might access config
print("Testing config access patterns:")
print(f"1. config.get('template_dir'): {config.get('template_dir')}")
print(f"2. config.get('reporting', {}).get('template_dir'): {config.get('reporting', {}).get('template_dir')}")
print(f"3. config['reporting']['template_dir']: {config['reporting']['template_dir']}")

# What SignalGenerator likely passes
reporting_config = config.get('reporting', {})
print(f"\n4. If SignalGenerator passes reporting section:")
print(f"   reporting_config.get('template_dir'): {reporting_config.get('template_dir')}")
EOF

python3 test_config_access.py
rm test_config_access.py

echo -e "\n${GREEN}=========================================="
echo "Diagnosis Complete!"
echo "==========================================${NC}"
echo ""
echo "Based on the output above, we can determine:"
echo "1. What config structure ReportManager expects"
echo "2. What SignalGenerator is actually passing"
echo "3. Why the template directory isn't being found"
echo ""
echo "Look for mismatches between what's passed and what's expected!"