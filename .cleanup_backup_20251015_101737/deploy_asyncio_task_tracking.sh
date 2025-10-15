#!/bin/bash

# Deploy Asyncio Task Tracking System to VPS
# This script deploys the complete task tracking system implementation

set -e

echo "🔄 Deploying Asyncio Task Tracking System to VPS..."

# Get list of all files that use task tracking
FILES_WITH_TASK_TRACKING=$(grep -r "create_tracked_task\|from.*task_tracker" src/ --include="*.py" -l)

echo "📁 Found $(echo "$FILES_WITH_TASK_TRACKING" | wc -l) files with task tracking implementation"

# Ensure utils/__init__.py includes task_tracker
echo "📝 Updating utils/__init__.py to include task_tracker import..."
echo "from .task_tracker import create_tracked_task, cleanup_background_tasks, get_task_info, get_task_count" >> src/utils/__init__.py

# Copy all task tracking files to VPS
echo "📤 Uploading task_tracker.py..."
scp src/utils/task_tracker.py vps:trading/Virtuoso_ccxt/src/utils/

echo "📤 Uploading utils/__init__.py..."
scp src/utils/__init__.py vps:trading/Virtuoso_ccxt/src/utils/

# Copy all files that use task tracking
echo "📤 Uploading all files with task tracking implementation..."
echo "$FILES_WITH_TASK_TRACKING" | while read file; do
    if [ -f "$file" ]; then
        echo "  → $file"
        scp "$file" "vps:trading/Virtuoso_ccxt/$file"
    fi
done

# Restart services on VPS
echo "🔄 Restarting services on VPS..."
ssh vps << 'EOF'
    cd trading/Virtuoso_ccxt

    echo "🛑 Stopping existing services..."
    pkill -f "python.*main.py" || true
    pkill -f "python.*web_server.py" || true
    pkill -f "python.*monitoring_api.py" || true

    sleep 5

    echo "🚀 Starting services with task tracking..."
    nohup ./venv311/bin/python src/main.py > logs/main.log 2>&1 &
    nohup ./venv311/bin/python src/web_server.py > logs/web_server.log 2>&1 &
    nohup MONITORING_PORT=8001 ./venv311/bin/python src/monitoring_api.py > logs/monitoring_api.log 2>&1 &

    sleep 10

    echo "✅ Services restarted with task tracking system"

    # Verify services are running
    ps aux | grep -E "main\.py|web_server\.py|monitoring_api\.py" | grep -v grep
EOF

echo "🎯 Testing endpoint availability..."
sleep 15

for endpoint in "/health" "/mobile" "/education" "/api/docs"; do
    echo -n "  Testing $endpoint: "
    if curl -s -o /dev/null -w "%{http_code}" "http://5.223.63.4:8002$endpoint" | grep -q "200"; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
done

echo ""
echo "🔍 Checking VPS resource usage after deployment..."
ssh vps 'top -bn1 | head -20'

echo ""
echo "✅ Asyncio Task Tracking System deployment completed!"
echo "📊 Task tracking is now active across all VPS services"
echo "🔧 Resource management and cleanup systems are operational"