#!/usr/bin/env python3
"""
Test the sentiment indicator with Long/Short ratio data.

This script verifies that:
1. Long/Short ratio is fetched from Bybit API
2. Sentiment indicator properly processes the L/S ratio
3. The complete sentiment calculation works correctly
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager
from src.core.exchanges.bybit import BybitExchange
from src.indicators.sentiment_indicators import SentimentIndicators

async def test_sentiment_with_lsr():
    """Test sentiment indicator with Long/Short ratio data."""
    logger = Logger('test_sentiment_lsr')
    config = ConfigManager().config
    
    # Initialize exchange
    exchange = BybitExchange(config, logger)
    
    # Initialize sentiment indicator
    sentiment_indicator = SentimentIndicators(config, logger)
    
    symbol = 'BTCUSDT'
    
    print("="*60)
    print("Testing Sentiment Indicator with Long/Short Ratio")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print(f"Symbol: {symbol}")
    print()
    
    try:
        # 1. Fetch market data (includes L/S ratio)
        print("1. Fetching market data...")
        market_data = await exchange.fetch_market_data(symbol)
        
        # Check if L/S ratio was fetched
        if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
            lsr = market_data['sentiment']['long_short_ratio']
            print(f"✅ Long/Short ratio fetched successfully:")
            print(f"   Long: {lsr.get('long', 'N/A')}%")
            print(f"   Short: {lsr.get('short', 'N/A')}%")
            print(f"   Timestamp: {datetime.fromtimestamp(lsr.get('timestamp', 0)/1000)}")
        else:
            print("❌ Long/Short ratio not found in market data")
            print(f"   Market data keys: {list(market_data.keys())}")
            if 'sentiment' in market_data:
                print(f"   Sentiment keys: {list(market_data['sentiment'].keys())}")
        
        print()
        
        # 2. Calculate individual sentiment components
        print("2. Calculating sentiment components...")
        
        # Funding rate
        funding_score = sentiment_indicator.calculate_funding_rate(market_data)
        print(f"   Funding Rate Score: {funding_score:.2f}")
        
        # Long/Short ratio
        lsr_score = sentiment_indicator.calculate_long_short_ratio(market_data)
        print(f"   Long/Short Ratio Score: {lsr_score:.2f}")
        
        # Volume sentiment
        volume_score = sentiment_indicator.calculate_volume_sentiment(market_data)
        print(f"   Volume Sentiment Score: {volume_score:.2f}")
        
        # Market mood
        mood_score = sentiment_indicator.calculate_market_mood(market_data)
        print(f"   Market Mood Score: {mood_score:.2f}")
        
        print()
        
        # 3. Calculate overall sentiment
        print("3. Calculating overall sentiment...")
        sentiment_result = await sentiment_indicator.calculate(market_data)
        overall_sentiment = sentiment_result.get('score', 50.0)
        
        print(f"\n✅ Overall Sentiment Score: {overall_sentiment:.2f}")
        
        # Interpret the score
        if overall_sentiment >= 70:
            interpretation = "Strong Bullish"
        elif overall_sentiment >= 60:
            interpretation = "Bullish"
        elif overall_sentiment >= 40:
            interpretation = "Neutral"
        elif overall_sentiment >= 30:
            interpretation = "Bearish"
        else:
            interpretation = "Strong Bearish"
        
        print(f"   Interpretation: {interpretation}")
        
        # 4. Show component weights
        print("\n4. Component Weights:")
        weights = sentiment_indicator.component_weights
        for component, weight in weights.items():
            print(f"   {component}: {weight*100:.1f}%")
        
        # 5. Test direct L/S ratio fetch
        print("\n5. Testing direct L/S ratio fetch...")
        direct_lsr = await exchange._fetch_long_short_ratio(symbol)
        print(f"✅ Direct fetch successful:")
        print(f"   Long: {direct_lsr.get('long', 'N/A')}%")
        print(f"   Short: {direct_lsr.get('short', 'N/A')}%")
        
        # 6. Verify data consistency
        print("\n6. Data Consistency Check:")
        if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
            market_lsr = market_data['sentiment']['long_short_ratio']
            if abs(market_lsr.get('long', 0) - direct_lsr.get('long', 0)) < 0.1:
                print("✅ L/S ratio data is consistent between market data and direct fetch")
            else:
                print("⚠️  L/S ratio data differs between market data and direct fetch")
                print(f"   Market data: Long={market_lsr.get('long')}%, Short={market_lsr.get('short')}%")
                print(f"   Direct fetch: Long={direct_lsr.get('long')}%, Short={direct_lsr.get('short')}%")
        
        # 7. Show full sentiment data structure
        print("\n7. Full Sentiment Data Structure:")
        if 'sentiment' in market_data:
            print(json.dumps(market_data['sentiment'], indent=2, default=str))
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)

async def main():
    """Run the test."""
    await test_sentiment_with_lsr()

if __name__ == "__main__":
    asyncio.run(main())