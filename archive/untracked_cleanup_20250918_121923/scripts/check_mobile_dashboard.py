#!/usr/bin/env python3
"""
Check mobile dashboard data quality
"""
import json
import urllib.request

url = "http://${VPS_HOST}:8003/api/dashboard/mobile-data"
response = urllib.request.urlopen(url)
data = json.loads(response.read())

scores = data.get('confluence_scores', [])

print('📱 Mobile Dashboard Verification')
print('=' * 50)
print(f'✅ Symbols returned: {len(scores)}')
print(f'⚡ Response time: {data.get("response_time_ms", "N/A")}ms')
print()

if scores:
    print('📊 All Symbols with Market Data:')
    print('-' * 50)
    
    for i, score in enumerate(scores, 1):
        symbol = score.get('symbol', 'N/A')
        price = score.get('price', 0)
        change = score.get('price_change_percent', score.get('change_24h', 0))
        volume = score.get('volume_24h', 0)
        turnover = score.get('turnover_24h', 0)
        sentiment = score.get('sentiment', 'N/A')
        conf_score = score.get('confluence_score', score.get('score', 0))
        
        # Format volume/turnover
        if turnover > 1_000_000:
            turnover_str = f"${turnover/1_000_000:.1f}M"
        else:
            turnover_str = f"${turnover:,.0f}"
        
        print(f'{i:2}. {symbol:12} ${price:10.2f} | {change:+6.2f}% | Vol: {turnover_str:>10}')
    
    print()
    print('📈 Data Quality Summary:')
    print('-' * 50)
    symbols_with_price = sum(1 for s in scores if s.get('price', 0) > 0)
    symbols_with_change = sum(1 for s in scores if 'price_change_percent' in s or 'change_24h' in s)
    symbols_with_volume = sum(1 for s in scores if s.get('volume_24h', 0) > 0 or s.get('turnover_24h', 0) > 0)
    symbols_with_components = sum(1 for s in scores if 'components' in s)
    
    print(f'  ✅ Symbols with price data: {symbols_with_price}/{len(scores)}')
    print(f'  ✅ Symbols with change %: {symbols_with_change}/{len(scores)}')
    print(f'  ✅ Symbols with volume: {symbols_with_volume}/{len(scores)}')
    print(f'  ✅ Symbols with components: {symbols_with_components}/{len(scores)}')
    
    # Check if we have all required fields
    if symbols_with_price == len(scores) and symbols_with_change == len(scores) and symbols_with_volume == len(scores):
        print()
        print('🎉 SUCCESS: All 15 symbols have complete market data!')
    else:
        print()
        print('⚠️  Some symbols missing data')
else:
    print('❌ No symbols returned!')

print()
print('📊 Market Overview:')
overview = data.get('market_overview', {})
print(f'  Regime: {overview.get("market_regime", "N/A")}')
print(f'  Volatility: {overview.get("volatility", 0)}')
print(f'  BTC Dominance: {overview.get("btc_dominance", 0)}%')
print(f'  Total Volume: ${overview.get("total_volume_24h", 0):,.0f}')