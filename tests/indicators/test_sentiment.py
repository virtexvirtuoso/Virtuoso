#!/usr/bin/env python
import os
import sys
import time
import logging
import json
import argparse
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import ccxt
import asyncio
from datetime import datetime, timedelta

# Add the project root to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger
from src.core.exchanges.bybit import BybitExchange

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
# Create a logger instance correctly
logger = Logger('sentiment_test')

async def fetch_live_data_async(symbol='BTCUSDT', timeframes=['1', '5', '30', '240'], use_testnet=False):
    """Fetch live market data using the BybitExchange implementation."""
    exchange = None
    try:
        print(f"Fetching live data from Bybit for {symbol}...")
        
        # Basic exchange configuration
        config = {
            'exchanges': {
                'bybit': {
                    'enabled': True,
                    'name': 'bybit',
                    'api_credentials': {
                        'api_key': os.getenv('BYBIT_API_KEY', ''),
                        'api_secret': os.getenv('BYBIT_API_SECRET', '')
                    },
                    'testnet': use_testnet,
                    'rest_endpoint': 'https://api-testnet.bybit.com' if use_testnet else 'https://api.bybit.com',
                    'websocket': {
                        'enabled': False,
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                        'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear',
                        'channels': ['trade', 'orderbook', 'kline', 'liquidation'],
                        'symbols': [symbol]
                    }
                }
            }
        }
        
        # Initialize exchange
        exchange = BybitExchange(config, None)
        await exchange.initialize()
        
        # Fetch comprehensive market data
        market_data = await exchange.fetch_market_data(symbol)
        
        if not market_data:
            print("Failed to fetch market data from Bybit API, falling back to mock data")
            await exchange.close()  # Ensure we close the exchange
            return create_mock_data()
            
        print(f"Successfully fetched live market data for {symbol}")
        
        # Process OHLCV data into DataFrame format
        ohlcv_data = {}

        # Fetch OHLCV data directly with timeframes
        for tf in timeframes:
            try:
                # Convert timeframe to minutes for logging
                minutes = {'1': '1m', '5': '5m', '30': '30m', '240': '4h'}.get(tf, tf)
                print(f"Fetching {minutes} timeframe data...")
                
                # Fetch OHLCV data
                candles = await exchange.fetch_ohlcv(symbol, tf, 100)
                
                if candles and len(candles) > 0:
                    # Create DataFrame
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df = df.sort_index()
                    ohlcv_data[tf] = df
                    print(f"  Got {len(df)} candles for {minutes}")
                else:
                    print(f"  No candles returned for {minutes}")
                    # Create empty DataFrame as fallback
                    df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                    df.index = pd.DatetimeIndex([])
                    df.index.name = 'timestamp'
                    ohlcv_data[tf] = df
            except Exception as e:
                print(f"Error fetching {tf} timeframe: {str(e)}")
                # Create empty DataFrame as fallback
                df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                df.index = pd.DatetimeIndex([])
                df.index.name = 'timestamp'
                ohlcv_data[tf] = df
                
        # Format market data structure for sentiment analysis
        formatted_data = {
            'ohlcv': {
                'base': {
                    'data': ohlcv_data.get('1', pd.DataFrame())
                }
            },
            'trades': market_data.get('trades', []),
            'ticker': market_data.get('ticker', {}),
            'sentiment': {
                'funding_rate': market_data.get('ticker', {}).get('fundingRate', 0.0),
                'long_short_ratio': market_data.get('long_short_ratio', {
                    'long': 1.2,
                    'short': 1.0
                }),
                'liquidations': market_data.get('sentiment', {}).get('liquidations', [])
            },
            'risk_limit': market_data.get('risk_limit', {})
        }
        
        # If no liquidations data available, create mock liquidations
        if not formatted_data['sentiment']['liquidations']:
            current_time = time.time() * 1000
            hour_ago = current_time - 3600000
            
            # Add some mock liquidation events
            liquidations = []
            for i in range(10):
                # Random timestamp in the last hour
                ts = hour_ago + (i * 360000)
                # Alternating long/short with more longs
                side = 'long' if i % 3 == 0 else 'short'
                # Random amount
                amount = np.random.randint(10000, 100000)
                
                liquidations.append({
                    'timestamp': ts,
                    'side': side,
                    'amount': amount,
                    'price': market_data.get('ticker', {}).get('last', 60000)
                })
            
            formatted_data['sentiment']['liquidations'] = liquidations
            print("Added mock liquidation data")
        
        # Get funding rate from ticker
        if 'ticker' in market_data and 'fundingRate' in market_data['ticker']:
            formatted_data['sentiment']['funding_rate'] = market_data['ticker']['fundingRate']
        
        # Print some data stats
        print(f"OHLCV rows: {len(formatted_data['ohlcv']['base']['data'])}, Trades: {len(formatted_data['trades'])}")
        
        # Ensure proper cleanup
        await exchange.close()
        return formatted_data
        
    except Exception as e:
        print(f"Error fetching live data: {str(e)}")
        import traceback
        traceback.print_exc()
        # Ensure proper cleanup even on error
        if exchange:
            try:
                await exchange.close()
            except:
                pass
        return create_mock_data()

def fetch_live_data(symbol='BTCUSDT', timeframes=['1', '5', '30', '240'], use_testnet=False):
    """Wrapper around async function to fetch live data."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(fetch_live_data_async(symbol, timeframes, use_testnet))

async def fetch_live_data(symbol='BTCUSDT', timeframes=['1', '5', '30', '240'], use_testnet=False):
    """Async function to fetch live data."""
    return await fetch_live_data_async(symbol, timeframes, use_testnet)

def create_mock_data():
    """Create mock data when live data cannot be fetched."""
    print("Creating mock data...")
    
    # Create mock OHLCV data
    now = datetime.now()
    dates = [now - timedelta(hours=i) for i in range(100)]
    dates.reverse()
    
    # Generate random price data
    base_price = 60000
    prices = []
    price = base_price
    
    for _ in range(100):
        change = np.random.normal(0, 100)
        price += change
        prices.append(price)
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': [p * (1 + np.random.normal(0, 0.002)) for p in prices],
        'volume': [np.random.randint(100000, 1000000) for _ in range(100)]
    })
    df.set_index('timestamp', inplace=True)
    
    # Create mock trades
    trades = []
    for i in range(50):
        side = 'buy' if np.random.random() > 0.4 else 'sell'
        trades.append({
            'id': str(i),
            'side': side,
            'price': base_price * (1 + np.random.normal(0, 0.002)),
            'amount': np.random.randint(1, 10),
            'timestamp': int(time.time() * 1000) - i * 1000
        })
    
    # Create sentiment data structure
    sentiment_data = {
        'funding_rate': 0.0001,
        'long_short_ratio': {
            'long': 1.2,
            'short': 1.0
        },
        'liquidations': []
    }
    
    # Add some mock liquidation events
    current_time = time.time() * 1000
    hour_ago = current_time - 3600000
    
    for i in range(10):
        ts = hour_ago + (i * 360000)
        side = 'long' if i % 3 == 0 else 'short'
        amount = np.random.randint(10000, 100000)
        
        sentiment_data['liquidations'].append({
            'timestamp': ts,
            'side': side,
            'amount': amount,
            'price': base_price
        })
    
    # Structure market data
    market_data = {
        'ohlcv': {
            'base': {
                'data': df
            }
        },
        'trades': trades,
        'ticker': {
            'last': base_price,
            'info': {
                'fundingRate': 0.0001
            }
        },
        'sentiment': sentiment_data,
        'risk_limit': {
            'list': [
                {
                    'riskLimitValue': 200000,
                    'initialMargin': 0.01,
                    'maxLeverage': 100,
                    'maintenanceMargin': 0.005
                }
            ]
        }
    }
    
    return market_data

async def test_sentiment_indicators(symbol='BTCUSDT', use_testnet=False, save_results=False):
    """Test the SentimentIndicators class with live data."""
    try:
        # Create a basic config
        config = {
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'components': {
                            'funding_rate': {'weight': 0.15},
                            'long_short_ratio': {'weight': 0.15},
                            'liquidations': {'weight': 0.15},
                            'volume_sentiment': {'weight': 0.15},
                            'market_mood': {'weight': 0.15},
                            'risk_score': {'weight': 0.15},
                            'funding_rate_volatility': {'weight': 0.1}
                        },
                        'funding_threshold': 0.01,
                        'liquidation_threshold': 1000000,
                        'window': 20
                    }
                }
            },
            'timeframes': {
                'base': {'interval': 60, 'validation': {'min_candles': 10}, 'weight': 0.5},
                '1h': {'interval': 60, 'validation': {'min_candles': 10}, 'weight': 0.3},
                '1d': {'interval': 1440, 'validation': {'min_candles': 5}, 'weight': 0.2}
            },
            'validation_requirements': {
                'trades': {'min_trades': 10, 'max_age': 3600}
            }
        }
        
        # Initialize logger with detailed formatting
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        logger = logging.getLogger('sentiment_test')
        
        # Create SentimentIndicators instance
        sentiment = SentimentIndicators(config, logger)
        
        # Get live market data
        print(f"Fetching live data from Bybit for {symbol}...")
        market_data = await fetch_live_data(symbol, use_testnet=use_testnet)
        
        # Store timing data
        execution_times = []
        
        # Test with live data
        print("\n= Testing calculate method =")
        start_time = time.time()
        result = await sentiment.calculate(market_data)
        end_time = time.time()
        calculation_time = end_time - start_time
        execution_times.append(calculation_time)
        print(f"Calculate method executed in {calculation_time:.3f} seconds")
        
        # Print result summary
        print("\n= Sentiment Result Summary =")
        print(f"Overall score: {result['score']:.2f}")
        print("Component scores:")
        for component, score in result.get('components', {}).items():
            print(f"  {component}: {score:.2f}")
            
        # Print more detailed interpretation
        if 'interpretation' in result:
            print("\n= Sentiment Interpretation =")
            interpretation = result['interpretation']
            print(f"Signal: {interpretation.get('signal', 'N/A')}")
            print(f"Bias: {interpretation.get('bias', 'N/A')}")
            print(f"Risk level: {interpretation.get('risk_level', 'N/A')}")
            print(f"Summary: {interpretation.get('summary', 'N/A')}")
            
            # Print component interpretations if available
            if 'component_interpretations' in interpretation:
                print("\nComponent interpretations:")
                for component, interp in interpretation['component_interpretations'].items():
                    print(f"  {component}: {interp}")
        
        print("\n= Testing signals generation =")
        start_time = time.time()
        signals = await sentiment.get_signals(market_data)
        end_time = time.time()
        print(f"Signals generated in {end_time - start_time:.3f} seconds")
        
        print(f"Generated {len(signals)} signals")
        for signal in signals:
            print(f"  Signal: {signal['signal']}, Strength: {signal['strength']}, Confidence: {signal['confidence']:.2f}")
            print(f"  Reason: {signal['reason']}")
        
        # Test calculating with already computed scores
        print("\n= Testing reuse of calculated scores =")
        start_time = time.time()
        signals_with_existing = await sentiment.get_signals(market_data, existing_scores=result['components'])
        end_time = time.time()
        print(f"Signals using existing scores generated in {end_time - start_time:.3f} seconds")
        
        print("\n= Verifying caching mechanisms =")
        # Test caching - should be faster the second time
        start_time = time.time()
        second_result = await sentiment.calculate(market_data)
        end_time = time.time()
        cached_calculation_time = end_time - start_time
        execution_times.append(cached_calculation_time)
        print(f"Second calculate call executed in {cached_calculation_time:.3f} seconds")
        
        # Reset cache and test again
        print("\n= Testing after cache reset =")
        sentiment.reset_cache()
        start_time = time.time()
        third_result = await sentiment.calculate(market_data)
        end_time = time.time()
        reset_calculation_time = end_time - start_time
        execution_times.append(reset_calculation_time)
        print(f"Calculate after cache reset executed in {reset_calculation_time:.3f} seconds")
        
        # Print performance summary
        if len(execution_times) >= 3:
            print("\n= Performance Summary =")
            print(f"First calculation:   {execution_times[0]:.3f} seconds")
            print(f"With cached data:    {execution_times[1]:.3f} seconds")
            print(f"After cache reset:   {execution_times[2]:.3f} seconds")
            
            if execution_times[0] > 0 and execution_times[1] > 0:
                speedup = (execution_times[0] - execution_times[1]) / execution_times[0] * 100
                print(f"Caching improvement: {speedup:.1f}%")
        
        # Save results to file if requested
        if save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sentiment_test_{symbol}_{timestamp}.json"
            
            # Prepare data for saving (converting DataFrames to lists)
            save_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'sentiment_score': float(result['score']),
                'components': {k: float(v) for k, v in result.get('components', {}).items()},
                'interpretation': result.get('interpretation', {}),
                'signals': signals
            }
            
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)
            print(f"\nResults saved to {filename}")
        
        print("\n= Test completed successfully =")
        return True
        
    except Exception as e:
        print(f"Error in test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Test sentiment indicators with live data')
    parser.add_argument('--symbol', '-s', type=str, default='BTCUSDT', 
                        help='Trading pair symbol to test (default: BTCUSDT)')
    parser.add_argument('--testnet', '-t', action='store_true',
                        help='Use Bybit testnet instead of mainnet')
    parser.add_argument('--save', action='store_true',
                        help='Save test results to a JSON file')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
    
    # Run the test with provided arguments - use asyncio.run to execute the async function
    import asyncio
    asyncio.run(test_sentiment_indicators(args.symbol, args.testnet, args.save)) 