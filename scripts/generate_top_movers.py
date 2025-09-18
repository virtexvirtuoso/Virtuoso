#!/usr/bin/env python3
"""Generate top movers from ticker and signal data"""

import asyncio
import aiomcache
import json
import time

async def generate_top_movers():
    """Generate top movers from ticker data"""
    client = aiomcache.Client('localhost', 11211)
    
    print("Generating top movers...")
    
    # Get ticker data
    tickers_cache = await client.get(b'market:tickers')
    if not tickers_cache:
        print("❌ No ticker data available")
        return
    
    tickers = json.loads(tickers_cache.decode())
    ticker_list = tickers.get('tickers', [])
    
    if not ticker_list:
        print("❌ No tickers in data")
        return
    
    # Get signals for confluence scores
    signals_cache = await client.get(b'analysis:signals')
    signal_scores = {}
    if signals_cache:
        signals = json.loads(signals_cache.decode())
        for sig in signals.get('signals', []):
            signal_scores[sig.get('symbol')] = {
                'confluence_score': sig.get('confluence_score', 50),
                'signal': sig.get('signal', 'NEUTRAL'),
                'reliability': sig.get('reliability', 0),
                'components': sig.get('components', {})
            }
    
    # Process tickers with real market data
    movers_data = []
    for ticker in ticker_list:
        symbol = ticker.get('symbol', '')
        if not symbol:
            continue
            
        # Get signal data if available
        signal_data = signal_scores.get(symbol, {})
        
        # Create mover entry with all data
        mover = {
            'symbol': symbol,
            'price': ticker.get('price', 0),
            'price_change_percent': ticker.get('price_change_percent', 0),
            'volume_24h_usd': ticker.get('volume_24h_usd', 0),
            'high_24h': ticker.get('high_24h', 0),
            'low_24h': ticker.get('low_24h', 0),
            'volume': ticker.get('volume', 0),
            # Add signal data
            'confluence_score': signal_data.get('confluence_score', 50),
            'signal': signal_data.get('signal', 'NEUTRAL'),
            'confidence': signal_data.get('reliability', 50),
            'change_24h': ticker.get('price_change_percent', 0)  # Alias for compatibility
        }
        
        # Only include if we have price change data
        if mover['price_change_percent'] != 0:
            movers_data.append(mover)
    
    # Sort and separate gainers/losers
    gainers = [m for m in movers_data if m['price_change_percent'] > 0]
    losers = [m for m in movers_data if m['price_change_percent'] < 0]
    
    # Sort by percentage change
    gainers.sort(key=lambda x: x['price_change_percent'], reverse=True)
    losers.sort(key=lambda x: x['price_change_percent'])
    
    # Create movers structure
    movers = {
        'gainers': gainers[:20],  # Top 20 gainers
        'losers': losers[:20],    # Top 20 losers
        'timestamp': int(time.time()),
        'total_symbols': len(ticker_list),
        'symbols_with_change': len(movers_data)
    }
    
    # Store in cache
    await client.set(
        b'market:movers',
        json.dumps(movers).encode(),
        exptime=300  # 5 minutes
    )
    
    print(f"✅ Generated top movers:")
    print(f"   Total symbols: {len(ticker_list)}")
    print(f"   Gainers: {len(gainers)} (showing top 20)")
    print(f"   Losers: {len(losers)} (showing top 20)")
    
    # Show top 3 of each
    if gainers:
        print("\n   Top 3 Gainers:")
        for i, g in enumerate(gainers[:3], 1):
            print(f"   {i}. {g['symbol']}: +{g['price_change_percent']:.2f}% @ ${g['price']:.2f}")
            print(f"      Volume: ${g['volume_24h_usd']:,.0f}")
            print(f"      Confluence: {g['confluence_score']:.1f}")
    
    if losers:
        print("\n   Top 3 Losers:")
        for i, l in enumerate(losers[:3], 1):
            print(f"   {i}. {l['symbol']}: {l['price_change_percent']:.2f}% @ ${l['price']:.2f}")
            print(f"      Volume: ${l['volume_24h_usd']:,.0f}")
            print(f"      Confluence: {l['confluence_score']:.1f}")

if __name__ == "__main__":
    asyncio.run(generate_top_movers())