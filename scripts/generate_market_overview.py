#!/usr/bin/env python3
"""Generate market overview data from signals and tickers"""

import asyncio
import aiomcache
import json
import time

async def generate_market_overview():
    """Generate market overview from available data"""
    client = aiomcache.Client('localhost', 11211)
    
    # Get signals data
    signals_data = await client.get(b'analysis:signals')
    if not signals_data:
        print("❌ No signals data available")
        return
    
    signals = json.loads(signals_data.decode())
    signal_list = signals.get('signals', [])
    
    if not signal_list:
        print("❌ No signals in data")
        return
    
    # Calculate market overview metrics
    total_symbols = len(signal_list)
    total_volume = sum(s.get('volume_24h', 0) for s in signal_list)
    
    # Calculate price changes
    gainers = [s for s in signal_list if s.get('price_change_percent', 0) > 0]
    losers = [s for s in signal_list if s.get('price_change_percent', 0) < 0]
    neutral = [s for s in signal_list if s.get('price_change_percent', 0) == 0]
    
    # Calculate average change
    changes = [s.get('price_change_percent', 0) for s in signal_list if s.get('price_change_percent', 0) != 0]
    avg_change = sum(changes) / len(changes) if changes else 0
    
    # Calculate volatility (standard deviation of price changes)
    if changes:
        mean = sum(changes) / len(changes)
        variance = sum((x - mean) ** 2 for x in changes) / len(changes)
        volatility = variance ** 0.5
    else:
        volatility = 0
    
    # Determine market regime based on gainers/losers ratio and average change
    if len(gainers) > len(losers) * 1.5 and avg_change > 2:
        market_regime = "BULLISH"
    elif len(losers) > len(gainers) * 1.5 and avg_change < -2:
        market_regime = "BEARISH"
    else:
        market_regime = "NEUTRAL"
    
    # Calculate trend strength (0-100)
    if total_symbols > 0:
        trend_strength = abs(len(gainers) - len(losers)) / total_symbols * 100
    else:
        trend_strength = 0
    
    # Get BTC dominance (hardcoded for now, should come from external API)
    btc_dominance = 57.9
    
    # Create market overview
    market_overview = {
        'total_symbols': total_symbols,
        'active_signals': len([s for s in signal_list if s.get('signal') != 'NEUTRAL']),
        'market_regime': market_regime,
        'trend_strength': round(trend_strength, 2),
        'volatility': round(volatility, 2),
        'btc_dominance': btc_dominance,
        'total_volume_24h': total_volume,
        'gainers': len(gainers),
        'losers': len(losers),
        'neutral': len(neutral),
        'average_change': round(avg_change, 2),
        'timestamp': int(time.time())
    }
    
    # Store in cache
    await client.set(
        b'market:overview',
        json.dumps(market_overview).encode(),
        exptime=300  # 5 minutes
    )
    
    print("✅ Generated market overview:")
    print(json.dumps(market_overview, indent=2))
    
    # Also create market movers
    movers = {
        'gainers': sorted(gainers, key=lambda x: x.get('price_change_percent', 0), reverse=True)[:10],
        'losers': sorted(losers, key=lambda x: x.get('price_change_percent', 0))[:10],
        'timestamp': int(time.time())
    }
    
    # Store movers
    await client.set(
        b'market:movers',
        json.dumps(movers).encode(),
        exptime=300
    )
    
    print(f"\n✅ Generated market movers: {len(movers['gainers'])} gainers, {len(movers['losers'])} losers")
    
    # Set market regime separately for compatibility
    await client.set(
        b'analysis:market_regime',
        market_regime.encode(),
        exptime=300
    )
    
    print(f"\n✅ Set market regime: {market_regime}")

if __name__ == "__main__":
    asyncio.run(generate_market_overview())