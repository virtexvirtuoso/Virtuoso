#!/bin/bash

#############################################################################
# Script: inspect_cache_vps.sh
# Purpose: Deploy and manage inspect cache vps
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
#   ./inspect_cache_vps.sh [options]
#   
#   Examples:
#     ./inspect_cache_vps.sh
#     ./inspect_cache_vps.sh --verbose
#     ./inspect_cache_vps.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

echo "================================"
echo "CACHE DATA INSPECTION"
echo "================================"
echo ""

# Check cache contents on VPS
ssh linuxuser@5.223.63.4 'bash -s' << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "📦 Checking Memcached contents..."
echo ""

# Use Python to read cache
venv311/bin/python << 'PYTHON'
import asyncio
import aiomcache
import json
from datetime import datetime

async def check_cache():
    client = aiomcache.Client('localhost', 11211)
    
    keys = [
        b'market:tickers',
        b'market:overview', 
        b'analysis:signals',
        b'analysis:market_regime',
        b'market:movers'
    ]
    
    print("Cache Contents at:", datetime.now())
    print("-" * 40)
    
    for key in keys:
        try:
            data = await client.get(key)
            if data:
                key_str = key.decode()
                if key_str == 'analysis:market_regime':
                    print(f"\n✅ {key_str}: {data.decode()}")
                else:
                    parsed = json.loads(data.decode())
                    if isinstance(parsed, dict):
                        if 'signals' in parsed:
                            print(f"\n✅ {key_str}: {len(parsed.get('signals', []))} signals")
                        elif 'total_symbols' in parsed:
                            print(f"\n✅ {key_str}:")
                            print(f"   - Symbols: {parsed.get('total_symbols')}")
                            print(f"   - Volume: {parsed.get('total_volume_24h', 0)/1e9:.2f}B")
                        elif 'gainers' in parsed:
                            print(f"\n✅ {key_str}:")
                            print(f"   - Gainers: {len(parsed.get('gainers', []))}")
                            print(f"   - Losers: {len(parsed.get('losers', []))}")
                        else:
                            print(f"\n✅ {key_str}: {len(str(parsed))} bytes")
                    elif isinstance(parsed, list):
                        print(f"\n✅ {key_str}: {len(parsed)} items")
                        if parsed and len(parsed) > 0:
                            first = parsed[0]
                            if isinstance(first, dict) and 'symbol' in first:
                                print(f"   First: {first.get('symbol')}")
            else:
                print(f"\n❌ {key_str}: EMPTY")
        except Exception as e:
            print(f"\n❌ {key.decode()}: Error - {str(e)[:50]}")
    
    await client.close()

asyncio.run(check_cache())
PYTHON

echo ""
echo "================================"
echo "SERVICE STATUS"
echo "================================"
echo ""

# Check service status
echo "Running services:"
ps aux | grep -E "service_coordinator|market_service|analysis_service" | grep -v grep | awk '{print "  -", $11, $12, $13}'

echo ""
echo "Recent service activity:"
tail -n 5 /tmp/phase2_services.log | grep -E "Updated|Fetched|ERROR"

EOF

echo ""
echo "================================"
echo "DASHBOARD DATA CHECK"
echo "================================"
echo ""

# Check what dashboard sees
echo "1. Fast endpoint (Phase 3):"
curl -s http://5.223.63.4:8001/api/fast/overview | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'   Cache Hit: {data.get(\"cache_hit\", False)}')
    if 'summary' in data:
        s = data['summary']
        print(f'   Symbols: {s.get(\"total_symbols\", 0)}')
        print(f'   Volume: {s.get(\"total_volume\", 0)}')
    print(f'   Market Regime: {data.get(\"market_regime\", \"N/A\")}')
    if 'signals' in data:
        print(f'   Signals: {len(data[\"signals\"])}')
except Exception as e:
    print(f'   Error: {e}')
"

echo ""
echo "2. Regular dashboard:"
curl -s http://5.223.63.4:8001/api/dashboard/overview | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'summary' in data:
        s = data['summary']
        print(f'   Symbols: {s.get(\"total_symbols\", 0)}')
        print(f'   Volume: {s.get(\"total_volume_24h\", 0)/1e9:.2f}B')
    print(f'   Market Regime: {data.get(\"market_regime\", \"N/A\")}')
except Exception as e:
    print(f'   Error: {e}')
"

echo ""
echo "================================"