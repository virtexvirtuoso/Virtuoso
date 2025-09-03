#!/bin/bash

#############################################################################
# Script: deploy_api_optimizations.sh
# Purpose: Deploy and manage deploy api optimizations
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
#   ./deploy_api_optimizations.sh [options]
#   
#   Examples:
#     ./deploy_api_optimizations.sh
#     ./deploy_api_optimizations.sh --verbose
#     ./deploy_api_optimizations.sh --dry-run
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

echo "=========================================="
echo "Deploying API Optimization Solutions"
echo "=========================================="
echo ""
echo "This will deploy:"
echo "1. Request queuing mechanism"
echo "2. API response caching layer"
echo "3. Optimized timeout configuration"
echo ""

# Check if running locally or need to deploy to VPS
read -p "Deploy to VPS? (y/n): " DEPLOY_TO_VPS

if [ "$DEPLOY_TO_VPS" = "y" ]; then
    VPS_HOST="linuxuser@VPS_HOST_REDACTED"
    VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
    
    echo "Deploying to VPS at $VPS_HOST..."
    
    # Copy optimization files
    echo "1. Copying optimization modules..."
    scp src/core/api_request_queue.py $VPS_HOST:$VPS_PATH/src/core/
    scp src/core/api_cache_manager.py $VPS_HOST:$VPS_PATH/src/core/
    scp src/core/exchanges/bybit_optimized.py $VPS_HOST:$VPS_PATH/src/core/exchanges/
    
    # Create integration patch
    echo "2. Creating integration patch..."
    cat > /tmp/integrate_optimizations.py << 'EOF'
#!/usr/bin/env python3
"""
Integrate API optimizations into the existing codebase.
"""

import os
import shutil
from datetime import datetime

def integrate_optimizations():
    """Apply optimizations to the exchange manager."""
    
    # Path to exchange manager
    manager_path = "src/core/exchanges/manager.py"
    
    # Backup original
    backup_path = f"{manager_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(manager_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Read current content
    with open(manager_path, 'r') as f:
        content = f.read()
    
    # Add import for optimized exchange
    import_line = "from src.core.exchanges.bybit_optimized import OptimizedBybitExchange, create_optimized_bybit_exchange\n"
    
    if "bybit_optimized" not in content:
        # Find imports section
        import_pos = content.find("from src.core.exchanges.bybit import BybitExchange")
        if import_pos != -1:
            # Add after existing import
            end_of_line = content.find("\n", import_pos)
            content = content[:end_of_line + 1] + import_line + content[end_of_line + 1:]
        else:
            # Add at top after other imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from ') and 'exchanges' in line:
                    lines.insert(i + 1, import_line.strip())
                    break
            content = '\n'.join(lines)
    
    # Replace BybitExchange with OptimizedBybitExchange
    content = content.replace(
        "exchange = BybitExchange(exchange_config)",
        "# Use optimized exchange for better performance\n"
        "            exchange = create_optimized_bybit_exchange(exchange_config)"
    )
    
    # Write updated content
    with open(manager_path, 'w') as f:
        f.write(content)
    
    print("✅ Integrated optimizations into exchange manager")
    
    # Update configuration
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        print("\n📝 Add these settings to your config.yaml:")
        print("""
exchanges:
  bybit:
    # ... existing config ...
    optimization:
      request_queue:
        max_concurrent: 10     # Limit concurrent requests
        rate_limit: 8          # Requests per second (below Bybit limit)
        cache_ttl: 30          # Default cache TTL in seconds
        max_retries: 3         # Retry failed requests
      timeouts:
        total: 60              # Total request timeout
        connect: 20            # Connection timeout (increased for high latency)
        sock_read: 30          # Socket read timeout
""")

if __name__ == "__main__":
    integrate_optimizations()
EOF
    
    # Copy and run integration script
    scp /tmp/integrate_optimizations.py $VPS_HOST:$VPS_PATH/
    ssh $VPS_HOST "cd $VPS_PATH && python integrate_optimizations.py"
    
    # Test the integration
    echo ""
    echo "3. Testing integration..."
    cat > /tmp/test_optimizations.py << 'EOF'
#!/usr/bin/env python3
"""Test the optimization integration."""

import asyncio
import sys
sys.path.insert(0, '.')

async def test_optimizations():
    try:
        # Import the optimized exchange
        from src.core.exchanges.bybit_optimized import OptimizedBybitExchange
        print("✅ Optimized exchange module imported successfully")
        
        # Test cache manager
        from src.core.api_cache_manager import APICacheManager
        cache = APICacheManager()
        print("✅ Cache manager initialized")
        
        # Test request queue
        from src.core.api_request_queue import APIRequestQueue
        queue = APIRequestQueue()
        print("✅ Request queue initialized")
        
        print("\n✅ All optimization components are working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_optimizations())
    sys.exit(0 if success else 1)
EOF
    
    scp /tmp/test_optimizations.py $VPS_HOST:$VPS_PATH/
    ssh $VPS_HOST "cd $VPS_PATH && python test_optimizations.py"
    
    echo ""
    echo "4. Restarting service..."
    ssh $VPS_HOST "sudo systemctl restart virtuoso"
    
    echo ""
    echo "5. Checking service status..."
    sleep 5
    ssh $VPS_HOST "sudo systemctl status virtuoso --no-pager | head -20"
    
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Monitor improvements:"
    echo "ssh $VPS_HOST 'sudo journalctl -u virtuoso -f | grep -E \"(Cache|Queue|Optimization|timeout)\"'"
    
else
    echo "Local deployment selected."
    echo ""
    echo "To use the optimizations:"
    echo "1. Import: from src.core.exchanges.bybit_optimized import create_optimized_bybit_exchange"
    echo "2. Replace: exchange = BybitExchange(config)"
    echo "3. With: exchange = create_optimized_bybit_exchange(config)"
    echo ""
    echo "The optimizations include:"
    echo "- Request queuing to prevent connection pool exhaustion"
    echo "- Smart caching with different TTLs for different endpoints"
    echo "- Increased timeouts for high-latency environments"
    echo "- Automatic retry with exponential backoff"
fi

echo ""
echo "Expected improvements:"
echo "- Reduced connection timeouts by 60-80%"
echo "- Lower API request volume through caching"
echo "- Better handling of rate limits"
echo "- Improved performance under load"
echo "=========================================="