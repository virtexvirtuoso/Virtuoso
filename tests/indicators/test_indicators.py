import logging
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_script")

try:
    from src.indicators.technical_indicators import TechnicalIndicators
    logger.info("Successfully imported TechnicalIndicators")
except ImportError as e:
    logger.error(f"Failed to import TechnicalIndicators: {e}")
    exit(1)

# Create sample OHLCV data
def create_test_data():
    """Create test data with different timeframes and lengths"""
    # Create a timestamp range
    now = datetime.now()
    
    # Base timeframe (1m) - create 100+ datapoints
    base_dates = pd.date_range(end=now, periods=120, freq='1min')
    base_df = pd.DataFrame({
        'open': np.random.rand(len(base_dates)) * 100 + 20000,
        'high': np.random.rand(len(base_dates)) * 100 + 20050,
        'low': np.random.rand(len(base_dates)) * 100 + 19950,
        'close': np.random.rand(len(base_dates)) * 100 + 20000,
        'volume': np.random.rand(len(base_dates)) * 1000
    }, index=base_dates)
    
    # LTF timeframe (5m) - create 50 datapoints
    ltf_dates = pd.date_range(end=now, periods=50, freq='5min')
    ltf_df = pd.DataFrame({
        'open': np.random.rand(len(ltf_dates)) * 100 + 20000,
        'high': np.random.rand(len(ltf_dates)) * 100 + 20050,
        'low': np.random.rand(len(ltf_dates)) * 100 + 19950,
        'close': np.random.rand(len(ltf_dates)) * 100 + 20000,
        'volume': np.random.rand(len(ltf_dates)) * 1000
    }, index=ltf_dates)
    
    # MTF timeframe (30m) - create 30 datapoints
    mtf_dates = pd.date_range(end=now, periods=34, freq='30min')
    mtf_df = pd.DataFrame({
        'open': np.random.rand(len(mtf_dates)) * 100 + 20000,
        'high': np.random.rand(len(mtf_dates)) * 100 + 20050,
        'low': np.random.rand(len(mtf_dates)) * 100 + 19950,
        'close': np.random.rand(len(mtf_dates)) * 100 + 20000,
        'volume': np.random.rand(len(mtf_dates)) * 1000
    }, index=mtf_dates)
    
    # HTF timeframe (4h) - create 10 datapoints
    htf_dates = pd.date_range(end=now, periods=10, freq='4h')
    htf_df = pd.DataFrame({
        'open': np.random.rand(len(htf_dates)) * 100 + 20000,
        'high': np.random.rand(len(htf_dates)) * 100 + 20050,
        'low': np.random.rand(len(htf_dates)) * 100 + 19950,
        'close': np.random.rand(len(htf_dates)) * 100 + 20000,
        'volume': np.random.rand(len(htf_dates)) * 1000
    }, index=htf_dates)
    
    return {
        'base': base_df,
        'ltf': ltf_df,
        'mtf': mtf_df,
        'htf': htf_df
    }

async def test_technical_indicators():
    """Test the TechnicalIndicators class with our sample data"""
    logger.info("Initializing TechnicalIndicators")
    
    # Create complete configuration with timeframes and validation
    config = {
        'analysis': {
            'indicators': {
                'momentum': {
                    'min_points': 100  # Default minimum points
                }
            }
        },
        'timeframes': {
            'base': {
                'interval': '1m',
                'friendly_name': '1-min',
                'validation': {
                    'min_candles': 100,
                    'max_age': 3600
                },
                'weight': 1.0
            },
            'ltf': {
                'interval': '5m',
                'friendly_name': '5-min',
                'validation': {
                    'min_candles': 40,
                    'max_age': 18000
                },
                'weight': 0.8
            },
            'mtf': {
                'interval': '30m',
                'friendly_name': '30-min',
                'validation': {
                    'min_candles': 20,
                    'max_age': 86400
                },
                'weight': 0.6
            },
            'htf': {
                'interval': '4h',
                'friendly_name': '4-hour',
                'validation': {
                    'min_candles': 5,
                    'max_age': 604800
                },
                'weight': 0.4
            }
        },
        'validation': {
            'min_candles': 20,
            'timeframe_weights': {
                'base': 1.0,
                'ltf': 0.8,
                'mtf': 0.6,
                'htf': 0.4
            }
        }
    }
    
    # Initialize TechnicalIndicators with the complete config
    try:
        indicator = TechnicalIndicators(config=config, logger=logger)
        # Set the TIMEFRAME_CONFIG directly on the instance to match our test data
        indicator.TIMEFRAME_CONFIG = {
            'base': {
                'interval': '1m',
                'friendly_name': '1-min',
                'validation': {
                    'min_candles': 100,
                    'max_age': 3600
                },
                'weight': 1.0
            },
            'ltf': {
                'interval': '5m',
                'friendly_name': '5-min',
                'validation': {
                    'min_candles': 40,
                    'max_age': 18000
                },
                'weight': 0.8
            },
            'mtf': {
                'interval': '30m',
                'friendly_name': '30-min',
                'validation': {
                    'min_candles': 20,
                    'max_age': 86400
                },
                'weight': 0.6
            },
            'htf': {
                'interval': '4h',
                'friendly_name': '4-hour',
                'validation': {
                    'min_candles': 5,
                    'max_age': 604800
                },
                'weight': 0.4
            }
        }
        logger.info("Successfully initialized TechnicalIndicators")
    except Exception as e:
        logger.error(f"Failed to initialize TechnicalIndicators: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    # Create test data
    test_data = create_test_data()
    
    # Prepare input data for validation
    input_data = {
        'ohlcv': test_data,
        'symbol': 'BTCUSDT'
    }
    
    # Test validation
    try:
        logger.info("Testing _validate_input method")
        logger.info(f"Data points in test data: base={len(test_data['base'])}, ltf={len(test_data['ltf'])}, mtf={len(test_data['mtf'])}, htf={len(test_data['htf'])}")
        validation_result = indicator._validate_input(input_data)
        logger.info(f"Validation result: {validation_result}")
        
        if validation_result:
            logger.info("✅ Validation passed successfully!")
        else:
            logger.error("❌ Validation failed")
            
        # Test calculate method as well if validation passes
        if validation_result:
            logger.info("Testing calculate method")
            result = await indicator.calculate(input_data)
            logger.info(f"Calculation result: {result}")
            
            if result.get('score', 0) > 0:
                logger.info("✅ Calculation succeeded!")
            else:
                logger.error("❌ Calculation failed")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting test script")
    asyncio.run(test_technical_indicators()) 