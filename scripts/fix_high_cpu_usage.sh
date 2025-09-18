#!/bin/bash

echo "🔧 Fixing high CPU usage on VPS by adjusting monitoring intervals..."

# Create a patch to fix the monitoring interval
cat > /tmp/fix_cpu_usage.patch << 'EOF'
--- a/src/main.py
+++ b/src/main.py
@@ -1176,7 +1176,7 @@ class Monitor:
         
         self.analysis_cache = {}
         self.cache_ttl = 5  # 5 seconds cache
-        self.analysis_interval = 2  # Analyze every 2 seconds
+        self.analysis_interval = 30  # Analyze every 30 seconds (reduced from 2 to save CPU)
         
         # Initialize market state
         self.market_state = {
EOF

# Apply the fix on VPS
echo "📤 Deploying fix to VPS..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && cat > /tmp/fix_cpu_usage.patch" < /tmp/fix_cpu_usage.patch

ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && patch -p1 < /tmp/fix_cpu_usage.patch"

# Also increase cache TTL to reduce API calls
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/self.cache_ttl = 5/self.cache_ttl = 30/' src/main.py"

# Restart services
echo "🔄 Restarting services..."
ssh vps "sudo systemctl restart virtuoso virtuoso-web"

echo "⏳ Waiting for services to stabilize..."
sleep 15

# Check CPU usage
echo "📊 Checking CPU usage after fix..."
ssh vps "top -bn1 | head -15"

echo "📋 Checking log frequency..."
ssh vps "sudo journalctl -u virtuoso -f -n 0 > /tmp/log_check.txt 2>&1 & sleep 5 && kill %1 2>/dev/null; echo 'Log lines in 5 seconds:' && wc -l /tmp/log_check.txt"

echo "✅ Fix deployed! Monitoring interval increased from 2s to 30s"