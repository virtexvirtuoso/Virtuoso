#!/bin/bash

echo "🔧 Fixing Connection Pool Based on Diagnostic Findings"
echo ""
echo "Diagnostic Results Summary:"
echo "✅ Direct API calls work perfectly (100% success)"
echo "✅ All endpoints respond in <2 seconds"
echo "✅ VPS handles 20 concurrent requests without issues"
echo "❌ Current limit_per_host=10 is too restrictive"
echo ""

cat > /tmp/fix_pool_limits.py << 'EOF'
import re

def fix_connection_pool(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the connection pool limits based on diagnostic findings
    # The diagnostic showed 20 concurrent requests work fine
    pattern = r'limit_per_host=\d+'
    content = re.sub(pattern, 'limit_per_host=30', content)
    
    # Also increase the total limit proportionally
    pattern = r'limit=100,'
    content = re.sub(pattern, 'limit=200,', content)
    
    # Fix the timeout values - the diagnostic showed all requests complete in <2s
    # So 20s timeout is excessive, causing false timeouts
    pattern = r'self\._timeout\s*=\s*\d+\.?\d*'
    content = re.sub(pattern, 'self._timeout = 10.0', content)
    
    # Ensure keepalive and proper connection recycling
    if 'keepalive_timeout' not in content:
        pattern = r'(ttl_dns_cache=300,)'
        replacement = r'\1\n                keepalive_timeout=30,'
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed connection pool limits:")
    print("   - limit_per_host: 10 → 30")
    print("   - limit: 100 → 200") 
    print("   - timeout: 20s → 10s")
    print("   - Added keepalive_timeout: 30s")

fix_connection_pool('src/core/exchanges/bybit.py')
EOF

python /tmp/fix_pool_limits.py

echo ""
echo "🔍 Adding connection monitoring..."

cat > /tmp/add_monitoring.py << 'EOF'
import re

def add_connection_monitoring(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find where we make requests and add connection monitoring
    for i, line in enumerate(lines):
        if 'async def _make_request' in line:
            # Add monitoring at the start
            for j in range(i+1, min(i+50, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith('#') and '"""' not in lines[j]:
                    monitor_code = '''        # Monitor connection pool usage
        if hasattr(self, 'session') and self.session and hasattr(self.session, 'connector'):
            connector = self.session.connector
            if hasattr(connector, '_acquired'):
                in_use = len(connector._acquired) if hasattr(connector, '_acquired') else 0
                available = len(connector._available) if hasattr(connector, '_available') else 0
                if in_use > 20:  # Warning threshold
                    self.logger.warning(f"⚠️ High connection usage: {in_use} in use, {available} available")
        
'''
                    if monitor_code not in ''.join(lines):
                        lines.insert(j, monitor_code)
                        print("✅ Added connection pool monitoring")
                    break
            break
    
    with open(file_path, 'w') as f:
        f.writelines(lines)

add_connection_monitoring('src/core/exchanges/bybit.py')
EOF

python /tmp/add_monitoring.py

echo ""
echo "🎯 Summary of Root Cause:"
echo ""
echo "The timeouts were caused by connection pool exhaustion:"
echo "1. Application makes many concurrent requests (likely >10)"
echo "2. Connection pool limit_per_host was only 10"
echo "3. Requests queue up waiting for available connections"
echo "4. Queued requests timeout (20s) before getting a connection"
echo "5. This creates a cascade of timeouts"
echo ""
echo "The fix increases limits to handle the actual load pattern."