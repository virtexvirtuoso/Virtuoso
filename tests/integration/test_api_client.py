#!/usr/bin/env python3
"""
Test script for Virtuoso Trading System API Client
Demonstrates using the API client SDK
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class VirtuosoClient:
    """Simple async client for testing Virtuoso API."""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def get_health(self) -> Dict[str, Any]:
        """Get system health status."""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()
            
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview."""
        async with self.session.get(f"{self.base_url}/api/dashboard/overview") as response:
            return await response.json()
            
    async def get_signals(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent trading signals."""
        async with self.session.get(
            f"{self.base_url}/api/dashboard/signals",
            params={"limit": limit}
        ) as response:
            return await response.json()
            
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview."""
        async with self.session.get(f"{self.base_url}/api/dashboard/market-overview") as response:
            return await response.json()
            
    async def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        async with self.session.get(f"{self.base_url}/api/dashboard/config") as response:
            return await response.json()

async def main():
    """Test the Virtuoso API client."""
    
    print("="*60)
    print("🚀 Virtuoso Trading System - API Client Test")
    print("="*60)
    
    async with VirtuosoClient() as client:
        
        # 1. Test system health
        print("\n📊 Testing System Health...")
        try:
            health = await client.get_health()
            print(f"✅ System Status: {health.get('status', 'unknown')}")
            
            components = health.get('components', {})
            print("\n📦 Components:")
            for component, status in components.items():
                status_icon = "✅" if status else "❌"
                print(f"  {status_icon} {component}: {status}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            
        # 2. Test dashboard overview
        print("\n📈 Testing Dashboard Overview...")
        try:
            overview = await client.get_dashboard_overview()
            print(f"✅ Active Symbols: {overview.get('active_symbols', 0)}")
            print(f"📊 Market Status: {overview.get('market_status', 'unknown')}")
            
            if 'recent_signals' in overview:
                print(f"📡 Recent Signals: {len(overview['recent_signals'])}")
        except Exception as e:
            print(f"❌ Dashboard overview failed: {e}")
            
        # 3. Test signals endpoint
        print("\n📡 Testing Trading Signals...")
        try:
            signals = await client.get_signals(limit=3)
            if signals:
                print(f"✅ Retrieved {len(signals)} signals")
                for i, signal in enumerate(signals[:3], 1):
                    print(f"\n  Signal {i}:")
                    print(f"    Symbol: {signal.get('symbol', 'N/A')}")
                    print(f"    Type: {signal.get('type', 'N/A')}")
                    print(f"    Score: {signal.get('confluence_score', 0):.2f}")
                    print(f"    Strength: {signal.get('strength', 0):.2%}")
            else:
                print("📭 No signals available")
        except Exception as e:
            print(f"❌ Signals fetch failed: {e}")
            
        # 4. Test market overview
        print("\n📊 Testing Market Overview...")
        try:
            market = await client.get_market_overview()
            print(f"✅ Market data retrieved")
            
            if 'top_gainers' in market:
                print(f"📈 Top Gainers: {len(market['top_gainers'])}")
            if 'top_losers' in market:
                print(f"📉 Top Losers: {len(market['top_losers'])}")
            if 'market_breadth' in market:
                breadth = market['market_breadth']
                print(f"🎯 Market Breadth - Advancing: {breadth.get('advancing', 0)}, Declining: {breadth.get('declining', 0)}")
        except Exception as e:
            print(f"❌ Market overview failed: {e}")
            
        # 5. Test configuration endpoint
        print("\n⚙️ Testing Configuration...")
        try:
            config = await client.get_config()
            print(f"✅ Configuration retrieved")
            
            if 'trading' in config:
                trading = config['trading']
                symbols = trading.get('symbols', [])
                print(f"📍 Monitored Symbols: {len(symbols)}")
                if symbols:
                    print(f"   First 5: {', '.join(symbols[:5])}")
                    
                timeframes = trading.get('timeframes', [])
                print(f"⏰ Timeframes: {', '.join(timeframes)}")
        except Exception as e:
            print(f"❌ Config fetch failed: {e}")
    
    print("\n" + "="*60)
    print("✅ API Client Test Complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())