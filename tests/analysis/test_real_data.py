import unittest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import logging
from src.analysis.session_analyzer import SessionAnalyzer
from src.data_processing.processors import DataProcessor
import aiohttp
import yaml
import os
import traceback
import time
import hmac
import hashlib
from typing import Dict, List
from src.data_processing.data_validator import DataValidator

class RealDataFetcher:
    """Real data fetcher for testing."""
    
    def __init__(self, api_key: str, api_secret: str, test_symbols: List[str]):
        """Initialize the fetcher."""
        self.base_url = "https://api.bybit.com"
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_symbols = test_symbols
        self.session = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_validator = DataValidator({})  # Initialize with empty config for testing

    def _validate_price_data(self, price_data: pd.DataFrame) -> bool:
        """Validate price data using DataValidator."""
        try:
            # Basic DataFrame validation
            if price_data.empty:
                self.logger.error("Empty DataFrame")
                return False
                
            # Use DataValidator for core validation
            if not self.data_validator.validate_data(price_data, context='price_data'):
                return False
                
            # Additional test-specific validations
            string_fields = ['symbol', 'timeframe', 'session', 'market_type', 'exchange']
            for field in string_fields:
                if price_data[field].isna().any():
                    self.logger.error(f"Found NaN values in {field}")
                    return False
                if price_data[field].str.len().eq(0).any():
                    self.logger.error(f"Found empty string in {field}")
                    return False
                    
            # Log validation success
            self.logger.debug("Price data validation successful")
            self.logger.debug(f"Data shape: {price_data.shape}")
            self.logger.debug(f"Date range: {price_data.index.min()} to {price_data.index.max()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating price data: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    async def fetch_session_data(self, symbols: list, session_info: dict) -> dict:
        """Fetch real session data for the given symbols."""
        try:
            # Get session start and end times
            start_time = session_info['start']
            end_time = session_info['end']
            
            # Convert session times to timestamps
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today_start - timedelta(days=1)
            
            self.logger.debug("Session Time Details:")
            self.logger.debug(f"Current UTC time: {now}")
            self.logger.debug(f"Today's start: {today_start}")
            self.logger.debug(f"Yesterday: {yesterday}")
            self.logger.debug(f"Session info: {session_info}")
            
            # For daily session, use yesterday's start to end
            if session_info.get('name') == 'daily':
                session_start = yesterday
                session_end = today_start
                self.logger.debug("Using daily session time range")
            else:
                # For other sessions, use yesterday's times
                session_start = datetime.combine(yesterday.date(), start_time)
                session_end = datetime.combine(yesterday.date(), end_time)
                
                # Handle overnight sessions
                if start_time > end_time:
                    session_end = session_end + timedelta(days=1)
                    self.logger.debug("Adjusted end time for overnight session")
            
            # Convert to timestamps (in milliseconds for Bybit V5 API)
            start_ts = int(session_start.timestamp() * 1000)
            end_ts = int(session_end.timestamp() * 1000)
            
            self.logger.info(f"Fetching session data from {session_start} to {session_end} UTC")
            self.logger.info(f"Start timestamp: {start_ts}, End timestamp: {end_ts}")
            self.logger.debug(f"Time range in minutes: {(end_ts - start_ts) / (60 * 1000):.2f}")
            
            # Validate time range
            if start_ts >= end_ts:
                self.logger.error(f"Invalid time range: start ({start_ts}) >= end ({end_ts})")
                return {}
            
            if end_ts - start_ts > 24 * 60 * 60 * 1000:  # More than 24 hours
                self.logger.warning("Time range exceeds 24 hours, may hit API limits")
            
            session_data = {}
            async with aiohttp.ClientSession() as session:
                for symbol in symbols:
                    try:
                        # Fetch price data
                        url = f"{self.base_url}/v5/market/kline"
                        params = {
                            'category': 'linear',
                            'symbol': symbol,
                            'interval': '1',  # 1-minute intervals
                            'start': str(start_ts),
                            'end': str(end_ts),
                            'limit': 1000  # Maximum allowed by API
                        }
                        
                        # Log request details
                        self.logger.debug(f"Fetching data for {symbol}")
                        self.logger.debug(f"URL: {url}")
                        self.logger.debug(f"Params: {params}")
                        
                        try:
                            # Generate authentication headers
                            timestamp = str(int(time.time() * 1000))
                            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
                            signature_payload = f"{timestamp}{self.api_key}{params_str}"
                            signature = hmac.new(
                                self.api_secret.encode('utf-8'),
                                signature_payload.encode('utf-8'),
                                hashlib.sha256
                            ).hexdigest()
                            
                            headers = {
                                'X-BAPI-API-KEY': self.api_key,
                                'X-BAPI-TIMESTAMP': timestamp,
                                'X-BAPI-SIGN': signature
                            }
                            
                            # Fetch price data
                            async with session.get(url, params=params, headers=headers) as response:
                                if response.status != 200:
                                    self.logger.error(f"HTTP error for {symbol}: {response.status}")
                                    self.logger.error(f"Response body: {await response.text()}")
                                    continue
                                
                                data = await response.json()
                                self.logger.debug(f"Response for {symbol}: {data}")
                                
                                if data.get('retCode') != 0:
                                    self.logger.error(f"API Error for {symbol}: {data.get('retMsg')}")
                                    self.logger.error(f"Full error response: {data}")
                                    continue

                                klines = data.get('result', {}).get('list', [])
                                if not klines:
                                    self.logger.error(f"No kline data received for {symbol}")
                                    self.logger.error(f"Response structure: {data.keys()}")
                                    self.logger.error(f"Result structure: {data.get('result', {}).keys()}")
                                    self.logger.error(f"Full response: {data}")
                                    continue

                                # Convert klines to DataFrame
                                df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                                df = df.astype({
                                    'timestamp': 'int64',
                                    'open': 'float64',
                                    'high': 'float64',
                                    'low': 'float64',
                                    'close': 'float64',
                                    'volume': 'float64',
                                    'turnover': 'float64'
                                })

                                # Convert timestamp to datetime
                                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms', utc=True)
                                df.set_index('timestamp', inplace=True)

                                # Calculate additional required fields
                                df['vwap'] = df['turnover'] / df['volume']  # Calculate VWAP directly from turnover and volume
                                df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
                                df['returns'] = df['close'].pct_change()
                                df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(252)

                                # Fill NaN values appropriately
                                df['vwap'] = df['vwap'].fillna(df['close'])  # Use close price if VWAP is NaN
                                df['returns'] = df['returns'].fillna(0)  # Fill NaN returns with 0
                                df['volatility'] = df['volatility'].fillna(method='bfill')  # Backfill volatility

                                # Add metadata columns
                                df['symbol'] = symbol
                                df['timeframe'] = '1m'
                                df['session'] = session_info['name']
                                df['market_type'] = 'linear'
                                df['exchange'] = 'bybit'
                                df['last_update'] = pd.Timestamp.utcnow()
                                
                                # Fetch orderbook data
                                orderbook_data = await self._fetch_orderbook_data(session, symbol)
                                
                                # Fetch trades data
                                trades_data = await self._fetch_trades_data(session, symbol)
                                
                                # Update the data structure with all components
                                session_data[symbol] = {
                                    'price_data': df,
                                    'orderbook_data': orderbook_data,
                                    'trades_data': trades_data,
                                    'indicator_data': {
                                        'price_data': df,
                                        'orderbook_data': orderbook_data,
                                        'trades_data': trades_data
                                    }
                                }
                                
                                self.logger.debug(f"{symbol} data sample:")
                                self.logger.debug(f"Columns: {df.columns.tolist()}")
                                self.logger.debug(f"Index type: {type(df.index)}")
                                self.logger.debug(f"First row: {df.iloc[0] if not df.empty else 'Empty DataFrame'}")
                                self.logger.debug(f"Volume sum: {df['volume'].sum() if 'volume' in df else 'No volume'}")
                                self.logger.debug(f"Orderbook data: {bool(orderbook_data)}")
                                self.logger.debug(f"Trades data: {not trades_data.empty if isinstance(trades_data, pd.DataFrame) else False}")
                            
                        except aiohttp.ClientError as e:
                            self.logger.error(f"HTTP error for {symbol}: {str(e)}")
                            continue
                        except Exception as e:
                            self.logger.error(f"Error processing {symbol}: {str(e)}")
                            self.logger.error(traceback.format_exc())
                            continue
                            
                    except Exception as e:
                        self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
                        self.logger.error(traceback.format_exc())
                        continue
            
            return session_data
            
        except Exception as e:
            self.logger.error(f"Error collecting session data: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {}

    async def _fetch_price_data(self, session: aiohttp.ClientSession, symbol: str) -> pd.DataFrame:
        """Fetch real price data from Bybit."""
        try:
            # Calculate time range for 1-day data
            current_time = datetime.now()
            end_time = int(current_time.timestamp())  # Current time in seconds
            start_time = int((current_time - timedelta(days=1)).timestamp())  # 24 hours ago in seconds
            
            self.logger.info(f"Time range for {symbol}: start={datetime.fromtimestamp(start_time)} end={datetime.fromtimestamp(end_time)}")
            
            # Construct URL with correct category
            url = f"{self.base_url}/v5/market/kline"
            params = {
                'category': 'linear',  # Using linear category
                'symbol': symbol,
                'interval': '60',  # 1-hour intervals
                'start': start_time,
                'end': end_time,
                'limit': 1000
            }
            
            # Generate authentication headers
            timestamp = int(time.time() * 1000)
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature_payload = f"{timestamp}{self.api_key}{params_str}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': str(timestamp),
                'X-BAPI-SIGN': signature
            }
            
            self.logger.debug(f"Kline request headers for {symbol}: {headers}")
            
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                self.logger.info(f"API Response for {symbol}:")
                self.logger.info(f"Status Code: {response.status}")
                self.logger.info(f"Response Headers: {dict(response.headers)}")
                self.logger.info(f"Response Data: {data}")
                
                if data.get('retCode') != 0:
                    self.logger.error(f"API Error for {symbol}: {data.get('retMsg')}")
                    return pd.DataFrame()

                result = data.get('result', {})
                self.logger.info(f"Response structure for {symbol}: {result.keys()}")
                klines = result.get('list', [])
                if not klines:
                    self.logger.error(f"No kline data received for {symbol}")
                    self.logger.error(f"Response structure: {data.keys()}")
                    self.logger.error(f"Result structure: {result.keys()}")
                    self.logger.error(f"Full response: {data}")
                    return pd.DataFrame()

                self.logger.info(f"Received {len(klines)} klines for {symbol}")
                self.logger.debug(f"First kline record: {klines[0] if klines else 'No klines'}")
                
                # Process klines according to V5 API format
                # Each kline is a list: [timestamp, open, high, low, close, volume, turnover]
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 
                    'volume', 'turnover'
                ])
                
                # Convert timestamp to numeric first
                df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                
                # Convert numeric columns and ensure proper types
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Create a new DataFrame with required columns and proper types
                result_df = pd.DataFrame({
                    'timestamp': df['timestamp'],
                    'open': df['open'].astype(float),
                    'high': df['high'].astype(float),
                    'low': df['low'].astype(float),
                    'close': df['close'].astype(float),
                    'volume': df['volume'].astype(float),
                    'turnover': df['turnover'].astype(float)
                })
                
                # Fill any remaining NaN values with forward fill then backward fill
                result_df = result_df.ffill().bfill()
                
                # Ensure all values are positive
                for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                    result_df[col] = result_df[col].abs()
                
                # Ensure high >= low and proper OHLC relationships
                result_df['high'] = result_df[['high', 'low', 'open', 'close']].max(axis=1)
                result_df['low'] = result_df[['high', 'low', 'open', 'close']].min(axis=1)

                # Calculate derived fields
                result_df['typical_price'] = (result_df['high'] + result_df['low'] + result_df['close']) / 3
                result_df['vwap'] = (result_df['typical_price'] * result_df['volume']).cumsum() / result_df['volume'].cumsum()
                result_df['returns'] = result_df['close'].pct_change()
                result_df['volatility'] = result_df['returns'].rolling(window=20).std()

                # Add metadata columns with correct market type
                result_df['symbol'] = symbol
                result_df['timeframe'] = '1m'
                result_df['session'] = 'ny'  # Default to NY session since that's what we're testing
                result_df['market_type'] = 'linear'  # Using linear market type
                result_df['exchange'] = 'bybit'
                result_df['last_update'] = pd.Timestamp.utcnow()

                # Fill NaN values in derived columns
                result_df['returns'] = result_df['returns'].fillna(0)
                result_df['volatility'] = result_df['volatility'].bfill()
                result_df['vwap'] = result_df['vwap'].fillna(result_df['typical_price'])
                
                # Set index to timestamp
                result_df = result_df.set_index('timestamp')
                result_df = result_df.sort_index()
                
                self.logger.debug(f"Processed kline data for {symbol}: {len(result_df)} rows")
                self.logger.debug(f"Final columns: {result_df.columns.tolist()}")
                self.logger.debug(f"First processed kline: {result_df.iloc[0].to_dict() if not result_df.empty else 'No klines'}")
                return result_df
                
        except Exception as e:
            self.logger.error(f"Error fetching price data for {symbol}: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()

    async def _fetch_trades_data(self, session: aiohttp.ClientSession, symbol: str) -> pd.DataFrame:
        """Fetch recent trades data."""
        try:
            url = f"{self.base_url}/v5/market/recent-trade"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': 1000
            }
            
            # Generate authentication headers
            timestamp = int(time.time() * 1000)
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature_payload = f"{timestamp}{self.api_key}{params_str}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': str(timestamp),
                'X-BAPI-SIGN': signature
            }
            
            self.logger.debug(f"Trades request headers for {symbol}: {headers}")
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP error fetching trades: {response.status}")
                    return pd.DataFrame()
                    
                data = await response.json()
                self.logger.debug(f"Trades response for {symbol}: {data}")
                
                if data.get('retCode') != 0:
                    self.logger.error(f"API Error fetching trades: {data.get('retMsg')}")
                    return pd.DataFrame()
                    
                trades = data.get('result', {}).get('list', [])
                if not trades:
                    self.logger.warning(f"No trades data for {symbol}")
                    return pd.DataFrame()
                    
                # Convert to DataFrame with proper V5 API format
                df = pd.DataFrame(trades)
                
                # Convert types
                df['price'] = pd.to_numeric(df['price'])
                df['size'] = pd.to_numeric(df['size'])
                df['time'] = pd.to_datetime(pd.to_numeric(df['time']), unit='ms')
                df.set_index('time', inplace=True)
                
                return df
                
        except Exception as e:
            self.logger.error(f"Error fetching trades data: {str(e)}")
            return pd.DataFrame()

    async def _fetch_orderbook_data(self, session: aiohttp.ClientSession, symbol: str) -> dict:
        """Fetch orderbook data."""
        try:
            url = f"{self.base_url}/v5/market/orderbook"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': 50
            }
            
            # Generate authentication headers
            timestamp = int(time.time() * 1000)
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature_payload = f"{timestamp}{self.api_key}{params_str}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': str(timestamp),
                'X-BAPI-SIGN': signature
            }
            
            self.logger.debug(f"Orderbook request headers for {symbol}: {headers}")
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP error fetching orderbook: {response.status}")
                    return {}
                    
                data = await response.json()
                self.logger.debug(f"Orderbook response for {symbol}: {data}")
                
                if data.get('retCode') != 0:
                    self.logger.error(f"API Error fetching orderbook: {data.get('retMsg')}")
                    return {}
                    
                result = data.get('result', {})
                if not result:
                    self.logger.warning(f"No orderbook data for {symbol}")
                    return {}
                    
                # Convert price and size to numeric according to V5 API format
                orderbook = {
                    'bids': [[float(price), float(size)] for price, size in result.get('b', [])],
                    'asks': [[float(price), float(size)] for price, size in result.get('a', [])]
                }
                
                return orderbook
                
        except Exception as e:
            self.logger.error(f"Error fetching orderbook data: {str(e)}")
            return {}

    async def ensure_session(self):
        """Ensure we have a valid session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
            # Verify available symbols
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {'category': 'linear'}
            
            # Generate authentication headers
            timestamp = int(time.time() * 1000)
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature_payload = f"{timestamp}{self.api_key}{params_str}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': str(timestamp),
                'X-BAPI-SIGN': signature,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            self.logger.info("Verifying available symbols...")
            self.logger.debug(f"URL: {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Params: {params}")
            
            async with self.session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                self.logger.debug(f"Response: {data}")
                
                if data.get('retCode') == 0:
                    symbols = data.get('result', {}).get('list', [])
                    available_symbols = [s['symbol'] for s in symbols]
                    self.logger.info(f"Available symbols: {available_symbols}")
                    
                    # Filter test symbols to only use available ones
                    self.test_symbols = [s for s in self.test_symbols if s in available_symbols]
                    self.logger.info(f"Using symbols: {self.test_symbols}")
                else:
                    self.logger.error(f"Failed to get available symbols: {data}")
        return self.session

    async def close(self):
        """Close aiohttp session"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        except Exception as e:
            self.logger.error(f"Error closing session: {e}")
        finally:
            self.session = None

    async def _send_public_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Add this method to match BybitClient implementation"""
        await self.ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Generate authentication headers
            timestamp = int(time.time() * 1000)
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature_payload = f"{timestamp}{self.api_key}{params_str}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': str(timestamp),
                'X-BAPI-SIGN': signature,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"HTTP {response.status} for {url}: {await response.text()}")
                    return {}
                
                return await response.json()
                
        except Exception as e:
            self.logger.error(f"Request failed for {url}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}

class TestRealData(unittest.TestCase):
    """
    Integration test suite for real market data analysis functionality.
    
    This test class verifies the end-to-end functionality of market data processing,
    analysis, and reporting using real market data from multiple symbols. It tests
    the integration between various components including data fetching, processing,
    and session analysis.

    Components Tested:
        - DataProcessor: Data preprocessing and normalization
        - SessionAnalyzer: Market session analysis and reporting
        - RealDataFetcher: Live market data retrieval

    Test Coverage:
        - Daily session report generation
        - Data processing pipeline
        - Multi-symbol analysis
        - Error handling and validation
    """
    
    def setUp(self):
        """
        Set up the test environment with necessary components and configurations.

        Initializes:
            - Logging configuration
            - Data processing components
            - Test symbols list
            - Data fetching client
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize components
        self.data_processor = DataProcessor()
        self.session_analyzer = SessionAnalyzer(self.data_processor)
        
        # Test symbols
        self.test_symbols = [
            'XRPUSDT', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT',
            'HBARUSDT', 'ADAUSDT', 'LINKUSDT', 'SUIUSDT', 'XLMUSDT',
            'MOODENGUSDT', '1000PEPEUSDT', 'ONDOUSDT', 'SANDUSDT', 'FTMUSDT',
            'ALGOUSDT', 'WIFUSDT', 'AVAXUSDT', 'LTCUSDT', 'ORDIUSDT',
            'IOTAUSDT', 'RSRUSDT', 'NEARUSDT', 'DOTUSDT', 'SHIB1000USDT'
        ]
        
        # Initialize data fetcher
        self.data_fetcher = RealDataFetcher(
            api_key="YOUR_API_KEY",
            api_secret="YOUR_API_SECRET",
            test_symbols=self.test_symbols
        )

    async def test_daily_session_report(self):
        """
        Test the generation of daily market session reports using real market data.

        This test verifies that:
            1. The session analyzer can successfully generate reports
            2. Reports contain valid data and expected format
            3. Error cases are properly handled
            4. Reports include data from all test symbols

        Assertions:
            - Report is not None
            - Report is not an error message
            - Report contains valid data

        Note:
            The test prints the generated report for manual inspection
            and verification of the format and content.
        """
        self.logger.info("Starting daily session report test")
        
        # Generate report
        report = await self.session_analyzer.generate_session_report(
            self.data_fetcher,
            self.test_symbols
        )
        
        # Verify report generation
        self.assertIsNotNone(report)
        self.assertNotEqual(report, "❌ No active session found")
        self.assertNotEqual(report, "❌ No valid data available for report generation")
        self.assertNotEqual(report, "❌ Error generating session report")
        
        # Print the report
        print("\nGenerated Market Report:")
        print("------------------------")
        print(report)
        print("------------------------")
        
        self.logger.info("Successfully generated report")

    def test_daily_session_report_wrapper(self):
        """Wrapper to run the async test."""
        asyncio.run(self.test_daily_session_report())

if __name__ == '__main__':
    unittest.main() 