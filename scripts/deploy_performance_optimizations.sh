#!/bin/bash

# Deploy Performance Optimizations to VPS
# This script copies all performance optimization files to the production server

echo "🚀 Deploying Virtuoso Performance Optimizations to VPS"
echo "Target: linuxuser@45.77.40.77"
echo "=========================================="

# VPS details
VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Function to copy files
copy_file() {
    local src=$1
    local dest=$2
    echo "📁 Copying $src -> $dest"
    scp "$src" "$VPS_USER@$VPS_HOST:$VPS_PATH/$dest" || {
        echo "❌ Failed to copy $src"
        return 1
    }
}

# Function to create directory on VPS
create_directory() {
    local dir=$1
    echo "📂 Creating directory: $dir"
    ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/$dir" || {
        echo "❌ Failed to create directory $dir"
        return 1
    }
}

echo "🔧 Phase 1: Creating directory structure"
create_directory "src/core"
create_directory "src/api/routes"
create_directory "src/dashboard/templates"
create_directory "scripts"

echo "🔧 Phase 2: Copying core performance components"

# Copy unified cache manager
copy_file "src/core/cache_manager.py" "src/core/cache_manager.py"

# Copy WebSocket manager
copy_file "src/core/websocket_manager.py" "src/core/websocket_manager.py"

# Copy performance monitoring API
copy_file "src/api/routes/performance.py" "src/api/routes/performance.py"

# Copy performance dashboard UI
copy_file "src/dashboard/templates/performance_dashboard.html" "src/dashboard/templates/performance_dashboard.html"

echo "🔧 Phase 3: Copying updated integration files"

# Copy updated cache adapter
copy_file "src/api/cache_adapter.py" "src/api/cache_adapter.py"

# Copy updated API initialization
copy_file "src/api/__init__.py" "src/api/__init__.py"

# Copy updated web server
copy_file "src/web_server.py" "src/web_server.py"

# Copy updated main.py (with sync/async fixes)
copy_file "src/main.py" "src/main.py"

echo "🔧 Phase 4: Copying test and documentation files"

# Copy performance test suite
copy_file "scripts/test_performance_optimizations.py" "scripts/test_performance_optimizations.py"

# Copy comprehensive deployment summary
copy_file "COMPREHENSIVE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md" "COMPREHENSIVE_OPTIMIZATION_DEPLOYMENT_SUMMARY.md"

echo "🔧 Phase 5: Installing dependencies on VPS"

# Install required Python packages
ssh "$VPS_USER@$VPS_HOST" << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Install aiomcache for unified cache manager
echo "📦 Installing aiomcache..."
./venv311/bin/pip install aiomcache || pip3 install --user aiomcache

# Install psutil for system monitoring
echo "📦 Installing psutil..."
./venv311/bin/pip install psutil || pip3 install --user psutil

# Install aiohttp for API testing
echo "📦 Installing aiohttp..."
./venv311/bin/pip install aiohttp || pip3 install --user aiohttp

# Restart memcached service if available
echo "🔄 Checking memcached service..."
if command -v memcached &> /dev/null; then
    sudo systemctl restart memcached 2>/dev/null || echo "ℹ️ Memcached service not available (will use fallback cache)"
else
    echo "ℹ️ Memcached not installed (will use in-memory fallback)"
fi

echo "✅ Dependencies installed successfully"
EOF

echo "🔧 Phase 6: Verifying deployment"

# Test that files exist on VPS
echo "🔍 Verifying deployed files..."
ssh "$VPS_USER@$VPS_HOST" << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Checking core files:"
ls -la src/core/cache_manager.py src/core/websocket_manager.py 2>/dev/null && echo "✅ Core files OK" || echo "❌ Core files missing"

echo "Checking API files:"
ls -la src/api/routes/performance.py 2>/dev/null && echo "✅ Performance API OK" || echo "❌ Performance API missing"

echo "Checking dashboard files:"
ls -la src/dashboard/templates/performance_dashboard.html 2>/dev/null && echo "✅ Performance dashboard OK" || echo "❌ Performance dashboard missing"

echo "Checking test files:"
ls -la scripts/test_performance_optimizations.py 2>/dev/null && echo "✅ Test suite OK" || echo "❌ Test suite missing"

echo "✅ Deployment verification complete"
EOF

echo "=========================================="
echo "🎉 Performance optimization deployment complete!"
echo ""
echo "Next steps:"
echo "1. Restart the Virtuoso service on VPS"
echo "2. Run performance tests: python scripts/test_performance_optimizations.py"
echo "3. Access performance dashboard: http://45.77.40.77:8000/performance"
echo "4. Monitor API endpoints: http://45.77.40.77:8000/api/monitoring/performance/summary"
echo ""
echo "To restart service:"
echo "ssh linuxuser@45.77.40.77 'cd /home/linuxuser/trading/Virtuoso_ccxt && ./scripts/restart_service.sh'"