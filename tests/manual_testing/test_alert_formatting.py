#!/usr/bin/env python3
"""Test script to verify alert formatting improvements."""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.manager import ConfigManager
from src.monitoring.alert_manager import AlertManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("AlertFormattingTest")

# Load config
def load_config():
    """Load configuration from file."""
    try:
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        config_path = base_dir / 'config.yaml'
        
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}, trying alternative path...")
            config_path = base_dir / 'config' / 'config.yaml'
            
        if not config_path.exists():
            logger.error("Config file not found")
            raise FileNotFoundError("Config file not found")
            
        # Load configuration
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

# Test data for alerts
def create_test_signal() -> Dict[str, Any]:
    """Create a complete test signal for formatting testing."""
    return {
        'symbol': 'ETHUSDT',
        'signal': 'sell',
        'score': 39.28,
        'confluence_score': 39.28,
        'price': 2189.39,
        'timestamp': int(time.time() * 1000),
        'components': {
            'volume': 35.05,
            'orderbook': 52.78,
            'orderflow': 17.17,
            'technical': 40.95,
            'price_structure': 50.53,
            'sentiment': 51.61
        },
        'results': {
            'technical': {
                'score': 40.95,
                'components': {
                    'rsi': 39.42,
                    'ao': 48.22,
                    'atr': 60.30
                },
                'interpretation': 'Neutral MACD and RSI - Technical Equilibrium ⚖️ (Momentum Consolidation)'
            },
            'volume': {
                'score': 35.05,
                'components': {
                    'adl': 64.88,
                    'cmf': 49.94,
                    'vwap': 49.58
                },
                'interpretation': 'Neutral Volume Trend - Balanced Trading Flow ↔️ (Consolidation Phase)'
            },
            'orderbook': {
                'score': 52.78,
                'components': {
                    'spread': 100.00,
                    'liquidity': 95.21,
                    'depth': 89.65
                },
                'interpretation': 'Tight Spread with Balanced Orders - High Market Efficiency ⚖️ (Liquid Trading Range)'
            },
            'orderflow': {
                'score': 17.17,
                'components': {
                    'open_interest_score': 70.41,
                    'trade_flow_score': 30.32,
                    'cvd': 3.26
                },
                'interpretation': 'Balanced Cumulative Volume Delta - Equilibrium Between Buying and Selling Forces ⚖️ (Range Trading)'
            },
            'sentiment': {
                'score': 51.61,
                'components': {
                    'market_mood': 56.43,
                    'sentiment': 51.61,
                    'long_short_ratio': 50.00
                },
                'interpretation': {
                    'signal': 'neutral',
                    'bias': 'neutral',
                    'risk_level': 'unfavorable',
                    'summary': 'Market sentiment is neutral with unfavorable risk conditions'
                }
            },
            'price_structure': {
                'score': 50.53,
                'components': {
                    'vwap': 60.31,
                    'order_block': 57.51,
                    'composite_value': 49.56
                },
                'signals': {
                    'support_resistance': {'value': 48.55, 'signal': 'weak_level'},
                    'trend': {'value': 60.31, 'signal': 'uptrend'},
                    'structure': {'value': 44.00, 'signal': 'neutral'}
                }
            }
        },
        'reliability': 1.0,
        'alert_style': 'risk_management'
    }

async def test_alert_formatting():
    """Test the formatting of alerts."""
    # Load config
    config = load_config()
    
    # Initialize AlertManager
    logger.info("Initializing AlertManager...")
    alert_manager = AlertManager(config)
    
    # Test 1: Format a sell signal with the risk management template
    logger.info("\nTest 1: Formatting a sell signal with the risk management template")
    test_signal = create_test_signal()
    
    # First, verify that the risk_management format works
    message = alert_manager._format_risk_management_alert(test_signal)
    logger.info(f"\nRisk Management Format:\n{message}\n")
    
    # Test 2: Send an actual alert
    logger.info("\nTest 2: Sending an actual alert")
    success = await alert_manager.send_signal_alert(test_signal)
    logger.info(f"Alert sent successfully: {success}")
    
    # Test 3: Format a buy signal with the risk management template
    logger.info("\nTest 3: Formatting a buy signal with the risk management template")
    buy_signal = create_test_signal()
    buy_signal['signal'] = 'buy'
    buy_signal['score'] = 72.5
    buy_signal['confluence_score'] = 72.5
    buy_signal['components']['volume'] = 85.5
    buy_signal['components']['orderflow'] = 68.2
    buy_signal['components']['technical'] = 75.3
    
    # Make sure we have interpretations
    buy_signal['interpretations'] = {
        'volume': 'Strong buying volume with increasing participation',
        'orderbook': 'Bullish order imbalance with strong support levels',
        'orderflow': 'Positive cumulative delta with institutional buying',
        'technical': 'Bullish momentum with positive RSI and MACD',
        'price_structure': 'Bullish structure with strong support',
        'sentiment': 'Optimistic market sentiment with favorable funding'
    }
    
    # Send the buy signal
    success = await alert_manager.send_signal_alert(buy_signal)
    logger.info(f"Buy alert sent successfully: {success}")
    
    logger.info("\nAll alert formatting tests completed successfully!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_alert_formatting()) 