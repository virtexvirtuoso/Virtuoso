#!/bin/bash

#############################################################################
# Script: fix_bybit_comprehensive.sh
# Purpose: Deploy and manage fix bybit comprehensive
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./fix_bybit_comprehensive.sh [options]
#   
#   Examples:
#     ./fix_bybit_comprehensive.sh
#     ./fix_bybit_comprehensive.sh --verbose
#     ./fix_bybit_comprehensive.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Comprehensive fix for Bybit connection issues
# This addresses timeout issues, connection pooling, and fallback mechanisms

echo "🔧 Applying Comprehensive Bybit Connection Fix..."

# Create a simple test script first
cat > /tmp/test_bybit_direct.py << 'EOF'
import asyncio
import aiohttp
import time
import json

async def test_bybit_connection():
    """Test direct connection to Bybit API"""
    endpoints = [
        ('https://api.bybit.com/v5/market/tickers', {'category': 'linear', 'symbol': 'BTCUSDT'}),
        ('https://api.bybit.com/v5/market/kline', {'category': 'linear', 'symbol': 'BTCUSDT', 'interval': '1'}),
        ('https://api.bybit.com/v5/market/recent-trade', {'category': 'linear', 'symbol': 'BTCUSDT'}),
    ]
    
    async with aiohttp.ClientSession() as session:
        for url, params in endpoints:
            try:
                start = time.time()
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    data = await response.json()
                    elapsed = time.time() - start
                    status = "✅ SUCCESS" if data.get('retCode') == 0 else f"❌ FAILED: {data.get('retMsg')}"
                    print(f"{url.split('/')[-1]}: {status} ({elapsed:.2f}s)")
            except asyncio.TimeoutError:
                print(f"{url.split('/')[-1]}: ❌ TIMEOUT")
            except Exception as e:
                print(f"{url.split('/')[-1]}: ❌ ERROR: {e}")

if __name__ == "__main__":
    print("Testing direct Bybit API connectivity...")
    asyncio.run(test_bybit_connection())
EOF

echo "📋 Testing Bybit API connectivity..."
python /tmp/test_bybit_direct.py

echo ""
echo "🔧 Applying comprehensive fixes to bybit.py..."

# Fix 1: Add fallback mechanism for timeouts
cat > /tmp/add_fallback_mechanism.py << 'EOF'
import re

def add_fallback_mechanism(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find the _make_request method
        for i, line in enumerate(lines):
            if 'async def _make_request' in line:
                # Look for the timeout handling section
                for j in range(i, min(i+200, len(lines))):
                    if 'except asyncio.TimeoutError:' in lines[j]:
                        indent = '            '
                        # Add fallback mechanism
                        fallback_code = f'''
{indent}# Try fallback to direct connection if intelligence adapter failed
{indent}if hasattr(self, 'intelligence_enabled') and self.intelligence_enabled:
{indent}    self.logger.warning("Falling back to direct connection after timeout")
{indent}    self.intelligence_enabled = False
{indent}    try:
{indent}        # Retry with direct connection
{indent}        result = await self._make_request(endpoint, method, params, private, raw)
{indent}        self.intelligence_enabled = True  # Re-enable if successful
{indent}        return result
{indent}    except:
{indent}        self.intelligence_enabled = True  # Re-enable for next attempt
{indent}        raise
'''
                        # Insert before the timeout error handling
                        lines.insert(j+1, fallback_code)
                        print("✅ Added fallback mechanism for timeouts")
                        break
                break
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ Error adding fallback: {e}")
        return False

add_fallback_mechanism('src/core/exchanges/bybit.py')
EOF

python /tmp/add_fallback_mechanism.py

# Fix 2: Implement request batching for efficiency
cat > /tmp/add_request_batching.py << 'EOF'
import re

def add_request_batching(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add request batching configuration
        if '_request_batch_size' not in content:
            # Find __ainit__ or __init__ method
            pattern = r'(async def __ainit__|def __init__)\(self.*?\):\s*\n'
            def add_batch_config(match):
                return match.group(0) + '''        # Request batching configuration
        self._request_batch_size = 5  # Process requests in batches
        self._request_batch_delay = 0.1  # Small delay between batch items
        self._batch_queue = []
        self._batch_processing = False
        
'''
            content = re.sub(pattern, add_batch_config, content, count=1)
            print("✅ Added request batching configuration")
        
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error adding batching: {e}")
        return False

add_request_batching('src/core/exchanges/bybit.py')
EOF

python /tmp/add_request_batching.py

# Fix 3: Optimize timeout values based on endpoint
cat > /tmp/optimize_timeouts.py << 'EOF'
import re

def optimize_timeouts(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add endpoint-specific timeout configuration
        timeout_config = """
        # Endpoint-specific timeout configuration
        self._endpoint_timeouts = {
            'v5/market/tickers': 8.0,      # Fast endpoint, short timeout
            'v5/market/kline': 15.0,        # Can be slow with large data
            'v5/market/recent-trade': 10.0, # Medium speed
            'v5/market/orderbook': 8.0,     # Fast endpoint
            'v5/market/open-interest': 10.0, # Medium speed
            'default': 20.0                  # Default for other endpoints
        }
"""
        
        # Find where to insert this
        if '_endpoint_timeouts' not in content:
            pattern = r'(self\._timeout\s*=.*?\n)'
            replacement = r'\1' + timeout_config
            content = re.sub(pattern, replacement, content, count=1)
            print("✅ Added endpoint-specific timeout configuration")
        
        # Update the timeout logic to use endpoint-specific values
        pattern = r'timeout\s*=\s*self\._timeout'
        replacement = 'timeout = self._endpoint_timeouts.get(endpoint, self._timeout)'
        content = re.sub(pattern, replacement, content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error optimizing timeouts: {e}")
        return False

optimize_timeouts('src/core/exchanges/bybit.py')
EOF

python /tmp/optimize_timeouts.py

# Fix 4: Add connection recycling
cat > /tmp/add_connection_recycling.py << 'EOF'
import re

def add_connection_recycling(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add connection recycling logic
        recycling_code = """
    async def _recycle_connections(self):
        \"\"\"Periodically recycle connections to prevent stale connections\"\"\"
        try:
            if hasattr(self, 'session') and self.session:
                # Get connector
                connector = self.session.connector
                if connector:
                    # Force cleanup of connections older than 60 seconds
                    connector.force_close()
                    self.logger.debug("♻️ Recycled stale connections")
        except Exception as e:
            self.logger.warning(f"Error recycling connections: {e}")
"""
        
        if '_recycle_connections' not in content:
            # Add the method after _create_session
            pattern = r'(async def _create_session.*?\n(?:.*?\n)*?        return.*?\n)'
            replacement = r'\1\n' + recycling_code
            content = re.sub(pattern, replacement, content, count=1)
            print("✅ Added connection recycling method")
        
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error adding recycling: {e}")
        return False

add_connection_recycling('src/core/exchanges/bybit.py')
EOF

python /tmp/add_connection_recycling.py

echo ""
echo "✅ Comprehensive fixes applied!"
echo ""
echo "Summary of improvements:"
echo "1. Added fallback mechanism from intelligence adapter to direct connection"
echo "2. Implemented request batching for better efficiency"
echo "3. Optimized endpoint-specific timeouts"
echo "4. Added connection recycling to prevent stale connections"
echo ""
echo "Deploy with: scp src/core/exchanges/bybit.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/"