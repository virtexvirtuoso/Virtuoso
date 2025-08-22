#!/usr/bin/env python3
"""
Verify data flow is working after fixes
"""
import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://45.77.40.77:8001"

async def check_data_flow():
    """Check if all data is flowing correctly"""
    
    print("=" * 60)
    print("DATA FLOW VERIFICATION")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print("-" * 60)
    
    issues = []
    successes = []
    
    async with aiohttp.ClientSession() as session:
        # Check different endpoints
        endpoints = [
            ('/api/dashboard/overview', 'Regular Dashboard'),
            ('/api/dashboard-cached/overview', 'Cached Dashboard'),
            ('/api/dashboard-cached/mobile-data', 'Mobile Data'),
            ('/api/fast/overview', 'Fast Dashboard'),
            ('/api/fast/signals', 'Fast Signals'),
            ('/api/fast/movers', 'Fast Movers'),
        ]
        
        for endpoint, name in endpoints:
            try:
                async with session.get(f'{BASE_URL}{endpoint}', timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"\n✅ {name} ({endpoint}):")
                        
                        # Check for signals
                        if 'signals' in data:
                            signals = data.get('signals', [])
                            if signals:
                                print(f"   Signals: {len(signals)} items")
                                if len(signals) > 0:
                                    first = signals[0]
                                    print(f"   First signal: {first.get('symbol', 'N/A')} - Score: {first.get('score', 0)}")
                                    successes.append(f"{name}: Signals working")
                            else:
                                print(f"   ⚠️  Signals: EMPTY")
                                issues.append(f"{name}: No signals")
                        
                        # Check for volume (field name fix)
                        if 'summary' in data:
                            summary = data['summary']
                            volume = summary.get('total_volume', 0)
                            if volume > 0:
                                print(f"   Volume: {volume/1e9:.2f}B ✅")
                                successes.append(f"{name}: Volume field fixed")
                            else:
                                print(f"   Volume: 0 ❌")
                                issues.append(f"{name}: Volume still 0")
                        
                        # Check for market overview
                        if 'market_overview' in data:
                            overview = data['market_overview']
                            volume = overview.get('total_volume_24h', 0)
                            regime = overview.get('market_regime', 'unknown')
                            print(f"   Market Volume: {volume/1e9:.2f}B")
                            print(f"   Market Regime: {regime}")
                            if volume > 0:
                                successes.append(f"{name}: Market overview working")
                        
                        # Check for movers
                        if 'top_movers' in data:
                            movers = data['top_movers']
                            gainers = len(movers.get('gainers', []))
                            losers = len(movers.get('losers', []))
                            if gainers > 0 and losers > 0:
                                print(f"   Top Movers: {gainers} gainers, {losers} losers ✅")
                                successes.append(f"{name}: Movers working")
                            else:
                                print(f"   Top Movers: {gainers} gainers, {losers} losers ⚠️")
                                if gainers == 0:
                                    issues.append(f"{name}: No gainers")
                                if losers == 0:
                                    issues.append(f"{name}: No losers")
                        
                        # Check for confluence scores
                        if 'confluence_scores' in data:
                            scores = data['confluence_scores']
                            if scores:
                                print(f"   Confluence Scores: {len(scores)} items ✅")
                                successes.append(f"{name}: Confluence scores working")
                            else:
                                print(f"   Confluence Scores: EMPTY ⚠️")
                                issues.append(f"{name}: No confluence scores")
                        
                        # Check gainers/losers directly
                        if 'gainers' in data:
                            gainers = data.get('gainers', [])
                            losers = data.get('losers', [])
                            print(f"   Direct Movers: {len(gainers)} gainers, {len(losers)} losers")
                            if gainers:
                                successes.append(f"{name}: Direct gainers working")
                            if losers:
                                successes.append(f"{name}: Direct losers working")
                        
                    else:
                        print(f"\n❌ {name}: HTTP {response.status}")
                        issues.append(f"{name}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"\n❌ {name}: Error - {str(e)[:50]}")
                issues.append(f"{name}: Connection error")
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if successes:
        print("\n✅ WORKING:")
        for success in set(successes):
            print(f"   - {success}")
    
    if issues:
        print("\n❌ ISSUES:")
        for issue in set(issues):
            print(f"   - {issue}")
    else:
        print("\n🎉 ALL DATA FLOWING CORRECTLY!")
    
    # Overall status
    print("\n" + "-" * 60)
    if len(issues) == 0:
        print("STATUS: ✅ FULLY OPERATIONAL")
        print("All data flow issues have been fixed!")
    elif len(issues) < len(successes):
        print("STATUS: ⚠️  PARTIALLY WORKING")
        print(f"{len(successes)} components working, {len(issues)} issues remaining")
    else:
        print("STATUS: ❌ CRITICAL ISSUES")
        print(f"Only {len(successes)} components working")
    
    print("=" * 60)

async def main():
    """Run verification"""
    await check_data_flow()

if __name__ == "__main__":
    print("\n🔍 Verifying Data Flow After Fixes...\n")
    asyncio.run(main())