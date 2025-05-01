#!/usr/bin/env python3
"""
Test script to verify PDF generation and attachment with signals.

This script creates a sample trading signal and processes it through
the SignalGenerator to verify PDF generation and attachment functionality.
"""

import os
import sys
import asyncio
import logging
import json
import yaml
import time
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import required components
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator
from src.core.reporting.report_manager import ReportManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml file."""
    try:
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            logger.error(f"Configuration file not found at {config_path}")
            sys.exit(1)
            
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            
        # Add Discord webhook from environment
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if not discord_webhook:
            logger.error("DISCORD_WEBHOOK_URL environment variable not set.")
            sys.exit(1)
            
        if 'monitoring' not in config:
            config['monitoring'] = {}
        if 'alerts' not in config['monitoring']:
            config['monitoring']['alerts'] = {}
        
        config['monitoring']['alerts']['discord'] = {
            'webhook_url': discord_webhook
        }
        
        # Ensure reporting is enabled
        if 'reporting' not in config:
            config['reporting'] = {
                'enabled': True,
                'attach_pdf': True,
                'template_dir': 'templates',
                'base_dir': 'reports'
            }
        else:
            config['reporting']['enabled'] = True
            config['reporting']['attach_pdf'] = True
            
        logger.info("Configuration loaded successfully")
        return config
    
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

def create_sample_signal() -> Dict[str, Any]:
    """Create a sample trading signal for testing."""
    try:
        # Set the symbol
        symbol = "BTCUSDT"
        
        # Set the current price (or fetch from exchange in a real scenario)
        current_price = 65000.0
        
        # Create component scores
        components = {
            'technical': 70.0,    # Technical indicators
            'volume': 65.0,       # Volume analysis
            'orderbook': 60.0,    # Orderbook analysis
            'orderflow': 75.0,    # Order flow
            'sentiment': 80.0,    # Market sentiment
            'price_structure': 68.0  # Price structure
        }
        
        # Calculate the overall confluence score (weighted average)
        weights = {
            'technical': 0.17,
            'volume': 0.12,
            'orderbook': 0.2,
            'orderflow': 0.25,
            'sentiment': 0.1,
            'price_structure': 0.15
        }
        
        score = sum(components[key] * weights[key] for key in components)
        
        # Create interpretations for each component
        interpretations = {
            'technical': {
                'score': components['technical'],
                'interpretation': "Technical indicators showing bullish momentum with RSI at 68 and positive MACD."
            },
            'volume': {
                'score': components['volume'],
                'interpretation': "Volume analysis indicates accumulation pattern over the last 3 days."
            },
            'orderbook': {
                'score': components['orderbook'],
                'interpretation': "Orderbook depth showing stronger support than resistance levels."
            },
            'orderflow': {
                'score': components['orderflow'],
                'interpretation': "Order flow ratio at 1.35 (buy/sell) indicating strong buying pressure."
            },
            'sentiment': {
                'score': components['sentiment'],
                'interpretation': "Very positive market sentiment with bullish funding rates."
            },
            'price_structure': {
                'score': components['price_structure'],
                'interpretation': f"Price ${current_price} above all major moving averages with clear uptrend."
            }
        }
        
        # Create detailed results for PDF report
        results = {
            'price': current_price,
            '24h_high': current_price * 1.02,
            '24h_low': current_price * 0.98,
            '24h_volume': 7500000000,  # 7.5B
            'open_interest': 52000,
            'funding_rate': 0.00004124,
            'volume_ratio': 1.35,
            'volatility': 0.025,
            'rsi': 68,
            'macd': {
                'macd': 45.2,
                'signal': 42.8,
                'histogram': 2.4
            },
            'moving_averages': {
                'ma_20': current_price * 0.97,
                'ma_50': current_price * 0.95,
                'ma_100': current_price * 0.92,
                'ma_200': current_price * 0.88
            },
            'technical': interpretations['technical'],
            'volume': interpretations['volume'],
            'orderbook': interpretations['orderbook'],
            'orderflow': interpretations['orderflow'],
            'sentiment': interpretations['sentiment'],
            'price_structure': interpretations['price_structure']
        }
        
        # Create signal data
        signal_data = {
            'symbol': symbol,
            'score': score,
            'signal': 'BUY' if score >= 60 else ('SELL' if score <= 40 else 'NEUTRAL'),
            'strength': 'Strong' if abs(score - 50) > 20 else 'Moderate',
            'timestamp': int(time.time() * 1000),  # Current time in milliseconds
            'price': current_price,
            'components': components,
            'results': results,
            'buy_threshold': 60.0,
            'sell_threshold': 40.0,
            'reliability': 85.0,
            'metadata': {
                'exchange': 'bybit',
                'timeframe': '1h',
                'market_type': 'futures'
            },
            'targets': {
                'entry': current_price,
                'stop_loss': current_price * 0.95,
                'take_profit_1': current_price * 1.05,
                'take_profit_2': current_price * 1.08,
                'take_profit_3': current_price * 1.12,
            }
        }
        
        logger.info(f"Created sample {signal_data['signal']} signal for {symbol} with score {score:.2f}")
        return signal_data
    
    except Exception as e:
        logger.error(f"Error creating sample signal: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def create_sample_ohlcv() -> pd.DataFrame:
    """Create sample OHLCV data for the test."""
    try:
        # Create a datetime index
        now = pd.Timestamp.now()
        dates = pd.date_range(end=now, periods=50, freq='1H')
        
        # Generate random price data with an uptrend
        np.random.seed(42)  # For reproducibility
        
        # Start price and trend
        start_price = 63000
        end_price = 65000
        
        # Generate linear trend from start to end
        price_range = end_price - start_price
        linear_trend = np.linspace(0, price_range, len(dates))
        
        # Add random noise to the trend
        noise = np.random.normal(0, price_range * 0.02, len(dates))
        close_prices = start_price + linear_trend + noise
        
        # Generate other OHLCV data
        typical_spread = price_range * 0.01  # 1% typical candle size
        
        # Calculate high, low, open based on close
        high_prices = close_prices + np.random.uniform(0, typical_spread, len(dates))
        low_prices = close_prices - np.random.uniform(0, typical_spread, len(dates))
        
        # Ensure high >= close >= low
        high_prices = np.maximum(high_prices, close_prices)
        low_prices = np.minimum(low_prices, close_prices)
        
        # Open prices random between previous close and current low/high
        open_prices = np.zeros_like(close_prices)
        open_prices[0] = start_price * 0.9999  # First open
        for i in range(1, len(dates)):
            prev_close = close_prices[i-1]
            curr_high = high_prices[i]
            curr_low = low_prices[i]
            # Open between prev close and current high/low
            if prev_close < curr_low:
                open_prices[i] = np.random.uniform(prev_close, curr_low)
            elif prev_close > curr_high:
                open_prices[i] = np.random.uniform(curr_high, prev_close)
            else:
                open_prices[i] = np.random.uniform(curr_low, curr_high)
        
        # Volume with some random spikes
        base_volume = 1000
        volume = np.random.exponential(base_volume, len(dates))
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })
        
        logger.info(f"Created sample OHLCV data with {len(df)} candles")
        return df
    
    except Exception as e:
        logger.error(f"Error creating sample OHLCV data: {str(e)}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

async def patch_processor_fetch_ohlcv(signal_generator):
    """Patch the _fetch_ohlcv_data method to return our sample data."""
    try:
        # Create sample OHLCV data
        ohlcv_data = create_sample_ohlcv()
        
        # Store the original method for reference
        original_fetch_ohlcv = signal_generator._fetch_ohlcv_data
        
        # Define the patched method
        async def patched_fetch_ohlcv(symbol, timeframe='1h', limit=50):
            logger.info(f"Using patched _fetch_ohlcv_data method for {symbol}")
            return ohlcv_data
        
        # Replace the method with our patched version
        signal_generator._fetch_ohlcv_data = patched_fetch_ohlcv
        
        logger.info("Patched _fetch_ohlcv_data method successfully")
    except Exception as e:
        logger.error(f"Error patching _fetch_ohlcv_data method: {str(e)}")
        logger.error(traceback.format_exc())

async def main():
    """Main function to run the test."""
    try:
        logger.info("Starting test of signal generation with PDF attachment")
        
        # Load configuration
        config = load_config()
        
        # Initialize AlertManager
        alert_manager = AlertManager(config)
        logger.info("Initialized AlertManager")
        
        # Initialize handlers
        alert_manager.register_handler('discord')
        logger.info("Registered Discord handler")
        
        # Initialize SignalGenerator
        signal_generator = SignalGenerator(config, alert_manager)
        logger.info("Initialized SignalGenerator")
        
        # Patch the _fetch_ohlcv_data method to return our sample data
        await patch_processor_fetch_ohlcv(signal_generator)
        
        # Create sample signal
        signal_data = create_sample_signal()
        
        # Process the signal
        logger.info("Processing signal...")
        await signal_generator.process_signal(signal_data)
        
        logger.info("Signal processed. Check Discord for the alert with PDF attachment.")
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    # Run the main function
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 