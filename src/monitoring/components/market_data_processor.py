"""Market data processing component for fetching and standardizing market data."""

import logging
import traceback
from typing import Dict, Any, Optional, List, Union
import pandas as pd

from ..utilities import TimestampUtility, MarketDataValidator


class MarketDataProcessor:
    """Handles market data fetching, processing, and standardization."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        market_data_manager=None,
        validator: Optional[MarketDataValidator] = None
    ):
        """Initialize market data processor.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
            market_data_manager: Market data manager for fetching data
            validator: Market data validator instance
        """
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.market_data_manager = market_data_manager
        self.validator = validator or MarketDataValidator(logger=self.logger)
        
        # Cache settings
        self._cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes default
        
        # Data caches
        self._market_data_cache = {}
        self._ohlcv_cache = {}
        self._last_ohlcv_update = {}
        
        # Timestamp utility
        self.timestamp_utility = TimestampUtility
        
        # Timeframe configuration
        self.timeframe_config = self.config.get('timeframes', {
            'base': {'interval': '1m'},
            'ltf': {'interval': '5m'},
            'mtf': {'interval': '30m'},
            'htf': {'interval': '4h'}
        })
    
    async def fetch_market_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch market data for a symbol from the market data manager with enhanced caching.
        
        Args:
            symbol: The symbol to fetch market data for
            force_refresh: If True, force refresh of market data (bypass cache)
            
        Returns:
            Market data dictionary with various components
        """
        try:
            if not self.market_data_manager:
                self.logger.error("Market data manager not initialized")
                return {}

            current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
            
            # Check if we have valid cached market data
            if (not force_refresh and
                symbol in self._market_data_cache and
                current_time - self._market_data_cache[symbol].get('fetch_time', 0) < self._cache_ttl):
                self.logger.debug(f"Using cached market data for {symbol} (age: {current_time - self._market_data_cache[symbol]['fetch_time']}s)")
                return self._market_data_cache[symbol]['data']

            # If only force refreshing OHLCV but we have recent other data, do partial refresh
            if force_refresh and symbol in self._market_data_cache:
                await self.market_data_manager.refresh_components(symbol, components=['kline'])
                # Fetch only the updated data and merge with cached data
                market_data = await self.market_data_manager.get_market_data(symbol)
                if market_data and self._market_data_cache[symbol]['data']:
                    # Update only the OHLCV component, keep other data
                    cached_data = self._market_data_cache[symbol]['data']
                    cached_data['ohlcv'] = market_data.get('ohlcv', cached_data['ohlcv'])
                    # Update the cache timestamp
                    self._market_data_cache[symbol]['fetch_time'] = current_time
                    self.logger.info(f"Updated OHLCV in cache for {symbol} while preserving other data")
                    return cached_data
            
            # Need fresh data, fetch everything
            self.logger.info(f"Fetching fresh market data for {symbol}")
            market_data = await self.market_data_manager.get_market_data(symbol)
            
            # Update the cache with complete data
            if market_data:
                # Ensure symbol field is always included
                if 'symbol' not in market_data:
                    market_data['symbol'] = symbol
                    
                # Update both caches
                self._market_data_cache[symbol] = {
                    'data': market_data,
                    'fetch_time': current_time,
                    'fetch_time_formatted': self.timestamp_utility.format_utc_time(current_time * 1000)
                }
                
                # Also update the OHLCV-specific cache for PDF reports
                if 'ohlcv' in market_data and market_data['ohlcv']:
                    self._ohlcv_cache[symbol] = {
                        'processed': market_data['ohlcv'],
                        'raw_responses': market_data.get('raw_responses', {}),
                        'fetch_time': current_time,
                        'fetch_time_formatted': self.timestamp_utility.format_utc_time(current_time * 1000)
                    }
                    self._last_ohlcv_update[symbol] = current_time
                    self.logger.info(f"Updated caches for {symbol} with fresh market data")
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}
    
    def standardize_ohlcv(self, raw_ohlcv: Any) -> Dict[str, Any]:
        """Standardize OHLCV data from the exchange into a consistent format.
        
        Args:
            raw_ohlcv: The raw OHLCV data from the exchange
            
        Returns:
            Dict containing standardized OHLCV data with timeframes
        """
        try:
            self.logger.debug("Starting standardization of OHLCV data")
            
            if not raw_ohlcv or len(raw_ohlcv) == 0:
                self.logger.warning("Empty OHLCV data received")
                return self._empty_ohlcv_result()
            
            # Log raw data information    
            if isinstance(raw_ohlcv, list):
                self.logger.debug(f"Raw OHLCV is a list with {len(raw_ohlcv)} entries")
            elif isinstance(raw_ohlcv, dict):
                self.logger.debug(f"Raw OHLCV is a dict with keys: {list(raw_ohlcv.keys())}")
            else:
                self.logger.debug(f"Raw OHLCV has type: {type(raw_ohlcv)}")
                
            # Convert to dataframe based on input format
            df = self._convert_to_dataframe(raw_ohlcv)
            if df is None or df.empty:
                return self._empty_ohlcv_result()
            
            # Ensure timestamp is numeric and sort
            df = self._prepare_dataframe(df)
            
            # Create timeframe data with proper resampling
            result = self._create_timeframes(df)
            
            # Log the shapes of each timeframe DataFrame
            self.logger.debug("Standardized OHLCV data shapes:")
            for tf, tf_df in result.items():
                self.logger.debug(f"  {tf}: {tf_df.shape}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error standardizing OHLCV data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return self._empty_ohlcv_result()
    
    def _empty_ohlcv_result(self) -> Dict[str, pd.DataFrame]:
        """Return empty OHLCV result structure."""
        return {
            'base': pd.DataFrame(),
            'ltf': pd.DataFrame(),
            'mtf': pd.DataFrame(),
            'htf': pd.DataFrame()
        }
    
    def _convert_to_dataframe(self, raw_ohlcv: Any) -> Optional[pd.DataFrame]:
        """Convert raw OHLCV data to pandas DataFrame."""
        try:
            if isinstance(raw_ohlcv, list):
                if len(raw_ohlcv) == 0:
                    return None
                    
                # Handle different formats from exchanges
                if isinstance(raw_ohlcv[0], list):
                    # Format: [timestamp, open, high, low, close, volume]
                    self.logger.debug(f"Processing list of lists format with {len(raw_ohlcv)} entries")
                    df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    self.logger.debug(f"Created DataFrame with shape {df.shape}")
                    return df
                    
                elif isinstance(raw_ohlcv[0], dict):
                    # Common dict format from exchanges
                    self.logger.debug(f"Processing list of dicts format with {len(raw_ohlcv)} entries")
                    df = pd.DataFrame(raw_ohlcv)
                    
                    # Rename columns if needed
                    column_mapping = {
                        't': 'timestamp',
                        'time': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    }
                    
                    # Log original columns before mapping
                    self.logger.debug(f"Original columns: {df.columns.tolist()}")
                    
                    df = df.rename(columns={col: new_col for col, new_col in column_mapping.items() if col in df.columns})
                    self.logger.debug(f"DataFrame after column mapping: {df.shape}, columns: {df.columns.tolist()}")
                    return df
                    
            elif isinstance(raw_ohlcv, dict):
                # Some exchanges return dict with timeframes
                self.logger.debug(f"Processing dictionary format with keys: {list(raw_ohlcv.keys())}")
                timeframes = {}
                for tf_key, candles in raw_ohlcv.items():
                    if isinstance(candles, list) and len(candles) > 0:
                        self.logger.debug(f"Processing timeframe {tf_key} with {len(candles)} candles")
                        tf_df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        timeframes[tf_key] = tf_df
                
                if timeframes:
                    # Return the first timeframe as base data for now
                    return list(timeframes.values())[0]
                
                # Handle other dict formats
                self.logger.warning(f"Unsupported OHLCV dict format: {list(raw_ohlcv.keys())}")
                return None
                
            else:
                self.logger.warning(f"Unsupported OHLCV data type: {type(raw_ohlcv)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error converting raw OHLCV to DataFrame: {str(e)}")
            return None
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for processing."""
        try:
            # Ensure timestamp is numeric
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_numeric(df['timestamp'])
            
            # Sort by timestamp
            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col])
            
            # Set timestamp as index for resampling
            if 'timestamp' in df.columns:
                # Convert timestamp to datetime for proper resampling
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.set_index('datetime')
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error preparing DataFrame: {str(e)}")
            return df
    
    def _create_timeframes(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create different timeframes from base data."""
        try:
            # Map CCXT timeframe strings to pandas resample rule
            timeframe_map = {
                '1m': '1Min', '5m': '5Min', '15m': '15Min', '30m': '30Min',
                '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
                '1d': '1D', '3d': '3D', '1w': '1W', '1M': '1M'
            }
            
            result = {}
            
            # Base timeframe (usually the raw data)
            base_tf = self.timeframe_config.get('base', {}).get('interval', '1m')
            result['base'] = df.copy().reset_index()  # No resampling needed for base
            
            # LTF (Lower TimeFrame)
            ltf = self.timeframe_config.get('ltf', {}).get('interval', '5m')
            ltf_rule = timeframe_map.get(ltf, '5Min')
            result['ltf'] = self._resample_ohlcv(df, ltf_rule)
            
            # MTF (Middle TimeFrame)
            mtf = self.timeframe_config.get('mtf', {}).get('interval', '30m')
            mtf_rule = timeframe_map.get(mtf, '30Min')
            result['mtf'] = self._resample_ohlcv(df, mtf_rule)
            
            # HTF (Higher TimeFrame)
            htf = self.timeframe_config.get('htf', {}).get('interval', '4h')
            htf_rule = timeframe_map.get(htf, '4h')
            result['htf'] = self._resample_ohlcv(df, htf_rule)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating timeframes: {str(e)}")
            return self._empty_ohlcv_result()
    
    def _resample_ohlcv(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """Resample OHLCV data to a different timeframe.
        
        Args:
            df: DataFrame with OHLCV data indexed by datetime
            rule: Pandas resampling rule string
            
        Returns:
            Resampled DataFrame
        """
        if df.empty:
            self.logger.warning(f"Cannot resample empty DataFrame with rule {rule}")
            return df
        
        self.logger.debug(f"Resampling with rule: {rule}, input data has {len(df)} rows")
        
        try:
            # Make sure timestamp is properly set as index
            if df.index.name != 'datetime' and 'datetime' in df.columns:
                df = df.set_index('datetime')
                self.logger.debug("Setting datetime as index before resampling")
            
            # Handle columns that might be missing
            agg_dict = {}
            for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']:
                if col in df.columns:
                    if col == 'open':
                        agg_dict[col] = 'first'
                    elif col == 'high':
                        agg_dict[col] = 'max'
                    elif col == 'low':
                        agg_dict[col] = 'min'
                    elif col == 'close':
                        agg_dict[col] = 'last'
                    elif col == 'volume':
                        agg_dict[col] = 'sum'
                    elif col == 'timestamp':
                        agg_dict[col] = 'first'  # Keep original timestamp
            
            # Perform the resampling
            resampled = df.resample(rule).agg(agg_dict)
            
            # Fill missing values for volume if needed
            if 'volume' in resampled.columns:
                resampled['volume'] = resampled['volume'].fillna(0)
            
            # Forward fill price columns (open, high, low, close)
            for col in ['open', 'high', 'low', 'close']:
                if col in resampled.columns:
                    resampled[col] = resampled[col].ffill()
            
            # Reset index to have datetime as a column
            resampled = resampled.reset_index()
            
            # Log data points before and after resampling
            self.logger.debug(f"Resampling with rule {rule}: {len(df)} rows -> {len(resampled)} rows")
            
            # Drop rows with all NaN values if any
            if resampled.isna().all(axis=1).any():
                orig_len = len(resampled)
                resampled = resampled.dropna(how='all')
                dropped = orig_len - len(resampled)
                if dropped > 0:
                    self.logger.debug(f"Dropped {dropped} rows with all NaN values after resampling")
            
            return resampled
            
        except Exception as e:
            self.logger.error(f"Error during resampling with rule {rule}: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Return the original data if resampling fails
            return df.reset_index() if hasattr(df, 'reset_index') else df
    
    async def process_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Process a symbol and return standardized market data.
        
        Args:
            symbol: Symbol to process
            
        Returns:
            Processed market data or None if failed
        """
        try:
            # Fetch raw market data
            market_data = await self.fetch_market_data(symbol)
            if not market_data:
                self.logger.warning(f"No market data received for {symbol}")
                return None
            
            # Validate the market data
            if not await self.validator.validate_market_data(market_data):
                self.logger.warning(f"Market data validation failed for {symbol}")
                return None
            
            # Standardize OHLCV if present
            if 'ohlcv' in market_data and market_data['ohlcv']:
                market_data['ohlcv'] = self.standardize_ohlcv(market_data['ohlcv'])
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None
    
    def get_cached_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data for a symbol.
        
        Args:
            symbol: Symbol to get cached data for
            
        Returns:
            Cached market data or None if not found/expired
        """
        if symbol not in self._market_data_cache:
            return None
        
        current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
        cache_entry = self._market_data_cache[symbol]
        
        if current_time - cache_entry.get('fetch_time', 0) > self._cache_ttl:
            # Cache expired, remove it
            del self._market_data_cache[symbol]
            return None
        
        return cache_entry['data']
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cache for a specific symbol or all symbols.
        
        Args:
            symbol: Symbol to clear cache for, or None to clear all
        """
        if symbol:
            self._market_data_cache.pop(symbol, None)
            self._ohlcv_cache.pop(symbol, None)
            self._last_ohlcv_update.pop(symbol, None)
        else:
            self._market_data_cache.clear()
            self._ohlcv_cache.clear()
            self._last_ohlcv_update.clear()
        
        self.logger.info(f"Cleared cache for {'all symbols' if not symbol else symbol}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        stats = {
            'total_cached_symbols': len(self._market_data_cache),
            'cache_ttl': self._cache_ttl,
            'symbols': {}
        }
        
        for symbol, cache_entry in self._market_data_cache.items():
            age = current_time - cache_entry.get('fetch_time', 0)
            stats['symbols'][symbol] = {
                'age_seconds': age,
                'expired': age > self._cache_ttl,
                'fetch_time': cache_entry.get('fetch_time_formatted', 'Unknown')
            }
        
        return stats 