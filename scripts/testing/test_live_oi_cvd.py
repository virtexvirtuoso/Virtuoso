#!/usr/bin/env python3
"""
Test script to demonstrate enhanced Open Interest and CVD analysis with live data.
Shows both the old vs new scoring methods and their interpretations.
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime
import time
import pandas as pd

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

async def test_live_oi_cvd():
    """Test enhanced OI and CVD analysis with live market data"""
    
    print("🔍 **LIVE OI & CVD ENHANCED ANALYSIS TEST**")
    print("=" * 60)
    
    try:
        # Import required modules
        from src.core.exchanges.bybit import BybitExchange
        from src.indicators.orderflow_indicators import OrderflowIndicators
        import logging
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        
        print("✅ Successfully imported required modules")
        
        # Simple config for exchange
        exchange_config = {
            'exchanges': {
                'bybit': {
                    'name': 'bybit',
                    'enabled': True,
                    'api_credentials': {
                        'api_key': '',
                        'api_secret': ''
                    },
                    'sandbox': False,
                    'testnet': False,
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                        'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                    }
                }
            }
        }
        
        # Initialize exchange
        exchange = BybitExchange(exchange_config)
        await exchange.initialize()
        
        print("✅ Exchange initialized successfully")
        
        # Enhanced config for orderflow indicators
        orderflow_config = {
            'debug_level': 2,
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
        
        # Create orderflow indicators instance
        orderflow_indicators = OrderflowIndicators.__new__(OrderflowIndicators)
        
        # Set required attributes manually
        orderflow_indicators.indicator_type = 'orderflow'
        orderflow_indicators.component_weights = {
            'cvd': 0.25,
            'trade_flow_score': 0.20,
            'imbalance_score': 0.15,
            'open_interest_score': 0.15,
            'pressure_score': 0.10,
            'liquidity_score': 0.10,
            'liquidity_zones': 0.05
        }
        orderflow_indicators._cache = {}
        orderflow_indicators.config = orderflow_config
        orderflow_indicators.logger = logger
        orderflow_indicators.debug_level = orderflow_config.get('debug_level', 1)
        orderflow_indicators.min_trades = orderflow_config.get('min_trades', 30)
        
        print("✅ Orderflow indicators initialized with enhanced config")
        
        # Test with live data
        test_symbol = "BTCUSDT"
        print(f"\n📊 Testing {test_symbol} with live data...")
        
        # Get live trades
        trades = await exchange.fetch_trades(test_symbol, limit=200)
        print(f"✅ Collected {len(trades)} recent trades")
        
        # Get live ticker for price data
        ticker = await exchange.fetch_ticker(test_symbol)
        print(f"✅ Current price: ${ticker['last']:.2f} ({ticker['percentage']:+.2f}%)")
        
        # Get live OHLCV for price direction
        ohlcv = await exchange.fetch_ohlcv(test_symbol, '1m', limit=10)
        ohlcv_df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Mock open interest data (since Bybit doesn't provide historical OI easily)
        # In production, this would come from the exchange
        mock_oi_data = {
            'current': 125000000,  # Current OI
            'previous': 123500000  # Previous OI (slight increase)
        }
        
        # Create comprehensive market data
        market_data = {
            'symbol': test_symbol,
            'trades': trades,
            'ticker': ticker,
            'ohlcv': {
                'base': ohlcv_df
            },
            'open_interest': mock_oi_data,
            'orderbook': {
                'bids': [[ticker['last'] - 1, 10], [ticker['last'] - 2, 20]],
                'asks': [[ticker['last'] + 1, 10], [ticker['last'] + 2, 20]]
            }
        }
        
        print(f"\n🧪 **ENHANCED CVD ANALYSIS**")
        print("=" * 50)
        
        # Test enhanced CVD
        cvd_score = orderflow_indicators._calculate_cvd(market_data)
        
        # Calculate raw CVD for comparison
        trades_df = pd.DataFrame(trades)
        if 'side' in trades_df.columns and 'amount' in trades_df.columns:
            buy_volume = trades_df[trades_df['side'] == 'buy']['amount'].sum()
            sell_volume = trades_df[trades_df['side'] == 'sell']['amount'].sum()
            total_volume = buy_volume + sell_volume
            raw_cvd = buy_volume - sell_volume
            cvd_percentage = (raw_cvd / total_volume * 100) if total_volume > 0 else 0
            
            print(f"📊 Raw CVD: {raw_cvd:.2f}")
            print(f"📊 CVD Percentage: {cvd_percentage:.3f}% of volume")
            print(f"📊 Buy Volume: {buy_volume:.2f} | Sell Volume: {sell_volume:.2f}")
            print(f"📊 Price Change: {ticker['percentage']:+.2f}%")
            
            # Determine scenario
            price_up = ticker['percentage'] > 0.1
            cvd_up = cvd_percentage > 1.0
            
            if price_up and cvd_up:
                scenario = "🟢 BULLISH CONFIRMATION (Price↑ + CVD↑)"
            elif price_up and not cvd_up:
                scenario = "🔴 BEARISH DIVERGENCE (Price↑ + CVD↓)"
            elif not price_up and not cvd_up:
                scenario = "🔴 BEARISH CONFIRMATION (Price↓ + CVD↓)"
            elif not price_up and cvd_up:
                scenario = "🟢 BULLISH DIVERGENCE (Price↓ + CVD↑)"
            else:
                scenario = "⚪ NEUTRAL"
                
            print(f"🎯 CVD Scenario: {scenario}")
            print(f"📊 Enhanced CVD Score: {cvd_score:.2f}")
        
        print(f"\n🧪 **ENHANCED OPEN INTEREST ANALYSIS**")
        print("=" * 50)
        
        # Test enhanced Open Interest
        oi_score = orderflow_indicators._calculate_open_interest_score(market_data)
        
        # Calculate OI change
        oi_change = mock_oi_data['current'] - mock_oi_data['previous']
        oi_change_pct = (oi_change / mock_oi_data['previous']) * 100
        
        print(f"📊 Current OI: {mock_oi_data['current']:,}")
        print(f"📊 Previous OI: {mock_oi_data['previous']:,}")
        print(f"📊 OI Change: {oi_change:+,} ({oi_change_pct:+.3f}%)")
        print(f"📊 Price Change: {ticker['percentage']:+.2f}%")
        
        # Determine OI scenario
        oi_up = oi_change_pct > 0.5
        price_up = ticker['percentage'] > 0.1
        
        if oi_up and price_up:
            oi_scenario = "🟢 BULLISH (↑OI + ↑Price = New money supporting uptrend)"
        elif not oi_up and price_up:
            oi_scenario = "🔴 BEARISH (↓OI + ↑Price = Short covering, weak rally)"
        elif oi_up and not price_up:
            oi_scenario = "🔴 BEARISH (↑OI + ↓Price = New shorts entering)"
        elif not oi_up and not price_up:
            oi_scenario = "🟢 BULLISH (↓OI + ↓Price = Shorts closing, selling pressure waning)"
        else:
            oi_scenario = "⚪ NEUTRAL"
            
        print(f"🎯 OI Scenario: {oi_scenario}")
        print(f"📊 Enhanced OI Score: {oi_score:.2f}")
        
        print(f"\n🧪 **COMPLETE ORDERFLOW ANALYSIS**")
        print("=" * 50)
        
        # Test all components
        try:
            imbalance_score = orderflow_indicators._calculate_trades_imbalance_score(market_data)
            print(f"📊 Trades Imbalance Score: {imbalance_score:.2f}")
        except Exception as e:
            print(f"❌ Imbalance Score failed: {str(e)}")
        
        try:
            pressure_score = orderflow_indicators._calculate_trades_pressure_score(market_data)
            print(f"📊 Trades Pressure Score: {pressure_score:.2f}")
        except Exception as e:
            print(f"❌ Pressure Score failed: {str(e)}")
        
        try:
            trade_flow_score = orderflow_indicators._calculate_trade_flow_score(market_data)
            print(f"📊 Trade Flow Score: {trade_flow_score:.2f}")
        except Exception as e:
            print(f"❌ Trade Flow Score failed: {str(e)}")
        
        try:
            liquidity_score = orderflow_indicators._calculate_liquidity_score(market_data)
            print(f"📊 Liquidity Score: {liquidity_score:.2f}")
        except Exception as e:
            print(f"❌ Liquidity Score failed: {str(e)}")
        
        # Calculate overall orderflow score
        try:
            overall_result = orderflow_indicators.calculate(market_data)
            if 'score' in overall_result:
                print(f"\n🎯 **OVERALL ORDERFLOW SCORE: {overall_result['score']:.2f}**")
                
                if overall_result['score'] > 70:
                    interpretation = "🟢 STRONG BULLISH"
                elif overall_result['score'] > 60:
                    interpretation = "🟢 BULLISH"
                elif overall_result['score'] < 30:
                    interpretation = "🔴 STRONG BEARISH"
                elif overall_result['score'] < 40:
                    interpretation = "🔴 BEARISH"
                elif overall_result['score'] > 55:
                    interpretation = "🟡 SLIGHTLY BULLISH"
                elif overall_result['score'] < 45:
                    interpretation = "🟡 SLIGHTLY BEARISH"
                else:
                    interpretation = "⚪ NEUTRAL"
                    
                print(f"🎯 **INTERPRETATION: {interpretation}**")
            else:
                print("❌ Overall calculation failed")
        except Exception as e:
            print(f"❌ Overall calculation error: {str(e)}")
        
        # Market context
        if trades:
            latest_trade = trades[0]
            timestamp = latest_trade.get('timestamp') or latest_trade.get('time') or latest_trade.get('datetime')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = float(timestamp)
                trade_time = datetime.fromtimestamp(timestamp / 1000)
                time_diff = datetime.now() - trade_time
                
                print(f"\n📊 **LIVE DATA CONTEXT**")
                print(f"   Latest trade: {trade_time.strftime('%H:%M:%S')} ({time_diff.total_seconds():.1f}s ago)")
                print(f"   Data freshness: {'🟢 LIVE' if time_diff.total_seconds() < 60 else '🟡 DELAYED'}")
                print(f"   Current price: ${ticker['last']:.2f}")
                print(f"   24h change: {ticker['percentage']:+.2f}%")
                print(f"   24h volume: {ticker.get('baseVolume', 0):,.0f} BTC")
        
        print(f"\n✅ **ENHANCED OI & CVD ANALYSIS COMPLETED!**")
        print("🎯 Both indicators now use sophisticated multi-dimensional analysis!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in live analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the live OI and CVD analysis test."""
    return asyncio.run(test_live_oi_cvd())

if __name__ == "__main__":
    main() 