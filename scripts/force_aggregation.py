#!/usr/bin/env python3
"""Force run aggregation to test if it properly includes components"""

import asyncio
import json
import time
import aiomcache

async def aggregate_confluence_signals():
    """Aggregate confluence scores into signals for dashboard"""
    try:
        # Initialize memcache client
        memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        all_analyses = {}
        
        # Use hardcoded list
        symbols_list = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT',
            'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT'
        ]
        
        print(f"Processing {len(symbols_list)} symbols...")
        
        # Get breakdown data directly from memcache for each symbol
        for symbol in symbols_list:
            try:
                # Try to get cached breakdown directly
                cache_key = f'confluence:breakdown:{symbol}'.encode()
                breakdown_data = await memcache_client.get(cache_key)
                
                if breakdown_data:
                    breakdown = json.loads(breakdown_data.decode())
                    
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
                        'price': 0,  # Will be filled from ticker data if available
                        'volume_24h': 0,
                        'price_change_percent': 0
                    }
                    all_analyses[symbol] = analysis
                    print(f"✓ {symbol}: score={breakdown.get('overall_score'):.1f}, has_components={bool(breakdown.get('components'))}")
            except Exception as e:
                print(f"✗ {symbol}: {e}")
        
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
            exptime=120  # 2 minutes
        )
        
        print(f"\n✅ Aggregated {len(signals_list)} signals to cache")
        
        # Verify what was stored
        stored = await memcache_client.get(b'analysis:signals')
        if stored:
            data = json.loads(stored.decode())
            if data['signals']:
                first = data['signals'][0]
                print(f"First signal: {first['symbol']}")
                print(f"  Keys: {list(first.keys())}")
                print(f"  Has components: {'components' in first}")
                if 'components' in first:
                    print(f"  Components: {first['components']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(aggregate_confluence_signals())