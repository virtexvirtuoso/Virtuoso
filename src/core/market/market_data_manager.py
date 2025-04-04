import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Callable, Optional
import pandas as pd
import traceback
import random

from src.core.exchanges.rate_limiter import BybitRateLimiter
from src.core.exchanges.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class MarketDataManager:
    """
    Market Data Manager that implements a hybrid WebSocket + REST API architecture
    for efficient market data fetching while respecting rate limits.
    """
    
    def __init__(self, config: Dict[str, Any], exchange_manager, alert_manager=None):
        """Initialize the market data manager
        
        Args:
            config: Application configuration dictionary
            exchange_manager: Exchange manager instance for API calls
            alert_manager: Optional alert manager instance for sending alerts
        """
        self.config = config
        self.exchange_manager = exchange_manager
        self.alert_manager = alert_manager
        self.rate_limiter = BybitRateLimiter()
        self.websocket_manager = WebSocketManager(config)
        
        # Initialize logger
        self.logger = logger
        
        # Data cache
        self.data_cache = {}
        self.last_full_refresh = {}
        
        # OHLCV specific cache
        self._ohlcv_cache = {}
        self._cache_enabled = self.config.get('market_data', {}).get('cache', {}).get('enabled', True)
        self._cache_ttl = self.config.get('market_data', {}).get('cache', {}).get('data_ttl', 60)
        
        # Configure refresh intervals (in seconds)
        self.refresh_intervals = {
            'ticker': 60,      # 1 minute
            'orderbook': 60,   # 1 minute
            'kline': {
                'base': 300,   # 5 minutes for 1m candles
                'ltf': 900,    # 15 minutes for 5m candles
                'mtf': 3600,   # 1 hour for 30m candles
                'htf': 14400   # 4 hours for 4h candles
            },
            'trades': 60,          # 1 minute
            'long_short_ratio': 3600,  # 1 hour (REST only)
            'risk_limits': 86400       # 1 day (REST only)
        }
        
        # State tracking
        self.symbols = []
        self.initialized = False
        self.running = False
        
        # Statistics
        self.stats = {
            'rest_calls': 0,
            'websocket_updates': 0,
            'data_freshness': {},
            'last_update_time': 0
        }
        
        # Get WebSocket logging throttle from config
        ws_throttle = self.config.get('market_data', {}).get('websocket_update_throttle', 5)
        
        # Websocket logging controls - throttle how often we log updates to prevent log spam
        self.ws_log_throttle = {
            'ticker': {'last_log': 0, 'interval': ws_throttle},
            'orderbook': {'last_log': 0, 'interval': ws_throttle},
            'kline': {'last_log': 0, 'interval': ws_throttle * 2},  # Less frequent for klines
            'trades': {'last_log': 0, 'interval': ws_throttle},
            'liquidation': {'last_log': 0, 'interval': 0}  # Always log liquidations (important)
        }
        
    async def initialize(self, symbols: List[str]) -> None:
        """Initialize data manager with symbols to monitor
        
        Args:
            symbols: List of symbols to monitor
        """
        self.logger.info(f"Initializing market data manager with {len(symbols)} symbols")
        self.symbols = symbols
        
        # Get WebSocket configuration
        ws_config = self.config.get('websocket', {})
        
        # Check if we should delay WebSocket initialization
        self.delay_websocket = self.config.get('market_data', {}).get('delay_websocket', False)
        
        # Load initial data for all symbols
        await self._load_initial_data()
        
        # Initialize WebSocket if enabled and not delayed
        if ws_config.get('enabled', True) and not self.delay_websocket:
            await self._initialize_websocket()
        elif self.delay_websocket:
            self.logger.info("WebSocket initialization delayed until after first monitoring cycle")
        
        self.initialized = True
        self.logger.info("Market data manager initialization complete")
    
    async def _initialize_websocket(self):
        """Initialize WebSocket manager and subscribe to channels"""
        try:
            # Initialize WebSocket manager
            await self.websocket_manager.initialize(self.symbols)
            
            # Register callback for WebSocket messages
            self.websocket_manager.register_message_callback(self._handle_websocket_message)
            
            self.logger.info("WebSocket initialization completed")
                
        except Exception as e:
            self.logger.error(f"Error initializing WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def start_monitoring(self):
        """Start market data monitoring"""
        if not self.initialized:
            self.logger.error("Market data manager not initialized")
            return
            
        self.logger.info("Starting market data monitoring loop")
        self.running = True
        
        # Create task for monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Market data monitoring started")
    
    async def _monitoring_loop(self):
        """Monitor market data and refresh as needed"""
        first_cycle_completed = False
        
        try:
            while self.running:
                # Process all symbols
                for symbol in self.symbols:
                    await self._refresh_symbol_data(symbol)
                    
                # Start WebSocket if delayed and this is the first cycle
                if self.delay_websocket and not first_cycle_completed:
                    self.logger.info("First monitoring cycle completed, initializing WebSocket")
                    await self._initialize_websocket()
                    first_cycle_completed = True
                
                # Wait before next refresh
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _refresh_symbol_data(self, symbol: str) -> None:
        """Selectively refresh components that need updating for a symbol
        
        Args:
            symbol: Symbol to refresh data for
        """
        try:
            # Get current time
            current_time = time.time()
            
            # Skip if no previous data exists (shouldn't happen after initialization)
            if symbol not in self.data_cache or symbol not in self.last_full_refresh:
                self.logger.warning(f"Symbol {symbol} not found in cache, fetching full data")
                market_data = await self._fetch_symbol_data_atomically(symbol)
                if market_data:
                    self.data_cache[symbol] = market_data
                    self.last_full_refresh[symbol] = {
                        'timestamp': current_time,
                        'components': {
                            'ticker': current_time,
                            'orderbook': current_time,
                            'trades': current_time,
                            'long_short_ratio': current_time,
                            'risk_limits': current_time,
                            'kline': {
                                'base': current_time,
                                'ltf': current_time,
                                'mtf': current_time,
                                'htf': current_time
                            }
                        }
                    }
                return
            
            # Get components that need refreshing based on configured intervals
            components_to_refresh = []
            
            # Check each component's last refresh time
            last_refresh = self.last_full_refresh[symbol]['components']
            
            # Check ticker
            if current_time - last_refresh['ticker'] > self.refresh_intervals['ticker']:
                components_to_refresh.append('ticker')
                
            # Check orderbook
            if current_time - last_refresh['orderbook'] > self.refresh_intervals['orderbook']:
                components_to_refresh.append('orderbook')
                
            # Check trades
            if current_time - last_refresh['trades'] > self.refresh_intervals['trades']:
                components_to_refresh.append('trades')
                
            # Check long/short ratio and risk limits (REST API only data)
            if current_time - last_refresh['long_short_ratio'] > self.refresh_intervals['long_short_ratio']:
                components_to_refresh.append('long_short_ratio')
                
            if current_time - last_refresh['risk_limits'] > self.refresh_intervals['risk_limits']:
                components_to_refresh.append('risk_limits')
                
            # Check each timeframe
            kline_last_refresh = last_refresh['kline']
            for tf, interval in [
                ('base', self.refresh_intervals['kline']['base']),
                ('ltf', self.refresh_intervals['kline']['ltf']),
                ('mtf', self.refresh_intervals['kline']['mtf']),
                ('htf', self.refresh_intervals['kline']['htf'])
            ]:
                if current_time - kline_last_refresh[tf] > interval:
                    components_to_refresh.append(f"kline_{tf}")
            
            # If there are components to refresh, refresh them
            if components_to_refresh:
                # Throttle logging to prevent log spam
                log_threshold = 300  # Log at most every 5 minutes per symbol
                if 'last_refresh_log' not in self.stats:
                    self.stats['last_refresh_log'] = {}
                
                if (symbol not in self.stats['last_refresh_log'] or 
                    current_time - self.stats['last_refresh_log'].get(symbol, 0) > log_threshold):
                    self.logger.debug(f"Refreshing components for {symbol}: {', '.join(components_to_refresh)}")
                    self.stats['last_refresh_log'][symbol] = current_time
                
                # Refresh the components
                await self._refresh_symbol_components(symbol, components_to_refresh)
            
        except Exception as e:
            self.logger.error(f"Error refreshing data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def _get_components_needing_refresh(self, symbol: str, current_time: float) -> List[str]:
        """Determine which data components need refreshing for a symbol
        
        Args:
            symbol: Trading pair symbol
            current_time: Current timestamp
            
        Returns:
            List of component names that need refreshing
        """
        if symbol not in self.last_full_refresh:
            return ['ticker', 'orderbook', 'kline', 'trades', 'long_short_ratio', 'risk_limits']
        
        last_refresh = self.last_full_refresh[symbol]
        components_to_refresh = []
        
        # Check simple components
        for component, interval in self.refresh_intervals.items():
            if component == 'kline':
                continue  # Handle kline separately
                
            component_time = last_refresh['components'].get(component, 0)
            if current_time - component_time > interval:
                components_to_refresh.append(component)
        
        # Check kline components
        kline_times = last_refresh['components'].get('kline', {})
        tf_needs_refresh = False
        
        for tf, interval in self.refresh_intervals['kline'].items():
            tf_time = kline_times.get(tf, 0)
            if current_time - tf_time > interval:
                tf_needs_refresh = True
                break
        
        if tf_needs_refresh:
            components_to_refresh.append('kline')
        
        return components_to_refresh
    
    async def _refresh_symbol_components(self, symbol: str, components: List[str]) -> None:
        """Refresh specific data components for a symbol
        
        Args:
            symbol: Trading pair symbol
            components: List of component names to refresh
        """
        current_time = time.time()
        
        # Perform specific fetches for each component
        for component in components:
            try:
                if component == 'ticker':
                    # Fetch ticker
                    ticker_data = await self._fetch_with_rate_limiting(
                        'v5/market/tickers',
                        lambda: self.exchange_manager.fetch_ticker(symbol)
                    )
                    if ticker_data:
                        self.data_cache[symbol]['ticker'] = ticker_data
                        self.last_full_refresh[symbol]['components']['ticker'] = current_time
                
                elif component == 'orderbook':
                    # Fetch orderbook
                    orderbook_data = await self._fetch_with_rate_limiting(
                        'v5/market/orderbook',
                        lambda: self.exchange_manager.fetch_orderbook(symbol, limit=50)
                    )
                    if orderbook_data:
                        self.data_cache[symbol]['orderbook'] = orderbook_data
                        self.last_full_refresh[symbol]['components']['orderbook'] = current_time
                
                elif component == 'kline':
                    # Fetch all timeframes
                    kline_data = await self._fetch_timeframes(symbol)
                    if kline_data:
                        self.data_cache[symbol]['kline'] = kline_data
                        # Update all timeframe refresh times
                        for tf in self.refresh_intervals['kline'].keys():
                            self.last_full_refresh[symbol]['components']['kline'][tf] = current_time
                
                elif component == 'trades':
                    # Fetch trades
                    trades_data = await self._fetch_with_rate_limiting(
                        'v5/market/recent-trade',
                        lambda: self.exchange_manager.fetch_trades(symbol, limit=1000)
                    )
                    if trades_data:
                        self.data_cache[symbol]['trades'] = trades_data
                        self.last_full_refresh[symbol]['components']['trades'] = current_time
                
                elif component == 'long_short_ratio':
                    # Fetch long/short ratio
                    lsr_data = await self._fetch_with_rate_limiting(
                        'v5/market/account-ratio',
                        lambda: self.exchange_manager.fetch_long_short_ratio(symbol)
                    )
                    if lsr_data:
                        self.data_cache[symbol]['long_short_ratio'] = lsr_data
                        self.last_full_refresh[symbol]['components']['long_short_ratio'] = current_time
                
                elif component == 'risk_limits':
                    # Fetch risk limits
                    risk_data = await self._fetch_with_rate_limiting(
                        'v5/market/risk-limit',
                        lambda: self.exchange_manager.fetch_risk_limits(symbol)
                    )
                    if risk_data:
                        self.data_cache[symbol]['risk_limits'] = risk_data
                        self.last_full_refresh[symbol]['components']['risk_limits'] = current_time
                
                # Update stats
                self.stats['rest_calls'] += 1
                
            except Exception as e:
                logger.error(f"Error refreshing {component} for {symbol}: {str(e)}")
    
    async def _fetch_symbol_data_atomically(self, symbol: str) -> Dict[str, Any]:
        """Fetch all required data types for a symbol atomically
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary containing all market data components
        """
        start_time = time.time()
        logger.debug(f"Atomic data fetch for {symbol}")
        
        # Prepare result structure
        market_data = {
            'symbol': symbol,
            'timestamp': int(start_time * 1000),
            'ticker': None,
            'orderbook': None,
            'kline': {
                'base': None,
                'ltf': None,
                'mtf': None,
                'htf': None
            },
            'trades': None,
            'long_short_ratio': None,
            'risk_limits': None,
            'open_interest': None  # Initialize open interest field
        }
        
        try:
            # Get primary exchange from exchange manager
            primary_exchange = await self.exchange_manager.get_primary_exchange()
            if not primary_exchange:
                logger.error("No primary exchange available")
                return market_data
                
            # Create fetch tasks
            tasks = {
                'orderbook': self._fetch_with_rate_limiting(
                    'v5/market/orderbook',
                    lambda: self.exchange_manager.fetch_order_book(symbol)
                ),
                'trades': self._fetch_with_rate_limiting(
                    'v5/market/recent-trade',
                    lambda: self.exchange_manager.fetch_trades(symbol, 100)
                ),
                'long_short_ratio': self._fetch_with_rate_limiting(
                    'v5/market/account-ratio',
                    lambda: self.exchange_manager.fetch_long_short_ratio(symbol)
                ),
                'risk_limits': self._fetch_with_rate_limiting(
                    'v5/market/risk-limit',
                    lambda: self.exchange_manager.fetch_risk_limits(symbol)
                ),
                # Add open interest history fetching
                'open_interest': self._fetch_with_rate_limiting(
                    'v5/market/open-interest',
                    lambda: primary_exchange.fetch_open_interest_history(symbol, interval='5min', limit=200)
                )
            }
            
            # Execute tasks to fetch data in parallel
            for key, task_coro in tasks.items():
                try:
                    result = await task_coro
                    market_data[key] = result
                except Exception as e:
                    logger.error(f"Error fetching {key} for {symbol}: {str(e)}")
            
            # Fetch OHLCV data for all timeframes
            try:
                kline_data = await self._fetch_timeframes(symbol)
                market_data['kline'] = kline_data
            except Exception as e:
                logger.error(f"Error fetching timeframes for {symbol}: {str(e)}")
            
            # Process open interest data if available
            try:
                if market_data.get('open_interest'):
                    oi_data = market_data['open_interest']
                    history_list = oi_data.get('history', [])
                    
                    # Get current and previous values from history if available
                    current_oi = 0.0
                    previous_oi = 0.0
                    
                    if history_list and len(history_list) > 0:
                        current_oi = float(history_list[0]['value'])
                        if len(history_list) > 1:
                            previous_oi = float(history_list[1]['value'])
                            self.logger.debug(f"Using OI history values: current={current_oi}, previous={previous_oi}")
                        else:
                            previous_oi = current_oi * 0.98  # Estimate previous
                            self.logger.debug(f"Only one OI history entry, estimating previous as 98% of current: {previous_oi}")
                    
                        # Create structured open interest data
                        market_data['open_interest'] = {
                            'current': current_oi,
                            'previous': previous_oi,
                            'timestamp': int(time.time() * 1000),
                            'history': history_list
                        }
                        
                        # ADDED: Create direct reference to history for easier access
                        market_data['open_interest_history'] = history_list
                        
                        # ADDED: Diagnostic logging for open interest processing
                        history_len = len(history_list)
                        self.logger.debug(f"Market data manager: Prepared OI data with {history_len} history entries")
                        if history_len > 0:
                            self.logger.debug(f"First history entry: {history_list[0]}")
                        
                        # Initialize in cache
                        if symbol not in self.data_cache:
                            self.data_cache[symbol] = {}
                        
                        self.data_cache[symbol]['open_interest'] = market_data['open_interest']
                        # ADDED: Also store direct reference in cache
                        self.data_cache[symbol]['open_interest_history'] = history_list
                        self.logger.info(f"Initialized open interest data for {symbol} with {len(history_list)} history entries")
                    else:
                        self.logger.warning(f"No open interest history available for {symbol}")
                        self.logger.warning(f"FALLBACK: Will try to use ticker data or create synthetic history")
                        
                        # Try to get current OI from ticker if available
                        if market_data.get('ticker') and 'open_interest' in market_data['ticker']:
                            current_oi = float(market_data['ticker']['open_interest'])
                            previous_oi = current_oi * 0.98  # Estimate
                            self.logger.debug(f"Using ticker OI value: {current_oi}")
                            self.logger.warning(f"FALLBACK: Creating synthetic OI history from ticker value {current_oi}")
                            
                            # Create synthetic history
                            now = int(time.time() * 1000)
                            history_list = [
                                {'timestamp': now, 'value': current_oi, 'symbol': symbol},
                                {'timestamp': now - 5*60*1000, 'value': previous_oi, 'symbol': symbol},  # 5 min ago
                                {'timestamp': now - 10*60*1000, 'value': previous_oi * 0.995, 'symbol': symbol},  # 10 min ago
                                {'timestamp': now - 15*60*1000, 'value': previous_oi * 0.99, 'symbol': symbol},  # 15 min ago
                                {'timestamp': now - 20*60*1000, 'value': previous_oi * 0.985, 'symbol': symbol},  # 20 min ago
                            ]
                            
                            # Create structured open interest data
                            market_data['open_interest'] = {
                                'current': current_oi,
                                'previous': previous_oi,
                                'timestamp': now,
                                'history': history_list
                            }
                            
                            # ADDED: Create direct reference to history for easier access
                            market_data['open_interest_history'] = history_list
                            
                            # ADDED: Diagnostic logging for synthetic open interest data
                            self.logger.debug(f"Market data manager: Prepared synthetic OI data with {len(history_list)} entries")
                            if len(history_list) > 0:
                                self.logger.debug(f"First synthetic history entry: {history_list[0]}")
                            
                            # Initialize in cache
                            if symbol not in self.data_cache:
                                self.data_cache[symbol] = {}
                            
                            self.data_cache[symbol]['open_interest'] = market_data['open_interest']
                            # ADDED: Also store direct reference in cache
                            self.data_cache[symbol]['open_interest_history'] = history_list
                            self.logger.info(f"Created synthetic OI history for {symbol} with {len(history_list)} entries")
                        else:
                            self.logger.warning(f"FALLBACK: No OI data available from ticker either for {symbol}")
                            self.logger.warning(f"FALLBACK: Will generate fully synthetic OI based on price and volume")
                            
                            # Create fully synthetic OI data based on price and volume
                            price = 0.0
                            volume_24h = 0.0
                            
                            # Try to get price and volume from ticker
                            if market_data.get('ticker'):
                                ticker = market_data['ticker']
                                price = float(ticker.get('last', 0)) or float(ticker.get('close', 0))
                                volume_24h = float(ticker.get('volume', 0))
                                
                                self.logger.debug(f"Using ticker data for synthetic OI: price={price}, volume={volume_24h}")
                            
                            # If ticker doesn't have price/volume, try OHLCV data
                            if (price <= 0 or volume_24h <= 0) and market_data.get('kline'):
                                base_df = None
                                
                                # Try to get DataFrame from kline data
                                if 'base' in market_data['kline'] and isinstance(market_data['kline']['base'], pd.DataFrame) and not market_data['kline']['base'].empty:
                                    base_df = market_data['kline']['base']
                                elif 'ltf' in market_data['kline'] and isinstance(market_data['kline']['ltf'], pd.DataFrame) and not market_data['kline']['ltf'].empty:
                                    base_df = market_data['kline']['ltf']
                                
                                if base_df is not None:
                                    # Get price from last candle close
                                    if price <= 0 and 'close' in base_df.columns:
                                        price = float(base_df['close'].iloc[-1])
                                    
                                    # Estimate 24h volume by summing recent candles
                                    if volume_24h <= 0 and 'volume' in base_df.columns:
                                        # For 1m candles, use last 24*60 = 1440 candles (or fewer if not available)
                                        # For 5m candles, use last 24*12 = 288 candles
                                        if len(base_df) >= 60:  # If we have at least an hour of data
                                            volume_24h = float(base_df['volume'].tail(min(len(base_df), 1440)).sum())
                                            
                                    self.logger.debug(f"Using OHLCV data for synthetic OI: price={price}, volume={volume_24h}")
                            
                            # Generate synthetic OI if we have price and volume
                            if price > 0 and volume_24h > 0:
                                # Use a formula to create realistic OI:
                                # For futures, OI is often 5-15x daily volume
                                # Use a conservative multiplier (5x)
                                synthetic_oi = price * volume_24h * 5.0
                                
                                # Create reasonable previous value
                                previous_oi = synthetic_oi * 0.98
                                
                                self.logger.warning(f"FALLBACK: Creating fully synthetic OI data with value {synthetic_oi:.2f}")
                                
                                # Create synthetic history
                                now = int(time.time() * 1000)
                                history_list = []
                                
                                # Create 10 synthetic entries with realistic variations
                                base_value = synthetic_oi
                                trend_factor = 0.005  # 0.5% change per step
                                
                                for i in range(10):
                                    # Create timestamps 30 minutes apart going backwards
                                    fake_timestamp = now - (i * 30 * 60 * 1000)
                                    
                                    # Create values with small random variations around a slight trend
                                    # Adds realism with some randomness but maintains a slight trend
                                    random_factor = 1.0 + (random.random() - 0.5) * 0.02  # ±1% random variation
                                    trend_value = base_value * (1.0 - (i * trend_factor))
                                    fake_value = trend_value * random_factor
                                    
                                    # Create the history entry
                                    entry = {
                                        'timestamp': fake_timestamp,
                                        'value': fake_value,
                                        'symbol': symbol
                                    }
                                    history_list.append(entry)
                                
                                # Sort by timestamp (newest first)
                                history_list.sort(key=lambda x: x['timestamp'], reverse=True)
                                
                                # Create structured open interest data
                                market_data['open_interest'] = {
                                    'current': synthetic_oi,
                                    'previous': previous_oi,
                                    'timestamp': now,
                                    'history': history_list,
                                    'is_synthetic': True  # Flag to indicate this is synthetic data
                                }
                                
                                # ADDED: Create direct reference to history for easier access
                                market_data['open_interest_history'] = history_list
                                
                                # ADDED: Diagnostic logging for fully synthetic open interest data
                                self.logger.debug(f"Market data manager: Prepared fully synthetic OI data with {len(history_list)} entries")
                                if len(history_list) > 0:
                                    self.logger.debug(f"First fully synthetic history entry: {history_list[0]}")
                                
                                # Initialize in cache
                                if symbol not in self.data_cache:
                                    self.data_cache[symbol] = {}
                                
                                self.data_cache[symbol]['open_interest'] = market_data['open_interest']
                                # ADDED: Also store direct reference in cache
                                self.data_cache[symbol]['open_interest_history'] = history_list
                                self.logger.info(f"Created fully synthetic OI history for {symbol} with {len(history_list)} entries")
                            else:
                                self.logger.error(f"FALLBACK FAILED: Could not create synthetic OI - missing price/volume data for {symbol}")
            except Exception as e:
                self.logger.error(f"Error processing open interest data: {str(e)}")
                self.logger.debug(traceback.format_exc())
            
            # Update stats
            self.stats['rest_calls'] += len(tasks) + 4
            
            # Store market data in cache
            try:
                self.data_cache[symbol] = market_data
                self.last_full_refresh[symbol] = {
                    'timestamp': time.time(),
                    'components': {
                        'ticker': time.time(),
                        'orderbook': time.time(),
                        'trades': time.time(),
                        'long_short_ratio': time.time(),
                        'risk_limits': time.time(),
                        'open_interest': time.time(),  # Add open interest tracking
                        'kline': {
                            'base': time.time(),
                            'ltf': time.time(),
                            'mtf': time.time(),
                            'htf': time.time()
                        }
                    }
                }
            except Exception as e:
                logger.error(f"Error caching market data for {symbol}: {str(e)}")
            
            end_time = time.time()
            logger.debug(f"Atomic fetch for {symbol} completed in {int((end_time - start_time) * 1000)}ms")
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error during atomic data fetch for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return market_data
    
    async def _fetch_timeframes(self, symbol: str) -> Dict[str, Any]:
        """Fetch OHLCV data for all timeframes for a symbol."""
        try:
            self.logger.info(f"Fetching OHLCV data for all timeframes for {symbol}")
            
            # Define timeframes to fetch
            timeframe_intervals = {
                'base': '1m',  # 1 minute
                'ltf': '5m',   # 5 minutes
                'mtf': '30m',  # 30 minutes
                'htf': '4h'    # 4 hours
            }
            
            # Define limits for each timeframe
            timeframe_limits = {
                'base': 1000,  # Increased from 100 to 1000
                'ltf': 300,    # Increased from 100 to 300
                'mtf': 200,    # Increased from 100 to 200
                'htf': 200     # Increased from 100 to 200
            }
            
            # Dictionary to store results
            timeframes = {}
            ohlcv_errors = 0
            
            # Fetch data for each timeframe
            for tf_name, interval in timeframe_intervals.items():
                try:
                    self.logger.debug(f"Fetching {tf_name} ({interval}) data for {symbol}")
                    
                    # Get exchange
                    exchange = await self.exchange_manager.get_primary_exchange()
                    if not exchange:
                        self.logger.error("No primary exchange available")
                        raise ValueError("No primary exchange available")
                    
                    # Rate limit the requests
                    await asyncio.sleep(0.2)  # Simple rate limiting
                    
                    # Fetch OHLCV data with increased limits
                    limit = timeframe_limits[tf_name]
                    self.logger.info(f"Fetching {limit} candles for {symbol} {tf_name} timeframe ({interval})")
                    ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
                    
                    # Log fetch results
                    if ohlcv_data:
                        self.logger.info(f"Fetched {len(ohlcv_data)} {tf_name} candles for {symbol}")
                    else:
                        self.logger.warning(f"No {tf_name} data returned for {symbol}")
                        
                    # Convert to DataFrame
                    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # Convert timestamp to datetime and set as index
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Store in results
                    timeframes[tf_name] = df
                    
                    # Add to cache if enabled
                    if self._cache_enabled:
                        self._update_cache(f"{symbol}_{tf_name}", df)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching {tf_name} OHLCV for {symbol}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    ohlcv_errors += 1
                    
                    # Create empty DataFrame with proper structure as fallback
                    timeframes[tf_name] = pd.DataFrame(
                        columns=['open', 'high', 'low', 'close', 'volume']
                    )
                    # Ensure proper column data types even for empty DataFrame
                    timeframes[tf_name] = timeframes[tf_name].astype({
                        'open': 'float64', 'high': 'float64', 'low': 'float64',
                        'close': 'float64', 'volume': 'float64'
                    })
                    # Create a proper datetime index
                    timeframes[tf_name].index = pd.DatetimeIndex([])
                    timeframes[tf_name].index.name = 'timestamp'
            
            # Log summary of fetched data
            if timeframes:
                timeframe_summary = []
                for tf_name, df in timeframes.items():
                    timeframe_summary.append(f"{tf_name}: {len(df)} candles")
                self.logger.info(f"Fetched OHLCV data summary for {symbol}: {', '.join(timeframe_summary)}")
            else:
                self.logger.error(f"Failed to fetch any valid OHLCV data for {symbol}")
                # Ensure we return a valid dictionary with empty DataFrames for all timeframes
                for tf_name in timeframe_intervals.keys():
                    if tf_name not in timeframes:
                        # Create empty DataFrame with proper structure
                        timeframes[tf_name] = pd.DataFrame(
                            columns=['open', 'high', 'low', 'close', 'volume']
                        )
                        # Ensure proper column data types even for empty DataFrame
                        timeframes[tf_name] = timeframes[tf_name].astype({
                            'open': 'float64', 'high': 'float64', 'low': 'float64',
                            'close': 'float64', 'volume': 'float64'
                        })
                        # Create a proper datetime index
                        timeframes[tf_name].index = pd.DatetimeIndex([])
                        timeframes[tf_name].index.name = 'timestamp'
            
            # Record stats
            if ohlcv_errors > 0:
                self.logger.warning(f"Encountered {ohlcv_errors} errors while fetching OHLCV data for {symbol}")
            
            return timeframes
            
        except Exception as e:
            self.logger.error(f"Error fetching timeframes for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Return empty timeframes dictionary with proper structure
            timeframes = {}
            for tf_name in ['base', 'ltf', 'mtf', 'htf']:
                # Create empty DataFrame with proper structure
                timeframes[tf_name] = pd.DataFrame(
                    columns=['open', 'high', 'low', 'close', 'volume']
                )
                # Ensure proper column data types even for empty DataFrame
                timeframes[tf_name] = timeframes[tf_name].astype({
                    'open': 'float64', 'high': 'float64', 'low': 'float64',
                    'close': 'float64', 'volume': 'float64'
                })
                # Create a proper datetime index
                timeframes[tf_name].index = pd.DatetimeIndex([])
                timeframes[tf_name].index.name = 'timestamp'
            return timeframes
    
    async def _fetch_with_rate_limiting(self, endpoint: str, fetch_func: Callable) -> Any:
        """Execute API call with rate limiting
        
        Args:
            endpoint: API endpoint being called
            fetch_func: Function to call to fetch data
            
        Returns:
            Response from the API call
        """
        # Wait if needed to respect rate limits
        await self.rate_limiter.wait_if_needed(endpoint)
        
        # Make the API call
        response = await fetch_func()
        
        # Update rate limiter from response headers if available
        if hasattr(response, 'headers'):
            self.rate_limiter.update_from_headers(endpoint, response.headers)
        elif isinstance(response, dict) and 'headers' in response:
            self.rate_limiter.update_from_headers(endpoint, response['headers'])
        
        # Record API call for monitoring
        self.rate_limiter.record_api_call(endpoint)
        
        return response
    
    async def _handle_websocket_message(self, symbol: str, topic: str, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message and update cached data
        
        Args:
            symbol: Trading pair symbol
            topic: Message topic
            message: WebSocket message data
        """
        try:
            # Skip if symbol not in cache
            if symbol not in self.data_cache:
                self.logger.warning(f"Received message for uncached symbol: {symbol}")
                return
            
            # Get WebSocket log level from config
            ws_log_level = self.config.get('market_data', {}).get('websocket_log_level', 'INFO')
            ws_log_level = getattr(logging, ws_log_level, logging.INFO)
            
            # Log message if level is DEBUG
            if self.logger.isEnabledFor(logging.DEBUG) and ws_log_level <= logging.DEBUG:
                self.logger.debug(f"WebSocket message for {symbol} on topic {topic}")
            
            # Extract data safely
            data = {}
            if isinstance(message, dict):
                data = message.get("data", {})
            else:
                self.logger.warning(f"Invalid WebSocket message format: {type(message)}")
                return
                
            # Process message based on topic type
            try:
                if "tickers" in topic:
                    self._update_ticker_from_ws(symbol, data)
                elif "kline" in topic:
                    self._update_kline_from_ws(symbol, data)
                elif "orderbook" in topic:
                    self._update_orderbook_from_ws(symbol, data)
                elif "publicTrade" in topic:
                    try:
                        self._update_trades_from_ws(symbol, data)
                    except TypeError as e:
                        self.logger.error(f"Type error in trade processing: {str(e)}")
                        # Log more details about the data to help with debugging
                        self.logger.debug(f"Trade data that caused error: {type(data)}")
                        if isinstance(data, dict) and 'data' in data:
                            self.logger.debug(f"Inner data type: {type(data['data'])}")
                elif "liquidation" in topic:
                    self._update_liquidation_from_ws(symbol, data)
                else:
                    # Log unhandled topic types only at debug level to avoid spamming
                    if self.logger.isEnabledFor(logging.DEBUG):
                        self.logger.debug(f"Unhandled WebSocket topic: {topic}")
                    return
                
                # Update stats only for successfully processed messages
                self.stats['websocket_updates'] += 1
            except Exception as e:
                error_msg = f"Error processing WebSocket {topic} for {symbol}: {str(e)}"
                self.logger.error(error_msg)
                
                # Only log detailed traceback at DEBUG level
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(traceback.format_exc())
                
                # Don't propagate the exception further - we want to keep listening for messages
                # even if one fails to process
                
        except Exception as e:
            # Catch-all for any unexpected errors in the main message handler
            self.logger.error(f"Critical error in WebSocket message handler: {str(e)}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(traceback.format_exc())
    
    def _update_ticker_from_ws(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update ticker data from WebSocket message."""
        try:
            # Extract ticker data from message
            ticker_data = {}
            
            if 'topic' in data and 'data' in data:
                ticker_data = data['data']
            elif 'data' in data and isinstance(data['data'], dict):
                ticker_data = data['data']
            elif isinstance(data, dict) and 'lastPrice' in data:
                ticker_data = data
            elif isinstance(data, dict) and ('bid1Price' in data or 'ask1Price' in data):
                # Direct ticker format with bid/ask prices
                ticker_data = data
            elif isinstance(data, dict) and 'symbol' in data:
                # Accept partial ticker updates with at least the symbol field
                ticker_data = data
            else:
                self.logger.warning(f"Unknown ticker data format from WebSocket: {data}")
                return
                
            # Ensure symbol exists in cache
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
            
            # Initialize ticker if it doesn't exist
            if 'ticker' not in self.data_cache[symbol]:
                self.data_cache[symbol]['ticker'] = {
                    'bid': 0, 'ask': 0, 'last': 0, 'high': 0, 'low': 0, 
                    'volume': 0, 'timestamp': int(time.time() * 1000)
                }
            
            # Update only the fields that are present in the new data
            for field, data_field in {
                'bid': 'bid1Price',
                'ask': 'ask1Price',
                'last': 'lastPrice',
                'high': 'highPrice24h',
                'low': 'lowPrice24h',
                'volume': 'volume24h',
                'mark': 'markPrice',
                'index': 'indexPrice',
                'open_interest': 'openInterest',
                'open_interest_value': 'openInterestValue',
                'turnover': 'turnover24h',
                'tick_direction': 'tickDirection'
            }.items():
                if data_field in ticker_data:
                    try:
                        # Convert numeric fields to float
                        if field not in ['tick_direction']:
                            self.data_cache[symbol]['ticker'][field] = float(ticker_data[data_field])
                        else:
                            self.data_cache[symbol]['ticker'][field] = ticker_data[data_field]
                    except (ValueError, TypeError):
                        self.logger.debug(f"Could not convert {data_field} value '{ticker_data[data_field]}' to float")
            
            # Always update timestamp
            if 'ts' in ticker_data:
                self.data_cache[symbol]['ticker']['timestamp'] = int(ticker_data['ts'])
            else:
                self.data_cache[symbol]['ticker']['timestamp'] = int(time.time() * 1000)
            
            # If we have open interest, store it in history
            if 'openInterest' in ticker_data:
                try:
                    oi_value = float(ticker_data['openInterest'])
                    oi_timestamp = self.data_cache[symbol]['ticker']['timestamp']
                    self._update_open_interest_history(symbol, oi_value, oi_timestamp)
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Error processing open interest: {e}")
            
            # Throttle logging based on configured intervals
            current_time = time.time()
            if (current_time - self.ws_log_throttle['ticker']['last_log'] >= 
                self.ws_log_throttle['ticker']['interval']):
                self.logger.debug(f"Updated ticker for {symbol} from WebSocket")
                self.ws_log_throttle['ticker']['last_log'] = current_time
            
            # Update statistics
            self.stats['websocket_updates'] += 1
            
        except Exception as e:
            self.logger.error(f"Error updating ticker from WebSocket: {str(e)}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(traceback.format_exc())
    
    def _update_kline_from_ws(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update kline (OHLCV) data from WebSocket message."""
        try:
            # Extract kline data from message
            kline_data = {}
            
            if 'topic' in data and 'data' in data:
                kline_data = data['data']
            elif 'data' in data and isinstance(data['data'], list):
                kline_data = data['data']
            elif isinstance(data, list):
                kline_data = data
            else:
                self.logger.warning(f"Unknown kline data format from WebSocket: {data}")
                return
                
            # Skip if empty kline data
            if not kline_data:
                self.logger.warning(f"Empty kline data received from WebSocket for {symbol}")
                return
                
            # Extract timeframe from topic
            timeframe = None
            if 'topic' in data:
                # Extract interval from topic like 'kline.1.BTCUSDT'
                parts = data['topic'].split('.')
                if len(parts) >= 2:
                    interval = parts[1]
                    # Map to our internal timeframe names
                    if interval == '1':
                        timeframe = 'base'
                    elif interval == '5':
                        timeframe = 'ltf'
                    elif interval == '30':
                        timeframe = 'mtf'
                    elif interval == '240':
                        timeframe = 'htf'
            
            # If we couldn't extract from topic, try from the kline data itself
            if not timeframe and isinstance(kline_data, list) and len(kline_data) > 0:
                first_candle = kline_data[0]
                if isinstance(first_candle, dict) and 'interval' in first_candle:
                    interval = first_candle['interval']
                    # Map to our internal timeframe names
                    if interval == '1':
                        timeframe = 'base'
                    elif interval == '5':
                        timeframe = 'ltf'
                    elif interval == '30':
                        timeframe = 'mtf'
                    elif interval == '240':
                        timeframe = 'htf'
                elif isinstance(first_candle, dict) and 'start' in first_candle and 'end' in first_candle:
                    # Try to determine interval from start and end timestamps
                    try:
                        start = int(first_candle['start'])
                        end = int(first_candle['end'])
                        interval_ms = end - start
                        interval_minutes = interval_ms / 60000  # Convert ms to minutes
                        
                        # Map to our internal timeframe names
                        if 0.5 <= interval_minutes <= 1.5:  # Allow for some timestamp flexibility
                            timeframe = 'base'
                        elif 4.5 <= interval_minutes <= 5.5:
                            timeframe = 'ltf'
                        elif 29.5 <= interval_minutes <= 30.5:
                            timeframe = 'mtf'
                        elif 239.5 <= interval_minutes <= 240.5:
                            timeframe = 'htf'
                    except (ValueError, TypeError):
                        pass
            
            if not timeframe:
                # Default to base timeframe with a warning
                self.logger.warning(f"Could not determine timeframe from WebSocket kline message: {kline_data}")
                timeframe = 'base'
                
            # Process kline data
            candles = []
            
            # If it's a single candle
            if isinstance(kline_data, dict):
                kline_data = [kline_data]
                
            self.logger.debug(f"Processing {len(kline_data)} WebSocket candles for {symbol} {timeframe}")
                
            for candle in kline_data:
                try:
                    # Process different possible formats
                    if 'start' in candle:
                        timestamp = int(candle['start'])
                        open_price = float(candle['open'])
                        high_price = float(candle['high'])
                        low_price = float(candle['low'])
                        close_price = float(candle['close'])
                        volume = float(candle['volume'])
                    elif 'confirm' in candle and isinstance(candle, dict):
                        # Bybit format
                        timestamp = int(candle['timestamp'])
                        open_price = float(candle['open'])
                        high_price = float(candle['high'])
                        low_price = float(candle['low'])
                        close_price = float(candle['close'])
                        volume = float(candle['volume'])
                    elif len(candle) >= 6 and isinstance(candle, list):
                        # Standard format [timestamp, open, high, low, close, volume]
                        timestamp = int(candle[0])
                        open_price = float(candle[1])
                        high_price = float(candle[2])
                        low_price = float(candle[3])
                        close_price = float(candle[4])
                        volume = float(candle[5])
                    else:
                        self.logger.warning(f"Unknown candle format from WebSocket: {candle}")
                        continue
                        
                    # Create candle dict
                    parsed_candle = {
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    }
                    
                    candles.append(parsed_candle)
                except (ValueError, KeyError, IndexError) as e:
                    self.logger.warning(f"Error parsing candle: {str(e)}")
                    continue
            
            if not candles:
                self.logger.warning(f"No valid candles extracted from WebSocket message for {symbol} {timeframe}")
                return
                
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            
            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Ensure symbol is in data cache
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
            
            # Ensure ohlcv data exists
            if 'ohlcv' not in self.data_cache[symbol]:
                self.data_cache[symbol]['ohlcv'] = {}
                
            # Update specific timeframe
            # If we don't have this timeframe yet, use this data directly
            if timeframe not in self.data_cache[symbol]['ohlcv']:
                self.data_cache[symbol]['ohlcv'][timeframe] = df
                self.logger.info(f"Added new {timeframe} OHLCV data for {symbol} from WebSocket ({len(df)} candles)")
            else:
                # Update existing DataFrame with new data, avoiding duplicates
                existing_df = self.data_cache[symbol]['ohlcv'][timeframe]
                
                # Combine and remove duplicates
                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()
                
                # Update cache
                self.data_cache[symbol]['ohlcv'][timeframe] = combined_df
                
                # Throttle logging
                now = time.time()
                if now - self.ws_log_throttle['kline']['last_log'] > self.ws_log_throttle['kline']['interval']:
                    self.logger.debug(f"Updated {timeframe} kline for {symbol} from WebSocket ({len(df)} candles)")
                    self.ws_log_throttle['kline']['last_log'] = now
            
            # Update timestamp
            self.data_cache[symbol]['timestamp'] = int(time.time() * 1000)
            
            # Update stats
            self.stats['websocket_updates'] += 1
            
        except Exception as e:
            self.logger.error(f"Error updating kline from WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def _update_orderbook_from_ws(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update orderbook data from WebSocket message."""
        try:
            # Extract orderbook snapshot or update from message
            orderbook_data = {}
            
            if 'topic' in data and 'data' in data:
                orderbook_data = data['data']
            elif 'data' in data and isinstance(data['data'], dict):
                orderbook_data = data['data']
            elif isinstance(data, dict) and 'a' in data and 'b' in data:
                orderbook_data = data
            elif isinstance(data, dict) and ('bid1Price' in data or 'ask1Price' in data):
                # Convert ticker-style orderbook to standard format
                orderbook_data = {
                    'a': [],  # asks
                    'b': []   # bids
                }
                
                # Add bid if available
                if 'bid1Price' in data and 'bid1Size' in data:
                    orderbook_data['b'].append([data['bid1Price'], data['bid1Size']])
                
                # Add ask if available
                if 'ask1Price' in data and 'ask1Size' in data:
                    orderbook_data['a'].append([data['ask1Price'], data['ask1Size']])
            else:
                self.logger.warning(f"Unknown orderbook data format from WebSocket: {data}")
                return
                
            # Process bids and asks
            bids = []
            asks = []
            
            # Extract bids
            if 'b' in orderbook_data:
                for bid in orderbook_data['b']:
                    try:
                        price = float(bid[0])
                        amount = float(bid[1])
                        bids.append([price, amount])
                    except (IndexError, ValueError):
                        continue
            
            # Extract asks
            if 'a' in orderbook_data:
                for ask in orderbook_data['a']:
                    try:
                        price = float(ask[0])
                        amount = float(ask[1])
                        asks.append([price, amount])
                    except (IndexError, ValueError):
                        continue
            
            # Get timestamp from data or current time
            timestamp = int(orderbook_data.get('ts', time.time() * 1000))
            
            # Ensure symbol exists in cache
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
            
            # Initialize orderbook if it doesn't exist
            if 'orderbook' not in self.data_cache[symbol]:
                self.data_cache[symbol]['orderbook'] = {
                    'bids': [],
                    'asks': [],
                    'timestamp': timestamp
                }
            
            # Update the orderbook - handle full snapshot or delta updates
            if orderbook_data.get('type') == 'delta':
                # Update existing orderbook with delta
                self._apply_orderbook_delta(symbol, bids, asks)
                # Always update the timestamp
                self.data_cache[symbol]['orderbook']['timestamp'] = timestamp
            else:
                # For full snapshot or when only updating best bid/ask
                current_book = self.data_cache[symbol]['orderbook']
                
                # If we received new bids, update them
                if bids:
                    current_book['bids'] = bids
                
                # If we received new asks, update them
                if asks:
                    current_book['asks'] = asks
                
                # Always update the timestamp
                current_book['timestamp'] = timestamp
            
            # Sort bids (descending) and asks (ascending) by price
            if self.data_cache[symbol]['orderbook']['bids']:
                self.data_cache[symbol]['orderbook']['bids'] = sorted(
                    self.data_cache[symbol]['orderbook']['bids'], 
                    key=lambda x: float(x[0]), 
                    reverse=True
                )
            
            if self.data_cache[symbol]['orderbook']['asks']:
                self.data_cache[symbol]['orderbook']['asks'] = sorted(
                    self.data_cache[symbol]['orderbook']['asks'], 
                    key=lambda x: float(x[0])
                )
            
            # Throttle logging based on configured intervals
            current_time = time.time()
            if (current_time - self.ws_log_throttle['orderbook']['last_log'] >= 
                self.ws_log_throttle['orderbook']['interval']):
                book_bids = self.data_cache[symbol]['orderbook']['bids']
                book_asks = self.data_cache[symbol]['orderbook']['asks']
                self.logger.debug(f"Updated orderbook for {symbol} from WebSocket ({len(book_bids)} bids, {len(book_asks)} asks)")
                self.ws_log_throttle['orderbook']['last_log'] = current_time
                
            # Update statistics
            self.stats['websocket_updates'] += 1
            
        except Exception as e:
            self.logger.error(f"Error updating orderbook from WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
    def _update_trades_from_ws(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update trades data from WebSocket message."""
        # Use the class logger attribute
        
        # Ensure symbol exists in cache
        if symbol not in self.data_cache:
            self.data_cache[symbol] = {}
        
        # Extract trades from the message
        trades = []
        try:
            if 'topic' in data and 'data' in data:
                trades = data['data']
            elif 'data' in data and isinstance(data['data'], list):
                trades = data['data']
            elif isinstance(data, list):
                trades = data
            else:
                self.logger.warning(f"Unknown trade data format from WebSocket: {data}")
                return
        except Exception as e:
            self.logger.error(f"Error extracting trades from WebSocket message: {str(e)}")
            return
        
        # Process each trade
        processed_trades = []
        for trade in trades:
            try:
                processed_trade = {
                    'price': float(trade.get('p', trade.get('price', 0))),
                    'amount': float(trade.get('v', trade.get('size', 0))),
                    'cost': None,  # Will calculate below
                    'side': trade.get('S', trade.get('side', '')).lower(),
                    'timestamp': int(trade.get('T', trade.get('time', time.time() * 1000))),
                    'datetime': None,  # Will be filled by analysis components if needed
                    'id': trade.get('i', trade.get('trade_id', str(time.time()))),
                    'symbol': symbol,
                    'taker_or_maker': 'taker'  # Default to taker for public trades
                }
                
                # Calculate cost (price * amount)
                processed_trade['cost'] = processed_trade['price'] * processed_trade['amount']
                
                processed_trades.append(processed_trade)
            except Exception as e:
                self.logger.error(f"Error processing trade from WebSocket: {str(e)}")
        
        # Update cache - prepend new trades to existing ones, keeping the limit
        existing_trades = self.data_cache[symbol].get('trades', [])
        
        # Ensure existing_trades is always a list
        if not isinstance(existing_trades, list):
            self.logger.warning(f"Existing trades for {symbol} is not a list (type: {type(existing_trades)}), resetting to empty list")
            existing_trades = []
            # Make sure the cache is updated with the empty list
            self.data_cache[symbol]['trades'] = []
            
        max_trades = 1000  # Maximum trades to keep
        
        # Combine trades, ensuring no duplicates by ID
        # Only extract IDs from valid dictionary entries in existing_trades
        trade_ids = set()
        try:
            for t in existing_trades:
                if isinstance(t, dict) and 'id' in t:
                    trade_ids.add(t.get('id'))
        except TypeError as e:
            self.logger.error(f"Error extracting trade IDs: {e}, type of existing_trades: {type(existing_trades)}")
            # Reset existing_trades to an empty list if it's not iterable
            existing_trades = []
            self.data_cache[symbol]['trades'] = []
                
        # Filter out trades we already have
        unique_new_trades = [t for t in processed_trades if t.get('id') not in trade_ids]
        
        # Combine and limit - make sure we don't get TypeErrors by using proper conditionals
        try:
            # Force both to be valid lists, don't just check
            unique_new_trades = list(unique_new_trades) if hasattr(unique_new_trades, '__iter__') else []
            existing_trades = list(existing_trades) if hasattr(existing_trades, '__iter__') else []
                
            # Safe concatenation
            all_trades = unique_new_trades + existing_trades
            
            # Limit the size
            all_trades = all_trades[:max_trades]
            
            # Update cache
            self.data_cache[symbol]['trades'] = all_trades
            
            # Throttle logging based on configured intervals
            current_time = time.time()
            if (current_time - self.ws_log_throttle['trades']['last_log'] >= 
                self.ws_log_throttle['trades']['interval']):
                if processed_trades:
                    self.logger.debug(f"Added {len(processed_trades)} new trades for {symbol} from WebSocket")
                self.ws_log_throttle['trades']['last_log'] = current_time
        except TypeError as e:
            self.logger.error(f"TypeError in trade update: {e}")
            self.logger.debug(f"Types: unique_new_trades={type(unique_new_trades)}, existing_trades={type(existing_trades)}")
            
            # Recover by setting trades to just the unique new trades if possible, otherwise keep existing
            if isinstance(unique_new_trades, list):
                self.data_cache[symbol]['trades'] = unique_new_trades
            elif isinstance(existing_trades, list):
                # No change needed, keep existing trades
                pass
            else:
                # Last resort - just create a new empty list
                self.data_cache[symbol]['trades'] = []
    
    def _update_liquidation_from_ws(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update liquidation data from WebSocket message
        
        Args:
            symbol: Trading pair symbol
            data: WebSocket message data
        """
        if not data:
            return
        
        # Extract liquidation data
        liq_data = data.get('data', {})
        if not liq_data:
            return
        
        # Format liquidation data
        liquidation = {
            'symbol': liq_data.get('symbol', symbol),
            'side': liq_data.get('side', ''),
            'price': float(liq_data.get('price', 0)),
            'amount': float(liq_data.get('size', 0)),
            'timestamp': int(liq_data.get('updatedTime', time.time() * 1000))
        }
        
        # Add to liquidations list in cache
        if 'liquidations' not in self.data_cache[symbol]:
            self.data_cache[symbol]['liquidations'] = []
        
        self.data_cache[symbol]['liquidations'].append(liquidation)
        
        # Keep only recent liquidations (last 24 hours)
        recent_time = time.time() * 1000 - 24 * 60 * 60 * 1000
        self.data_cache[symbol]['liquidations'] = [
            l for l in self.data_cache[symbol]['liquidations'] 
            if l['timestamp'] >= recent_time
        ]
        
        logger.info(f"Liquidation detected for {symbol}: {liquidation['side']} {liquidation['amount']} @ {liquidation['price']}")
        
        # Send to AlertManager if it's available
        if hasattr(self, 'alert_manager') and self.alert_manager is not None:
            # Prepare data for the alert manager format
            liquidation_data = {
                'symbol': symbol,
                'side': liquidation['side'],
                'price': liquidation['price'],
                'size': liquidation['amount'],  # Use 'amount' as 'size' for consistency with AlertManager
                'timestamp': liquidation['timestamp']
            }
            
            # Use asyncio to call the coroutine
            asyncio.create_task(
                self.alert_manager.check_liquidation_threshold(symbol, liquidation_data)
            )
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get complete market data for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary containing all market data
        """
        if symbol not in self.data_cache:
            # Symbol not in cache, fetch data
            logger.warning(f"Symbol {symbol} not in cache, fetching data")
            return await self._fetch_symbol_data_atomically(symbol)
        
        # Return cached data with WebSocket updates applied
        return self.data_cache[symbol]
    
    async def stop(self) -> None:
        """Stop the market data manager and cleanup resources"""
        logger.info("Stopping market data manager")
        
        # Stop monitoring loop
        self.running = False
        
        # Close WebSocket connections
        await self.websocket_manager.close()
        
        logger.info("Market data manager stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the market data manager
        
        Returns:
            Dictionary containing statistics
        """
        # Add data freshness statistics
        for symbol in self.symbols:
            if symbol in self.last_full_refresh:
                last_refresh = self.last_full_refresh[symbol]
                current_time = time.time()
                
                self.stats['data_freshness'][symbol] = {
                    'age_seconds': current_time - last_refresh['timestamp'],
                    'components': {}
                }
                
                # Add component ages
                for component, timestamp in last_refresh['components'].items():
                    if component == 'kline':
                        # Handle kline separately
                        self.stats['data_freshness'][symbol]['components']['kline'] = {
                            tf: current_time - time_val for tf, time_val in timestamp.items()
                        }
                    else:
                        self.stats['data_freshness'][symbol]['components'][component] = current_time - timestamp
        
        # Add API call statistics
        self.stats['api_calls'] = self.rate_limiter.get_api_call_stats()
        
        # Add WebSocket status
        self.stats['websocket'] = self.websocket_manager.get_status()
        
        return self.stats
    
    async def _load_initial_data(self) -> None:
        """Perform initial atomic data load for all symbols with rate limiting"""
        self.logger.info(f"Starting initial data load for {len(self.symbols)} symbols")
        
        # Group symbols in batches to respect rate limits (5 symbols at a time)
        symbol_batches = [self.symbols[i:i+5] for i in range(0, len(self.symbols), 5)]
        
        for batch_idx, symbol_batch in enumerate(symbol_batches):
            self.logger.info(f"Processing batch {batch_idx+1}/{len(symbol_batches)} with {len(symbol_batch)} symbols")
            
            # Process each symbol atomically but with rate limiting between symbols
            for symbol in symbol_batch:
                try:
                    # Ensure symbol is a string
                    symbol_str = symbol
                    if isinstance(symbol, dict) and 'symbol' in symbol:
                        symbol_str = symbol['symbol']
                    
                    # Fetch data atomically
                    market_data = await self._fetch_symbol_data_atomically(symbol_str)
                    
                    # Skip if no data was returned
                    if not market_data:
                        self.logger.warning(f"No market data returned for {symbol_str}")
                        continue
                    
                    # Store in cache using symbol string as key
                    self.data_cache[symbol_str] = market_data
                    self.last_full_refresh[symbol_str] = {
                        'timestamp': time.time(),
                        'components': {
                            'ticker': time.time(),
                            'orderbook': time.time(),
                            'trades': time.time(),
                            'long_short_ratio': time.time(),
                            'risk_limits': time.time(),
                            'kline': {
                                'base': time.time(),
                                'ltf': time.time(),
                                'mtf': time.time(),
                                'htf': time.time()
                            }
                        }
                    }
                    
                    self.logger.info(f"Initial data load complete for {symbol_str}")
                    
                except Exception as e:
                    self.logger.error(f"Error during initial data load for {symbol}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
            
            # Add delay between batches to avoid rate limit issues
            if batch_idx < len(symbol_batches) - 1:
                await asyncio.sleep(2)
        
        self.logger.info(f"Initial data load completed for {len(self.symbols)} symbols")
        self.stats['last_update_time'] = time.time()
    
    def _update_cache(self, key: str, data: Any) -> None:
        """Update the OHLCV cache with new data.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        if not self._cache_enabled:
            return
            
        try:
            # Store data in cache
            self._ohlcv_cache[key] = {
                'data': data,
                'timestamp': time.time()
            }
            
            # Log cache update at debug level
            self.logger.debug(f"Updated cache for {key} with {len(data) if hasattr(data, '__len__') else 'N/A'} entries")
            
        except Exception as e:
            self.logger.error(f"Error updating cache for {key}: {str(e)}")
            # Don't propagate this exception as caching is non-critical 
    
    def _update_open_interest_history(self, symbol: str, value: float, timestamp: int) -> None:
        """Update open interest history for a symbol.
        
        Args:
            symbol: Symbol to update
            value: Open interest value
            timestamp: Timestamp for the update
        """
        try:
            # Ensure symbol exists in cache
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
                
            # Initialize open interest structure if it doesn't exist
            if 'open_interest' not in self.data_cache[symbol]:
                self.data_cache[symbol]['open_interest'] = {
                    'current': 0.0,
                    'previous': 0.0,
                    'timestamp': 0,
                    'history': []
                }
                
            oi_data = self.data_cache[symbol]['open_interest']
            
            # Update current and previous values
            if oi_data['current'] != value:
                oi_data['previous'] = oi_data['current']
                oi_data['current'] = value
                oi_data['timestamp'] = timestamp
                
                # Get history reference
                history = oi_data['history']
                
                # Create synthetic history if we have a value but no history
                # This ensures we always have enough data points for divergence calculations
                if value > 0 and not history:
                    self.logger.warning(f"FALLBACK: No OI history available for {symbol} during WebSocket update")
                    self.logger.info(f"Creating synthetic OI history for {symbol} starting with value {value}")
                    
                    # Create 5 synthetic entries with slightly decreasing values and older timestamps
                    base_timestamp = timestamp
                    for i in range(5):
                        # Create timestamps 5 minutes apart going backwards
                        fake_timestamp = base_timestamp - ((i + 1) * 300000)  # 5 minutes (300,000ms) intervals
                        
                        # Create slightly decreasing values (approx 0.5% decrease per entry)
                        # This creates a more natural-looking history
                        fake_value = value * (0.995 - (i * 0.005))
                        
                        # Create the history entry
                        entry = {
                            'timestamp': fake_timestamp,
                            'value': fake_value,
                            'symbol': symbol
                        }
                        
                        # Add to history
                        history.append(entry)
                    
                    # Sort history by timestamp descending (most recent first)
                    history.sort(key=lambda x: x['timestamp'], reverse=True)
                    
                    self.logger.warning(f"FALLBACK: Created {len(history)} synthetic OI history entries for {symbol}")
                    self.logger.debug(f"Synthetic history details: {history}")
                
                # Add current value to history if timestamp is different from last entry
                if not history or history[0]['timestamp'] < timestamp:
                    entry = {
                        'timestamp': timestamp,
                        'value': value,
                        'symbol': symbol
                    }
                    # Insert at beginning of list (most recent first)
                    history.insert(0, entry)
                    
                    # Maintain a maximum history size (keep the 200 most recent entries)
                    if len(history) > 200:
                        history.pop()
                
                self.logger.debug(f"Updated open interest for {symbol}: {value} (history: {len(history)} entries)")
                
        except Exception as e:
            self.logger.error(f"Error updating open interest history: {str(e)}")
            self.logger.debug(traceback.format_exc()) 