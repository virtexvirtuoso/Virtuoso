#!/usr/bin/env python3
"""
Fix all data flow issues in the Virtuoso trading system.
Ensures all calculated data reaches the dashboard.
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

ISSUES_FOUND = []

async def check_and_fix_data_flows():
    """Check and fix all data flow issues"""
    
    main_file = project_root / "src" / "main.py"
    
    # Read current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Enhanced aggregation function that handles ALL data types
    enhanced_aggregation = '''
async def aggregate_all_dashboard_data():
    """Aggregate ALL data for dashboard - fixes missing data flows"""
    try:
        import aiomcache
        import numpy as np
        
        # Initialize memcache client
        memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # 1. Aggregate market overview
        market_overview = {
            'market_regime': 'unknown',
            'trend_strength': 0,
            'volatility': 0,
            'btc_dominance': 0,
            'total_volume_24h': 0,
            'timestamp': int(time.time())
        }
        
        # Calculate from cached analyses
        if 'confluence_cache_service' in globals():
            cache_service = globals()['confluence_cache_service']
            
            # Get BTC data for dominance calculation
            try:
                btc_analysis = await cache_service.get_cached_analysis('BTCUSDT')
                if btc_analysis:
                    btc_volume = btc_analysis.get('volume_24h', 0)
                    total_volume = 0
                    volatilities = []
                    trend_scores = []
                    
                    # Get all symbols data
                    if 'top_symbols_manager' in globals():
                        symbols = await globals()['top_symbols_manager'].get_top_symbols(limit=30)
                        
                        for symbol_info in symbols:
                            symbol = symbol_info.get('symbol')
                            if symbol:
                                try:
                                    analysis = await cache_service.get_cached_analysis(symbol)
                                    if analysis:
                                        total_volume += analysis.get('volume_24h', 0)
                                        
                                        # Get volatility from sentiment data
                                        sentiment = analysis.get('sentiment', {})
                                        if isinstance(sentiment, dict):
                                            vol = sentiment.get('volatility_24h', 0)
                                            if vol > 0:
                                                volatilities.append(vol)
                                        
                                        # Get trend from technical component
                                        components = analysis.get('components', {})
                                        tech_score = components.get('technical', 50)
                                        trend_scores.append(tech_score)
                                except:
                                    pass
                    
                    # Calculate market overview metrics
                    if total_volume > 0:
                        market_overview['btc_dominance'] = round((btc_volume / total_volume) * 100, 2)
                    
                    if volatilities:
                        market_overview['volatility'] = round(np.mean(volatilities) * 100, 2)
                    
                    if trend_scores:
                        avg_trend = np.mean(trend_scores)
                        market_overview['trend_strength'] = round(abs(avg_trend - 50) * 2, 0)  # 0-100 scale
                        
                        # Determine market regime
                        if avg_trend > 65:
                            market_overview['market_regime'] = 'bullish'
                        elif avg_trend < 35:
                            market_overview['market_regime'] = 'bearish'
                        else:
                            market_overview['market_regime'] = 'neutral'
                    
                    market_overview['total_volume_24h'] = total_volume
                    
            except Exception as e:
                logger.error(f"Error calculating market overview: {e}")
        
        # Store market overview
        await memcache_client.set(
            b'market:overview',
            json.dumps(market_overview).encode(),
            exptime=60
        )
        logger.info(f"✅ Stored market overview: regime={market_overview['market_regime']}, btc_dom={market_overview['btc_dominance']}%")
        
        # 2. Aggregate top movers
        movers_data = {'gainers': [], 'losers': [], 'timestamp': int(time.time())}
        
        if 'confluence_cache_service' in globals() and 'top_symbols_manager' in globals():
            try:
                symbols = await globals()['top_symbols_manager'].get_top_symbols(limit=30)
                symbol_changes = []
                
                for symbol_info in symbols:
                    symbol = symbol_info.get('symbol')
                    if symbol:
                        try:
                            analysis = await cache_service.get_cached_analysis(symbol)
                            if analysis:
                                # Get price change from sentiment or ticker data
                                sentiment = analysis.get('sentiment', {})
                                price_change = 0
                                
                                if isinstance(sentiment, dict):
                                    price_change = sentiment.get('price_change_24h', 0)
                                    
                                    # Also check ticker data
                                    ticker = sentiment.get('ticker', {})
                                    if isinstance(ticker, dict) and ticker.get('percentage'):
                                        price_change = ticker['percentage']
                                
                                if price_change != 0:
                                    symbol_changes.append({
                                        'symbol': symbol,
                                        'confluence_score': analysis.get('confluence_score', 50),
                                        'price': analysis.get('price', 0),
                                        'change_24h': round(price_change, 2),
                                        'volume_24h_usd': analysis.get('volume_24h', 0),
                                        'signal': analysis.get('signal', 'NEUTRAL'),
                                        'confidence': analysis.get('reliability', 0) * 100
                                    })
                        except:
                            pass
                
                # Sort and get top gainers/losers
                symbol_changes.sort(key=lambda x: x['change_24h'], reverse=True)
                movers_data['gainers'] = symbol_changes[:5]
                movers_data['losers'] = symbol_changes[-5:][::-1]  # Reverse to show biggest loser first
                
            except Exception as e:
                logger.error(f"Error calculating top movers: {e}")
        
        # Store top movers
        await memcache_client.set(
            b'market:movers',
            json.dumps(movers_data).encode(),
            exptime=60
        )
        logger.info(f"✅ Stored top movers: {len(movers_data['gainers'])} gainers, {len(movers_data['losers'])} losers")
        
        # 3. Store enhanced signals with full data
        if 'confluence_cache_service' in globals():
            all_analyses = {}
            
            # Get symbols from top_symbols_manager
            if 'top_symbols_manager' in globals():
                symbols = await globals()['top_symbols_manager'].get_top_symbols(limit=30)
                
                for symbol_info in symbols:
                    symbol = symbol_info.get('symbol')
                    if symbol:
                        try:
                            analysis = await cache_service.get_cached_analysis(symbol)
                            if analysis and 'confluence_score' in analysis:
                                # Ensure all required fields are present
                                analysis['symbol'] = symbol
                                analysis['signal'] = analysis.get('signal', 'NEUTRAL')
                                analysis['reliability'] = analysis.get('reliability', 0)
                                analysis['timestamp'] = analysis.get('timestamp', int(time.time() * 1000))
                                
                                # Ensure components and interpretations are included
                                if 'components' not in analysis:
                                    analysis['components'] = {}
                                if 'interpretations' not in analysis:
                                    analysis['interpretations'] = {}
                                    
                                all_analyses[symbol] = analysis
                        except:
                            pass
            
            # Convert to signals format with full data
            signals_list = []
            for symbol, analysis in all_analyses.items():
                signals_list.append(analysis)
            
            # Sort by confluence score
            signals_list.sort(key=lambda x: x.get('confluence_score', 50), reverse=True)
            
            # Create signals data
            signals_data = {
                'signals': signals_list[:50],  # Top 50 signals
                'count': len(signals_list),
                'timestamp': int(time.time()),
                'source': 'aggregated_all_data'
            }
            
            # Store in cache
            await memcache_client.set(
                b'analysis:signals',
                json.dumps(signals_data).encode(),
                exptime=30
            )
            
            logger.info(f"✅ Aggregated {len(signals_list)} complete signals with components and interpretations")
            
    except Exception as e:
        logger.error(f"Error in aggregate_all_dashboard_data: {e}")
        import traceback
        logger.error(traceback.format_exc())
'''
    
    # Check if the enhanced aggregation already exists
    if "aggregate_all_dashboard_data" in content:
        print("⚠️  Enhanced aggregation already exists, updating it...")
        # Replace the existing function
        start_idx = content.find("async def aggregate_all_dashboard_data():")
        if start_idx != -1:
            # Find the end of the function (next async def or class)
            end_idx = content.find("\nasync def ", start_idx + 1)
            if end_idx == -1:
                end_idx = content.find("\nclass ", start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)
            
            # Replace the function
            content = content[:start_idx] + enhanced_aggregation.strip() + "\n\n" + content[end_idx:]
    else:
        # Insert before update_symbols_cache
        insert_pos = content.find("async def update_symbols_cache():")
        if insert_pos == -1:
            print("❌ Could not find update_symbols_cache function")
            return False
        
        content = content[:insert_pos] + enhanced_aggregation + "\n" + content[insert_pos:]
    
    # Ensure the aggregation is called in update_symbols_cache
    if "aggregate_all_dashboard_data()" not in content:
        update_pattern = "logger.info(\"Background cache update completed\")"
        update_replacement = '''# Aggregate all dashboard data
            await aggregate_all_dashboard_data()
            logger.info("Background cache update completed")'''
        
        content = content.replace(update_pattern, update_replacement)
    
    # Write back
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Enhanced data aggregation added/updated")
    return True

async def verify_issues():
    """Verify what data is missing"""
    import subprocess
    
    print("\n🔍 Checking current data issues...")
    
    # Test endpoints
    endpoints = [
        ("Market Overview", "http://VPS_HOST_REDACTED:8002/api/dashboard/market-overview"),
        ("Dashboard Data", "http://VPS_HOST_REDACTED:8002/api/dashboard/data"),
        ("Mobile Data", "http://VPS_HOST_REDACTED:8002/api/dashboard/mobile"),
    ]
    
    for name, url in endpoints:
        try:
            result = subprocess.run(
                f"curl -s '{url}' | python3 -c \"import sys, json; d=json.load(sys.stdin); print('data_exists' if d else 'empty')\"",
                shell=True, capture_output=True, text=True
            )
            if "empty" in result.stdout or not result.stdout.strip():
                ISSUES_FOUND.append(f"{name}: No data")
                print(f"  ❌ {name}: No data returned")
            else:
                print(f"  ✅ {name}: Has data")
        except:
            print(f"  ⚠️  {name}: Could not check")
    
    return len(ISSUES_FOUND) > 0

async def main():
    """Main execution"""
    print("🔧 Fixing all data flow issues...")
    
    # Check current issues
    has_issues = await verify_issues()
    
    if not has_issues:
        print("\n✅ No data flow issues detected!")
        return
    
    print(f"\n⚠️  Found {len(ISSUES_FOUND)} issues to fix")
    
    # Apply fixes
    success = await check_and_fix_data_flows()
    
    if success:
        print("\n✅ All fixes applied successfully!")
        print("\n📝 Next steps:")
        print("1. Deploy to VPS: scp src/main.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/")
        print("2. Restart services: ssh vps 'sudo systemctl restart virtuoso-trading virtuoso-web'")
        print("3. Wait 1 minute for cache to populate")
        print("4. Test: curl http://VPS_HOST_REDACTED:8002/api/dashboard/data")
    else:
        print("\n❌ Fix failed. Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())