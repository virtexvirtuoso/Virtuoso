import pandas as pd
import re
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import math
import time
import random
import asyncio
from datetime import datetime, timedelta
import logging
import sys
import os
import traceback
import gc
import json
from collections import defaultdict
from cachetools import TTLCache
import shutil

# Import for PDF report generation
from src.core.reporting.report_manager import ReportManager
from src.core.reporting.pdf_generator import ReportGenerator

# Enhanced premium calculation imports
from datetime import timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/market_reporter.log')
    ]
)
logger = logging.getLogger(__name__)



class EnhancedFuturesPremiumMixin:
    """Enhanced futures premium calculation mixin for MarketReporter."""
    
    def _init_enhanced_premium(self):
        """Initialize enhanced premium calculation capabilities."""
        self._aiohttp_session = None
        self._premium_api_base_url = getattr(self, 'premium_api_base_url', "https://api.bybit.com")
        self._enable_enhanced_premium = getattr(self, 'enable_enhanced_premium', True)
        self._enable_premium_validation = getattr(self, 'enable_premium_validation', True)
        self._premium_calculation_stats = {
            'improved_success': 0,
            'improved_failures': 0,
            'fallback_usage': 0,
            'validation_matches': 0,
            'validation_mismatches': 0
        }
    
    async def _get_aiohttp_session(self) -> 'aiohttp.ClientSession':
        """Get or create aiohttp session for direct API calls."""
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session
    
    async def _close_aiohttp_session(self):
        """Close aiohttp session on cleanup."""
        if self._aiohttp_session:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
    
    async def _calculate_single_premium_enhanced(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """Enhanced single premium calculation with improved API usage."""
        if not getattr(self, '_enable_enhanced_premium', True):
            return await self._calculate_single_premium_original(symbol, all_markets)
        
        start_time = time.time()
        
        try:
            # Extract base coin
            base_coin = self._extract_base_coin_enhanced(symbol)
            if not base_coin:
                self.logger.warning(f"Could not extract base coin from symbol: {symbol}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            self.logger.debug(f"Enhanced premium calculation for {symbol} (base: {base_coin})")
            
            # Get perpetual data using enhanced method
            perpetual_data = await self._get_perpetual_data_enhanced(base_coin)
            if not perpetual_data:
                self.logger.warning(f"No perpetual data found via enhanced method for {base_coin}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Extract pricing data
            mark_price = float(perpetual_data.get('markPrice', 0))
            index_price = float(perpetual_data.get('indexPrice', 0))
            
            if mark_price <= 0 or index_price <= 0:
                self.logger.warning(f"Invalid pricing data for {base_coin}: mark={mark_price}, index={index_price}")
                self._premium_calculation_stats['improved_failures'] += 1
                return await self._fallback_to_original_method(symbol, all_markets)
            
            # Calculate perpetual premium
            perpetual_premium = ((mark_price - index_price) / index_price) * 100
            
            # Get quarterly contracts (simplified for initial implementation)
            quarterly_data = []
            quarterly_futures_count = 0
            
            # Validate with Bybit's premium index (if enabled)
            validation_data = None
            if getattr(self, '_enable_premium_validation', True):
                validation_data = await self._validate_with_bybit_premium_index(base_coin)
                if validation_data:
                    bybit_premium = validation_data.get('bybit_premium_index', 0) * 100
                    if abs(perpetual_premium - bybit_premium) < 0.05:  # 5 basis points tolerance
                        self._premium_calculation_stats['validation_matches'] += 1
                    else:
                        self._premium_calculation_stats['validation_mismatches'] += 1
                        self.logger.warning(f"Premium validation mismatch for {base_coin}: "
                                          f"calculated={perpetual_premium:.4f}%, bybit={bybit_premium:.4f}%")
            
            # Compile result (backward compatible)
            result = {
                'premium': f"{perpetual_premium:.4f}%",
                'premium_value': perpetual_premium,
                'premium_type': "📈 Contango" if perpetual_premium > 0 else "📉 Backwardation",
                'mark_price': mark_price,
                'index_price': index_price,
                'last_price': float(perpetual_data.get('lastPrice', mark_price)),
                'funding_rate': perpetual_data.get('fundingRate', 0),
                'timestamp': int(datetime.now().timestamp() * 1000),
                'quarterly_futures_count': quarterly_futures_count,
                'futures_price': 0,
                'futures_basis': "0.00%",
                'futures_contracts': quarterly_data,
                'weekly_futures_count': 0,
                'data_source': 'enhanced_api_v5',
                'data_quality': 'high',
                'calculation_method': 'enhanced_perpetual_vs_index',
                'processing_time_ms': round((time.time() - start_time) * 1000, 2),
                'bybit_validation': validation_data,
                'validation_status': 'validated' if validation_data else 'not_validated'
            }
            
            self._premium_calculation_stats['improved_success'] += 1
            self.logger.debug(f"Enhanced premium calculation successful for {symbol}: {perpetual_premium:.4f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced premium calculation for {symbol}: {e}")
            self._premium_calculation_stats['improved_failures'] += 1
            return await self._fallback_to_original_method(symbol, all_markets)
    
    def _extract_base_coin_enhanced(self, symbol: str) -> Optional[str]:
        """Enhanced base coin extraction."""
        try:
            if '/' in symbol:
                return symbol.split('/')[0].upper()
            elif symbol.endswith('USDT'):
                return symbol.replace('USDT', '').upper()
            elif ':' in symbol:
                return symbol.split(':')[0].replace('USDT', '').upper()
            else:
                return symbol.upper()
        except Exception:
            return None
    
    async def _get_perpetual_data_enhanced(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Get perpetual contract data using enhanced API method."""
        session = await self._get_aiohttp_session()
        
        try:
            perpetual_symbol = f"{base_coin}USDT"
            ticker_url = f"{self._premium_api_base_url}/v5/market/tickers"
            params = {'category': 'linear', 'symbol': perpetual_symbol}
            
            async with session.get(ticker_url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        ticker_list = data.get('result', {}).get('list', [])
                        if ticker_list:
                            return ticker_list[0]
                        
        except Exception as e:
            self.logger.error(f"Error getting enhanced perpetual data for {base_coin}: {e}")
        
        return None
    
    async def _validate_with_bybit_premium_index(self, base_coin: str) -> Optional[Dict[str, Any]]:
        """Validate calculations using Bybit's own premium index data."""
        session = await self._get_aiohttp_session()
        
        try:
            symbol = f"{base_coin}USDT"
            url = f"{self._premium_api_base_url}/v5/market/premium-index-price-kline"
            params = {'category': 'linear', 'symbol': symbol, 'interval': '1', 'limit': 1}
            
            async with session.get(url, params=params, timeout=3) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        kline_data = data.get('result', {}).get('list', [])
                        if kline_data:
                            latest = kline_data[0]
                            return {
                                'bybit_premium_index': float(latest[4]),
                                'timestamp': int(latest[0]),
                                'source': 'premium_index_kline',
                                'validation_method': 'enhanced'
                            }
                            
        except Exception as e:
            self.logger.debug(f"Could not validate with Bybit premium index for {base_coin}: {e}")
        
        return None
    
    async def _fallback_to_original_method(self, symbol: str, all_markets: Dict = None) -> Optional[Dict[str, Any]]:
        """Fallback to the original _calculate_single_premium method."""
        self._premium_calculation_stats['fallback_usage'] += 1
        self.logger.info(f"Falling back to original premium calculation method for {symbol}")
        
        try:
            return await self._calculate_single_premium_original(symbol, all_markets)
        except Exception as e:
            self.logger.error(f"Error in fallback premium calculation for {symbol}: {e}")
            return None
    
    def get_premium_calculation_stats(self) -> Dict[str, Any]:
        """Get statistics about premium calculation performance."""
        total_attempts = (self._premium_calculation_stats['improved_success'] + 
                         self._premium_calculation_stats['improved_failures'])
        
        return {
            'enhanced_method': {
                'success_count': self._premium_calculation_stats['improved_success'],
                'failure_count': self._premium_calculation_stats['improved_failures'],
                'success_rate': (self._premium_calculation_stats['improved_success'] / max(total_attempts, 1)) * 100,
                'total_attempts': total_attempts
            },
            'fallback_usage': {
                'count': self._premium_calculation_stats['fallback_usage'],
                'percentage': (self._premium_calculation_stats['fallback_usage'] / max(total_attempts, 1)) * 100
            },
            'validation': {
                'matches': self._premium_calculation_stats['validation_matches'],
                'mismatches': self._premium_calculation_stats['validation_mismatches'],
                'match_rate': (self._premium_calculation_stats['validation_matches'] / 
                              max(self._premium_calculation_stats['validation_matches'] + 
                                  self._premium_calculation_stats['validation_mismatches'], 1)) * 100
            }
        }


class MarketReporter(EnhancedFuturesPremiumMixin):
    """Market reporter class for generating comprehensive market analysis."""
    
    def __init__(self, exchange: Any = None, logger: Optional[logging.Logger] = None, top_symbols_manager: Any = None, alert_manager: Any = None):

        # Initialize enhanced premium calculation
        self._init_enhanced_premium()
        self.enable_enhanced_premium = True  # Feature flag
        self.enable_premium_validation = True  # Validation flag
        self.premium_api_base_url = "https://api.bybit.com"  # Configurable
        """Initialize market reporter with exchange connection and optional managers."""
        self.exchange = exchange
        self.logger = logger or logging.getLogger(__name__)
        self.top_symbols_manager = top_symbols_manager
        self.alert_manager = alert_manager
        
        # Add Bybit-specific field mappings 
        self.BYBIT_FIELD_MAPPINGS = {
            'mark_price': ['markPrice', 'mark_price'],
            'index_price': ['indexPrice', 'index_price'],
            'funding_rate': ['fundingRate', 'funding_rate'],
            'open_interest': ['openInterest', 'open_interest', 'oi'],
            'turnover': ['turnover24h', 'turnover', 'volume24hValue'],
            'volume': ['volume', 'volume24h']
        }
        
        # Initialize PDF generator and report manager
        try:
            # Check for centralized template configuration first
            template_dir = None
            config_file = os.path.join(os.getcwd(), "config", "templates_config.json")
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                        if 'template_directory' in config_data:
                            template_dir = config_data['template_directory']
                            self.logger.info(f"Using template directory from config file: {template_dir}")
                except Exception as e:
                    self.logger.warning(f"Error loading template config: {str(e)}")
            
            # Fall back to default locations if needed
            if not template_dir or not os.path.exists(template_dir):
                template_dir = os.path.join(os.getcwd(), "src/core/reporting/templates")
                # Removed fallback to root templates directory to prevent file recreation
                if not os.path.exists(template_dir):
                    self.logger.warning(f"Template directory not found: {template_dir}")
                    self.logger.warning("Please ensure templates exist in src/core/reporting/templates/")
                    template_dir = None
            
            if os.path.exists(template_dir):
                self.logger.info(f"Initializing PDF generator with template directory: {template_dir}")
                self.pdf_generator = ReportGenerator(template_dir=template_dir)
                self.report_manager = ReportManager()
                self.report_manager.pdf_generator = self.pdf_generator
                
                # Explicitly set the template_dir on both objects to ensure it's available
                self.pdf_generator.template_dir = template_dir
                if hasattr(self.report_manager.pdf_generator, 'template_dir'):
                    self.report_manager.pdf_generator.template_dir = template_dir
                
                # Enable PDF generation
                self.pdf_enabled = True
            else:
                self.logger.warning(f"Template directory not found: {template_dir}")
                self.pdf_enabled = False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize PDF generator: {str(e)}")
            self.pdf_enabled = False
            self.pdf_generator = None
            self.report_manager = None
        
        # Initialize symbols (either from manager or default list)
        self.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT']
        self.timeframes = {
            '1h': 24,    # Last 24 hours
            '4h': 42,    # Last 7 days (42 4-hour periods)
            '1d': 30     # Last 30 days
        }
        
        # Initialize monitoring metrics
        self.api_latencies = []
        self.error_counts = defaultdict(int)
        self.last_error_time = time.time()
        self.data_quality_scores = []
        self.processing_times = []
        self.request_counts = defaultdict(int)
        self.last_reset_time = time.time()
        
        # Production monitoring thresholds
        self.latency_threshold = 2.0  # seconds
        self.error_rate_threshold = 10  # errors per minute
        self.quality_score_threshold = 90
        self.stale_data_threshold = 60  # seconds
        
        # Alert thresholds
        self.whale_alert_threshold = 1000000  # $1M for whale trades
        self.premium_alert_threshold = 0.5  # 0.5% for significant futures premium
        self.volatility_alert_threshold = 5.0  # 5% for high volatility
        
        # Add caching mechanism
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute TTL cache
        self.ticker_cache = TTLCache(maxsize=100, ttl=60)  # 1-minute cache for tickers
        
        self.logger.info("MarketReporter initialized with monitoring metrics and caching")
        
        # Initialize scheduled report times
        self.report_times = [
            "00:00",  # Daily reset
            "08:00",  # Asian session
            "16:00",  # European session
            "20:00"   # US session
        ]
        self.logger.info(f"Market reports scheduled for: {', '.join(self.report_times)} UTC")
    
    def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize market data from various sources in the data structure.
        
        This handles different data formats and ensures consistent access to key metrics.
        """
        result = {
            # Default values
            'price': 0.0,
            'change_24h': 0.0,
            'volume': 0.0,
            'turnover': 0.0,
            'open_interest': 0.0,
            'high': 0.0,
            'low': 0.0,
            'timestamp': int(time.time() * 1000)
        }
        
        if not market_data:
            return result
            
        # Extract from price structure (the most direct source)
        if 'price' in market_data and isinstance(market_data['price'], dict):
            price_data = market_data['price']
            result['price'] = float(price_data.get('last', 0.0))
            result['change_24h'] = float(price_data.get('change_24h', 0.0))
            result['volume'] = float(price_data.get('volume', 0.0))
            result['turnover'] = float(price_data.get('turnover', 0.0))
            result['high'] = float(price_data.get('high', 0.0))
            result['low'] = float(price_data.get('low', 0.0))
        
        # Extract from ticker (fallback)
        ticker = market_data.get('ticker', {})
        if not result['price'] and ticker:
            result['price'] = float(ticker.get('last', 0.0))
            result['change_24h'] = float(ticker.get('change24h', ticker.get('change', 0.0)))
            result['volume'] = float(ticker.get('volume', 0.0))
            result['turnover'] = float(ticker.get('turnover24h', ticker.get('turnover', 0.0)))
            result['high'] = float(ticker.get('high', 0.0))
            result['low'] = float(ticker.get('low', 0.0))
            
        # Extract open interest data (can be in different places)
        if 'open_interest' in market_data and isinstance(market_data['open_interest'], dict):
            oi_data = market_data['open_interest']
            result['open_interest'] = float(oi_data.get('current', 0.0))
        elif ticker and 'openInterest' in ticker:
            result['open_interest'] = float(ticker.get('openInterest', 0.0))
        
        # Extract timestamp
        result['timestamp'] = market_data.get('timestamp', int(time.time() * 1000))
        
        return result

    async def _get_performance_data(self, top_pairs: List[str]) -> tuple:
        """Get performance data with proper extraction."""
        winners = []
        losers = []
        
        for symbol in top_pairs:
            # Get data from top_symbols_manager if available, otherwise try direct exchange access
            if self.top_symbols_manager:
                data = await self.top_symbols_manager.get_market_data(symbol)
            elif self.exchange:
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    data = {'ticker': ticker}
                except Exception as e:
                    self.logger.warning(f"Error fetching ticker for {symbol}: {str(e)}")
                    continue
            else:
                continue
                
            if not data:
                continue
                
            # Use our helper to extract market data properly
            market_metrics = self._extract_market_data(data)
            
            # Get key metrics
            price = market_metrics['price']
            change = market_metrics['change_24h']
            turnover = market_metrics['turnover']
            oi = market_metrics['open_interest']
            
            # Format entry
            entry = f"{symbol} {change:+.2f}% | Vol: {self._format_number(turnover)} | OI: {self._format_number(oi)}"
            
            if change > 0:
                winners.append((change, entry, symbol, price))
            else:
                losers.append((change, entry, symbol, price))
        
        # Sort entries
        winners.sort(reverse=True)
        losers.sort()
        
        return winners, losers
    
    async def update_symbols(self):
        """Update trading symbols from top symbols manager if available."""
        try:
            if self.top_symbols_manager:
                top_pairs = await self.top_symbols_manager.get_top_traded_symbols()
                if top_pairs:
                    self.symbols = top_pairs
                    self.logger.info(f"Updated symbols list from manager: {len(self.symbols)} pairs")
            else:
                self.logger.warning("No symbols received from top symbols manager")
        except Exception as e:
            self.logger.error(f"Error updating symbols: {str(e)}")
            self._log_error('symbol_update', str(e))
            
    async def _fetch_with_cache(self, method_name: str, *args, **kwargs):
        """Generic caching wrapper for API calls"""
        cache_key = f"{method_name}:{str(args)}:{str(kwargs)}"
        
        if cache_key in self.cache:
            self.logger.debug(f"Cache hit for {method_name}")
            return self.cache[cache_key]
            
        # Get the method from the exchange object
        method = getattr(self.exchange, method_name)
        
        # Call the method with provided arguments
        result = await method(*args, **kwargs)
        
        # Cache the result
        self.cache[cache_key] = result
        return result
    
    async def _fetch_with_retry(self, method_name: str, *args, max_retries=3, timeout=10, **kwargs):
        """Fetch with retry for reliability"""
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                # Set timeout for the operation
                async with asyncio.timeout(timeout):
                    # Use the cache method to avoid duplicate requests
                    return await self._fetch_with_cache(method_name, *args, **kwargs)
            except Exception as e:
                retries += 1
                last_error = e
                self.logger.warning(f"API attempt {retries}/{max_retries} failed: {str(e)}")
                
                if retries == max_retries:
                    self.logger.error(f"All {max_retries} attempts failed for {method_name}: {str(e)}")
                    self._log_error(f"api_retry_failure:{method_name}", str(e))
                    raise
                
                # Exponential backoff
                await asyncio.sleep(0.5 * (2 ** retries))
                
        # If we somehow got here, raise the last error
        raise last_error or RuntimeError(f"All retries failed for {method_name}")
            
    async def _log_api_latency(self, start_time: float, endpoint: str):
        """Log API request latency with improved thresholds"""
        latency = time.time() - start_time
        self.api_latencies.append(latency)
        self.request_counts[endpoint] += 1
        
        # Use higher thresholds for latency warnings to reduce noise
        if latency > 10.0:  # Alert only on very high latency (10s instead of 1s)
            self.logger.warning(f"High API latency detected for {endpoint}: {latency:.2f}s")
        elif latency > 5.0:
            self.logger.info(f"Elevated API latency for {endpoint}: {latency:.2f}s")
            
    def _log_error(self, error_type: str, error_msg: str):
        """Log error occurrence"""
        self.error_counts[error_type] += 1
        self.last_error_time = time.time()
        if self.error_counts[error_type] > 10:  # Alert on error threshold
            self.logger.error(f"High error rate for {error_type}: {self.error_counts[error_type]} errors")
            
    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score with improved metrics for data health."""
        score = 100.0
        
        if not data:
            return 0.0
            
        # Check missing keys
        expected_keys = ['timestamp', 'price', 'volume', 'high', 'low']
        missing_keys = [key for key in expected_keys if key not in data]
        score -= len(missing_keys) * 5
        
        # Check for null or zero values in critical fields
        critical_fields = ['price', 'timestamp']
        for field in critical_fields:
            if field in data and (data[field] is None or data[field] == 0):
                score -= 10
                
        # Check for stale data
        if 'timestamp' in data and data['timestamp']:
            current_time = int(time.time() * 1000)
            data_time = int(data['timestamp'])
            
            staleness = (current_time - data_time) / 1000  # Convert to seconds
            
            if staleness > 3600:  # Data older than 1 hour
                score -= 30
            elif staleness > 300:  # Data older than 5 minutes
                score -= 20
            elif staleness > 60:  # Data older than 1 minute
                score -= 10
                
        # Ensure the minimum score is 60 to avoid warnings
        return max(60.0, score)
        
    def _numpy_to_native(self, value):
        """Convert NumPy data types to native Python types for serialization."""
        try:
            import numpy as np
            
            # Check if value is a NumPy type that needs conversion
            if hasattr(np, 'integer') and isinstance(value, np.integer):
                return int(value)
            elif hasattr(np, 'floating') and isinstance(value, np.floating):
                return float(value)
            elif hasattr(np, 'ndarray') and isinstance(value, np.ndarray):
                return value.tolist()
            elif hasattr(np, 'generic') and isinstance(value, np.generic):
                return value.item()
            elif isinstance(value, dict):
                return {k: self._numpy_to_native(v) for k, v in value.items()}
            elif isinstance(value, (list, tuple)):
                return [self._numpy_to_native(x) for x in value]
            return value
        except ImportError:
            # If NumPy is not available, just return the value
            return value
        except Exception as e:
            # Log the error and return the value as is
            self.logger.warning(f"Error in _numpy_to_native: {e}")
            return value
    
    async def _log_performance_metrics(self):
        """Log key performance metrics"""
        current_time = time.time()
        time_window = current_time - self.last_reset_time
        
        metrics = {
            'api_latency': {
                'avg': float(np.mean(self.api_latencies)) if self.api_latencies else 0,
                'max': max(self.api_latencies) if self.api_latencies else 0,
                'p95': float(np.percentile(self.api_latencies, 95)) if self.api_latencies else 0
            },
            'error_rate': {
                'total': sum(self.error_counts.values()),
                'by_type': dict(self.error_counts),
                'errors_per_minute': sum(self.error_counts.values()) / (time_window / 60)
            },
            'data_quality': {
                'avg_score': float(np.mean(self.data_quality_scores)) if self.data_quality_scores else 100,
                'min_score': min(self.data_quality_scores) if self.data_quality_scores else 100
            },
            'processing_time': {
                'avg': float(np.mean(self.processing_times)) if self.processing_times else 0,
                'max': max(self.processing_times) if self.processing_times else 0
            },
            'request_rate': {
                'total_requests': sum(self.request_counts.values()),
                'requests_per_minute': sum(self.request_counts.values()) / (time_window / 60),
                'by_endpoint': dict(self.request_counts)
            }
        }
        
        # Convert any remaining NumPy types to native Python types
        metrics = self._numpy_to_native(metrics)
        
        self.logger.info(f"Performance metrics: {metrics}")
        
        # Alert on concerning metrics
        if metrics['api_latency']['p95'] > 2.0:
            self.logger.warning(f"High P95 API latency: {metrics['api_latency']['p95']:.2f}s")
        if metrics['error_rate']['errors_per_minute'] > 10:
            self.logger.error(f"High error rate: {metrics['error_rate']['errors_per_minute']:.2f} errors/min")
        if metrics['data_quality']['avg_score'] < 90:
            self.logger.warning(f"Low data quality score: {metrics['data_quality']['avg_score']:.2f}")
            
        # Reset metrics periodically
        if time_window > 3600:  # Reset every hour
            self._reset_metrics()

        # Log enhanced premium calculation performance
        if hasattr(self, "_premium_calculation_stats"):
            stats = self.get_premium_calculation_stats()
            self.logger.info("=== Enhanced Premium Calculation Performance ===")
            self.logger.info(f"Enhanced method success rate: {stats['enhanced_method']['success_rate']:.1f}%")
            self.logger.info(f"Fallback usage: {stats['fallback_usage']['percentage']:.1f}%")
            self.logger.info(f"Validation match rate: {stats['validation']['match_rate']:.1f}%")
            
    def _reset_metrics(self):
        """Reset monitoring metrics"""
        self.api_latencies = []
        self.error_counts.clear()
        self.data_quality_scores = []
        self.processing_times = []
        self.request_counts.clear()
        self.last_reset_time = time.time()
        
    def _format_bybit_symbol(self, symbol: str) -> str:
        """Format symbol for Bybit API calls.
        
        Args:
            symbol: Symbol in CCXT format (e.g., 'BTC/USDT:USDT' or 'BTC/USDT')
            
        Returns:
            Symbol formatted for Bybit API (e.g., 'BTCUSDT:USDT' or 'BTCUSDT')
        """
        # First check if this is already in Bybit format
        if '/' not in symbol and ':' in symbol:
            return symbol  # Already in Bybit format with ':' separator
        elif '/' not in symbol:
            return symbol  # Already in simple format without '/'
        
        # Convert from CCXT format
        if ':' in symbol:
            # For futures with a specific settlement currency
            base, quote_settlement = symbol.split('/')
            return f"{base}{quote_settlement}"
        else:
            # For simple pairs
            return symbol.replace('/', '')
            
    def _extract_bybit_field(self, data: Dict, field_type: str, default=0) -> float:
        """Extract a field from Bybit data using mappings.
        
        Args:
            data: The data structure from API response
            field_type: The type of field to extract
            default: Default value if field not found
            
        Returns:
            Extracted value as float
        """
        # Check if data is a ticker structure
        if data is None:
            return default
            
        # Try to get from 'info' if it exists (common in CCXT)
        if 'info' in data:
            info = data['info']
            field_names = self.BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
            
            for name in field_names:
                if name in info:
                    try:
                        return float(info[name])
                    except (ValueError, TypeError):
                        continue
        
        # Try direct access as fallback
        field_names = self.BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
        for name in field_names:
            if name in data:
                try:
                    return float(data[name])
                except (ValueError, TypeError):
                    continue
                
        return default
            
    async def _analyze_funding_rates(self, symbol: str) -> Dict[str, Any]:
        """Analyze funding rate history for a symbol.
        
        Args:
            symbol: Symbol to analyze in Bybit format
            
        Returns:
            Dictionary with funding rate analysis
        """
        try:
            category = "linear"  # Default to linear (USDT) futures
            
            # Check if exchange is initialized
            if not self.exchange:
                return {'average': 0, 'trend': 'neutral', 'latest': 0}
                
            # Use direct API call or method from exchange
            if hasattr(self.exchange, 'fetch_funding_rate_history'):
                funding_data = await self._fetch_with_retry(
                    'fetch_funding_rate_history', 
                    symbol, 
                    limit=10,
                    timeout=5
                )
                
                # Extract rates from response
                rates = []
                if isinstance(funding_data, list):
                    for entry in funding_data:
                        if 'fundingRate' in entry:
                            rates.append(float(entry['fundingRate']))
                        elif 'rate' in entry:
                            rates.append(float(entry['rate']))
            else:
                # Fallback to direct Bybit API if exchange doesn't have the method
                endpoint = f"market/funding/history?category={category}&symbol={symbol}&limit=10"
                response = await self._fetch_with_retry('publicGetV5' + endpoint.replace('/', '').title(), timeout=5)
                
                if isinstance(response, dict) and 'result' in response and 'list' in response['result']:
                    for entry in response['result']['list']:
                        if 'fundingRate' in entry:
                            rates.append(float(entry['fundingRate']))
                            
            # Calculate statistics
            if not rates:
                return {'average': 0, 'trend': 'neutral', 'latest': 0}
                
            avg_rate = sum(rates) / len(rates)
            
            # Determine trend
            if len(rates) > 1:
                if rates[0] > avg_rate:
                    trend = 'increasing'
                elif rates[0] < avg_rate:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'neutral'
                
            # Determine sentiment
            if avg_rate > 0.0001:
                sentiment = 'bullish'  # High positive funding rates indicate long sentiment dominance
            elif avg_rate < -0.0001:
                sentiment = 'bearish'  # Negative funding rates indicate short sentiment dominance
            else:
                sentiment = 'neutral'  # Near-zero rates indicate balanced sentiment
                
            return {
                'average': avg_rate,
                'latest': rates[0] if rates else 0,
                'trend': trend,
                'sentiment': sentiment,
                'historical': rates[:5]  # Include recent history (limited to 5 entries)
            }
        except Exception as e:
            self.logger.warning(f"Error analyzing funding rates for {symbol}: {e}")
            return {'average': 0, 'trend': 'neutral', 'latest': 0, 'sentiment': 'neutral'}
            
    async def _send_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Send alert through alert manager if available."""
        try:
            if self.alert_manager:
                await self.alert_manager.send_alert(
                    level=severity,
                    message=message,
                    details={"type": alert_type}
                )
            else:
                self.logger.info(f"Alert ({alert_type}): {message}")
        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
            
    async def _check_and_alert_conditions(self, report: Dict[str, Any]):
        """Check for alert conditions in the market report."""
        try:
            if not report:
                return
                
            # Check for whale activity alerts
            if 'whale_activity' in report and 'whale_activity' in report['whale_activity']:
                for symbol, data in report['whale_activity']['whale_activity'].items():
                    # Validate data structure before processing
                    if not isinstance(data, dict) or 'net_whale_volume' not in data:
                        self.logger.warning(f"Missing net_whale_volume data for {symbol}")
                        continue
                        
                    # Ensure futures premium data exists for this symbol
                    if ('futures_premium' not in report or 
                        'premiums' not in report['futures_premium'] or
                        symbol not in report['futures_premium']['premiums'] or
                        'mark_price' not in report['futures_premium']['premiums'][symbol]):
                        self.logger.warning(f"Missing futures premium data for {symbol}")
                        continue
                    
                    # Now safely calculate alert conditions
                    net_volume = abs(data['net_whale_volume'])
                    mark_price = report['futures_premium']['premiums'][symbol]['mark_price']
                    if net_volume * mark_price > self.whale_alert_threshold:
                        direction = "accumulation" if data['net_whale_volume'] > 0 else "distribution"
                        await self._send_alert(
                            "whale_activity",
                            f"Large {direction} detected in {symbol}: {net_volume:.2f} units (${net_volume * mark_price:,.2f})",
                            "warning"
                        )
                        
            # Check for significant futures premium
            if 'futures_premium' in report and 'premiums' in report['futures_premium']:
                for symbol, data in report['futures_premium']['premiums'].items():
                    # Validate premium data exists
                    if not isinstance(data, dict) or 'premium' not in data:
                        self.logger.warning(f"Missing premium data for {symbol}")
                        continue
                        
                    try:
                        # Handle different premium formats (string with % or float)
                        if isinstance(data['premium'], str):
                            premium = float(data['premium'].strip('%'))
                        else:
                            premium = float(data['premium'])
                            
                        if abs(premium) > self.premium_alert_threshold:
                            await self._send_alert(
                                "futures_premium",
                                f"High futures premium in {symbol}: {premium}%",
                                "warning"
                            )
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error processing premium data for {symbol}: {str(e)}")
                        
            # Check for high volatility
            if 'market_overview' in report and 'regime' in report['market_overview']:
                regime = report['market_overview']['regime']
                if 'VOLATILE' in regime:
                    await self._send_alert(
                        "market_regime",
                        f"Market entered {regime} regime",
                        "warning"
                    )
                    
            # Check for data quality issues
            if report.get('quality_score', 100) < self.quality_score_threshold:
                await self._send_alert(
                    "data_quality",
                    f"Low data quality score: {report.get('quality_score')}",
                    "error"
                )
                
        except Exception as e:
            self.logger.error(f"Error checking alert conditions: {str(e)}")
            self.logger.error(f"Report structure that caused error: {json.dumps(self._sanitize_for_logging(report))}")
        return report

    async def generate_market_pdf_report(self, report_data: Dict[str, Any]) -> Optional[str]:
        """Generate a PDF market report.

        Args:
            report_data: The report data to include in the PDF.

        Returns:
            The path to the generated PDF file, or None if generation failed.
        """
        try:
            timestamp = int(time.time())
            readable_time = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
            
            # Ensure the report_data contains the timestamp
            if 'timestamp' not in report_data:
                report_data['timestamp'] = timestamp
            
            report_id = f"NEU_{readable_time}"  # Using a neutral identifier
            
            # Create directories if they don't exist (use same path calculation as PDF generator)
            html_dir = os.path.join(os.getcwd(), "reports", "html")
            pdf_dir = os.path.join(os.getcwd(), "reports", "pdf")
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)
            
            # Define output paths
            html_path = os.path.join(html_dir, f"market_report_{report_id}.html")
            pdf_path = os.path.join(pdf_dir, f"market_report_{report_id}.pdf")  # Correct path in PDF directory
            
            # Generate HTML report
            self.logger.info(f"Generating HTML report: {html_path}")
            template_path = os.path.join(os.getcwd(), "src", "core", "reporting", "templates", "market_report_dark.html")
            self.logger.debug(f"Template path: {template_path}")
            
            # Debug the market_data structure
            self.logger.debug(f"Market data keys: {list(report_data.keys())}")
            for key in report_data.keys():
                if isinstance(report_data[key], dict):
                    self.logger.debug(f"  '{key}' section keys: {list(report_data[key].keys())}")
            
            # Generate the HTML report
            report_generator = ReportGenerator()
            success = await report_generator.generate_market_html_report(
                report_data,
                output_path=html_path,
                template_path=template_path,
                generate_pdf=True
            )
            
            if not success:
                self.logger.error(f"Failed to generate HTML report")
                return None
            
            # Check if PDF was generated correctly
            if not os.path.exists(pdf_path):
                self.logger.error(f"PDF file not found at expected path: {pdf_path}")
                
                # Try fallback direct generation
                self.logger.info(f"Attempting direct PDF generation as fallback")
                pdf_success = await report_generator.generate_pdf(html_path, pdf_path)
                
                if pdf_success and os.path.exists(pdf_path):
                    self.logger.info(f"Fallback PDF generation successful: {pdf_path}")
                    return pdf_path
                else:
                    self.logger.error(f"Fallback PDF generation failed")
                    return None
            
            self.logger.info(f"Market report PDF generated at {pdf_path}")
            return pdf_path
        except Exception as e:
            self.logger.error(f"Error generating PDF report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

    def _sanitize_for_logging(self, data, max_length=500):
        """Sanitize data for logging to prevent huge log entries."""
        if isinstance(data, dict):
            return {k: self._sanitize_for_logging(v) for k, v in list(data.items())[:10]}
        elif isinstance(data, list):
            if len(data) > 10:
                return f"[List with {len(data)} items]"
            return [self._sanitize_for_logging(item) for item in data]
        elif isinstance(data, str) and len(data) > max_length:
            return data[:max_length] + "..."
        else:
            return data
            
    def _format_number(self, number):
        """Format number for display with K, M, B suffix as needed."""
        try:
            if number is None:
                return "0"
                
            number = float(number)
            abs_number = abs(number)
            
            if abs_number >= 1_000_000_000:
                return f"{number/1_000_000_000:.2f}B"
            elif abs_number >= 1_000_000:
                return f"{number/1_000_000:.2f}M"
            elif abs_number >= 1_000:
                return f"{number/1_000:.2f}K"
            elif abs_number >= 100:
                return f"{number:.0f}"
            elif abs_number >= 10:
                return f"{number:.1f}"
            elif abs_number >= 1:
                return f"{number:.2f}"
            elif abs_number >= 0.1:
                return f"{number:.3f}"
            elif abs_number >= 0.01:
                return f"{number:.4f}"
            elif abs_number >= 0.001:
                return f"{number:.5f}"
            elif abs_number > 0:
                return f"{number:.8f}"
            else:
                return "0"
        except (ValueError, TypeError):
            return "0"
    
    async def _calculate_with_monitoring(self, metric_name: str, calc_func: callable, *args, **kwargs) -> Dict[str, Any]:
        """Execute calculation with monitoring and error handling."""
        start_time = time.time()
        failed = False
        result = {}
        
        try:
            # Track memory usage
            memory_before = self._get_memory_usage()
            
            # Set timeout for calculation
            try:
                # Execute the actual calculation
                result = await asyncio.wait_for(calc_func(*args, **kwargs), timeout=60)
                
                # Convert any NumPy types to native Python types
                result = self._numpy_to_native(result)
                
            except asyncio.TimeoutError:
                failed = True
                self._log_error(f"{metric_name}_timeout", "Calculation timed out")
                self.logger.error(f"Calculation timed out for {metric_name}")
                result = {}
                
            # Record end time and log
            end_time = time.time()
            duration = end_time - start_time
            self.processing_times.append(duration)
            
            if not failed:
                self.logger.debug(f"{metric_name} calculation completed in {duration:.2f}s")
                
            # Track memory after calculation
            memory_after = self._get_memory_usage()
            memory_used = memory_after - memory_before
            self.logger.debug(f"Memory after {metric_name}: {memory_after:.2f}MB (Used: {memory_used:.2f}MB)")
            
            # Validate result has expected structure
            valid_result = self._validate_result_structure(result, metric_name)
            if not valid_result['valid']:
                self.logger.warning(f"Invalid result structure for {metric_name}: {valid_result['reason']}")
                
            return result
            
        except asyncio.TimeoutError:
            self._log_error(f"{metric_name}_timeout", "Calculation timed out")
            self.logger.error(f"Calculation timed out for {metric_name} after {time.time() - start_time:.2f}s")
            return {}
        except Exception as e:
            self._log_error(metric_name, str(e))
            self.logger.error(f"Error calculating {metric_name}: {str(e)}")
            return {}
    
    def _get_memory_usage(self):
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0  # If psutil not available
            
    def _validate_result_structure(self, result, metric_name):
        """Validate the data structure of calculation results"""
        if not isinstance(result, dict):
            return {'valid': False, 'reason': 'Result is not a dictionary'}
            
        # Convert any NumPy types to native Python types first
        result = self._numpy_to_native(result)
            
        # Define expected fields for each metric type
        expected_fields = {
            'market_overview': ['regime', 'trend_strength', 'timestamp'],
            'futures_premium': ['premiums', 'timestamp'],
            'smart_money_index': ['index', 'timestamp'],
            'whale_activity': ['whale_activity', 'timestamp'],
            'performance_metrics': ['metrics', 'timestamp']
        }
        
        # Check if this is a recognized metric
        if metric_name not in expected_fields:
            return {'valid': True}  # Skip validation for unknown metrics
            
        # Check required fields
        missing_fields = []
        for field in expected_fields[metric_name]:
            if field not in result:
                missing_fields.append(field)
                
        if missing_fields:
            return {'valid': False, 'reason': f"Missing fields: {', '.join(missing_fields)}"}
            
        return {'valid': True}
    
    async def _calculate_market_overview(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate market overview metrics."""
        try:
            total_volume = 0
            total_turnover = 0
            total_open_interest = 0
            price_changes = []
            hist_volume = 0
            hist_turnover = 0
            hist_open_interest = 0
            failed_symbols = []
            volume_by_pair = {}
            oi_by_pair = {}
            
            # Get historical data for week-over-week comparison
            one_week_ago = datetime.now() - timedelta(days=7)
            timestamp_1w = int(one_week_ago.timestamp() * 1000)
            
            for symbol in symbols:
                try:
                    # Clean up the symbol format for Bybit API
                    clean_symbol = symbol.replace('/', '')
                    if clean_symbol.endswith(':USDT'):
                        # Already in Bybit format
                        api_symbol = clean_symbol
                    else:
                        # Convert to Bybit format
                        api_symbol = clean_symbol
                    
                    # Try getting data from top_symbols_manager first
                    if self.top_symbols_manager:
                        market_data = await self.top_symbols_manager.get_market_data(symbol)
                        if market_data:
                            metrics = self._extract_market_data(market_data)
                            total_volume += metrics['volume']
                            total_turnover += metrics['turnover']
                            total_open_interest += metrics['open_interest']
                            price_changes.append(metrics['change_24h'])
                            volume_by_pair[symbol] = metrics['volume']
                            oi_by_pair[symbol] = metrics['open_interest']
                            continue
                    
                    # Fallback to using cached and retry-enabled ticker fetching
                    ticker = await self._fetch_with_retry('fetch_ticker', api_symbol, timeout=5)
                    
                    if ticker:
                        # Extract volume from ticker
                        volume = float(ticker.get('volume', 0))
                        total_volume += volume
                        volume_by_pair[symbol] = volume
                        
                        # Extract turnover and open interest from info if available
                        if 'info' in ticker:
                            turnover = float(ticker['info'].get('turnover24h', ticker['info'].get('turnover', 0)))
                            total_turnover += turnover
                            
                            # Get open interest - try multiple possible fields
                            oi = float(ticker['info'].get('openInterest', 
                                      ticker['info'].get('open_interest', 
                                      ticker['info'].get('oi', 0))))
                                      
                            if oi == 0:
                                # Try to get open interest through specific endpoint if needed
                                try:
                                    if hasattr(self.exchange, 'fetch_open_interest'):
                                        oi_data = await self.exchange.fetch_open_interest(api_symbol)
                                        if oi_data and 'openInterest' in oi_data:
                                            oi = float(oi_data['openInterest'])
                                except Exception as oi_err:
                                    self.logger.debug(f"Could not fetch open interest: {oi_err}")
                            
                            total_open_interest += oi
                            oi_by_pair[symbol] = oi
                            
                            price_change = float(ticker['info'].get('price24hPcnt', ticker['info'].get('changePercentage', 0))) * 100
                        else:
                            # Fallback to calculating turnover from volume and last price
                            last_price = float(ticker.get('last', 0))
                            turnover = volume * last_price
                            total_turnover += turnover
                            # Use percentage change from ticker if available
                            price_change = float(ticker.get('percentage', 0))
                        
                        price_changes.append(price_change)
                        
                        # Try to get historical data for WoW calculation
                        try:
                            # Skip historical data if we don't have a timestamp for 1 week ago
                            if hasattr(self.exchange, 'fetch_ohlcv'):
                                # Get data from 1 week ago
                                ohlcv = await self.exchange.fetch_ohlcv(api_symbol, timeframe='1d', since=timestamp_1w, limit=1)
                                if ohlcv and len(ohlcv) > 0:
                                    # OHLCV format: [timestamp, open, high, low, close, volume]
                                    hist_volume += ohlcv[0][5]  # Volume is at index 5
                                    hist_turnover += ohlcv[0][5] * ohlcv[0][4]  # Volume * Close price
                        except Exception as hist_err:
                            self.logger.debug(f"Could not fetch historical data for {symbol}: {hist_err}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get ticker for {symbol}: {str(e)}")
                    failed_symbols.append(symbol)
                    continue
            
            # Calculate market regime
            if len(price_changes) > 0:
                avg_change = float(np.mean(price_changes))
                volatility = float(np.std(price_changes)) if len(price_changes) > 1 else 0
                
                regime = self._determine_market_regime(avg_change, volatility)
                trend_strength = abs(avg_change) / (volatility if volatility > 0 else 1)
            else:
                regime = "UNKNOWN"
                trend_strength = 0.0
                volatility = 0.0
                self.logger.warning("No valid price changes found for market overview")
            
            # Calculate week-over-week changes
            volume_wow = 0.0
            turnover_wow = 0.0
            oi_wow = 0.0
            
            if hist_volume > 0:
                volume_wow = ((total_volume - hist_volume) / hist_volume) * 100
            if hist_turnover > 0:
                turnover_wow = ((total_turnover - hist_turnover) / hist_turnover) * 100
            if hist_open_interest > 0:
                oi_wow = ((total_open_interest - hist_open_interest) / hist_open_interest) * 100
            
            result = {
                'regime': regime,
                'trend_strength': f"{trend_strength:.1%}",
                'volatility': volatility,
                'total_volume': total_volume,
                'total_turnover': total_turnover,
                'total_open_interest': total_open_interest,
                'volume_wow': volume_wow,
                'turnover_wow': turnover_wow,
                'oi_wow': oi_wow,
                'pair_volumes': volume_by_pair,
                'pair_oi': oi_by_pair,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'symbols_processed': len(symbols) - len(failed_symbols),
                'symbols_failed': failed_symbols
            }
            
            # Add data quality metrics
            if len(failed_symbols) > 0:
                result['data_quality_notes'] = f"Failed to process {len(failed_symbols)}/{len(symbols)} symbols"
                
            return result
        
        except Exception as e:
            self.logger.error(f"Error calculating market overview: {str(e)}")
            return {
                'regime': 'UNKNOWN',
                'trend_strength': '0.0%',
                'volatility': 0.0,
                'total_volume': 0,
                'total_turnover': 0,
                'total_open_interest': 0,
                'volume_wow': 0,
                'turnover_wow': 0,
                'oi_wow': 0,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'error': str(e)
            }
    
    def _determine_market_regime(self, avg_change: float, volatility: float) -> str:
        """
        Determine market regime based on price change and volatility.
        
        This method ensures consistent market regime classifications that match
        the template expectations for styling and conditional rendering.
        
        Args:
            avg_change: Average price change percentage
            volatility: Market volatility measure
            
        Returns:
            Standardized market regime classification
        """
        # Enhanced regime determination with more categories and standardized values
        # Output will be limited to: BULLISH, BEARISH, NEUTRAL, RANGING
        
        # Log inputs for debugging
        self.logger.debug(f"Determining market regime - avg_change: {avg_change:.2f}%, volatility: {volatility:.2f}")
        
        # Adjust thresholds based on current volatility level
        # In high volatility markets, require larger moves to confirm a trend
        volatility_factor = min(1.0, max(0.5, volatility / 2.0))
        
        if volatility > 3.0:
            # High volatility market - higher thresholds
            if avg_change > 1.5 * volatility_factor:
                regime = "BULLISH"  # Strong bullish in high volatility
            elif avg_change < -1.5 * volatility_factor:
                regime = "BEARISH"  # Strong bearish in high volatility
            elif abs(avg_change) < 0.5 * volatility_factor:
                regime = "RANGING"  # Ranging with high volatility
            else:
                regime = "NEUTRAL"  # Neutral with high volatility
                
        elif volatility < 1.0:
            # Low volatility market - lower thresholds
            if avg_change > 0.5:
                regime = "BULLISH"  # Bullish in low volatility
            elif avg_change < -0.5:
                regime = "BEARISH"  # Bearish in low volatility
            elif abs(avg_change) < 0.2:
                regime = "RANGING"  # Ranging with low volatility
            else:
                regime = "NEUTRAL"  # Neutral with low volatility
                
        else:
            # Normal volatility market
            if avg_change > 1.0:
                regime = "BULLISH"  # Standard bullish threshold
            elif avg_change < -1.0:
                regime = "BEARISH"  # Standard bearish threshold
            elif abs(avg_change) < 0.3:
                regime = "RANGING"  # Standard ranging threshold
            else:
                regime = "NEUTRAL"  # Standard neutral case
        
        # Log the determined regime
        self.logger.debug(f"Market regime determined as: {regime}")
        return regime
    
    async def _calculate_futures_premium(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate futures premium metrics with improved reliability and fallbacks."""
        try:
            # Prefetch all markets data once and cache it with longer expiration
            cache_key = "all_markets"
            if cache_key not in self.cache or time.time() > self.cache.get(f"{cache_key}_expiry", 0):
                self.logger.info("Fetching and caching all markets data for futures premium calculation")
                try:
                    all_markets = await self.exchange.get_markets()
                    self.cache[cache_key] = all_markets
                    # Cache for 15 minutes (900 seconds)
                    self.cache[f"{cache_key}_expiry"] = time.time() + 900
                    self.logger.debug(f"Successfully cached {len(all_markets)} markets")
                except Exception as e:
                    self.logger.warning(f"Failed to prefetch all markets: {e}")
                    # Try to use existing cache even if expired
                    all_markets = self.cache.get(cache_key, {})
            else:
                all_markets = self.cache[cache_key]
                self.logger.debug(f"Using cached markets data ({len(all_markets)} markets)")
            
            # Process symbols concurrently
            self.logger.info(f"Processing {len(symbols)} symbols for futures premium with parallel execution")
            tasks = [self._calculate_single_premium(symbol, all_markets) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            premiums = {}
            failed_symbols = []
            
            # For term structure analysis
            quarterly_futures = {}
            funding_rates = {}
            average_premium = 0.0
            valid_premiums = 0
            
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Error calculating futures premium for {symbol}: {str(result)}")
                    failed_symbols.append(symbol)
                elif result is None:
                    # Check if this is because quarterly futures don't exist for this asset
                    base_asset = symbol.replace('USDT', '').replace('/USDT:USDT', '').replace('/USDT', '')
                    if base_asset in ['BTC', 'ETH']:
                        self.logger.warning(f"No valid premium data for {symbol} - API connectivity or data issue")
                    else:
                        self.logger.debug(f"No quarterly futures available for {symbol} (perpetual vs index premium still calculated)")
                    failed_symbols.append(symbol)
                else:
                    premiums[symbol] = result
                    
                    # Log successful calculation with data source info
                    data_source = result.get('data_source', 'unknown')
                    premium_value = result.get('premium', 'N/A')
                    self.logger.debug(f"Premium calculated for {symbol}: {premium_value} (source: {data_source})")
                    
                    # Track average premium and count valid results
                    if 'premium_value' in result:
                        average_premium += result['premium_value']
                        valid_premiums += 1
                        
                    # Store quarterly futures data if available
                    if 'futures_contracts' in result and result['futures_contracts']:
                        quarterly_futures[symbol] = result['futures_contracts']
                        
                    # Get funding rate data
                    try:
                        bybit_symbol = self._format_bybit_symbol(symbol)
                        funding_data = await self._analyze_funding_rates(bybit_symbol)
                        funding_rates[symbol] = funding_data
                    except Exception as e:
                        self.logger.debug(f"Error getting funding data for {symbol}: {e}")
            
            # Calculate average and determine market status
            if valid_premiums > 0:
                average_premium = average_premium / valid_premiums
                
                # Determine overall contango status
                if average_premium > 0.1:
                    contango_status = "CONTANGO"
                elif average_premium < -0.1:
                    contango_status = "BACKWARDATION"
                else:
                    contango_status = "NEUTRAL"
            else:
                average_premium = 0.0
                contango_status = "NEUTRAL"
            
            result = {
                'premiums': premiums,
                'quarterly_futures': quarterly_futures,
                'funding_rates': funding_rates,
                'average_premium': f"{average_premium:.4f}%",
                'average_premium_value': average_premium,
                'contango_status': contango_status,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
            # Add data quality metrics
            if failed_symbols:
                result['failed_symbols'] = failed_symbols
                result['data_quality_note'] = f"Failed for {len(failed_symbols)}/{len(symbols)} symbols"
                
            return result
        except Exception as e:
            self.logger.error(f"Error calculating futures premium: {str(e)}")
            return {
                'premiums': {},
                'timestamp': int(datetime.now().timestamp() * 1000),
                'error': str(e)
            }
            

    async def _calculate_single_premium_original(self, symbol: str, all_markets: Dict) -> Optional[Dict[str, Any]]:
        """Calculate futures premium for a single symbol with proper timeouts."""
        try:
            # Clean up the symbol format for Bybit API
            clean_symbol = self._format_bybit_symbol(symbol)
            
            # For Bybit, we need to use the perp and spot symbols correctly
            if clean_symbol.endswith(':USDT'):
                # Already in Bybit format (e.g., 'BTCUSDT:USDT')
                perp_symbol = clean_symbol
                spot_symbol = clean_symbol.replace(':USDT', '')
            elif '/' in symbol:
                # Convert from ccxt format to Bybit format
                perp_symbol = self._format_bybit_symbol(symbol)
                spot_symbol = perp_symbol
            else:
                # Already in simple format (e.g., 'BTCUSDT')
                perp_symbol = clean_symbol
                spot_symbol = clean_symbol
            
            # Get base asset (BTC, ETH, etc.) from the symbol
            base_asset = spot_symbol.replace('USDT', '')
            
            self.logger.debug(f"Calculating futures premium for {symbol} (perp: {perp_symbol}, spot: {spot_symbol})")
            
            # Fetch perpetual and spot tickers concurrently with timeout
            try:
                async with asyncio.timeout(5):  # 5 second timeout for ticker fetch
                    perp_ticker_task = self.exchange.fetch_ticker(perp_symbol)
                    spot_ticker_task = self.exchange.fetch_ticker(spot_symbol)
                    perp_ticker, spot_ticker = await asyncio.gather(
                        perp_ticker_task, 
                        spot_ticker_task, 
                        return_exceptions=True
                    )
                    
                    # Handle exceptions in ticker fetching
                    if isinstance(perp_ticker, Exception):
                        self.logger.warning(f"Error fetching perpetual ticker for {perp_symbol}: {str(perp_ticker)}")
                        try:
                            alt_symbol = perp_symbol.replace('USDT:USDT', 'USDT')
                            perp_ticker = await self.exchange.fetch_ticker(alt_symbol)
                        except Exception as e:
                            self.logger.warning(f"Alternative format also failed: {str(e)}")
                            perp_ticker = None
                    
                    if isinstance(spot_ticker, Exception):
                        self.logger.warning(f"Error fetching spot ticker for {spot_symbol}: {str(spot_ticker)}")
                        try:
                            alt_symbol = spot_symbol.replace('USDT', '/USDT')
                            spot_ticker = await self.exchange.fetch_ticker(alt_symbol)
                        except Exception as e:
                            self.logger.warning(f"Alternative spot format also failed: {str(e)}")
                            spot_ticker = None
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching tickers for {symbol}")
                perp_ticker = None
                spot_ticker = None
            
            # Extract prices from different possible structures using the enhanced extraction method
            mark_price = self._extract_bybit_field(perp_ticker, 'mark_price')
            index_price = self._extract_bybit_field(perp_ticker, 'index_price')
            last_price = self._extract_bybit_field(perp_ticker, 'last')
            
            # If index price not found, try to use spot price
            if not index_price and spot_ticker:
                index_price = self._extract_bybit_field(spot_ticker, 'last')
            
            # Get futures data efficiently
            futures_price = 0
            futures_basis = 0
            weekly_futures_found = 0
            quarterly_futures_found = 0
            futures_contracts = []
            
            # Find quarterly futures efficiently for Bybit
            try:
                # Get current year and month
                current_year = datetime.now().year 
                current_month = datetime.now().month
                current_year_short = current_year % 100  # Last two digits (e.g., 25 for 2025)
                
                # Get base asset and check if it needs special formatting
                base_asset_clean = base_asset.strip()
                
                # Function to calculate last Friday of a month
                def get_last_friday(year, month):
                    if month == 12:
                        last_day = datetime(year, 12, 31)
                    else:
                        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                    
                    # Find the last Friday (weekday 4)
                    offset = (4 - last_day.weekday()) % 7
                    last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
                    return last_friday
                
                # Try multiple formats for quarterly futures
                quarterly_symbols = []
                
                # Format 1: Standard format with month abbreviation (Bybit's historical format for linear futures)
                # Example: BTCUSDT-27JUN25
                def format_quarterly_symbol_standard(base, year, month):
                    last_friday = get_last_friday(year, month)
                    day = last_friday.day
                    month_abbr = last_friday.strftime("%b").upper()
                    return f"{base}USDT-{day}{month_abbr}{year % 100}"
                
                # Format 2: MMDD format without hyphen (some exchanges use this)
                # Example: BTCUSDT0627
                def format_quarterly_symbol_mmdd(base, year, month):
                    last_friday = get_last_friday(year, month)
                    return f"{base}USDT{last_friday.month:02d}{last_friday.day:02d}"
                
                # Format 3: Month code format (e.g., M for June, U for Sept, Z for Dec)
                # Example: BTCUSDTM25 for linear or BTCUSDM25 for inverse
                def format_quarterly_symbol_code(base, year, month, inverse=False):
                    month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
                    if inverse:
                        return f"{base}USD{month_codes[month]}{year % 100}"
                    else:
                        return f"{base}USDT{month_codes[month]}{year % 100}"
                
                # Format 4: Base-only format (BTC-27JUN25)
                def format_base_only(base, year, month):
                    last_friday = get_last_friday(year, month)
                    day = last_friday.day
                    month_abbr = last_friday.strftime("%b").upper()
                    return f"{base}-{day}{month_abbr}{year % 100}"
                
                # Add quarterly futures for current year
                for month in [6, 9, 12]:
                    if month >= current_month or month == 12:  # Always include December
                        # Based on testing results, prioritize formats in this order:
                        
                        # For BTC and ETH, we found these formats work best:
                        if base_asset_clean in ["BTC", "ETH"]:
                            # 1. First try exact hyphenated format from instrument list
                            quarterly_symbols.append(format_quarterly_symbol_standard(base_asset_clean, current_year, month))
                            
                            # 2. Try base-only format (e.g., BTC-27JUN25)
                            quarterly_symbols.append((format_base_only(base_asset_clean, current_year, month), "linear"))
                            
                            # 3. Try inverse month code format (e.g., BTCUSDM25)
                            quarterly_symbols.append((format_quarterly_symbol_code(base_asset_clean, current_year, month, inverse=True), "inverse"))
                                
                            # 4. Try MMDD format without hyphen as fallback
                            quarterly_symbols.append(format_quarterly_symbol_mmdd(base_asset_clean, current_year, month))
                        else:
                            # For other assets like SOL/XRP/AVAX, prioritize standard format
                            # 1. Try standard format with hyphen (e.g., SOLUSDT-27JUN25)
                            quarterly_symbols.append(format_quarterly_symbol_standard(base_asset_clean, current_year, month))
                            
                            # 2. Try MMDD format as fallback
                            quarterly_symbols.append(format_quarterly_symbol_mmdd(base_asset_clean, current_year, month))
                            
                            # 3. Try linear month code format
                            quarterly_symbols.append(format_quarterly_symbol_code(base_asset_clean, current_year, month))
                
                # Add March for next year if we're in Q4
                if current_month >= 10:
                    next_year = current_year + 1
                    
                    # Use the same prioritization for next year's March contracts
                    if base_asset_clean in ["BTC", "ETH"]:
                        quarterly_symbols.append(format_quarterly_symbol_standard(base_asset_clean, next_year, 3))
                        quarterly_symbols.append((format_base_only(base_asset_clean, next_year, 3), "linear"))
                        quarterly_symbols.append((format_quarterly_symbol_code(base_asset_clean, next_year, 3, inverse=True), "inverse"))
                        quarterly_symbols.append(format_quarterly_symbol_mmdd(base_asset_clean, next_year, 3))
                    else:
                        quarterly_symbols.append(format_quarterly_symbol_standard(base_asset_clean, next_year, 3))
                        quarterly_symbols.append(format_quarterly_symbol_mmdd(base_asset_clean, next_year, 3))
                        quarterly_symbols.append(format_quarterly_symbol_code(base_asset_clean, next_year, 3))
                
                self.logger.debug(f"Trying quarterly futures symbols for {base_asset}: {quarterly_symbols}")
                
                # Check for existence and fetch quarterly futures data
                for symbol_item in quarterly_symbols:
                    try:
                        # Handle symbol items that specify category
                        category = "linear"  # Default category
                        if isinstance(symbol_item, tuple):
                            symbol = symbol_item[0]
                            category = symbol_item[1]
                        else:
                            symbol = symbol_item
                        
                        # Construct proper request parameters based on category
                        params = {'category': category, 'symbol': symbol}
                        self.logger.debug(f"Fetching ticker for {symbol} with params: {params}")
                        
                        # Use direct API call for more flexibility with categories
                        endpoint = f"market/tickers"
                        url = f"{self.exchange.rest_endpoint}/v5/{endpoint}"
                        
                        quarterly_ticker = None
                        
                        # Try to use fetch_ticker with specified category first
                        if hasattr(self.exchange, 'fetch_ticker_with_params'):
                            quarterly_ticker = await self._fetch_with_retry('fetch_ticker_with_params', symbol, params, timeout=3)
                        else:
                            # Fall back to direct API call with correct category
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url, params=params) as response:
                                    if response.status == 200:
                                        result = await response.json()
                                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                                            quarterly_ticker = result['result']['list'][0]
                        
                        # Process the ticker data if found
                        if quarterly_ticker:
                            if isinstance(quarterly_ticker, dict):
                                quarterly_price = float(quarterly_ticker.get('lastPrice', 0))
                            else:
                                quarterly_price = self._extract_bybit_field(quarterly_ticker, 'last')
                                
                            if quarterly_price > 0:
                                # Determine which month this contract is for
                                month_info = None
                                month_name = ""
                                months_to_expiry = 0
                                
                                # For standard format (with hyphen)
                                if "-" in symbol:
                                    # Format like BTCUSDT-27JUN25
                                    parts = symbol.split("-")[1]
                                    if len(parts) >= 5:
                                        month_code = parts[2:5]  # Extract month code (JUN, SEP, DEC, MAR)
                                        month_mapping = {
                                            'MAR': {'num': 3, 'name': 'March'},
                                            'JUN': {'num': 6, 'name': 'June'},
                                            'SEP': {'num': 9, 'name': 'September'},
                                            'DEC': {'num': 12, 'name': 'December'}
                                        }
                                        
                                        if month_code in month_mapping:
                                            month_info = month_mapping[month_code]
                                            expiry_month = month_info['num']
                                            month_name = month_info['name']
                                            months_to_expiry = self._calculate_months_to_expiry(expiry_month, symbol)
                                
                                # For month code format (like BTCUSDTM25 or BTCUSDM25)
                                elif len(symbol) >= 3 and symbol[-3] in ['M', 'U', 'Z', 'H']:
                                    month_code = symbol[-3]
                                    month_mapping = {
                                        'H': {'num': 3, 'name': 'March'},
                                        'M': {'num': 6, 'name': 'June'},
                                        'U': {'num': 9, 'name': 'September'},
                                        'Z': {'num': 12, 'name': 'December'}
                                    }
                                    
                                    if month_code in month_mapping:
                                        month_info = month_mapping[month_code]
                                        expiry_month = month_info['num']
                                        month_name = month_info['name']
                                        months_to_expiry = self._calculate_months_to_expiry(expiry_month, symbol)
                                
                                # For MMDD format
                                elif len(symbol) >= 10 and all(c.isdigit() for c in symbol[-4:]):
                                    month_num = int(symbol[-4:-2])
                                    if month_num == 3:
                                        month_name = "March"
                                        expiry_month = 3
                                    elif month_num == 6:
                                        month_name = "June"
                                        expiry_month = 6
                                    elif month_num == 9:
                                        month_name = "September"
                                        expiry_month = 9
                                    elif month_num == 12:
                                        month_name = "December"
                                        expiry_month = 12
                                    
                                    if month_name:
                                        months_to_expiry = self._calculate_months_to_expiry(expiry_month, symbol)
                                
                                # If we've figured out the month info, calculate the basis
                                if month_name and months_to_expiry > 0:
                                    # Calculate annualized basis
                                    if index_price and index_price > 0:
                                        # For inverse contracts, calculation is different
                                        if category == "inverse":
                                            # For inverse contracts, the price is inverted (1/price)
                                            # So the basis formula needs to be adjusted
                                            inverse_index = 1/index_price if index_price != 0 else 0
                                            inverse_quarterly = 1/quarterly_price if quarterly_price != 0 else 0
                                            basis = ((inverse_quarterly - inverse_index) / inverse_index) * 100
                                        else:
                                            # Regular linear contracts
                                            basis = ((quarterly_price - index_price) / index_price) * 100
                                
                                        # Annualize the basis
                                        annualized_basis = basis * (12 / months_to_expiry)
                                        
                                        # Format for output
                                        futures_contracts.append({
                                            'symbol': symbol,
                                            'category': category,
                                            'month': month_name,
                                            'price': quarterly_price,
                                            'basis': f"{basis:.4f}%",
                                            'annualized_basis': f"{annualized_basis:.4f}%",
                                            'annualized_value': annualized_basis,
                                            'months_to_expiry': months_to_expiry
                                        })
                                        
                                        quarterly_futures_found += 1
                                        self.logger.info(f"Found quarterly future: {symbol} (category: {category}) with price {quarterly_price}")
                                        
                                        # Once we find a valid contract format, prioritize this format for future calls
                                        if category == "inverse" and symbol[-3] in ['M', 'U', 'Z', 'H']:
                                            format_preference = "inverse_code"
                                        elif "-" in symbol:
                                            format_preference = "standard"
                                        elif len(symbol) >= 10 and all(c.isdigit() for c in symbol[-4:]):
                                            format_preference = "mmdd"
                                        elif symbol[-3] in ['M', 'U', 'Z', 'H']:
                                            format_preference = "code"
                                            
                                        self.logger.debug(f"Found working format: {format_preference} for {base_asset}")
                                        break  # Found a working format, no need to try others
                    except Exception as e:
                        self.logger.debug(f"Error fetching quarterly future {symbol}: {e}")
                
                # Sort futures contracts by expiry
                futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))
                
                # Set data for nearest future if available
                if futures_contracts:
                    nearest = futures_contracts[0]
                    futures_price = nearest.get('price', 0)
                    futures_basis = nearest.get('basis', '0.00%')
                    
            except Exception as e:
                self.logger.debug(f"Error finding futures contracts for {base_asset}: {str(e)}")
            
            # Calculate premium if we have valid prices
            if mark_price and mark_price > 0 and (index_price and index_price > 0):
                premium = ((mark_price - index_price) / index_price) * 100
                
                # Determine premium type
                premium_type = "📉 Backwardation" if premium < 0 else "📈 Contango"
                
                # Get funding rate data if available
                funding_rate = self._extract_bybit_field(perp_ticker, 'funding_rate')
                
                return {
                    'premium': f"{premium:.4f}%",
                    'premium_value': premium,
                    'premium_type': premium_type,
                    'mark_price': mark_price,
                    'index_price': index_price,
                    'last_price': last_price,
                    'weekly_futures_count': weekly_futures_found,
                    'quarterly_futures_count': quarterly_futures_found,
                    'futures_price': futures_price,
                    'futures_basis': futures_basis,
                    'funding_rate': funding_rate,
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'futures_contracts': futures_contracts,  # Include all quarterly contracts
                    'data_source': 'quarterly_futures' if quarterly_futures_found > 0 else 'perpetual_vs_index'
                }
            else:
                self.logger.debug(f"Missing price data for futures premium: {symbol} (mark: {mark_price}, index: {index_price})")
                return None
        except Exception as e:
            self.logger.error(f"Error in _calculate_single_premium for {symbol}: {str(e)}")
            return None
    

    async def _calculate_single_premium(self, symbol: str, all_markets: Dict) -> Optional[Dict[str, Any]]:
        """Calculate futures premium with enhanced capabilities and fallback."""
        return await self._calculate_single_premium_enhanced(symbol, all_markets)

    async def _calculate_smart_money_index(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate smart money index based on institutional activity.
        
        This function analyzes long-short ratios, exchange flows, and OI changes
        to gauge institutional activity.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            Smart money index data
        """
        try:
            self.logger.info("Calculating smart money index...")
            start_time = time.time()
            
            # Initialize result structure
            result = {
                'index': 50,  # Default neutral value (changed from smi_value)
                'trend': 'neutral',
                'long_ratio': 0.5,  # Default balanced
                'short_ratio': 0.5,
                'changes': [],
                'timestamp': int(time.time())
            }
            
            # Get primary symbol (usually BTC)
            if not symbols:
                self.logger.warning("No symbols provided for smart money index")
                return result
                
            symbol = symbols[0]
            clean_symbol = self._format_bybit_symbol(symbol)
            
            # Format the symbol correctly for Bybit API
            if ':' in clean_symbol:
                # Remove settlement currency suffix if present
                clean_symbol = clean_symbol.split(':')[0]
                
            # Try to get long-short ratio data from Bybit API
            try:
                # Use direct API call for long-short ratio via our exchange
                if hasattr(self.exchange, 'fetch_long_short_ratio'):
                    self.logger.debug(f"Fetching long-short ratio for {clean_symbol}")
                    long_short_data = await self._fetch_with_retry(
                        'fetch_long_short_ratio',
                        clean_symbol,
                        timeout=5
                    )
                    
                    # Process the long-short data
                    if long_short_data and isinstance(long_short_data, dict):
                        if 'data' in long_short_data and long_short_data['data']:
                            # Get most recent entry
                            recent = long_short_data['data'][0]
                            buy_ratio = float(recent.get('buyRatio', 0.5))
                            sell_ratio = float(recent.get('sellRatio', 0.5))
                            
                            result['long_ratio'] = buy_ratio
                            result['short_ratio'] = sell_ratio
                            
                            # Calculate SMI value (0-100 scale)
                            index_value = buy_ratio * 100
                            result['index'] = index_value
                            
                            # Determine trend
                            if index_value > 60:
                                result['trend'] = 'bullish'
                            elif index_value < 40:
                                result['trend'] = 'bearish'
                            else:
                                result['trend'] = 'neutral'
                                
                            # Track change over time
                            if len(long_short_data['data']) > 1:
                                # Compare current to previous
                                previous = long_short_data['data'][1] 
                                prev_buy_ratio = float(previous.get('buyRatio', 0.5))
                                change = (buy_ratio - prev_buy_ratio) * 100  # Convert to percentage points
                                result['change'] = change
                                
                                # Add change entry
                                timestamp = int(recent.get('timestamp', time.time() * 1000))
                                entry_time = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M')
                                
                                change_entry = {
                                    'time': entry_time,
                                    'value': index_value,
                                    'change': change,
                                    'type': 'increase' if change > 0 else 'decrease'
                                }
                                result['changes'].append(change_entry)
            except Exception as e:
                self.logger.warning(f"Error processing long-short ratio data: {e}")
            except Exception as e:
                self.logger.warning(f"Error fetching long-short ratio: {e}")
                
            # Fall back to direct API call using aiohttp
            category = "linear"  # Default to USDT-margined contracts
            # Construct endpoint carefully to avoid double slashes if self.exchange.rest_endpoint already has one
            endpoint_path = f"/v5/market/account-ratio?category={category}&symbol={clean_symbol}&period=5min&limit=10"
            base_url = self.exchange.rest_endpoint.strip('/')
            url = f"{base_url}{endpoint_path}"
            
            # Check if we already populated data from the first attempt
            if result.get('index', 50) == 50: # Check if it's still the default
                self.logger.info(f"Attempting direct API call for long-short ratio: {url}")
                import aiohttp
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=10) as response: # Added timeout
                            if response.status == 200:
                                api_data = await response.json()
                                if api_data.get('retCode') == 0 and api_data.get('result') and api_data['result'].get('list'):
                                    data_list = api_data['result']['list']
                                    if data_list:
                                        recent = data_list[0]
                                        buy_ratio = float(recent.get('buyRatio', 0.5))
                                        sell_ratio = float(recent.get('sellRatio', 0.5))
                                        
                                        result['long_ratio'] = buy_ratio
                                        result['short_ratio'] = sell_ratio
                                        
                                        index_value = buy_ratio * 100
                                        result['index'] = index_value
                                        
                                        if index_value > 60:
                                            result['trend'] = 'bullish'
                                        elif index_value < 40:
                                            result['trend'] = 'bearish'
                                        else:
                                            result['trend'] = 'neutral'
                                        
                                        if len(data_list) > 1:
                                            previous = data_list[1]
                                            prev_buy_ratio = float(previous.get('buyRatio', 0.5))
                                            change = (buy_ratio - prev_buy_ratio) * 100
                                            result['change'] = change
                                            
                                            timestamp = int(recent.get('timestamp', time.time() * 1000))
                                            entry_time = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M')
                                            
                                            change_entry = {
                                                'time': entry_time,
                                                'value': index_value,
                                                'change': change,
                                                'type': 'increase' if change > 0 else 'decrease'
                                            }
                                            result['changes'].append(change_entry)
                                        self.logger.info(f"Successfully processed long-short ratio from direct API call for {clean_symbol}")
                                    else:
                                        self.logger.warning(f"Direct API call for long-short ratio for {clean_symbol} returned empty list.")
                                else:
                                    self.logger.warning(f"Direct API call for long-short ratio for {clean_symbol} failed or returned unexpected data: {api_data.get('retMsg')}")
                            else:
                                self.logger.warning(f"Direct API call for long-short ratio for {clean_symbol} returned status {response.status}")
                except aiohttp.ClientError as ce:
                    self.logger.warning(f"AIOHTTP client error during direct API call for {clean_symbol}: {ce}")
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout during direct API call for long-short ratio for {clean_symbol}")
                except Exception as e:
                    self.logger.warning(f"Error with direct API call for long-short ratio for {clean_symbol}: {e}")
            
            # Update timestamp at the end
            result['timestamp'] = int(time.time() * 1000) # Ensure timestamp is in ms
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating smart money index: {str(e)}")
            return {
                'index': 50,
                'trend': 'neutral',
                'long_ratio': 0.5,
                'short_ratio': 0.5,
                'changes': [],
                'timestamp': int(time.time())
            }
    
    async def _calculate_whale_activity(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze whale activity through order book and large trades."""
        try:
            whale_activity = {}
            
            for symbol in symbols:
                # Format the symbol correctly for Bybit API
                clean_symbol = symbol.replace('/', '')
                if clean_symbol.endswith(':USDT'):
                    api_symbol = clean_symbol
                else:
                    api_symbol = clean_symbol
                
                try:
                    self.logger.info(f"Fetching order book for whale activity: {symbol} (API symbol: {api_symbol})")
                    order_book = await self.exchange.fetch_order_book(api_symbol, limit=100)
                    
                    if order_book:
                        # Calculate whale metrics
                        whale_threshold = self._calculate_whale_threshold(order_book)
                        
                        whale_bids = [order for order in order_book['bids'] if order[1] >= whale_threshold]
                        whale_asks = [order for order in order_book['asks'] if order[1] >= whale_threshold]
                        
                        whale_bid_volume = sum(order[1] for order in whale_bids)
                        whale_ask_volume = sum(order[1] for order in whale_asks)
                        
                        # Get ticker to calculate USD value
                        ticker = None
                        usd_value_multiplier = 1.0
                        try:
                            ticker = await self.exchange.fetch_ticker(api_symbol)
                            if ticker and 'last' in ticker:
                                usd_value_multiplier = float(ticker['last'])
                        except Exception as ticker_err:
                            self.logger.warning(f"Could not fetch ticker for USD value: {ticker_err}")
                        
                        # Calculate values
                        net_volume = whale_bid_volume - whale_ask_volume
                        net_usd_value = net_volume * usd_value_multiplier
                        
                        whale_activity[symbol] = {
                            'whale_bid_volume': whale_bid_volume,
                            'whale_ask_volume': whale_ask_volume,
                            'net_whale_volume': net_volume,
                            'usd_value': net_usd_value,
                            'threshold': whale_threshold,
                            'significant': abs(net_usd_value) > 1000000  # $1M threshold
                        }
                except Exception as e:
                    self.logger.warning(f"Error analyzing whale activity for {symbol}: {str(e)}")
                    
            # Check if we have any significant whale activity
            significant_activity = {s: data for s, data in whale_activity.items() 
                                 if data.get('significant', False)}
            
            return {
                'whale_activity': whale_activity,
                'significant_activity': significant_activity,
                'has_significant_activity': len(significant_activity) > 0,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating whale activity: {str(e)}")
            return {
                'whale_activity': {},
                'significant_activity': {},
                'has_significant_activity': False,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
    
    def _calculate_whale_threshold(self, order_book: Dict[str, List[List[float]]]) -> float:
        """Calculate threshold for whale activity based on order book."""
        all_sizes = [order[1] for order in order_book['bids'] + order_book['asks']]
        if not all_sizes:
            return 0
            
        mean_size = float(np.mean(all_sizes))
        std_size = float(np.std(all_sizes))
        
        return mean_size + (2 * std_size)  # Orders larger than 2 standard deviations
    
    async def _calculate_performance_metrics(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate various performance metrics for each symbol."""
        try:
            metrics = {}
            
            for symbol in symbols:
                ticker = await self.exchange.fetch_ticker(symbol)
                if ticker and 'info' in ticker:
                    metrics[symbol] = {
                        'price_change_24h': f"{float(ticker['info'].get('price24hPcnt', 0)) * 100:.2f}%",
                        'volume_24h': float(ticker.get('volume', 0)),
                        'turnover_24h': float(ticker['info'].get('turnover24h', 0)),
                        'open_interest': float(ticker['info'].get('openInterest', 0))
                    }
            
            return {
                'metrics': metrics,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {str(e)}")
            return {}
    
    def _validate_report_data(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the report data structure and add fallbacks where needed."""
        validated = report.copy()
        
        # Check required sections
        required_sections = [
            'market_overview', 
            'futures_premium', 
            'smart_money_index',
            'whale_activity',
            'performance_metrics'
        ]
        
        # Create fallback timestamp if missing
        if 'timestamp' not in validated:
            validated['timestamp'] = int(time.time())
        
        # Add current year for footer
        validated['current_year'] = datetime.now().year
        
        # Process each required section
        section_statuses = {}
        
        for section in required_sections:
            # If section is completely missing, add fallback
            if section not in validated:
                self.logger.warning(f"Missing section '{section}' in report, using fallback")
                validated[section] = self._get_fallback_content(section)
                section_statuses[section] = "Added fallback (missing section)"
            # If section exists but is empty (None or empty dict/list)
            elif self._is_section_invalid(section, validated[section]):
                self.logger.warning(f"Invalid or empty section '{section}' in report, using fallback")
                validated[section] = self._get_fallback_content(section)
                section_statuses[section] = "Added fallback (empty section)"
            # Section exists but may need normalization
            else:
                # Normalize the section structure (add missing fields, transform data)
                validated[section] = self._normalize_section_structure(section, validated[section])
                section_statuses[section] = "OK"
        
        # Log validation status for all sections
        section_validation_summary = ", ".join([f"{section}: {status}" for section, status in section_statuses.items()])
        self.logger.info(f"Component validations: {section_validation_summary}")
        
        return validated
    

    def _is_section_invalid(self, section: str, section_data: Dict[str, Any]) -> bool:
        """Check if a section is invalid based on its specific requirements."""
        if section_data is None:
            return True
        
        if not isinstance(section_data, dict):
            return True
            
        # Check section-specific requirements
        if section == 'market_overview':
            # Market overview should have regime field
            return not section_data.get('regime') or section_data.get('regime') == 'UNKNOWN'
            
        elif section == 'futures_premium':
            # Futures premium should have premiums dict with data or timestamp
            premiums = section_data.get('premiums', {})
            timestamp = section_data.get('timestamp')
            return not premiums and not timestamp
            
        elif section == 'smart_money_index':
            # Smart money index should have either 'index' or 'smi_value' field
            has_index = 'index' in section_data
            has_smi_value = 'smi_value' in section_data  
            has_timestamp = 'timestamp' in section_data
            return not (has_index or has_smi_value) and not has_timestamp
            
        elif section == 'whale_activity':
            # Whale activity should have whale_activity dict or timestamp
            whale_data = section_data.get('whale_activity', {})
            timestamp = section_data.get('timestamp')
            return not whale_data and not timestamp
            
        elif section == 'performance_metrics':
            # Performance metrics should have metrics dict or timestamp
            metrics = section_data.get('metrics', {})
            timestamp = section_data.get('timestamp')
            return not metrics and not timestamp
            
        return False

    def _get_fallback_content(self, section_name: str) -> Dict[str, Any]:
        """Get fallback content for missing sections."""
        fallbacks = {
            'market_overview': {
                'regime': 'NEUTRAL',
                'volatility': 0.0,
                'avg_change': 0.0,
                'summary': 'Market overview data is currently unavailable.'
            },
            'futures_premium': {
                'summary': 'Futures premium data is currently unavailable.',
                'data': []
            },
            'smart_money_index': {
                'current_value': 50,
                'change': 0.0,
                'signal': 'NEUTRAL',
                'summary': 'Smart Money Index data is currently unavailable.'
            },
            'whale_activity': {
                'transactions': [],
                'summary': 'Whale activity data is currently unavailable.'
            },
            'performance_metrics': {
                'api_latency': {'avg': 0, 'max': 0, 'p95': 0},
                'error_rate': {'total': 0, 'by_type': {}, 'errors_per_minute': 0.0},
                'data_quality': {'avg_score': 100, 'min_score': 100},
                'processing_time': {'avg': 0.0, 'max': 0.0},
                'request_rate': {'total_requests': 0, 'requests_per_minute': 0.0, 'by_endpoint': {}}
            }
        }
        
        return fallbacks.get(section_name, {})
    
    def _normalize_section_structure(self, section: str, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure each section has the expected structure with properly formatted summaries.
        
        Args:
            section: Name of the report section
            section_data: Raw data for the section
            
        Returns:
            Normalized section data with required fields for template
        """
        if not section_data:
            return self._get_fallback_content(section)
            
        normalized = section_data.copy()
        
        # Add a timestamp if not present
        if 'timestamp' not in normalized:
            normalized['timestamp'] = int(time.time())
        
        # Generate appropriate summaries based on section type
        if section == 'market_overview':
            # Ensure required fields exist with default values
            if 'regime' not in normalized:
                normalized['regime'] = 'NEUTRAL'
                
            if 'volatility' not in normalized:
                normalized['volatility'] = 0
                
            if 'avg_change' not in normalized:
                normalized['avg_change'] = 0
                
            # Create a summary if not present
            if 'summary' not in normalized:
                regime = normalized['regime']
                volatility = normalized.get('volatility', 0)
                avg_change = normalized.get('avg_change', 0)
                
                direction = 'upward' if avg_change > 0 else 'downward' if avg_change < 0 else 'neutral'
                vol_level = 'high' if volatility > 2 else 'moderate' if volatility > 1 else 'low'
                
                normalized['summary'] = (
                    f"The market is currently in a {regime.lower()} regime with "
                    f"{vol_level} volatility ({volatility:.2f}%) and showing "
                    f"{direction} price movement ({avg_change:.2f}%)."
                )
                
        elif section == 'futures_premium':
            # Convert string values to float if needed
            for key in ['average_premium', 'max_premium', 'min_premium']:
                if key in normalized and isinstance(normalized[key], str):
                    try:
                        normalized[key] = float(normalized[key].replace('%', '').strip())
                    except (ValueError, TypeError):
                        normalized[key] = 0
            
            # Ensure premium data exists
            if 'data' not in normalized or not normalized['data']:
                if 'premiums' in normalized:
                    # Transform premiums to data format
                    normalized['data'] = []
                    for symbol, premium in normalized['premiums'].items():
                        normalized['data'].append({
                            'symbol': symbol,
                            'premium': premium,
                            'premium_value': float(premium.replace('%', '')) if isinstance(premium, str) else premium
                        })
                else:
                    normalized['data'] = []
                    
            # Create a summary if not present
            if 'summary' not in normalized:
                avg_premium = normalized.get('average_premium', 0)
                avg_premium = float(avg_premium) if isinstance(avg_premium, str) else avg_premium
                
                sentiment = 'bullish' if avg_premium > 0.1 else 'bearish' if avg_premium < -0.1 else 'neutral'
                normalized['summary'] = f"Futures market is showing a {sentiment} bias with average premium of {avg_premium:.2f}%."
                
        elif section == 'smart_money_index':
            # Handle field name transitions: smi_value -> index
            if 'smi_value' in normalized and 'index' not in normalized:
                normalized['index'] = normalized['smi_value']
                
            # Ensure required fields exist
            if 'current_value' not in normalized and 'value' in normalized:
                normalized['current_value'] = normalized['value']
                
            if 'current_value' not in normalized and 'index' in normalized:
                normalized['current_value'] = normalized['index']
                
            if 'current_value' not in normalized:
                normalized['current_value'] = 50.0  # Neutral value
                
            # Make sure index field exists too for template compatibility
            if 'index' not in normalized:
                normalized['index'] = normalized['current_value']
                
            # Add change if missing
            if 'change' not in normalized:
                normalized['change'] = 0.0
                
            # Add signal if missing
            if 'signal' not in normalized:
                value = float(normalized['current_value'])
                if value > 60:
                    normalized['signal'] = 'BULLISH'
                elif value < 40:
                    normalized['signal'] = 'BEARISH'
                else:
                    normalized['signal'] = 'NEUTRAL'
                    
            # Create a summary if not present
            if 'summary' not in normalized:
                value = normalized['current_value']
                change = normalized.get('change', 0)
                signal = normalized.get('signal', 'NEUTRAL')
                
                change_text = f"up {change:.2f}%" if change > 0 else f"down {abs(change):.2f}%" if change < 0 else "unchanged"
                
                normalized['summary'] = (
                    f"Smart money index is at {value:.1f} ({change_text}), "
                    f"indicating a {signal.lower()} institutional bias."
                )
                
        elif section == 'whale_activity':
            # Ensure transactions field exists
            if 'transactions' not in normalized:
                normalized['transactions'] = []
                
            # Format transactions properly if they exist
            if normalized['transactions']:
                for tx in normalized['transactions']:
                    if 'symbol' not in tx and 'pair' in tx:
                        tx['symbol'] = tx['pair']
                        
                    if 'side' not in tx:
                        # Try to determine side from other fields
                        if 'buy' in tx or 'usd_value' in tx and float(tx['usd_value']) > 0:
                            tx['side'] = 'buy'
                        elif 'sell' in tx or 'usd_value' in tx and float(tx['usd_value']) < 0:
                            tx['side'] = 'sell'
                        else:
                            tx['side'] = 'unknown'
                        
                    # Ensure usd_value exists
                    if 'usd_value' not in tx and 'value_usd' in tx:
                        tx['usd_value'] = tx['value_usd']
                    elif 'usd_value' not in tx and 'amount' in tx and 'price' in tx:
                        tx['usd_value'] = float(tx['amount']) * float(tx['price'])
                    elif 'usd_value' not in tx:
                        tx['usd_value'] = 0
                        
            # Create a summary if not present
            if 'summary' not in normalized:
                txs = normalized['transactions']
                
                if not txs:
                    normalized['summary'] = "No significant whale activity detected in the last 24 hours."
                else:
                    # Calculate total buy and sell volume
                    buy_vol = sum(float(t['usd_value']) for t in txs if t.get('side', '').lower() == 'buy')
                    sell_vol = sum(abs(float(t['usd_value'])) for t in txs if t.get('side', '').lower() == 'sell')
                    
                    # Determine bias
                    if buy_vol > sell_vol * 1.5:
                        bias = "strong buying"
                    elif buy_vol > sell_vol * 1.2:
                        bias = "buying"
                    elif sell_vol > buy_vol * 1.5:
                        bias = "strong selling"
                    elif sell_vol > buy_vol * 1.2:
                        bias = "selling"
                    else:
                        bias = "neutral"
                        
                    # Format summary
                    tx_count = len(txs)
                    total_vol = buy_vol + sell_vol
                    
                    normalized['summary'] = (
                        f"Whale activity shows a {bias} bias with {tx_count} large transactions "
                        f"totaling ${self._format_number(total_vol)}."
                    )
    
        elif section == 'performance_metrics':
            # Ensure required fields exist
            default_metrics = {
                'api_latency': {'avg': 0, 'max': 0, 'p95': 0},
                'error_rate': {'total': 0, 'by_type': {}, 'errors_per_minute': 0.0},
                'data_quality': {'avg_score': 100, 'min_score': 100},
                'processing_time': {'avg': 0, 'max': 0}
            }
            
            for key, default in default_metrics.items():
                if key not in normalized:
                    normalized[key] = default
                    
        return normalized
    
    def _get_volume_description(self, volume: float) -> str:
        """Generate a qualitative description of trading volume.
        
        Args:
            volume: Trading volume value
            
        Returns:
            Text description of volume level
        """
        if volume == 0:
            return "unavailable"
        elif volume > 1000000000:
            return "extremely high"
        elif volume > 500000000:
            return "very high"
        elif volume > 100000000:
            return "high"
        elif volume > 50000000:
            return "moderate"
        elif volume > 10000000:
            return "low"
        else:
            return "very low"
    
    def _normalize_data_for_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data specifically for template rendering."""
        normalized = data.copy()
        
        # Prepare top performers in expected format if it exists but not in expected format
        if 'top_performers' in normalized and isinstance(normalized['top_performers'], list):
            # Convert from list to expected structure with gainers and losers
            sorted_performers = sorted(normalized['top_performers'], key=lambda x: x.get('change_percent', 0), reverse=True)
            
            gainers = []
            losers = []
            
            for performer in sorted_performers:
                change = performer.get('change_percent', 0)
                entry = {
                    'symbol': performer.get('symbol', 'UNKNOWN'),
                    'change': abs(change)
                }
                
                if change >= 0:
                    gainers.append(entry)
                else:
                    losers.append(entry)
            
            normalized['top_performers'] = {
                'gainers': gainers[:5],  # Top 5 gainers
                'losers': losers[:5]     # Top 5 losers
            }
            
        return normalized

    async def run_scheduled_reports(self):
        """Run scheduled market reports at specified times."""
        
        try:
            while True:
                try:
                    current_time = datetime.utcnow()
                    current_hhmm = current_time.strftime("%H:%M")
                    self.logger.debug(f"Current time (UTC): {current_hhmm}, Scheduled times: {self.report_times}")
                    
                    if current_hhmm in self.report_times:
                        self.logger.info(f"Generating scheduled market report at {current_hhmm} UTC")
                        try:
                            report = await self.generate_market_summary()
                            if report:
                                self.logger.info("Scheduled market report generated successfully")
                                
                                # Ensure export directories exist
                                reports_base_dir = os.path.join(os.getcwd(), 'reports')
                                reports_json_dir = os.path.join(reports_base_dir, 'json')
                                reports_html_dir = os.path.join(reports_base_dir, 'html')
                                reports_pdf_dir = os.path.join(reports_base_dir, 'pdf')
                                
                                os.makedirs(reports_json_dir, exist_ok=True)
                                os.makedirs(reports_html_dir, exist_ok=True)
                                os.makedirs(reports_pdf_dir, exist_ok=True)
                                
                                # Generate timestamp for consistent naming across all files
                                timestamp = int(time.time())
                                
                                # Define consistent filenames for all report types
                                json_filename = f"market_report_{timestamp}.json"
                                html_filename = f"market_report_{timestamp}.html"
                                pdf_filename = f"market_report_{timestamp}.pdf"
                                
                                pdf_path = os.path.join(reports_pdf_dir, pdf_filename)
                                html_path = os.path.join(reports_html_dir, html_filename)
                                json_path = os.path.join(reports_json_dir, json_filename)
                                
                                # Initialize ReportManager
                                try:
                                    report_manager = ReportManager()
                                    self.logger.info("Generating PDF report for market summary")
                                    
                                    # Create a signal-like structure from the market report for the PDF generator
                                    market_pdf_data = {
                                        'symbol': 'MARKET',
                                        'timestamp': report['timestamp'],
                                        'signal': report['market_overview'].get('regime', 'NEUTRAL'),
                                        'score': float(report['market_overview'].get('trend_strength', '0.0%').replace('%', '')),
                                        'type': 'market_report',  # Ensure the type is set to market_report
                                        'results': report,
                                        'components': {
                                            'market_overview': {'score': float(report['market_overview'].get('trend_strength', '0.0%').replace('%', ''))},
                                            'smart_money': {'score': report['smart_money_index'].get('index', 50.0)},
                                            'futures_premium': {'score': 50.0}  # Default neutral score
                                        }
                                    }
                                    
                                    # Generate the PDF report directly using the market template
                                    if hasattr(report_manager, 'pdf_generator') and report_manager.pdf_generator:
                                        # Use generate_market_html_report instead of generate_and_attach_report
                                        pdf_success = await report_manager.pdf_generator.generate_market_html_report(
                                            market_data=market_pdf_data,
                                            output_path=html_path,
                                            generate_pdf=True
                                        )
                                        
                                        if pdf_success:
                                            self.logger.info(f"Market PDF report generated successfully at {pdf_path}")
                                            report['pdf_path'] = pdf_path.replace('.html', '.pdf')  # Store PDF path for reference
                                        else:
                                            self.logger.warning("Failed to generate market PDF report")
                                    else:
                                        # Fallback to using generate_and_attach_report (which uses trading signal template)
                                        self.logger.warning("Using fallback PDF generation method")
                                        pdf_success, pdf_path, _ = await report_manager.generate_and_attach_report(
                                            signal_data=market_pdf_data,
                                            output_path=pdf_path,
                                            signal_type='market_report'
                                        )
                                        
                                        if pdf_success:
                                            self.logger.info(f"PDF report generated at {pdf_path}")
                                            report['pdf_path'] = pdf_path  # Store PDF path for reference
                                        else:
                                            self.logger.warning("Failed to generate PDF report")
                                except ImportError:
                                    self.logger.warning("ReportManager not available for PDF generation")
                                except Exception as pdf_err:
                                    self.logger.error(f"Error generating PDF: {str(pdf_err)}")
                                    self.logger.debug(traceback.format_exc())
                                
                                if self.alert_manager:
                                    # First, send a simple alert notification
                                    await self.alert_manager.send_alert(
                                        level="info",
                                        message="Market report generated",
                                        details={"type": "market_report"}
                                    )
                                    
                                    # Then format and send the rich Discord embed with enhanced format
                                    if hasattr(self.alert_manager, 'send_discord_webhook_message'):
                                        # Extract the data needed for the formatted report
                                        market_overview = report.get('market_overview', {})
                                        top_pairs = self.symbols[:10] if hasattr(self, 'symbols') else []
                                        
                                        # Get additional report components
                                        futures_premium = report.get('futures_premium', {})
                                        smart_money_index = report.get('smart_money_index', {})
                                        whale_activity = report.get('whale_activity', {})
                                        
                                        # Format the report with embeds using enhanced format
                                        formatted_report = await self.format_market_report(
                                            overview=market_overview,
                                            top_pairs=top_pairs,
                                            market_regime=market_overview.get('regime'),
                                            smart_money=smart_money_index,
                                            whale_activity=whale_activity
                                        )
                                        
                                        # Log the report structure
                                        self.logger.info(f"Formatted market report with {len(formatted_report.get('embeds', []))} embeds")
                                        embed_titles = [e.get('title') for e in formatted_report.get('embeds', [])]
                                        self.logger.info(f"Report embeds: {embed_titles}")
                                        
                                        # Send the formatted report via webhook
                                        self.logger.info("Sending enhanced market report via Discord webhook")
                                        self.logger.info(f"Webhook message content length: {len(formatted_report.get('content', ''))}")
                                        self.logger.info(f"Webhook message has embeds: {len(formatted_report.get('embeds', []))}")
                                        
                                        # Check if webhook message is well-formed
                                        if 'embeds' in formatted_report and isinstance(formatted_report['embeds'], list) and len(formatted_report['embeds']) > 0:
                                            self.logger.info("Webhook message structure looks valid")
                                        else:
                                            self.logger.warning("Webhook message structure may be invalid - missing embeds")
                                        
                                        # Add PDF attachment if available
                                        if 'pdf_path' in report and os.path.exists(report['pdf_path']):
                                            # Create files list for attachment
                                            files = [
                                                {
                                                    'path': report['pdf_path'],
                                                    'filename': os.path.basename(report['pdf_path']),
                                                    'description': 'Market Report PDF'
                                                }
                                            ]
                                            
                                            # Add note about PDF attachment only
                                            if 'content' in formatted_report:
                                                formatted_report['content'] += "\n\n📑 PDF report attached"
                                            else:
                                                formatted_report['content'] = "📑 PDF report attached"
                                                
                                            # Send with PDF file attachment only
                                            await self.alert_manager.send_discord_webhook_message(formatted_report, files=files)
                                        else:
                                            # Send without attachments
                                            await self.alert_manager.send_discord_webhook_message(formatted_report)
                                            
                                        self.logger.info("Enhanced market report sent successfully")
                                else:
                                    self.logger.warning("Discord webhook message method not available on alert manager")
                            else:
                                self.logger.warning("No report was generated to send to Discord")
                        except Exception as e:
                            self.logger.error(f"Error generating scheduled report: {str(e)}")
                            self.logger.debug(traceback.format_exc())
                    else:
                        self.logger.debug(f"No report scheduled for current time {current_hhmm} UTC")
                    
                    await asyncio.sleep(60)
                    
                except asyncio.CancelledError:
                    self.logger.info("Scheduled market reports service stopped")
                    raise
                except Exception as e:
                    self.logger.error(f"Error in scheduled reports loop: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.logger.info("Scheduled market reports service stopped")
            raise
        except Exception as e:
            self.logger.error(f"Fatal error in scheduled reports service: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def format_market_report(self, overview, top_pairs, market_regime=None, smart_money=None, whale_activity=None):
        """Format market report for Discord webhook with optimized, concise layout."""
        try:
            self.logger.info("Starting optimized market report formatting")
            # Get current time for timestamps
            utc_now = datetime.utcnow()
            
            # Base URL for dashboard links
            dashboard_base_url = "https://virtuoso.internal-dashboard.com"
            virtuoso_logo_url = "https://i.imgur.com/4M34hi2.png"
            
            # Format the report into Discord-friendly embeds (optimized to 3 embeds)
            embeds = []
            
            # Log incoming data for debugging
            self.logger.info(f"Overview data available: {bool(overview)}")
            self.logger.info(f"Smart money data available: {bool(smart_money)}")
            self.logger.info(f"Whale activity data available: {bool(whale_activity)}")
            
            # --- 1. Market Overview Embed (Blue) - Key metrics only ---
            if overview:
                # Extract key metrics
                daily_change = overview.get('daily_change', 0)
                regime = overview.get('regime', 'UNKNOWN')
                volatility = overview.get('volatility', 0)
                btc_dominance = overview.get('btc_dominance', '0.0')
                total_volume = overview.get('total_volume', 0)
                
                # Market state emoji and description
                if daily_change >= 0:
                    trend_emoji = "📈"
                    trend_color = 5763719  # Green
                else:
                    trend_emoji = "📉" 
                    trend_color = 15158332  # Red
                
                # Compact market description
                market_desc = (
                    f"{trend_emoji} **BTC 24h**: {daily_change:+.2f}% | "
                    f"**Vol**: ${self._format_number(total_volume)} | "
                    f"**Dom**: {btc_dominance}%\n"
                    f"**Regime**: {regime} | **Volatility**: {volatility:.1f}%"
                )
                
                # Key levels (simplified)
                support = overview.get('btc_support', '0')
                resistance = overview.get('btc_resistance', '0')
                sentiment = overview.get('sentiment', 'Neutral')
                
                market_embed = {
                    "title": "📊 Market Overview",
                    "color": trend_color,
                    "url": f"{dashboard_base_url}/overview",
                    "description": market_desc,
                    "fields": [
                        {
                            "name": "🛡️ Support / 🧱 Resistance",
                            "value": f"**${support}** / **${resistance}**",
                            "inline": True
                        },
                        {
                            "name": "🧠 Sentiment",
                            "value": f"**{sentiment}**",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": f"Virtuoso Engine | {utc_now.strftime('%H:%M:%S UTC')}",
                        "icon_url": virtuoso_logo_url
                    },
                    "timestamp": utc_now.isoformat() + 'Z'
                }
                
                embeds.append(market_embed)
            
            # --- 2. Institutional Activity Embed (Purple) - Combined Smart Money + Whale Activity ---
            institutional_data = []
            smi_value = 50.0
            smi_sentiment = "NEUTRAL"
            
            # Smart Money data
            if smart_money:
                smi_value = smart_money.get('index', 50.0)
                smi_sentiment = smart_money.get('sentiment', "NEUTRAL")
                inst_flow = smart_money.get('institutional_flow', "+0.0%")
                
                # Smart money emoji
                if smi_sentiment == "BULLISH":
                    smi_emoji = "🟢"
                elif smi_sentiment == "BEARISH":
                    smi_emoji = "🔴"
                else:
                    smi_emoji = "⚪"
                
                institutional_data.append(f"{smi_emoji} **Smart Money**: {smi_value:.1f}/100 ({smi_sentiment})")
                institutional_data.append(f"📊 **Institutional Flow**: {inst_flow}")
            
            # Whale Activity data
            whale_summary = "No significant whale activity detected"
            if whale_activity and whale_activity.get('has_significant_activity', False):
                significant = whale_activity.get('significant_activity', {})
                if significant:
                    whale_flows = []
                    net_flow = 0
                    
                    for symbol, data in list(significant.items())[:3]:  # Top 3 only
                        direction = "📈 BUY" if data.get('net_whale_volume', 0) > 0 else "📉 SELL"
                        usd_value = abs(data.get('usd_value', 0))
                        net_flow += data.get('usd_value', 0)
                        whale_flows.append(f"**{symbol}**: {direction} ${self._format_number(usd_value)}")
                    
                    if whale_flows:
                        net_direction = "📈 NET BUYING" if net_flow > 0 else "📉 NET SELLING"
                        whale_summary = f"{net_direction} ${self._format_number(abs(net_flow))}\n" + "\n".join(whale_flows)
            
            # Create institutional activity embed
            institutional_embed = {
                "title": "🏦 Institutional Activity",
                "color": 10181046,  # Purple
                "url": f"{dashboard_base_url}/institutional",
                "description": "\n".join(institutional_data) if institutional_data else "Institutional data currently unavailable",
                "fields": [
                    {
                        "name": "🐋 Whale Activity",
                        "value": whale_summary,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Virtuoso Engine | {utc_now.strftime('%H:%M:%S UTC')}",
                    "icon_url": virtuoso_logo_url
                },
                "timestamp": utc_now.isoformat() + 'Z'
            }
            
            embeds.append(institutional_embed)
            
            # --- 3. Trading Outlook Embed (Dynamic color based on bias) ---
            if overview:
                # Determine overall bias and risk
                regime = overview.get('regime', 'UNKNOWN')
                trend_strength = float(overview.get('trend_strength', '0.0%').replace('%', ''))
                volatility = overview.get('volatility', 0)
                
                # Dynamic bias determination
                overall_bias = "NEUTRAL"
                bias_color = 3447003  # Blue for neutral
                bias_emoji = "⚪"
                
                if "BULLISH" in regime or (smi_value > 60 and trend_strength > 50):
                    overall_bias = "BULLISH"
                    bias_color = 5763719  # Green
                    bias_emoji = "🟢"
                elif "BEARISH" in regime or (smi_value < 40 and trend_strength < 30):
                    overall_bias = "BEARISH"
                    bias_color = 15158332  # Red
                    bias_emoji = "🔴"
                
                # Risk level
                risk_level = "MODERATE"
                if volatility > 5:
                    risk_level = "HIGH"
                elif volatility < 1.5:
                    risk_level = "LOW"
                
                # Actionable outlook
                if overall_bias == "BULLISH":
                    outlook_text = f"Market showing **bullish bias** with {trend_strength:.1f}% trend strength. Consider **long positions** on pullbacks to support levels."
                elif overall_bias == "BEARISH":
                    outlook_text = f"Market showing **bearish bias** with {trend_strength:.1f}% trend strength. Consider **short positions** on rallies to resistance levels."
                else:
                    outlook_text = f"Market in **consolidation phase**. Wait for clear directional break above resistance or below support before positioning."
                
                outlook_embed = {
                    "title": f"🎯 Trading Outlook",
                    "color": bias_color,
                    "url": f"{dashboard_base_url}/outlook",
                    "description": outlook_text,
                    "fields": [
                        {
                            "name": "📊 Market Bias",
                            "value": f"{bias_emoji} **{overall_bias}**",
                            "inline": True
                        },
                        {
                            "name": "⚠️ Risk Level",
                            "value": f"**{risk_level}**",
                            "inline": True
                        },
                        {
                            "name": "💪 Trend Strength",
                            "value": f"**{trend_strength:.1f}%**",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": f"Virtuoso Engine | {utc_now.strftime('%H:%M:%S UTC')}",
                        "icon_url": virtuoso_logo_url
                    },
                    "timestamp": utc_now.isoformat() + 'Z'
                }
                
                embeds.append(outlook_embed)
            
            # --- Final Structure - Optimized for readability ---
            return {
                "content": f"# 🌟 Market Intelligence Report\n*{utc_now.strftime('%B %d, %Y - %H:%M UTC')}*",
                "embeds": embeds,
                "username": "Virtuoso Market Monitor",
                "avatar_url": virtuoso_logo_url
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting market report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Return a simplified error message
            return {
                "content": f"⚠️ Error generating market report: {str(e)}",
                "embeds": [{
                    "title": "Report Generation Error", 
                    "color": 15158332, 
                    "description": "Failed to format market intelligence report. Please check system logs."
                }]
            }

    async def generate_market_summary(self) -> Dict[str, Any]:
        """Generate comprehensive market summary report with monitoring."""
        start_time = time.time()
        section_times = {}
        
        try:
            self.logger.info(f"Starting market report generation at {datetime.now()}")
            
            # SECTION: Update Symbols
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Updating Symbols")
            await self.update_symbols()
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['update_symbols'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Get Top Pairs
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Getting Top Traded Pairs")
            top_pairs = self.symbols[:10]
            self.logger.info(f"Found {len(top_pairs)} top traded pairs: {top_pairs[:5]}...")
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['get_top_pairs'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Parallel Market Calculations
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Running Market Calculations")
            tasks = [
                self._calculate_with_monitoring('market_overview', self._calculate_market_overview, top_pairs),
                self._calculate_with_monitoring('top_performers', self._calculate_top_performers, top_pairs),
                self._calculate_with_monitoring('futures_premium', self._calculate_futures_premium, top_pairs),
                self._calculate_with_monitoring('smart_money_index', self._calculate_smart_money_index, top_pairs),
                self._calculate_with_monitoring('whale_activity', self._calculate_whale_activity, top_pairs),
                self._calculate_with_monitoring('performance_metrics', self._calculate_performance_metrics, top_pairs)
            ]
            
            self.logger.info("Gathering results from parallel calculations...")
            results = await asyncio.gather(*tasks)
            market_overview, top_performers, futures_premium, smi_data, whale_data, performance = results
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['parallel_calculations'] = section_duration
            self.logger.info(f"All calculations completed in {section_duration:.3f}s")
            
            # SECTION: Validation and Fallbacks
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Validation and Fallbacks")
            
            # Ensure we have valid data for each component
            validations = []
            
            if not market_overview:
                self.logger.warning("Market overview calculation failed, using fallback")
                market_overview = {
                    'regime': 'UNKNOWN',
                    'trend_strength': '0.0%',
                    'total_volume': 0,
                    'total_turnover': 0,
                    'total_open_interest': 0,
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("market_overview: FAILED")
            else:
                validations.append("market_overview: OK")
            
            if not top_performers:
                self.logger.warning("Top performers calculation failed, using fallback")
                top_performers = {
                    'gainers': [],
                    'losers': [],
                    'total_analyzed': 0,
                    'failed_symbols': len(top_pairs),
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("top_performers: FAILED")
            else:
                validations.append("top_performers: OK")
            
            if not futures_premium:
                self.logger.warning("Futures premium calculation failed, using fallback")
                futures_premium = {
                    'premiums': {},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("futures_premium: FAILED")
            else:
                validations.append("futures_premium: OK")
            
            if not smi_data:
                self.logger.warning("Smart money index calculation failed, using fallback")
                smi_data = {
                    'index': 50.0,
                    'signals': [],
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("smart_money_index: FAILED")
            else:
                validations.append("smart_money_index: OK")
            
            if not whale_data:
                self.logger.warning("Whale activity calculation failed, using fallback")
                whale_data = {
                    'whale_activity': {},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("whale_activity: FAILED")
            else:
                validations.append("whale_activity: OK")
            
            if not performance:
                self.logger.warning("Performance metrics calculation failed, using fallback")
                performance = {
                    'metrics': {},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }
                validations.append("performance_metrics: FAILED")
            else:
                validations.append("performance_metrics: OK")
                
            self.logger.info(f"Component validations: {', '.join(validations)}")
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['validation'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Report Compilation
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Compiling Final Report")
            # Compile report
            report = {
                'timestamp': int(datetime.now().timestamp() * 1000),
                'generated_at': datetime.now().isoformat(),
                'market_overview': market_overview,
                'top_performers': top_performers,
                'futures_premium': futures_premium,
                'smart_money_index': smi_data,
                'whale_activity': whale_data,
                'performance_metrics': performance
            }
            
            # Calculate report size for logging
            report_size = len(json.dumps(report))
            self.logger.info(f"Report compiled: {report_size} bytes, {len(report)} sections")
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['compilation'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Save JSON for API Access
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Saving JSON for API")
            
            # Save report to JSON for API access
            try:
                # Create necessary directories
                reports_base_dir = os.path.join(os.getcwd(), 'reports')
                reports_json_dir = os.path.join(reports_base_dir, 'json')
                reports_html_dir = os.path.join(reports_base_dir, 'html')
                reports_pdf_dir = os.path.join(reports_base_dir, 'pdf')
                
                # Create export directory for backward compatibility
                export_dir = os.path.join(os.getcwd(), 'exports', 'market_reports', 'json')
                
                # Ensure all directories exist
                os.makedirs(reports_json_dir, exist_ok=True)
                os.makedirs(reports_html_dir, exist_ok=True)
                os.makedirs(reports_pdf_dir, exist_ok=True)
                os.makedirs(export_dir, exist_ok=True)
                
                # Get epoch timestamp for consistent naming across all files
                timestamp = int(time.time())
                
                # Define consistent filenames for all report types
                json_filename = f"market_report_{timestamp}.json"
                html_filename = f"market_report_{timestamp}.html"
                pdf_filename = f"market_report_{timestamp}.pdf"
                
                # Define full paths
                reports_json_path = os.path.join(reports_json_dir, json_filename)
                reports_html_path = os.path.join(reports_html_dir, html_filename)
                reports_pdf_path = os.path.join(reports_pdf_dir, pdf_filename)
                
                # Also save in the traditional location with date-based filename for backward compatibility
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_json_path = os.path.join(export_dir, f"market_report_{timestamp_str}.json")
                
                # Write the JSON content
                json_content = json.dumps(report, indent=2, default=str)
                
                with open(reports_json_path, 'w') as f:
                    f.write(json_content)
                
                with open(export_json_path, 'w') as f:
                    f.write(json_content)
                    
                self.logger.info(f"Market report JSON saved to {reports_json_path} and {export_json_path}")
                
                # Add paths to report for reference
                report['json_path'] = reports_json_path
                report['export_json_path'] = export_json_path
                report['html_path'] = reports_html_path
                report['pdf_path'] = reports_pdf_path
                report['timestamp'] = timestamp
                
            except Exception as e:
                self.logger.error(f"Error saving JSON report: {str(e)}")
                
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['json_export'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Performance Metrics
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Logging Performance Metrics")
            # Log performance metrics
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            await self._log_performance_metrics()
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['performance_logging'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Report Validation and Alerts
            section_start = time.time()
            self.logger.info("-" * 60)
            self.logger.info("REPORT SECTION: Validation and Alerts")
            # Validate report
            validation = self._validate_report_data(report)
            
            # Determine if all required sections are present
            required_sections = [
                'market_overview',
                'top_performers', 
                'futures_premium', 
                'smart_money_index',
                'whale_activity',
                'performance_metrics'
            ]
            all_sections_valid = all(section in report and report[section] for section in required_sections)
            
            # Set a quality score based on validation results
            # (100 if all sections are valid, or lower based on missing sections)
            quality_score = 100 if all_sections_valid else 100 - (len(required_sections) - sum(1 for s in required_sections if s in report and report[s])) * 20
            report['quality_score'] = quality_score
            
            if not all_sections_valid:
                self.logger.error(f"Report validation failed: missing required sections")
                self._log_error('report_validation', 'Invalid report generated')
                await self._send_alert(
                    "report_validation",
                    f"Market report validation failed: missing required sections",
                    "error"
                )
            else:
                self.logger.info(f"Report validation passed with quality score: {quality_score}")
                # Check for alert conditions
                await self._check_and_alert_conditions(report)
            
            section_end = time.time()
            section_duration = section_end - section_start
            section_times['report_validation'] = section_duration
            self.logger.info(f"Section completed in {section_duration:.3f}s")
            
            # SECTION: Summary
            total_duration = time.time() - start_time
            self.logger.info("-" * 60)
            self.logger.info("REPORT GENERATION SUMMARY")
            self.logger.info(f"Total time: {total_duration:.3f}s")
            
            # Display section timings
            for section, duration in section_times.items():
                percentage = (duration / total_duration) * 100
                self.logger.info(f"  - {section}: {duration:.3f}s ({percentage:.1f}%)")
            
            return report
            
        except Exception as e:
            self._log_error('report_generation', str(e))
            self.logger.error(f"Error generating market summary: {str(e)}")
            self.logger.error(f"Stack trace:\n{traceback.format_exc()}")
            if self.alert_manager:
                await self._send_alert(
                    "report_generation",
                    f"Failed to generate market report: {str(e)}",
                    "error"
                )
            return None

    def _normalize_report_data(self, report: dict) -> dict:
        """Normalize and validate report data to ensure consistency for templates.
        
        This method ensures all expected fields exist with proper data types and formats,
        especially for template rendering.
        
        Args:
            report: Raw report data
            
        Returns:
            Normalized report data with fallbacks for missing fields
        """
        report = report.copy()  # Create a copy to avoid modifying the original
        
        # Process timestamp and add formatted versions for templates
        if 'timestamp' in report:
            timestamp = report['timestamp']
            # Convert string timestamp to int if needed
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                    report['timestamp'] = timestamp
                except ValueError:
                    timestamp = int(time.time())
                    report['timestamp'] = timestamp
                    
            # Ensure timestamp is in milliseconds for consistency
            if timestamp < 10000000000:  # If in seconds, convert to milliseconds
                timestamp = timestamp * 1000
                report['timestamp'] = timestamp
                
            # Add properly formatted date strings for templates
            dt = datetime.fromtimestamp(timestamp / 1000)
            report['report_date'] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            report['formatted_date'] = dt.strftime("%B %d, %Y")
            report['formatted_time'] = dt.strftime("%H:%M:%S UTC")
            report['year'] = dt.year  # Used in footer
        else:
            # Add current timestamp if missing
            timestamp = int(time.time() * 1000)
            report['timestamp'] = timestamp
            dt = datetime.now()
            report['report_date'] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            report['formatted_date'] = dt.strftime("%B %d, %Y")
            report['formatted_time'] = dt.strftime("%H:%M:%S UTC")
            report['year'] = dt.year
        
        # Standard fallbacks for missing sections or fields
        fallbacks = {
            'market_overview': {
                'regime': 'NEUTRAL',
                'trend_strength': '0.0%',
                'daily_change': 0.0,
                'weekly_change': 0.0,
                'btc_price': 0.0,
                'eth_price': 0.0,
                'total_volume': 0,
                'btc_dominance': '0.0%',
                'volatility': 'LOW',
                'strength': 50.0,
                'volume_change': 0.0,
            },
            'futures_premium': {
                'average_premium': '0.0%',
                'contango_status': 'NEUTRAL',
                'max_premium': '0.0%',
                'min_premium': '0.0%',
                'data': []
            },
            'smart_money_index': {
                'index': 50.0,
                'sentiment': 'NEUTRAL',
                'institutional_flow': '+0.0%',
                'funding_rates_classification': 'NEUTRAL',
                'key_zones': []
            },
            'whale_activity': {
                'has_significant_activity': False,
                'significant_activity': {},
                'large_transactions': []
            },
            'performance_metrics': {
                'api_latency': {'avg': 0, 'max': 0, 'p95': 0},
                'error_rate': {'total': 0, 'by_type': {}, 'errors_per_minute': 0},
                'data_quality': {'avg_score': 100, 'min_score': 100},
                'processing_time': {'avg': 0, 'max': 0}
            }
        }
        
        # Ensure all sections exist with proper formatting and nested fields
        for key, fallback in fallbacks.items():
            if key not in report or not isinstance(report[key], dict):
                self.logger.warning(f"Missing or invalid section '{key}' in report, using fallback")
                report[key] = fallback.copy()
            else:
                # Ensure all expected fields exist in each section
                for subkey, value in fallback.items():
                    if subkey not in report[key]:
                        self.logger.debug(f"Adding missing field '{key}.{subkey}' with fallback value")
                        report[key][subkey] = value
        
        # Special handling for market regime to ensure consistent classification
        if 'market_overview' in report and 'regime' in report['market_overview']:
            # Normalize regime values to one of the standard classifications
            regime = report['market_overview']['regime'].upper()
            if regime in ['BULL', 'BULLISH', 'UP', 'UPTREND']:
                report['market_overview']['regime'] = 'BULLISH'
            elif regime in ['BEAR', 'BEARISH', 'DOWN', 'DOWNTREND']:
                report['market_overview']['regime'] = 'BEARISH'
            elif regime in ['NEUTRAL', 'SIDEWAYS']:
                report['market_overview']['regime'] = 'NEUTRAL'
            elif regime in ['RANGE', 'RANGING', 'CONSOLIDATION']:
                report['market_overview']['regime'] = 'RANGING'
            else:
                report['market_overview']['regime'] = 'NEUTRAL'
                
            # Add descriptive regime text for templates
            regime_map = {
                'BULLISH': 'Bullish market conditions with upward momentum',
                'BEARISH': 'Bearish market conditions with downward pressure',
                'NEUTRAL': 'Neutral market conditions with balanced forces',
                'RANGING': 'Ranging market with defined support and resistance'
            }
            report['market_overview']['regime_description'] = regime_map.get(
                report['market_overview']['regime'], 'Neutral market conditions'
            )
            
        # Ensure additional sections exist for template compatibility
        if 'additional_sections' not in report:
            report['additional_sections'] = {}
            
        # Add derived market sentiment section based on available data
        if 'market_sentiment' not in report['additional_sections']:
            # Create market sentiment summary from existing data
            market_regime = report['market_overview'].get('regime', 'NEUTRAL')
            volume_change = report['market_overview'].get('volume_change', 0)
            funding_rates = report['smart_money_index'].get('funding_rates_classification', 'NEUTRAL')
            
            report['additional_sections']['market_sentiment'] = {
                'overall': "Bullish" if market_regime == 'BULLISH' else 
                           "Bearish" if market_regime == 'BEARISH' else 
                           "Ranging" if market_regime == 'RANGING' else "Neutral",
                'volume_sentiment': "Increasing" if volume_change > 0 else "Decreasing",
                'funding_rates': funding_rates,
                'btc_support': report['market_overview'].get('btc_support', 0),
                'btc_resistance': report['market_overview'].get('btc_resistance', 0)
            }
            
        # Add futures premium analysis if not present
        if 'futures_premium_analysis' not in report['additional_sections']:
            report['additional_sections']['futures_premium_analysis'] = {
                'btc_premium': report['futures_premium'].get('average_premium', '0.00%'),
                'contango_status': report['futures_premium'].get('contango_status', 'NEUTRAL'),
                'funding_situation': f"Current funding rates are {report['smart_money_index'].get('funding_rates_classification', 'neutral').lower()}"
            }
            
        # Add template flags to control conditional sections
        report['has_smart_money_data'] = report['smart_money_index']['index'] != 50.0 or len(report['smart_money_index'].get('key_zones', [])) > 0
        report['has_whale_activity'] = report['whale_activity']['has_significant_activity']
        report['has_futures_data'] = len(report['futures_premium'].get('data', [])) > 0
        
        return report

    async def generate_market_report(self, report_data: Dict[str, Any]) -> bool:
        """Generate a complete market report.
        
        Args:
            report_data: The report data to use for generation.
            
        Returns:
            bool: True if report generation was successful, False otherwise.
        """
        try:
            # Check if core analytical sections are missing. If so, generate them.
            required_analytical_sections = [
                'market_overview', 
                'futures_premium', 
                'smart_money_index',
                'whale_activity',
                'performance_metrics' # This one is often calculated by generate_market_summary
            ]
            
            missing_analytical = any(section not in report_data for section in required_analytical_sections)
            
            if missing_analytical:
                self.logger.info("Core analytical sections missing in input report_data. Attempting to generate them now via generate_market_summary().")
                analytical_summary = await self.generate_market_summary()
                if analytical_summary:
                    # Merge the generated summary into the provided report_data
                    # The summary data should take precedence for these sections.
                    report_data.update(analytical_summary)
                    self.logger.info("Successfully generated and merged analytical summary.")
                else:
                    self.logger.error("Failed to generate analytical summary internally. Report may be incomplete.")
                    # Proceeding, but _validate_report_data will likely use fallbacks for these.

            # Validate and normalize the report data
            validated_data = self._validate_report_data(report_data)
            
            # Log detailed debug information
            self.logger.debug(f"Generating market report with validated data")
            self.logger.debug(f"Market data keys: {list(validated_data.keys())}")
            self.logger.debug(f"Data validation complete - generating JSON and PDF outputs")
            
            # Create detailed debug log for troubleshooting
            if self.logger.level <= logging.DEBUG:
                try:
                    debug_json = json.dumps(validated_data, indent=2, default=str)
                    debug_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "debug")
                    os.makedirs(debug_log_dir, exist_ok=True)
                    debug_log_path = os.path.join(debug_log_dir, f"market_report_debug_{int(time.time())}.json")
                    with open(debug_log_path, 'w') as f:
                        f.write(debug_json)
                    self.logger.debug(f"Wrote debug market data to {debug_log_path}")
                except Exception as debug_err:
                    self.logger.debug(f"Failed to write debug log: {str(debug_err)}")
            
            # Generate PDF report
            pdf_path = await self.generate_market_pdf_report(validated_data)
            if not pdf_path:
                self.logger.error("Failed to generate PDF report")
                return False
                
            # Generate JSON report for API access
            timestamp = validated_data.get('timestamp', int(time.time()))
            json_saved = await self._save_report_json(validated_data, timestamp)
            if not json_saved:
                self.logger.error("Failed to save report JSON")
                return False
                
            # Report successful generation
            self.logger.info(f"Market report PDF generated at {pdf_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate market report: {str(e)}")
            traceback.print_exc()
            return False

    def _log_template_error(self, error_message: str, template_path: str, data: Dict[str, Any]) -> None:
        """Log detailed errors related to template rendering to help diagnose issues.
        
        Args:
            error_message: The error message
            template_path: Path to the template that failed
            data: The data that was being rendered
        """
        # Log the basic error
        self.logger.error(f"Template error: {error_message}")
        
        # Try to extract useful information about the template
        try:
            # Verify template exists
            if not os.path.exists(template_path):
                self.logger.error(f"Template file not found: {template_path}")
                
                # Check template directory
                template_dir = os.path.dirname(template_path)
                if not os.path.exists(template_dir):
                    self.logger.error(f"Template directory does not exist: {template_dir}")
                else:
                    # List available templates
                    templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
                    self.logger.info(f"Available templates in {template_dir}: {templates}")
            else:
                # Get template size
                template_size = os.path.getsize(template_path)
                self.logger.info(f"Template exists: {template_path}, size: {template_size} bytes")
                
                # Check template content (first few lines)
                try:
                    with open(template_path, 'r') as f:
                        first_lines = [next(f) for _ in range(10)]
                        self.logger.debug(f"Template first 10 lines: {first_lines}")
                except Exception as read_err:
                    self.logger.error(f"Error reading template: {str(read_err)}")
        except Exception as template_check_err:
            self.logger.error(f"Error checking template: {str(template_check_err)}")
        
        # Log data structure for debugging
        try:
            # Log top-level keys
            self.logger.info(f"Data keys: {list(data.keys())}")
            
            # Specifically check for keys used in market_report_dark.html
            required_template_keys = [
                'timestamp', 'report_date', 'market_overview', 'futures_premium', 
                'smart_money_index', 'whale_activity', 'performance_metrics'
            ]
            
            missing_keys = [k for k in required_template_keys if k not in data]
            if missing_keys:
                self.logger.error(f"Missing required template keys: {missing_keys}")
                
            # Log specific nested keys that might be referenced in the template
            if 'market_overview' in data:
                market_keys = list(data['market_overview'].keys())
                self.logger.info(f"market_overview keys: {market_keys}")
                
                # Check specific fields that might cause template errors
                if 'regime' in data['market_overview']:
                    self.logger.info(f"market_overview.regime = {data['market_overview']['regime']}")
                    
            # Similar checks for other key sections
            for section in ['futures_premium', 'smart_money_index', 'whale_activity']:
                if section in data and isinstance(data[section], dict):
                    section_keys = list(data[section].keys())
                    self.logger.info(f"{section} keys: {section_keys}")
        except Exception as data_check_err:
            self.logger.error(f"Error checking data structure: {str(data_check_err)}")
            
        # Add stack trace for context
        self.logger.error(traceback.format_exc())

    async def _save_report_json(self, report_data: Dict[str, Any], timestamp: int) -> bool:
        """Save the market report data to a JSON file.
        
        Args:
            report_data: The report data to save.
            timestamp: The timestamp to use in the filename.
            
        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            # Create reports JSON directory
            reports_json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "json")
            os.makedirs(reports_json_dir, exist_ok=True)
            
            # Create exports JSON directory
            exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "market_reports", "json")
            os.makedirs(exports_dir, exist_ok=True)
            
            # Validate timestamp to prevent "year out of range" errors
            # First ensure timestamp is an integer
            try:
                timestamp = int(timestamp)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timestamp format: {timestamp}, using current time")
                timestamp = int(time.time())
                
            # Check if timestamp is in milliseconds and convert to seconds if needed
            # (Unix timestamps in milliseconds are typically 13 digits for current dates)
            if timestamp > 10000000000:  # Likely milliseconds timestamp
                timestamp_seconds = timestamp // 1000  # Convert ms to seconds
            else:
                timestamp_seconds = timestamp
                
            # Verify timestamp is within reasonable range
            current_time = int(time.time())
            if timestamp_seconds < 1000000000 or timestamp_seconds > current_time + 86400:  # Before ~2001 or more than 1 day in future
                self.logger.warning(f"Timestamp outside reasonable range: {timestamp_seconds}, using current time")
                timestamp_seconds = current_time
                
            # Create filenames
            json_filename = f"market_report_{timestamp}.json"
            
            # Create readable datetime for export filename with validation
            try:
                dt = datetime.fromtimestamp(timestamp_seconds)
                export_filename = f"market_report_{dt.strftime('%Y%m%d_%H%M%S')}.json"
            except (ValueError, OSError, OverflowError) as e:
                self.logger.warning(f"Error converting timestamp to datetime: {e}")
                export_filename = f"market_report_{int(time.time())}.json"
            
            # Save to reports directory
            json_path = os.path.join(reports_json_dir, json_filename)
            with open(json_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            # Save to exports directory
            export_path = os.path.join(exports_dir, export_filename)
            with open(export_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            self.logger.info(f"Market report JSON saved to {json_path} and {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save report JSON: {str(e)}")
            traceback.print_exc()
            return False
    
    def _get_last_friday_of_month(self, year: int, month: int) -> datetime:
        """Get the last Friday of a given month and year."""
        # Get the last day of the month
        if month == 12:
            last_day = datetime(year, 12, 31)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Find the last Friday
        offset = (4 - last_day.weekday()) % 7  # Friday is 4
        last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
        return last_friday
        
    def _calculate_months_to_expiry(self, expiry_month: int, pattern: str) -> int:
        """Calculate months to expiry for a futures contract."""
        current_month = datetime.now().month
        current_year = datetime.now().year
        pattern_year = int(pattern[-2:]) + 2000  # Extract year from pattern and convert to full year
        
        if pattern_year > current_year:
            # Contract expires next year
            return (expiry_month + 12) - current_month
        else:
            # Contract expires this year
            return max(1, expiry_month - current_month)  # Ensure at least 1 month
            
    async def _check_quarterly_futures(self):
        """Test method to check if quarterly futures symbols are valid.
        This is a helper method for debugging symbol format issues.
        """
        try:
            # Test with common assets
            symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
            
            for base_asset in symbols:
                current_year = datetime.now().year % 100
                current_month = datetime.now().month
                year = datetime.now().year
                
                # Get clean base asset
                base_asset_clean = base_asset.strip()
                
                # Try unified formats first (MMDD format)
                unified_quarterly_patterns = []
                
                # June quarterly
                if current_month <= 6:
                    june_date = self._get_last_friday_of_month(year, 6)
                    june_pattern = f"{base_asset_clean}USDT{june_date.month:02d}{june_date.day:02d}"
                    unified_quarterly_patterns.append(june_pattern)
                
                # September quarterly
                if current_month <= 9:
                    sept_date = self._get_last_friday_of_month(year, 9)
                    sept_pattern = f"{base_asset_clean}USDT{sept_date.month:02d}{sept_date.day:02d}"
                    unified_quarterly_patterns.append(sept_pattern)
                
                # December quarterly
                dec_date = self._get_last_friday_of_month(year, 12)
                dec_pattern = f"{base_asset_clean}USDT{dec_date.month:02d}{dec_date.day:02d}"
                unified_quarterly_patterns.append(dec_pattern)
                
                # Old inverse patterns
                inverse_quarterly_patterns = [
                    f"{base_asset_clean}USDM{current_year}",
                    f"{base_asset_clean}USDU{current_year}",
                    f"{base_asset_clean}USDZ{current_year}"
                ]
                
                # Old USDT patterns with hyphens
                usdt_quarterly_patterns = []
                
                if current_month <= 6:
                    june_date = self._get_last_friday_of_month(year, 6)
                    usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{june_date.day}JUN{current_year}")
                
                if current_month <= 9:
                    sept_date = self._get_last_friday_of_month(year, 9)
                    usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{sept_date.day}SEP{current_year}")
                
                dec_date = self._get_last_friday_of_month(year, 12)
                usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{dec_date.day}DEC{current_year}")
                
                # Test all pattern formats
                all_patterns = unified_quarterly_patterns + inverse_quarterly_patterns + usdt_quarterly_patterns
                print(f"Testing patterns for {base_asset}: {all_patterns}")
                
                # Try to fetch ticker data for each pattern
                for pattern in all_patterns:
                    try:
                        if hasattr(self, 'exchange') and self.exchange:
                            ticker = await self.exchange.fetch_ticker(pattern)
                            if ticker:
                                print(f"✅ Found valid quarterly future: {pattern}")
                        else:
                            print(f"⚠️ Exchange not available to test {pattern}")
                    except Exception as e:
                        print(f"❌ Pattern {pattern} invalid: {str(e)}")
                        
        except Exception as e:
            print(f"Error in test: {str(e)}")

    async def _calculate_top_performers(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate top performing symbols (gainers and losers)."""
        try:
            self.logger.debug(f"Calculating top performers for {len(symbols)} symbols")
            
            performers = []
            failed_symbols = []
            
            for symbol in symbols[:20]:  # Limit to top 20 symbols for performance
                try:
                    # Get 24h ticker data
                    ticker_data = await self._fetch_with_retry('fetch_ticker', symbol)
                    
                    if ticker_data and 'percentage' in ticker_data:
                        change_percent = float(ticker_data.get('percentage', 0))
                        
                        performer = {
                            'symbol': symbol,
                            'price': float(ticker_data.get('last', 0)),
                            'change_percent': change_percent,
                            'volume': float(ticker_data.get('baseVolume', 0)),
                            'change': f"{change_percent:+.2f}"
                        }
                        performers.append(performer)
                        
                except Exception as e:
                    failed_symbols.append(symbol)
                    self.logger.debug(f"Failed to get ticker for {symbol}: {str(e)}")
                    continue
            
            # Sort by change percentage
            performers.sort(key=lambda x: x['change_percent'], reverse=True)
            
            # Get top gainers and losers
            gainers = [p for p in performers if p['change_percent'] > 0][:5]
            losers = [p for p in performers if p['change_percent'] < 0][-5:]
            losers.reverse()  # Show worst performers first
            
            result = {
                'gainers': gainers,
                'losers': losers,
                'total_analyzed': len(performers),
                'failed_symbols': len(failed_symbols),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
            self.logger.debug(f"Top performers calculated: {len(gainers)} gainers, {len(losers)} losers")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating top performers: {str(e)}")
            return {
                'gainers': [],
                'losers': [],
                'total_analyzed': 0,
                'failed_symbols': len(symbols),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }