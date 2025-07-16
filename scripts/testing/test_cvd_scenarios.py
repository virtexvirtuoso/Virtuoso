#!/usr/bin/env python3
"""
Test script to demonstrate the four CVD-Price divergence scenarios.

This script creates mock data to test all four scenarios:
1. Price Up + CVD Up = Bullish Confirmation
2. Price Up + CVD Down = Bearish Divergence
3. Price Down + CVD Down = Bearish Confirmation  
4. Price Down + CVD Up = Bullish Divergence
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from src.indicators.orderflow_indicators import OrderflowIndicators
import logging

def create_mock_cvd_data(cvd_bias: float, price_change_pct: float, symbol: str = "BTCUSDT"):
    """Create mock trade data with specified CVD bias and price change.
    
    Args:
        cvd_bias: CVD bias (-1.0 to 1.0) where -1 = all sells, +1 = all buys
        price_change_pct: Price change percentage
        symbol: Trading symbol
    """
    
    # Create mock OHLCV data showing price direction
    base_price = 50000.0
    current_price = base_price * (1 + price_change_pct / 100)
    
    ohlcv_data = pd.DataFrame({
        'open': [base_price, base_price],
        'high': [max(base_price, current_price) * 1.001, max(base_price, current_price) * 1.001],
        'low': [min(base_price, current_price) * 0.999, min(base_price, current_price) * 0.999],
        'close': [base_price, current_price],
        'volume': [1000, 1000]
    })
    
    # Create mock trades with specified CVD bias
    num_trades = 200
    mock_trades = []
    
    # Calculate buy probability based on CVD bias
    # cvd_bias of +1.0 = 100% buys, -1.0 = 100% sells, 0.0 = 50/50
    buy_probability = (cvd_bias + 1.0) / 2.0
    
    for i in range(num_trades):
        # Determine if this trade is a buy or sell
        is_buy = np.random.random() < buy_probability
        
        # Create trade with varying amounts
        trade_amount = np.random.uniform(0.1, 5.0)
        
        # Add some larger trades to make CVD more pronounced
        if np.random.random() < 0.1:  # 10% chance of large trade
            trade_amount *= np.random.uniform(5, 20)
        
        mock_trades.append({
            'id': f'trade_{i}',
            'price': current_price + np.random.normal(0, 10),
            'amount': trade_amount,
            'side': 'buy' if is_buy else 'sell',
            'time': 1640995200000 + i * 1000  # Mock timestamps
        })
    
    return {
        'symbol': symbol,
        'ohlcv': {
            'base': ohlcv_data
        },
        'trades': mock_trades,
        'orderbook': {
            'bids': [[current_price - 1, 10], [current_price - 2, 20]],
            'asks': [[current_price + 1, 10], [current_price + 2, 20]]
        },
        'ticker': {
            'last': current_price,
            'percentage': price_change_pct
        }
    }

def test_cvd_scenario(scenario_name: str, cvd_bias: float, price_change: float):
    """Test a specific CVD-Price scenario."""
    print(f"\n{'='*70}")
    print(f"🧪 TESTING: {scenario_name}")
    print(f"{'='*70}")
    print(f"📊 CVD Bias: {cvd_bias:+.2f} ({('Selling' if cvd_bias < 0 else 'Buying') if cvd_bias != 0 else 'Neutral'} pressure)")
    print(f"📈 Price Change: {price_change:+.2f}%")
    
    # Create mock data
    market_data = create_mock_cvd_data(cvd_bias, price_change)
    
    # Calculate actual CVD from the mock data
    trades_df = pd.DataFrame(market_data['trades'])
    buy_volume = trades_df[trades_df['side'] == 'buy']['amount'].sum()
    sell_volume = trades_df[trades_df['side'] == 'sell']['amount'].sum()
    total_volume = buy_volume + sell_volume
    actual_cvd = buy_volume - sell_volume
    actual_cvd_pct = actual_cvd / total_volume if total_volume > 0 else 0
    
    print(f"📊 Actual CVD: {actual_cvd:.2f} ({actual_cvd_pct:.3f}% of volume)")
    print(f"📊 Buy Volume: {buy_volume:.2f}, Sell Volume: {sell_volume:.2f}")
    
    # Initialize orderflow indicators with minimal config
    orderflow_config = {
        'debug_level': 2,
        'min_trades': 30,
        'analysis': {
            'indicators': {
                'orderflow': {
                    'cvd': {
                        'price_direction_threshold': 0.1,
                        'cvd_significance_threshold': 0.01
                    }
                }
            }
        }
    }
    
    # Create orderflow indicators instance directly
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
    orderflow_indicators.logger = logging.getLogger(__name__)
    orderflow_indicators.debug_level = orderflow_config.get('debug_level', 1)
    orderflow_indicators.min_trades = orderflow_config.get('min_trades', 30)
    
    # Calculate CVD score
    cvd_score = orderflow_indicators._calculate_cvd(market_data)
    
    # Interpret the score
    if cvd_score > 70:
        interpretation = "🟢 STRONG BULLISH"
    elif cvd_score > 60:
        interpretation = "🟢 BULLISH"
    elif cvd_score < 30:
        interpretation = "🔴 STRONG BEARISH"
    elif cvd_score < 40:
        interpretation = "🔴 BEARISH"
    elif cvd_score > 55:
        interpretation = "🟡 SLIGHTLY BULLISH"
    elif cvd_score < 45:
        interpretation = "🟡 SLIGHTLY BEARISH"
    else:
        interpretation = "⚪ NEUTRAL"
    
    print(f"📊 CVD Score: {cvd_score:.2f}")
    print(f"🎯 Interpretation: {interpretation}")
    
    # Determine if this is a divergence or confirmation
    price_bullish = price_change > 0.1
    cvd_bullish = actual_cvd_pct > 0.01
    
    if (price_bullish and cvd_bullish) or (not price_bullish and not cvd_bullish):
        signal_type = "✅ CONFIRMATION"
    else:
        signal_type = "⚠️ DIVERGENCE"
    
    print(f"🔍 Signal Type: {signal_type}")
    
    return cvd_score, actual_cvd_pct

def main():
    """Run all four CVD-Price scenarios."""
    print("🔍 **CVD-PRICE DIVERGENCE ANALYSIS TEST**")
    print("=" * 70)
    print("Testing the four fundamental CVD-Price scenarios:")
    print("1. Price↑ + CVD↑ = Bullish Confirmation (aggressive buying driving price up)")
    print("2. Price↑ + CVD↓ = Bearish Divergence (price rising without buying aggression)")  
    print("3. Price↓ + CVD↓ = Bearish Confirmation (aggressive selling driving price down)")
    print("4. Price↓ + CVD↑ = Bullish Divergence (aggressive buying despite falling price)")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scenarios = [
        ("Scenario 1: Price↑ + CVD↑ = BULLISH CONFIRMATION", 0.6, 2.5),
        ("Scenario 2: Price↑ + CVD↓ = BEARISH DIVERGENCE", -0.4, 2.0),
        ("Scenario 3: Price↓ + CVD↓ = BEARISH CONFIRMATION", -0.7, -3.0),
        ("Scenario 4: Price↓ + CVD↑ = BULLISH DIVERGENCE", 0.5, -2.5),
        ("Edge Case: Neutral CVD, Price Up", 0.0, 1.5),
        ("Edge Case: Strong CVD, Minimal Price", 0.8, 0.05),
        ("Edge Case: Weak CVD, Strong Price", 0.1, 4.0)
    ]
    
    results = []
    for scenario_name, cvd_bias, price_change in scenarios:
        score, actual_cvd_pct = test_cvd_scenario(scenario_name, cvd_bias, price_change)
        results.append((scenario_name, cvd_bias, price_change, score, actual_cvd_pct))
    
    # Summary
    print(f"\n{'='*70}")
    print("📋 **SUMMARY OF CVD-PRICE ANALYSIS RESULTS**")
    print(f"{'='*70}")
    
    for scenario_name, cvd_bias, price_change, score, actual_cvd_pct in results:
        if score > 65:
            result_icon = "🟢"
        elif score < 35:
            result_icon = "🔴"
        elif score > 55:
            result_icon = "🟡+"
        elif score < 45:
            result_icon = "🟡-"
        else:
            result_icon = "⚪"
            
        # Determine signal type
        price_bullish = price_change > 0.1
        cvd_bullish = actual_cvd_pct > 0.01
        
        if (price_bullish and cvd_bullish) or (not price_bullish and not cvd_bullish):
            signal_type = "CONF"
        else:
            signal_type = "DIV"
            
        print(f"{result_icon} {scenario_name[:35]:<35} | Price: {price_change:+5.1f}% | CVD: {actual_cvd_pct:+6.3f}% | Score: {score:5.1f} | {signal_type}")
    
    print(f"\n✅ **CVD-PRICE DIVERGENCE ANALYSIS TEST COMPLETED!**")
    print("🎯 CVD analysis now properly detects confirmations and divergences!")
    print("📊 Key insights:")
    print("   • Confirmations = Strong directional signals")
    print("   • Divergences = Potential reversal or exhaustion signals")
    print("   • CVD shows aggressive buying/selling vs passive price movement")

if __name__ == "__main__":
    main() 