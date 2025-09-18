#!/bin/bash

# Deploy VPS Performance Optimization to Production
# Optimized for: 4 vCPU, 16GB RAM, 160GB SSD, Singapore VPS (${VPS_HOST})

set -e

VPS_HOST="vps"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "🚀 Deploying VPS Performance Optimization"
echo "========================================"
echo "Target: Singapore VPS (${VPS_HOST})"
echo "Specs: 4 vCPU, 16GB RAM, 160GB SSD"
echo ""

# Verify local files exist
echo "🔍 Verifying optimization files..."
required_files=(
    "scripts/optimize_vps_performance.sh"
    "config/vps_optimization_config.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$LOCAL_PATH/$file" ]]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
    echo "✅ Found: $file"
done

echo ""
echo "📤 Transferring optimization files to VPS..."

# Copy optimization files
scp "$LOCAL_PATH/scripts/optimize_vps_performance.sh" "$VPS_HOST:$VPS_PATH/scripts/"
scp "$LOCAL_PATH/config/vps_optimization_config.py" "$VPS_HOST:$VPS_PATH/config/"

echo "✅ Files transferred successfully"

# Make scripts executable on VPS
echo "🔧 Making scripts executable on VPS..."
ssh "$VPS_HOST" "chmod +x $VPS_PATH/scripts/optimize_vps_performance.sh"

echo "✅ Scripts made executable"

# Create backup of current configuration
echo "💾 Creating backup of current configuration..."
ssh "$VPS_HOST" "
    mkdir -p $VPS_PATH/backups/pre_optimization_$(date +%Y%m%d_%H%M%S)
    
    # Backup current systemd service
    if [ -f /etc/systemd/system/virtuoso.service ]; then
        sudo cp /etc/systemd/system/virtuoso.service $VPS_PATH/backups/pre_optimization_$(date +%Y%m%d_%H%M%S)/
    fi
    
    # Backup current memcached config
    if [ -f /etc/memcached.conf ]; then
        sudo cp /etc/memcached.conf $VPS_PATH/backups/pre_optimization_$(date +%Y%m%d_%H%M%S)/
    fi
    
    # Backup current redis config
    if [ -f /etc/redis/redis.conf ]; then
        sudo cp /etc/redis/redis.conf $VPS_PATH/backups/pre_optimization_$(date +%Y%m%d_%H%M%S)/
    fi
"

echo "✅ Configuration backup created"

# Run optimization script on VPS
echo "⚙️ Running optimization script on VPS..."
echo "This will update system configurations and restart services..."

ssh "$VPS_HOST" "cd $VPS_PATH && sudo ./scripts/optimize_vps_performance.sh"

echo ""
echo "🔄 Restarting Virtuoso service with optimizations..."
ssh "$VPS_HOST" "sudo systemctl restart virtuoso.service"

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 10

# Verify deployment
echo "🔍 Verifying optimization deployment..."

# Check service status
echo "Checking service status..."
service_status=$(ssh "$VPS_HOST" "systemctl is-active virtuoso.service" || echo "failed")

if [[ "$service_status" == "active" ]]; then
    echo "✅ Virtuoso service is running"
else
    echo "❌ Virtuoso service failed to start"
    echo "Service status: $service_status"
    echo "Checking logs..."
    ssh "$VPS_HOST" "sudo journalctl -u virtuoso.service --no-pager -n 20"
    exit 1
fi

# Test API endpoints
echo "Testing API endpoints..."
api_health=$(ssh "$VPS_HOST" "curl -s http://localhost:8003/health" || echo "failed")

if [[ "$api_health" == *"healthy"* ]] || [[ "$api_health" == *"ok"* ]]; then
    echo "✅ API health check passed"
else
    echo "⚠️  API health check inconclusive"
    echo "Response: $api_health"
fi

# Check resource utilization
echo "Checking resource utilization..."
ssh "$VPS_HOST" "cd $VPS_PATH && python3 scripts/monitor_performance.py" > /tmp/vps_performance.json

if [[ -f /tmp/vps_performance.json ]]; then
    echo "📊 Performance metrics collected:"
    python3 -c "
import json
with open('/tmp/vps_performance.json', 'r') as f:
    data = json.load(f)
    
metrics = data['metrics']
print(f'  CPU Usage: {metrics[\"cpu\"][\"average\"]:.1f}%')
print(f'  Memory Usage: {metrics[\"memory\"][\"percent\"]:.1f}%')
print(f'  Disk Usage: {metrics[\"disk\"][\"percent\"]:.1f}%')

if data['recommendations']:
    print('\\n🎯 Recommendations:')
    for rec in data['recommendations']:
        print(f'  {rec}')
"
fi

# Test dashboard access
echo "Testing dashboard access..."
dashboard_test=$(ssh "$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003/" || echo "000")

if [[ "$dashboard_test" == "200" ]]; then
    echo "✅ Desktop dashboard accessible"
else
    echo "⚠️  Dashboard returned status: $dashboard_test"
fi

# Test mobile dashboard
mobile_test=$(ssh "$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003/mobile" || echo "000")

if [[ "$mobile_test" == "200" ]]; then
    echo "✅ Mobile dashboard accessible"
else
    echo "⚠️  Mobile dashboard returned status: $mobile_test"
fi

echo ""
echo "🎉 VPS Optimization Deployment Complete!"
echo "========================================"
echo ""
echo "📊 Optimization Summary:"
echo "  • CPU: 4 cores optimized with 2 workers + background tasks"
echo "  • Memory: 16GB allocated (8GB app, 4GB memcached, 2GB redis)"
echo "  • Storage: 160GB SSD with log rotation and cleanup"
echo "  • Cache: Multi-layer caching with optimized TTLs"
echo "  • Network: Singapore location optimizations applied"
echo ""
echo "🌐 Access URLs:"
echo "  • Desktop Dashboard: http://${VPS_HOST}:8003/"
echo "  • Mobile Dashboard: http://${VPS_HOST}:8003/mobile"
echo "  • Health Check: http://${VPS_HOST}:8003/health"
echo "  • Monitoring API: http://${VPS_HOST}:8001/api/monitoring/status"
echo ""
echo "📈 Performance Targets:"
echo "  • CPU Utilization: 70-80% (Currently: checking...)"
echo "  • Memory Usage: 75-85%"
echo "  • Response Time: <100ms"
echo "  • Cache Hit Ratio: >90%"
echo "  • Uptime Target: >99.9%"
echo ""
echo "🛠️  Monitoring Commands:"
echo "  • Live logs: ssh $VPS_HOST 'sudo journalctl -u virtuoso.service -f'"
echo "  • Performance: ssh $VPS_HOST 'cd $VPS_PATH && python3 scripts/monitor_performance.py'"
echo "  • Service status: ssh $VPS_HOST 'sudo systemctl status virtuoso.service'"
echo ""
echo "⚠️  Rollback (if needed):"
echo "  ssh $VPS_HOST 'sudo systemctl stop virtuoso.service'"
echo "  ssh $VPS_HOST 'sudo cp $VPS_PATH/backups/pre_optimization_*/virtuoso.service /etc/systemd/system/'"
echo "  ssh $VPS_HOST 'sudo systemctl daemon-reload && sudo systemctl start virtuoso.service'"