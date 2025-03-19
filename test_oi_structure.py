import json
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('oi_structure_test')

def test_oi_structure():
    """Test the structure of open interest data for price-OI divergence calculation."""
    
    # Create a mock market data structure with proper open interest data
    market_data = {
        'symbol': 'BTC/USDT',
        'timestamp': 1735525000000,
        'open_interest': {
            'current': 2301512.557,
            'previous': 2301422.912,
            'value': 221755125901.48,
            'timestamp': 1735525000000,
            'history': [
                {'timestamp': 1735524600000, 'value': 2301512.557, 'symbol': 'BTCUSDT'},
                {'timestamp': 1735524300000, 'value': 2301422.912, 'symbol': 'BTCUSDT'},
                {'timestamp': 1735524000000, 'value': 2301377.931, 'symbol': 'BTCUSDT'},
                {'timestamp': 1735523700000, 'value': 2301144.778, 'symbol': 'BTCUSDT'},
                {'timestamp': 1735523400000, 'value': 2301680.998, 'symbol': 'BTCUSDT'}
            ]
        },
        'ohlcv': {
            '1': {
                'data': [
                    {'timestamp': 1735524600000, 'open': 96405.4, 'high': 96420.0, 'low': 96405.4, 'close': 96405.4, 'volume': 12.035},
                    {'timestamp': 1735524300000, 'open': 96405.4, 'high': 96420.0, 'low': 96405.4, 'close': 96405.4, 'volume': 1.315},
                    {'timestamp': 1735524000000, 'open': 96405.4, 'high': 96420.0, 'low': 96405.4, 'close': 96405.4, 'volume': 1.539},
                    {'timestamp': 1735523700000, 'open': 96405.4, 'high': 96420.0, 'low': 96405.4, 'close': 96405.4, 'volume': 1.33},
                    {'timestamp': 1735523400000, 'open': 96405.4, 'high': 96420.0, 'low': 96405.4, 'close': 96405.4, 'volume': 2.5}
                ]
            }
        }
    }
    
    # Check if the market data has the required structure manually first
    if 'open_interest' in market_data:
        oi_data = market_data['open_interest']
        logger.info(f"Found open interest data at top level with keys: {list(oi_data.keys())}")
        
        if 'history' in oi_data and isinstance(oi_data['history'], list):
            logger.info(f"Found history with {len(oi_data['history'])} entries")
            logger.info(f"First history entry: {oi_data['history'][0]}")
            
            # Check if history entries have the required fields
            if all(isinstance(entry, dict) and 'timestamp' in entry and 'value' in entry for entry in oi_data['history']):
                logger.info("All history entries have required fields (timestamp, value)")
            else:
                logger.error("Some history entries are missing required fields")
        else:
            logger.error("Missing or invalid history in open interest data")
    else:
        logger.error("Missing open interest data at top level")
    
    # Now try using the OrderflowIndicators class
    try:
        # Try to import OrderflowIndicators class
        from src.indicators.orderflow_indicators import OrderflowIndicators
        
        # Create a proper configuration for OrderflowIndicators
        indicator_config = {
            'timeframes': {
                '1m': {'weight': 1.0},
                '5m': {'weight': 1.0},
                '15m': {'weight': 1.0},
                '1h': {'weight': 1.0}
            },
            'components': {
                'imbalance': {'weight': 1.0},
                'cvd': {'weight': 1.0},
                'trade_flow': {'weight': 1.0},
                'open_interest': {'weight': 1.0}
            },
            'signal_threshold': 70.0,
            'cache_timeout': 60.0,
            'time_weighting': True,
            'recency_factor': 0.95
        }
        
        # Create an instance of OrderflowIndicators
        logger.info("Creating OrderflowIndicators instance...")
        indicators = OrderflowIndicators(indicator_config)
        
        # Get open interest values
        logger.info("Getting open interest values...")
        oi_values = indicators._get_open_interest_values(market_data)
        logger.info(f"Open interest values: {oi_values}")
        
        # Calculate price-OI divergence
        logger.info("Calculating price-OI divergence...")
        divergence = indicators._calculate_price_oi_divergence(market_data)
        logger.info(f"Divergence result: {divergence}")
        
        # If we got this far without errors, the structure is correct
        logger.info("Price-OI divergence calculation completed successfully")
        logger.info("The structure of open interest data is correct for price-OI divergence calculation")
        
    except Exception as e:
        logger.error(f"Error testing OrderflowIndicators: {str(e)}", exc_info=True)
    
    logger.info("Test completed")

if __name__ == "__main__":
    test_oi_structure() 