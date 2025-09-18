#!/usr/bin/env python3
"""Fix aggregation to include real price data from tickers"""

import asyncio
import json
import time
import aiomcache

async def aggregate_confluence_signals_with_prices():
    """Aggregate confluence scores with real price data"""
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
        
        # First, try to get ticker data from cache
        ticker_data = {}
        tickers_cache = await memcache_client.get(b'market:tickers')
        if tickers_cache:
            try:
                tickers = json.loads(tickers_cache.decode())
                # Convert to dict for easy lookup
                for ticker in tickers.get('tickers', []):
                    ticker_data[ticker['symbol']] = ticker
                print(f"Found ticker data for {len(ticker_data)} symbols")
            except:
                print("Could not parse ticker data")
        
        # If no ticker cache, try symbol-specific ticker cache
        if not ticker_data:
            for symbol in symbols_list:
                ticker_key = f'ticker:{symbol}'.encode()
                ticker_cache = await memcache_client.get(ticker_key)
                if ticker_cache:
                    try:
                        ticker = json.loads(ticker_cache.decode())
                        ticker_data[symbol] = ticker
                    except:
                        pass
        
        # Get breakdown data and merge with ticker data
        for symbol in symbols_list:
            try:
                # Get cached breakdown
                cache_key = f'confluence:breakdown:{symbol}'.encode()
                breakdown_data = await memcache_client.get(cache_key)
                
                if breakdown_data:
                    breakdown = json.loads(breakdown_data.decode())
                    
                    # Get ticker info for this symbol
                    ticker = ticker_data.get(symbol, {})
                    
                    # Map breakdown structure to expected format with price data
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
                        # Add real price data from ticker (matching Bybit field names)
                        'price': ticker.get('price', ticker.get('last', 0)),
                        'volume_24h': ticker.get('volume_24h_usd', ticker.get('volume', 0)),
                        'price_change_percent': ticker.get('price_change_percent', ticker.get('percentage', 0)),
                        'high_24h': ticker.get('high_24h', ticker.get('high', 0)),
                        'low_24h': ticker.get('low_24h', ticker.get('low', 0)),
                        'turnover_24h': ticker.get('volume_24h_usd', ticker.get('turnover', 0))
                    }
                    all_analyses[symbol] = analysis
                    print(f"✓ {symbol}: score={breakdown.get('overall_score'):.1f}, price=${analysis['price']:.2f}, vol=${analysis['volume_24h']:.0f}")
            except Exception as e:
                print(f"✗ {symbol}: {e}")
        
        # Convert to signals format
        signals_list = []
        for symbol, analysis in all_analyses.items():
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
                'price_change_percent': analysis.get('price_change_percent', 0),
                'high_24h': analysis.get('high_24h', 0),
                'low_24h': analysis.get('low_24h', 0),
                'turnover_24h': analysis.get('turnover_24h', 0)
            }
            signals_list.append(signal)
        
        # Sort by confluence score
        signals_list.sort(key=lambda x: x['confluence_score'], reverse=True)
        
        # Create signals data
        signals_data = {
            'signals': signals_list[:50],
            'count': len(signals_list),
            'timestamp': int(time.time()),
            'source': 'aggregated_confluence_with_prices'
        }
        
        # Store in cache with longer TTL
        await memcache_client.set(
            b'analysis:signals',
            json.dumps(signals_data).encode(),
            exptime=300  # 5 minutes
        )
        
        print(f"\n✅ Aggregated {len(signals_list)} signals with price data to cache")
        
        # Verify what was stored
        stored = await memcache_client.get(b'analysis:signals')
        if stored:
            data = json.loads(stored.decode())
            if data['signals']:
                first = data['signals'][0]
                print(f"\nFirst signal: {first['symbol']}")
                print(f"  Price: ${first.get('price', 0):.2f}")
                print(f"  Volume 24h: ${first.get('volume_24h', 0):.0f}")
                print(f"  Change 24h: {first.get('price_change_percent', 0):.2f}%")
                print(f"  Turnover: ${first.get('turnover_24h', 0):.0f}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(aggregate_confluence_signals_with_prices())