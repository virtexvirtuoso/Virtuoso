#!/usr/bin/env python
"""
Test module for generating a confluence signal alert with real Bybit data.

This test loads real market data collected from Bybit API and processes it
through the signal generation and alert system.
"""

import os
import sys
import asyncio
import logging
import json
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.utils.serializers import serialize_for_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_bybit_signal')

def load_config() -> dict:
    """Load configuration from YAML file."""
    try:
        # Try loading from config/config.yaml first
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            # Fallback to src/config/config.yaml
            config_path = Path("src/config/config.yaml")
            
        if not config_path.exists():
            raise FileNotFoundError("Config file not found in config/ or src/config/")
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def load_bybit_data() -> Dict[str, Any]:
    """Load Bybit data from JSON files."""
    data_dir = os.path.join(os.getcwd(), 'data', 'test', 'bybit')
    
    data = {}
    
    # Load kline (OHLCV) data
    try:
        with open(os.path.join(data_dir, 'kline_data.json'), 'r') as f:
            data['kline'] = json.load(f)
            logger.info(f"Loaded {len(data['kline']['result']['list'])} kline records")
    except Exception as e:
        logger.error(f"Error loading kline data: {str(e)}")
        data['kline'] = None
    
    # Load orderbook data
    try:
        with open(os.path.join(data_dir, 'orderbook_data.json'), 'r') as f:
            data['orderbook'] = json.load(f)
            logger.info(f"Loaded orderbook with {len(data['orderbook']['result']['a'])} asks and {len(data['orderbook']['result']['b'])} bids")
    except Exception as e:
        logger.error(f"Error loading orderbook data: {str(e)}")
        data['orderbook'] = None
    
    # Load ticker data
    try:
        with open(os.path.join(data_dir, 'ticker_data.json'), 'r') as f:
            data['ticker'] = json.load(f)
            logger.info(f"Loaded ticker data for {data['ticker']['result']['list'][0]['symbol']}")
    except Exception as e:
        logger.error(f"Error loading ticker data: {str(e)}")
        data['ticker'] = None
    
    # Load trades data
    try:
        with open(os.path.join(data_dir, 'trades_data.json'), 'r') as f:
            data['trades'] = json.load(f)
            logger.info(f"Loaded {len(data['trades']['result']['list'])} trade records")
    except Exception as e:
        logger.error(f"Error loading trades data: {str(e)}")
        data['trades'] = None
    
    return data

def prepare_signal_data(bybit_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Bybit data into signal data format."""
    # Extract current price from ticker
    ticker = bybit_data['ticker']['result']['list'][0]
    current_price = float(ticker['lastPrice'])
    
    # Extract OHLCV data
    klines = bybit_data['kline']['result']['list']
    
    # Calculate some basic technical indicators
    # Using simple moving averages for demonstration
    closes = [float(k[4]) for k in klines]  # Close prices
    volumes = [float(k[6]) for k in klines]  # Volume values
    
    # Simple 20-period moving average
    ma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
    # Simple 50-period moving average
    ma_50 = sum(closes[:50]) / 50 if len(closes) >= 50 else sum(closes) / len(closes)
    
    # Calculate relative strength between current price and moving averages
    ma_20_strength = (current_price / ma_20 - 1) * 100
    ma_50_strength = (current_price / ma_50 - 1) * 100
    
    # Calculate average volume and recent volume
    avg_volume = sum(volumes[:20]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    recent_volume = sum(volumes[:5]) / 5 if len(volumes) >= 5 else sum(volumes) / len(volumes)
    vol_change = (recent_volume / avg_volume - 1) * 100
    
    # Extract orderbook data
    orderbook = bybit_data['orderbook']['result']
    asks = [[float(price), float(size)] for price, size in orderbook['a']]
    bids = [[float(price), float(size)] for price, size in orderbook['b']]
    
    # Calculate orderbook imbalance
    ask_value = sum(price * size for price, size in asks[:10])
    bid_value = sum(price * size for price, size in bids[:10])
    imbalance = (bid_value - ask_value) / (bid_value + ask_value) * 100
    
    # Recent trades analysis
    trades = bybit_data['trades']['result']['list']
    buy_trades = [t for t in trades if t['side'] == 'Buy']
    sell_trades = [t for t in trades if t['side'] == 'Sell']
    
    buy_volume = sum(float(t['size']) for t in buy_trades)
    sell_volume = sum(float(t['size']) for t in sell_trades)
    
    trade_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume) * 100 if (buy_volume + sell_volume) > 0 else 0
    
    # Create component scores based on the analysis
    # These are simplified for demonstration
    technical_score = 50 + (ma_20_strength + ma_50_strength) / 2
    volume_score = 50 + vol_change / 2
    orderbook_score = 50 + imbalance
    orderflow_score = 50 + trade_imbalance
    
    # Clip scores to 0-100 range
    technical_score = max(0, min(100, technical_score))
    volume_score = max(0, min(100, volume_score))
    orderbook_score = max(0, min(100, orderbook_score))
    orderflow_score = max(0, min(100, orderflow_score))
    
    # Generate a price structure score based on recent price action
    price_structure_score = 55.0  # Neutral with slight bullish bias
    
    # Generate sentiment score
    sentiment_score = 60.0  # Slightly bullish
    
    # Calculate overall confluence score as weighted average
    components = {
        'technical': technical_score,
        'volume': volume_score,
        'orderbook': orderbook_score,
        'orderflow': orderflow_score,
        'price_structure': price_structure_score,
        'sentiment': sentiment_score
    }
    
    # Weights - adjust as needed
    weights = {
        'technical': 0.25,
        'volume': 0.15,
        'orderbook': 0.20,
        'orderflow': 0.20,
        'price_structure': 0.10,
        'sentiment': 0.10
    }
    
    # Calculate weighted score
    weighted_score = sum(score * weights.get(comp, 0.0) for comp, score in components.items())
    
    # Create detailed results for each component
    results = {
        'technical': {
            'score': technical_score,
            'components': {
                'ma_20': 50 + ma_20_strength,
                'ma_50': 50 + ma_50_strength,
                'trend': 55.0
            },
            'interpretation': f"{'Bullish' if technical_score > 60 else 'Bearish' if technical_score < 40 else 'Neutral'} technical indicators with MA20 at {ma_20:.2f} and MA50 at {ma_50:.2f}"
        },
        'volume': {
            'score': volume_score,
            'components': {
                'volume_change': 50 + vol_change,
                'relative_volume': 55.0,
                'volume_trend': 52.0
            },
            'interpretation': f"Volume is {vol_change:.1f}% {'higher' if vol_change > 0 else 'lower'} than average"
        },
        'orderbook': {
            'score': orderbook_score,
            'components': {
                'imbalance': 50 + imbalance,
                'depth': 52.0,
                'resistance': 48.0
            },
            'interpretation': f"Orderbook shows {'buying' if imbalance > 0 else 'selling'} pressure with {abs(imbalance):.1f}% imbalance"
        },
        'orderflow': {
            'score': orderflow_score,
            'components': {
                'trade_imbalance': 50 + trade_imbalance,
                'large_trades': 53.0,
                'pressure': 51.0
            },
            'interpretation': f"Recent trades show {'more buying' if trade_imbalance > 0 else 'more selling'} with {abs(trade_imbalance):.1f}% imbalance"
        },
        'price_structure': {
            'score': price_structure_score,
            'components': {
                'support_resistance': 54.0,
                'patterns': 56.0,
                'volatility': 52.0
            },
            'interpretation': "Price structure showing moderate bullish bias"
        },
        'sentiment': {
            'score': sentiment_score,
            'components': {
                'market_sentiment': 58.0,
                'fear_greed': 62.0,
                'social_media': 60.0
            },
            'interpretation': "Market sentiment slightly bullish with positive social indicators"
        }
    }
    
    # Create the signal data structure
    signal_data = {
        'symbol': 'BTCUSDT',
        'confluence_score': weighted_score,
        'timestamp': int(time.time() * 1000),
        'reliability': 0.85,  # High reliability since we're using real data
        'price': current_price,
        'components': components,
        'weights': weights,
        'results': results
    }
    
    return signal_data

async def save_signal_data(signal_data: Dict[str, Any], filename: str = None) -> str:
    """Save signal data to a JSON file for inspection."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"bybit_signal_{timestamp}.json"
        
    # Create exports directory if it doesn't exist
    exports_dir = os.path.join(os.getcwd(), 'exports', 'signal_data')
    os.makedirs(exports_dir, exist_ok=True)
    
    # Create filepath
    filepath = os.path.join(exports_dir, filename)
    
    # Use serializer to prepare data for JSON
    json_ready_data = serialize_for_json(signal_data)
    
    # Write to file with pretty formatting
    with open(filepath, 'w') as f:
        json.dump(json_ready_data, f, indent=2, default=str)
    
    logger.info(f"Saved signal data to {filepath}")
    return filepath

async def test_bybit_signal():
    """Test generating a signal from real Bybit data."""
    # Load config 
    config = load_config()
    
    # Step 1: Initialize components
    logger.info("\nStep 1: Initializing components...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Step 2: Load real Bybit data
    logger.info("\nStep 2: Loading Bybit market data...")
    bybit_data = load_bybit_data()
    
    # Step 3: Prepare signal data from Bybit data
    logger.info("\nStep 3: Converting market data to signal format...")
    signal_data = prepare_signal_data(bybit_data)
    logger.info(f"Created signal for {signal_data['symbol']} with score {signal_data['confluence_score']:.2f}")
    
    # Log reliability value explicitly
    reliability = signal_data.get('reliability', 0)
    logger.info(f"Signal reliability value: {reliability} (should display as {int(reliability*100)}%)")
    
    # Save original signal data
    original_filepath = await save_signal_data(signal_data, 'bybit_original_signal.json')
    logger.info(f"Saved original signal data to {original_filepath}")
    
    # Step 4: Process signal and generate alert
    logger.info("\nStep 4: Processing signal...")
    
    # Set thresholds (adjust as needed)
    signal_generator.thresholds = {'buy': 60.0, 'sell': 40.0}
    
    # Process the signal
    await signal_generator.process_signal(signal_data)
    logger.info("Signal processed through SignalGenerator")
    
    # Wait for a moment to let processing complete
    await asyncio.sleep(2)
    
    logger.info("\nTest completed!")

if __name__ == "__main__":
    logger.info("Starting Bybit signal alert test...")
    asyncio.run(test_bybit_signal()) 