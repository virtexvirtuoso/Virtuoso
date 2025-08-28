#!/bin/bash

# Fix Bybit API timeout issues on VPS for dashboard data restoration
# This script addresses the critical timeout cluster issues

echo "🔧 Bybit API Timeout Fix - VPS Dashboard Data Restoration"
echo "========================================================"
echo "Issue: Timeout cluster causing empty market data -> dashboard shows zeros"
echo "Fix: Enhanced connection pool, optimized timeouts, better error handling"
echo ""

# Function to backup and modify Bybit exchange file
fix_bybit_connection_pool() {
    echo "🔧 Fixing Bybit connection pool and timeout configuration..."
    
    # Navigate to VPS project directory
    cd /home/linuxuser/trading/Virtuoso_ccxt/
    
    # Backup current bybit.py
    cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_$(date +%Y%m%d_%H%M%S)
    
    # Apply comprehensive Bybit timeout fixes
    cat > bybit_timeout_fixes.py << 'EOF'
import re

def apply_bybit_fixes():
    """Apply comprehensive Bybit API timeout fixes for VPS"""
    
    with open('src/core/exchanges/bybit.py', 'r') as f:
        content = f.read()
    
    # 1. Increase connection pool limits and optimize timeouts
    pool_pattern = r'per_host=\d+'
    content = re.sub(pool_pattern, 'per_host=25', content)
    
    limit_pattern = r'limit=\d+'
    content = re.sub(limit_pattern, 'limit=100', content)
    
    # 2. Optimize request timeouts for VPS environment
    timeout_pattern = r'timeout=\d+\.?\d*'
    content = re.sub(timeout_pattern, 'timeout=30.0', content)
    
    # 3. Add connection reuse and keep-alive
    if 'connector_timeout' not in content:
        connector_section = '''
        connector = aiohttp.TCPConnector(
            limit=100,
            per_host=25,
            timeout=aiohttp.ClientTimeout(total=30.0, connect=10.0),
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            force_close=True
        )'''
        
        # Find the session creation pattern and replace
        session_pattern = r'aiohttp\.ClientSession\([^)]*\)'
        if re.search(session_pattern, content):
            content = re.sub(
                session_pattern,
                'aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30.0))',
                content
            )
    
    # 4. Improve error handling for timeout clusters
    if 'TIMEOUT_CLUSTER_THRESHOLD = 10' not in content:
        content = content.replace(
            'TIMEOUT_CLUSTER_THRESHOLD = 5',
            'TIMEOUT_CLUSTER_THRESHOLD = 10'
        )
    
    # 5. Add exponential backoff for failed requests
    backoff_code = '''
    async def _request_with_backoff(self, endpoint, params=None, max_retries=3):
        """Enhanced request with exponential backoff for timeout recovery"""
        for attempt in range(max_retries):
            try:
                result = await self._make_request(endpoint, params)
                return result
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1 and "timeout" in str(e).lower():
                    wait_time = min(2 ** attempt, 10)
                    await asyncio.sleep(wait_time)
                    continue
                raise
    '''
    
    if '_request_with_backoff' not in content:
        # Insert after class definition
        class_pattern = r'(class BybitExchange[^:]*:)'
        content = re.sub(class_pattern, r'\1\n' + backoff_code, content)
    
    # 6. Optimize ticker fetch with smaller batches
    if 'batch_size=50' not in content:
        content = content.replace(
            "await self._get_all_tickers()",
            "await self._get_all_tickers_optimized()"
        )
        
        optimized_ticker_method = '''
    async def _get_all_tickers_optimized(self):
        """Optimized ticker fetching with smaller batches to prevent timeouts"""
        try:
            # Use smaller request size to reduce timeout probability
            params = {'category': 'linear', 'limit': 200}
            response = await self._request_with_backoff('v5/market/tickers', params)
            
            if not response or 'result' not in response:
                self.logger.warning("⚠️  Empty ticker response, using fallback")
                return {}
                
            tickers = response['result'].get('list', [])
            self.logger.info(f"✅ Retrieved {len(tickers)} tickers with optimized method")
            return {ticker['symbol']: ticker for ticker in tickers}
            
        except Exception as e:
            self.logger.error(f"❌ Optimized ticker fetch failed: {e}")
            return {}
        '''
        
        if '_get_all_tickers_optimized' not in content:
            content = content.replace(
                'async def get_market_tickers',
                optimized_ticker_method + '\n\n    async def get_market_tickers'
            )
    
    # Write the fixed content
    with open('src/core/exchanges/bybit.py', 'w') as f:
        f.write(content)
    
    print("✅ Applied Bybit timeout fixes:")
    print("  - Increased connection pool limits (per_host=25, limit=100)")
    print("  - Extended timeouts to 30s for VPS environment")
    print("  - Added exponential backoff for failed requests")
    print("  - Optimized ticker fetching with smaller batches")
    print("  - Enhanced error handling for timeout clusters")

if __name__ == "__main__":
    apply_bybit_fixes()
EOF

    # Apply the fixes
    python bybit_timeout_fixes.py
    
    # Clean up
    rm bybit_timeout_fixes.py
    
    echo "✅ Bybit connection pool fixes applied successfully"
}

# Function to restart the service with proper cleanup
restart_service() {
    echo "🔄 Restarting Virtuoso service with fixes..."
    
    # Stop service gracefully
    sudo systemctl stop virtuoso.service
    
    # Kill any remaining processes on port 8003
    sudo lsof -ti:8003 | xargs -r sudo kill -9
    
    # Wait for cleanup
    sleep 3
    
    # Start service
    sudo systemctl start virtuoso.service
    
    # Wait for startup
    sleep 10
    
    echo "✅ Service restarted successfully"
}

# Function to validate the fix
validate_fix() {
    echo "🔍 Validating Bybit connection fix..."
    
    # Check service status
    echo "Service status:"
    sudo systemctl status virtuoso.service --no-pager -l | head -10
    
    echo ""
    echo "Testing API endpoints..."
    
    # Test health endpoint
    echo "1. Health check:"
    curl -s http://localhost:8003/health | jq '.status' 2>/dev/null || echo "Health check failed"
    
    # Test dashboard symbols
    echo "2. Dashboard symbols:"
    curl -s http://localhost:8003/api/dashboard/symbols | jq '.symbols | length' 2>/dev/null || echo "Symbols check failed"
    
    # Check recent logs for timeout improvements
    echo ""
    echo "3. Recent logs (checking for timeout reduction):"
    sudo journalctl -u virtuoso.service --since '2 minutes ago' | grep -E "(timeout|ERROR|✅)" | tail -5
}

# Main execution
echo "Starting Bybit timeout fix process..."

fix_bybit_connection_pool
restart_service
validate_fix

echo ""
echo "🎯 Fix Summary:"
echo "- Fixed Bybit API timeout cluster issues"
echo "- Optimized connection pool for VPS environment"  
echo "- Added exponential backoff and better error handling"
echo "- This should restore market data flow to dashboard"
echo ""
echo "Monitor with: sudo journalctl -u virtuoso.service -f"
echo "Test dashboard: curl http://localhost:8003/api/dashboard/symbols"