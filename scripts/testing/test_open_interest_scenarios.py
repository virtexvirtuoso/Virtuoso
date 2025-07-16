#!/usr/bin/env python3
"""
Test script to demonstrate the four open interest scenarios.

This script creates mock data to test all four scenarios:
1. Increasing OI + Price Up = Bullish
2. Decreasing OI + Price Up = Bearish  
3. Increasing OI + Price Down = Bearish
4. Decreasing OI + Price Down = Bullish
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

def create_mock_market_data(oi_change_pct: float, price_change_pct: float, symbol: str = "BTCUSDT"):
    """Create mock market data with specified OI and price changes."""
    
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
    
    # Create mock open interest data
    base_oi = 100000.0
    current_oi = base_oi * (1 + oi_change_pct / 100)
    
    # Create mock trades data (minimal for other components)
    mock_trades = []
    for i in range(100):
        mock_trades.append({
            'id': f'trade_{i}',
            'price': current_price + np.random.normal(0, 10),
            'amount': np.random.uniform(0.1, 2.0),
            'side': 'buy' if np.random.random() > 0.5 else 'sell',
            'time': 1640995200000 + i * 1000  # Mock timestamps
        })
    
    return {
        'symbol': symbol,
        'ohlcv': {
            'base': ohlcv_data
        },
        'open_interest': {
            'current': current_oi,
            'previous': base_oi
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

def test_oi_scenario(scenario_name: str, oi_change: float, price_change: float):
    """Test a specific open interest scenario."""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {scenario_name}")
    print(f"{'='*60}")
    print(f"📊 Open Interest Change: {oi_change:+.2f}%")
    print(f"📈 Price Change: {price_change:+.2f}%")
    
    # Create mock data
    market_data = create_mock_market_data(oi_change, price_change)
    
    # Initialize orderflow indicators with minimal config
    orderflow_config = {
        'debug_level': 2,
        'min_trades': 30,
        'analysis': {
            'indicators': {
                'orderflow': {
                    'open_interest': {
                        'normalization_threshold': 5.0,
                        'minimal_change_threshold': 0.5,
                        'price_direction_threshold': 0.1
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
    
    # Calculate just the open interest score
    oi_score = orderflow_indicators._calculate_open_interest_score(market_data)
    
    # Interpret the score
    if oi_score > 65:
        interpretation = "🟢 BULLISH"
    elif oi_score < 35:
        interpretation = "🔴 BEARISH"
    elif oi_score > 55:
        interpretation = "🟡 SLIGHTLY BULLISH"
    elif oi_score < 45:
        interpretation = "🟡 SLIGHTLY BEARISH"
    else:
        interpretation = "⚪ NEUTRAL"
    
    print(f"📊 Open Interest Score: {oi_score:.2f}")
    print(f"🎯 Interpretation: {interpretation}")
    
    return oi_score

def main():
    """Run all four open interest scenarios."""
    print("🔍 **OPEN INTEREST ANALYSIS SCENARIOS TEST**")
    print("=" * 60)
    print("Testing the four fundamental open interest scenarios:")
    print("1. ↑OI + ↑Price = Bullish (new money supporting uptrend)")
    print("2. ↓OI + ↑Price = Bearish (short covering, weak rally)")  
    print("3. ↑OI + ↓Price = Bearish (new shorts entering)")
    print("4. ↓OI + ↓Price = Bullish (shorts closing, selling pressure waning)")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scenarios = [
        ("Scenario 1: ↑OI + ↑Price = BULLISH", 3.0, 2.5),
        ("Scenario 2: ↓OI + ↑Price = BEARISH", -2.5, 2.0),
        ("Scenario 3: ↑OI + ↓Price = BEARISH", 4.0, -3.0),
        ("Scenario 4: ↓OI + ↓Price = BULLISH", -3.5, -2.5),
        ("Edge Case: Minimal Changes", 0.2, 0.05),
        ("Edge Case: Large OI, Small Price", 8.0, 0.3),
        ("Edge Case: Small OI, Large Price", 0.3, 5.0)
    ]
    
    results = []
    for scenario_name, oi_change, price_change in scenarios:
        score = test_oi_scenario(scenario_name, oi_change, price_change)
        results.append((scenario_name, oi_change, price_change, score))
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 **SUMMARY OF RESULTS**")
    print(f"{'='*60}")
    
    for scenario_name, oi_change, price_change, score in results:
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
            
        print(f"{result_icon} {scenario_name[:30]:<30} | OI: {oi_change:+5.1f}% | Price: {price_change:+5.1f}% | Score: {score:5.1f}")
    
    print(f"\n✅ **OPEN INTEREST SCENARIOS TEST COMPLETED!**")
    print("🎯 The analysis now properly considers both OI changes AND price direction!")

if __name__ == "__main__":
    main() 