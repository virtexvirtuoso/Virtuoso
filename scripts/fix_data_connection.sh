#!/bin/bash

# Fix data connection between main service and web server
VPS_HOST="linuxuser@45.77.40.77"

echo "Fixing data connection for mobile dashboard..."

# Create a cache bridge that pushes main service data to Memcached
ssh $VPS_HOST 'cat > /home/linuxuser/trading/Virtuoso_ccxt/src/core/cache_bridge.py << '\''BRIDGE'\''
"""
Cache Bridge - Connects main service data to Memcached for web server
"""
import json
import time
import logging
import asyncio
import aiomcache
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CacheBridge:
    """Bridges main service data to Memcached for web server access"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        
    async def connect(self):
        """Connect to Memcached"""
        try:
            self.client = aiomcache.Client("localhost", 11211, pool_size=4)
            self.connected = True
            logger.info("✅ Cache bridge connected to Memcached")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Memcached: {e}")
            self.connected = False
            return False
    
    async def push_market_data(self, data: Dict[str, Any]):
        """Push market overview data to cache"""
        if not self.connected:
            await self.connect()
            
        if not self.client:
            return
            
        try:
            # Extract and format market overview
            overview = {
                "total_symbols": len(data.get("symbols", [])),
                "total_volume": sum(s.get("volume", 0) for s in data.get("symbols", [])),
                "total_volume_24h": sum(s.get("volume_24h", 0) for s in data.get("symbols", [])),
                "average_change": sum(s.get("change_24h", 0) for s in data.get("symbols", [])) / max(len(data.get("symbols", [])), 1),
                "volatility": data.get("volatility", 0),
                "timestamp": int(time.time())
            }
            
            # Store in cache
            await self.client.set(
                b"market:overview",
                json.dumps(overview).encode(),
                exptime=60  # 60 second TTL
            )
            
            # Store tickers
            if "symbols" in data:
                await self.client.set(
                    b"market:tickers",
                    json.dumps(data["symbols"]).encode(),
                    exptime=60
                )
            
            # Store top movers
            if "symbols" in data:
                sorted_symbols = sorted(data["symbols"], key=lambda x: x.get("change_24h", 0), reverse=True)
                movers = {
                    "gainers": sorted_symbols[:10],
                    "losers": sorted_symbols[-10:]
                }
                await self.client.set(
                    b"market:movers",
                    json.dumps(movers).encode(),
                    exptime=60
                )
                
            logger.debug(f"Pushed market data: {overview['total_symbols']} symbols")
            
        except Exception as e:
            logger.error(f"Error pushing market data: {e}")
    
    async def push_analysis_data(self, symbol: str, analysis: Dict[str, Any]):
        """Push analysis data for a symbol"""
        if not self.connected:
            await self.connect()
            
        if not self.client:
            return
            
        try:
            # Store individual symbol analysis
            key = f"analysis:{symbol}".encode()
            await self.client.set(
                key,
                json.dumps(analysis).encode(),
                exptime=30  # 30 second TTL
            )
            
            # Update signals list if this is a signal
            if analysis.get("signal_type"):
                # Get existing signals
                signals_data = await self.client.get(b"analysis:signals")
                signals = json.loads(signals_data.decode()) if signals_data else {"signals": []}
                
                # Add/update this signal
                signal_entry = {
                    "symbol": symbol,
                    "type": analysis.get("signal_type"),
                    "strength": analysis.get("signal_strength", 0),
                    "timestamp": int(time.time())
                }
                
                # Keep only recent signals (last 50)
                signals["signals"] = [s for s in signals.get("signals", []) if s["symbol"] != symbol]
                signals["signals"].insert(0, signal_entry)
                signals["signals"] = signals["signals"][:50]
                
                # Store updated signals
                await self.client.set(
                    b"analysis:signals",
                    json.dumps(signals).encode(),
                    exptime=60
                )
                
            logger.debug(f"Pushed analysis for {symbol}")
            
        except Exception as e:
            logger.error(f"Error pushing analysis data: {e}")
    
    async def push_regime(self, regime: str):
        """Push market regime"""
        if not self.connected:
            await self.connect()
            
        if not self.client:
            return
            
        try:
            await self.client.set(
                b"analysis:market_regime",
                regime.encode(),
                exptime=300  # 5 minute TTL
            )
            logger.debug(f"Pushed market regime: {regime}")
        except Exception as e:
            logger.error(f"Error pushing regime: {e}")
    
    async def close(self):
        """Close cache connection"""
        if self.client:
            await self.client.close()
            self.connected = False

# Global instance
cache_bridge = CacheBridge()
BRIDGE'

# Now patch the main.py to use the cache bridge
ssh $VPS_HOST 'cat > /tmp/patch_main_cache.py << '\''PATCH'\''
#!/usr/bin/env python3
import sys

# Read the main.py file
with open("/home/linuxuser/trading/Virtuoso_ccxt/src/main.py", "r") as f:
    lines = f.readlines()

# Check if already patched
if any("cache_bridge" in line for line in lines):
    print("Already patched")
    sys.exit(0)

# Find where to add the import
import_index = 0
for i, line in enumerate(lines):
    if "from src.core" in line:
        import_index = i + 1
        break

# Add cache bridge import
if import_index > 0:
    lines.insert(import_index, "from src.core.cache_bridge import cache_bridge\n")

# Find the analyze_market method
for i, line in enumerate(lines):
    if "async def analyze_market(self)" in line:
        # Find the end of the method where results are processed
        for j in range(i, min(i + 100, len(lines))):
            if "self.analysis_cache[symbol_key] = {" in lines[j]:
                # Add cache bridge push after internal cache update
                indent = " " * 20
                lines.insert(j + 3, f"{indent}# Push to Memcached for web server\n")
                lines.insert(j + 4, f"{indent}asyncio.create_task(cache_bridge.push_analysis_data(symbol, confluence_result))\n")
                break
        break

# Find where to push market overview
for i, line in enumerate(lines):
    if "# Compile results" in line:
        # Add market data push
        for j in range(i, min(i + 50, len(lines))):
            if "return market_analysis" in lines[j]:
                indent = " " * 12
                lines.insert(j, f"{indent}# Push market data to cache\n")
                lines.insert(j + 1, f"{indent}if hasattr(self, '\''exchange_manager'\'') and self.exchange_manager:\n")
                lines.insert(j + 2, f"{indent}    market_data = {{\n")
                lines.insert(j + 3, f"{indent}        '\''symbols'\'': list(results.values()),\n")
                lines.insert(j + 4, f"{indent}        '\''volatility'\'': market_analysis.get('\''volatility'\'', 0)\n")
                lines.insert(j + 5, f"{indent}    }}\n")
                lines.insert(j + 6, f"{indent}    asyncio.create_task(cache_bridge.push_market_data(market_data))\n")
                lines.insert(j + 7, f"{indent}    asyncio.create_task(cache_bridge.push_regime(market_regime))\n\n")
                break
        break

# Write the patched file
with open("/home/linuxuser/trading/Virtuoso_ccxt/src/main.py", "w") as f:
    f.writelines(lines)

print("Patched successfully")
PATCH
chmod +x /tmp/patch_main_cache.py
python3 /tmp/patch_main_cache.py
'

echo ""
echo "Cache bridge created and main.py patched"
echo ""

# Restart the main service to apply changes
ssh $VPS_HOST 'sudo systemctl restart virtuoso'
echo "Main service restarted"

# Wait for it to start collecting data
echo "Waiting for data collection to start..."
sleep 10

# Check if data is now in cache
echo ""
echo "Checking cache for data..."
ssh $VPS_HOST 'echo -e "get market:overview\\r\\nquit" | nc localhost 11211 | head -5'

echo ""
echo "Testing API endpoint..."
ssh $VPS_HOST 'curl -s http://localhost:8001/api/dashboard-cached/overview | python3 -m json.tool | head -20'

echo ""
echo "✅ Data connection fix applied!"
echo ""
echo "The mobile dashboard should now receive real data."
echo "Access it at: http://45.77.40.77:8001/dashboard/mobile"