import asyncio
import json
import logging
from datetime import datetime
import time
from typing import Dict, List, Any, Callable, Optional
import pandas as pd
import traceback
from src.core.error.unified_exceptions import DataUnavailableError

from src.core.exchanges.rate_limiter import BybitRateLimiter
from src.core.exchanges.websocket_manager import WebSocketManager
from src.core.market.smart_intervals import SmartIntervalsManager, MarketActivity
from src.core.cache.liquidation_cache import LiquidationCacheManager
from src.core.models.liquidation import LiquidationEvent
from src.data_storage.liquidation_storage import LiquidationStorage
from src.utils.task_tracker import create_tracked_task
from src.utils.data_validation import TimestampValidator

logger = logging.getLogger(__name__)


class MarketDataManager:
    async def fetch_real_open_interest(self, symbol: str) -> Dict:
        """Fetch real open interest data from exchange"""
        try:
            # get_primary_exchange is async; ensure we await it to obtain the client
            exchange_client = await self.exchange_manager.get_primary_exchange()
            if hasattr(exchange_client, 'fetch_open_interest'):
                oi_data = await exchange_client.fetch_open_interest(symbol)
                return {
                    'current': oi_data.get('openInterest', 0),
                    'previous': oi_data.get('prevOpenInterest', 0),
                    'timestamp': oi_data.get('timestamp', int(time.time() * 1000)),
                    'history': [],  # Exchange API typically doesn't provide history
                    'is_synthetic': False
                }
        except Exception as e:
            self.logger.warning(f"Failed to fetch real OI for {symbol}: {e}")
        
        # Return None if real data unavailable
        return None

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
        self._cache_ttl = self.config.get('market_data', {}).get('cache', {}).get('data_ttl', 30)
        
        # Initialize smart intervals manager
        self.smart_intervals = SmartIntervalsManager(config.get('market_data', {}))

        # Initialize liquidation cache manager
        cache_config = self.config.get('caching', {})  # Fixed: was 'cache', now 'caching'
        cache_type = cache_config.get('backend', 'memcached')  # Fixed: was 'type', now 'backend'

        # Get backend-specific configuration
        backend_config = cache_config.get(cache_type, {})
        self.liquidation_cache = LiquidationCacheManager(
            cache_type=cache_type,
            host=backend_config.get('host', 'localhost'),
            port=backend_config.get('port', 11211 if cache_type == 'memcached' else 6379),
            db=backend_config.get('db', 0) if cache_type == 'redis' else None
        )
        self.logger.info(f"Liquidation cache initialized with {cache_type} backend")

        # Initialize optional database persistence for liquidations
        self.liquidation_storage = None
        liquidation_persistence = self.config.get('liquidation_persistence', {})
        if liquidation_persistence.get('enabled', False):
            database_url = self.config.get('database', {}).get('url', 'sqlite:///./data/virtuoso.db')
            self.liquidation_storage = LiquidationStorage(database_url)
            self.logger.info(f"Liquidation database persistence enabled: {database_url}")
        else:
            self.logger.info("Liquidation database persistence disabled")

        # Configure refresh intervals (in seconds) - now using smart intervals
        # NOTE: WebSocket provides real-time data for ticker, orderbook, and trades.
        # REST polling is a fallback/supplement, so longer intervals reduce rate limit pressure.
        self.base_refresh_intervals = {
            'ticker': 60,      # Base: 1 minute (will be adjusted by smart intervals)
            'orderbook': 60,   # Base: 1 minute (will be adjusted by smart intervals)
            'kline': {
                'base': 300,   # 5 minutes for 1m candles
                'ltf': 900,    # 15 minutes for 5m candles
                'mtf': 3600,   # 1 hour for 30m candles
                'htf': 14400   # 4 hours for 4h candles
            },
            'trades': 300,         # Base: 5 minutes - WebSocket provides real-time trades,
                                   # REST is only for initial load/recovery. Reduces rate limit warnings.
            'long_short_ratio': 3600,  # 1 hour (REST only)
            'risk_limits': 86400,      # 1 day (REST only)
            'taker_volume_ratio': 120, # 2 minutes - needs fresh trades within 5-min lookback
            'premium_index': 300,      # 5 minutes - uses 5-min kline data
            'open_interest': 300       # 5 minutes - OI history for divergence calculation
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

        # Initialize timestamp validator for multi-timeframe synchronization
        validation_config = self.config.get('data_validation', {}).get('timestamp_sync', {})
        if validation_config.get('enabled', False):
            max_delta = validation_config.get('max_delta_seconds', 60)
            strict_mode = validation_config.get('strict_mode', False)
            self.timestamp_validator = TimestampValidator(
                max_delta_seconds=max_delta,
                strict_mode=strict_mode
            )
            self.timestamp_validation_enabled = True
            self.timestamp_validation_fallback = validation_config.get('fallback_to_base', True)
            self.logger.info(f"Timestamp validation enabled: max_delta={max_delta}s, strict={strict_mode}, fallback={self.timestamp_validation_fallback}")
        else:
            self.timestamp_validator = None
            self.timestamp_validation_enabled = False
            self.timestamp_validation_fallback = False
            self.logger.info("Timestamp validation disabled")
        
        # Get WebSocket logging throttle from config
        ws_throttle = self.config.get('market_data', {}).get('websocket_update_throttle', 5)
        
        # Websocket logging controls - throttle how often we log updates to prevent log spam
        self.ws_log_throttle = {
            'ticker': {'last_log': 0, 'interval': ws_throttle},
            'orderbook': {'last_log': 0, 'interval': ws_throttle},
            'kline': {'last_log': 0, 'interval': ws_throttle * 2},  # Less frequent for klines
            'trades': {'last_log': 0, 'interval': ws_throttle},
            'liquidation': {'last_log': 0, 'interval': 0},  # Always log liquidations (important)
            'open_interest': {'last_log': 0, 'interval': ws_throttle}  # Add specific open interest throttling
        }
        
        # Track candle processing for aggregated logging
        self.candle_processing = {
            'symbols': {},
            'last_log': 0,
            'interval': ws_throttle * 2,  # Less frequent for batch logs
            'batch_count': 0
        }
    
    def get_refresh_intervals(self) -> Dict[str, Any]:
        """Get current refresh intervals, adjusted by smart intervals if enabled."""
        if self.smart_intervals.enabled:
            return {
                'ticker': self.smart_intervals.get_current_interval('ticker'),
                'orderbook': self.smart_intervals.get_current_interval('orderbook'),
                'trades': self.smart_intervals.get_current_interval('trades'),
                'kline': self.base_refresh_intervals['kline'],  # Keep kline intervals static
                'long_short_ratio': self.base_refresh_intervals['long_short_ratio'],
                'risk_limits': self.base_refresh_intervals['risk_limits'],
                'taker_volume_ratio': self.base_refresh_intervals['taker_volume_ratio'],
                'premium_index': self.base_refresh_intervals['premium_index'],
                'open_interest': self.base_refresh_intervals['open_interest']
            }
        else:
            return self.base_refresh_intervals
    
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
        self.monitoring_task = create_tracked_task(self._monitoring_loop(), name="auto_tracked_task")
        
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
            
            # Get current refresh intervals (with smart intervals adjustment)
            refresh_intervals = self.get_refresh_intervals()
            
            # Check ticker
            if current_time - last_refresh['ticker'] > refresh_intervals['ticker']:
                components_to_refresh.append('ticker')
                
            # Check orderbook
            if current_time - last_refresh['orderbook'] > refresh_intervals['orderbook']:
                components_to_refresh.append('orderbook')
                
            # Check trades
            if current_time - last_refresh['trades'] > refresh_intervals['trades']:
                components_to_refresh.append('trades')
                
            # Check long/short ratio and risk limits (REST API only data)
            if current_time - last_refresh['long_short_ratio'] > refresh_intervals['long_short_ratio']:
                components_to_refresh.append('long_short_ratio')
                
            if current_time - last_refresh['risk_limits'] > refresh_intervals['risk_limits']:
                components_to_refresh.append('risk_limits')
                
            # Check each timeframe
            kline_last_refresh = last_refresh['kline']
            for tf, interval in [
                ('base', refresh_intervals['kline']['base']),
                ('ltf', refresh_intervals['kline']['ltf']),
                ('mtf', refresh_intervals['kline']['mtf']),
                ('htf', refresh_intervals['kline']['htf'])
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
            return ['ticker', 'orderbook', 'kline', 'trades', 'long_short_ratio', 'risk_limits', 'taker_volume_ratio', 'premium_index', 'open_interest']
        
        last_refresh = self.last_full_refresh[symbol]
        components_to_refresh = []
        
        # Get current refresh intervals (with smart intervals adjustment)
        refresh_intervals = self.get_refresh_intervals()
        
        # Check simple components
        for component, interval in refresh_intervals.items():
            if component == 'kline':
                continue  # Handle kline separately
                
            component_time = last_refresh['components'].get(component, 0)
            if current_time - component_time > interval:
                components_to_refresh.append(component)
        
        # Check kline components
        kline_times = last_refresh['components'].get('kline', {})
        tf_needs_refresh = False
        
        for tf, interval in refresh_intervals['kline'].items():
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
                    # Fetch both standard and RPI orderbook data
                    enhanced_orderbook_data = await self._fetch_enhanced_orderbook_data(symbol)
                    if enhanced_orderbook_data:
                        self.data_cache[symbol]['orderbook'] = enhanced_orderbook_data['standard_orderbook']
                        self.data_cache[symbol]['rpi_orderbook'] = enhanced_orderbook_data.get('rpi_orderbook', {})
                        self.data_cache[symbol]['enhanced_orderbook'] = enhanced_orderbook_data.get('enhanced_orderbook', {})
                        self.data_cache[symbol]['rpi_enabled'] = enhanced_orderbook_data.get('rpi_enabled', False)
                        self.last_full_refresh[symbol]['components']['orderbook'] = current_time
                
                elif component == 'kline':
                    # Fetch all timeframes
                    kline_data = await self._fetch_timeframes(symbol)
                    if kline_data:
                        self.data_cache[symbol]['kline'] = kline_data
                        # Update all timeframe refresh times
                        refresh_intervals = self.get_refresh_intervals()
                        for tf in refresh_intervals['kline'].keys():
                            self.last_full_refresh[symbol]['components']['kline'][tf] = current_time
                
                elif component == 'trades':
                    # Fetch trades
                    trades_data = await self._fetch_with_rate_limiting(
                        'v5/market/recent-trade',
                        lambda: self.exchange_manager.fetch_trades(symbol, limit=1000)
                    )
                    # Fallback: if no trades via primary path, try direct exchange (e.g., Bybit) fetch
                    if not trades_data:
                        try:
                            exchange = await self.exchange_manager.get_primary_exchange()
                            if exchange and hasattr(exchange, 'fetch_trades'):
                                trades_data = await exchange.fetch_trades(symbol, limit=1000) or []
                        except Exception:
                            trades_data = trades_data or []
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

                elif component == 'taker_volume_ratio':
                    # Refresh taker volume ratio (needs fresh trades for accurate calculation)
                    primary_exchange = await self.exchange_manager.get_primary_exchange()
                    if primary_exchange and hasattr(primary_exchange, 'calculate_taker_buy_sell_ratio'):
                        taker_data = await self._fetch_with_rate_limiting(
                            'v5/market/recent-trade',
                            lambda: primary_exchange.calculate_taker_buy_sell_ratio(symbol)
                        )
                        if taker_data:
                            self.data_cache[symbol]['taker_volume_ratio'] = taker_data
                            self.last_full_refresh[symbol]['components']['taker_volume_ratio'] = current_time

                elif component == 'premium_index':
                    # Refresh premium index for basis score calculation
                    primary_exchange = await self.exchange_manager.get_primary_exchange()
                    if primary_exchange and hasattr(primary_exchange, 'fetch_premium_index_kline'):
                        premium_data = await self._fetch_with_rate_limiting(
                            'v5/market/premium-index-price-kline',
                            lambda: primary_exchange.fetch_premium_index_kline(symbol, interval='5')
                        )
                        if premium_data:
                            self.data_cache[symbol]['premium_index'] = premium_data
                            self.last_full_refresh[symbol]['components']['premium_index'] = current_time

                elif component == 'open_interest':
                    # Refresh open interest history for OI-price divergence calculation
                    primary_exchange = await self.exchange_manager.get_primary_exchange()
                    if primary_exchange and hasattr(primary_exchange, 'fetch_open_interest_history'):
                        oi_data = await self._fetch_with_rate_limiting(
                            'v5/market/open-interest',
                            lambda: primary_exchange.fetch_open_interest_history(symbol, interval='5min', limit=200)
                        )
                        if oi_data and isinstance(oi_data, dict) and oi_data.get('history'):
                            history_list = oi_data.get('history', [])
                            # Get current and previous values from history
                            current_oi = float(history_list[0]['value']) if history_list else 0.0
                            previous_oi = float(history_list[1]['value']) if len(history_list) > 1 else current_oi

                            self.data_cache[symbol]['open_interest'] = {
                                'current': current_oi,
                                'previous': previous_oi,
                                'timestamp': int(oi_data.get('timestamp', time.time() * 1000)),
                                'history': history_list,
                                'is_synthetic': False
                            }
                            self.data_cache[symbol]['open_interest_history'] = history_list
                            self.last_full_refresh[symbol]['components']['open_interest'] = current_time
                            logger.debug(f"Refreshed OI for {symbol}: {len(history_list)} history points")
                        else:
                            logger.warning(f"OI refresh for {symbol} returned empty/invalid data")

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
            'open_interest': None,  # Initialize open interest field
            'premium_index': None,  # Initialize premium index for basis score calculation
            'taker_volume_ratio': None  # Initialize taker volume ratio for orderflow analysis
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
                ),
                # Add premium index for basis score calculation (5-min interval for granular data)
                'premium_index': self._fetch_with_rate_limiting(
                    'v5/market/premium-index-price-kline',
                    lambda: primary_exchange.fetch_premium_index_kline(symbol, interval='5')
                ),
                # Add taker volume ratio for orderflow analysis
                'taker_volume_ratio': self._fetch_with_rate_limiting(
                    'v5/market/recent-trade',  # Uses trades data
                    lambda: primary_exchange.calculate_taker_buy_sell_ratio(symbol)
                )
            }
            
            # Execute tasks to fetch data in parallel
            for key, task_coro in tasks.items():
                try:
                    result = await task_coro
                    # Ensure open interest result is valid, set to empty dict if None
                    if key == 'open_interest' and result is None:
                        logger.warning(f"Open interest fetch returned None for {symbol}, will create fallback data")
                        result = {}  # This will trigger the fallback logic below
                    market_data[key] = result
                except Exception as e:
                    logger.error(f"Error fetching {key} for {symbol}: {str(e)}")
                    # For open interest, ensure we set an empty dict to trigger fallback
                    if key == 'open_interest':
                        market_data[key] = {}
            
            # Fetch OHLCV data for all timeframes
            try:
                kline_data = await self._fetch_timeframes(symbol)
                market_data['kline'] = kline_data
                # Also store under 'ohlcv' key for compatibility with confluence analyzer
                market_data['ohlcv'] = kline_data
            except Exception as e:
                logger.error(f"Error fetching timeframes for {symbol}: {str(e)}")
            
            # Process open interest data if available
            try:
                oi_data = market_data.get('open_interest')
                # Check if OI data exists and has valid history
                if oi_data and isinstance(oi_data, dict) and oi_data.get('history'):
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
                        
                        # Also store in sentiment-compatible format
                        if symbol in self.data_cache:
                            sentiment_oi = {
                                'value': float(current_oi),
                                'change_24h': float(current_oi - previous_oi) if previous_oi else 0.0,
                                'timestamp': int(market_data['open_interest'].get('timestamp', time.time() * 1000))
                            }
                            # Merge sentiment OI with existing structure
                            if 'open_interest' not in self.data_cache[symbol]:
                                self.data_cache[symbol]['open_interest'] = {
                                    'current': 0.0,
                                    'previous': 0.0,
                                    'timestamp': 0,
                                    'history': []
                                }
                            
                            # Update with sentiment values while preserving structure
                            oi_data = self.data_cache[symbol]['open_interest']
                            oi_data['previous'] = oi_data.get('current', 0.0)
                            oi_data['current'] = float(current_oi)
                            oi_data['timestamp'] = sentiment_oi['timestamp']
                            oi_data['value'] = sentiment_oi['value']  # Keep for compatibility
                            oi_data['change_24h'] = sentiment_oi['change_24h']
                            self.logger.debug(f"Stored sentiment OI for {symbol}: value={sentiment_oi['value']}, change={sentiment_oi['change_24h']}")
                        
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
                            
                            # Create minimal structure even when no real OI data available
                            # This prevents "No proper history found" warnings in confluence analyzer
                            now = int(time.time() * 1000)
                            if price > 0 and volume_24h > 0:
                                self.logger.warning(f"No real OI data available for {symbol}, using minimal structure")
                            else:
                                self.logger.error(f"FALLBACK: No price/volume data for synthetic OI for {symbol}, using minimal structure")

                            # Create minimal structure with empty history
                            # This allows confluence analyzer to gracefully skip OI divergence calculation
                            market_data['open_interest'] = {
                                'current': 0.0,
                                'previous': 0.0,
                                'timestamp': now,
                                'history': []
                            }
                            market_data['open_interest_history'] = []
                                
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
                elif "liquidation" in topic.lower():
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
            if 'ticker' not in self.data_cache[symbol] or self.data_cache[symbol]['ticker'] is None:
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
            # Extract candle data from message
            kline_data = {}
            
            if 'topic' in data and 'data' in data:
                kline_data = data['data']
            elif 'data' in data and isinstance(data['data'], list):
                kline_data = data['data']
            elif 'data' in data and isinstance(data['data'], dict):
                kline_data = [data['data']]
            elif isinstance(data, list):
                kline_data = data
            elif isinstance(data, dict) and ('open' in data or 'close' in data):
                kline_data = [data]
            else:
                self.logger.warning(f"Unknown kline data format from WebSocket: {data}")
                return
                
            # Determine timeframe
            timeframe = None
            
            # Try to extract from topic
            if 'topic' in data:
                topic = data['topic']
                try:
                    # Parse interval from topic (like 'kline.1m' or 'kline.5')
                    if '.' in topic:
                        parts = topic.split('.')
                        if len(parts) > 1:
                            interval_str = parts[1]
                            
                            # Convert to minutes for standardized comparison
                            if interval_str.endswith('m'):
                                interval_minutes = float(interval_str.rstrip('m'))
                            elif interval_str.endswith('h'):
                                interval_minutes = float(interval_str.rstrip('h')) * 60
                            elif interval_str.endswith('d') or interval_str.endswith('D'):
                                interval_minutes = float(interval_str.rstrip('dD')) * 1440
                            else:
                                interval_minutes = float(interval_str)
                            
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
            
            # If timeframe couldn't be determined from topic, try to get from kline_data itself
            if not timeframe and isinstance(kline_data, list) and len(kline_data) > 0:
                first_candle = kline_data[0]
                if isinstance(first_candle, dict) and 'interval' in first_candle:
                    interval = first_candle['interval']
                    # Map interval to timeframe
                    interval_map = {
                        '1': 'base',
                        '5': 'ltf',
                        '30': 'mtf',
                        '60': 'mtf',
                        '240': 'htf',
                        '1D': 'htf'
                    }
                    timeframe = interval_map.get(interval, None)
            
            # Update candle processing aggregation stats
            now = time.time()
            if symbol not in self.candle_processing['symbols']:
                self.candle_processing['symbols'][symbol] = {
                    'count': 0, 
                    'timeframes': set(),
                    'last_update': now,
                    'warnings': 0,
                    'last_warning': 0
                }
            
            # Update symbol stats
            symbol_data = self.candle_processing['symbols'][symbol]
            symbol_data['count'] += len(kline_data)
            symbol_data['timeframes'].add(timeframe if timeframe else 'base')
            symbol_data['last_update'] = now
            self.candle_processing['batch_count'] += len(kline_data)
            
            # Only log warnings if we haven't seen many for this symbol recently
            warning_throttle_interval = 60  # Only log warnings once per minute per symbol
            warning_throttled = (now - symbol_data['last_warning'] < warning_throttle_interval and 
                               symbol_data['warnings'] > 2)
            
            # Log warnings for missing timeframe with throttling
            if not timeframe:
                # Set default timeframe
                timeframe = 'base'
                
                # Only log warning if not throttled
                if not warning_throttled:
                    self.logger.warning(f"Could not determine timeframe from WebSocket kline message: {kline_data}")
                    symbol_data['warnings'] += 1
                    symbol_data['last_warning'] = now
            
            # Process kline data
            candles = []
            
            # If it's a single candle
            if isinstance(kline_data, dict):
                kline_data = [kline_data]
            
            # Log individual updates only if threshold not exceeded and not too frequent
            log_threshold_exceeded = self.candle_processing['batch_count'] > 20  # Reduced from 50
            time_to_log = (now - self.candle_processing['last_log'] >= self.candle_processing['interval'])
            
            if not log_threshold_exceeded:
                self.logger.debug(f"Processing {len(kline_data)} WebSocket candles for {symbol} {timeframe}")
            elif time_to_log:
                # Log aggregated stats
                active_symbols = sum(1 for s in self.candle_processing['symbols'].values() 
                                 if now - s['last_update'] < 60)  # active in last minute
                total_candles = sum(s['count'] for s in self.candle_processing['symbols'].values())
                self.logger.debug(f"Processed {total_candles} WebSocket candles for {active_symbols} symbols in the last {int(now - self.candle_processing['last_log'])}s")
                
                # Reset counters
                self.candle_processing['batch_count'] = 0
                self.candle_processing['last_log'] = now
                for s in self.candle_processing['symbols'].values():
                    s['count'] = 0
            
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
            data: WebSocket message data (official Bybit allLiquidation format)
        """
        if not data:
            return

        # Extract liquidation data array (handle both direct array and nested format)
        # After message routing, data is already extracted from message['data']
        if isinstance(data, list):
            liquidation_data_array = data
            ts = int(time.time() * 1000)  # Use current time if data is direct array
        else:
            liquidation_data_array = data.get('data', [])
            ts = data.get('ts', int(time.time() * 1000))

        if not liquidation_data_array:
            return

        # Log receipt of liquidation message
        logger.info(f"📡 Received liquidation WebSocket message for {symbol} with {len(liquidation_data_array)} events")
        
        # Process each liquidation event in the array
        for liq_data in liquidation_data_array:
            # Format liquidation data using official Bybit field names (T, s, S, v, p)
            liquidation_dict = {
                'symbol': liq_data.get('s', symbol),
                'side': liq_data.get('S', ''),
                'price': float(liq_data.get('p', 0)),
                'amount': float(liq_data.get('v', 0)),
                'timestamp': int(liq_data.get('T', ts))
            }

            # Skip creating LiquidationEvent Pydantic object - it requires many fields
            # that WebSocket data doesn't provide (severity, confidence_score, etc.)
            # Store raw liquidation dict directly in caches instead

            # Store in in-memory cache
            if 'liquidations' not in self.data_cache[liquidation_dict['symbol']]:
                self.data_cache[liquidation_dict['symbol']]['liquidations'] = []

            self.data_cache[liquidation_dict['symbol']]['liquidations'].append(liquidation_dict)

            # Keep only recent liquidations (last 24 hours)
            recent_time = time.time() * 1000 - 24 * 60 * 60 * 1000
            self.data_cache[liquidation_dict['symbol']]['liquidations'] = [
                l for l in self.data_cache[liquidation_dict['symbol']]['liquidations']
                if l['timestamp'] >= recent_time
            ]

            logger.info(f"Liquidation detected for {liquidation_dict['symbol']}: {liquidation_dict['side']} {liquidation_dict['amount']} @ {liquidation_dict['price']} (cached)")

            # Update BybitExchange's liquidation storage for backward compatibility
            # This ensures get_recent_liquidations() returns actual data
            # We need to schedule this as a background task to avoid blocking
            async def update_exchange_storage():
                try:
                    exchange = await self.exchange_manager.get_primary_exchange()
                    if exchange:
                        if not hasattr(exchange, '_liquidations') or exchange._liquidations is None:
                            exchange._liquidations = {}

                        if liquidation_dict['symbol'] not in exchange._liquidations:
                            exchange._liquidations[liquidation_dict['symbol']] = []

                        # Store with 'size' key for backward compatibility
                        exchange_liq_data = {
                            'symbol': liquidation_dict['symbol'],
                            'side': liquidation_dict['side'],
                            'price': liquidation_dict['price'],
                            'size': liquidation_dict['amount'],
                            'timestamp': liquidation_dict['timestamp']
                        }
                        exchange._liquidations[liquidation_dict['symbol']].append(exchange_liq_data)

                        # Keep only last 24 hours in exchange storage
                        cutoff = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
                        exchange._liquidations[liquidation_dict['symbol']] = [
                            liq for liq in exchange._liquidations[liquidation_dict['symbol']]
                            if liq['timestamp'] > cutoff
                        ]

                        logger.debug(f"Updated BybitExchange liquidation storage for {liquidation_dict['symbol']} (count: {len(exchange._liquidations[liquidation_dict['symbol']])})")
                except Exception as exchange_update_error:
                    logger.debug(f"Could not update exchange liquidation storage: {exchange_update_error}")

            # Create task to update exchange storage without blocking
            create_tracked_task(update_exchange_storage(), name="update_exchange_liquidations")

            # Send to AlertManager if it's available
            if hasattr(self, 'alert_manager') and self.alert_manager is not None:
                # Prepare data for the alert manager format
                liquidation_data = {
                    'symbol': liquidation_dict['symbol'],
                    'side': liquidation_dict['side'],
                    'price': liquidation_dict['price'],
                    'size': liquidation_dict['amount'],  # Use 'amount' as 'size' for consistency with AlertManager
                    'timestamp': liquidation_dict['timestamp']
                }
                
                # Use asyncio to call the coroutine with proper error handling
                task = create_tracked_task(
                    self.alert_manager.check_liquidation_threshold(liquidation_dict['symbol'], liquidation_data),
                    name="liquidation_threshold_check"
                )
                # Add error callback to handle any exceptions
                def handle_liquidation_alert_error(task):
                    try:
                        task.result()  # This will raise any exception that occurred
                    except Exception as e:
                        logger.error(f"Error in liquidation threshold check for {liquidation_dict['symbol']}: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                
                task.add_done_callback(handle_liquidation_alert_error)
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get all available market data for a symbol.
        
        Args:
            symbol: The symbol to get market data for
            
        Returns:
            Dict containing market data components (ticker, orderbook, trades, etc.)
        """
        if symbol not in self.data_cache:
            self.logger.warning(f"Symbol {symbol} not in cache, initializing")
            self.data_cache[symbol] = {}
            
        # First ensure we have refreshed data
        try:
            # Add 'kline' and sentiment-related components to refresh
            await self.refresh_components(symbol, components=['ticker', 'orderbook', 'trades', 'kline', 'long_short_ratio'])
        except Exception as e:
            self.logger.error(f"Error refreshing market data for {symbol}: {str(e)}")
            
        # Build the result dict with all available data
        market_data = {
            'symbol': symbol,  # Required by validation
            'timestamp': int(time.time() * 1000)  # Required by validation
        }
        
        # Require real ticker data; do not synthesize defaults
        if 'ticker' not in self.data_cache[symbol] or not self.data_cache[symbol]['ticker']:
            raise DataUnavailableError(
                message=f"No ticker data available for {symbol}",
                data_type="ticker"
            )
            
        # Include basic market data components
        market_data['ticker'] = self.data_cache[symbol].get('ticker')
        market_data['orderbook'] = self.data_cache[symbol].get('orderbook')
        market_data['trades'] = self.data_cache[symbol].get('trades', [])
        
        # OHLCV data - required for market reports
        market_data['ohlcv'] = {}
        
        # Check if ohlcv data exists directly in the symbol's cache
        if 'ohlcv' in self.data_cache[symbol] and isinstance(self.data_cache[symbol]['ohlcv'], dict):
            # Use the ohlcv data directly from the cache
            market_data['ohlcv'] = self.data_cache[symbol]['ohlcv']
            self.logger.debug(f"Retrieved OHLCV data from symbol cache: {len(market_data['ohlcv'])} timeframes")
        # FIX: Also check for 'kline' key which is how the data is actually stored
        elif 'kline' in self.data_cache[symbol] and isinstance(self.data_cache[symbol]['kline'], dict):
            # Use the kline data from the cache (this is the actual storage key)
            market_data['ohlcv'] = self.data_cache[symbol]['kline']
            self.logger.debug(f"Retrieved OHLCV data from kline cache: {len(market_data['ohlcv'])} timeframes")
        else:
            # If no ohlcv data in symbol cache, try to get it from _ohlcv_cache
            self.logger.debug(f"No OHLCV data in symbol cache, fetching from main cache")
            
            # Try to retrieve from _ohlcv_cache using different key formats
            for tf in ['base', 'ltf', 'mtf', 'htf']:
                # Check different formats of cache keys
                possible_keys = [
                    f"{symbol}_{tf}",  # Format: BTCUSDT_base
                    f"{symbol.replace('/', '')}_{tf}"  # Format: BTCUSDT_base (removing / if present)
                ]
                
                # Try each possible key
                for key in possible_keys:
                    if key in self._ohlcv_cache and 'data' in self._ohlcv_cache[key]:
                        market_data['ohlcv'][tf] = self._ohlcv_cache[key]['data']
                        self.logger.debug(f"Found {tf} timeframe data in cache with key: {key}")
                        break
        
            # If still no data, try to fetch it
            if not market_data['ohlcv']:
                self.logger.warning(f"No OHLCV data in cache for {symbol}, fetching from API")
                try:
                    # Fetch timeframes
                    timeframes = await self._fetch_timeframes(symbol)
                    if timeframes:
                        # Store in result
                        market_data['ohlcv'] = timeframes
                        # Also update symbol cache for future use (store under both keys for compatibility)
                        if symbol in self.data_cache:
                            self.data_cache[symbol]['ohlcv'] = timeframes
                            self.data_cache[symbol]['kline'] = timeframes  # Store under both keys
                        self.logger.info(f"Fetched and stored OHLCV data for {symbol}: {len(timeframes)} timeframes")
                    else:
                        raise DataUnavailableError(
                            message=f"No OHLCV data available for {symbol}",
                            data_type="ohlcv"
                        )
                except Exception as e:
                    # Surface explicit unavailability, log others
                    if isinstance(e, DataUnavailableError):
                        raise
                    self.logger.error(f"Error fetching OHLCV data: {str(e)}")
                    self.logger.debug(traceback.format_exc())

        # Validate multi-timeframe timestamp synchronization
        if self.timestamp_validation_enabled and market_data.get('ohlcv'):
            try:
                is_valid, error_message = self.timestamp_validator.validate_multi_timeframe_sync(
                    market_data['ohlcv']
                )

                if not is_valid:
                    self.logger.warning(f"Timestamp validation failed for {symbol}: {error_message}")

                    # If fallback is enabled and we have base timeframe data
                    if self.timestamp_validation_fallback and 'base' in market_data['ohlcv']:
                        self.logger.info(f"Falling back to base timeframe only for {symbol}")
                        # Keep only base timeframe data
                        base_data = market_data['ohlcv']['base']
                        market_data['ohlcv'] = {'base': base_data}
                else:
                    self.logger.debug(f"Timestamp validation passed for {symbol}")

            except Exception as e:
                self.logger.error(f"Error during timestamp validation for {symbol}: {str(e)}")
                self.logger.debug(traceback.format_exc())

        # Log summary of what we're returning
        ohlcv_summary = ', '.join([f"{tf}: {len(df)}" for tf, df in market_data.get('ohlcv', {}).items()])
        self.logger.debug(f"Market data for {symbol} includes: ticker={bool(market_data.get('ticker'))}, "
                         f"orderbook={bool(market_data.get('orderbook'))}, "
                         f"trades={len(market_data.get('trades', []))}, "
                         f"ohlcv=[{ohlcv_summary}]")
        
        # Add open interest data if available
        market_data['open_interest'] = self.get_open_interest_data(symbol)
        
        # --- FIX: Propagate sentiment dict (including long_short_ratio) ---
        sentiment = {}
        # Copy over any sentiment fields from the data cache if present
        if 'sentiment' in self.data_cache[symbol] and isinstance(self.data_cache[symbol]['sentiment'], dict):
            sentiment = self.data_cache[symbol]['sentiment'].copy()
        # If long_short_ratio is present at the top level, add it to sentiment
        if 'long_short_ratio' in self.data_cache[symbol]:
            sentiment['long_short_ratio'] = self.data_cache[symbol]['long_short_ratio']
        
        # Extract funding_rate from ticker if available
        if 'ticker' in self.data_cache[symbol] and self.data_cache[symbol]['ticker']:
            ticker = self.data_cache[symbol]['ticker']
            if 'funding_rate' in ticker:
                sentiment['funding_rate'] = {
                    'rate': float(ticker.get('funding_rate', 0)),
                    'next_funding_time': int(ticker.get('next_funding_time', time.time() * 1000 + 28800000))
                }
                self.logger.debug(f"Extracted funding_rate from ticker: {sentiment['funding_rate']}")
        
        # Add other possible sentiment fields as needed (e.g., liquidations, market_mood, risk)
        # FIX: Also check for 'risk_limits' since that's how it's actually stored
        for key in ['liquidations', 'market_mood', 'risk', 'risk_limits']:
            if key in self.data_cache[symbol]:
                # Map risk_limits to risk in sentiment for consistency
                sentiment_key = 'risk' if key == 'risk_limits' else key
                sentiment[sentiment_key] = self.data_cache[symbol][key]
        
        # Special handling for open_interest to ensure correct structure
        if 'open_interest' in self.data_cache[symbol]:
            oi_data = self.data_cache[symbol]['open_interest']
            
            # Check if we have the full OI structure with history
            if isinstance(oi_data, dict) and 'current' in oi_data:
                # We have the full structure from market data
                sentiment['open_interest'] = {
                    'value': float(oi_data.get('current', 0)),
                    'change_24h': float(oi_data.get('current', 0)) - float(oi_data.get('previous', 0)),
                    'timestamp': int(oi_data.get('timestamp', time.time() * 1000))
                }
            elif isinstance(oi_data, dict) and 'value' in oi_data:
                # Already in sentiment format
                sentiment['open_interest'] = oi_data
            else:
                # Try to get from market_data['open_interest'] if available
                if 'open_interest' in market_data and market_data['open_interest']:
                    md_oi = market_data['open_interest']
                    if isinstance(md_oi, dict) and 'current' in md_oi:
                        sentiment['open_interest'] = {
                            'value': float(md_oi.get('current', 0)),
                            'change_24h': float(md_oi.get('current', 0)) - float(md_oi.get('previous', 0)),
                            'timestamp': int(md_oi.get('timestamp', time.time() * 1000))
                        }
                    else:
                        # Last resort - check if we have OI history
                        oi_history = self.get_open_interest_data(symbol)
                        if oi_history and isinstance(oi_history, dict):
                            if 'current' in oi_history:
                                sentiment['open_interest'] = {
                                    'value': float(oi_history.get('current', 0)),
                                    'change_24h': float(oi_history.get('current', 0)) - float(oi_history.get('previous', 0)),
                                    'timestamp': int(oi_history.get('timestamp', time.time() * 1000))
                                }
                            elif 'history' in oi_history and oi_history['history']:
                                # Extract from history
                                latest = oi_history['history'][0]
                                previous = oi_history['history'][1] if len(oi_history['history']) > 1 else latest
                                sentiment['open_interest'] = {
                                    'value': float(latest.get('value', 0)),
                                    'change_24h': float(latest.get('value', 0)) - float(previous.get('value', 0)),
                                    'timestamp': int(latest.get('timestamp', time.time() * 1000))
                                }
                            else:
                                # No valid OI data found
                                self.logger.warning(f"No valid OI data found for {symbol}")
                                sentiment['open_interest'] = {
                                    'value': 0.0,
                                    'change_24h': 0.0,
                                    'timestamp': int(time.time() * 1000)
                                }
                else:
                    # No OI data available
                    self.logger.debug(f"No open interest data in cache for {symbol}")
                    sentiment['open_interest'] = {
                        'value': 0.0,
                        'change_24h': 0.0,
                        'timestamp': int(time.time() * 1000)
                    }
        # Enhanced logging for debugging sentiment data population
        self.logger.info(f"get_market_data: Sentiment dict keys: {list(sentiment.keys())}")
        if 'long_short_ratio' in sentiment:
            self.logger.info(f"get_market_data: long_short_ratio: {sentiment['long_short_ratio']}")
        if 'risk' in sentiment:
            self.logger.info(f"get_market_data: risk data: {sentiment['risk']}")
        if 'liquidations' in sentiment:
            self.logger.info(f"get_market_data: liquidations count: {len(sentiment.get('liquidations', []))}")
        if 'funding_rate' in sentiment:
            self.logger.info(f"get_market_data: funding_rate: {sentiment['funding_rate']}")
        market_data['sentiment'] = sentiment
        
        # Ensure OHLCV data is fetched if missing
        if 'ohlcv' not in market_data or not market_data['ohlcv']:
            self.logger.info(f"OHLCV data missing for {symbol}, fetching now")
            try:
                timeframes = await self._fetch_timeframes(symbol)
                if timeframes:
                    market_data['ohlcv'] = timeframes
                    # Also update symbol cache for future use (store under both keys for compatibility)
                    if symbol in self.data_cache:
                        self.data_cache[symbol]['ohlcv'] = timeframes
                        self.data_cache[symbol]['kline'] = timeframes  # Store under both keys
                    self.logger.info(f"Successfully fetched OHLCV data for {symbol}")
                else:
                    raise DataUnavailableError(
                        message=f"Failed to fetch OHLCV data for {symbol}",
                        data_type="ohlcv"
                    )
            except Exception as e:
                if isinstance(e, DataUnavailableError):
                    raise
                self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
                import traceback
                self.logger.debug(traceback.format_exc())
        
        return market_data
    
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
                    
                    # Ensure OHLCV data is available under both 'kline' and 'ohlcv' keys for compatibility
                    if 'kline' in market_data and market_data['kline']:
                        self.data_cache[symbol_str]['ohlcv'] = market_data['kline']
                    elif 'ohlcv' in market_data and market_data['ohlcv']:
                        self.data_cache[symbol_str]['kline'] = market_data['ohlcv']
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
            # Validate inputs
            if not isinstance(value, (int, float)):
                self.logger.warning(f"Invalid OI value type for {symbol}: {type(value)}")
                return
            
            if value < 0:
                self.logger.warning(f"Negative OI value for {symbol}: {value}")
                return
        
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
            # Handle both old and new structure formats
            current_value = oi_data.get('current', oi_data.get('value', 0.0))
            
            if current_value != value:
                # Ensure we have the correct structure
                if 'current' not in oi_data:
                    # Convert from sentiment structure to history structure
                    oi_data['current'] = oi_data.get('value', 0.0)
                    oi_data['previous'] = oi_data.get('current', 0.0)
                    if 'history' not in oi_data:
                        oi_data['history'] = []
                
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
                    
                    # Don't create synthetic entries - use empty history
                    # Real historical data should come from exchange API
                    self.logger.debug(f"No historical OI data available for {symbol}")
                    # Skip synthetic data creation - history remains empty
                
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
                
                # Throttle open interest logging similar to other WebSocket updates
                now = time.time()
                if now - self.ws_log_throttle['open_interest']['last_log'] >= self.ws_log_throttle['open_interest']['interval']:
                    self.logger.debug(f"Updated open interest for {symbol}: {value} (history: {len(history)} entries)")
                    self.ws_log_throttle['open_interest']['last_log'] = now
                
        except Exception as e:
            self.logger.error(f"Error updating open interest history: {str(e)}")
            self.logger.debug(traceback.format_exc()) 

    def _validate_market_data(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate market data before processing.
        
        Returns:
            bool: True if data is valid, False otherwise
        """
        if not data:
            self.logger.warning(f"No market data for {symbol}")
            return False
            
        # Check for required fields
        required_fields = ['ticker', 'timestamp']
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Missing required field '{field}' for {symbol}")
                return False
        
        # Validate ticker data
        ticker = data.get('ticker', {})
        if not ticker or ticker.get('last_price', 0) <= 0:
            self.logger.warning(f"Invalid ticker data for {symbol}")
            return False
            
        return True

    def get_open_interest_data(self, symbol: str) -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Symbol to get open interest data for
            
        Returns:
            Dict containing open interest data or None if not available
        """
        try:
            if symbol not in self.data_cache:
                return None
                
            if 'open_interest' not in self.data_cache[symbol]:
                return None
                
            return self.data_cache[symbol]['open_interest']
        except Exception as e:
            self.logger.error(f"Error getting open interest data: {str(e)}")
            return None
            
    async def refresh_components(self, symbol: str, components: List[str] = None) -> None:
        """Refresh specific components for a symbol.
        
        Args:
            symbol: Symbol to refresh components for
            components: List of component names to refresh, or None for all
        """
        try:
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
                
            if components is None:
                # Include sentiment-related components by default
                components = ['ticker', 'orderbook', 'trades', 'kline', 'long_short_ratio', 'risk_limits']
                
            # Track new fetches
            fetched_data = {}
            
            # Fetch each component
            for component in components:
                try:
                    if component == 'ticker':
                        # Try to find exchange
                        exchange = await self.exchange_manager.get_primary_exchange()
                        if exchange:
                            ticker = await exchange.fetch_ticker(symbol)
                            if ticker:
                                fetched_data['ticker'] = ticker
                        else:
                            self.logger.error("No exchange available for ticker fetch")
                    
                    elif component == 'orderbook':
                        # Try to find exchange and fetch enhanced orderbook data
                        exchange = await self.exchange_manager.get_primary_exchange()
                        if exchange:
                            enhanced_orderbook_data = await self._fetch_enhanced_orderbook_data(symbol)
                            if enhanced_orderbook_data:
                                fetched_data['orderbook'] = enhanced_orderbook_data['standard_orderbook']
                                fetched_data['rpi_orderbook'] = enhanced_orderbook_data.get('rpi_orderbook', {})
                                fetched_data['enhanced_orderbook'] = enhanced_orderbook_data.get('enhanced_orderbook', {})
                                fetched_data['rpi_enabled'] = enhanced_orderbook_data.get('rpi_enabled', False)
                        else:
                            self.logger.error("No exchange available for orderbook fetch")
                    
                    elif component == 'trades':
                        # Try to find exchange
                        exchange = await self.exchange_manager.get_primary_exchange()
                        if exchange:
                            trades = await exchange.fetch_trades(symbol, 100)
                            if trades:
                                fetched_data['trades'] = trades
                        else:
                            self.logger.error("No exchange available for trades fetch")
                        
                    elif component == 'kline':
                        # Fetch OHLCV data using _fetch_timeframes method
                        try:
                            self.logger.info(f"Fetching OHLCV data for {symbol}")
                            timeframes = await self._fetch_timeframes(symbol)
                            if timeframes:
                                # Initialize ohlcv in data_cache if needed
                                if 'ohlcv' not in self.data_cache[symbol]:
                                    self.data_cache[symbol]['ohlcv'] = {}
                                
                                # Store each timeframe
                                for tf, data in timeframes.items():
                                    self.data_cache[symbol]['ohlcv'][tf] = data
                                
                                self.logger.info(f"Successfully fetched OHLCV data for {symbol} with {len(timeframes)} timeframes")
                                fetched_data['kline'] = True
                            else:
                                self.logger.warning(f"No OHLCV data returned for {symbol}")
                        except Exception as e:
                            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
                            self.logger.debug(traceback.format_exc())
                    
                    elif component == 'long_short_ratio':
                        # Fetch long/short ratio
                        try:
                            self.logger.info(f"Fetching long_short_ratio for {symbol}")
                            exchange = await self.exchange_manager.get_primary_exchange()
                            if exchange and hasattr(exchange, 'fetch_long_short_ratio'):
                                lsr_data = await exchange.fetch_long_short_ratio(symbol)
                                if lsr_data:
                                    self.data_cache[symbol]['long_short_ratio'] = lsr_data
                                    fetched_data['long_short_ratio'] = lsr_data
                                    self.logger.info(f"Successfully fetched long_short_ratio for {symbol}: {lsr_data}")
                                else:
                                    self.logger.warning(f"No long_short_ratio data returned for {symbol}")
                            else:
                                self.logger.warning(f"Exchange doesn't support fetch_long_short_ratio")
                        except Exception as e:
                            self.logger.error(f"Error fetching long_short_ratio for {symbol}: {str(e)}")
                            self.logger.debug(traceback.format_exc())
                        
                except Exception as e:
                    self.logger.error(f"Error refreshing {component} for {symbol}: {str(e)}")
            
            # Update cache with fetched data
            for component, data in fetched_data.items():
                if data:
                    if component != 'kline':  # Skip kline as it's handled separately above
                        self.data_cache[symbol][component] = data
                        
            self.logger.debug(f"Refreshed components for {symbol}: {list(fetched_data.keys())}")
            
        except Exception as e:
            self.logger.error(f"Error refreshing components for {symbol}: {str(e)}")

    async def force_websocket_initialization(self):
        """Force initialize WebSocket connections even if delayed"""
        try:
            self.logger.info("Force initializing WebSocket connections for real-time data feeds")
            
            # Override delay setting temporarily
            original_delay = self.delay_websocket
            self.delay_websocket = False
            
            # Initialize WebSocket manager
            await self._initialize_websocket()
            
            # Restore original delay setting
            self.delay_websocket = original_delay
            
            self.logger.info("✅ WebSocket connections successfully initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to force initialize WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    async def get_websocket_status(self) -> Dict[str, Any]:
        """Get current WebSocket connection status"""
        try:
            if not hasattr(self, 'websocket_manager') or not self.websocket_manager:
                return {
                    "enabled": False,
                    "connected": False,
                    "active_connections": 0,
                    "status": "not_initialized"
                }
            
            # Get status from WebSocket manager
            status = getattr(self.websocket_manager, 'status', {})
            return {
                "enabled": True,
                "connected": status.get('connected', False),
                "active_connections": status.get('active_connections', 0),
                "messages_received": status.get('messages_received', 0),
                "last_message_time": status.get('last_message_time', 0),
                "errors": status.get('errors', 0),
                "status": "connected" if status.get('connected', False) else "disconnected"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting WebSocket status: {str(e)}")
            return {
                "enabled": False,
                "connected": False,
                "active_connections": 0,
                "status": "error",
                "error": str(e)
            }

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            timeframe: Timeframe for candles ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        try:
            self.logger.info(f"Fetching OHLCV data for {symbol} - {timeframe} - {limit} candles")

            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self._ohlcv_cache:
                cached_data = self._ohlcv_cache[cache_key]
                if isinstance(cached_data, dict) and 'data' in cached_data:
                    df = cached_data['data']
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        # Return last 'limit' candles from cache
                        self.logger.info(f"Returning {min(limit, len(df))} candles from cache for {symbol}")
                        return df.tail(limit)

            # If not in cache, fetch from exchange
            exchange = await self.exchange_manager.get_exchange()
            if not exchange:
                self.logger.error("Exchange not available for OHLCV fetch")
                return None

            # Fetch OHLCV data
            ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

            if not ohlcv_data:
                self.logger.warning(f"No OHLCV data returned for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Cache the data
            self._ohlcv_cache[cache_key] = {
                'data': df,
                'timestamp': datetime.now()
            }

            self.logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            return None

    async def _fetch_enhanced_orderbook_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch both standard and RPI orderbook data and merge them.

        Args:
            symbol: Trading symbol to fetch data for

        Returns:
            Dict containing standard, RPI, and enhanced orderbook data
        """
        import time
        start_time = time.time()

        try:
            self.logger.debug(f"🔍 [RPI_DEBUG] Starting enhanced orderbook fetch for {symbol}")

            exchange_client = await self.exchange_manager.get_primary_exchange()
            if not exchange_client:
                self.logger.error("No exchange client available for enhanced orderbook fetch")
                return {}

            self.logger.debug(f"🔍 [RPI_DEBUG] Exchange client obtained: {type(exchange_client).__name__}")

            # Fetch both standard and RPI orderbook concurrently
            self.logger.debug(f"🔍 [RPI_DEBUG] Setting up concurrent fetch tasks")

            standard_task = self._fetch_with_rate_limiting(
                'v5/market/orderbook',
                lambda: exchange_client.fetch_order_book(symbol, limit=50)
            )
            self.logger.debug(f"🔍 [RPI_DEBUG] Standard orderbook task created")

            # Check if RPI method is available before creating task
            rpi_task = None
            if hasattr(exchange_client, 'fetch_rpi_orderbook'):
                self.logger.debug(f"🔍 [RPI_DEBUG] RPI method available, creating RPI task")
                rpi_task = self._fetch_with_rate_limiting(
                    'v5/market/rpi_orderbook',
                    lambda: exchange_client.fetch_rpi_orderbook(symbol, limit=50)
                )
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] RPI method not available on exchange client")

            # Execute tasks
            fetch_start = time.time()
            if rpi_task:
                self.logger.debug(f"🔍 [RPI_DEBUG] Executing concurrent fetch tasks (standard + RPI)")
                standard_ob, rpi_ob = await asyncio.gather(standard_task, rpi_task, return_exceptions=True)
                fetch_time = (time.time() - fetch_start) * 1000
                self.logger.debug(f"🔍 [RPI_DEBUG] Concurrent fetch completed in {fetch_time:.2f}ms")

                # Handle exceptions in RPI fetch
                if isinstance(rpi_ob, Exception):
                    self.logger.warning(f"RPI fetch failed for {symbol}: {rpi_ob}, using standard orderbook only")
                    self.logger.debug(f"🔍 [RPI_DEBUG] RPI fetch exception type: {type(rpi_ob).__name__}")
                    rpi_ob = {}
                else:
                    self.logger.debug(f"🔍 [RPI_DEBUG] RPI fetch successful, data keys: {list(rpi_ob.keys()) if rpi_ob else 'empty'}")
                    if rpi_ob:
                        bids_count = len(rpi_ob.get('b', []))
                        asks_count = len(rpi_ob.get('a', []))
                        self.logger.debug(f"🔍 [RPI_DEBUG] RPI data: {bids_count} bids, {asks_count} asks")
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] Executing standard fetch task only")
                standard_ob = await standard_task
                fetch_time = (time.time() - fetch_start) * 1000
                self.logger.debug(f"🔍 [RPI_DEBUG] Standard fetch completed in {fetch_time:.2f}ms")
                rpi_ob = {}

            # Handle exceptions in standard fetch
            if isinstance(standard_ob, Exception):
                self.logger.error(f"Standard orderbook fetch failed for {symbol}: {standard_ob}")
                self.logger.debug(f"🔍 [RPI_DEBUG] Standard fetch exception type: {type(standard_ob).__name__}")
                return {}

            self.logger.debug(f"🔍 [RPI_DEBUG] Standard orderbook fetch successful")
            if standard_ob:
                bids_count = len(standard_ob.get('bids', []))
                asks_count = len(standard_ob.get('asks', []))
                self.logger.debug(f"🔍 [RPI_DEBUG] Standard data: {bids_count} bids, {asks_count} asks")

            # Merge RPI data into standard orderbook format
            merge_start = time.time()
            self.logger.debug(f"🔍 [RPI_DEBUG] Starting RPI data merge")
            enhanced_orderbook = self._merge_rpi_data(standard_ob, rpi_ob)
            merge_time = (time.time() - merge_start) * 1000
            self.logger.debug(f"🔍 [RPI_DEBUG] RPI merge completed in {merge_time:.2f}ms")

            if enhanced_orderbook.get('enhanced'):
                enhanced_bids = len(enhanced_orderbook.get('bids', []))
                enhanced_asks = len(enhanced_orderbook.get('asks', []))
                self.logger.debug(f"🔍 [RPI_DEBUG] Enhanced orderbook: {enhanced_bids} bids, {enhanced_asks} asks")
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] No enhancement applied, using standard orderbook")

            total_time = (time.time() - start_time) * 1000
            rpi_enabled = bool(rpi_ob)

            result = {
                'standard_orderbook': standard_ob,
                'rpi_orderbook': rpi_ob,
                'enhanced_orderbook': enhanced_orderbook,
                'rpi_enabled': rpi_enabled,
                'symbol': symbol,
                'timestamp': int(time.time() * 1000)
            }

            self.logger.debug(f"🔍 [RPI_DEBUG] Enhanced orderbook fetch completed in {total_time:.2f}ms")
            self.logger.debug(f"🔍 [RPI_DEBUG] Result summary: RPI enabled={rpi_enabled}, enhanced={enhanced_orderbook.get('enhanced', False)}")

            return result

        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            self.logger.error(f"Error fetching enhanced orderbook for {symbol}: {str(e)}")
            self.logger.debug(f"🔍 [RPI_DEBUG] Enhanced orderbook fetch failed after {total_time:.2f}ms")
            self.logger.debug(f"🔍 [RPI_DEBUG] Exception details: {traceback.format_exc()}")
            return {}

    def _merge_rpi_data(self, standard_ob: Dict, rpi_ob: Dict) -> Dict:
        """
        Merge RPI data with standard orderbook to get total liquidity.

        Args:
            standard_ob: Standard orderbook data
            rpi_ob: RPI orderbook data

        Returns:
            Enhanced orderbook with merged liquidity
        """
        self.logger.debug(f"🔍 [RPI_DEBUG] Starting RPI data merge process")
        self.logger.debug(f"🔍 [RPI_DEBUG] Standard OB available: {bool(standard_ob)}")
        self.logger.debug(f"🔍 [RPI_DEBUG] RPI OB available: {bool(rpi_ob)}")

        if not rpi_ob or not rpi_ob.get('b') or not rpi_ob.get('a'):
            self.logger.debug(f"🔍 [RPI_DEBUG] No RPI data to merge, returning standard orderbook")
            if not rpi_ob:
                self.logger.debug(f"🔍 [RPI_DEBUG] RPI orderbook is empty")
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] RPI bids: {len(rpi_ob.get('b', []))}, asks: {len(rpi_ob.get('a', []))}")
            return standard_ob

        try:
            standard_bids = standard_ob.get('bids', [])
            standard_asks = standard_ob.get('asks', [])
            rpi_bids = rpi_ob.get('b', [])
            rpi_asks = rpi_ob.get('a', [])

            self.logger.debug(f"🔍 [RPI_DEBUG] Input data sizes:")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Standard bids: {len(standard_bids)}, asks: {len(standard_asks)}")
            self.logger.debug(f"🔍 [RPI_DEBUG]   RPI bids: {len(rpi_bids)}, asks: {len(rpi_asks)}")

            # Enhance bids and asks with RPI liquidity
            self.logger.debug(f"🔍 [RPI_DEBUG] Merging bid side data")
            enhanced_bids = self._merge_side_data(
                standard_bids,
                rpi_bids,
                is_bid=True
            )

            self.logger.debug(f"🔍 [RPI_DEBUG] Merging ask side data")
            enhanced_asks = self._merge_side_data(
                standard_asks,
                rpi_asks,
                is_bid=False
            )

            self.logger.debug(f"🔍 [RPI_DEBUG] Merge completed:")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Enhanced bids: {len(enhanced_bids)}, asks: {len(enhanced_asks)}")

            # Log sample of enhanced data for validation
            if enhanced_bids:
                sample_bid = enhanced_bids[0]
                self.logger.debug(f"🔍 [RPI_DEBUG] Sample enhanced bid: {sample_bid}")
            if enhanced_asks:
                sample_ask = enhanced_asks[0]
                self.logger.debug(f"🔍 [RPI_DEBUG] Sample enhanced ask: {sample_ask}")

            result = {
                'bids': enhanced_bids,
                'asks': enhanced_asks,
                'timestamp': standard_ob.get('timestamp'),
                'enhanced': True
            }

            self.logger.debug(f"🔍 [RPI_DEBUG] RPI merge successful - orderbook enhanced")
            return result

        except Exception as e:
            self.logger.error(f"Error merging RPI data: {str(e)}")
            self.logger.debug(f"🔍 [RPI_DEBUG] RPI merge failed: {traceback.format_exc()}")
            return standard_ob

    def _merge_side_data(self, standard_levels: List, rpi_levels: List, is_bid: bool) -> List:
        """
        Merge one side of orderbook with RPI data.

        Args:
            standard_levels: Standard orderbook levels [[price, size], ...]
            rpi_levels: RPI levels [[price, non_rpi_size, rpi_size], ...]
            is_bid: True for bids (descending), False for asks (ascending)

        Returns:
            Merged orderbook levels with enhanced liquidity
        """
        side_name = "bids" if is_bid else "asks"
        self.logger.debug(f"🔍 [RPI_DEBUG] Merging {side_name} - standard: {len(standard_levels)}, RPI: {len(rpi_levels)} levels")

        price_to_total = {}
        standard_processed = 0
        rpi_processed = 0

        # Add standard sizes
        self.logger.debug(f"🔍 [RPI_DEBUG] Processing standard {side_name} levels")
        for i, level in enumerate(standard_levels):
            if len(level) >= 2:
                try:
                    price, size = float(level[0]), float(level[1])
                    price_to_total[price] = price_to_total.get(price, 0.0) + size
                    standard_processed += 1

                    if i < 3:  # Log first 3 levels
                        self.logger.debug(f"🔍 [RPI_DEBUG]   Standard level {i+1}: price={price:.2f}, size={size:.4f}")
                except (ValueError, IndexError) as e:
                    self.logger.debug(f"🔍 [RPI_DEBUG] Skipping invalid standard level {i}: {level}, error: {e}")
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] Skipping malformed standard level {i}: {level}")

        # Add RPI sizes (non_rpi + rpi = total additional)
        self.logger.debug(f"🔍 [RPI_DEBUG] Processing RPI {side_name} levels")
        for i, level in enumerate(rpi_levels):
            if len(level) >= 3:
                try:
                    price, non_rpi, rpi = float(level[0]), float(level[1]), float(level[2])
                    total_additional = non_rpi + rpi

                    # Track before and after for this price level
                    original_size = price_to_total.get(price, 0.0)
                    price_to_total[price] = original_size + total_additional
                    rpi_processed += 1

                    if i < 3:  # Log first 3 levels
                        self.logger.debug(f"🔍 [RPI_DEBUG]   RPI level {i+1}: price={price:.2f}, non_rpi={non_rpi:.4f}, rpi={rpi:.4f}, total_add={total_additional:.4f}")
                        self.logger.debug(f"🔍 [RPI_DEBUG]     Price {price:.2f}: {original_size:.4f} -> {price_to_total[price]:.4f} (+{total_additional:.4f})")

                except (ValueError, IndexError) as e:
                    self.logger.debug(f"🔍 [RPI_DEBUG] Skipping invalid RPI level {i}: {level}, error: {e}")
            else:
                self.logger.debug(f"🔍 [RPI_DEBUG] Skipping malformed RPI level {i}: {level}")

        # Sort and return
        self.logger.debug(f"🔍 [RPI_DEBUG] Sorting merged {side_name} data (reverse={is_bid})")
        sorted_items = sorted(price_to_total.items(), key=lambda x: x[0], reverse=is_bid)
        result = [[price, size] for price, size in sorted_items]

        self.logger.debug(f"🔍 [RPI_DEBUG] Merge summary for {side_name}:")
        self.logger.debug(f"🔍 [RPI_DEBUG]   Standard processed: {standard_processed}/{len(standard_levels)}")
        self.logger.debug(f"🔍 [RPI_DEBUG]   RPI processed: {rpi_processed}/{len(rpi_levels)}")
        self.logger.debug(f"🔍 [RPI_DEBUG]   Unique price levels: {len(price_to_total)}")
        self.logger.debug(f"🔍 [RPI_DEBUG]   Final result levels: {len(result)}")

        if result:
            top_level = result[0]
            self.logger.debug(f"🔍 [RPI_DEBUG]   Best level: price={top_level[0]:.2f}, size={top_level[1]:.4f}")

        return result