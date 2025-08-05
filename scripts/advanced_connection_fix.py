#!/usr/bin/env python3
"""
Advanced connection fixes for Bybit API timeout issues.
Based on research findings about CloudFront CDN and connection problems.
"""

import subprocess
import sys

# The fixes to apply
fixes = """
# 1. Increase all timeouts significantly
sed -i 's/total=60,  # Total timeout (increased for high latency)/total=90,  # Total timeout (increased for CDN issues)/' src/core/exchanges/bybit.py
sed -i 's/connect=20,  # Connection timeout (increased from 10s)/connect=30,  # Connection timeout (increased for CDN)/' src/core/exchanges/bybit.py
sed -i 's/sock_read=30  # Socket read timeout (increased from 20s)/sock_read=45  # Socket read timeout (increased for CDN)/' src/core/exchanges/bybit.py

# 2. Increase connection limits
sed -i 's/limit=150,/limit=200,  # Increased total connections/' src/core/exchanges/bybit.py
sed -i 's/limit_per_host=30,  # Reduced to prevent exhaustion/limit_per_host=50,  # Increased for better throughput/' src/core/exchanges/bybit.py

# 3. Reduce DNS cache TTL for CDN changes
sed -i 's/ttl_dns_cache=300,/ttl_dns_cache=60,  # Reduced for CDN changes/' src/core/exchanges/bybit.py

# 4. Force close connections to avoid stale connections
sed -i 's/force_close=False,/force_close=True,  # Force close to avoid stale CDN connections/' src/core/exchanges/bybit.py

# 5. Add trust_env for proxy support if needed
sed -i '/self.session = aiohttp.ClientSession(/a\\                trust_env=True,  # Trust proxy settings if any' src/core/exchanges/bybit.py
"""

def apply_fixes():
    """Apply the fixes to the VPS."""
    print("Applying advanced connection fixes...")
    
    # Create the fix script
    fix_script = f"""
ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Backup current file
cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.advanced_backup

{fixes}

# Verify the changes
echo "Verifying changes..."
grep -E "(total=|connect=|sock_read=|limit=|limit_per_host=|ttl_dns_cache=|force_close=)" src/core/exchanges/bybit.py | head -10

# Check syntax
python3 -m py_compile src/core/exchanges/bybit.py && echo "✅ Syntax check passed" || echo "❌ Syntax error"

EOF
"""
    
    # Execute the fixes
    result = subprocess.run(fix_script, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Fixes applied successfully")
        print(result.stdout)
        
        # Restart the service
        print("\nRestarting service...")
        restart_result = subprocess.run(
            'ssh linuxuser@45.77.40.77 "sudo systemctl restart virtuoso && sleep 5 && sudo systemctl status virtuoso | grep Active"',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if "active (running)" in restart_result.stdout:
            print("✅ Service restarted successfully")
        else:
            print("❌ Service restart failed")
            print(restart_result.stdout)
            print(restart_result.stderr)
    else:
        print("❌ Failed to apply fixes")
        print(result.stderr)

if __name__ == "__main__":
    apply_fixes()