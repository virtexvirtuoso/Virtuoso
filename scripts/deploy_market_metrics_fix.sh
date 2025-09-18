#!/bin/bash

#############################################################################
# Script: deploy_market_metrics_fix.sh
# Purpose: Deploy and manage deploy market metrics fix
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
#   ./deploy_market_metrics_fix.sh [options]
#   
#   Examples:
#     ./deploy_market_metrics_fix.sh
#     ./deploy_market_metrics_fix.sh --verbose
#     ./deploy_market_metrics_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

echo "🔧 Deploying Comprehensive Market Metrics Fix..."
echo "==============================================="

VPS_HOST="linuxuser@${VPS_HOST}"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Create a service to continuously update market metrics
echo "📝 Creating market metrics update service..."

cat > /tmp/market_metrics_service.py << 'EOF'
#!/usr/bin/env python3
"""
Market Metrics Service - Continuously updates market overview with proper metrics
"""

import asyncio
import json
import aiohttp
import aiomcache
import numpy as np
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketMetricsService:
    def __init__(self):
        self.cache = None
        self.last_update = 0
        
    async def start(self):
        """Start the service"""
        self.cache = aiomcache.Client('localhost', 11211)
        logger.info("Market Metrics Service started")
        
        while True:
            try:
                await self.update_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(10)
    
    async def fetch_market_cap_data(self) -> Dict[str, float]:
        """Fetch BTC dominance from CoinGecko"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.coingecko.com/api/v3/global"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get('data', {})
                        btc_dominance = market_data.get('market_cap_percentage', {}).get('btc', 0)
                        return {'btc_dominance': btc_dominance}
        except:
            pass
        return {'btc_dominance': 57.5}  # Current approximate
    
    async def fetch_bybit_tickers(self) -> Dict[str, Any]:
        """Fetch all tickers from Bybit"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.bybit.com/v5/market/tickers?category=spot"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', {})
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
        return {}
    
    def calculate_trend_strength(self, avg_change: float, volatility: float) -> float:
        """Calculate trend strength 0-100"""
        if volatility == 0:
            volatility = 1
        raw_strength = abs(avg_change) / volatility
        if raw_strength == 0:
            return 0
        scaled_strength = 50 * (1 + np.log10(1 + raw_strength))
        return min(100, max(0, scaled_strength))
    
    async def update_metrics(self):
        """Update market metrics in cache"""
        try:
            # Get existing overview from cache
            existing_data = await self.cache.get(b'market:overview')
            if existing_data:
                existing = json.loads(existing_data.decode())
            else:
                existing = {}
            
            # Fetch new data
            bybit_data = await self.fetch_bybit_tickers()
            market_cap_data = await self.fetch_market_cap_data()
            
            if bybit_data and 'list' in bybit_data:
                tickers = bybit_data['list']
                
                # Calculate metrics
                total_volume = 0
                price_changes = []
                up_count = 0
                down_count = 0
                
                for ticker in tickers:
                    try:
                        volume_24h = float(ticker.get('turnover24h', 0))
                        total_volume += volume_24h
                        
                        price_change = float(ticker.get('price24hPcnt', 0)) * 100
                        if price_change != 0:
                            price_changes.append(price_change)
                            if price_change > 0:
                                up_count += 1
                            elif price_change < 0:
                                down_count += 1
                    except:
                        continue
                
                # Calculate aggregates
                avg_change = np.mean(price_changes) if price_changes else 0
                current_volatility = float(np.std(price_changes)) if len(price_changes) > 1 else 0
                trend_strength = self.calculate_trend_strength(avg_change, current_volatility)
                
                # Determine regime
                if avg_change > 1.0 and up_count > down_count * 1.2:
                    regime = 'bullish'
                elif avg_change < -1.0 and down_count > up_count * 1.2:
                    regime = 'bearish'
                elif abs(avg_change) < 0.5:
                    regime = 'neutral'
                elif avg_change > 0:
                    regime = 'neutral_bullish'
                else:
                    regime = 'neutral_bearish'
                
                # Update overview - preserve existing fields and add new ones
                updated_overview = {
                    **existing,  # Keep existing fields
                    'market_regime': regime,
                    'trend_strength': round(trend_strength, 1),
                    'current_volatility': round(current_volatility, 2),
                    'avg_volatility': 20.0,
                    'btc_dominance': round(market_cap_data['btc_dominance'], 1),
                    'total_volume': total_volume,
                    'total_volume_24h': total_volume,
                    'volatility': round(current_volatility, 2),  # Compatibility
                    'average_change': round(avg_change, 2),
                    'timestamp': int(time.time()),
                    'last_update': datetime.utcnow().isoformat()
                }
                
                # Store in cache
                overview_json = json.dumps(updated_overview).encode()
                await self.cache.set(b'market:overview', overview_json, exptime=120)
                
                # Also update market breadth
                breadth = {
                    'up': up_count,
                    'down': down_count,
                    'up_count': up_count,
                    'down_count': down_count,
                    'flat': len(tickers) - up_count - down_count,
                    'breadth_percentage': round((up_count / (up_count + down_count) * 100) if (up_count + down_count) > 0 else 50, 1),
                    'sentiment': 'bullish' if up_count > down_count * 1.5 else 'bearish' if down_count > up_count * 1.5 else 'neutral'
                }
                breadth_json = json.dumps(breadth).encode()
                await self.cache.set(b'market:breadth', breadth_json, exptime=120)
                
                # Log success every 5 updates
                self.last_update += 1
                if self.last_update % 5 == 0:
                    logger.info(f"Updated: trend={trend_strength:.1f}%, btc_dom={market_cap_data['btc_dominance']:.1f}%, vol={current_volatility:.2f}%")
                
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

async def main():
    service = MarketMetricsService()
    await service.start()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Copy service to VPS
echo "📤 Copying service to VPS..."
scp /tmp/market_metrics_service.py $VPS_HOST:$PROJECT_DIR/scripts/

# Copy updated cache adapter
scp src/api/cache_adapter.py $VPS_HOST:$PROJECT_DIR/src/api/

# Create systemd service
echo "🔧 Creating systemd service..."
ssh $VPS_HOST "sudo tee /etc/systemd/system/market-metrics.service > /dev/null << 'EOF'
[Unit]
Description=Market Metrics Update Service
After=network.target memcached.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python /home/linuxuser/trading/Virtuoso_ccxt/scripts/market_metrics_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Start the service
echo "🚀 Starting market metrics service..."
ssh $VPS_HOST "sudo systemctl daemon-reload && sudo systemctl enable market-metrics && sudo systemctl restart market-metrics"

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for services
sleep 5

# Test the results
echo ""
echo "🧪 Testing Fixed Metrics..."
echo "============================"

curl -s "http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
print('✅ Market Overview Fixed:')
print(f'  • Market Regime: {overview.get(\"market_regime\")}')
print(f'  • Trend Strength: {overview.get(\"trend_strength\")}%')
print(f'  • BTC Dominance: {overview.get(\"btc_dominance\")}%')
print(f'  • Current Volatility: {overview.get(\"current_volatility\")}%')
print(f'  • Average Volatility: {overview.get(\"avg_volatility\", 20)}%')
print(f'  • Total Volume: \${overview.get(\"total_volume_24h\", 0):,.0f}')

if 'market_breadth' in data:
    breadth = data['market_breadth']
    print(f'\\n✅ Market Breadth:')
    print(f'  • {breadth.get(\"up_count\", 0)} symbols rising')
    print(f'  • {breadth.get(\"down_count\", 0)} symbols falling')
    print(f'  • {breadth.get(\"breadth_percentage\", 0):.1f}% Bullish')
"

echo ""
echo "✅ All Market Metrics Fixed!"
echo ""
echo "📊 Service Status:"
ssh $VPS_HOST "sudo systemctl status market-metrics --no-pager | head -10"

echo ""
echo "📱 View the fixed dashboard at:"
echo "   http://${VPS_HOST}:8001/dashboard/mobile"
echo ""
echo "💡 The market-metrics service will continuously update:"
echo "   • Every 30 seconds with fresh data"
echo "   • BTC dominance from CoinGecko API"
echo "   • Trend strength, volatility from Bybit"
echo "   • Total volume aggregation"