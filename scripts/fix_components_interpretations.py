#!/usr/bin/env python3
"""
Fix components and interpretations not appearing in dashboard.
The issue: Aggregation function uses wrong method name to retrieve cached data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_aggregation_method():
    """Fix the aggregation function to use correct cache retrieval method"""
    
    main_file = project_root / "src" / "main.py"
    
    # Read current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace get_cached_analysis with get_cached_breakdown
    content = content.replace(
        "analysis = await cache_service.get_cached_analysis(symbol)",
        "analysis = await cache_service.get_cached_breakdown(symbol)"
    )
    
    # Fix 2: Ensure we're using the correct data structure
    # The cached breakdown has the structure we need, but we need to map it correctly
    fixed_aggregation = '''
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
                        # Try to get cached breakdown (not analysis)
                        try:
                            breakdown = await cache_service.get_cached_breakdown(symbol)
                            if breakdown:
                                # Map breakdown structure to expected format
                                analysis = {
                                    'symbol': symbol,
                                    'confluence_score': breakdown.get('overall_score', 50),
                                    'components': breakdown.get('components', {}),
                                    'interpretations': breakdown.get('interpretations', {}),
                                    'sub_components': breakdown.get('sub_components', {}),
                                    'signal': breakdown.get('sentiment', 'NEUTRAL'),
                                    'reliability': breakdown.get('reliability', 0),
                                    'timestamp': breakdown.get('timestamp', int(time.time() * 1000)),
                                    'has_breakdown': True,
                                    # Add any additional fields from ticker if available
                                    'price': symbol_info.get('price', 0),
                                    'volume_24h': symbol_info.get('volume_24h', 0),
                                    'price_change_percent': symbol_info.get('price_change_percent', 0)
                                }
                                all_analyses[symbol] = analysis
                        except Exception as e:
                            logger.debug(f"Could not get breakdown for {symbol}: {e}")
            
            # Convert to signals format
            signals_list = []
            for symbol, analysis in all_analyses.items():
                # Ensure all required fields are present
                signal = {
                    'symbol': analysis.get('symbol', symbol),
                    'confluence_score': analysis.get('confluence_score', 50),
                    'components': analysis.get('components', {}),
                    'interpretations': analysis.get('interpretations', {}),
                    'sub_components': analysis.get('sub_components', {}),
                    'signal': analysis.get('signal', 'NEUTRAL'),
                    'reliability': analysis.get('reliability', 0),
                    'timestamp': analysis.get('timestamp', int(time.time() * 1000)),
                    'has_breakdown': analysis.get('has_breakdown', True),
                    'price': analysis.get('price', 0),
                    'volume_24h': analysis.get('volume_24h', 0),
                    'price_change_percent': analysis.get('price_change_percent', 0)
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
            
            logger.info(f"✅ Aggregated {len(signals_list)} confluence signals with components and interpretations")
            
        else:
            logger.warning("Confluence cache service not available for aggregation")
            
    except Exception as e:
        logger.error(f"Error aggregating confluence signals: {e}")
        import traceback
        logger.error(traceback.format_exc())
'''
    
    # Find and replace the aggregate_confluence_signals function
    start_idx = content.find("async def aggregate_confluence_signals():")
    if start_idx != -1:
        # Find the end of the function
        end_idx = content.find("\nasync def ", start_idx + 1)
        if end_idx == -1:
            end_idx = content.find("\nclass ", start_idx + 1)
        if end_idx == -1:
            # Look for the next function that we know exists
            end_idx = content.find("\nasync def aggregate_all_dashboard_data():", start_idx + 1)
        
        if end_idx != -1:
            # Replace the function
            content = content[:start_idx] + fixed_aggregation.strip() + "\n\n" + content[end_idx:]
            print("✅ Fixed aggregate_confluence_signals function")
        else:
            print("⚠️  Could not find end of function, applying simpler fix")
            # Just do the simple replacement
            content = content.replace(
                "analysis = await cache_service.get_cached_analysis(symbol)",
                "breakdown = await cache_service.get_cached_breakdown(symbol)"
            )
    else:
        print("⚠️  Could not find aggregate_confluence_signals function")
        return False
    
    # Write back
    with open(main_file, 'w') as f:
        f.write(content)
    
    return True

def main():
    """Main execution"""
    print("🔧 Fixing components and interpretations issue...")
    
    success = fix_aggregation_method()
    
    if success:
        print("\n✅ Fix applied successfully!")
        print("\n📝 Next steps:")
        print("1. Deploy to VPS: scp src/main.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/")
        print("2. Restart services: ssh vps 'sudo systemctl restart virtuoso-trading virtuoso-web'")
        print("3. Wait 30 seconds for cache to populate")
        print("4. Test: curl http://VPS_HOST_REDACTED:8002/api/dashboard/data | python3 -m json.tool | grep -A5 components")
    else:
        print("\n❌ Fix failed. Please check the error messages above.")

if __name__ == "__main__":
    main()