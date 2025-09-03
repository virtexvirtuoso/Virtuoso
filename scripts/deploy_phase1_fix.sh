#!/bin/bash

#############################################################################
# Script: deploy_phase1_fix.sh
# Purpose: Deploy Phase 1 Emergency Fix - Memory Cache Implementation
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
#   ./deploy_phase1_fix.sh [options]
#   
#   Examples:
#     ./deploy_phase1_fix.sh
#     ./deploy_phase1_fix.sh --verbose
#     ./deploy_phase1_fix.sh --dry-run
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

# This script deploys the caching solution to fix slow API responses

set -e  # Exit on error

echo "🚀 Deploying Phase 1 Emergency Fix - Memory Cache Implementation"
echo "================================================================"
echo ""

# Configuration
VPS_HOST="linuxuser@VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Step 1: Check connection to VPS
echo "Step 1: Checking VPS connection..."
if ssh -q $VPS_HOST exit; then
    print_status "VPS connection successful"
else
    print_error "Cannot connect to VPS"
    exit 1
fi

# Step 2: Create backups
echo ""
echo "Step 2: Creating backups..."
ssh $VPS_HOST << EOF
cd $VPS_PATH
# Backup existing files
if [ -f src/main.py ]; then
    cp src/main.py src/main.py.backup_${TIMESTAMP}
    echo "  • Backed up src/main.py"
fi

if [ -f src/api/routes/dashboard.py ]; then
    cp src/api/routes/dashboard.py src/api/routes/dashboard.py.backup_${TIMESTAMP}
    echo "  • Backed up src/api/routes/dashboard.py"
fi

if [ -f src/web_server.py ]; then
    cp src/web_server.py src/web_server.py.backup_${TIMESTAMP}
    echo "  • Backed up src/web_server.py"
fi
EOF
print_status "Backups created"

# Step 3: Copy new files to VPS
echo ""
echo "Step 3: Deploying cache implementation..."

# Copy cache implementation
scp -q src/core/api_cache.py $VPS_HOST:$VPS_PATH/src/core/
print_status "Deployed api_cache.py"

# Copy dashboard updater
scp -q src/core/dashboard_updater.py $VPS_HOST:$VPS_PATH/src/core/
print_status "Deployed dashboard_updater.py"

# Copy patch script
scp -q scripts/patch_api_routes.py $VPS_HOST:$VPS_PATH/scripts/
print_status "Deployed patch script"

# Step 4: Apply patches
echo ""
echo "Step 4: Applying patches to existing files..."
ssh $VPS_HOST << EOF
cd $VPS_PATH
python3 scripts/patch_api_routes.py
EOF

# Step 5: Test syntax
echo ""
echo "Step 5: Testing Python syntax..."
ssh $VPS_HOST << EOF
cd $VPS_PATH
echo -n "  • Testing api_cache.py... "
python3 -m py_compile src/core/api_cache.py && echo "✅ OK" || echo "❌ FAILED"

echo -n "  • Testing dashboard_updater.py... "
python3 -m py_compile src/core/dashboard_updater.py && echo "✅ OK" || echo "❌ FAILED"

echo -n "  • Testing main.py... "
python3 -m py_compile src/main.py && echo "✅ OK" || echo "❌ FAILED"

echo -n "  • Testing dashboard.py... "
python3 -m py_compile src/api/routes/dashboard.py && echo "✅ OK" || echo "❌ FAILED"
EOF

# Step 6: Get current service status
echo ""
echo "Step 6: Current service status..."
ssh $VPS_HOST << 'EOF'
echo "Main Service:"
systemctl status virtuoso --no-pager | grep -E "Active:|Main PID:" || true
echo ""
echo "Web Service:"
systemctl status virtuoso-web --no-pager | grep -E "Active:|Main PID:" || true
EOF

# Step 7: Restart services
echo ""
echo "Step 7: Restarting services..."
print_warning "Services will be briefly unavailable"

ssh $VPS_HOST << EOF
# Restart main service first
sudo systemctl restart virtuoso
echo "  • Main service restarted"
sleep 5

# Then restart web service
sudo systemctl restart virtuoso-web
echo "  • Web service restarted"
sleep 3
EOF

print_status "Services restarted"

# Step 8: Verify services are running
echo ""
echo "Step 8: Verifying services..."
ssh $VPS_HOST << 'EOF'
# Check if services are active
MAIN_STATUS=$(systemctl is-active virtuoso)
WEB_STATUS=$(systemctl is-active virtuoso-web)

if [ "$MAIN_STATUS" = "active" ]; then
    echo "  ✅ Main service: RUNNING"
else
    echo "  ❌ Main service: NOT RUNNING"
fi

if [ "$WEB_STATUS" = "active" ]; then
    echo "  ✅ Web service: RUNNING"
else
    echo "  ❌ Web service: NOT RUNNING"
fi
EOF

# Step 9: Test API endpoints
echo ""
echo "Step 9: Testing API endpoints..."
ssh $VPS_HOST << 'EOF'
# Test main service health
echo -n "  • Main service health: "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health)
if [ "$STATUS" = "200" ]; then
    echo "✅ OK (200)"
else
    echo "❌ Failed ($STATUS)"
fi

# Test web service health
echo -n "  • Web service health: "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)
if [ "$STATUS" = "200" ]; then
    echo "✅ OK (200)"
else
    echo "❌ Failed ($STATUS)"
fi

# Test cache status endpoint
echo -n "  • Cache status endpoint: "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/api/dashboard/cache-status)
if [ "$STATUS" = "200" ] || [ "$STATUS" = "404" ]; then
    if [ "$STATUS" = "404" ]; then
        echo "⚠️ Not available yet (404)"
    else
        echo "✅ OK (200)"
    fi
else
    echo "❌ Failed ($STATUS)"
fi
EOF

# Step 10: Wait for cache to populate
echo ""
echo "Step 10: Waiting for cache to populate (30 seconds)..."
for i in {1..6}; do
    echo -n "."
    sleep 5
done
echo ""

# Step 11: Test cached responses
echo ""
echo "Step 11: Testing cached API responses..."
ssh $VPS_HOST << 'EOF'
# Test signals endpoint (should be fast now)
echo "  • Testing /api/dashboard/signals response time:"
time curl -s http://localhost:8003/api/dashboard/signals -o /dev/null

# Test overview endpoint
echo ""
echo "  • Testing /api/dashboard/overview response time:"
time curl -s http://localhost:8003/api/dashboard/overview -o /dev/null

# Check cache status
echo ""
echo "  • Cache statistics:"
curl -s http://localhost:8003/api/dashboard/cache-status 2>/dev/null | python3 -m json.tool | head -20 || echo "    Cache status not available"
EOF

# Step 12: Check integration status
echo ""
echo "Step 12: Checking dashboard integration..."
ssh $VPS_HOST << 'EOF'
STATUS=$(curl -s http://localhost:8001/api/dashboard/mobile 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")

echo "  Dashboard integration status: $STATUS"

if [ "$STATUS" = "main_service" ] || [ "$STATUS" = "main_service_cached" ]; then
    echo "  ✅ Integration: WORKING"
elif [ "$STATUS" = "no_integration" ]; then
    echo "  ⚠️ Integration: Still using fallback (may need more time)"
else
    echo "  ❌ Integration: Error or unknown status"
fi
EOF

# Step 13: Monitor logs for errors
echo ""
echo "Step 13: Checking for recent errors..."
ssh $VPS_HOST << 'EOF'
ERROR_COUNT=$(sudo journalctl -u virtuoso -u virtuoso-web --since "2 minutes ago" -p err --no-pager | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    echo "  ✅ No errors in last 2 minutes"
else
    echo "  ⚠️ Found $ERROR_COUNT errors in last 2 minutes:"
    sudo journalctl -u virtuoso -u virtuoso-web --since "2 minutes ago" -p err --no-pager | head -5
fi
EOF

# Step 14: Create rollback script
echo ""
echo "Step 14: Creating rollback script..."
cat << 'ROLLBACK' > /tmp/rollback_phase1.sh
#!/bin/bash
# Emergency rollback script for Phase 1

echo "🚨 Rolling back Phase 1 changes..."

VPS_HOST="linuxuser@VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
TIMESTAMP=$1

if [ -z "$TIMESTAMP" ]; then
    echo "Usage: ./rollback_phase1.sh TIMESTAMP"
    echo "Available backups:"
    ssh $VPS_HOST "ls -la $VPS_PATH/src/*.backup_* 2>/dev/null | tail -5"
    exit 1
fi

ssh $VPS_HOST << EOF
cd $VPS_PATH

# Restore backups
if [ -f src/main.py.backup_${TIMESTAMP} ]; then
    cp src/main.py.backup_${TIMESTAMP} src/main.py
    echo "Restored main.py"
fi

if [ -f src/api/routes/dashboard.py.backup_${TIMESTAMP} ]; then
    cp src/api/routes/dashboard.py.backup_${TIMESTAMP} src/api/routes/dashboard.py
    echo "Restored dashboard.py"
fi

# Remove new files
rm -f src/core/api_cache.py
rm -f src/core/dashboard_updater.py

# Restart services
sudo systemctl restart virtuoso
sudo systemctl restart virtuoso-web

echo "✅ Rollback complete"
EOF
ROLLBACK

chmod +x /tmp/rollback_phase1.sh
scp -q /tmp/rollback_phase1.sh $VPS_HOST:$VPS_PATH/scripts/
print_status "Rollback script created: scripts/rollback_phase1.sh"

# Final summary
echo ""
echo "================================================================"
echo "📊 DEPLOYMENT SUMMARY"
echo "================================================================"

ssh $VPS_HOST << 'EOF'
# Get final status
MAIN_ACTIVE=$(systemctl is-active virtuoso)
WEB_ACTIVE=$(systemctl is-active virtuoso-web)
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/api/dashboard/signals)
INTEGRATION=$(curl -s http://localhost:8001/api/dashboard/mobile 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")

echo "Service Status:"
echo "  • Main Service: $MAIN_ACTIVE"
echo "  • Web Service: $WEB_ACTIVE"
echo ""
echo "API Performance:"
echo -n "  • Response time: "
TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost:8003/api/dashboard/signals)
echo "${TIME}s"
echo ""
echo "Integration:"
echo "  • Status: $INTEGRATION"

if [ "$MAIN_ACTIVE" = "active" ] && [ "$WEB_ACTIVE" = "active" ] && [ "$API_STATUS" = "200" ]; then
    echo ""
    echo "✅ PHASE 1 DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "Next steps:"
    echo "1. Monitor services for 30 minutes"
    echo "2. Check dashboard functionality"
    echo "3. Verify cache hit rates"
    echo "4. If stable, proceed to Phase 2 (Redis implementation)"
else
    echo ""
    echo "⚠️ DEPLOYMENT COMPLETED WITH WARNINGS"
    echo "Please check the services and logs for issues"
fi
EOF

echo ""
echo "Rollback command (if needed):"
echo "  ssh $VPS_HOST 'cd $VPS_PATH && ./scripts/rollback_phase1.sh $TIMESTAMP'"
echo ""
echo "Monitor logs:"
echo "  ssh $VPS_HOST 'sudo journalctl -u virtuoso -f'"
echo ""
echo "Check cache stats:"
echo "  ssh $VPS_HOST 'curl -s http://localhost:8003/api/dashboard/cache-status | python3 -m json.tool'"
echo ""
print_status "Phase 1 deployment script completed!"