import pandas as pd
import logging
import random
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_simple_oi')

def mock_calculate_price_oi_divergence(market_data):
    """Simplified version of the _calculate_price_oi_divergence method 
    to test if the structure we're providing will avoid the warning."""
    
    logger.info("Starting mock price-OI divergence calculation")
    
    # Check if open interest data is available
    if ('open_interest' not in market_data and 
        ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
        logger.warning("Missing open interest data for price-OI divergence calculation")
        return {'type': 'neutral', 'strength': 0.0}
    
    # Check for open interest at the top level (our fixed structure)
    logger.info("Checking for open interest data")
    oi_data = None
    oi_history = []
    
    if 'open_interest' in market_data:
        oi_data = market_data['open_interest']
        logger.info(f"Found open interest data at top level with keys: {list(oi_data.keys())}")
    elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
        oi_data = market_data['sentiment']['open_interest']
        logger.info(f"Found open interest data in sentiment section with keys: {list(oi_data.keys())}")
    else:
        logger.warning("Missing open interest data for price-OI divergence calculation")
        return {'type': 'neutral', 'strength': 0.0}
    
    # Get open interest history
    if isinstance(oi_data, dict) and 'history' in oi_data:
        oi_history = oi_data['history']
        logger.info(f"Found open interest history with {len(oi_history)} entries")
    elif isinstance(oi_data, list):
        oi_history = oi_data
        logger.info(f"Using open interest data directly as list with {len(oi_history)} entries")
    else:
        logger.warning("No open interest history available for divergence calculation")
        return {'type': 'neutral', 'strength': 0.0}
    
    if len(oi_history) < 2:
        logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
        return {'type': 'neutral', 'strength': 0.0}
    
    # If we made it here, the data structure is correct
    logger.info("Data structure is correct for price-OI divergence calculation")
    logger.info(f"First history entry: {oi_history[0]}")
    
    # For a real implementation, we would do further calculations here
    # But for the test, we just return a mock result
    return {'type': 'bullish', 'strength': 75.0}

def test_market_data_structure():
    """Test if our fixed market data structure solves the issue"""
    
    # Create a test market data structure with our fixed open interest data
    market_data = {
        'symbol': 'BTC/USDT',
        'timestamp': int(time.time() * 1000),
        'open_interest': {
            'current': 2301512.557,
            'previous': 2301422.912,
            'value': 221755125901.48,
            'timestamp': int(time.time() * 1000),
            'history': [
                {'timestamp': int(time.time() * 1000), 'value': 2301512.557, 'symbol': 'BTCUSDT'},
                {'timestamp': int(time.time() * 1000) - 300000, 'value': 2301422.912, 'symbol': 'BTCUSDT'},
                {'timestamp': int(time.time() * 1000) - 600000, 'value': 2301377.931, 'symbol': 'BTCUSDT'},
                {'timestamp': int(time.time() * 1000) - 900000, 'value': 2301144.778, 'symbol': 'BTCUSDT'},
                {'timestamp': int(time.time() * 1000) - 1200000, 'value': 2301680.998, 'symbol': 'BTCUSDT'}
            ]
        }
    }
    
    # Test with our mock implementation
    divergence = mock_calculate_price_oi_divergence(market_data)
    logger.info(f"Divergence result: {divergence}")
    
    # Test a structure without history (should produce a warning)
    bad_market_data = {
        'symbol': 'BTC/USDT',
        'timestamp': int(time.time() * 1000),
        'open_interest': {
            'current': 2301512.557,
            'previous': 2301422.912,
            'value': 221755125901.48,
            'timestamp': int(time.time() * 1000)
        }
    }
    
    logger.info("\nTesting with bad market data (missing history):")
    divergence = mock_calculate_price_oi_divergence(bad_market_data)
    logger.info(f"Divergence result: {divergence}")
    
    # Test a structure with empty history (should produce a warning)
    empty_history_data = {
        'symbol': 'BTC/USDT',
        'timestamp': int(time.time() * 1000),
        'open_interest': {
            'current': 2301512.557,
            'previous': 2301422.912,
            'value': 221755125901.48,
            'timestamp': int(time.time() * 1000),
            'history': []
        }
    }
    
    logger.info("\nTesting with empty history:")
    divergence = mock_calculate_price_oi_divergence(empty_history_data)
    logger.info(f"Divergence result: {divergence}")
    
    # Test a structure with just one history entry (should produce a warning)
    single_history_data = {
        'symbol': 'BTC/USDT',
        'timestamp': int(time.time() * 1000),
        'open_interest': {
            'current': 2301512.557,
            'previous': 2301422.912,
            'value': 221755125901.48,
            'timestamp': int(time.time() * 1000),
            'history': [
                {'timestamp': int(time.time() * 1000), 'value': 2301512.557, 'symbol': 'BTCUSDT'}
            ]
        }
    }
    
    logger.info("\nTesting with single history entry:")
    divergence = mock_calculate_price_oi_divergence(single_history_data)
    logger.info(f"Divergence result: {divergence}")
    
    logger.info("\nTest completed")

if __name__ == "__main__":
    test_market_data_structure() 