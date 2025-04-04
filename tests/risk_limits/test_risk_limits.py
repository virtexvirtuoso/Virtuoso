import sys
import os
import logging
import json

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.indicators.sentiment_indicators import SentimentIndicators

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_risk_limits():
    """Test risk limit calculation with sample Bybit data."""
    try:
        # Sample Bybit risk limit data
        sample_data = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "category": "linear",
                "list": [
                    {
                        "id": 1,
                        "symbol": "BTCUSDT",
                        "riskLimitValue": "2000000",
                        "maintenanceMargin": "0.005",
                        "initialMargin": "0.01",
                        "isLowestRisk": 1,
                        "maxLeverage": "100.00",
                        "mmDeduction": ""
                    },
                    {
                        "id": 2,
                        "symbol": "BTCUSDT",
                        "riskLimitValue": "2600000",
                        "maintenanceMargin": "0.0056",
                        "initialMargin": "0.0111",
                        "isLowestRisk": 0,
                        "maxLeverage": "90.00",
                        "mmDeduction": "1200"
                    }
                ]
            }
        }

        # Create test market data structure
        market_data = {
            'risk_limit': sample_data
        }

        # Initialize SentimentIndicators with complete config
        config = {
            'timeframes': {
                'base': {
                    'interval': '5',
                    'weight': 0.4,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'ltf': {
                    'interval': '1',
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'mtf': {
                    'interval': '30',
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'htf': {
                    'interval': '240',
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 100
                    }
                }
            },
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'parameters': {
                            'sigmoid_transformation': {
                                'default_sensitivity': 0.12
                            }
                        }
                    }
                }
            }
        }

        sentiment_indicator = SentimentIndicators(config)

        # Calculate risk score
        logger.info("Calculating risk score...")
        risk_score = sentiment_indicator._calculate_risk_score(market_data)

        # Log the results
        logger.info("\n=== Risk Score Test Results ===")
        logger.info(f"Final Risk Score: {risk_score:.2f}")

        # Test with full sample data
        full_sample_data = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "category": "linear",
                "list": [
                    {
                        "id": 1,
                        "symbol": "BTCUSDT",
                        "riskLimitValue": "2000000",
                        "maintenanceMargin": "0.005",
                        "initialMargin": "0.01",
                        "isLowestRisk": 1,
                        "maxLeverage": "100.00",
                        "mmDeduction": ""
                    }
                ] + [
                    {
                        "id": i,
                        "symbol": "BTCUSDT",
                        "riskLimitValue": str(2000000 + (i-1)*600000),
                        "maintenanceMargin": str(0.005 + (i-1)*0.001),
                        "initialMargin": str(0.01 + (i-1)*0.002),
                        "isLowestRisk": 0,
                        "maxLeverage": str(100.0 - (i-1)*5.0),
                        "mmDeduction": str(1000 * (i-1))
                    }
                    for i in range(2, 36)
                ]
            }
        }

        # Test with full sample data
        market_data_full = {
            'risk_limit': full_sample_data
        }

        logger.info("\nCalculating risk score with full sample data...")
        risk_score_full = sentiment_indicator._calculate_risk_score(market_data_full)
        logger.info(f"Final Risk Score (full data): {risk_score_full:.2f}")

        # Print detailed breakdown of the calculation
        logger.info("\nDetailed Risk Score Calculation:")
        logger.info("1. Base Tier (Tier 1):")
        base_tier = full_sample_data['result']['list'][0]
        logger.info(f"   - Initial Margin: {base_tier['initialMargin']}")
        logger.info(f"   - Max Leverage: {base_tier['maxLeverage']}")
        logger.info(f"   - Risk Limit Value: {base_tier['riskLimitValue']}")
        
        logger.info("\n2. Market Depth:")
        logger.info(f"   - Number of Tiers: {len(full_sample_data['result']['list'])}")
        logger.info(f"   - Max Risk Limit: {full_sample_data['result']['list'][-1]['riskLimitValue']}")
        logger.info(f"   - Min Risk Limit: {full_sample_data['result']['list'][0]['riskLimitValue']}")

    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)

def test_sentiment_indicators():
    """Test sentiment indicators with Bybit data."""
    
    # Configure the sentiment indicators
    config = {
        'timeframes': {
            'base': {'interval': '5', 'weight': 0.4, 'validation': {'min_candles': 100}},
            'ltf': {'interval': '1', 'weight': 0.2, 'validation': {'min_candles': 100}},
            'mtf': {'interval': '30', 'weight': 0.2, 'validation': {'min_candles': 100}},
            'htf': {'interval': '240', 'weight': 0.2, 'validation': {'min_candles': 100}}
        },
        'analysis': {
            'indicators': {
                'sentiment': {
                    'parameters': {
                        'sigmoid_transformation': {
                            'default_sensitivity': 0.12
                        }
                    }
                }
            }
        }
    }
    
    # Initialize sentiment indicators
    sentiment = SentimentIndicators(config)
    
    # Test data with Bybit format
    market_data = {
        'sentiment': {},
        'long_short_ratio': {
            'list': [
                {
                    'symbol': 'BTCUSDT',
                    'buyRatio': '0.6002',
                    'sellRatio': '0.3998',
                    'timestamp': '1740415200000'
                }
            ]
        },
        'risk_limit': {
            'id': 1,
            'symbol': 'BTCUSDT',
            'riskLimitValue': '2000000',
            'maintenanceMargin': '0.005',
            'initialMargin': '0.01',
            'isLowestRisk': 1,
            'maxLeverage': '100.00'
        }
    }
    
    logger.info("Testing sentiment calculation...")
    result = sentiment._calculate_lsr_score(market_data['long_short_ratio']['list'][0])
    logger.info(f"\nLong/Short Ratio Score: {result}")
    
    # Test with full market data
    market_data_full = {
        'sentiment': {},
        'long_short_ratio': {
            'list': [
                {
                    'symbol': 'BTCUSDT',
                    'buyRatio': '0.5946',
                    'sellRatio': '0.4054',
                    'timestamp': '1735524900000'
                }
            ]
        },
        'risk_limit': {
            'category': 'linear',
            'list': [
                {
                    'id': 1,
                    'symbol': 'BTCUSDT',
                    'riskLimitValue': '2000000',
                    'maintenanceMargin': '0.005',
                    'initialMargin': '0.01',
                    'isLowestRisk': 1,
                    'maxLeverage': '100.00'
                }
            ]
        }
    }
    
    logger.info("\nTesting with full market data...")
    result_full = sentiment._calculate_lsr_score(market_data_full['long_short_ratio']['list'][0])
    logger.info(f"Long/Short Ratio Score (full data): {result_full}")
    
    logger.info("\nDetailed Long/Short Ratio Analysis:")
    logger.info("1. Basic Test:")
    logger.info(f"   - Buy Ratio: 0.6002 (60.02%)")
    logger.info(f"   - Sell Ratio: 0.3998 (39.98%)")
    logger.info(f"   - Score: {result}")
    logger.info("\n2. Full Data Test:")
    logger.info(f"   - Buy Ratio: 0.5946 (59.46%)")
    logger.info(f"   - Sell Ratio: 0.4054 (40.54%)")
    logger.info(f"   - Score: {result_full}")

if __name__ == "__main__":
    test_risk_limits()
    test_sentiment_indicators() 