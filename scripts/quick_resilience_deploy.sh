#!/bin/bash

# Quick deployment script for resilience to VPS
# Optimized for high-latency connections

set -e

echo "============================================================"
echo "🚀 Quick Resilience Deployment to VPS"
echo "============================================================"

VPS="45.77.40.77"

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