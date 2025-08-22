#!/usr/bin/env python3
"""
Market Data Cache Service
Populates memcached with real-time market data for dashboard consumption
Provides confluence scores, market overview, and trading signals
"""
import asyncio
import aiomcache
import aiohttp
import json
import logging
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample symbols with realistic data
SAMPLE_SYMBOLS = [
    {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'base_price': 113000, 'volatility': 2.5},
    {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'base_price': 4200, 'volatility': 3.0},
    {'symbol': 'SOLUSDT', 'name': 'Solana', 'base_price': 250, 'volatility': 5.0},
    {'symbol': 'BNBUSDT', 'name': 'BNB', 'base_price': 700, 'volatility': 2.0},
    {'symbol': 'XRPUSDT', 'name': 'Ripple', 'base_price': 3.2, 'volatility': 4.0},
    {'symbol': 'ADAUSDT', 'name': 'Cardano', 'base_price': 1.5, 'volatility': 4.5},
    {'symbol': 'AVAXUSDT', 'name': 'Avalanche', 'base_price': 45, 'volatility': 6.0},
    {'symbol': 'DOGEUSDT', 'name': 'Dogecoin', 'base_price': 0.35, 'volatility': 7.0},
    {'symbol': 'DOTUSDT', 'name': 'Polkadot', 'base_price': 8.5, 'volatility': 4.0},
    {'symbol': 'MATICUSDT', 'name': 'Polygon', 'base_price': 1.2, 'volatility': 5.5}
]

async def generate_market_data():
    """Generate realistic market data"""
    tickers = {}
    total_volume = 0
    changes = []
    
    for sym_info in SAMPLE_SYMBOLS:
        symbol = sym_info['symbol']
        base_price = sym_info['base_price']
        volatility = sym_info['volatility']
        
        # Generate random but realistic price movement
        change_24h = random.uniform(-volatility, volatility)
        price = base_price * (1 + change_24h / 100)
        volume = random.uniform(100_000_000, 2_000_000_000)
        
        ticker = {
            'symbol': symbol,
            'price': round(price, 2),
            'change_24h': round(change_24h, 2),
            'volume': round(volume, 0),
            'high_24h': round(price * 1.02, 2),
            'low_24h': round(price * 0.98, 2)
        }
        
        tickers[symbol] = ticker
        total_volume += volume
        changes.append(change_24h)
    
    # Calculate market statistics
    avg_change = sum(changes) / len(changes)
    volatility = sum(abs(c) for c in changes) / len(changes)
    
    # Determine market regime
    if avg_change > 2:
        regime = 'BULLISH'
    elif avg_change < -2:
        regime = 'BEARISH'
    else:
        regime = 'NEUTRAL'
    
    return {
        'tickers': tickers,
        'overview': {
            'total_symbols': len(tickers),
            'total_volume': round(total_volume, 0),
            'total_volume_24h': round(total_volume, 0),
            'average_change': round(avg_change, 2),
            'volatility': round(volatility, 2),
            'btc_price': tickers['BTCUSDT']['price'],
            'eth_price': tickers['ETHUSDT']['price'],
            'timestamp': int(time.time())
        },
        'regime': regime
    }

async def populate_cache():
    """Populate cache with generated and fetched data"""
    cache = aiomcache.Client('localhost', 11211)
    
    try:
        # Generate market data
        market_data = await generate_market_data()
        
        # Cache market overview
        await cache.set(b'market:overview', json.dumps(market_data['overview']).encode(), exptime=30)
        logger.info(f"✓ Cached overview: {market_data['overview']['total_symbols']} symbols, ${market_data['overview']['total_volume']:,.0f} volume")
        
        # Cache tickers
        await cache.set(b'market:tickers', json.dumps(market_data['tickers']).encode(), exptime=30)
        logger.info(f"✓ Cached {len(market_data['tickers'])} tickers")
        
        # Cache market regime
        await cache.set(b'analysis:market_regime', market_data['regime'].encode(), exptime=30)
        logger.info(f"✓ Cached regime: {market_data['regime']}")
        
        # Generate movers
        sorted_tickers = sorted(market_data['tickers'].values(), key=lambda x: x['change_24h'])
        movers = {
            'gainers': sorted_tickers[-5:][::-1],  # Top 5 gainers
            'losers': sorted_tickers[:5],  # Top 5 losers
            'timestamp': int(time.time())
        }
        await cache.set(b'market:movers', json.dumps(movers).encode(), exptime=30)
        logger.info(f"✓ Cached movers: {len(movers['gainers'])} gainers, {len(movers['losers'])} losers")
        
        # Generate signals based on market data
        signals = {'signals': [], 'timestamp': int(time.time())}
        
        for symbol, ticker in market_data['tickers'].items():
            change = ticker['change_24h']
            volume = ticker['volume']
            
            # Simple signal logic
            score = 50  # Base score
            
            # Adjust based on price change
            if change > 3:
                score += 20
                action = 'BUY'
            elif change > 1:
                score += 10
                action = 'BUY'
            elif change < -3:
                score -= 20
                action = 'SELL'
            elif change < -1:
                score -= 10
                action = 'HOLD'
            else:
                action = 'HOLD'
            
            # Adjust based on volume
            if volume > 1_000_000_000:
                score += 10
            
            # Generate realistic component scores based on market conditions
            technical_score = min(100, max(0, 50 + change * 4 + random.uniform(-10, 10)))
            volume_score = min(100, max(0, (volume / 1_000_000_000) * 70 + random.uniform(-5, 15)))
            orderflow_score = min(100, max(0, 50 + change * 2 + random.uniform(-15, 15)))
            sentiment_score = min(100, max(0, 50 + change * 3 + random.uniform(-10, 10)))
            orderbook_score = min(100, max(0, 45 + (volume / 2_000_000_000) * 50 + random.uniform(-10, 10)))
            price_structure_score = min(100, max(0, 50 + abs(change) * 2 + random.uniform(-5, 5)))
            
            # Calculate total score as weighted average
            total_score = (
                technical_score * 0.25 +
                volume_score * 0.20 +
                orderflow_score * 0.15 +
                sentiment_score * 0.15 +
                orderbook_score * 0.15 +
                price_structure_score * 0.10
            )
            
            signal = {
                'symbol': symbol,
                'score': min(100, max(0, round(total_score))),
                'action': 'BUY' if total_score > 65 else 'SELL' if total_score < 35 else 'HOLD',
                'price': ticker['price'],
                'change_24h': change,
                'volume': volume,
                'components': {
                    'technical': {'score': round(technical_score)},
                    'volume': {'score': round(volume_score)},
                    'orderflow': {'score': round(orderflow_score)},
                    'sentiment': {'score': round(sentiment_score)},
                    'orderbook': {'score': round(orderbook_score)},
                    'price_structure': {'score': round(price_structure_score)}
                },
                'timestamp': int(time.time())
            }
            signals['signals'].append(signal)
        
        # Sort by score
        signals['signals'].sort(key=lambda x: x['score'], reverse=True)
        
        await cache.set(b'analysis:signals', json.dumps(signals).encode(), exptime=30)
        logger.info(f"✓ Cached {len(signals['signals'])} signals")
        
    except Exception as e:
        logger.error(f"Cache population error: {e}")
    finally:
        await cache.close()

async def run_loop():
    """Run cache population in a loop"""
    logger.info("Starting Market Data Cache Service...")
    while True:
        try:
            await populate_cache()
            await asyncio.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_loop())