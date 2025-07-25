#!/usr/bin/env python3
"""Test script to verify range volume validation fix."""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.config.config_manager import ConfigManager
from src.indicators.price_structure_indicators import PriceStructureIndicators

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_test_data(num_periods=100, consolidation_volume_ratio=0.6):
    """Generate test OHLCV data with a consolidation range."""
    dates = pd.date_range(end=datetime.now(), periods=num_periods, freq='1h')
    
    # Base price around 100
    base_price = 100
    
    # Generate trending data for first half
    trend_periods = num_periods // 2
    prices_trend = base_price + np.linspace(0, 10, trend_periods) + np.random.randn(trend_periods) * 0.5
    
    # Generate range-bound data for second half (consolidation)
    range_periods = num_periods - trend_periods
    range_center = prices_trend[-1]
    range_width = 2.0  # 2% range
    prices_range = range_center + np.sin(np.linspace(0, 4*np.pi, range_periods)) * range_width/2 + np.random.randn(range_periods) * 0.2
    
    # Combine prices
    prices = np.concatenate([prices_trend, prices_range])
    
    # Generate OHLCV
    data = []
    base_volume = 1000000
    
    for i in range(num_periods):
        close = prices[i]
        open_price = prices[i-1] if i > 0 else close - 0.1
        high = max(open_price, close) + abs(np.random.randn() * 0.2)
        low = min(open_price, close) - abs(np.random.randn() * 0.2)
        
        # Volume: higher during trend, lower during consolidation
        if i < trend_periods:
            volume = base_volume * (1 + abs(np.random.randn() * 0.5))
        else:
            # Consolidation has lower volume
            volume = base_volume * consolidation_volume_ratio * (1 + abs(np.random.randn() * 0.3))
        
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df

async def test_range_analysis():
    """Test the range analysis with the volume fix."""
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        config = config_manager._config
        
        # Initialize indicator
        indicator = PriceStructureIndicators(config, logger)
        
        # Test with different volume ratios
        volume_ratios = [0.4, 0.6, 0.8, 1.0]
        
        logger.info("Testing range analysis with different consolidation volume ratios...")
        logger.info(f"Range volume threshold configured: {indicator.vol_range_threshold}")
        
        for ratio in volume_ratios:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing with consolidation volume ratio: {ratio:.1f}")
            
            # Generate test data
            df = generate_test_data(consolidation_volume_ratio=ratio)
            
            # Create market data structure
            market_data = {
                'symbol': 'TEST/USDT',
                'ohlcv': {
                    'base': df,
                    'ltf': df,
                    'mtf': df,
                    'htf': df
                }
            }
            
            # Analyze range
            try:
                range_score = indicator._analyze_range(market_data['ohlcv'])
                logger.info(f"Range analysis score: {range_score:.2f}")
                
                # Check individual timeframe results
                for tf in ['base', 'ltf', 'mtf', 'htf']:
                    if tf in market_data['ohlcv']:
                        range_result = indicator._identify_range(market_data['ohlcv'][tf])
                        logger.info(f"  {tf}: valid={range_result['is_valid']}, "
                                  f"low={range_result['low']:.4f}, high={range_result['high']:.4f}")
                
            except Exception as e:
                logger.error(f"Error analyzing range: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"\n{'='*60}")
        logger.info("Range analysis test completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_range_analysis())