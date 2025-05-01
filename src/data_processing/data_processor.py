# data_processor.py

"""Data processing module.

This module provides functionality for processing market data:
- Data normalization
- Data validation
- Data transformation
- Data enrichment
- Out-of-order data handling
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import time
from collections import deque, OrderedDict
import heapq

from src.core.validation import ValidationResult, ValidationContext
from .error_handler import SimpleErrorHandler
from src.core.error.models import ErrorContext, ErrorSeverity
from src.data.repositories import MarketRepository

class DataProcessor:
    """Centralized data processing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process all market data components."""
        try:
            processed_data = {
                'symbol': market_data['symbol'],
                'timestamp': market_data['timestamp'],
                'metadata': market_data.get('metadata', {})
            }
            
            # Process OHLCV data
            if 'ohlcv' in market_data:
                processed_data['ohlcv'] = await self.process_ohlcv(market_data['ohlcv'])
                
            # Process orderbook
            if 'orderbook' in market_data:
                processed_data['orderbook'] = await self.process_orderbook(market_data['orderbook'])
                
            # Process trades
            if 'trades' in market_data:
                processed_data['trades'] = await self.process_trades(market_data['trades'])
                
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            raise

    async def process_ohlcv(self, ohlcv_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Process OHLCV data for all timeframes."""
        try:
            processed_ohlcv = {}
            
            for timeframe, tf_data in ohlcv_data.items():
                if not isinstance(tf_data, dict) or 'data' not in tf_data:
                    continue
                    
                df = tf_data['data']
                if not isinstance(df, pd.DataFrame):
                    df = pd.DataFrame(df)
                    
                # Ensure numeric columns
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                # Sort by timestamp
                df = df.sort_values('timestamp')
                
                # Remove duplicates
                df = df.drop_duplicates(subset=['timestamp'])
                
                # Store processed DataFrame
                processed_ohlcv[timeframe] = {
                    'data': df,
                    'interval': tf_data.get('interval'),
                    'start': tf_data.get('start'),
                    'end': tf_data.get('end')
                }
                
            return processed_ohlcv
            
        except Exception as e:
            self.logger.error(f"Error processing OHLCV data: {str(e)}")
            raise

    async def process_orderbook(self, orderbook: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process orderbook data."""
        try:
            processed_book = {}
            
            for side in ['bids', 'asks']:
                if side not in orderbook:
                    continue
                    
                # Convert to DataFrame
                df = pd.DataFrame(orderbook[side], columns=['price', 'amount'])
                
                # Ensure numeric
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Sort appropriately
                df = df.sort_values('price', ascending=(side == 'bids'))
                
                # Remove invalid entries
                df = df.dropna()
                
                processed_book[side] = df
                
            return processed_book
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook: {str(e)}")
            raise

    async def process_trades(self, trades: List[Dict]) -> pd.DataFrame:
        """Process trade data."""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Standardize column names
            rename_map = {
                'p': 'price',
                'v': 'amount',
                'S': 'side',
                'T': 'timestamp',
                'i': 'trade_id'
            }
            df = df.rename(columns=rename_map)
            
            # Ensure required columns
            required_cols = ['timestamp', 'price', 'amount', 'side']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Missing required columns: {[col for col in required_cols if col not in df.columns]}")
                
            # Convert numeric columns
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            # Remove invalid trades
            df = df.dropna(subset=['price', 'amount'])
            
            # Standardize side
            df['side'] = df['side'].str.lower()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing trades: {str(e)}")
            raise

    def _standardize_timeframes(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize timeframe data structure."""
        try:
            standardized = {}
            
            for tf, data in ohlcv_data.items():
                if not isinstance(data, dict):
                    continue
                    
                standardized[tf] = {
                    'data': data.get('data', pd.DataFrame()),
                    'interval': data.get('interval'),
                    'start': data.get('start'),
                    'end': data.get('end')
                }
                
            return standardized
            
        except Exception as e:
            self.logger.error(f"Error standardizing timeframes: {str(e)}")
            raise

    TIMEFRAMES = {
        'base': '1',    # 1 minute
        'ltf': '5',     # 5 minutes
        'mtf': '30',    # 30 minutes
        'htf': '240'    # 4 hours
    }
    
    def __init__(
        self,
        config: Dict[str, Any],
        metrics_manager: Optional[Any] = None,
        alert_manager: Optional[Any] = None,
        error_handler: Optional[SimpleErrorHandler] = None,
        validation_service: Optional[Any] = None,
        market_repository: MarketRepository = None
    ):
        """Initialize data processor.
        
        Args:
            config: Configuration dictionary
            metrics_manager: Optional metrics manager instance
            alert_manager: Optional alert manager instance
            error_handler: Optional error handler instance
            validation_service: Optional validation service instance
            market_repository: Optional market repository instance
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        
        self.config = config
        self.metrics_manager = metrics_manager
        self.alert_manager = alert_manager
        self.error_handler = error_handler or SimpleErrorHandler()
        self.validation_service = validation_service
        self.market_repository = market_repository
        
        # Initialize processing state
        self._processing_task = None
        self._last_process_time = time.time()
        self._process_interval = config.get('process_interval', 1)
        
        # Initialize statistics
        self._stats = {
            'total_processed': 0,
            'invalid_data': 0,
            'processing_errors': 0,
            'last_process_time': None,
            'out_of_order_events': 0
        }
        
        # Initialize data buffers with timestamp ordering
        self._data_buffer = deque(maxlen=config.get('buffer_size', 1000))
        self._processed_data = OrderedDict()
        
        # Initialize out-of-order handling
        self._reorder_buffer_size = config.get('reorder_buffer_size', 1000)
        self._reorder_window_ms = config.get('reorder_window_ms', 5000)  # 5 second window
        self._reorder_buffers: Dict[str, List] = {}  # Symbol -> priority queue
        self._last_processed_timestamps: Dict[str, float] = {}  # Symbol -> timestamp
        
        # Initialize state for delta updates
        self._processed_data: Dict[str, Dict[str, Any]] = {}
        
        # Initialize timeframe weights from config
        self.timeframe_weights = {
            tf_name: tf_config['weight']
            for tf_name, tf_config in config['timeframes'].items()
        }
        
        # Initialize pipeline components
        self.pipeline = self._initialize_pipeline(config)
        
        self.logger.info("Data processor initialized with out-of-order handling")
        
    def _initialize_pipeline(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Initialize the data processing pipeline from configuration.
        
        Args:
            config: Configuration dictionary containing pipeline settings
            
        Returns:
            List of pipeline component configurations
        """
        pipeline_config = config.get('data_processing', {}).get('pipeline', [])
        if not pipeline_config:
            self.logger.warning("No pipeline configuration found, using default empty pipeline")
            return []
            
        self.logger.info(f"Initializing data processing pipeline with {len(pipeline_config)} components")
        return pipeline_config

    def _get_timestamp(self, data: Dict[str, Any]) -> float:
        """Extract timestamp from data in milliseconds."""
        ts = data.get('timestamp')
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp() * 1000
            except ValueError:
                return float(ts)
        return float(ts) if ts else time.time() * 1000

    async def handle_out_of_order(
        self,
        data: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Handle out-of-order data using a priority queue approach.
        
        Args:
            data: Market data
            symbol: Trading pair symbol
            
        Returns:
            Data when ready to be processed, None if buffered
        """
        timestamp = self._get_timestamp(data)
        
        # Initialize buffer for symbol if needed
        if symbol not in self._reorder_buffers:
            self._reorder_buffers[symbol] = []
            self._last_processed_timestamps[symbol] = timestamp
            
        last_ts = self._last_processed_timestamps[symbol]
        
        # If timestamp is too old, log and discard
        if timestamp < last_ts - self._reorder_window_ms:
            self.logger.warning(f"Discarding too old out-of-order data for {symbol}: {timestamp} < {last_ts}")
            self._stats['out_of_order_events'] += 1
            return None
            
        # If timestamp is in order, process immediately
        if timestamp >= last_ts:
            self._last_processed_timestamps[symbol] = timestamp
            return data
            
        # Buffer out-of-order data
        heapq.heappush(self._reorder_buffers[symbol], (timestamp, data))
        
        # Trim buffer if too large
        while len(self._reorder_buffers[symbol]) > self._reorder_buffer_size:
            _, oldest = heapq.heappop(self._reorder_buffers[symbol])
            self.logger.warning(f"Dropping oldest buffered data for {symbol} due to buffer overflow")
            
        return None

    async def process_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data with proper error handling."""
        try:
            self.logger.debug(f"Processing market data for {market_data.get('symbol')}")
            
            # Process trades if available
            trades = market_data.get('trades', [])
            if trades:
                try:
                    processed_trades = await self.process_trades(trades)
                    market_data['processed_trades'] = processed_trades
                except Exception as e:
                    self.logger.error(f"Error processing trades: {str(e)}")
                    market_data['processed_trades'] = pd.DataFrame()
            
            # Validate OHLCV data
            for timeframe in ['base', 'ltf', 'mtf', 'htf']:
                ohlcv = market_data.get('ohlcv', {}).get(timeframe)
                if not isinstance(ohlcv, pd.DataFrame) or ohlcv.empty:
                    self.logger.error(f"Missing or invalid {timeframe} OHLCV data")
                    market_data['ohlcv'][timeframe] = pd.DataFrame()
                    
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            return market_data

    def _validate_ohlcv_data(self, df: pd.DataFrame) -> bool:
        """Validate OHLCV DataFrame structure and content."""
        try:
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
            # Check columns exist
            if not all(col in df.columns for col in required_columns):
                self.logger.error(f"Missing required columns. Found: {df.columns}")
                return False
                
            # Check for empty DataFrame
            if df.empty:
                self.logger.error("Empty OHLCV DataFrame")
                return False
                
            # Check for numeric values
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if not pd.to_numeric(df[col], errors='coerce').notna().all():
                    self.logger.error(f"Non-numeric values found in {col} column")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating OHLCV data: {str(e)}")
            return False

    async def _process_trade(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process trade data."""
        self.logger.debug(f"Processing trade data: {data}")
        try:
            # Handle WebSocket format
            if 'data' in data and isinstance(data['data'], list):
                trade = data['data'][0]  # Get first trade
                return {
                    'price': float(trade.get('p', 0)),
                    'size': float(trade.get('v', 0)),
                    'side': trade.get('S', ''),
                    'trade_time': int(trade.get('T', 0)),
                    'trade_id': trade.get('i', ''),
                    'is_block_trade': trade.get('BT', False)
                }
            # Handle REST API format
            elif isinstance(data, dict):
                return {
                    'price': float(data.get('price', 0)),
                    'size': float(data.get('size', 0)),
                    'side': data.get('side', ''),
                    'trade_time': int(data.get('time', 0))
                }
            else:
                self.logger.warning(f"Unknown trade data format: {type(data)}")
                return None
        except Exception as e:
            self.logger.error(f"Error processing trade: {str(e)}")
            self.logger.debug(f"Failed trade data: {data}")
            return None
            
    async def _process_ticker(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process ticker data from Bybit API.
        
        Handles WebSocket formats:
        - snapshot: full ticker data
        - delta: partial updates
        And REST API format
        """
        self.logger.debug(f"Processing ticker data: {data}")
        try:
            # Extract ticker data based on format
            ticker_data = {}
            symbol = None
            
            # Handle WebSocket format
            if 'topic' in data:
                msg_type = data.get('type', '')
                if msg_type == 'snapshot':
                    ticker = data.get('data', {})
                    if isinstance(ticker, list):
                        ticker = ticker[0] if ticker else {}
                    symbol = ticker.get('symbol')
                    # For snapshot, use all fields
                    ticker_data = {
                        'lastPrice': float(ticker.get('lastPrice', 0)),
                        'indexPrice': float(ticker.get('indexPrice', 0)),
                        'markPrice': float(ticker.get('markPrice', 0)),
                        'prevPrice24h': float(ticker.get('prevPrice24h', 0)),
                        'price24hPcnt': float(ticker.get('price24hPcnt', 0)),
                        'highPrice24h': float(ticker.get('highPrice24h', 0)),
                        'lowPrice24h': float(ticker.get('lowPrice24h', 0)),
                        'prevPrice1h': float(ticker.get('prevPrice1h', 0)),
                        'openInterest': float(ticker.get('openInterest', 0)),
                        'openInterestValue': float(ticker.get('openInterestValue', 0)),
                        'turnover24h': float(ticker.get('turnover24h', 0)),
                        'volume24h': float(ticker.get('volume24h', 0)),
                        'fundingRate': float(ticker.get('fundingRate', 0)),
                        'nextFundingTime': int(ticker.get('nextFundingTime', 0)),
                        'bid1Price': float(ticker.get('bid1Price', 0)),
                        'bid1Size': float(ticker.get('bid1Size', 0)),
                        'ask1Price': float(ticker.get('ask1Price', 0)),
                        'ask1Size': float(ticker.get('ask1Size', 0)),
                        'tickDirection': ticker.get('tickDirection', '')  # String field, no conversion
                    }
                elif msg_type == 'delta':
                    # For delta updates, get existing state and update only changed fields
                    ticker = data.get('data', {})
                    symbol = ticker.get('symbol')
                    if symbol in self._processed_data:
                        ticker_data = self._processed_data[symbol].copy()
                    # Update only the fields that are present in the delta
                    for key, value in ticker.items():
                        if key not in ['symbol', 'type'] and value:
                            try:
                                if key == 'tickDirection':
                                    ticker_data[key] = value  # Store string value as is
                                elif key == 'nextFundingTime':
                                    ticker_data[key] = int(value)
                                else:
                                    ticker_data[key] = float(value)
                            except (ValueError, TypeError):
                                self.logger.warning(f"Could not convert value for {key}: {value}")
                                continue
            # Handle REST API format
            elif 'list' in data and data['list']:
                ticker = data['list'][0]
                symbol = ticker.get('symbol')
                ticker_data = {
                    'lastPrice': float(ticker.get('lastPrice', 0)),
                    'indexPrice': float(ticker.get('indexPrice', 0)),
                    'markPrice': float(ticker.get('markPrice', 0)),
                    'prevPrice24h': float(ticker.get('prevPrice24h', 0)),
                    'price24hPcnt': float(ticker.get('price24hPcnt', 0)),
                    'highPrice24h': float(ticker.get('highPrice24h', 0)),
                    'lowPrice24h': float(ticker.get('lowPrice24h', 0)),
                    'prevPrice1h': float(ticker.get('prevPrice1h', 0)),
                    'openInterest': float(ticker.get('openInterest', 0)),
                    'openInterestValue': float(ticker.get('openInterestValue', 0)),
                    'turnover24h': float(ticker.get('turnover24h', 0)),
                    'volume24h': float(ticker.get('volume24h', 0)),
                    'fundingRate': float(ticker.get('fundingRate', 0)),
                    'nextFundingTime': int(ticker.get('nextFundingTime', 0)),
                    'bid1Price': float(ticker.get('bid1Price', 0)),
                    'bid1Size': float(ticker.get('bid1Size', 0)),
                    'ask1Price': float(ticker.get('ask1Price', 0)),
                    'ask1Size': float(ticker.get('ask1Size', 0)),
                    'tickDirection': ticker.get('tickDirection', '')  # String field, no conversion
                }
            else:
                ticker = data
                symbol = ticker.get('symbol')
                ticker_data = {
                    'lastPrice': float(ticker.get('lastPrice', ticker.get('last_price', 0))),
                    'indexPrice': float(ticker.get('indexPrice', ticker.get('index_price', 0))),
                    'markPrice': float(ticker.get('markPrice', ticker.get('mark_price', 0))),
                    'prevPrice24h': float(ticker.get('prevPrice24h', ticker.get('prev_price_24h', 0))),
                    'price24hPcnt': float(ticker.get('price24hPcnt', ticker.get('price_24h_pcnt', 0))),
                    'highPrice24h': float(ticker.get('highPrice24h', ticker.get('high_price_24h', 0))),
                    'lowPrice24h': float(ticker.get('lowPrice24h', ticker.get('low_price_24h', 0))),
                    'prevPrice1h': float(ticker.get('prevPrice1h', ticker.get('prev_price_1h', 0))),
                    'openInterest': float(ticker.get('openInterest', ticker.get('open_interest', 0))),
                    'openInterestValue': float(ticker.get('openInterestValue', ticker.get('open_interest_value', 0))),
                    'turnover24h': float(ticker.get('turnover24h', ticker.get('turnover_24h', 0))),
                    'volume24h': float(ticker.get('volume24h', ticker.get('volume_24h', 0))),
                    'fundingRate': float(ticker.get('fundingRate', ticker.get('funding_rate', 0))),
                    'nextFundingTime': int(ticker.get('nextFundingTime', ticker.get('next_funding_time', 0))),
                    'bid1Price': float(ticker.get('bid1Price', ticker.get('bid1_price', 0))),
                    'bid1Size': float(ticker.get('bid1Size', ticker.get('bid1_size', 0))),
                    'ask1Price': float(ticker.get('ask1Price', ticker.get('ask1_price', 0))),
                    'ask1Size': float(ticker.get('ask1Size', ticker.get('ask1_size', 0))),
                    'tickDirection': ticker.get('tickDirection', ticker.get('tick_direction', ''))  # String field, no conversion
                }

            if not ticker_data or not symbol:
                self.logger.warning("Empty ticker data or missing symbol")
                return None

            # Create processed data with type and timestamp
            processed_data = {
                'type': 'ticker',
                'timestamp': int(time.time() * 1000),
                'symbol': symbol,
                **ticker_data
            }

            # Store processed data for future delta updates
            self._processed_data[symbol] = ticker_data

            self.logger.debug(f"Processed ticker data: {json.dumps(processed_data, indent=2)}")
            return processed_data

        except Exception as e:
            self.logger.error(f"Error processing ticker: {str(e)}")
            return None
            
    async def _process_orderbook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process orderbook data."""
        try:
            return {
                'bids': [[float(p), float(s)] for p, s in data.get('b', [])],
                'asks': [[float(p), float(s)] for p, s in data.get('a', [])],
                'timestamp': int(data.get('ts', 0))
            }
        except Exception as e:
            self.logger.error(f"Error processing orderbook: {str(e)}")
            return None
            
    async def _process_kline(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kline/candlestick data.
        
        Args:
            data: Raw kline data
            
        Returns:
            Processed kline data if successful, None otherwise
        """
        try:
            self.logger.debug(f"[KLINE FLOW] Processing kline data: {json.dumps(data, indent=2)}")
            
            # Handle REST API format (initial klines)
            if 'result' in data and 'list' in data['result']:
                klines = data['result']['list']
                timeframe = data.get('timeframe', 'base')
                self.logger.debug(f"[KLINE FLOW] Processing {len(klines)} REST API klines @ {timeframe}")
                
                processed_klines = []
                for kline in klines:
                    processed_kline = {
                        'timestamp': int(kline[0]),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                        'turnover': float(kline[6]),
                        'timeframe': timeframe,
                        'type': 'kline',
                        'symbol': data.get('symbol')
                    }
                    processed_klines.append(processed_kline)
                
                self.logger.debug(f"[KLINE FLOW] Processed {len(processed_klines)} REST API klines")
                if processed_klines:
                    self.logger.debug(f"[KLINE FLOW] First REST API kline: {json.dumps(processed_klines[0], indent=2)}")
                    self.logger.debug(f"[KLINE FLOW] Last REST API kline: {json.dumps(processed_klines[-1], indent=2)}")
                return processed_klines
                
            # Handle WebSocket format
            elif 'type' in data and data['type'] == 'kline':
                # Data is already processed by WebSocket handler
                self.logger.debug(f"[KLINE FLOW] Processing WebSocket kline @ {data.get('timeframe', 'base')}")
                return data
                
            # Handle raw WebSocket format
            elif 'data' in data:
                kline_data = data['data']
                if isinstance(kline_data, list):
                    kline_data = kline_data[0]  # Get first kline from list
                
                timeframe = data.get('timeframe', 'base')
                self.logger.debug(f"[KLINE FLOW] Processing raw WebSocket kline @ {timeframe}")
                
                processed_kline = {
                    'timestamp': int(kline_data.get('start', data.get('ts', 0))),
                    'open': float(kline_data.get('open', 0)),
                    'high': float(kline_data.get('high', 0)),
                    'low': float(kline_data.get('low', 0)),
                    'close': float(kline_data.get('close', 0)),
                    'volume': float(kline_data.get('volume', 0)),
                    'turnover': float(kline_data.get('turnover', 0)),
                    'timeframe': timeframe,
                    'type': 'kline',
                    'symbol': data.get('symbol')
                }
                
                self.logger.debug(f"[KLINE FLOW] Processed WebSocket kline: {json.dumps(processed_kline, indent=2)}")
                return processed_kline
                
            else:
                self.logger.warning(f"[KLINE FLOW] Unknown kline data format")
                self.logger.debug(f"[KLINE FLOW] Raw data: {json.dumps(data, indent=2)}")
                return None
            
        except Exception as e:
            self.logger.error(f"[KLINE FLOW] Error processing kline data: {str(e)}")
            self.logger.debug(f"[KLINE FLOW] Failed raw kline data: {json.dumps(data, indent=2)}")
            return None
            
    async def _process_funding(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process funding data."""
        self.logger.debug(f"Processing funding data: {data}")
        try:
            return {
                'funding_rate': float(data.get('fundingRate', 0)),
                'funding_time': int(data.get('fundingRateTimestamp', 0)),
                'next_funding_time': int(data.get('nextFundingTime', 0)),
                'predicted_funding_rate': float(data.get('predictedFundingRate', 0))
            }
        except Exception as e:
            self.logger.error(f"Error processing funding: {str(e)}")
            return None
            
    async def _process_open_interest(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process open interest data."""
        self.logger.debug(f"Processing open interest data: {data}")
        try:
            return {
                'open_interest': float(data.get('openInterest', 0)),
                'open_interest_value': float(data.get('openInterestValue', 0)),
                'timestamp': int(data.get('timestamp', time.time() * 1000))
            }
        except Exception as e:
            self.logger.error(f"Error processing open interest: {str(e)}")
            return None
            
    async def _process_ratio(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process long/short ratio data."""
        self.logger.debug(f"Processing ratio data: {data}")
        try:
            return {
                'buy_ratio': float(data.get('buyRatio', 0)),
                'sell_ratio': float(data.get('sellRatio', 0)),
                'timestamp': int(data.get('timestamp', time.time() * 1000))
            }
        except Exception as e:
            self.logger.error(f"Error processing ratio: {str(e)}")
            return None
            
    async def _process_long_short_ratio(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process long/short ratio data."""
        try:
            if not data or 'list' not in data or not data['list']:
                self.logger.warning("Invalid long/short ratio data format")
                return None
            
            # Get latest data point
            latest = data['list'][0]
            return {
                'buy_ratio': float(latest.get('buyRatio', 0.5)),
                'sell_ratio': float(latest.get('sellRatio', 0.5)),
                'timestamp': int(latest.get('timestamp', time.time() * 1000))
            }
        except Exception as e:
            self.logger.error(f"Error processing long/short ratio data: {str(e)}")
            return None

    async def _process_funding_rate(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process funding rate data."""
        try:
            if not data or 'rate' not in data:
                self.logger.warning("Invalid funding rate data format")
                return None
            
            return {
                'rate': float(data.get('rate', 0)),
                'predicted_rate': float(data.get('predictedRate', 0)),
                'next_funding_time': int(data.get('nextFundingTime', 0))
            }
        except Exception as e:
            self.logger.error(f"Error processing funding rate data: {str(e)}")
            return None

    async def is_healthy(self) -> bool:
        """Check if the data processor is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Check if processing task is running
            if not self._processing_task or self._processing_task.done():
                return False
                
            # Check if data has been processed recently
            current_time = time.time()
            if current_time - self._last_process_time > self.config.get('health_check_interval', 60):
                return False
                
            return True
            
        except Exception as e:
            error_context = ErrorContext(
                component="data_processor",
                operation="is_healthy"
            )
            await self.error_handler.handle_error(
                error=e,
                context=error_context,
                severity=ErrorSeverity.LOW
            )
            return False
            
    async def process_incoming_market_data(self, websocket_handler, database_client, data_manager) -> None:
        """Process incoming market data from WebSocket handler."""
        if not all([websocket_handler, database_client, data_manager]):
            return
        
        try:
            # Get market data from WebSocket handler
            market_data = await websocket_handler.get_market_data()
            if not market_data:
                return
                
            # Skip subscription responses and connection messages
            if market_data.get('op') == 'subscribe' or market_data.get('success') is not None:
                return
            
            # Log incoming market data structure
            self.logger.debug(f"[DATA FLOW] Received market data structure: {json.dumps({k: str(type(v).__name__) for k,v in market_data.items()}, indent=2)}")
            self.logger.debug(f"[DATA FLOW] Market data: {json.dumps(market_data, indent=2)}")
            
            # Extract symbol and data type
            symbol = None
            data_type = None
            
            # Try to get symbol from different locations
            if 'symbol' in market_data:
                symbol = market_data['symbol']
            elif 'data' in market_data and isinstance(market_data['data'], dict):
                symbol = market_data['data'].get('symbol')
            elif 'topic' in market_data:
                # Extract from topic (e.g., "tickers.BTCUSDT" or "kline.1.BTCUSDT")
                parts = market_data['topic'].split('.')
                if len(parts) >= 2:
                    symbol = parts[-1]  # Last part is always the symbol
                    
            self.logger.debug(f"[DATA FLOW] Extracted symbol: {symbol}")
                    
            # Extract data type and interval from topic or type field
            if 'topic' in market_data:
                topic_parts = market_data['topic'].split('.')
                if topic_parts:
                    channel = topic_parts[0]
                    # Map channel to data type
                    type_mapping = {
                        'tickers': 'ticker',
                        'publicTrade': 'trade',
                        'liquidation': 'liquidation',
                        'kline': 'kline',
                        'orderbook': 'orderbook'
                    }
                    data_type = type_mapping.get(channel)
                    self.logger.debug(f"[DATA FLOW] Mapped channel {channel} to data_type: {data_type}")
                    
                    # For klines, get the interval and map to timeframe
                    if channel == 'kline' and len(topic_parts) > 1:
                        interval = topic_parts[1]
                        # Map interval to timeframe
                        timeframe_mapping = {
                            '1': 'base',
                            '5': 'ltf',
                            '15': 'mtf',
                            '240': 'htf'
                        }
                        timeframe = timeframe_mapping.get(interval, 'base')
                        market_data['timeframe'] = timeframe
                        self.logger.debug(f"[DATA FLOW] Mapped interval {interval} to timeframe: {timeframe}")
            else:
                data_type = market_data.get('type', 'trade')
                self.logger.debug(f"[DATA FLOW] Using data_type from market_data: {data_type}")
            
            if not symbol:
                self.logger.error("[DATA FLOW] Missing symbol in market data")
                self.logger.debug(f"[DATA FLOW] Market data without symbol: {json.dumps(market_data, indent=2)}")
                return
            
            # Process market data
            processed_data = await self.process_market_data(market_data)
            
            # Log processed data structure
            if processed_data:
                self.logger.debug(f"[DATA FLOW] Processed data structure: {json.dumps({k: str(type(v).__name__) for k,v in processed_data.items()}, indent=2)}")
                self.logger.debug(f"[DATA FLOW] Processed data: {json.dumps(processed_data, indent=2)}")
            
            if processed_data:
                try:
                    # Store in database
                    await database_client.store_market_data(
                        data=processed_data,
                        symbol=symbol
                    )
                    self.logger.debug(f"[DATA FLOW] Stored market data in database for {symbol}")
                    
                    # Update data manager state
                    if isinstance(processed_data, dict):
                        await data_manager.update_market_data(processed_data)
                        self.logger.debug(f"[DATA FLOW] Updated data manager state for {symbol}")
                        
                        # Get current market data state
                        current_state = data_manager.get_market_data(symbol)
                        if current_state:
                            self.logger.debug(f"[DATA FLOW] Current market data state for {symbol}: {json.dumps(current_state, indent=2)}")
                    elif isinstance(processed_data, list):
                        # Handle list of klines
                        for kline in processed_data:
                            await data_manager.update_market_data(kline)
                        self.logger.debug(f"[DATA FLOW] Updated data manager state with {len(processed_data)} klines for {symbol}")
                except Exception as e:
                    self.logger.error(f"[DATA FLOW] Error updating market data state: {str(e)}")
                    self.logger.debug(f"[DATA FLOW] Failed processed data: {json.dumps(processed_data, indent=2)}")
                
        except Exception as e:
            self.logger.error(f"[DATA FLOW] Error processing market data: {str(e)}")
            self.logger.debug(f"[DATA FLOW] Failed market data: {json.dumps(market_data, indent=2)}")
            
    async def format_market_data(self, data: Dict[str, Any], data_type: str, base_symbol: str) -> Optional[Dict[str, Any]]:
        """Format market data for processing based on type."""
        try:
            current_time = datetime.now(timezone.utc)
            formatted_data = {
                'symbol': base_symbol,
                'timestamp': int(current_time.timestamp() * 1000),  # Current timestamp in milliseconds
                'type': data_type
            }
            # Add type-specific data
            if data_type == 'ticker' and 'list' in data:
                ticker_data = data['list'][0] if data['list'] else {}
                formatted_data.update({
                    'lastPrice': ticker_data.get('lastPrice', 0),
                    'indexPrice': ticker_data.get('indexPrice', 0),
                    'markPrice': ticker_data.get('markPrice', 0),
                    'volume24h': ticker_data.get('volume24h', 0),
                    'turnover24h': ticker_data.get('turnover24h', 0),
                    'openInterest': ticker_data.get('openInterest', 0)
                })
            elif data_type == 'orderbook':
                formatted_data.update({
                    'b': data.get('b', []),  # bids
                    'a': data.get('a', []),  # asks
                    'ts': data.get('ts', 0)  # timestamp
                })
            elif data_type in ('trade', 'trades'):
                if 'list' in data:
                    trade_data = data['list'][0] if data['list'] else {}
                    formatted_data.update({
                        'price': trade_data.get('price', 0),
                        'size': trade_data.get('size', 0),
                        'side': trade_data.get('side', ''),
                        'time': trade_data.get('time', 0)
                    })
            elif data_type == 'kline':
                # Handle both WebSocket and REST API kline formats
                if 'data' in data:
                    # WebSocket format
                    klines = data['data']
                elif 'result' in data and 'list' in data['result']:
                    # REST API format
                    klines = data['result']['list']
                else:
                    klines = data.get('list', [])
                    
                # Transform klines to standard format
                formatted_klines = []
                for kline in klines:
                    if isinstance(kline, list):
                        # REST API format: [timestamp, open, high, low, close, volume, turnover]
                        formatted_kline = {
                            'timestamp': int(kline[0]),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5]),
                            'turnover': float(kline[6]),
                            'timeframe': data.get('timeframe', 'base'),
                            'type': 'kline',
                            'symbol': base_symbol
                        }
                    else:
                        # WebSocket format or already formatted
                        formatted_kline = {
                            'timestamp': int(kline.get('timestamp', 0)),
                            'open': float(kline.get('open', 0)),
                            'high': float(kline.get('high', 0)),
                            'low': float(kline.get('low', 0)),
                            'close': float(kline.get('close', 0)),
                            'volume': float(kline.get('volume', 0)),
                            'turnover': float(kline.get('turnover', 0)),
                            'timeframe': kline.get('timeframe', data.get('timeframe', 'base')),
                            'type': 'kline',
                            'symbol': base_symbol
                        }
                    formatted_klines.append(formatted_kline)
                    
                # Always return in a consistent format
                return {
                    'type': 'kline',
                    'symbol': base_symbol,
                    'timestamp': int(current_time.timestamp() * 1000),
                    'timeframe': data.get('timeframe', 'base'),
                    'klines': formatted_klines
                }
            elif data_type == 'funding':
                if 'list' in data and data['list']:
                    funding_data = data['list'][0]
                    formatted_data.update({
                        'fundingRate': funding_data.get('fundingRate', 0),
                        'fundingRateTimestamp': funding_data.get('fundingRateTimestamp', 0)
                    })
            elif data_type == 'open_interest':
                if 'list' in data and data['list']:
                    oi_data = data['list'][0]
                    formatted_data.update({
                        'openInterest': oi_data.get('openInterest', 0),
                        'timestamp': oi_data.get('timestamp', 0)
                    })
            elif data_type == 'long_short_ratio':
                if 'list' in data and data['list']:
                    ratio_data = data['list'][0]
                    formatted_data.update({
                        'buyRatio': ratio_data.get('buyRatio', 0),
                        'sellRatio': ratio_data.get('sellRatio', 0),
                        'timestamp': ratio_data.get('timestamp', 0)
                    })
            return formatted_data
        except Exception as e:
            self.logger.error(f"Error formatting market data: {str(e)}")
            return None

    def process_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method for processing individual trades. Redirects to _process_trades."""
        self.logger.debug("Using legacy process_trade method - consider using _process_trades instead")
        result = asyncio.run(self._process_trades([data]))
        return result[0] if result else {}

    def process_ticker_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method for processing ticker data. Redirects to _process_ticker."""
        self.logger.debug("Using legacy process_ticker_data method - consider using _process_ticker instead")
        return asyncio.run(self._process_ticker(data))

    async def initialize(self) -> None:
        """Initialize the data processor.
        
        This method sets up any necessary resources and validates the configuration.
        """
        try:
            self.logger.debug("Initializing data processor...")
            
            # Validate configuration
            if not self.config:
                raise ValueError("Missing configuration")
            
            # Initialize processing parameters
            self.batch_size = self.config.get('data_processing', {}).get('batch_size', 100)
            self.max_workers = self.config.get('data_processing', {}).get('max_workers', 4)
            self.update_interval = self.config.get('data_processing', {}).get('update_interval', 1.0)
            
            # Initialize processing pipeline
            self.pipeline = self.config.get('data_processing', {}).get('pipeline', [])
            if not self.pipeline:
                self.logger.warning("No processing pipeline configured")
            
            # Initialize caching if enabled
            cache_enabled = self.config.get('data_processing', {}).get('performance', {}).get('cache_enabled', True)
            if cache_enabled:
                cache_size = self.config.get('data_processing', {}).get('performance', {}).get('cache_size', 1000)
                self.initialize_cache(cache_size)
            
            self.initialized = True
            self.logger.info("Data processor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing data processor: {str(e)}")
            raise

    def initialize_cache(self, cache_size: int) -> None:
        """Initialize the data processing cache.
        
        Args:
            cache_size: Maximum number of items to cache
        """
        try:
            self.cache = {}
            self.cache_size = cache_size
            self.cache_hits = 0
            self.cache_misses = 0
            self.logger.debug(f"Initialized cache with size {cache_size}")
        except Exception as e:
            self.logger.error(f"Error initializing cache: {str(e)}")
            raise

    async def process(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process market data through the configured pipeline."""
        try:
            self.logger.debug(f"Processing market data for {market_data.get('symbol', 'unknown')}")
            
            # Validate input data
            if not market_data or not isinstance(market_data, dict):
                raise ValueError("Invalid market data format")
                
            # Initialize processed data with metadata
            processed_data = {
                'symbol': market_data.get('symbol'),
                'timestamp': int(time.time() * 1000),
                'metadata': market_data.get('metadata', {}),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Process through configured pipeline
            for step in self.pipeline:
                if not step.get('enabled', True):
                    continue
                    
                step_name = step.get('name')
                timeout = step.get('timeout', 5)
                
                try:
                    if step_name == 'validation':
                        processed_data = await self._validate_market_data(market_data)
                    elif step_name == 'normalization':
                        processed_data = await self._normalize_market_data(processed_data or market_data)
                    elif step_name == 'feature_engineering':
                        processed_data = await self._engineer_features(processed_data or market_data)
                    elif step_name == 'aggregation':
                        processed_data = await self._aggregate_data(processed_data or market_data)
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout in {step_name} step")
                    if not step.get('optional', False):
                        raise
                except Exception as e:
                    self.logger.error(f"Error in {step_name} step: {str(e)}")
                    if not step.get('optional', False):
                        raise
            
            # Process each data type
            if 'ohlcv' in market_data:
                processed_data['ohlcv'] = await self._process_ohlcv(market_data['ohlcv'])
                
            if 'orderbook' in market_data:
                processed_data['orderbook'] = await self._process_orderbook(market_data['orderbook'])
                
            if 'trades' in market_data:
                processed_data['trades'] = await self._process_trades(market_data['trades'])
                
            if 'ticker' in market_data:
                processed_data['ticker'] = await self._process_ticker(market_data['ticker'])
            
            # Additional market data processing
            if 'funding' in market_data:
                processed_data['funding'] = await self._process_funding(market_data['funding'])
                
            if 'open_interest' in market_data:
                processed_data['open_interest'] = await self._process_open_interest(market_data['open_interest'])
                
            if 'ratio' in market_data:
                processed_data['ratio'] = await self._process_ratio(market_data['ratio'])
                
            if 'long_short_ratio' in market_data:
                processed_data['long_short_ratio'] = await self._process_long_short_ratio(market_data['long_short_ratio'])
                
            if 'funding_rate' in market_data:
                processed_data['funding_rate'] = await self._process_funding_rate(market_data['funding_rate'])
            
            # Update processing statistics
            self._stats['total_processed'] += 1
            self._stats['last_process_time'] = time.time()
            
            self.logger.debug(f"Successfully processed market data for {processed_data.get('symbol')}")
            return processed_data
            
        except Exception as e:
            self._stats['processing_errors'] += 1
            error_context = ErrorContext(
                component="data_processor",
                operation="process",
                details={
                    "symbol": market_data.get('symbol'),
                    "error": str(e)
                }
            )
            await self.error_handler.handle_error(
                error=e,
                context=error_context,
                severity=ErrorSeverity.HIGH
            )
            self.logger.error(f"Error processing market data: {str(e)}")
            return None

    async def _process_ohlcv(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process OHLCV/kline data."""
        try:
            processed_ohlcv = {}
            for timeframe, data in ohlcv_data.items():
                if isinstance(data, pd.DataFrame):
                    # Ensure numeric types
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in data.columns:
                            data[col] = pd.to_numeric(data[col], errors='coerce')
                    
                    # Remove any rows with NaN values
                    data = data.dropna()
                    
                    # Store processed DataFrame
                    processed_ohlcv[timeframe] = data
                elif isinstance(data, list):
                    # Convert list format to DataFrame
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    processed_ohlcv[timeframe] = df
                    
            return processed_ohlcv
            
        except Exception as e:
            self.logger.error(f"Error processing OHLCV data: {str(e)}")
            return {}

    async def _process_orderbook(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process orderbook data."""
        try:
            if not isinstance(orderbook_data, dict):
                return {}
                
            return {
                'bids': [[float(p), float(s)] for p, s in orderbook_data.get('bids', [])],
                'asks': [[float(p), float(s)] for p, s in orderbook_data.get('asks', [])],
                'timestamp': int(orderbook_data.get('timestamp', time.time() * 1000))
            }
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook: {str(e)}")
            return {}

    async def _process_trades(self, trades_data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process trades data handling both WebSocket and REST formats."""
        try:
            processed_trades = []
            
            # Handle WebSocket format
            if isinstance(trades_data, dict) and 'data' in trades_data:
                trades_list = trades_data['data']
                if not isinstance(trades_list, list):
                    trades_list = [trades_list]
            else:
                trades_list = trades_data if isinstance(trades_data, list) else [trades_data]
                
            for trade in trades_list:
                processed_trade = {
                    'price': float(trade.get('price', trade.get('p', 0))),
                    'size': float(trade.get('size', trade.get('v', 0))),
                    'side': trade.get('side', trade.get('S', '')),
                    'timestamp': int(trade.get('timestamp', trade.get('T', trade.get('time', 0)))),
                    'trade_id': trade.get('id', trade.get('i', '')),
                    'is_block_trade': trade.get('is_block_trade', trade.get('BT', False))
                }
                processed_trades.append(processed_trade)
                
            return processed_trades
            
        except Exception as e:
            self.logger.error(f"Error processing trades: {str(e)}")
            return []

    async def _process_ticker(self, ticker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticker data handling both WebSocket and REST formats."""
        try:
            # Extract ticker data based on format
            if 'data' in ticker_data and isinstance(ticker_data['data'], list):
                ticker = ticker_data['data'][0] if ticker_data['data'] else {}
            else:
                ticker = ticker_data
                
            return {
                'last_price': float(ticker.get('last_price', ticker.get('lastPrice', 0))),
                'mark_price': float(ticker.get('mark_price', ticker.get('markPrice', 0))),
                'index_price': float(ticker.get('index_price', ticker.get('indexPrice', 0))),
                'funding_rate': float(ticker.get('funding_rate', ticker.get('fundingRate', 0))),
                'volume_24h': float(ticker.get('volume_24h', ticker.get('volume24h', 0))),
                'timestamp': int(ticker.get('timestamp', time.time() * 1000))
            }
            
        except Exception as e:
            self.logger.error(f"Error processing ticker: {str(e)}")
            return {}

    async def _validate_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate market data structure and content."""
        if not self.validation_service:
            return data
            
        try:
            # Create validation context
            context = ValidationContext(
                data_type="market_data",
                symbol=data.get('symbol'),
                timestamp=data.get('timestamp')
            )
            
            # Perform validation
            result = await self.validation_service.validate(data, context)
            
            if not result.is_valid:
                self._stats['invalid_data'] += 1
                self.logger.warning(f"Invalid market data: {result.errors}")
                
            return data
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return data
            
    async def _normalize_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize market data values."""
        try:
            # Implement normalization logic here
            return data
        except Exception as e:
            self.logger.error(f"Error normalizing market data: {str(e)}")
            return data
            
    async def _engineer_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Engineer additional features from market data."""
        try:
            # Implement feature engineering logic here
            return data
        except Exception as e:
            self.logger.error(f"Error engineering features: {str(e)}")
            return data
            
    async def _aggregate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate processed market data."""
        try:
            # Implement aggregation logic here
            return data
        except Exception as e:
            self.logger.error(f"Error aggregating data: {str(e)}")
            return data

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 50) -> Optional[pd.DataFrame]:
        """Fetch OHLCV (candlestick) data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            self.logger.debug(f"Fetching OHLCV data for {symbol} ({timeframe}, {limit} candles)")
            
            # Get the configuration
            config = self.config
            if not config:
                raise ValueError("Configuration not available")
            
            # Initialize exchange manager if not already passed
            exchange_manager = getattr(self, 'exchange_manager', None)
            
            if not exchange_manager:
                # Import here dynamically to avoid circular imports
                # but don't re-import on every function call
                if not hasattr(self, '_exchange_manager_module'):
                    # Store the module reference on the instance to avoid reimporting
                    from src.core.exchanges.manager import ExchangeManager
                    self._exchange_manager_module = ExchangeManager
                    
                    if not hasattr(self, '_config_manager_module'):
                        from src.core.config.config_manager import ConfigManager
                        self._config_manager_module = ConfigManager
                    
                    config_manager = self._config_manager_module(config)
                    exchange_manager = self._exchange_manager_module(config_manager)
                    # Store for future use
                    self.exchange_manager = exchange_manager
            await exchange_manager.initialize()
            
            # Fetch the OHLCV data
            ohlcv_data = await exchange_manager.fetch_ohlcv(symbol, timeframe, limit)
            
            if not ohlcv_data:
                self.logger.warning(f"No OHLCV data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['datetime'] = df['timestamp']
            
            # Set index
            df.set_index('timestamp', inplace=True)
            
            self.logger.debug(f"Retrieved {len(df)} OHLCV candles for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
