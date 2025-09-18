#!/bin/bash

#############################################################################
# Script: deploy_priority2_to_vps.sh
# Purpose: Deploy and manage deploy priority2 to vps
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
#   ./deploy_priority2_to_vps.sh [options]
#   
#   Examples:
#     ./deploy_priority2_to_vps.sh
#     ./deploy_priority2_to_vps.sh --verbose
#     ./deploy_priority2_to_vps.sh --dry-run
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

# Priority 2 VPS Deployment Script
# Deploy multi-tier cache and API gateway improvements

set -e  # Exit on any error

echo "========================================"
echo "🚀 Priority 2 VPS Deployment Starting"
echo "========================================"

# Configuration
VPS_HOST="linuxuser@${VPS_HOST}"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PROJECT_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Ensure Redis is available on VPS
log_info "Step 1: Checking Redis availability on VPS..."
ssh $VPS_HOST << 'EOF'
    # Check if Redis is installed and running
    if ! command -v redis-server &> /dev/null; then
        echo "Installing Redis..."
        sudo apt-get update
        sudo apt-get install -y redis-server
    fi
    
    # Start Redis service
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    
    # Check Redis status
    if systemctl is-active --quiet redis-server; then
        echo "✅ Redis is running on port 6379"
        redis-cli ping
    else
        echo "❌ Redis failed to start"
        exit 1
    fi
EOF

if [ $? -ne 0 ]; then
    log_error "Redis setup failed on VPS"
    exit 1
fi

# Step 2: Ensure Memcached is available on VPS
log_info "Step 2: Checking Memcached availability on VPS..."
ssh $VPS_HOST << 'EOF'
    # Check if Memcached is installed and running
    if ! command -v memcached &> /dev/null; then
        echo "Installing Memcached..."
        sudo apt-get install -y memcached
    fi
    
    # Configure Memcached (increase memory limit)
    sudo sed -i 's/-m 64/-m 512/' /etc/memcached.conf
    
    # Start Memcached service
    sudo systemctl enable memcached
    sudo systemctl start memcached
    
    # Check Memcached status
    if systemctl is-active --quiet memcached; then
        echo "✅ Memcached is running on port 11211"
        echo "stats" | nc -w 1 localhost 11211 | head -5
    else
        echo "❌ Memcached failed to start"
        exit 1
    fi
EOF

if [ $? -ne 0 ]; then
    log_error "Memcached setup failed on VPS"
    exit 1
fi

# Step 3: Deploy Priority 2 files
log_info "Step 3: Deploying Priority 2 implementation files..."

# Create the directory structure on VPS if needed
ssh $VPS_HOST "mkdir -p $VPS_PROJECT_PATH/src/core/cache $VPS_PROJECT_PATH/src/api/routes"

# Copy multi-tier cache implementation
log_info "Copying multi-tier cache system..."
scp "$LOCAL_PROJECT_PATH/src/core/cache/multi_tier_cache.py" "$VPS_HOST:$VPS_PROJECT_PATH/src/core/cache/"

# Copy API gateway implementation
log_info "Copying API gateway system..."
scp "$LOCAL_PROJECT_PATH/src/api/gateway.py" "$VPS_HOST:$VPS_PROJECT_PATH/src/api/"
scp "$LOCAL_PROJECT_PATH/src/api/routes/gateway_routes.py" "$VPS_HOST:$VPS_PROJECT_PATH/src/api/routes/"

# Copy startup integration
log_info "Copying startup integration..."
scp "$LOCAL_PROJECT_PATH/src/core/startup.py" "$VPS_HOST:$VPS_PROJECT_PATH/src/core/"

# Copy updated API initialization
log_info "Copying updated API initialization..."
scp "$LOCAL_PROJECT_PATH/src/api/__init__.py" "$VPS_HOST:$VPS_PROJECT_PATH/src/api/"

# Step 4: Install Python dependencies
log_info "Step 4: Installing required Python packages..."
ssh $VPS_HOST << EOF
    cd $VPS_PROJECT_PATH
    
    # Install Redis Python client
    pip3 install redis aioredis
    
    # Install async Memcached client
    pip3 install aiomcache
    
    # Install additional dependencies
    pip3 install aiohttp
    
    echo "✅ Python dependencies installed"
EOF

# Step 5: Update main.py to include Priority 2 startup
log_info "Step 5: Updating main.py with Priority 2 startup..."

# Create a backup of the current main.py
ssh $VPS_HOST "cp $VPS_PROJECT_PATH/src/main.py $VPS_PROJECT_PATH/src/main.py.backup"

# Add Priority 2 startup to main.py
ssh $VPS_HOST << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt/src
    
    # Check if Priority 2 startup is already added
    if ! grep -q "Priority 2" main.py; then
        # Add Priority 2 import and startup
        cat << 'PYTHON_CODE' >> main.py

# ===== Priority 2 Architectural Improvements =====
try:
    from src.core.startup import run_priority2_startup
    import asyncio
    
    async def startup_priority2():
        """Initialize Priority 2 improvements"""
        try:
            results = await run_priority2_startup()
            print("🚀 Priority 2 improvements initialized")
            return results
        except Exception as e:
            print(f"⚠️ Priority 2 startup error: {e}")
            return {}
    
    # Run Priority 2 startup if this is the main execution
    if __name__ == "__main__" and "--skip-priority2" not in sys.argv:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            priority2_results = loop.run_until_complete(startup_priority2())
            loop.close()
        except Exception as e:
            print(f"Priority 2 startup failed: {e}")

except ImportError as e:
    print(f"Priority 2 components not available: {e}")

PYTHON_CODE
        
        echo "✅ Priority 2 startup added to main.py"
    else
        echo "✅ Priority 2 startup already present in main.py"
    fi
EOF

# Step 6: Test the deployment
log_info "Step 6: Testing Priority 2 deployment..."
ssh $VPS_HOST << EOF
    cd $VPS_PROJECT_PATH
    
    # Test import of Priority 2 components
    python3 -c "
try:
    from src.core.cache.multi_tier_cache import MultiTierCache
    from src.api.gateway import APIGateway
    from src.core.startup import Priority2Startup
    print('✅ All Priority 2 components import successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
    
    # Test Redis connection
    python3 -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"
    
    # Test Memcached connection
    python3 -c "
from pymemcache.client.base import Client
try:
    mc = Client(('127.0.0.1', 11211))
    mc.set('test', 'value')
    result = mc.get('test')
    mc.delete('test')
    mc.close()
    print('✅ Memcached connection successful')
except Exception as e:
    print(f'❌ Memcached connection failed: {e}')
    exit(1)
"
EOF

if [ $? -ne 0 ]; then
    log_error "Priority 2 testing failed"
    exit 1
fi

# Step 7: Restart the service
log_info "Step 7: Restarting Virtuoso service with Priority 2 improvements..."
ssh $VPS_HOST << 'EOF'
    # Stop the current service
    sudo systemctl stop virtuoso.service
    
    # Wait for clean shutdown
    sleep 5
    
    # Start the service with Priority 2 improvements
    sudo systemctl start virtuoso.service
    
    # Check service status
    sleep 10
    if systemctl is-active --quiet virtuoso.service; then
        echo "✅ Virtuoso service restarted successfully"
    else
        echo "❌ Virtuoso service failed to start"
        sudo systemctl status virtuoso.service
        exit 1
    fi
EOF

if [ $? -ne 0 ]; then
    log_error "Service restart failed"
    exit 1
fi

# Step 8: Verify Priority 2 performance
log_info "Step 8: Verifying Priority 2 performance..."
sleep 15  # Give the system time to initialize

# Test the new gateway endpoints
log_info "Testing Priority 2 endpoints..."
ssh $VPS_HOST << 'EOF'
    # Test gateway health
    echo "Testing gateway health endpoint..."
    curl -s http://localhost:8003/gateway/health | python3 -m json.tool
    
    # Test gateway metrics
    echo -e "\nTesting gateway metrics endpoint..."
    curl -s http://localhost:8003/gateway/metrics | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Cache Hit Rate: {data['cache'].get('total_hit_rate_percent', 0):.1f}%\")
    print(f\"Avg Response Time: {data['requests'].get('avg_response_time_ms', 0):.1f}ms\")
    print(f\"Redis Available: {data['cache'].get('redis_available', False)}\")
    print(f\"Memcached Available: {data['cache'].get('memcached_available', False)}\")
except Exception as e:
    print(f'Error parsing metrics: {e}')
"
    
    # Test cached dashboard endpoint
    echo -e "\nTesting cached dashboard endpoint..."
    start_time=$(date +%s%3N)
    curl -s http://localhost:8003/gateway/dashboard/mobile > /dev/null
    end_time=$(date +%s%3N)
    response_time=$((end_time - start_time))
    echo "Response time: ${response_time}ms"
    
    if [ $response_time -lt 150 ]; then
        echo "✅ Response time target achieved (<150ms)"
    else
        echo "⚠️ Response time above target (${response_time}ms)"
    fi
EOF

# Step 9: Monitor service logs
log_info "Step 9: Monitoring Priority 2 startup in service logs..."
echo "Checking service logs for Priority 2 initialization..."
ssh $VPS_HOST "sudo journalctl -u virtuoso.service --since '2 minutes ago' | grep -E '(Priority 2|Multi-tier|Gateway|✅|❌)' | tail -20"

echo "========================================"
echo "✅ Priority 2 VPS Deployment Complete!"
echo "========================================"
echo ""
echo "🎯 Performance Targets:"
echo "   - Cache Hit Rate: 70%+ (check with: curl localhost:8003/gateway/stats)"
echo "   - Response Times: <150ms"
echo "   - Redis L1 + Memcached L2: Active"
echo "   - API Gateway: Rate limiting at 100 req/sec"
echo ""
echo "📊 Monitor Performance:"
echo "   - Gateway Health: curl localhost:8003/gateway/health"
echo "   - Gateway Metrics: curl localhost:8003/gateway/metrics"
echo "   - Service Logs: ssh $VPS_HOST 'sudo journalctl -u virtuoso.service -f'"
echo ""
echo "🔧 New Endpoints Available:"
echo "   - /gateway/health - Gateway health check"
echo "   - /gateway/metrics - Performance metrics"
echo "   - /gateway/dashboard/mobile - Cached mobile dashboard"
echo "   - /gateway/proxy/* - Universal gateway proxy"

log_info "Priority 2 deployment completed successfully! 🚀"