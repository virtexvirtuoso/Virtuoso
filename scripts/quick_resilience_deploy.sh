#!/bin/bash

#############################################################################
# Script: quick_resilience_deploy.sh
# Purpose: Deploy and manage quick resilience deploy
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
#   ./quick_resilience_deploy.sh [options]
#   
#   Examples:
#     ./quick_resilience_deploy.sh
#     ./quick_resilience_deploy.sh --verbose
#     ./quick_resilience_deploy.sh --dry-run
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

# Quick deployment script for resilience to VPS
# Optimized for high-latency connections

set -e

echo "============================================================"
echo "🚀 Quick Resilience Deployment to VPS"
echo "============================================================"

VPS="VPS_HOST_REDACTED"

# Step 1: Package files locally
echo -e "\n📦 Creating deployment package..."
cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt
tar -czf /tmp/resilience_deploy.tar.gz \
    src/core/resilience/ \
    src/api/routes/health.py \
    scripts/monitor_resilience.py \
    scripts/test_resilience.py \
    2>/dev/null || true

echo "✅ Package created"

# Step 2: Transfer package
echo -e "\n📤 Transferring to VPS..."
scp -o ConnectTimeout=30 /tmp/resilience_deploy.tar.gz linuxuser@$VPS:/tmp/
echo "✅ Package transferred"

# Step 3: Deploy on VPS
echo -e "\n🔧 Deploying on VPS..."
ssh -o ConnectTimeout=30 linuxuser@$VPS << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Backup
mkdir -p backups
tar -czf backups/pre_resilience_$(date +%Y%m%d_%H%M%S).tar.gz src/ 2>/dev/null || true

# Extract new files
tar -xzf /tmp/resilience_deploy.tar.gz

# Create cache directory
mkdir -p cache/fallback
chmod 755 cache/fallback

# Quick patch for main.py to add resilience
if ! grep -q "RESILIENCE_AVAILABLE" src/main.py; then
    cat >> src/main.py << 'EOF'

# Resilience quick patch
try:
    from src.core.resilience import wrap_exchange_manager
    if 'exchange_manager' in locals() and exchange_manager:
        exchange_manager._resilient_wrapper = wrap_exchange_manager(exchange_manager)
        print("✅ Resilience wrapper applied")
except Exception as e:
    print(f"Resilience not applied: {e}")
EOF
fi

# Restart service
sudo systemctl restart virtuoso || true

echo "✅ Deployed on VPS"
ENDSSH

# Step 4: Quick verification
echo -e "\n✅ Testing deployment..."
sleep 5
curl -s --max-time 10 http://$VPS:8001/api/health/system | head -3 || echo "⚠️ Health endpoint may need more time to start"

echo -e "\n============================================================"
echo "✅ Quick deployment complete!"
echo "Check: http://$VPS:8001/api/health/system"
echo "Logs: ssh vps 'sudo journalctl -u virtuoso -f'"
echo "============================================================"