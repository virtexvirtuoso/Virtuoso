#!/usr/bin/env python3
"""Final test showing enhanced OI and CVD analysis with live data."""

import asyncio
import sys
from pathlib import Path
import pandas as pd
import logging

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

async def final_test():
    from src.core.exchanges.bybit import BybitExchange
    from src.indicators.orderflow_indicators import OrderflowIndicators
    
    # Minimal logging
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    
    # Exchange setup
    exchange_config = {
        'exchanges': {
            'bybit': {
                'name': 'bybit',
                'enabled': True,
                'api_credentials': {'api_key': '', 'api_secret': ''},
                'sandbox': False,
                'testnet': False,
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                }
            }
        }
    }
    
    exchange = BybitExchange(exchange_config)
    await exchange.initialize()
    
    # Get live data
    trades = await exchange.fetch_trades('BTCUSDT', limit=150)
    ticker = await exchange.fetch_ticker('BTCUSDT')
    ohlcv = await exchange.fetch_ohlcv('BTCUSDT', '1m', limit=5)
    ohlcv_df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Setup indicators
    config = {
        'debug_level': 1,
        'min_trades': 30,
        'analysis': {
            'indicators': {
                'orderflow': {
                    'cvd': {
                        'price_direction_threshold': 0.1,
                        'cvd_significance_threshold': 0.01
                    },
                    'open_interest': {
                        'normalization_threshold': 5.0,
                        'minimal_change_threshold': 0.5,
                        'price_direction_threshold': 0.1
                    }
                }
            }
        }
    }
    
    indicators = OrderflowIndicators.__new__(OrderflowIndicators)
    indicators.indicator_type = 'orderflow'
    indicators.component_weights = {
        'cvd': 0.25, 'trade_flow_score': 0.20, 'imbalance_score': 0.15,
        'open_interest_score': 0.15, 'pressure_score': 0.10,
        'liquidity_score': 0.10, 'liquidity_zones': 0.05
    }
    indicators._cache = {}
    indicators.config = config
    indicators.logger = logger
    indicators.debug_level = 1
    indicators.min_trades = 30
    
    # Market data
    market_data = {
        'symbol': 'BTCUSDT',
        'trades': trades,
        'ticker': ticker,
        'ohlcv': {'base': ohlcv_df},
        'open_interest': {'current': 125000000, 'previous': 123500000}
    }
    
    print('🔍 **ENHANCED ORDERFLOW ANALYSIS WITH LIVE DATA**')
    print('=' * 60)
    print(f'📊 Current Price: ${ticker["last"]:.2f} ({ticker["percentage"]:+.2f}%)')
    print(f'📊 Trade Count: {len(trades)}')
    
    # Calculate CVD with price analysis
    cvd_score = indicators._calculate_cvd(market_data)
    
    # Calculate raw CVD for context (using correct column names)
    trades_df = pd.DataFrame(trades)
    # Convert side to lowercase for consistency
    trades_df['side_lower'] = trades_df['side'].str.lower()
    buy_vol = trades_df[trades_df['side_lower'] == 'buy']['size'].astype(float).sum()
    sell_vol = trades_df[trades_df['side_lower'] == 'sell']['size'].astype(float).sum()
    total_vol = buy_vol + sell_vol
    raw_cvd = buy_vol - sell_vol
    cvd_pct = (raw_cvd / total_vol * 100) if total_vol > 0 else 0
    
    print(f'\n🧪 **ENHANCED CVD ANALYSIS**')
    print(f'📊 Raw CVD: {raw_cvd:.2f} ({cvd_pct:.3f}% of volume)')
    print(f'📊 Buy Volume: {buy_vol:.2f} | Sell Volume: {sell_vol:.2f}')
    
    # Determine CVD scenario
    price_up = ticker['percentage'] > 0.1
    cvd_up = cvd_pct > 1.0
    
    if price_up and cvd_up:
        scenario = '🟢 BULLISH CONFIRMATION (Price↑ + CVD↑)'
        scenario_desc = 'Aggressive buying driving price up'
    elif price_up and not cvd_up:
        scenario = '🔴 BEARISH DIVERGENCE (Price↑ + CVD↓)'
        scenario_desc = 'Price rising without buying aggression - potential exhaustion'
    elif not price_up and not cvd_up:
        scenario = '🔴 BEARISH CONFIRMATION (Price↓ + CVD↓)'
        scenario_desc = 'Aggressive selling driving price down'
    elif not price_up and cvd_up:
        scenario = '🟢 BULLISH DIVERGENCE (Price↓ + CVD↑)'
        scenario_desc = 'Aggressive buying despite falling price - potential accumulation'
    else:
        scenario = '⚪ NEUTRAL'
        scenario_desc = 'Minimal changes in both price and CVD'
        
    print(f'🎯 CVD Scenario: {scenario}')
    print(f'💡 Meaning: {scenario_desc}')
    print(f'📊 Enhanced CVD Score: {cvd_score:.2f}')
    
    # Calculate OI with price analysis
    oi_score = indicators._calculate_open_interest_score(market_data)
    
    oi_change = 1500000  # 125M - 123.5M
    oi_change_pct = 1.215  # Pre-calculated
    
    print(f'\n🧪 **ENHANCED OPEN INTEREST ANALYSIS**')
    print(f'📊 Current OI: 125,000,000')
    print(f'📊 Previous OI: 123,500,000')
    print(f'📊 OI Change: +{oi_change:,} (+{oi_change_pct:.3f}%)')
    
    # Determine OI scenario
    oi_up = oi_change_pct > 0.5
    
    if oi_up and price_up:
        oi_scenario = '🟢 BULLISH (↑OI + ↑Price)'
        oi_desc = 'New money supporting uptrend'
    elif not oi_up and price_up:
        oi_scenario = '🔴 BEARISH (↓OI + ↑Price)'
        oi_desc = 'Short covering, weak rally'
    elif oi_up and not price_up:
        oi_scenario = '🔴 BEARISH (↑OI + ↓Price)'
        oi_desc = 'New shorts entering'
    elif not oi_up and not price_up:
        oi_scenario = '🟢 BULLISH (↓OI + ↓Price)'
        oi_desc = 'Shorts closing, selling pressure waning'
    else:
        oi_scenario = '⚪ NEUTRAL'
        oi_desc = 'Minimal changes'
        
    print(f'🎯 OI Scenario: {oi_scenario}')
    print(f'💡 Meaning: {oi_desc}')
    print(f'📊 Enhanced OI Score: {oi_score:.2f}')
    
    print(f'\n🎯 **SUMMARY**')
    print('=' * 40)
    print(f'🔸 Market: BTCUSDT at ${ticker["last"]:.2f} ({ticker["percentage"]:+.2f}%)')
    print(f'🔸 CVD Analysis: {scenario.split("(")[0].strip()}')
    print(f'🔸 OI Analysis: {oi_scenario.split("(")[0].strip()}')
    print(f'🔸 CVD Score: {cvd_score:.1f}/100')
    print(f'🔸 OI Score: {oi_score:.1f}/100')
    
    # Overall interpretation
    avg_score = (cvd_score + oi_score) / 2
    if avg_score > 65:
        overall = '🟢 STRONG BULLISH'
    elif avg_score > 55:
        overall = '🟢 BULLISH'
    elif avg_score < 35:
        overall = '🔴 STRONG BEARISH'
    elif avg_score < 45:
        overall = '🔴 BEARISH'
    else:
        overall = '⚪ NEUTRAL'
        
    print(f'🔸 Combined Signal: {overall} (Avg: {avg_score:.1f})')
    
    print(f'\n✅ **ENHANCED ANALYSIS COMPLETE!**')
    print('🎯 Both indicators now use sophisticated multi-dimensional analysis!')
    print('📊 CVD detects aggressive buying/selling vs passive price movement')
    print('📊 OI detects new money flow vs position closure patterns')

if __name__ == "__main__":
    asyncio.run(final_test()) 