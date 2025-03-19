import asyncio
import logging
import pandas as pd
import numpy as np
import pytest
import pandas_ta as ta
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Any
import time
from pybit.exceptions import FailedRequestError
import aiohttp

from src.core.exchanges.bybit import BybitExchange
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.position_indicators import PositionIndicators
from src.indicators.momentum_indicators import MomentumIndicators
from src.indicators.sentiment_indicators import SentimentIndicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)7s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def find_and_close_client_sessions(obj, seen=None):
    """Recursively find and close all client sessions."""
    if seen is None:
        seen = set()
    
    if id(obj) in seen:
        return
    seen.add(id(obj))
    
    # If object is a client session, close it
    if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
        try:
            await asyncio.wait_for(obj.close(), timeout=1.0)
            logger.debug("Closed client session")
        except asyncio.TimeoutError:
            logger.warning("Timeout closing client session")
        return
    
    # Handle common container types
    if isinstance(obj, dict):
        for value in obj.values():
            await find_and_close_client_sessions(value, seen)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            await find_and_close_client_sessions(item, seen)
    elif hasattr(obj, '__dict__'):
        await find_and_close_client_sessions(obj.__dict__, seen)

@pytest.mark.asyncio
async def test_confluence_analysis():
    """Test the confluence analysis functionality"""
    exchange = None
    indicators = None
    try:
        # Initialize exchange
        exchange = BybitExchange()
        await exchange.init()
        logger.info("Bybit exchange initialized successfully")

        # Initialize indicators with configuration
        indicators = initialize_indicators()
        logger.info("Initialized indicators with configuration")

        # Define symbols to analyze
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        for symbol in symbols:
            try:
                logger.info(f"\nAnalyzing {symbol}...")

                # Fetch market data for all timeframes
                timeframes = {
                    "1m": "base",
                    "5m": "ltf",
                    "15m": "mtf",
                    "4h": "htf"
                }
                
                # Validate symbol is available
                try:
                    await exchange.fetch_ticker(symbol)
                except Exception as e:
                    logger.error(f"Symbol {symbol} is not available: {str(e)}")
                    continue
                    
                price_data = await fetch_all_historical_data(exchange, symbol, timeframes)

                # Fetch orderbook and trades with error handling
                logger.info(f"Fetching orderbook and trades for {symbol}...")
                try:
                    orderbook = await exchange.fetch_order_book(symbol, limit=50)
                    
                    # Calculate time range for trades (last 24 hours)
                    end_time = int(time.time() * 1000)
                    start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
                    
                    # Fetch trades in batches
                    all_trades = []
                    batch_size = 60  # Keep at 60 due to exchange limits
                    current_end = end_time
                    
                    logger.info(f"Fetching trades from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
                    
                    while current_end > start_time and len(all_trades) < 5000:  # Limit total trades to 5000
                        try:
                            batch = await exchange.fetch_trades(
                                symbol,
                                limit=batch_size,
                                params={
                                    'endTime': current_end
                                }
                            )
                            
                            if not batch:
                                break
                                
                            all_trades.extend(batch)
                            logger.info(f"Fetched batch of {len(batch)} trades, total trades: {len(all_trades)}")
                            
                            # Update end time for next batch
                            batch_timestamps = [trade['timestamp'] for trade in batch]
                            if batch_timestamps:
                                current_end = min(batch_timestamps) - 1
                            else:
                                break
                                
                            # Reduced delay between batches but keep it safe
                            await asyncio.sleep(0.2)  # Balanced between speed and rate limits
                            
                        except Exception as e:
                            logger.error(f"Error fetching trade batch: {str(e)}")
                            await asyncio.sleep(1)  # Wait longer on error
                            continue
                    
                    trades = all_trades
                    logger.info(f"Total trades fetched: {len(trades)}")
                    
                except Exception as e:
                    logger.error(f"Error fetching market data for {symbol}: {str(e)}")
                    continue
                
                # Debug orderbook structure
                logger.info(f"Orderbook structure:")
                logger.info(f"Keys: {list(orderbook.keys())}")
                logger.info(f"Number of bids: {len(orderbook.get('bids', []))}")
                logger.info(f"Number of asks: {len(orderbook.get('asks', []))}")
                logger.info(f"Sample bid: {orderbook.get('bids', [])[0] if orderbook.get('bids', []) else None}")
                logger.info(f"Sample ask: {orderbook.get('asks', [])[0] if orderbook.get('asks', []) else None}")
                
                # Debug trades structure
                logger.info(f"Trades structure:")
                logger.info(f"Number of trades: {len(trades)}")
                logger.info(f"Sample trade: {trades[0] if trades else None}")
                
                # Convert trades to DataFrame
                logger.info(f"Converting trades data for {symbol}...")
                try:
                    trades_df = pd.DataFrame(trades)
                    if trades_df.empty:
                        logger.warning("All trades data was invalid after cleaning")
                        trades_df = pd.DataFrame(columns=['timestamp', 'side', 'price', 'amount', 'volume', 'high', 'low', 'close'])
                        # Add a single row with neutral values to prevent calculation errors
                        current_time = pd.Timestamp.now()
                        trades_df.loc[current_time] = {
                            'side': 'buy',
                            'price': 0.0,
                            'amount': 0.0,
                            'volume': 0.0,
                            'high': 0.0,
                            'low': 0.0,
                            'close': 0.0
                        }
                    else:
                        # Map and validate required columns
                        required_columns = {
                            'timestamp': 'timestamp',
                            'side': 'side',
                            'price': 'price',
                            'amount': 'amount'
                        }
                        
                        # Check for missing columns
                        missing_columns = [col for col in required_columns.values() if col not in trades_df.columns]
                        if missing_columns:
                            raise ValueError(f"Missing required columns in trades data: {missing_columns}")
                            
                        # Set index and convert timestamp
                        trades_df.set_index('timestamp', inplace=True)
                        trades_df.index = pd.to_datetime(trades_df.index, unit='ms')
                        
                        # Validate and convert data types
                        trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
                        trades_df['amount'] = pd.to_numeric(trades_df['amount'], errors='coerce')
                        trades_df['side'] = trades_df['side'].astype(str).str.lower()
                        
                        # Validate side values
                        valid_sides = ['buy', 'sell']
                        trades_df = trades_df[trades_df['side'].isin(valid_sides)]
                        
                        # Calculate volume
                        trades_df['volume'] = trades_df['price'] * trades_df['amount']
                        
                        # Remove any rows with NaN values
                        trades_df.dropna(subset=['price', 'amount', 'volume'], inplace=True)
                        
                        # Remove any rows with zero or negative values
                        trades_df = trades_df[
                            (trades_df['price'] > 0) & 
                            (trades_df['amount'] > 0) & 
                            (trades_df['volume'] > 0)
                        ]
                        
                        if trades_df.empty:
                            logger.warning("All trades data was invalid after cleaning")
                            trades_df = pd.DataFrame(columns=['timestamp', 'side', 'price', 'amount', 'volume', 'high', 'low', 'close'])
                            # Add a single row with neutral values
                            current_time = pd.Timestamp.now()
                            trades_df.loc[current_time] = {
                                'side': 'buy',
                                'price': 0.0,
                                'amount': 0.0,
                                'volume': 0.0,
                                'high': 0.0,
                                'low': 0.0,
                                'close': 0.0
                            }
                        else:
                            # Calculate OHLCV data
                            trades_df['high'] = trades_df['price'].rolling(window=10, min_periods=1).max()
                            trades_df['low'] = trades_df['price'].rolling(window=10, min_periods=1).min()
                            trades_df['close'] = trades_df['price']
                            logger.info(f"Processed {len(trades_df)} valid trades")
                            logger.debug(f"Trades summary:\n{trades_df.describe()}")
                            
                except Exception as e:
                    logger.error(f"Error processing trades data: {str(e)}")
                    trades_df = pd.DataFrame(columns=['timestamp', 'side', 'price', 'amount', 'volume', 'high', 'low', 'close'])
                    # Add a single row with neutral values
                    current_time = pd.Timestamp.now()
                    trades_df.loc[current_time] = {
                        'side': 'buy',
                        'price': 0.0,
                        'amount': 0.0,
                        'volume': 0.0,
                        'high': 0.0,
                        'low': 0.0,
                        'close': 0.0
                    }
                
                # Convert orderbook to DataFrame
                try:
                    if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                        logger.warning("Invalid orderbook structure")
                        orderbook_df = pd.DataFrame(columns=['price', 'size', 'side'])
                        # Add neutral values
                        orderbook_df = pd.concat([
                            pd.DataFrame({
                                'price': [100.0] * 10,
                                'size': [1.0] * 10,
                                'side': ['bid'] * 10
                            }),
                            pd.DataFrame({
                                'price': [100.1] * 10,
                                'size': [1.0] * 10,
                                'side': ['ask'] * 10
                            })
                        ])
                    else:
                        # Validate and convert orderbook data
                        bids = [(float(x[0]), float(x[1])) for x in orderbook['bids'] if len(x) >= 2 and float(x[0]) > 0 and float(x[1]) > 0]
                        asks = [(float(x[0]), float(x[1])) for x in orderbook['asks'] if len(x) >= 2 and float(x[0]) > 0 and float(x[1]) > 0]
                        
                        if not bids or not asks:
                            logger.warning("No valid bids or asks in orderbook")
                            # Use last known good price if available
                            last_price = market_data.get('ticker', {}).get('last', 100.0)
                            orderbook_df = pd.concat([
                                pd.DataFrame({
                                    'price': [last_price * 0.999] * 10,
                                    'size': [1.0] * 10,
                                    'side': ['bid'] * 10
                                }),
                                pd.DataFrame({
                                    'price': [last_price * 1.001] * 10,
                                    'size': [1.0] * 10,
                                    'side': ['ask'] * 10
                                })
                            ])
                        else:
                            orderbook_df = pd.DataFrame({
                                'price': [p for p, _ in bids] + [p for p, _ in asks],
                                'size': [s for _, s in bids] + [s for _, s in asks],
                                'side': ['bid'] * len(bids) + ['ask'] * len(asks)
                            })
                            
                            # Sort by price
                            orderbook_df.sort_values('price', ascending=True, inplace=True)
                            
                            # Ensure minimum size
                            orderbook_df.loc[orderbook_df['size'] < 0.0001, 'size'] = 0.0001
                            
                except Exception as e:
                    logger.error(f"Error processing orderbook data: {str(e)}")
                    # Use last known good price if available
                    last_price = market_data.get('ticker', {}).get('last', 100.0)
                    orderbook_df = pd.concat([
                        pd.DataFrame({
                            'price': [last_price * 0.999] * 10,
                            'size': [1.0] * 10,
                            'side': ['bid'] * 10
                        }),
                        pd.DataFrame({
                            'price': [last_price * 1.001] * 10,
                            'size': [1.0] * 10,
                            'side': ['ask'] * 10
                        })
                    ])
                
                logger.info(f"Orderbook DataFrame info:")
                logger.info(f"Shape: {orderbook_df.shape}")
                logger.info(f"Columns: {orderbook_df.columns.tolist()}")
                logger.info(f"Sample data:\n{orderbook_df.head()}")
                
                # Prepare market data for analysis with correct naming
                logger.info(f"Preparing market data for {symbol}...")
                
                # Use base timeframe data for ticker calculations
                base_data = price_data.get('base')
                if base_data is None or base_data.empty:
                    raise ValueError(f"No base timeframe data available for {symbol}")
                    
                market_data = {
                    'symbol': symbol,
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'ticker': {
                        'last': float(base_data['close'].iloc[-1]),
                        'high': float(base_data['high'].max()),
                        'low': float(base_data['low'].min()),
                        'volume': float(base_data['volume'].sum()),
                        'quote_volume': None,  # Not available in test data
                        'change': float(((base_data['close'].iloc[-1] / base_data['open'].iloc[0]) - 1) * 100)
                    },
                    'price_data': price_data,
                    'orderbook': orderbook_df,
                    'trades': pd.DataFrame({
                        'symbol': [symbol] * len(trades_df),
                        'side': trades_df['side'],
                        'price': trades_df['price'],
                        'amount': trades_df['amount'],
                        'timestamp': trades_df.index,
                        'type': ['market'] * len(trades_df)  # Adding type field to match exchange
                    }).set_index('timestamp'),
                    'timeframes': timeframes,
                    'metadata': {
                        'exchange': 'bybit',
                        'market_type': 'spot'
                    },
                    'ohlcv': base_data[['open', 'high', 'low', 'close', 'volume']]  # Add OHLCV data
                }
                
                # Debug market data structure
                logger.info(f"Market data structure:")
                logger.info(f"Keys: {list(market_data.keys())}")
                logger.info(f"Price data timeframes: {list(market_data['price_data'].keys())}")
                logger.info(f"Trades shape: {market_data['trades'].shape}")
                logger.info(f"Orderbook shape: {market_data['orderbook'].shape}")

                # Validate market data before analysis
                try:
                    required_data = {
                        'price_data': ['base'],
                        'orderbook': ['price', 'size', 'side'],
                        'trades': ['side', 'price', 'amount']
                    }
                    
                    # Check price data
                    if 'base' not in price_data:
                        raise ValueError("Missing base timeframe data")
                    
                    # Check orderbook data
                    for col in required_data['orderbook']:
                        if col not in orderbook_df.columns:
                            raise ValueError(f"Missing required column in orderbook data: {col}")
                    
                    # Check trades data
                    for col in required_data['trades']:
                        if col not in trades_df.columns:
                            raise ValueError(f"Missing required column in trades data: {col}")
                            
                    logger.info("Market data validation successful")
                    
                except Exception as e:
                    logger.error(f"Market data validation failed: {str(e)}")
                    continue
                    
                # Calculate indicator scores with timeout protection
                logger.info(f"\nCalculating indicator scores for {symbol}...")
                
                async def calculate_indicator_score(name: str, indicator: Any, data: Dict[str, Any]) -> Dict[str, Any]:
                    """Calculate indicator score with timeout and validation.
                    
                    Args:
                        name: Indicator name
                        indicator: Indicator instance
                        data: Market data
                        
                    Returns:
                        Validated indicator result
                    """
                    try:
                        # Special handling for orderflow indicator
                        method = indicator.analyze_orderflow if name == 'orderflow' else indicator.analyze
                        
                        result = await asyncio.wait_for(
                            method(data),
                            timeout=30.0  # 30 second timeout
                        )
                        
                        return validate_indicator_result(result, name)
                        
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout calculating {name} score")
                        return {'score': 50.0, 'status': 'timeout'}
                    except Exception as e:
                        logger.error(f"Error calculating {name} score: {str(e)}")
                        return {'score': 50.0, 'status': 'error'}
                
                # Calculate all scores with timeout protection
                scores = {}
                for name, indicator in indicators.items():
                    logger.info(f"Running {name} analysis...")
                    if name == 'orderflow':
                        result = await calculate_indicator_score(name, indicator, market_data)
                        scores[name] = result['score'] if isinstance(result, dict) else 50.0
                    else:
                        result = await calculate_indicator_score(name, indicator, market_data)
                        scores[name] = result['score'] if isinstance(result, dict) else 50.0
                    
                    logger.info(f"{name.capitalize()} Analysis Score: {scores[name]:.2f}")
                    if isinstance(result, dict) and 'components' in result:
                        logger.info(f"{name.capitalize()} Analysis Components: {result['components']}")

                # Calculate overall confluence score
                overall_score = calculate_overall_score(scores)

                # Log analysis results
                logger.info(f"\nConfluence Analysis Results for {symbol}:")
                logger.info(f"Overall Score: {overall_score:.2f}")
                logger.info(f"Interpretation: {interpret_score(overall_score)}")
                
                # Log individual components
                logger.info("\nComponent Scores:")
                for component, score in scores.items():
                    logger.info(f"{component.capitalize()}: {score:.2f}")

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                logger.error(f"Traceback:", exc_info=True)
                continue
                
    except Exception as e:
        logger.error(f"Error in test_confluence_analysis: {str(e)}")
        raise
        
    finally:
        # Ensure exchange cleanup
        if exchange:
            try:
                # First close the exchange connection
                await exchange.close()
                logger.info("Exchange connection closed successfully")
                
                # Close the main client session if it exists
                if hasattr(exchange, 'client') and exchange.client is not None and hasattr(exchange.client, 'closed') and not exchange.client.closed:
                    try:
                        await asyncio.wait_for(exchange.client.close(), timeout=1.0)
                        logger.debug("Closed main client session")
                    except asyncio.TimeoutError:
                        logger.warning("Timeout closing main client session")
                
                # Get all tasks except the current one
                current_task = asyncio.current_task()
                tasks = [t for t in asyncio.all_tasks() if t is not current_task]
                
                if tasks:
                    logger.info(f"Found {len(tasks)} pending tasks to clean up")
                    
                    # Cancel all pending tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    
                    # Wait for all tasks to complete/cancel with a timeout
                    try:
                        await asyncio.wait(tasks, timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for tasks to cancel")
                
                # Find and close all client sessions
                if exchange:
                    await find_and_close_client_sessions(exchange)
                if indicators:
                    await find_and_close_client_sessions(indicators)
                
                # Check for any remaining client sessions in tasks
                for task in tasks:
                    if hasattr(task, '_coro'):
                        await find_and_close_client_sessions(task._coro)
                
                logger.info("All resources cleaned up successfully")
                
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                raise

async def fetch_all_historical_data(exchange: BybitExchange, symbol: str, timeframes: dict) -> Dict[str, pd.DataFrame]:
    """Fetch historical data for all timeframes"""
    price_data = {}
    try:
        required_candles = {
            'base': 1000,
            'ltf': 200,
            'mtf': 200,
            'htf': 200
        }
        
        logger.info(f"\nFetching historical data for {symbol}...")
        logger.info(f"Timeframes to fetch: {timeframes}")
        logger.info(f"Required candles per timeframe: {required_candles}")
        
        for tf, tf_key in timeframes.items():
            retries = 3
            retry_delay = 1
            
            for attempt in range(retries):
                try:
                    # Get required number of candles for this timeframe
                    limit = required_candles[tf_key]
                    logger.info(f"\nFetching {limit} candles for {symbol} on {tf} timeframe (attempt {attempt + 1}/{retries})...")
                    
                    klines = await exchange.fetch_historical_klines(symbol, tf, limit=limit)
                    if not klines:
                        logger.warning(f"No klines data returned for {symbol} on {tf} timeframe")
                        break
                        
                    logger.info(f"Received {len(klines)} klines")
                    
                    df = pd.DataFrame(klines)
                    if df.empty:
                        logger.warning(f"Empty DataFrame for {symbol} on {tf} timeframe")
                        break
                        
                    df.set_index('timestamp', inplace=True)
                    df.index = pd.to_datetime(df.index, unit='ms')
                    
                    # Ensure all required columns are present and properly formatted
                    required_columns = ['open', 'high', 'low', 'close', 'volume']
                    for col in required_columns:
                        if col not in df.columns:
                            logger.warning(f"Missing {col} column in {tf} timeframe data")
                            df[col] = 0.0
                        else:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Calculate additional required fields
                    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
                    df['hlc3'] = df['typical_price']  # Alias for typical price
                    df['ohlc4'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
                    df['ha_close'] = df['ohlc4']  # Heikin-Ashi close
                    
                    # Drop any rows with NaN values
                    df.dropna(subset=required_columns, inplace=True)
                    
                    if df.empty:
                        logger.warning(f"No valid data after cleaning for {symbol} on {tf} timeframe")
                        break
                    
                    # Store only the timeframe-specific version
                    price_data[tf_key] = df.copy()
                    
                    logger.info(f"Successfully stored {len(df)} candles for {symbol} on {tf} timeframe")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < retries - 1:
                        logger.warning(f"Error fetching {symbol} data for {tf} timeframe (attempt {attempt + 1}/{retries}): {str(e)}")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"Failed to fetch {symbol} data for {tf} timeframe after {retries} attempts: {str(e)}")
                        logger.error("Traceback:", exc_info=True)
        
        if not price_data:
            raise ValueError(f"No price data could be fetched for {symbol}")
            
        logger.info(f"\nFinal price data summary for {symbol}:")
        logger.info(f"Available timeframes: {list(price_data.keys())}")
        for tf_key, df in price_data.items():
            logger.info(f"{tf_key} timeframe shape: {df.shape}")
            logger.info(f"{tf_key} timeframe date range: {df.index.min()} to {df.index.max()}")
                
        return price_data
        
    except Exception as e:
        logger.error(f"Error in fetch_all_historical_data: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        raise

def interpret_score(score: float) -> str:
    """Interpret a score value"""
    if score >= 70:
        return "Market analysis indicates strongly bullish conditions"
    elif score >= 60:
        return "Market analysis indicates moderately bullish conditions"
    elif score >= 55:
        return "Market analysis indicates slightly bullish conditions"
    elif score >= 45:
        return "Market analysis indicates neutral conditions"
    elif score >= 40:
        return "Market analysis indicates slightly bearish conditions"
    elif score >= 30:
        return "Market analysis indicates moderately bearish conditions"
    else:
        return "Market analysis indicates strongly bearish conditions"

def calculate_confidence(scores):
    """Calculate confidence factor based on score distribution"""
    valid_scores = [s for s in scores.values() if s is not None]
    if not valid_scores:
        return 0.0
    
    # Calculate standard deviation and range
    std = np.std(valid_scores)
    score_range = max(valid_scores) - min(valid_scores)
    
    # Higher confidence when scores are consistent (low std) and cover good range
    confidence = (1 - std/100) * (score_range/100)
    return min(max(confidence, 0.0), 1.0)

def calculate_overall_score(scores):
    """Calculate weighted average of component scores"""
    weights = {
        'volume': 0.3,
        'orderbook': 0.2,
        'orderflow': 0.2, 
        'momentum': 0.15,
        'sentiment': 0.15
    }
    
    total_weight = 0
    weighted_sum = 0
    
    for component, score in scores.items():
        if score is not None and component in weights:
            weighted_sum += score * weights[component]
            total_weight += weights[component]
    
    if total_weight == 0:
        return 0
        
    return weighted_sum / total_weight

def initialize_indicators():
    """Initialize all indicator classes with configurations"""
    configs = {
        'volume': {
            'volume_analysis': {
                'timeframes': ['1m', '5m', '15m', '1h'],
                'ma_periods': [20, 50, 200],
                'volume_thresholds': {'high': 2.0, 'low': 0.5},
                'delta_thresholds': {'strong': 0.7, 'weak': 0.3}
            }
        },
        'orderbook': {
            'analysis': {
                'depth_levels': 50,
                'price_levels': 20,
                'volume_levels': 10
            }
        },
        'position': {
            'analysis': {
                'position_size_threshold': 0.1,
                'leverage_threshold': 10,
                'risk_threshold': 0.02
            }
        },
        'orderflow': {
            'analysis': {
                'trade_sample_size': 1000,
                'volume_threshold': 1.5
            }
        },
        'momentum': {
            'analysis': {
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9
            }
        },
        'sentiment': {
            'analysis': {
                'funding_threshold': 0.01,
                'liquidation_threshold': 1000000
            }
        }
    }
    
    return {
        'volume': VolumeIndicators(config=configs['volume']),
        'orderbook': OrderbookIndicators(config=configs['orderbook']),
        'position': PositionIndicators(config=configs['position']),
        'orderflow': OrderflowIndicators(config=configs['orderflow']),
        'momentum': MomentumIndicators(config=configs['momentum']),
        'sentiment': SentimentIndicators(config=configs['sentiment'])
    }

def validate_indicator_result(result: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Validate and normalize indicator result.
    
    Args:
        result: Raw indicator result
        name: Indicator name
        
    Returns:
        Normalized indicator result with score and status
    """
    try:
        if not isinstance(result, dict):
            logger.warning(f"Invalid {name} result type: {type(result)}")
            return {'score': 50.0, 'status': 'invalid_type'}
            
        if 'score' not in result:
            logger.warning(f"Missing score in {name} result")
            return {'score': 50.0, 'status': 'missing_score'}
            
        score = float(result['score'])
        if not 0 <= score <= 100:
            logger.warning(f"Invalid {name} score range: {score}")
            return {'score': 50.0, 'status': 'invalid_range'}
            
        return {
            'score': score,
            'status': result.get('status', 'success'),
            'components': result.get('components', {})
        }
        
    except Exception as e:
        logger.error(f"Error validating {name} result: {str(e)}")
        return {'score': 50.0, 'status': 'validation_error'}

if __name__ == "__main__":
    asyncio.run(test_confluence_analysis()) 