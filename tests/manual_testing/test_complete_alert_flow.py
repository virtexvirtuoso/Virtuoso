#!/usr/bin/env python3
"""Comprehensive test to verify the complete alert system with a specific confidence score."""

import os
import sys
import asyncio
import logging
import time
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.manager import ConfigManager
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("CompleteAlertTest")

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

def create_detailed_test_signal(symbol: str, score: float = 71.0) -> Dict[str, Any]:
    """Create a detailed test signal with rich component data.
    
    Args:
        symbol: Trading symbol to use
        score: Confluence score (default: 71.0)
        
    Returns:
        A detailed signal dictionary with all needed components
    """
    # Calculate component scores that result in the target confluence score
    # For a 71 score, we want some high scores and some medium scores
    components = {
        'volume': 83.7,
        'orderbook': 77.2,
        'orderflow': 68.1,
        'technical': 72.5,
        'price_structure': 65.8,
        'sentiment': 62.4
    }
    
    # Create detailed results with realistic interpretations
    results = {}
    
    # Volume results
    results['volume'] = {
        'score': components['volume'],
        'components': {
            'volume_delta': 82.3,
            'adl': 85.4,
            'cmf': 79.8,
            'relative_volume': 1.87,
            'obv': 80.1,
            'vwap': 76.2
        },
        'signals': {
            'volume_sma': {'value': 65.4, 'signal': 'high'},
            'volume_trend': {'value': 80.2, 'signal': 'increasing'},
            'volume_profile': {'value': 85.3, 'signal': 'bullish'}
        },
        'interpretation': 'Strong Rising Volume With Buying Momentum - Significant Accumulation 🚀 (Strong Bull Trend)'
    }
    
    # Orderbook results
    results['orderbook'] = {
        'score': components['orderbook'],
        'components': {
            'imbalance': 85.3,
            'depth': 81.2,
            'liquidity': 75.6,
            'spread': 65.3,
            'absorption': 72.8
        },
        'interpretation': 'Strong Buy-Side Imbalance - Deep Support Structure Forming 📈 (Uptrend Confirmation)'
    }
    
    # Orderflow results
    results['orderflow'] = {
        'score': components['orderflow'],
        'components': {
            'cvd': 72.4,
            'trade_flow_score': 65.3,
            'open_interest_score': 68.7
        },
        'signals': {
            'score': components['orderflow'],
            'interpretation': {
                'message': 'Strong bullish orderflow',
                'signal': 'strong_buy'
            }
        },
        'interpretation': 'Positive Cumulative Delta - Consistent Buying Pressure 📈 (Uptrend Continuation)'
    }
    
    # Technical results
    results['technical'] = {
        'score': components['technical'],
        'components': {
            'rsi': 68.2,
            'macd': 75.3,
            'ao': 71.2,
            'williams_r': 81.4,
            'atr': 65.7,
            'cci': 73.2
        },
        'signals': {
            'trend': 'bullish',
            'strength': 0.72
        },
        'interpretation': 'Bullish Momentum Breakout - Strong Technical Confirmation 💹 (Trend Acceleration)'
    }
    
    # Price structure results
    results['price_structure'] = {
        'score': components['price_structure'],
        'components': {
            'support_resistance': 63.2,
            'order_block': 68.5,
            'vwap': 71.3,
            'market_structure': 65.2,
            'composite_value': 60.8 
        },
        'signals': {
            'support_resistance': {'value': 63.2, 'signal': 'strong_level'},
            'trend': {'value': 71.3, 'signal': 'uptrend'},
            'structure': {'value': 65.2, 'signal': 'bullish'}
        },
        'interpretation': 'Strong Support Base With Higher Lows - Established Uptrend 📈 (Healthy Structure)'
    }
    
    # Sentiment results 
    results['sentiment'] = {
        'score': components['sentiment'],
        'components': {
            'funding_rate': 58.3,
            'long_short_ratio': 65.2,
            'market_mood': 67.8,
            'sentiment': 62.4
        },
        'interpretation': {
            'signal': 'bullish',
            'bias': 'optimistic',
            'risk_level': 'moderate',
            'summary': 'Optimistic market sentiment with favorable positioning ratio'
        }
    }
    
    # Create a signal
    signal = {
        'symbol': symbol,
        'signal': 'BUY',
        'score': score,
        'confluence_score': score,
        'price': 50000.0,  # Set a reasonable test price
        'timestamp': int(time.time() * 1000),
        'components': components,
        'results': results,
        'reliability': 0.95
    }
    
    # Create interpretations
    interpretations = {}
    for component_name, component_data in results.items():
        if 'interpretation' in component_data:
            interp = component_data['interpretation']
            if isinstance(interp, dict) and 'summary' in interp:
                interpretations[component_name] = interp['summary']
            elif isinstance(interp, str):
                interpretations[component_name] = interp
    
    signal['interpretations'] = interpretations
    
    return signal

async def test_complete_alert_flow():
    """Test the complete alert flow with a specific confidence score."""
    # Load config
    config = load_config()
    
    # Make sure to load environment variables
    load_dotenv()
    
    # Check for Discord webhook URL
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        logger.info("Found Discord webhook URL in environment variables")
        # Add it to config to ensure AlertManager picks it up during initialization
        if 'monitoring' not in config:
            config['monitoring'] = {}
        if 'alerts' not in config['monitoring']:
            config['monitoring']['alerts'] = {}
        config['monitoring']['alerts']['discord_webhook'] = discord_webhook
    else:
        logger.warning("No Discord webhook URL found in environment variables")
    
    # Initialize components
    logger.info("Initializing AlertManager and SignalGenerator...")
    alert_manager = AlertManager(config)
    
    try:
        # Ensure Discord webhook is configured
        if not alert_manager.discord_webhook_url:
            logger.warning("No Discord webhook found in config, checking environment variable again...")
            if discord_webhook:
                alert_manager.discord_webhook_url = discord_webhook
                logger.info("Discord webhook set from environment variable")
            else:
                logger.error("No Discord webhook URL found in config or environment. Alerts won't be delivered.")
                print("\n⚠️ WARNING: No Discord webhook configured. Test will run but alerts won't be sent!")
                print("Please set the DISCORD_WEBHOOK_URL environment variable and try again.")
        else:
            logger.info(f"Discord webhook URL is configured: {alert_manager.discord_webhook_url[:15]}...{alert_manager.discord_webhook_url[-10:]}")
        
        # Register Discord handler explicitly
        if alert_manager.discord_webhook_url:
            logger.info("Registering Discord handler...")
            alert_manager.register_discord_handler()
            logger.info(f"Handlers after registration: {alert_manager.handlers}")
            logger.info(f"Alert handlers dictionary: {list(alert_manager.alert_handlers.keys())}")
        
        # Initialize signal generator with alert manager
        signal_generator = SignalGenerator(config, alert_manager)
        
        # Step 1: Create a detailed test signal with a confidence score of 71
        logger.info("\nStep 1: Creating a detailed BUY signal with confidence score of 71...")
        test_signal = create_detailed_test_signal("BTCUSDT", 71.0)
        logger.info(f"Created detailed test signal for {test_signal['symbol']} with score {test_signal['score']}")
        
        # Log the components and their scores
        logger.info("Signal components:")
        for component, score in test_signal['components'].items():
            logger.info(f"  - {component}: {score:.1f}")
        
        # Step 2: Process through signal generator
        logger.info("\nStep 2: Processing signal through SignalGenerator...")
        # Ensure the signal generator has proper thresholds
        signal_generator.thresholds = {'buy': 60.0, 'sell': 40.0}
        
        # Process the signal
        await signal_generator.process_signal(test_signal)
        logger.info("Signal processed through SignalGenerator")
        
        # Wait for alerts
        logger.info("Waiting for alerts to be processed...")
        await asyncio.sleep(1)
        
        # Step 3: Process directly through alert manager
        logger.info("\nStep 3: Processing signal directly through AlertManager...")
        
        # Create a slightly different signal to test formatting consistency
        direct_signal = create_detailed_test_signal("ETHUSDT", 71.0)
        
        # Process through AlertManager
        await alert_manager.process_signal(direct_signal)
        logger.info("Signal processed through AlertManager")
        
        # Wait for alerts
        logger.info("Waiting for alerts to be processed...")
        await asyncio.sleep(1)
        
        # Step 4: Test send_signal_alert directly
        logger.info("\nStep 4: Testing send_signal_alert directly...")
        
        direct_alert_signal = create_detailed_test_signal("SOLUSDT", 71.0)
        success = await alert_manager.send_signal_alert(direct_alert_signal)
        logger.info(f"Direct signal_alert call success: {success}")
        
        # Wait for alerts
        logger.info("Waiting for alerts to be processed...")
        await asyncio.sleep(1)
        
        # Step 5: Test send_confluence_alert directly 
        logger.info("\nStep 5: Testing send_confluence_alert directly...")
        
        await alert_manager.send_confluence_alert(
            symbol="DOGEUSDT",
            confluence_score=71.0,
            components=test_signal['components'],
            results=test_signal['results'],
            reliability=0.95
        )
        logger.info("Confluence alert sent directly")
        
        # Wait for alerts
        logger.info("Waiting for alerts to be processed...")
        await asyncio.sleep(1)
        
        # Step 6: Test deduplication
        logger.info("\nStep 6: Testing deduplication with identical signal...")
        
        # Try reusing the original signal
        duplicate_success = await alert_manager.send_signal_alert(test_signal)
        logger.info(f"Attempted to send duplicate signal, success: {duplicate_success} (should be False)")
        
        # Step 7: Test with a different score but same symbol
        logger.info("\nStep 7: Testing with different score but same symbol...")
        
        # Create signal with different score
        different_score_signal = create_detailed_test_signal("BTCUSDT", 75.0)
        await alert_manager.send_signal_alert(different_score_signal)
        logger.info("Signal with different score for same symbol processed")
        
        # Wait for final processing
        logger.info("\nAll tests completed! Check the Discord output for the formatted alerts.")
        
        # Output completion message with instructions
        print("\n" + "="*80)
        print("Complete Alert Flow Test Finished!")
        print("="*80)
        print("Please check your Discord channel for the following alerts:")
        print("1. BTCUSDT BUY signal with score 71.0 (through SignalGenerator)")
        print("2. ETHUSDT BUY signal with score 71.0 (through AlertManager)")
        print("3. SOLUSDT BUY signal with score 71.0 (through send_signal_alert)")
        print("4. DOGEUSDT BUY signal with score 71.0 (through send_confluence_alert)")
        print("5. BTCUSDT BUY signal with score 75.0 (same symbol, different score)")
        print("\nThe duplicate BTCUSDT signal with score 71.0 should have been deduplicated.")
        print("="*80)
        
        # Final messages to Discord to mark the end of the test
        if alert_manager.discord_webhook_url:
            try:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                final_message = {
                    "content": f"✅ **Test completed at {current_time}**\n\nThe test successfully completed. Check the alerts above for proper formatting and deduplication."
                }
                
                # Send directly to Discord webhook
                if not alert_manager._client_session or alert_manager._client_session.closed:
                    alert_manager._client_session = aiohttp.ClientSession()
                    logger.info("Created new client session for final message")
                
                # Send the message
                async with alert_manager._client_session.post(
                    alert_manager.discord_webhook_url,
                    json=final_message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status not in (200, 204):
                        response_text = await response.text()
                        logger.error(f"Failed to send final message: {response.status} - {response_text}")
                    else:
                        logger.info("Sent final test completion message to Discord")
            except Exception as e:
                logger.error(f"Error sending final message: {str(e)}")
    
    finally:
        # Clean up resources - close aiohttp client session to prevent warnings
        logger.info("Cleaning up resources...")
        if hasattr(alert_manager, '_client_session') and alert_manager._client_session:
            if not alert_manager._client_session.closed:
                logger.info("Closing aiohttp client session...")
                await alert_manager._client_session.close()
                logger.info("Client session closed.")
            else:
                logger.info("Client session already closed.")
        else:
            logger.info("No client session to close.")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_complete_alert_flow()) 