#!/bin/bash
"""
Deploy Priority 1 Dashboard Performance Fixes to VPS
Deploys advanced optimizations for dashboard performance
"""

set -e  # Exit on any error

echo "🔥 Deploying Priority 1 Dashboard Performance Fixes to VPS"
echo "=========================================================="

# Configuration
VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Step 1: Creating optimized files locally...${NC}"
python3 scripts/fix_dashboard_performance_priority1.py

echo -e "${BLUE}📦 Step 2: Syncing optimized files to VPS...${NC}"
rsync -avz --progress \
    src/api/cache_adapter_optimized.py \
    src/api/routes/dashboard_streaming.py \
    src/core/connection_manager.py \
    ${VPS_USER}@${VPS_HOST}:${VPS_PROJECT_PATH}/

echo -e "${BLUE}🔧 Step 3: Updating API routes on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    
    # Add streaming routes to API initialization
    if ! grep -q 'dashboard_streaming' src/api/__init__.py; then
        cp src/api/__init__.py src/api/__init__.py.backup
        
        cat >> src/api/__init__.py << 'EOF'

# Priority 1 Performance: Streaming routes
try:
    from .routes import dashboard_streaming
    dashboard_streaming_available = True
except ImportError:
    dashboard_streaming_available = False

# Add to init_api_routes function
if dashboard_streaming_available:
    app.include_router(
        dashboard_streaming.router,
        prefix=f'{api_prefix}/dashboard-stream',
        tags=['dashboard-streaming']
    )
EOF
    fi
"

echo -e "${BLUE}🔄 Step 4: Restarting with optimizations...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    sudo systemctl stop virtuoso.service
    sleep 5
    sudo systemctl start virtuoso.service
    sleep 10
"

echo -e "${BLUE}✅ Step 5: Verifying Priority 1 optimizations...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    echo 'Testing optimized endpoints:'
    
    echo 'Standard mobile-data:'
    time curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s - %{size_download} bytes' http://localhost:8003/api/dashboard-cached/mobile-data
    echo
    
    echo 'Streaming mobile-data:'
    time curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s - %{size_download} bytes' http://localhost:8003/api/dashboard-stream/mobile-data-stream
    echo
    
    echo 'Cache performance metrics:'
    curl -s http://localhost:8003/api/dashboard-stream/cache-performance | head -20
    echo
"

echo -e "${GREEN}🎉 Priority 1 deployment complete!${NC}"
echo "New optimized endpoints available:"
echo "  http://45.77.40.77:8003/api/dashboard-stream/mobile-data-stream"  
echo "  http://45.77.40.77:8003/api/dashboard-stream/overview-stream"
echo "  http://45.77.40.77:8003/api/dashboard-stream/cache-performance"

exit 0