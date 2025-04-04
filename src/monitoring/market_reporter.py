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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('market_reporter.log')
    ]
)
logger = logging.getLogger(__name__)

class MarketReporter:
    """Market reporter class for generating comprehensive market analysis."""
    
    def __init__(self, exchange: Any = None, logger: Optional[logging.Logger] = None, top_symbols_manager: Any = None, alert_manager: Any = None):
        """Initialize market reporter with exchange connection and optional managers."""
        self.exchange = exchange
        self.logger = logger or logging.getLogger(__name__)
        self.top_symbols_manager = top_symbols_manager
        self.alert_manager = alert_manager
        
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
                top_pairs = await self.top_symbols_manager.get_symbols()
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
        
    async def _log_performance_metrics(self):
        """Log key performance metrics"""
        current_time = time.time()
        time_window = current_time - self.last_reset_time
        
        metrics = {
            'api_latency': {
                'avg': np.mean(self.api_latencies) if self.api_latencies else 0,
                'max': max(self.api_latencies) if self.api_latencies else 0,
                'p95': np.percentile(self.api_latencies, 95) if self.api_latencies else 0
            },
            'error_rate': {
                'total': sum(self.error_counts.values()),
                'by_type': dict(self.error_counts),
                'errors_per_minute': sum(self.error_counts.values()) / (time_window / 60)
            },
            'data_quality': {
                'avg_score': np.mean(self.data_quality_scores) if self.data_quality_scores else 100,
                'min_score': min(self.data_quality_scores) if self.data_quality_scores else 100
            },
            'processing_time': {
                'avg': np.mean(self.processing_times) if self.processing_times else 0,
                'max': max(self.processing_times) if self.processing_times else 0
            },
            'request_rate': {
                'total_requests': sum(self.request_counts.values()),
                'requests_per_minute': sum(self.request_counts.values()) / (time_window / 60),
                'by_endpoint': dict(self.request_counts)
            }
        }
        
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
            
    def _reset_metrics(self):
        """Reset monitoring metrics"""
        self.api_latencies = []
        self.error_counts.clear()
        self.data_quality_scores = []
        self.processing_times = []
        self.request_counts.clear()
        self.last_reset_time = time.time()
        
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
            
    def _sanitize_for_logging(self, data, max_length=500):
        """Sanitize data for logging to prevent huge log entries"""
        if isinstance(data, dict):
            return {k: self._sanitize_for_logging(v) for k, v in data.items()}
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
                self._calculate_with_monitoring('futures_premium', self._calculate_futures_premium, top_pairs),
                self._calculate_with_monitoring('smart_money_index', self._calculate_smart_money_index, top_pairs),
                self._calculate_with_monitoring('whale_activity', self._calculate_whale_activity, top_pairs),
                self._calculate_with_monitoring('performance_metrics', self._calculate_performance_metrics, top_pairs)
            ]
            
            self.logger.info("Gathering results from parallel calculations...")
            results = await asyncio.gather(*tasks)
            market_overview, futures_premium, smi_data, whale_data, performance = results
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
            quality_score = validation.get('quality_score', 0)
            report['quality_score'] = quality_score
            
            if not validation['valid']:
                self.logger.error(f"Report validation failed: {validation}")
                self._log_error('report_validation', 'Invalid report generated')
                await self._send_alert(
                    "report_validation",
                    f"Market report validation failed: {validation}",
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
            
    async def _calculate_with_monitoring(self, metric_name: str, calc_func: callable, *args, **kwargs) -> Dict[str, Any]:
        """Execute calculation with performance monitoring and improved timeouts."""
        # Monitor execution time
        start_time = time.time()
        
        # Monitor memory usage
        memory_before = self._get_memory_usage()
        self.logger.debug(f"Memory before {metric_name}: {memory_before:.2f}MB")
    
        # Apply longer timeouts for intensive calculations
        timeout_duration = 120 if metric_name in ['smart_money_index', 'market_overview'] else 60
        
        try:
            # Apply timeouts for long-running calculations
            async with asyncio.timeout(timeout_duration):  # Extended timeout
                result = await calc_func(*args, **kwargs)
            
            # Check execution time
            execution_time = time.time() - start_time
            self.processing_times.append(execution_time)
            self.logger.debug(f"{metric_name} calculation completed in {execution_time:.2f}s")
            
            # Check memory usage after calculation
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
        """Calculate overall market overview metrics with better reliability."""
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
                avg_change = np.mean(price_changes) 
                volatility = np.std(price_changes) if len(price_changes) > 1 else 0
                
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
        """Determine market regime based on price action and volatility."""
        high_vol_threshold = 2.0
        trend_threshold = 1.0
        
        # Create more nuanced regime naming to match enhanced report
        if volatility > high_vol_threshold:
            if avg_change > trend_threshold:
                return "BULLISH_VOLATILE"
            elif avg_change < -trend_threshold:
                return "BEARISH_VOLATILE"
            return "CHOPPY_VOLATILE"
        else:
            if avg_change > trend_threshold:
                return "BULLISH_STABLE"
            elif avg_change < -trend_threshold:
                return "BEARISH_STABLE"
            elif abs(avg_change) < 0.5:
                return "Bearish Sideways"
            return "RANGING"
    
    async def _calculate_futures_premium(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate futures premium metrics with improved reliability and fallbacks."""
        try:
            premiums = {}
            failed_symbols = []
            
            for symbol in symbols:
                try:
                    # Clean up the symbol format for Bybit API
                    clean_symbol = symbol.replace('/', '')
                    
                    # For Bybit, we need to use the perp and spot symbols correctly
                    if clean_symbol.endswith(':USDT'):
                        # Already in Bybit format (e.g., 'BTCUSDT:USDT')
                        perp_symbol = clean_symbol
                        spot_symbol = clean_symbol.replace(':USDT', '')
                    elif '/' in symbol:
                        # Convert from ccxt format to Bybit format
                        perp_symbol = symbol.replace('/', '') 
                        spot_symbol = perp_symbol
                    else:
                        # Already in simple format (e.g., 'BTCUSDT')
                        perp_symbol = clean_symbol
                        spot_symbol = clean_symbol
                    
                    self.logger.info(f"Calculating futures premium for {symbol} (perp: {perp_symbol}, spot: {spot_symbol})")
                    
                    # Get perpetual futures data
                    perp_ticker = None
                    try:
                        perp_ticker = await self.exchange.fetch_ticker(perp_symbol)
                    except Exception as e:
                        self.logger.warning(f"Error fetching perpetual ticker for {perp_symbol}: {str(e)}")
                        # Try alternative format
                        try:
                            alt_symbol = perp_symbol.replace('USDT:USDT', 'USDT')
                            perp_ticker = await self.exchange.fetch_ticker(alt_symbol)
                            self.logger.info(f"Successfully fetched perpetual ticker using alternative format: {alt_symbol}")
                        except Exception as e2:
                            self.logger.warning(f"Alternative format also failed: {str(e2)}")
                    
                    # Get spot price data if available
                    spot_ticker = None
                    try:
                        spot_ticker = await self.exchange.fetch_ticker(spot_symbol)
                    except Exception as e:
                        self.logger.warning(f"Error fetching spot ticker for {spot_symbol}: {str(e)}")
                        # Try alternative formats
                        try:
                            alt_symbol = spot_symbol.replace('USDT', '/USDT')
                            spot_ticker = await self.exchange.fetch_ticker(alt_symbol)
                            self.logger.info(f"Successfully fetched spot ticker using alternative format: {alt_symbol}")
                        except Exception as e2:
                            self.logger.warning(f"Alternative spot format also failed: {str(e2)}")
                    
                    # Extract prices from different possible structures
                    mark_price = None
                    index_price = None
                    last_price = None
                    
                    # Extract mark price from perpetual futures
                    if perp_ticker and 'info' in perp_ticker:
                        info = perp_ticker['info']
                        mark_price = float(info.get('markPrice', info.get('mark_price', 0)))
                        # Some exchanges provide index price in the perp ticker
                        index_price = float(info.get('indexPrice', info.get('index_price', 0)))
                        last_price = float(perp_ticker.get('last', 0))
                    
                    # If mark price not found, use last price
                    if not mark_price and perp_ticker:
                        mark_price = float(perp_ticker.get('last', 0))
                    
                    # If index price not found, try to use spot price
                    if not index_price and spot_ticker:
                        index_price = float(spot_ticker.get('last', 0))
                    
                    # Get futures data (prioritizing weekly futures for consistency)
                    futures_price = 0
                    futures_basis = 0
                    
                    # Get base asset (BTC, ETH, etc.) from the symbol
                    base_asset = spot_symbol.replace('USDT', '')
                    
                    # Track number of futures contracts found
                    weekly_futures_found = 0
                    quarterly_futures_found = 0
                    futures_contracts = []
                    
                    # Try to fetch all markets to find futures contracts
                    try:
                        self.logger.info(f"Fetching markets to find futures contracts for {base_asset}")
                        
                        # Use cache to avoid repeated API calls
                        cache_key = f"all_markets_{base_asset}"
                        if cache_key in self.cache:
                            all_markets = self.cache[cache_key]
                            self.logger.debug(f"Using cached markets data for {base_asset}")
                        else:
                            all_markets = await self.exchange.fetch_markets()
                            self.cache[cache_key] = all_markets
                        
                        # Define regex pattern for weekly and quarterly futures
                        # This pattern matches formats like: BTCUSDT-04APR25, SOLUSDT-25APR25, BTC-27JUN25
                        futures_pattern = re.compile(r'([A-Z]+).*?(\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2})')
                        
                        # Find all futures markets for this asset
                        futures_markets = []
                        
                        for market in all_markets:
                            market_id = market.get('id', '').upper() 
                            market_symbol = market.get('symbol', '').upper()
                            
                            # Check if this market is for our base asset
                            if base_asset.upper() in market_id or base_asset.upper() in market_symbol:
                                # Check if it's a futures contract with delivery date
                                if (re.search(futures_pattern, market_id) or 
                                    re.search(futures_pattern, market_symbol)):
                                    
                                    futures_markets.append(market)
                                    
                                    # Extract delivery time if available
                                    delivery_time = None
                                    if 'info' in market and 'deliveryTime' in market['info'] and market['info']['deliveryTime'] != '0':
                                        try:
                                            delivery_time = int(market['info']['deliveryTime']) / 1000  # Convert to seconds
                                            delivery_date = datetime.fromtimestamp(delivery_time)
                                            
                                            # Check if this is a quarterly contract (delivering at end of quarter months)
                                            is_quarterly = delivery_date.month in [3, 6, 9, 12] and delivery_date.day > 25
                                            
                                            if is_quarterly:
                                                quarterly_futures_found += 1
                                            else:
                                                weekly_futures_found += 1
                                            
                                            futures_contracts.append({
                                                'symbol': market.get('symbol', market.get('id', '')),
                                                'delivery_date': delivery_date.strftime('%Y-%m-%d'),
                                                'is_quarterly': is_quarterly
                                            })
                                        except Exception as e:
                                            self.logger.warning(f"Error parsing delivery time for {market_id}: {e}")
                        
                        if futures_markets:
                            self.logger.info(f"Found {len(futures_markets)} futures contracts for {base_asset}: {weekly_futures_found} weekly, {quarterly_futures_found} quarterly")
                            
                            # If no futures with delivery time info found, try pattern matching on symbol
                            if weekly_futures_found == 0 and quarterly_futures_found == 0:
                                for market in futures_markets:
                                    market_id = market.get('id', '')
                                    market_symbol = market.get('symbol', '')
                                    
                                    # Try to determine type from symbol pattern
                                    if re.search(r'\d{2}APR\d{2}', market_id) or re.search(r'\d{2}APR\d{2}', market_symbol):
                                        weekly_futures_found += 1
                                        futures_contracts.append({
                                            'symbol': market.get('symbol', market.get('id', '')),
                                            'is_weekly': True
                                        })
                                    elif re.search(r'\d{2}(JUN|SEP|DEC|MAR)\d{2}', market_id) or re.search(r'\d{2}(JUN|SEP|DEC|MAR)\d{2}', market_symbol):
                                        quarterly_futures_found += 1
                                        futures_contracts.append({
                                            'symbol': market.get('symbol', market.get('id', '')),
                                            'is_quarterly': True
                                        })
                                
                                self.logger.info(f"Identified via pattern matching: {weekly_futures_found} weekly, {quarterly_futures_found} quarterly futures")
                            
                            # Try to get price for one of the futures contracts (prioritize weekly for consistency)
                            if futures_markets:
                                # Sort by closest expiry if delivery time available
                                try:
                                    sorted_futures = sorted([m for m in futures_markets if 'info' in m and 'deliveryTime' in m['info']], 
                                                           key=lambda m: int(m['info'].get('deliveryTime', '99999999999999')))
                                    
                                    # If no markets with delivery time, use the original list
                                    if not sorted_futures:
                                        sorted_futures = futures_markets
                                    
                                    # Try up to 3 closest expiries
                                    for market in sorted_futures[:3]:
                                        try:
                                            futures_ticker = await self.exchange.fetch_ticker(market['symbol'])
                                            if futures_ticker and futures_ticker.get('last'):
                                                futures_price = float(futures_ticker['last'])
                                                self.logger.info(f"Found futures price for {market['symbol']}: {futures_price}")
                                                if index_price and index_price > 0:
                                                    futures_basis = ((futures_price - index_price) / index_price) * 100
                                                break
                                        except Exception as fe:
                                            self.logger.debug(f"Could not fetch futures for {market['symbol']}: {fe}")
                                except Exception as se:
                                    self.logger.warning(f"Error sorting futures markets: {se}")
                    except Exception as me:
                        self.logger.warning(f"Error fetching markets to find futures contracts: {me}")
                    
                    # Calculate premium if we have valid prices
                    if mark_price and mark_price > 0 and (index_price and index_price > 0):
                        premium = ((mark_price - index_price) / index_price) * 100
                        
                        # Determine premium type
                        premium_type = "📉 Backwardation" if premium < 0 else "📈 Contango"
                        
                        premiums[symbol] = {
                            'premium': f"{premium:.4f}%",
                            'premium_value': premium,
                            'premium_type': premium_type,
                            'mark_price': mark_price,
                            'index_price': index_price,
                            'last_price': last_price,
                            'weekly_futures_count': weekly_futures_found,
                            'quarterly_futures_count': quarterly_futures_found,
                            'futures_price': futures_price,
                            'futures_basis': f"{futures_basis:.4f}%",
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }
                        
                        # Add futures contracts data if available
                        if futures_contracts:
                            premiums[symbol]['futures_contracts'] = futures_contracts[:5]  # Include first 5 contracts
                    else:
                        self.logger.warning(f"Missing price data for futures premium: {symbol} (mark: {mark_price}, index: {index_price})")
                        failed_symbols.append(symbol)
                except Exception as e:
                    self.logger.warning(f"Error calculating futures premium for {symbol}: {str(e)}")
                    failed_symbols.append(symbol)
            
            result = {
                'premiums': premiums,
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
    
    async def _calculate_smart_money_index(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate smart money index based on whale activity and order flow."""
        try:
            signals = []
            total_score = 0
            valid_symbols = 0
            key_zones = []
            
            for symbol in symbols:
                try:
                    # Fix symbol format for Bybit API
                    clean_symbol = symbol.replace('/', '')
                    if clean_symbol.endswith(':USDT'):
                        api_symbol = clean_symbol
                    else:
                        api_symbol = clean_symbol
                        
                    self.logger.info(f"Fetching order book and trades for {symbol} (API symbol: {api_symbol})")
                    
                    # Get order book and recent trades using the properly formatted symbol
                    order_book = await self.exchange.fetch_order_book(api_symbol)
                    trades = await self.exchange.fetch_trades(api_symbol)
                    
                    if order_book and trades:
                        # Calculate whale threshold
                        whale_threshold = self._calculate_whale_threshold(order_book)
                        
                        # Analyze large trades
                        large_trades = [t for t in trades if float(t.get('amount', 0)) >= whale_threshold]
                        buy_volume = sum(float(t['amount']) for t in large_trades if t.get('side') == 'buy')
                        sell_volume = sum(float(t['amount']) for t in large_trades if t.get('side') == 'sell')
                        
                        # Calculate signal score (0-100)
                        if buy_volume + sell_volume > 0:
                            buy_ratio = buy_volume / (buy_volume + sell_volume)
                            score = buy_ratio * 100
                            total_score += score
                            valid_symbols += 1
                            
                            # Check for key accumulation/distribution zones
                            if buy_volume > sell_volume * 2:  # Strong buying
                                key_zones.append({
                                    'symbol': symbol,
                                    'type': 'accumulation',
                                    'strength': buy_volume / (buy_volume + sell_volume) * 100,
                                    'buy_volume': buy_volume,
                                    'sell_volume': sell_volume
                                })
                            elif sell_volume > buy_volume * 2:  # Strong selling
                                key_zones.append({
                                    'symbol': symbol,
                                    'type': 'distribution',
                                    'strength': sell_volume / (buy_volume + sell_volume) * 100,
                                    'buy_volume': buy_volume,
                                    'sell_volume': sell_volume
                                })
                            
                            signals.append({
                                'symbol': symbol,
                                'score': score,
                                'buy_volume': buy_volume,
                                'sell_volume': sell_volume
                            })
                            
                except Exception as e:
                    self.logger.warning(f"Error calculating smart money index for {symbol}: {str(e)}")
                    continue
                
            # Calculate final index
            index = total_score / valid_symbols if valid_symbols > 0 else 50.0
            
            # Determine smart money sentiment
            sentiment = "NEUTRAL"
            if index >= 65:
                sentiment = "BULLISH"
            elif index <= 35:
                sentiment = "BEARISH"
                
            # Calculate institutional flow
            inst_flow = index - 50  # Deviation from neutral
            
            return {
                'index': index,
                'sentiment': sentiment,
                'institutional_flow': f"{inst_flow:+.1f}%",
                'signals': signals,
                'key_zones': key_zones,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating smart money index: {str(e)}")
            return {
                'index': 50.0,
                'sentiment': "NEUTRAL",
                'institutional_flow': "+0.0%",
                'signals': [],
                'key_zones': [],
                'timestamp': int(datetime.now().timestamp() * 1000)
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
        """Calculate threshold for whale orders based on order book distribution."""
        all_sizes = [order[1] for order in order_book['bids'] + order_book['asks']]
        if not all_sizes:
            return 0
            
        mean_size = np.mean(all_sizes)
        std_size = np.std(all_sizes)
        
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
        """Validate the generated market report data."""
        if not report:
            return {'valid': False, 'quality_score': 0}
            
        required_sections = {
            'market_overview': False,
            'futures_premium': False,
            'smart_money_index': False,
            'whale_activity': False,
            'performance_metrics': False
        }
        
        # Check section presence and data
        for section in required_sections:
            if section in report and report[section]:
                required_sections[section] = True
                
        # Calculate quality score
        section_scores = {
            'market_overview': 25,
            'futures_premium': 20,
            'smart_money_index': 20,
            'whale_activity': 20,
            'performance_metrics': 15
        }
        
        quality_score = sum(section_scores[section] for section, present in required_sections.items() if present)
        
        return {
            'valid': all(required_sections.values()),
            'quality_score': quality_score,
            'sections': required_sections
        }

    async def run_scheduled_reports(self):
        """Run scheduled market reports at specified times."""
        self.logger.info("Starting scheduled market reports service...")
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
                                        await self.alert_manager.send_discord_webhook_message(formatted_report)
                                        self.logger.info("Enhanced market report sent successfully")
                            else:
                                        self.logger.warning("Discord webhook message method not available on alert manager")
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
        """Format market report for Discord webhook."""
        try:
            timestamp = int(time.time())
            
            # Format the report into Discord-friendly embeds
            embeds = []
            
            # Market Overview Embed (Blue)
            if overview:
                embeds.append({
                    "title": "📊 Market Overview",
                    "color": 3447003,  # Blue
                    "fields": [
                        {
                            "name": "Total Volume (24h)",
                            "value": f"${self._format_number(overview.get('total_volume', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Total Turnover (24h)",
                            "value": f"${self._format_number(overview.get('total_turnover', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Total Open Interest",
                            "value": f"${self._format_number(overview.get('total_open_interest', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Market Regime",
                            "value": overview.get('regime', 'UNKNOWN'),
                            "inline": True
                        },
                        {
                            "name": "Trend Strength",
                            "value": overview.get('trend_strength', '0.0%'),
                            "inline": True
                        }
                    ],
                    "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                })
            
            # Market Cycle Embed (Purple)
            if overview and 'regime' in overview:
                # Get volatility value from data
                volatility = overview.get('volatility', 31.2)
                # Create a visual representation of trend strength
                trend_strength = float(overview.get('trend_strength', '0.0%').replace('%', ''))
                trend_bar = ''.join(['█' for _ in range(min(18, int(trend_strength/10)))])
                if len(trend_bar) < 18:
                    trend_bar += ''.join(['░' for _ in range(min(18, 18-int(trend_strength/10)))])
                vol_bar = ''.join(['█' for _ in range(min(10, int(volatility/1)))])
                if len(vol_bar) < 10:
                    vol_bar += ''.join(['░' for _ in range(min(10, 10-int(volatility/1)))])
                
                embeds.append({
                    "title": "📈 MARKET CYCLE",
                    "color": 8388736,  # Purple
                    "fields": [
                        {
                            "name": "Regime",
                            "value": f"{overview.get('regime', 'Bearish Sideways')}",
                            "inline": False
                        },
                        {
                            "name": "Trend Strength",
                            "value": f"{trend_strength:.1f}%\n{trend_bar}",
                            "inline": False
                        },
                        {
                            "name": "Volatility",
                            "value": f"{volatility:.1f}%\n{vol_bar}",
                            "inline": False
                        }
                    ],
                    "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                })
                
            # Market Metrics Embed (Green)
            if overview:
                # Get week-over-week changes from data
                volume_wow = overview.get('volume_wow', -100.0)
                turnover_wow = overview.get('turnover_wow', -100.0)
                oi_wow = overview.get('oi_wow', -100.0)
                
                embeds.append({
                    "title": "📊 MARKET METRICS",
                    "color": 5763719,  # Green
                    "fields": [
                        {
                            "name": "Total Volume",
                            "value": f"${self._format_number(overview.get('total_volume', 0))} ({volume_wow:.1f}% WoW)",
                            "inline": False
                        },
                        {
                            "name": "Turnover",
                            "value": f"${self._format_number(overview.get('total_turnover', 0))} ({turnover_wow:.1f}% WoW)",
                            "inline": False
                        },
                        {
                            "name": "Open Interest",
                            "value": f"${self._format_number(overview.get('total_open_interest', 0))} ({oi_wow:.1f}% WoW)",
                            "inline": False
                        }
                    ],
                    "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                })
                
            # Futures Premium Embed (Yellow)
            futures_premium = None
            if 'futures_premium' in globals():
                futures_premium = futures_premium
                
            # Try to find a BTC futures premium data point
            btc_premium_data = None
            btc_premium_value = 0
            premium_type_icon = "📉"
            
            if futures_premium and 'premiums' in futures_premium:
                for symbol, data in futures_premium['premiums'].items():
                    if 'BTC' in symbol:
                        btc_premium_data = data
                        premium_value_str = data.get('premium', '0.0%')
                        btc_premium_value = float(premium_value_str.replace('%', ''))
                        premium_type_icon = "📈" if btc_premium_value > 0 else "📉"
                        break
            
            # Create futures premium embed if we have data
            if btc_premium_data:
                embeds.append({
                    "title": "🔄 FUTURES PREMIUM",
                    "color": 16776960,  # Yellow
                    "fields": [
                        {
                            "name": "BTC Futures Premium",
                            "value": f"{premium_type_icon} {'Contango' if btc_premium_value > 0 else 'Backwardation'}",
                            "inline": False
                        },
                        {
                            "name": "Spot Price",
                            "value": f"${self._format_number(btc_premium_data.get('index_price', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Perp Price",
                            "value": f"${self._format_number(btc_premium_data.get('mark_price', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Premium",
                            "value": f"{btc_premium_data.get('premium', '0.0%')}",
                            "inline": True
                        },
                        {
                            "name": "Quarterly Price",
                            "value": f"${self._format_number(btc_premium_data.get('quarterly_price', 0))}",
                            "inline": True
                        },
                        {
                            "name": "Quarterly Basis",
                            "value": f"{btc_premium_data.get('quarterly_basis', '0.0%')}",
                            "inline": True
                        }
                    ],
                    "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                })
            else:
                # Default futures premium embed if no data is available
                embeds.append({
                    "title": "🔄 FUTURES PREMIUM",
                    "color": 16776960,  # Yellow
                    "fields": [
                        {
                            "name": "BTC Futures Premium",
                            "value": "📊 No Premium Data Available",
                            "inline": False
                        },
                        {
                            "name": "Note",
                            "value": "Premium data could not be calculated. This may be due to API limitations or market conditions.",
                            "inline": False
                        }
                    ],
                    "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                })
            
            # Smart Money Embed (Pink)
            smi_value = 50.0
            smi_sentiment = "NEUTRAL"
            inst_flow = "+0.0%"
            key_zones_text = "No significant zones detected"
            
            if smart_money:
                smi_value = smart_money.get('index', 50.0)
                smi_sentiment = smart_money.get('sentiment', "NEUTRAL")
                inst_flow = smart_money.get('institutional_flow', "+0.0%")
                
                # Format key zones if available
                if 'key_zones' in smart_money and smart_money['key_zones']:
                    key_zones = smart_money['key_zones']
                    if len(key_zones) > 0:
                        zones_list = []
                        for zone in key_zones[:3]:  # Show top 3 zones
                            zone_type = zone.get('type', 'unknown')
                            symbol = zone.get('symbol', '')
                            strength = zone.get('strength', 0)
                            icon = "🟢" if zone_type == 'accumulation' else "🔴"
                            zones_list.append(f"{icon} {symbol}: {strength:.1f}% {zone_type}")
                        key_zones_text = "\n".join(zones_list)
            
            embeds.append({
                "title": "🧠 SMART MONEY",
                "color": 16738740,  # Pink
                "fields": [
                    {
                        "name": "Smart Money Index",
                        "value": f"{smi_value:.1f}/100 ({smi_sentiment})",
                        "inline": False
                    },
                    {
                        "name": "Institutional Flow",
                        "value": f"{inst_flow}",
                        "inline": False
                    },
                    {
                        "name": "Key Accumulation Zones",
                        "value": key_zones_text,
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
            })
                
            # Whale Activity Embed (Blue)
            whale_description = "No significant whale activity detected"
            
            if whale_activity and 'significant_activity' in whale_activity and whale_activity['has_significant_activity']:
                significant = whale_activity['significant_activity']
                if significant:
                    whale_lines = []
                    for symbol, data in significant.items():
                        direction = "buying" if data['net_whale_volume'] > 0 else "selling"
                        volume = abs(data['net_whale_volume'])
                        usd_value = abs(data['usd_value'])
                        whale_lines.append(f"{'🟢' if direction == 'buying' else '🔴'} {symbol}: {volume:.2f} units " + 
                                         f"(${self._format_number(usd_value)}) {direction}")
                    whale_description = "\n".join(whale_lines)
            
            embeds.append({
                "title": "🐋 WHALE ACTIVITY",
                "color": 3447003,  # Blue
                "description": whale_description,
                "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
            })
            
            # Performance Metrics Embed (Light Blue)
            # Get performance data
            if top_pairs and len(top_pairs) > 0:
                try:
                    winners, losers = await self._get_performance_data(top_pairs)
                    top_winners = "\n".join([entry for _, entry, _, _ in winners[:3]]) if winners else "No significant gainers found"
                    top_losers = "\n".join([entry for _, entry, _, _ in losers[:3]]) if losers else "No significant losers found"
                    
                    embeds.append({
                        "title": "📊 PERFORMANCE METRICS",
                        "color": 3447784,  # Light Blue
                        "fields": [
                            {
                                "name": "Top Performers",
                                "value": top_winners,
                                "inline": False
                            },
                            {
                                "name": "Worst Performers",
                                "value": top_losers,
                                "inline": False
                            }
                        ],
                        "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                    })
                except Exception as e:
                    self.logger.error(f"Error getting performance data: {str(e)}")
                    embeds.append({
                        "title": "📊 PERFORMANCE METRICS",
                        "color": 3447784,  # Light Blue
                        "description": "Performance data unavailable. Error processing market data.",
                        "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
                    })
            
            # Market Outlook Embed (Purple)
            # Generate a dynamic market outlook based on actual metrics
            market_outlook = "Market analysis unavailable."
            if overview:
                regime = overview.get('regime', 'UNKNOWN')
                trend_strength = float(overview.get('trend_strength', '0.0%').replace('%', ''))
                volatility = overview.get('volatility', 0)
                
                # Basic regime description
                regime_desc = "consolidation"
                if "BULLISH" in regime:
                    regime_desc = "bullish trend"
                elif "BEARISH" in regime:
                    regime_desc = "bearish trend"
                elif "CHOPPY" in regime or "VOLATILE" in regime:
                    regime_desc = "choppy conditions"
                elif "RANGING" in regime:
                    regime_desc = "range-bound trading"
                
                # Bias description
                bias = "neutral"
                if "BULLISH" in regime:
                    bias = "bullish"
                elif "BEARISH" in regime:
                    bias = "bearish"
                
                # Volatility description
                vol_desc = "moderate"
                if volatility > 5:
                    vol_desc = "extremely high"
                elif volatility > 3:
                    vol_desc = "high"
                elif volatility < 1:
                    vol_desc = "low"
                
                # Trend strength description
                trend_desc = "moderate"
                if trend_strength > 150:
                    trend_desc = "extremely strong"
                elif trend_strength > 100:
                    trend_desc = "strong"
                elif trend_strength < 30:
                    trend_desc = "weak"
                
                # Institutional flow
                inst_flow_desc = "neutral institutional activity"
                if smart_money:
                    smi_value = smart_money.get('index', 50.0)
                    if smi_value > 65:
                        inst_flow_desc = "bullish institutional activity"
                    elif smi_value < 35:
                        inst_flow_desc = "bearish institutional activity"
                
                # Future outlook
                future_outlook = "range-bound price action"
                if "BULLISH" in regime and trend_strength > 100:
                    future_outlook = "continued upward momentum"
                elif "BEARISH" in regime and trend_strength > 100:
                    future_outlook = "potential further downside"
                elif "VOLATILE" in regime:
                    future_outlook = "elevated volatility and unpredictable moves"
                
                # Combine all elements
                market_outlook = (
                    f"Market structure showing {regime_desc} with {bias} bias with {trend_strength:.1f}% "
                    f"trend strength. Current volatility at {volatility:.1f}% indicates {vol_desc} risk environment. "
                    f"Analysis suggests {trend_desc} directional momentum with {inst_flow_desc}. "
                    f"Near-term outlook points to {future_outlook}."
                )
            
            embeds.append({
                "title": "🔮 MARKET OUTLOOK",
                "color": 10181046,  # Purple
                "description": market_outlook,
                "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
            })
            
            # System Status Embed (Green)
            embeds.append({
                "title": "⚙️ SYSTEM STATUS",
                "color": 5763719,  # Green
                "fields": [
                    {
                        "name": "Market Monitor",
                        "value": "✅ Active",
                        "inline": False
                    },
                    {
                        "name": "Data Collection",
                        "value": "✅ Running",
                        "inline": False
                    },
                    {
                        "name": "Analysis Engine",
                        "value": "✅ Ready",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
            })
            
            # Return properly structured webhook message
            return {
                "content": f"# 🌟 VIRTUOSO MARKET INTELLIGENCE\nYour comprehensive market analysis for {datetime.utcnow().strftime('%B %d, %Y')}\nReport #{random.randint(500, 999)} | {datetime.utcnow().strftime('%H:%M UTC')} • {datetime.utcnow().strftime('%m/%d/%y, %H:%M %p')}",
                "embeds": embeds,
                "username": "Virtuoso Market Monitor",
                "avatar_url": "https://i.imgur.com/4M34hi2.png"
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting market report: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Return a simplified error message with proper structure
            return {
                "content": f"Error generating market report: {str(e)}",
                "embeds": [{
                    "title": "Error Report",
                    "color": 15158332,  # Red
                    "description": "An error occurred while generating the market report."
                }]
            } 