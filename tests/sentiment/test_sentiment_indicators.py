#!/usr/bin/env python3
import sys
import os
import json
import pandas as pd
import numpy as np
import time
import logging
import asyncio
from typing import Dict, Any, List
import traceback
import requests

# Add the src directory to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import the SentimentIndicators class
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Use the custom Logger class
logger = Logger("sentiment_test")

# Default configuration for sentiment indicators
DEFAULT_CONFIG = {
    "analysis": {
        "indicators": {
            "sentiment": {
                "parameters": {
                    "sigmoid_transformation": {
                        "default_sensitivity": 0.12,
                        "long_short_sensitivity": 0.12,
                        "funding_sensitivity": 0.15,
                        "liquidation_sensitivity": 0.10
                    }
                }
            }
        }
    },
    "timeframes": {
        "base": {
            "interval": 1,
            "validation": {
                "min_candles": 100
            },
            "weight": 0.4
        },
        "ltf": {
            "interval": 5,
            "validation": {
                "min_candles": 100
            },
            "weight": 0.3
        },
        "mtf": {
            "interval": 30,
            "validation": {
                "min_candles": 100
            },
            "weight": 0.2
        },
        "htf": {
            "interval": 240,
            "validation": {
                "min_candles": 100
            },
            "weight": 0.1
        }
    }
}

class BybitDataFetcher:
    """Simple class to fetch data from Bybit API"""
    
    BASE_URL = "https://api.bybit.com"
    
    def fetch_kline_data(self, symbol='BTCUSDT', interval='1', limit=1000):
        """Fetch OHLCV data"""
        endpoint = f"/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['retCode'] != 0:
            logger.error(f"Error fetching kline data: {data['retMsg']}")
            return pd.DataFrame()
        
        # Convert to dataframe
        df = pd.DataFrame(data['result']['list'], 
                          columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        
        # Convert types
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = pd.to_numeric(df[col])
        
        df['timestamp'] = pd.to_numeric(df['timestamp'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Reverse order to get ascending timestamps
        df = df.iloc[::-1].reset_index(drop=True)
        
        return df
    
    def fetch_ticker(self, symbol='BTCUSDT'):
        """Fetch ticker data"""
        endpoint = f"/v5/market/tickers"
        params = {
            "category": "linear",
            "symbol": symbol
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['retCode'] != 0:
            logger.error(f"Error fetching ticker data: {data['retMsg']}")
            return {}
        
        # Process ticker data
        ticker_data = data['result']['list'][0]
        processed_ticker = {
            'symbol': ticker_data['symbol'],
            'timestamp': int(time.time() * 1000),
            'datetime': pd.Timestamp.now().isoformat(),
            'high': float(ticker_data['highPrice24h']),
            'low': float(ticker_data['lowPrice24h']),
            'bid': float(ticker_data['bid1Price']),
            'ask': float(ticker_data['ask1Price']),
            'last': float(ticker_data['lastPrice']),
            'volume': float(ticker_data['volume24h']),
            'turnover': float(ticker_data['turnover24h']),
            'mark': float(ticker_data['markPrice']),
            'index': float(ticker_data['indexPrice']),
            'percentage': float(ticker_data['price24hPcnt']),
            'bid_size': float(ticker_data['bid1Size']),
            'ask_size': float(ticker_data['ask1Size']),
            'open_interest': float(ticker_data['openInterest']),
            'open_interest_value': float(ticker_data['openInterestValue']),
            'openInterest': float(ticker_data['openInterest']),
            'openInterestValue': float(ticker_data['openInterestValue']),
            'fundingRate': float(ticker_data['fundingRate']),
            'nextFundingTime': int(ticker_data['nextFundingTime']),
            'raw_data': ticker_data
        }
        
        return processed_ticker
    
    def fetch_funding_rate(self, symbol='BTCUSDT'):
        """Fetch funding rate"""
        endpoint = f"/v5/market/funding/history"
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": 1
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['retCode'] != 0:
            logger.error(f"Error fetching funding rate: {data['retMsg']}")
            return {}
        
        funding_data = {}
        if len(data['result']['list']) > 0:
            entry = data['result']['list'][0]
            funding_data = {
                'rate': float(entry['fundingRate']),
                'next_funding_time': int(time.time() * 1000) + 8 * 3600 * 1000  # 8 hours in the future
            }
        
        return funding_data
    
    def create_mock_long_short_ratio(self):
        """Create mock long/short ratio data since free API doesn't provide it"""
        # Generate slightly bullish bias with random component
        long_pct = 0.53 + (np.random.random() * 0.05)
        short_pct = 1 - long_pct
        
        return {
            'symbol': 'BTCUSDT',
            'long': long_pct,
            'short': short_pct,
            'timestamp': int(time.time() * 1000)
        }
    
    def prepare_market_data(self, symbol='BTCUSDT'):
        """Prepare complete market data for sentiment analysis"""
        # Fetch OHLCV data for different timeframes
        logger.info(f"Fetching OHLCV data for {symbol}...")
        ohlcv = {
            'base': self.fetch_kline_data(symbol, '1', 1000),
            'ltf': self.fetch_kline_data(symbol, '5', 200),
            'mtf': self.fetch_kline_data(symbol, '30', 200),
            'htf': self.fetch_kline_data(symbol, '240', 200)
        }
        
        # Fetch ticker data
        logger.info(f"Fetching ticker data for {symbol}...")
        ticker = self.fetch_ticker(symbol)
        
        # Fetch funding rate
        logger.info(f"Fetching funding rate for {symbol}...")
        funding_rate = self.fetch_funding_rate(symbol)
        
        # Create mock long/short ratio
        logger.info(f"Creating mock long/short ratio...")
        lsr = self.create_mock_long_short_ratio()
        
        # Calculate previous open interest for change calculation
        # Just a slight drop to test the calculation
        prev_oi = float(ticker['openInterest']) * 0.98
        
        # Build sentiment data
        sentiment_data = {
            'funding_rate': funding_rate,
            'long_short_ratio': lsr,
            'liquidations': [],  # Empty for this test
            'open_interest': {
                'value': float(ticker['openInterest']),
                'previous': prev_oi,
                'change_24h': ((float(ticker['openInterest']) / prev_oi) - 1) * 100,
                'timestamp': int(time.time() * 1000)
            }
        }
        
        # Add volume change calculation if not present in ticker
        if 'volume_change_24h' not in ticker:
            # Mock a slight increase in volume
            ticker['volume_change_24h'] = 2.5  # 2.5% increase
        
        # Combine all data
        market_data = {
            'symbol': symbol,
            'exchange': 'bybit',
            'timestamp': int(time.time() * 1000),
            'ohlcv': ohlcv,
            'ticker': ticker,
            'sentiment': sentiment_data
        }
        
        return market_data

async def test_sentiment_indicators():
    """Test sentiment indicators with live data"""
    try:
        # Initialize the data fetcher
        fetcher = BybitDataFetcher()
        
        # Fetch data
        market_data = fetcher.prepare_market_data('BTCUSDT')
        
        # Initialize sentiment indicators
        logger.info("Initializing sentiment indicators...")
        sentiment = SentimentIndicators(DEFAULT_CONFIG, logger)
        
        # Calculate sentiment
        logger.info("Calculating sentiment...")
        result = await sentiment.calculate(market_data)
        
        # Print results
        print("\n" + "="*80)
        print(" SENTIMENT ANALYSIS RESULTS ".center(80, '='))
        print("="*80)
        print(f"Overall Score: {result['score']:.2f}")
        print("-"*80)
        print(" Component Scores ".center(80, '-'))
        
        # Print component scores
        components = result['components']
        for component, score in sorted(components.items()):
            if component != 'sentiment':  # Skip the overall sentiment score
                # Add weight information if available
                weight = sentiment.component_weights.get(component, 0)
                weighted_score = score * weight
                print(f"{component:20}: {score:6.2f} × {weight:.2f} = {weighted_score:.2f}")
        
        print("-"*80)
        print(" Interpretations ".center(80, '-'))
        
        # Print interpretations
        if 'interpretation' in result:
            for key, interpretation in result['interpretation'].items():
                print(f"{key:20}: {interpretation}")
        
        print("-"*80)
        print(" Generated Signals ".center(80, '-'))
        
        # Print signals
        if 'signals' in result:
            for signal in result['signals']:
                direction = signal.get('direction', 'NEUTRAL')
                strength = signal.get('strength', 0)
                description = signal.get('description', 'No description')
                source = signal.get('source', 'unknown')
                print(f"[{direction}] ({strength:.1f}%) {description} (source: {source})")
        
        print("="*80)
        
        # Focus on market_activity component
        print("\n" + "="*80)
        print(" MARKET ACTIVITY COMPONENT DETAILS ".center(80, '='))
        print("="*80)
        
        market_activity_score = components.get('market_activity', 'N/A')
        print(f"Market Activity Score: {market_activity_score}")
        
        # Breakdown of what went into the market activity calculation
        ticker_data = market_data.get('ticker', {})
        sentiment_data = market_data.get('sentiment', {})
        
        print(f"Volume: {ticker_data.get('volume', 'N/A')}")
        print(f"Volume Change (24h): {ticker_data.get('volume_change_24h', 'N/A')}%")
        
        oi_data = sentiment_data.get('open_interest', {})
        if isinstance(oi_data, dict):
            print(f"Open Interest: {oi_data.get('value', 'N/A')}")
            print(f"OI Change (24h): {oi_data.get('change_24h', 'N/A')}%")
        
        print(f"Price Change (24h): {ticker_data.get('percentage', 'N/A') * 100}%")
        
        print("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing sentiment indicators: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run the test
    logger.info("Starting sentiment indicators test...")
    result = asyncio.run(test_sentiment_indicators())
    logger.info("Test completed.") 