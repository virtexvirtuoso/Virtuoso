#!/usr/bin/env python3
"""
Test script to verify that 15+ symbols would be populated in signals cache
"""
import asyncio
import json
import aiomcache
import time
from datetime import datetime

async def populate_15_signals():
    """Populate signals cache with 15 symbols"""
    client = aiomcache.Client('localhost', 11211)
    
    # Create 15 symbols with varying scores
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
        'AVAXUSDT', 'ADAUSDT', 'MATICUSDT', 'DOTUSDT', 'LINKUSDT',
        'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'ATOMUSDT', 'NEARUSDT'
    ]
    
    signals = []
    for i, symbol in enumerate(symbols):
        score = 80 - (i * 3)  # Descending scores
        change = 5.0 - (i * 0.5)
        price = 100 * (i + 1)
        
        signals.append({
            'symbol': symbol,
            'signal': 'BUY' if score > 65 else 'NEUTRAL' if score > 50 else 'SELL',
            'score': score,
            'price': price,
            'change_24h': change,
            'volume': 1000000 + (i * 50000),
            'timestamp': datetime.now().isoformat(),
            'components': {
                'technical': score - 5,
                'volume': score + 5,
                'orderflow': score,
                'sentiment': score - 2,
                'orderbook': score + 2,
                'price_structure': score - 3
            }
        })
    
    # Store in cache
    signals_data = {
        'signals': signals,
        'count': len(signals),
        'timestamp': int(time.time()),
        'source': 'test_script'
    }
    
    await client.set(b'analysis:signals', json.dumps(signals_data).encode(), exptime=300)
    print(f"✅ Populated cache with {len(signals)} signals")
    
    # Verify it was stored
    stored_data = await client.get(b'analysis:signals')
    if stored_data:
        stored_signals = json.loads(stored_data.decode())
        print(f"✅ Verified: {len(stored_signals['signals'])} signals in cache")
        for s in stored_signals['signals'][:5]:
            print(f"  - {s['symbol']}: Score={s['score']}, Price=${s['price']}")
        print(f"  ... and {len(stored_signals['signals']) - 5} more")
    
    await client.close()

async def check_mobile_endpoint():
    """Check what mobile endpoint would return with 15 signals"""
    import sys
    sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
    
    from api.cache_adapter_direct import cache_adapter
    
    # Get mobile data using the adapter
    mobile_data = await cache_adapter.get_mobile_data()
    
    print(f"\n📱 Mobile endpoint would return:")
    print(f"  - Confluence scores: {len(mobile_data.get('confluence_scores', []))} symbols")
    
    if mobile_data.get('confluence_scores'):
        for score in mobile_data['confluence_scores'][:5]:
            print(f"    • {score['symbol']}: {score['score']}")
        if len(mobile_data['confluence_scores']) > 5:
            print(f"    ... and {len(mobile_data['confluence_scores']) - 5} more")

if __name__ == "__main__":
    asyncio.run(populate_15_signals())
    asyncio.run(check_mobile_endpoint())