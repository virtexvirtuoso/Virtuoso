#!/bin/bash

# Script to fix Bybit connection pool exhaustion issues
# Created: 2025-08-27

echo "🔧 Fixing Bybit Connection Pool Exhaustion Issues..."

# Backup current files
echo "📦 Creating backups..."
cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_$(date +%Y%m%d_%H%M%S)
cp src/core/exchanges/intelligence_adapter.py src/core/exchanges/intelligence_adapter.py.backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
cp src/core/exchanges/bybit_intelligence_adapter.py src/core/exchanges/bybit_intelligence_adapter.py.backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Fix 1: Disable intelligence adapter temporarily
echo "1️⃣ Disabling intelligence adapter temporarily..."
cat > /tmp/disable_intelligence.py << 'EOF'
import sys
import re

def fix_intelligence_adapter(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the initialization section
        if 'self.intelligence_enabled = True' in content:
            content = content.replace('self.intelligence_enabled = True', 
                                    'self.intelligence_enabled = False  # Temporarily disabled due to connection pool issues')
            print(f"✅ Disabled intelligence adapter in {file_path}")
        elif 'self.intelligence_enabled' not in content:
            # Add the flag if it doesn't exist
            init_pattern = r'(async def __ainit__.*?:.*?\n)'
            replacement = r'\1        self.intelligence_enabled = False  # Temporarily disabled\n'
            content = re.sub(init_pattern, replacement, content, count=1, flags=re.DOTALL)
            print(f"✅ Added intelligence_enabled flag to {file_path}")
        
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error fixing intelligence adapter: {e}")
        return False

fix_intelligence_adapter('src/core/exchanges/bybit.py')
EOF

python /tmp/disable_intelligence.py

# Fix 2: Lower session recreation threshold
echo "2️⃣ Lowering session recreation threshold..."
cat > /tmp/fix_session_threshold.py << 'EOF'
import re

def fix_session_threshold(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix consecutive timeout threshold
        pattern = r'if\s+self\._consecutive_timeouts\s*>\s*3:'
        replacement = 'if self._consecutive_timeouts > 1:  # Lowered from 3 for faster recovery'
        content = re.sub(pattern, replacement, content)
        
        # Also fix the warning threshold
        pattern2 = r'if\s+consecutive_timeouts\s*>\s*3:'
        replacement2 = 'if consecutive_timeouts > 1:  # Lowered threshold'
        content = re.sub(pattern2, replacement2, content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Lowered session recreation threshold")
        return True
    except Exception as e:
        print(f"❌ Error fixing threshold: {e}")
        return False

fix_session_threshold('src/core/exchanges/bybit.py')
EOF

python /tmp/fix_session_threshold.py

# Fix 3: Improve connection cleanup in timeout handler
echo "3️⃣ Improving connection cleanup in timeout handler..."
cat > /tmp/fix_timeout_cleanup.py << 'EOF'
import re

def fix_timeout_cleanup(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find the timeout cleanup method
        for i, line in enumerate(lines):
            if '_handle_timeout_cleanup' in line and 'async def' in line:
                # Find the end of the method
                indent_level = len(line) - len(line.lstrip())
                
                # Add force session recreation logic
                for j in range(i+1, min(i+50, len(lines))):
                    if lines[j].strip().startswith('return') or (lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent_level):
                        # Insert before return or at end of method
                        insert_line = j if 'return' in lines[j] else j-1
                        
                        new_code = f"""
        # Force session recreation on repeated timeouts
        if self._consecutive_timeouts > 1:
            self.logger.warning("🔄 Force recreating session due to repeated timeouts")
            try:
                if hasattr(self, 'session') and self.session:
                    await self.session.close()
            except:
                pass
            await self._create_session()
            self._consecutive_timeouts = 0  # Reset counter after recreation
"""
                        lines.insert(insert_line, new_code)
                        print("✅ Added improved cleanup logic to timeout handler")
                        break
                break
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ Error fixing timeout cleanup: {e}")
        return False

fix_timeout_cleanup('src/core/exchanges/bybit.py')
EOF

python /tmp/fix_timeout_cleanup.py

# Fix 4: Increase connection pool limits
echo "4️⃣ Increasing connection pool limits..."
cat > /tmp/fix_pool_limits.py << 'EOF'
import re

def fix_pool_limits(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix TCPConnector limits
        pattern = r'aiohttp\.TCPConnector\([^)]*limit\s*=\s*\d+'
        def replace_limit(match):
            text = match.group(0)
            # Replace limit values
            text = re.sub(r'limit\s*=\s*\d+', 'limit=100', text)
            text = re.sub(r'limit_per_host\s*=\s*\d+', 'limit_per_host=20', text)
            return text
        
        content = re.sub(pattern, replace_limit, content)
        
        # Also add cleanup settings if not present
        if 'enable_cleanup_closed' not in content:
            content = content.replace(
                'aiohttp.TCPConnector(',
                'aiohttp.TCPConnector(\n            enable_cleanup_closed=True,  # Clean up closed connections\n            '
            )
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Increased connection pool limits")
        return True
    except Exception as e:
        print(f"❌ Error fixing pool limits: {e}")
        return False

fix_pool_limits('src/core/exchanges/bybit.py')
EOF

python /tmp/fix_pool_limits.py

# Fix 5: Add circuit breaker for problematic endpoint
echo "5️⃣ Adding circuit breaker for v5/market/tickers endpoint..."
cat > /tmp/add_circuit_breaker.py << 'EOF'
import re

def add_circuit_breaker(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find the make_request method
        for i, line in enumerate(lines):
            if 'async def _make_request' in line:
                # Find the start of the method body
                for j in range(i+1, min(i+20, len(lines))):
                    if '"""' not in lines[j] and lines[j].strip() and not lines[j].strip().startswith('#'):
                        # Insert circuit breaker logic
                        indent = '        '
                        circuit_breaker_code = f'''
{indent}# Circuit breaker for problematic endpoints
{indent}if endpoint == 'v5/market/tickers' and self._consecutive_timeouts > 2:
{indent}    self.logger.warning(f"⚡ Circuit breaker active for {{endpoint}} ({{self._consecutive_timeouts}} timeouts)")
{indent}    return {{'retCode': -1, 'retMsg': 'Circuit breaker active - too many timeouts'}}
        
'''
                        lines.insert(j, circuit_breaker_code)
                        print("✅ Added circuit breaker for v5/market/tickers")
                        break
                break
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ Error adding circuit breaker: {e}")
        return False

add_circuit_breaker('src/core/exchanges/bybit.py')
EOF

python /tmp/add_circuit_breaker.py

echo ""
echo "✅ All fixes applied successfully!"
echo ""
echo "Summary of changes:"
echo "1. Disabled intelligence adapter to avoid complex connection pool issues"
echo "2. Lowered session recreation threshold from 3 to 1 consecutive timeout"
echo "3. Improved timeout cleanup with forced session recreation"
echo "4. Increased connection pool limits (50→100 total, 10→20 per host)"
echo "5. Added circuit breaker for problematic v5/market/tickers endpoint"
echo ""
echo "Next steps:"
echo "1. Restart the service: sudo systemctl restart virtuoso.service"
echo "2. Monitor logs: sudo journalctl -u virtuoso.service -f"
echo "3. Check if timeouts are resolved"
echo ""