#!/usr/bin/env python3
"""
Demo script that shows how to include a confluence analysis breakdown in a PDF report.
This script creates a sample trading signal with confluence analysis text and generates a PDF report.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np

# Add the parent directory to the path to allow imports from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the ReportGenerator
from src.core.reporting.pdf_generator import ReportGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample confluence analysis text
SAMPLE_CONFLUENCE_TEXT = """╔════════════════════════════════════════════════════════════════════════════════╗
║ ETHUSDT CONFLUENCE ANALYSIS BREAKDOWN                                         ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ OVERALL SCORE: 61.32 (NEUTRAL)                                                ║
║ RELIABILITY: 100% (HIGH)                                                      ║
╠════════════════════╦════════╦════════╦═════════════════════════════════════╣
║ COMPONENT          ║ SCORE  ║ IMPACT ║ GAUGE                               ║
╠════════════════════╬════════╬════════╬═════════════════════════════════════╣
║ Orderflow          ║ 71.95  ║ 18.2   ║ █████████████████████████·········· ║
║ Orderbook          ║ 78.48  ║ 15.9   ║ ███████████████████████████········ ║
║ Price Structure    ║ 54.54  ║ 8.3    ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓················ ║
║ Technical          ║ 41.73  ║ 7.2    ║ ░░░░░░░░░░░░░░····················· ║
║ Sentiment          ║ 60.67  ║ 6.1    ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓·············· ║
║ Volume             ║ 47.32  ║ 5.7    ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓··················· ║
╠════════════════════╩════════╩════════╩═════════════════════════════════════╣
║ TOP INFLUENTIAL INDIVIDUAL COMPONENTS                                         ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ Technical (41.73)                                                             ║
║  • Atr                 : 59.81  → ▓▓▓▓▓▓▓▓·······                            ║
║  • Macd                : 40.19  ↓ ░░░░░░·········                            ║
║  • Ao                  : 39.74  ↓ ░░░░░··········                            ║
║                                                                                ║
║ Volume (47.32)                                                                ║
║  • Cmf                 : 100.00 ↑ ███████████████                            ║
║  • Adl                 : 57.12  → ▓▓▓▓▓▓▓▓·······                            ║
║  • Obv                 : 49.61  → ▓▓▓▓▓▓▓········                            ║
║                                                                                ║
║ Orderbook (78.48)                                                             ║
║  • Spread              : 100.00 ↑ ██████████████·                            ║
║  • Liquidity           : 93.90  ↑ ██████████████·                            ║
║  • Obps                : 93.38  ↑ ██████████████·                            ║
║                                                                                ║
║ Orderflow (71.95)                                                             ║
║  • Cvd                 : 99.44  ↑ ██████████████·                            ║
║  • Trade Flow Score    : 93.14  ↑ █████████████··                            ║
║  • Open Interest Score : 70.41  ↑ ██████████·····                            ║
║                                                                                ║
║ Sentiment (60.67)                                                             ║
║  • Market Activity     : 95.71  ↑ ██████████████·                            ║
║  • Risk                : 81.43  ↑ ████████████···                            ║
║  • Sentiment           : 60.67  → ▓▓▓▓▓▓▓▓▓······                            ║
║                                                                                ║
║ Price Structure (54.54)                                                       ║
║  • Support Resistance  : 76.55  ↑ ███████████····                            ║
║  • Vwap                : 60.78  → ▓▓▓▓▓▓▓▓▓······                            ║
║  • Volume Profile      : 54.33  → ▓▓▓▓▓▓▓▓·······                            ║
║                                                                                ║
╠════════════════════════════════════════════════════════════════════════════════╣
╠════════════════════════════════════════════════════════════════════════════════╣
║ MARKET INTERPRETATIONS                                                        ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ • Technical: Technical indicators show slight bearish bias within overall     ║
║   neutrality. ATR is the most influential indicator (59.8). Bearish           ║
║   divergence detected: ATR: 1m volatility (2.092931) significantly            ║
║   lower than 5m (5.748050)                                                    ║
║                                                                                ║
║ • Volume: Volume analysis shows increasing selling pressure with rising       ║
║   participation. CMF is particularly strong (100.0). Significant              ║
║   positive volume delta suggests strong buying pressure. Money flow           ║
║   confirms accumulation pattern                                               ║
║                                                                                ║
║ • Orderbook: Orderbook shows Strong bid-side dominance with high bid-side     ║
║   liquidity and tight spreads. Strong order depth suggests stable             ║
║   price levels                                                                ║
║                                                                                ║
║ • Orderflow: Strong bullish orderflow with low liquidity. Rising open interest║
║   confirms trend strength. Positive cumulative volume delta showing           ║
║   buying dominance. Large trades predominantly on the buy side.               ║
║   Bullish divergence between price and orderflow detected                     ║
║                                                                                ║
║ • Sentiment: Moderately bullish market sentiment with high risk conditions and║
║   neutral funding rates                                                       ║
║                                                                                ║
║ • Price Structure: Price structure shows established uptrend. Strong support  ║
║   level identified. Bullish divergence detected in MTF order                  ║
║   block                                                                       ║
║                                                                                ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ CROSS-COMPONENT INSIGHTS                                                      ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ • Bullish orderflow aligned with positive sentiment - strong buying conviction║
║                                                                                ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ ACTIONABLE TRADING INSIGHTS                                                   ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ • NEUTRAL-BULLISH BIAS: Score (61.32) approaching buy threshold - monitor for ║
║   confirmation                                                                ║
║                                                                                ║
║ • RISK ASSESSMENT: HIGH - Reduce position size despite bullish bias and use   ║
║   tighter stops                                                               ║
║                                                                                ║
║ • KEY LEVELS: Support level (strong strength), Strong bid liquidity cluster   ║
║                                                                                ║
║ • STRATEGY: Range-bound conditions likely; consider mean-reversion trades at  ║
║   support/resistance levels                                                   ║"""

async def main():
    # Create sample signal data with confluence analysis text
    signal_data = {
        'symbol': 'ETHUSDT',
        'score': 61.32,
        'reliability': 1.0,  # 100%
        'price': 3456.78,
        'timestamp': datetime.now(),
        'confluence_analysis': SAMPLE_CONFLUENCE_TEXT,
        'components': {
            'Orderflow': {'score': 71.95, 'impact': 18.2, 'interpretation': 'Strong bullish orderflow with low liquidity.'},
            'Orderbook': {'score': 78.48, 'impact': 15.9, 'interpretation': 'Strong bid-side dominance with high liquidity.'},
            'Price Structure': {'score': 54.54, 'impact': 8.3, 'interpretation': 'Established uptrend with strong support.'},
            'Technical': {'score': 41.73, 'impact': 7.2, 'interpretation': 'Slight bearish bias within overall neutrality.'},
            'Sentiment': {'score': 60.67, 'impact': 6.1, 'interpretation': 'Moderately bullish market sentiment.'},
            'Volume': {'score': 47.32, 'impact': 5.7, 'interpretation': 'Increasing selling pressure with rising participation.'}
        },
        'insights': [
            'Technical indicators show slight bearish bias within overall neutrality',
            'Volume analysis indicates increasing selling pressure with rising participation',
            'Orderbook shows strong bid-side dominance with high liquidity',
            'Strong bullish orderflow with increasing open interest',
            'Moderately bullish market sentiment with high risk conditions',
            'Price structure shows established uptrend with strong support'
        ],
        'actionable_insights': [
            'NEUTRAL-BULLISH BIAS: Score (61.32) approaching buy threshold - monitor for confirmation',
            'RISK ASSESSMENT: HIGH - Reduce position size despite bullish bias',
            'KEY LEVELS: Support level (strong strength), Strong bid liquidity cluster',
            'STRATEGY: Range-bound conditions likely; consider mean-reversion trades'
        ],
        'entry_price': 3450.00,
        'stop_loss': 3380.00,
        'targets': {
            'Target 1': {'price': 3520.00, 'size': 50},
            'Target 2': {'price': 3580.00, 'size': 30},
            'Target 3': {'price': 3650.00, 'size': 20}
        }
    }

    # Create sample OHLCV data
    periods = 50
    dates = pd.date_range(end=datetime.now(), periods=periods)
    base_price = 3400
    
    # Create a simulated price series with an uptrend
    np.random.seed(42)  # For reproducibility
    price_changes = np.cumsum(np.random.normal(0.2, 1, periods))  # Slight upward bias
    prices = base_price + price_changes * 10
    
    ohlcv_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices[:-1],
        'close': prices[1:],
        'high': [max(o, c) * (1 + np.random.uniform(0, 0.01)) for o, c in zip(prices[:-1], prices[1:])],
        'low': [min(o, c) * (1 - np.random.uniform(0, 0.01)) for o, c in zip(prices[:-1], prices[1:])],
        'volume': [np.random.uniform(100, 1000) for _ in range(periods-1)]
    })
    
    # Create output directory for reports
    output_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the report generator
    generator = ReportGenerator(log_level=logging.INFO)
    
    # Generate the report
    logger.info("Generating PDF report with confluence analysis breakdown...")
    pdf_path, json_path = generator.generate_trading_report(signal_data, ohlcv_data, output_dir)
    
    if pdf_path:
        logger.info(f"PDF report generated successfully: {pdf_path}")
    else:
        logger.error("Failed to generate PDF report")
    
    if json_path:
        logger.info(f"JSON data exported: {json_path}")

if __name__ == "__main__":
    asyncio.run(main()) 