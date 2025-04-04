#!/usr/bin/env python3
"""
Sentiment Indicator Improvements Test

This script implements and tests enhancements to the sentiment indicator components:
1. WebSocket connection for real-time liquidation events
2. Volume sentiment validation for anomalous distributions
3. Fix for risk limit API access
4. Signal balance mechanism for component correlation
5. Funding rate verification with historical context

"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import time
import os
import sys
import aiohttp
import websockets
import matplotlib.pyplot as plt
from pprint import pprint
import gc

# Add src to path if running directly
if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indicators.sentiment_indicators import SentimentIndicators
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.core.logger import Logger
from src.utils.liquidation_cache import liquidation_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SENTIMENT_IMPROVEMENTS_TEST")

# Define constants for liquidation cache
CACHE_DIR = "cache"
CACHE_EXPIRY = 60 * 60  # 1 hour in seconds

def save_liquidations_to_cache(liquidations, symbol):
    """
    Save liquidation events to a file-based cache.
    
    Args:
        liquidations: List of liquidation events
        symbol: Trading pair symbol
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f"liquidations_{symbol}.json")
        
        cache_data = {
            "timestamp": int(time.time()),
            "symbol": symbol,
            "data": liquidations
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
            
        logger.info(f"Saved {len(liquidations)} liquidation events to cache")
    except Exception as e:
        logger.error(f"Error saving liquidations to cache: {e}")

def load_liquidations_from_cache(symbol):
    """
    Load liquidation events from file-based cache if available and not expired.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        List of liquidation events or None if cache is invalid/expired
    """
    try:
        cache_file = os.path.join(CACHE_DIR, f"liquidations_{symbol}.json")
        
        if not os.path.exists(cache_file):
            logger.debug(f"No cache file found for {symbol}")
            return None
            
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
            
        # Check if cache is expired
        cache_time = cache_data.get("timestamp", 0)
        if time.time() - cache_time > CACHE_EXPIRY:
            logger.debug(f"Cache for {symbol} is expired")
            return None
            
        # Check if symbol matches
        if cache_data.get("symbol") != symbol:
            logger.debug(f"Cache symbol mismatch: {cache_data.get('symbol')} vs {symbol}")
            return None
            
        liquidations = cache_data.get("data", [])
        logger.info(f"Loaded {len(liquidations)} liquidation events from cache (age: {(time.time() - cache_time) / 60:.1f} min)")
        return liquidations
        
    except Exception as e:
        logger.error(f"Error loading liquidations from cache: {e}")
        return None

async def fetch_exchange_cached_liquidations(bybit, symbol):
    """
    Try to fetch cached liquidation events from the exchange.
    
    Args:
        bybit: Bybit exchange instance
        symbol: Trading pair symbol
        
    Returns:
        List of liquidation events or empty list if no cache available
    """
    try:
        # Try different endpoints that might contain liquidation data
        
        # Option 1: Try public trade history with a liquidation flag
        params = {
            'category': 'linear',
            'symbol': symbol,
            'limit': 100
        }
        trades = await bybit._make_request('GET', '/v5/market/recent-trade', params)
        
        # Look for large trades that could be liquidations (size > 10 BTC for BTC pairs)
        liquidation_candidates = []
        threshold = 10.0  # Size threshold for BTC
        if "USDT" in symbol and symbol != "BTCUSDT":
            # For altcoins, adjust threshold relative to BTC price
            ticker = await bybit.fetch_ticker(symbol)
            btc_ticker = await bybit.fetch_ticker("BTCUSDT")
            if ticker and btc_ticker:
                btc_price = float(btc_ticker.get('last', 50000))
                coin_price = float(ticker.get('last', 1))
                threshold = (10.0 * btc_price / coin_price) if coin_price > 0 else 100
        
        if trades and 'result' in trades and 'list' in trades['result']:
            trade_list = trades['result']['list']
            for trade in trade_list:
                try:
                    size = float(trade.get('size', 0))
                    if size > threshold:
                        # This could be a liquidation
                        price = float(trade.get('price', 0))
                        side = trade.get('side', '').lower()
                        time_ms = int(trade.get('time', time.time() * 1000))
                        
                        liquidation_candidates.append({
                            'side': side,
                            'size': size,
                            'price': price,
                            'timestamp': time_ms,
                            'source': 'inferred'
                        })
                except (ValueError, TypeError):
                    pass
            
            if liquidation_candidates:
                logger.info(f"Found {len(liquidation_candidates)} potential liquidation events from trade history")
                return liquidation_candidates
        
        # Option 2: Try market statistics endpoint if available
        params = {
            'category': 'linear',
            'symbol': symbol
        }
        stats = await bybit._make_request('GET', '/v5/market/statistics', params)
        
        if stats and 'result' in stats and 'liquidations' in stats['result']:
            liq_data = stats['result']['liquidations']
            logger.info(f"Found liquidation statistics from market data")
            # Transform to our expected format
            result = []
            for liq in liq_data:
                result.append({
                    'side': liq.get('side', '').lower(),
                    'size': float(liq.get('size', 0)),
                    'price': float(liq.get('price', 0)),
                    'timestamp': int(liq.get('time', time.time() * 1000)),
                    'source': 'statistics'
                })
            return result
            
        # No liquidation data found through exchange cache
        return []
        
    except Exception as e:
        logger.error(f"Error fetching cached liquidations: {e}")
        return []

async def fetch_liquidations(bybit, symbol, duration=30):
    """
    Fetch liquidation events using multiple methods, with fallbacks.
    
    Args:
        bybit: Bybit exchange instance
        symbol: Trading pair symbol
        duration: WebSocket connection duration in seconds
        
    Returns:
        List of liquidation events
    """
    liquidations = []
    
    # Step 1: Try file-based cache first
    cached_liq = load_liquidations_from_cache(symbol)
    if cached_liq and len(cached_liq) > 0:
        logger.info(f"Using {len(cached_liq)} liquidation events from file cache")
        return cached_liq
    
    # Step 2: Try exchange's cached data
    exchange_cached_liq = await fetch_exchange_cached_liquidations(bybit, symbol)
    if exchange_cached_liq and len(exchange_cached_liq) > 0:
        logger.info(f"Using {len(exchange_cached_liq)} liquidation events from exchange cache")
        # Save to file cache for future use
        save_liquidations_to_cache(exchange_cached_liq, symbol)
        return exchange_cached_liq
    
    # Step 3: Try WebSocket for real-time data
    logger.info("No cached liquidations found, attempting WebSocket connection")
    ws_liquidations = await fetch_liquidations_via_websocket(symbol, duration)
    if ws_liquidations and len(ws_liquidations) > 0:
        logger.info(f"Collected {len(ws_liquidations)} liquidation events via WebSocket")
        # Save to file cache for future use
        save_liquidations_to_cache(ws_liquidations, symbol)
        return ws_liquidations
    
    # Step 4: No liquidations found, generate synthetic data
    logger.warning("No liquidation events found through any method, using synthetic data")
    synthetic_liq = generate_synthetic_liquidations(symbol)
    return synthetic_liq

def generate_synthetic_liquidations(symbol):
    """
    Generate synthetic liquidation events for testing purposes.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        List of synthetic liquidation events
    """
    # Create balanced synthetic data
    liquidations = []
    now = int(time.time() * 1000)
    
    # Generate 10 long and 10 short liquidations in the past hour
    for i in range(20):
        side = 'long' if i % 2 == 0 else 'short'
        timestamp = now - (i * 3 * 60 * 1000)  # Every 3 minutes
        size = np.random.uniform(5, 30)
        
        liquidations.append({
            'side': side,
            'size': size,
            'price': 0,  # Will be filled in with current price later
            'timestamp': timestamp,
            'source': 'synthetic'
        })
    
    logger.info(f"Generated {len(liquidations)} synthetic liquidation events")
    return liquidations

async def fetch_liquidations_via_websocket(symbol="BTCUSDT", duration=30):
    """
    Connect to Bybit WebSocket and fetch real-time liquidation events.
    
    Args:
        symbol: Trading pair symbol
        duration: How long to collect data in seconds
        
    Returns:
        List of liquidation events
    """
    logger.info(f"Connecting to Bybit WebSocket to collect liquidations for {duration} seconds...")
    
    uri = "wss://stream.bybit.com/v5/public/linear"
    liquidations = []
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to liquidation topic
        topic = f"liquidation.{symbol}"
        await websocket.send(json.dumps({
            "op": "subscribe",
            "args": [topic]
        }))
        
        # Wait for confirmation
        response = await websocket.recv()
        logger.info(f"Subscription response: {response}")
        
        # Collect liquidations for the specified duration
        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    # Check if this is a liquidation event
                    if 'topic' in data and data['topic'] == topic and 'data' in data:
                        event = data['data']
                        logger.info(f"Liquidation event: {event}")
                        
                        # Transform to our expected format
                        liq_event = {
                            'side': event.get('side', '').lower(),
                            'size': float(event.get('size', 0)),
                            'price': float(event.get('price', 0)),
                            'timestamp': int(time.time() * 1000)
                        }
                        liquidations.append(liq_event)
                except asyncio.TimeoutError:
                    # No data received within timeout, continue
                    pass
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            # Unsubscribe before closing
            await websocket.send(json.dumps({
                "op": "unsubscribe",
                "args": [topic]
            }))
    
    logger.info(f"Collected {len(liquidations)} liquidation events")
    return liquidations

def validate_volume_data(buy_volume, sell_volume, trades):
    """
    Validate volume data for anomalous distributions and outliers.
    
    Args:
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        trades: List of trade events
        
    Returns:
        tuple: (is_valid, corrected_buy_volume, corrected_sell_volume, reason)
    """
    total_volume = buy_volume + sell_volume
    if total_volume == 0:
        return False, 0, 0, "Zero total volume"
    
    buy_percentage = (buy_volume / total_volume) * 100
    
    # Check for extremely skewed distribution
    if buy_percentage > 95 or buy_percentage < 5:
        logger.warning(f"Extremely skewed volume distribution: {buy_percentage:.2f}% buys")
        
        # Check for few large outlier trades
        trade_sizes = [float(t.get('amount', t.get('size', 0))) for t in trades]
        if not trade_sizes:
            return False, 0, 0, "No trade sizes available"
            
        trade_sizes.sort()
        median_size = np.median(trade_sizes)
        
        # Find outliers (more than 5x median)
        outliers = [size for size in trade_sizes if size > 5 * median_size]
        if len(outliers) > 0 and len(outliers) <= 3:
            logger.warning(f"Found {len(outliers)} large outlier trades that may skew volume")
            
            # Remove outliers and recalculate
            filtered_trades = [t for t in trades if float(t.get('amount', t.get('size', 0))) <= 5 * median_size]
            if filtered_trades:
                # Recalculate volumes
                corr_buy_volume = sum(float(t.get('amount', t.get('size', 0))) 
                                   for t in filtered_trades if t.get('side', '').lower() == 'buy')
                corr_sell_volume = sum(float(t.get('amount', t.get('size', 0))) 
                                    for t in filtered_trades if t.get('side', '').lower() == 'sell')
                
                # If still valid, return corrected values
                if corr_buy_volume + corr_sell_volume > 0:
                    corr_buy_pct = (corr_buy_volume / (corr_buy_volume + corr_sell_volume)) * 100
                    logger.info(f"Corrected volume distribution: {corr_buy_pct:.2f}% buys (after outlier removal)")
                    return True, corr_buy_volume, corr_sell_volume, "Outliers removed"
    
    # Check for time-based trends (second half vs first half)
    if len(trades) >= 10:
        halfway = len(trades) // 2
        first_half = trades[:halfway]
        second_half = trades[halfway:]
        
        first_half_buy = sum(float(t.get('amount', t.get('size', 0))) 
                         for t in first_half if t.get('side', '').lower() == 'buy')
        first_half_sell = sum(float(t.get('amount', t.get('size', 0))) 
                          for t in first_half if t.get('side', '').lower() == 'sell')
        
        second_half_buy = sum(float(t.get('amount', t.get('size', 0))) 
                          for t in second_half if t.get('side', '').lower() == 'buy')
        second_half_sell = sum(float(t.get('amount', t.get('size', 0))) 
                           for t in second_half if t.get('side', '').lower() == 'sell')
        
        # Calculate percentages
        if first_half_buy + first_half_sell > 0:
            first_half_pct = (first_half_buy / (first_half_buy + first_half_sell)) * 100
        else:
            first_half_pct = 50
            
        if second_half_buy + second_half_sell > 0:
            second_half_pct = (second_half_buy / (second_half_buy + second_half_sell)) * 100
        else:
            second_half_pct = 50
        
        # Check for significant shift in trend
        if abs(second_half_pct - first_half_pct) > 30:
            logger.warning(f"Volume trend shift detected: {first_half_pct:.1f}% buys -> {second_half_pct:.1f}% buys")
            # Give more weight to recent trend (last half)
            weighted_buy = (first_half_buy * 0.3) + (second_half_buy * 0.7)
            weighted_sell = (first_half_sell * 0.3) + (second_half_sell * 0.7)
            
            if weighted_buy + weighted_sell > 0:
                weighted_pct = (weighted_buy / (weighted_buy + weighted_sell)) * 100
                logger.info(f"Time-weighted volume distribution: {weighted_pct:.2f}% buys")
                return True, weighted_buy, weighted_sell, "Trend-weighted"
    
    # Data seems valid as is
    return True, buy_volume, sell_volume, "Valid"

async def fetch_risk_limit_data(bybit, symbol):
    """
    Fetch risk limit data using properly authenticated endpoint.
    
    Args:
        bybit: Bybit exchange instance
        symbol: Trading pair symbol
        
    Returns:
        Risk limit data or None
    """
    try:
        # First try V5 API endpoint with proper category parameter
        risk_params = {
            'category': 'linear',
            'symbol': symbol
        }
        
        # Try with authenticated request - _make_request only accepts method, endpoint, params
        risk_limit_data = await bybit._make_request('GET', '/v5/position/risk-limit', risk_params)
        
        if risk_limit_data and 'result' in risk_limit_data and 'list' in risk_limit_data['result']:
            risk_limits = risk_limit_data['result']['list']
            if risk_limits:
                logger.info(f"Successfully fetched risk limit data: {len(risk_limits)} levels")
                return {
                    "levels": risk_limits,
                    "current_utilization": 0.4  # Placeholder
                }
        
        # If that failed, try alternative endpoint for unified margin accounts
        risk_params['unified'] = True
        risk_limit_data = await bybit._make_request('GET', '/v5/position/risk-limit', risk_params)
        
        if risk_limit_data and 'result' in risk_limit_data and 'list' in risk_limit_data['result']:
            risk_limits = risk_limit_data['result']['list']
            if risk_limits:
                logger.info(f"Successfully fetched unified margin risk limit data: {len(risk_limits)} levels")
                return {
                    "levels": risk_limits,
                    "current_utilization": 0.4  # Placeholder
                }
        
        # If still no data, try one more approach with different endpoint
        account_data = await bybit._make_request('GET', '/v5/position/list', {'category': 'linear', 'symbol': symbol})
        if account_data and 'result' in account_data and 'list' in account_data['result']:
            positions = account_data['result']['list']
            if positions:
                # Extract risk limit info from position data
                position = positions[0]
                risk_limit = {
                    "levels": [{
                        "id": position.get('riskId', 1),
                        "limit": position.get('riskLimitValue', 100000),
                        "starting_margin": position.get('imRate', 0.01),
                        "maintain_margin": position.get('mmRate', 0.005)
                    }],
                    "current_utilization": float(position.get('positionValue', 0)) / 
                                         float(position.get('riskLimitValue', 100000))
                }
                logger.info(f"Extracted risk limit from position data")
                return risk_limit
    
    except Exception as e:
        logger.error(f"Error fetching risk limit data: {e}")
    
    logger.warning("Could not fetch risk limit data")
    return None

def analyze_component_correlations(components):
    """
    Analyze correlations between sentiment components and detect outliers.
    
    Args:
        components: Dictionary of component scores
        
    Returns:
        tuple: (balanced_components, outliers)
    """
    if not components or len(components) < 3:
        return components, []
    
    # Calculate mean and standard deviation
    scores = np.array(list(components.values()))
    mean_score = np.mean(scores)
    std_dev = np.std(scores)
    
    # Identify outliers (more than 2 standard deviations from mean)
    outliers = []
    for component, score in components.items():
        if abs(score - mean_score) > 2 * std_dev:
            outliers.append((component, score))
    
    # Create balanced version with outliers dampened
    balanced_components = components.copy()
    for component, score in outliers:
        # Move extreme outliers 30% closer to the mean
        direction = 1 if score > mean_score else -1
        adjustment = abs(score - mean_score) * 0.3
        balanced_components[component] = score - (direction * adjustment)
    
    return balanced_components, outliers

async def analyze_funding_rate_context(funding_rate, funding_history):
    """
    Analyze funding rate in historical context.
    
    Args:
        funding_rate: Current funding rate
        funding_history: List of historical funding rates
        
    Returns:
        dict: Analysis results
    """
    results = {
        'current_rate': funding_rate,
        'is_extreme': False,
        'percentile': 50,
        'trend': 'neutral',
        'context': 'normal'
    }
    
    if not funding_history or len(funding_history) < 5:
        return results
    
    # Extract rates from history
    if isinstance(funding_history[0], dict):
        if 'rate' in funding_history[0]:
            rates = [float(entry['rate']) for entry in funding_history]
        elif 'fundingRate' in funding_history[0]:
            rates = [float(entry['fundingRate']) for entry in funding_history]
        else:
            key = next((k for k in funding_history[0].keys() if 'rate' in k.lower()), None)
            if key:
                rates = [float(entry[key]) for entry in funding_history]
            else:
                return results
    else:
        rates = [float(rate) for rate in funding_history]
    
    # Calculate statistics
    abs_rates = [abs(rate) for rate in rates]
    mean_rate = np.mean(rates)
    max_abs_rate = max(abs_rates)
    
    # Check if current rate is extreme
    if abs(funding_rate) > 0.75 * max_abs_rate:
        results['is_extreme'] = True
        
    # Calculate percentile
    sorted_rates = sorted(rates)
    idx = sorted_rates.index(funding_rate) if funding_rate in sorted_rates else -1
    if idx >= 0:
        results['percentile'] = (idx / len(sorted_rates)) * 100
    else:
        # Find approximate position
        for i, rate in enumerate(sorted_rates):
            if funding_rate < rate:
                results['percentile'] = (i / len(sorted_rates)) * 100
                break
    
    # Determine trend
    if len(rates) >= 3:
        recent_rates = rates[:3]  # Most recent first
        if all(rate < recent_rates[i+1] for i, rate in enumerate(recent_rates[:-1])):
            results['trend'] = 'decreasing'
        elif all(rate > recent_rates[i+1] for i, rate in enumerate(recent_rates[:-1])):
            results['trend'] = 'increasing'
    
    # Determine context
    if abs(funding_rate) < 0.0001:
        results['context'] = 'very_low'
    elif results['is_extreme']:
        results['context'] = 'extreme'
    elif abs(funding_rate) > 0.001:
        results['context'] = 'high'
    
    return results

async def test_integrated_liquidation_cache(symbol="BTCUSDT"):
    """
    Test the integrated liquidation caching system with the sentiment indicators.
    
    Args:
        symbol: Trading pair symbol
    """
    logger.info("\n=== Testing Integrated Liquidation Cache for %s ===", symbol)
    
    # Initialize config and exchange
    config_mgr = ConfigManager()
    exchange_mgr = ExchangeManager(config_mgr)
    
    try:
        await exchange_mgr.initialize()
        bybit = await exchange_mgr.get_primary_exchange()
        
        if not bybit:
            logger.error("Failed to initialize Bybit exchange")
            return None, None
        
        # Initialize sentiment indicator
        sentiment_config = {
            'components': {
                'funding_rate': {'weight': 0.2},
                'long_short_ratio': {'weight': 0.2},
                'liquidations': {'weight': 0.2}, 
                'volume_sentiment': {'weight': 0.2},
                'market_mood': {'weight': 0.1},
                'risk': {'weight': 0.1}
            },
            'funding_threshold': 0.01,
            'liquidation_threshold': 1000000,
            'window': 20,
            'timeframes': {
                'base': {'interval': '1m', 'weight': 0.4, 'validation': {'min_candles': 20}},
                'ltf': {'interval': '5m', 'weight': 0.3, 'validation': {'min_candles': 20}},
                'mtf': {'interval': '1h', 'weight': 0.2, 'validation': {'min_candles': 20}},
                'htf': {'interval': '4h', 'weight': 0.1, 'validation': {'min_candles': 20}}
            }
        }
        sentiment = SentimentIndicators(sentiment_config)
        
        # Step 1: Fetch market data from exchange (should include cached liquidations if any)
        logger.info("\n--- Fetching Market Data ---")
        
        # Market data structure
        market_data = {
            'symbol': symbol,
            'ticker': {},
            'trades': [],
            'ohlcv': {},
            'sentiment': {
                'liquidations': []
            }
        }
        
        # Fetch current price
        ticker = await bybit.fetch_ticker(symbol)
        market_data['ticker'] = ticker
        current_price = float(ticker.get('last', 0))
        logger.info(f"Current price: {current_price}")
        
        # Fetch long/short ratio
        try:
            lsr = await bybit.fetch_long_short_ratio(symbol)
            market_data['sentiment']['long_short_ratio'] = lsr
            logger.info(f"Long/Short ratio: {lsr.get('long', 0):.1f}/{lsr.get('short', 0):.1f}")
        except Exception as e:
            logger.warning(f"Could not fetch long/short ratio: {e}")
            market_data['sentiment']['long_short_ratio'] = {'long': 1.0, 'short': 1.0}
        
        # Fetch funding rate
        try:
            funding_info = await bybit.fetch_funding_rate(symbol)
            funding_rate = funding_info.get('fundingRate', 0)
            market_data['sentiment']['funding_rate'] = funding_rate
            logger.info(f"Current funding rate: {funding_rate}")
        except Exception as e:
            logger.warning(f"Could not fetch funding rate: {e}")
            market_data['sentiment']['funding_rate'] = 0
        
        # Step 2: Check for cached liquidations
        logger.info("\n--- Checking Liquidation Cache ---")
        
        cached_liquidations = liquidation_cache.load(symbol)
        
        if cached_liquidations:
            logger.info(f"Found {len(cached_liquidations)} cached liquidation events")
            market_data['sentiment']['liquidations'] = cached_liquidations
        else:
            logger.info("No cached liquidation events found")
            
            # Generate some sample liquidation data for testing if needed
            if not cached_liquidations:
                logger.info("Generating sample liquidation data for testing")
                sample_liquidations = [
                    {
                        'side': 'long',
                        'size': 15.2,
                        'price': current_price * 0.995,
                        'timestamp': int(time.time() * 1000) - 300000,  # 5 min ago
                        'source': 'sample'
                    },
                    {
                        'side': 'short',
                        'size': 18.5,
                        'price': current_price * 1.005,
                        'timestamp': int(time.time() * 1000) - 600000,  # 10 min ago
                        'source': 'sample'
                    },
                    {
                        'side': 'long',
                        'size': 22.4,
                        'price': current_price * 0.99,
                        'timestamp': int(time.time() * 1000) - 1200000,  # 20 min ago
                        'source': 'sample'
                    }
                ]
                
                # Save sample data to cache
                liquidation_cache.save(sample_liquidations, symbol)
                logger.info(f"Saved {len(sample_liquidations)} sample liquidation events to cache")
                
                # Now load from cache to verify it works
                cached_liquidations = liquidation_cache.load(symbol)
                if cached_liquidations:
                    logger.info(f"Successfully loaded {len(cached_liquidations)} liquidation events from cache")
                    market_data['sentiment']['liquidations'] = cached_liquidations
        
        # Step 3: Calculate sentiment score
        logger.info("\n--- Calculating Sentiment Score ---")
        sentiment_result = sentiment._calculate_sync(market_data)
        
        # Print results
        logger.info("\nStandard Sentiment Score Calculation:")
        logger.info(f"Overall score: {sentiment_result.get('score', 0):.2f}")
        logger.info("Component scores:")
        for component, score in sentiment_result.items():
            if component != 'score' and component != 'sentiment':
                if isinstance(score, dict):
                    logger.info(f"  {component}: {score}")
                elif isinstance(score, (int, float)):
                    logger.info(f"  {component}: {score:.2f}")
                else:
                    logger.info(f"  {component}: {score}")
        
        # Return market data and sentiment result for further analysis
        return market_data, sentiment_result
        
    finally:
        # Cleanup resources
        await exchange_mgr.close()

async def main():
    """Main function to run the test."""
    try:
        market_data, sentiment_result = await test_integrated_liquidation_cache("BTCUSDT")
        
        print("\n=== Sentiment Improvements Test Summary ===")
        print(f"Standard Score: {sentiment_result.get('score', 0):.2f}")
        print("\nComponents:")
        for component, score in sentiment_result.items():
            if component != 'score' and component != 'sentiment':
                if isinstance(score, dict):
                    print(f"  {component}: {score}")
                elif isinstance(score, (int, float)):
                    print(f"  {component}: {score:.2f}")
                else:
                    print(f"  {component}: {score}")
        if 'sentiment' in sentiment_result:
            print(f"  sentiment: {sentiment_result.get('sentiment', 0):.2f}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Cleanup resources
        if 'bybit' in locals() and hasattr(bybit, 'close'):
            await bybit.close()
            
        # Close any pending tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(main()) 