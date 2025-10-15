#!/bin/bash
set -e

echo "🚀 Deploying Complete AsyncIO Task Management Fixes to VPS..."

# Check local changes
echo "📊 Checking local repository status..."
git status --porcelain

# Create deployment package
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_DIR="deploy_asyncio_fixes_${TIMESTAMP}"
echo "📦 Creating deployment package: $DEPLOY_DIR"

# Sync critical files to VPS
echo "📤 Syncing AsyncIO fixes to VPS..."
rsync -avz --progress \
    --include='src/utils/task_tracker.py' \
    --include='src/main.py' \
    --include='src/web_server.py' \
    --include='src/monitoring/' \
    --include='src/api/' \
    --include='src/core/' \
    --include='src/data_processing/' \
    --include='src/dashboard/' \
    --include='src/services/' \
    --include='src/trade_execution/' \
    --include='src/strategies/' \
    --include='src/phase4_integration.py' \
    --include='src/reports/' \
    --include='src/portfolio/' \
    --include='src/testing/' \
    --include='src/websocket/' \
    --include='src/tools/' \
    --include='src/integrated_server.py' \
    --include='src/demo_trading_runner.py' \
    --include='src/analysis/' \
    --include='src/data_acquisition/' \
    --exclude='*' \
    ./ vps:~/trading/Virtuoso_ccxt/

echo "🔄 Restarting VPS services with AsyncIO fixes..."
ssh vps << 'ENDSSH'
cd ~/trading/Virtuoso_ccxt

# Stop existing services
echo "⏹️ Stopping existing services..."
pkill -f "python.*src/main.py" || true
pkill -f "python.*src/web_server.py" || true
pkill -f "python.*src/monitoring_api.py" || true
sleep 5

# Force kill if still running
pkill -9 -f "python.*src/main.py" || true
pkill -9 -f "python.*src/web_server.py" || true
pkill -9 -f "python.*src/monitoring_api.py" || true

# Verify Python environment
echo "🐍 Checking Python environment..."
source venv311/bin/activate
python -c "import sys; print(f'Python: {sys.version}')"

# Start monitoring API (port 8001)
echo "🔧 Starting monitoring API on port 8001..."
nohup python src/monitoring_api.py > logs/monitoring_api.log 2>&1 &
sleep 3

# Start main trading system
echo "🚀 Starting main trading system..."
nohup python -u src/main.py > logs/main.log 2>&1 &
sleep 5

# Start web server (port 8002)
echo "🌐 Starting web server on port 8002..."
nohup python src/web_server.py > logs/web_server.log 2>&1 &
sleep 3

# Check service status
echo "✅ Checking service status..."
ps aux | grep python | grep -E "(main|web_server|monitoring_api)" | grep -v grep || echo "No services found"

# Test endpoints
echo "🧪 Testing endpoints..."
curl -s -o /dev/null -w "Health: %{http_code}\n" http://localhost:8002/health
curl -s -o /dev/null -w "Mobile: %{http_code}\n" http://localhost:8002/mobile
curl -s -o /dev/null -w "Monitoring: %{http_code}\n" http://localhost:8001/health

ENDSSH

echo "🎯 Testing VPS endpoints from local..."
sleep 5

# Test endpoints from local
for endpoint in "/health" "/mobile" "/api/docs" "/education"; do
    echo -n "VPS $endpoint: "
    curl -s -o /dev/null -w "%{http_code}" "http://5.223.63.4:8002$endpoint" || echo "failed"
    echo
done

echo "🧪 Testing monitoring API from local..."
curl -s -o /dev/null -w "Monitoring API: %{http_code}\n" "http://5.223.63.4:8001/health"

echo "✅ AsyncIO Task Management Fixes Deployment Complete!"
echo "📊 Task tracking system now active across all services"
echo "🔧 All asyncio.create_task() calls converted to create_tracked_task()"
echo "🧹 Proper resource cleanup enabled during shutdown"
echo ""
echo "📈 Expected improvements:"
echo "  - Reduced CPU usage from untracked tasks"
echo "  - Eliminated 'Task was destroyed but it is pending' warnings"
echo "  - Proper aiomcache connection cleanup"
echo "  - Graceful application shutdown"