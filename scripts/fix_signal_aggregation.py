#!/usr/bin/env python3
"""
Fix signal aggregation to ensure confluence scores flow to dashboard.
The issue: Confluence scores are calculated but not aggregated to 'analysis:signals' cache key.
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def add_signal_aggregation():
    """Add signal aggregation to the background cache update"""
    
    main_file = project_root / "src" / "main.py"
    
    # Read current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find the update_symbols_cache function and add signal aggregation
    aggregation_code = '''
async def aggregate_confluence_signals():
    """Aggregate confluence scores into signals for dashboard"""
    try:
        import aiomcache
        
        # Initialize memcache client
        memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Get all cached confluence analyses
        if 'confluence_cache_service' in globals():
            cache_service = globals()['confluence_cache_service']
            all_analyses = {}
            
            # Get symbols from top_symbols_manager
            if 'top_symbols_manager' in globals():
                symbols = await globals()['top_symbols_manager'].get_top_symbols(limit=30)
                
                for symbol_info in symbols:
                    symbol = symbol_info.get('symbol')
                    if symbol:
                        # Try to get cached analysis
                        cache_key = f"confluence:{symbol}"
                        try:
                            analysis = await cache_service.get_cached_analysis(symbol)
                            if analysis and 'confluence_score' in analysis:
                                all_analyses[symbol] = analysis
                        except:
                            pass
            
            # Convert to signals format
            signals_list = []
            for symbol, analysis in all_analyses.items():
                signal = {
                    'symbol': symbol,
                    'confluence_score': analysis.get('confluence_score', 50),
                    'components': analysis.get('components', {}),
                    'interpretation': analysis.get('interpretation', {}),
                    'signal': analysis.get('signal', 'NEUTRAL'),
                    'reliability': analysis.get('reliability', 0),
                    'timestamp': analysis.get('timestamp', int(time.time() * 1000))
                }
                signals_list.append(signal)
            
            # Sort by confluence score
            signals_list.sort(key=lambda x: x['confluence_score'], reverse=True)
            
            # Create signals data
            signals_data = {
                'signals': signals_list[:50],  # Top 50 signals
                'count': len(signals_list),
                'timestamp': int(time.time()),
                'source': 'aggregated_confluence'
            }
            
            # Store in cache
            await memcache_client.set(
                b'analysis:signals',
                json.dumps(signals_data).encode(),
                exptime=30
            )
            
            logger.info(f"✅ Aggregated {len(signals_list)} confluence signals to cache")
            
        else:
            logger.warning("Confluence cache service not available for aggregation")
            
    except Exception as e:
        logger.error(f"Error aggregating confluence signals: {e}")
'''
    
    # Find where to insert the aggregation function
    insert_pos = content.find("async def update_symbols_cache():")
    if insert_pos == -1:
        print("❌ Could not find update_symbols_cache function")
        return False
    
    # Insert the aggregation function before update_symbols_cache
    content = content[:insert_pos] + aggregation_code + "\n" + content[insert_pos:]
    
    # Now modify update_symbols_cache to also call signal aggregation
    update_pattern = "logger.info(\"Background cache update completed\")"
    update_replacement = '''# Also aggregate confluence signals
            await aggregate_confluence_signals()
            logger.info("Background cache update completed")'''
    
    content = content.replace(update_pattern, update_replacement)
    
    # Write back
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Added signal aggregation to background cache updates")
    return True

async def main():
    """Main execution"""
    print("🔧 Fixing signal aggregation issue...")
    
    success = await add_signal_aggregation()
    
    if success:
        print("\n✅ Fix applied successfully!")
        print("\n📝 Next steps:")
        print("1. Deploy to VPS: ./scripts/deploy_signal_aggregation_fix.sh")
        print("2. Restart services: ssh vps 'sudo systemctl restart virtuoso-trading virtuoso-web'")
        print("3. Test: curl http://${VPS_HOST}:8003/api/dashboard/data")
    else:
        print("\n❌ Fix failed. Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())