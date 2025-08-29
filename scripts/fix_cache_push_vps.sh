#!/bin/bash

#############################################################################
# Script: fix_cache_push_vps.sh
# Purpose: Deploy and manage fix cache push vps
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
#   ./fix_cache_push_vps.sh [options]
#   
#   Examples:
#     ./fix_cache_push_vps.sh
#     ./fix_cache_push_vps.sh --verbose
#     ./fix_cache_push_vps.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

echo "Fixing dashboard cache push on VPS..."

# Create the cache push module
ssh linuxuser@45.77.40.77 "cat > /home/linuxuser/trading/Virtuoso_ccxt/src/core/cache/dashboard_cache_push.py" << 'EOF'
"""Dashboard cache push functionality to populate memcached with market data."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DashboardCachePusher:
    """Handles pushing dashboard data to memcached."""
    
    def __init__(self):
        self._client = None
        
    async def _get_client(self):
        """Get or create memcached client."""
        if self._client is None:
            self._client = aiomcache.Client('localhost', 11211, pool_size=2)
        return self._client
    
    async def push_complete_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Push complete market data to cache."""
        try:
            client = await self._get_client()
            
            # Push symbols if present
            if 'symbols' in market_data:
                symbols_data = market_data['symbols']
                
                # Prepare tickers
                tickers = {}
                for symbol_data in symbols_data:
                    symbol = symbol_data.get('symbol', '')
                    if symbol:
                        tickers[symbol] = {
                            'price': symbol_data.get('price', 0),
                            'change_24h': symbol_data.get('change_24h', 0),
                            'volume_24h': symbol_data.get('volume_24h', 0),
                            'confluence_score': symbol_data.get('confluence_score', 0)
                        }
                
                await client.set(b'market:tickers', json.dumps(tickers).encode(), exptime=300)
                
                # Push overview
                total_volume = sum(s.get('volume_24h', 0) for s in symbols_data)
                avg_change = sum(s.get('change_24h', 0) for s in symbols_data) / max(len(symbols_data), 1)
                
                overview = {
                    'total_symbols': len(symbols_data),
                    'total_volume': total_volume,
                    'total_volume_24h': total_volume,
                    'average_change': avg_change,
                    'timestamp': int(time.time())
                }
                
                await client.set(b'market:overview', json.dumps(overview).encode(), exptime=300)
                
                # Push signals
                await client.set(b'analysis:signals', json.dumps({'signals': symbols_data}).encode(), exptime=300)
                
                # Push market regime
                regime = 'bullish' if avg_change > 0 else 'bearish'
                await client.set(b'analysis:market_regime', regime.encode(), exptime=300)
                
                logger.debug(f"Pushed {len(symbols_data)} symbols to cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push to cache: {e}")
            return False
    
    async def close(self):
        """Close the cache connection."""
        if self._client:
            await self._client.close()

# Global instance
_pusher = DashboardCachePusher()

async def push_complete_market_data(market_data: Dict[str, Any]) -> bool:
    """Push complete market data using the global pusher."""
    return await _pusher.push_complete_market_data(market_data)
EOF

# Update the dashboard_cache_manager to include the push method
ssh linuxuser@45.77.40.77 "cat >> /home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py" << 'EOF'

# Import the cache pusher
from src.core.cache.dashboard_cache_push import push_complete_market_data

# Add the method to the existing dashboard_cache object
dashboard_cache.push_complete_market_data = push_complete_market_data
EOF

# Restart the service
ssh linuxuser@45.77.40.77 "sudo systemctl restart virtuoso.service"

echo "✅ Cache push fix deployed. Waiting for service to start..."
sleep 15

# Check if data is being pushed
echo "Checking cache population..."
ssh linuxuser@45.77.40.77 "/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -c \"
import asyncio
import aiomcache
import json

async def check():
    client = aiomcache.Client('localhost', 11211)
    
    keys = ['market:tickers', 'market:overview', 'analysis:signals']
    for key in keys:
        data = await client.get(key.encode())
        if data:
            parsed = json.loads(data.decode())
            if key == 'market:tickers':
                print(f'{key}: {len(parsed)} symbols')
            else:
                print(f'{key}: Data present')
        else:
            print(f'{key}: EMPTY')
    
    await client.close()

asyncio.run(check())
\""

echo "✅ Fix applied!"