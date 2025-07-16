#!/usr/bin/env python3
"""
Test script for enhanced market reporter features
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from monitoring.market_reporter import MarketReporter
from core.exchanges.bybit_exchange import BybitExchange

async def test_enhanced_features():
    print('🚀 Testing Enhanced Market Reporter Features...')
    
    # Initialize exchange and reporter
    exchange = BybitExchange()
    reporter = MarketReporter(exchange=exchange)
    
    # Test symbols
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    print(f'📊 Testing with symbols: {test_symbols}')
    
    # Test enhanced futures premium calculation
    print('\n🔄 Testing Enhanced Futures Premium Calculation...')
    try:
        futures_premium = await reporter._calculate_futures_premium(test_symbols)
        print(f'✅ Futures Premium: Found {len(futures_premium.get("premiums", {}))} symbols')
        print(f'   - Average Premium: {futures_premium.get("average_premium", "N/A")}')
        print(f'   - Contango Status: {futures_premium.get("contango_status", "N/A")}')
        print(f'   - Quarterly Futures: {len(futures_premium.get("quarterly_futures", {}))} symbols')
        print(f'   - Funding Rates: {len(futures_premium.get("funding_rates", {}))} symbols')
        
        # Show sample premium data
        for symbol, premium_data in list(futures_premium.get("premiums", {}).items())[:2]:
            print(f'   - {symbol}: {premium_data.get("premium", "N/A")} ({premium_data.get("premium_type", "N/A")})')
            
    except Exception as e:
        print(f'❌ Futures Premium Error: {e}')
    
    # Test enhanced smart money index
    print('\n🧠 Testing Enhanced Smart Money Index...')
    try:
        smart_money = await reporter._calculate_smart_money_index(test_symbols)
        print(f'✅ Smart Money Index: {smart_money.get("index", "N/A")}')
        print(f'   - Signal: {smart_money.get("signal", "N/A")}')
        print(f'   - Sentiment: {smart_money.get("sentiment", "N/A")}')
        print(f'   - Institutional Flow: {smart_money.get("institutional_flow", "N/A")}')
        print(f'   - Key Zones: {len(smart_money.get("key_zones", []))} zones')
        print(f'   - Technical Score: {smart_money.get("technical_score", "N/A")}')
        print(f'   - Flow Score: {smart_money.get("flow_score", "N/A")}')
        print(f'   - Funding Classification: {smart_money.get("funding_rates_classification", "N/A")}')
        
        # Show sample key zones
        for zone in smart_money.get("key_zones", [])[:3]:
            print(f'   - Zone: {zone.get("type", "N/A")} at ${zone.get("price", 0):.2f} ({zone.get("distance_pct", 0):.2f}%)')
            
    except Exception as e:
        print(f'❌ Smart Money Error: {e}')
    
    # Test enhanced whale activity
    print('\n🐋 Testing Enhanced Whale Activity...')
    try:
        whale_activity = await reporter._calculate_whale_activity(test_symbols)
        whale_data = whale_activity.get('whale_activity', {})
        print(f'✅ Whale Activity: {whale_data.get("count", 0)} transactions')
        print(f'   - Total Volume: ${whale_data.get("total_volume", 0):,.0f}')
        print(f'   - Buy Volume: ${whale_data.get("buy_volume", 0):,.0f}')
        print(f'   - Sell Volume: ${whale_data.get("sell_volume", 0):,.0f}')
        print(f'   - Net Volume: ${whale_data.get("net_volume", 0):,.0f}')
        print(f'   - Whale Sentiment: {whale_data.get("whale_sentiment", "N/A")}')
        print(f'   - Whale Bias: {whale_data.get("whale_bias", 0):.2f}%')
        print(f'   - Symbols Affected: {whale_data.get("symbols_affected", 0)}')
        print(f'   - Has Significant Activity: {whale_activity.get("has_significant_activity", False)}')
        
        whale_summary = whale_activity.get("whale_summary", "N/A")
        if len(whale_summary) > 100:
            whale_summary = whale_summary[:100] + "..."
        print(f'   - Summary: {whale_summary}')
        
        # Show sample transactions
        transactions = whale_data.get("transactions", [])
        if transactions:
            print(f'   - Sample Transactions:')
            for tx in transactions[:3]:
                print(f'     * {tx.get("symbol", "N/A")}: {tx.get("side", "N/A")} ${tx.get("usd_value", 0):,.0f} (confidence: {tx.get("whale_confidence", 0):.1f}x)')
        
        # Show significant activity by symbol
        sig_activity = whale_activity.get("significant_activity", {})
        if sig_activity:
            print(f'   - Significant Activity by Symbol:')
            for symbol, activity in list(sig_activity.items())[:3]:
                print(f'     * {symbol}: {activity.get("transaction_count", 0)} txs, ${activity.get("usd_value", 0):,.0f} volume')
                
    except Exception as e:
        print(f'❌ Whale Activity Error: {e}')
    
    print('\n🎯 Enhanced Features Test Complete!')
    print('\n📈 Summary of Enhancements:')
    print('   ✅ Futures Premium: Comprehensive quarterly futures analysis, term structure, funding rates')
    print('   ✅ Smart Money Index: Institutional flow analysis, order clustering, key zones')
    print('   ✅ Whale Activity: Dynamic thresholds, market impact, sentiment analysis')

if __name__ == "__main__":
    asyncio.run(test_enhanced_features()) 