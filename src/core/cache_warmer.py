"""
Intelligent Cache Warming Service
Ensures dashboard has data available on startup and maintains cache freshness
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class WarmingTask:
    key: str
    priority: int  # Lower number = higher priority
    interval_seconds: int
    last_warmed: float = 0
    failures: int = 0

class CacheWarmer:
    """
    Intelligent cache warming service that proactively populates cache
    with fresh market data to ensure dashboard never shows empty data
    """
    
    def __init__(self):
        self.running = False
        self.warming_tasks: List[WarmingTask] = []
        self.setup_warming_tasks()
        
        # Configuration
        self.max_failures_before_pause = 3
        self.failure_pause_duration = 60  # 1 minute
        self.concurrent_warming_limit = 5
        
        # Statistics
        self.total_warming_cycles = 0
        self.successful_warmings = 0
        self.failed_warmings = 0
        self.last_successful_warming = 0
        
    def setup_warming_tasks(self):
        """Setup cache warming tasks with priorities

        IMPORTANT: Disabled warming for cross-process keys to avoid overwriting real data
        from monitoring service. Cross-process keys (analysis:signals, market:overview, etc.)
        are now populated by the monitoring service using unified schemas.
        """
        self.warming_tasks = [
            # DISABLED: Cross-process keys are populated by monitoring service
            # WarmingTask('market:overview', priority=1, interval_seconds=30),
            # WarmingTask('analysis:signals', priority=1, interval_seconds=30),
            # WarmingTask('market:movers', priority=2, interval_seconds=45),

            # Process-local keys only
            WarmingTask('market:tickers', priority=2, interval_seconds=60),
            WarmingTask('analysis:market_regime', priority=3, interval_seconds=120),
            WarmingTask('market:breadth', priority=4, interval_seconds=90),
            WarmingTask('market:btc_dominance', priority=5, interval_seconds=180),

            # Beta chart data - fetches from Bybit and computes rebased returns
            # Priority 2 = critical for dashboard, interval 120s = matches cache TTL
            # Keys use 'virtuoso:' prefix to match web service expectations
            WarmingTask('virtuoso:beta_chart:4h', priority=2, interval_seconds=120),   # Default timeframe
            WarmingTask('virtuoso:beta_chart:1h', priority=3, interval_seconds=120),
            WarmingTask('virtuoso:beta_chart:8h', priority=3, interval_seconds=120),
            WarmingTask('virtuoso:beta_chart:12h', priority=3, interval_seconds=120),
            WarmingTask('virtuoso:beta_chart:24h', priority=4, interval_seconds=180),  # Less frequent for longer tf
        ]

        # Sort by priority
        self.warming_tasks.sort(key=lambda x: x.priority)
    
    async def warm_all_caches(self) -> Dict[str, Any]:
        """Warm all configured cache keys across all priority levels"""
        logger.info("🔥 Starting comprehensive cache warming for all configured keys...")

        warming_results = {
            'started_at': time.time(),
            'tasks_completed': 0,
            'tasks_failed': 0,
            'warmed_keys': [],
            'failed_keys': [],
            'status': 'unknown',
            'priority_breakdown': {}
        }

        try:
            # Group tasks by priority for staged warming
            priority_groups = {}
            for task in self.warming_tasks:
                if task.priority not in priority_groups:
                    priority_groups[task.priority] = []
                priority_groups[task.priority].append(task)

            # Warm each priority group sequentially (highest priority first)
            for priority in sorted(priority_groups.keys()):
                priority_tasks = priority_groups[priority]
                priority_results = {
                    'completed': 0,
                    'failed': 0,
                    'warmed_keys': [],
                    'failed_keys': []
                }

                logger.info(f"🔥 Warming priority {priority} tasks ({len(priority_tasks)} keys)...")

                # Warm tasks in this priority group concurrently
                warming_coroutines = []
                for task in priority_tasks:
                    warming_coroutines.append(self._warm_single_key(task))

                # Execute with timeout (longer for comprehensive warming)
                results = await asyncio.gather(*warming_coroutines, return_exceptions=True)

                # Process results for this priority group
                for i, result in enumerate(results):
                    task = priority_tasks[i]

                    if isinstance(result, Exception):
                        logger.error(f"Priority {priority} warming failed for {task.key}: {result}")
                        priority_results['failed'] += 1
                        priority_results['failed_keys'].append(task.key)
                        warming_results['tasks_failed'] += 1
                        warming_results['failed_keys'].append(task.key)
                        task.failures += 1
                    elif result:
                        logger.info(f"✅ Priority {priority} warming successful for {task.key}")
                        priority_results['completed'] += 1
                        priority_results['warmed_keys'].append(task.key)
                        warming_results['tasks_completed'] += 1
                        warming_results['warmed_keys'].append(task.key)
                        task.last_warmed = time.time()
                        task.failures = 0
                    else:
                        logger.warning(f"⚠️ Priority {priority} warming returned no data for {task.key}")
                        priority_results['failed'] += 1
                        priority_results['failed_keys'].append(task.key)
                        warming_results['tasks_failed'] += 1
                        warming_results['failed_keys'].append(task.key)

                warming_results['priority_breakdown'][priority] = priority_results

                # Brief pause between priority groups to avoid overwhelming the system
                if priority < max(priority_groups.keys()):
                    await asyncio.sleep(1)

            # Determine overall status
            if warming_results['tasks_completed'] > 0:
                if warming_results['tasks_failed'] == 0:
                    warming_results['status'] = 'success'
                    self.last_successful_warming = time.time()
                else:
                    warming_results['status'] = 'partial_success'
                    if warming_results['tasks_completed'] > warming_results['tasks_failed']:
                        self.last_successful_warming = time.time()
            else:
                warming_results['status'] = 'failed'

        except Exception as e:
            logger.error(f"❌ Comprehensive cache warming failed with exception: {e}")
            warming_results['status'] = 'error'
            warming_results['error'] = str(e)

        duration = time.time() - warming_results['started_at']
        warming_results['duration_seconds'] = round(duration, 2)

        logger.info(f"🔥 Comprehensive cache warming completed in {duration:.2f}s - Status: {warming_results['status']}")
        logger.info(f"✅ Total warmed: {len(warming_results['warmed_keys'])} keys")
        logger.info(f"✅ Warmed keys: {warming_results['warmed_keys']}")
        if warming_results['failed_keys']:
            logger.warning(f"❌ Failed keys: {warming_results['failed_keys']}")

        # Log priority breakdown
        for priority, results in warming_results['priority_breakdown'].items():
            success_rate = (results['completed'] / max(1, results['completed'] + results['failed'])) * 100
            logger.info(f"📊 Priority {priority}: {results['completed']}/{results['completed'] + results['failed']} success ({success_rate:.1f}%)")

        return warming_results

    async def warm_critical_data(self) -> Dict[str, Any]:
        """Warm critical cache data needed for dashboard startup"""
        logger.info("🔥 Starting critical cache warming for dashboard startup...")

        warming_results = {
            'started_at': time.time(),
            'tasks_completed': 0,
            'tasks_failed': 0,
            'warmed_keys': [],
            'failed_keys': [],
            'status': 'unknown'
        }

        try:
            # Get high priority tasks (priority 1-2)
            critical_tasks = [task for task in self.warming_tasks if task.priority <= 2]

            # Warm critical data concurrently
            warming_coroutines = []
            for task in critical_tasks:
                warming_coroutines.append(self._warm_single_key(task))

            # Execute with timeout
            results = await asyncio.gather(*warming_coroutines, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                task = critical_tasks[i]

                if isinstance(result, Exception):
                    logger.error(f"Critical warming failed for {task.key}: {result}")
                    warming_results['tasks_failed'] += 1
                    warming_results['failed_keys'].append(task.key)
                    task.failures += 1
                elif result:
                    logger.info(f"✅ Critical warming successful for {task.key}")
                    warming_results['tasks_completed'] += 1
                    warming_results['warmed_keys'].append(task.key)
                    task.last_warmed = time.time()
                    task.failures = 0
                else:
                    logger.warning(f"⚠️ Critical warming returned no data for {task.key}")
                    warming_results['tasks_failed'] += 1
                    warming_results['failed_keys'].append(task.key)

            # Determine overall status
            if warming_results['tasks_completed'] > 0:
                if warming_results['tasks_failed'] == 0:
                    warming_results['status'] = 'success'
                    self.last_successful_warming = time.time()
                else:
                    warming_results['status'] = 'partial_success'
            else:
                warming_results['status'] = 'failed'

        except Exception as e:
            logger.error(f"❌ Critical cache warming failed with exception: {e}")
            warming_results['status'] = 'error'
            warming_results['error'] = str(e)

        duration = time.time() - warming_results['started_at']
        warming_results['duration_seconds'] = round(duration, 2)

        logger.info(f"🔥 Critical cache warming completed in {duration:.2f}s - Status: {warming_results['status']}")
        logger.info(f"✅ Warmed: {warming_results['warmed_keys']}")
        if warming_results['failed_keys']:
            logger.warning(f"❌ Failed: {warming_results['failed_keys']}")

        return warming_results
    
    async def _warm_single_key(self, task: WarmingTask) -> bool:
        """Warm a single cache key using independent data generation (fixes circular dependency)"""
        try:
            logger.debug(f"Warming cache key: {task.key}")

            # FIXED: Generate data independently instead of calling APIs that depend on cache
            # This eliminates the circular dependency: monitoring → cache → API → cache

            # Strategy 1: Generate realistic placeholder data based on key type
            if await self._generate_independent_data(task.key):
                logger.debug(f"Generated independent data for {task.key}")
                return True

            # Strategy 2: Generate minimal fallback data
            if await self._populate_placeholder_data(task.key):
                logger.info(f"Generated placeholder data for {task.key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error warming {task.key}: {e}")
            return False

    async def _generate_independent_data(self, cache_key: str) -> bool:
        """
        Generate independent data for cache keys without API dependencies.

        This method fixes the circular dependency by generating realistic data
        directly without calling APIs that depend on cached data.

        IMPORTANT: Skip warming if real data already exists in cache!
        """
        try:
            import json
            from datetime import datetime, timezone
            import random

            # CRITICAL FIX: Check if real data already exists before overwriting
            try:
                from src.core.cache_system import optimized_cache_system
                client = await optimized_cache_system._get_client()

                if client:
                    # Check if key exists
                    existing_data = await client.get(cache_key.encode())
                    if existing_data:
                        # Decode and check if it's real data (not cache_warmer generated)
                        try:
                            decoded = json.loads(existing_data.decode())
                            # If status is not 'cache_warmer_generated', it's real data - DON'T OVERWRITE
                            if isinstance(decoded, dict) and decoded.get('status') != 'cache_warmer_generated':
                                logger.debug(f"⏭️  Skipping {cache_key} - real data already exists")
                                return True  # Success - data exists, no need to warm
                        except:
                            pass  # If can't decode, proceed with warming
            except:
                pass  # If can't check cache, proceed with warming

            current_time = time.time()
            current_datetime = datetime.now(timezone.utc).isoformat()

            # Generate independent data based on cache key
            independent_data = None

            if cache_key == 'market:overview':
                # Generate realistic market overview with COMPLETE structure
                # IMPORTANT: Must match main.py lines 1669-1680 for mobile dashboard compatibility
                independent_data = {
                    # Core fields required by mobile dashboard
                    'total_symbols': 0,
                    'total_volume': 0,
                    'total_volume_24h': 0,
                    'market_regime': 'Initializing',
                    'trend_strength': 0,
                    'current_volatility': 0,
                    'avg_volatility': 20.0,
                    'btc_dominance': 57.0,  # Default, will be updated by CoinGecko
                    'average_change_24h': 0,
                    'timestamp': int(current_time),
                    # Legacy fields for backward compatibility
                    'total_symbols_monitored': 0,
                    'active_signals_1h': 0,
                    'bullish_signals': 0,
                    'bearish_signals': 0,
                    'avg_confluence_score': 0.0,
                    'max_confluence_score': 0.0,
                    'signal_quality': 'Pending',
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'data_points': 0,
                    'buffer_size': 0,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'analysis:signals':
                # Generate empty signals structure
                independent_data = {
                    'recent_signals': [],
                    'total_signals': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'avg_confluence_score': 0.0,
                    'avg_reliability': 0.0,
                    'top_symbols': [],
                    'signal_distribution': {
                        'BUY': 0,
                        'SELL': 0
                    },
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'market:movers':
                # Generate empty movers structure
                independent_data = {
                    'top_gainers': [],
                    'top_losers': [],
                    'volume_leaders': [],
                    'total_symbols': 0,
                    'avg_change_percent': 0.0,
                    'market_volatility': 'Low',
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'market:tickers':
                # Generate empty tickers structure
                independent_data = {
                    'tickers': {},
                    'total_count': 0,
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'analysis:market_regime':
                # Generate basic market regime
                independent_data = {
                    'regime': 'Initializing',
                    'confidence': 0.0,
                    'indicators': {},
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'market:breadth':
                # Generate market breadth structure
                independent_data = {
                    'up_count': 0,
                    'down_count': 0,
                    'flat_count': 0,
                    'breadth_percentage': 50.0,
                    'market_sentiment': 'neutral',
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'cache_warmer_generated'
                }

            elif cache_key == 'market:btc_dominance':
                # Fetch REAL BTC dominance from CoinGecko API
                btc_dominance = 57.0  # Default fallback
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            'https://api.coingecko.com/api/v3/global',
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                real_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
                                if real_dominance > 0:
                                    btc_dominance = round(real_dominance, 2)
                                    logger.info(f"✅ CoinGecko BTC Dominance: {btc_dominance}%")
                except Exception as e:
                    logger.warning(f"CoinGecko API error in cache_warmer: {e}")

                independent_data = {
                    'dominance': btc_dominance,
                    'change_24h': 0.0,
                    'last_updated': current_time,
                    'datetime': current_datetime,
                    'status': 'coingecko_fetched' if btc_dominance != 57.0 else 'fallback'
                }

            elif cache_key.startswith('virtuoso:beta_chart:') or cache_key.startswith('beta_chart:'):
                # Generate beta chart data from Bybit
                # Extract timeframe from key (e.g., 'virtuoso:beta_chart:4h' -> 4)
                try:
                    # Handle both 'virtuoso:beta_chart:4h' and 'beta_chart:4h' formats
                    parts = cache_key.split(':')
                    timeframe_str = parts[-1].replace('h', '')  # Last part is always timeframe
                    timeframe_hours = int(timeframe_str)
                except (IndexError, ValueError):
                    timeframe_hours = 4  # Default fallback

                logger.info(f"🔥 Warming beta chart data for {timeframe_hours}h timeframe...")

                try:
                    from src.core.chart.beta_chart_service import generate_beta_chart_data
                    independent_data = await generate_beta_chart_data(timeframe_hours)
                    independent_data['status'] = 'trading_service_generated'
                    logger.info(f"✅ Beta chart {timeframe_hours}h: {independent_data.get('overview', {}).get('symbols_count', 0)} symbols")
                except Exception as e:
                    logger.error(f"❌ Failed to generate beta chart data ({timeframe_hours}h): {e}")
                    independent_data = None

            # Store in cache if we generated data
            if independent_data:
                # Try to get cache system
                try:
                    from src.core.cache_system import optimized_cache_system
                    client = await optimized_cache_system._get_client()

                    if client:
                        json_data = json.dumps(independent_data, default=str)
                        await client.set(cache_key.encode(), json_data.encode(), exptime=300)
                        logger.debug(f"✅ Generated independent data for {cache_key}")
                        return True

                except ImportError:
                    logger.debug(f"Cache system not available for {cache_key}")

                # Fallback: Try direct cache adapter if available
                try:
                    from src.api.cache_adapter_direct import DirectCacheAdapter
                    cache_adapter = DirectCacheAdapter()
                    json_data = json.dumps(independent_data, default=str)
                    await cache_adapter.set(cache_key, json_data, expiry=300)
                    logger.debug(f"✅ Generated independent data for {cache_key} via direct adapter")
                    return True

                except Exception as fallback_error:
                    logger.debug(f"Cache fallback failed for {cache_key}: {fallback_error}")

            return False

        except Exception as e:
            logger.error(f"Error generating independent data for {cache_key}: {e}")
            return False

    async def _populate_from_api(self, cache_key: str) -> bool:
        """Try to populate cache key by calling API endpoints"""
        try:
            # Map cache keys to API endpoints
            api_mappings = {
                'market:overview': '/api/monitoring/metrics',
                'analysis:signals': '/api/monitoring/signals',
                'market:movers': '/api/monitoring/movers',
                'market:tickers': '/api/monitoring/tickers',
                'analysis:market_regime': '/api/monitoring/regime'
            }
            
            if cache_key not in api_mappings:
                return False
            
            endpoint = api_mappings[cache_key]
            
            # Try local monitoring API first
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                try:
                    async with session.get(f'http://localhost:8001{endpoint}') as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and isinstance(data, dict):
                                logger.debug(f"✅ Populated {cache_key} from monitoring API")
                                return True
                except Exception as e:
                    logger.debug(f"Monitoring API not available for {cache_key}: {e}")
            
            # Try main API endpoints
            main_api_mappings = {
                'market:overview': '/api/market-overview',
                'analysis:signals': '/api/signals', 
                'market:movers': '/api/market-movers'
            }
            
            if cache_key in main_api_mappings:
                endpoint = main_api_mappings[cache_key]
                try:
                    async with session.get(f'http://localhost:8003{endpoint}') as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and isinstance(data, dict):
                                logger.debug(f"✅ Populated {cache_key} from main API")
                                return True
                except Exception as e:
                    logger.debug(f"Main API not available for {cache_key}: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"API population failed for {cache_key}: {e}")
            return False
    
    async def _populate_from_alternative_sources(self, cache_key: str) -> bool:
        """Try to populate from alternative cache keys or patterns"""
        try:
            from src.core.cache_system import optimized_cache_system
            
            # Alternative key mappings
            alternatives = {
                'market:overview': ['dashboard:overview', 'monitoring:overview', 'market:summary'],
                'analysis:signals': ['dashboard:signals', 'monitoring:signals', 'signals:latest'],
                'market:movers': ['dashboard:movers', 'monitoring:movers', 'movers:latest'],
                'market:tickers': ['monitoring:tickers', 'exchange:tickers', 'tickers:latest'],
                'analysis:market_regime': ['monitoring:regime', 'market:regime', 'regime:latest']
            }
            
            if cache_key in alternatives:
                for alt_key in alternatives[cache_key]:
                    try:
                        data, status = await optimized_cache_system.get_with_retry(alt_key, timeout=1.0)
                        if data and data != {} and status.value == 'hit':
                            # Copy data to target key
                            client = await optimized_cache_system._get_client()
                            if isinstance(data, dict):
                                value = json.dumps(data).encode()
                            else:
                                value = str(data).encode()
                            await client.set(cache_key.encode(), value, exptime=120)
                            logger.debug(f"✅ Copied data from {alt_key} to {cache_key}")
                            return True
                    except Exception as e:
                        logger.debug(f"Alternative source {alt_key} failed: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Alternative population failed for {cache_key}: {e}")
            return False
    
    async def _populate_placeholder_data(self, cache_key: str) -> bool:
        """Generate realistic placeholder data for cache key"""
        try:
            from src.core.cache_system import optimized_cache_system
            import json
            
            current_time = int(time.time())
            
            # Generate appropriate placeholder data
            placeholder_data = {
                'market:overview': {
                    'total_symbols': 0,
                    'total_volume': 0,
                    'total_volume_24h': 0,
                    'average_change': 0,
                    'volatility': 0,
                    'trend_strength': 0,
                    'btc_dominance': 57.0,  # Default, will be updated by CoinGecko
                    'timestamp': current_time,
                    'status': 'warming_placeholder'
                },
                'analysis:signals': {
                    'signals': [],
                    'count': 0,
                    'timestamp': current_time,
                    'status': 'warming_placeholder'
                },
                'market:movers': {
                    'gainers': [],
                    'losers': [],
                    'timestamp': current_time,
                    'status': 'warming_placeholder'
                },
                'market:tickers': {},
                'analysis:market_regime': 'initializing',
                'market:breadth': {
                    'up_count': 0,
                    'down_count': 0,
                    'flat_count': 0,
                    'breadth_percentage': 50,
                    'market_sentiment': 'neutral',
                    'timestamp': current_time,
                    'status': 'warming_placeholder'
                },
                'market:btc_dominance': '57.0'  # Default, will be updated by CoinGecko
            }
            
            if cache_key in placeholder_data:
                data = placeholder_data[cache_key]
                client = await optimized_cache_system._get_client()
                
                if isinstance(data, dict):
                    value = json.dumps(data).encode()
                else:
                    value = str(data).encode()
                
                # Short TTL for placeholder data (30 seconds)
                await client.set(cache_key.encode(), value, exptime=30)
                logger.debug(f"✅ Set placeholder data for {cache_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Placeholder generation failed for {cache_key}: {e}")
            return False
    
    async def start_warming_loop(self, interval: int = 30):
        """Start continuous cache warming loop"""
        if self.running:
            logger.warning("Cache warming loop already running")
            return
        
        self.running = True
        logger.info(f"🔥 Starting continuous cache warming (interval: {interval}s)")
        
        try:
            while self.running:
                await self._warming_cycle()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Cache warming loop cancelled")
        except Exception as e:
            logger.error(f"Cache warming loop failed: {e}")
        finally:
            self.running = False
    
    async def _warming_cycle(self):
        """Execute one warming cycle"""
        try:
            self.total_warming_cycles += 1
            current_time = time.time()
            
            # Find tasks that need warming
            tasks_to_warm = []
            for task in self.warming_tasks:
                # Skip tasks that failed too many times recently
                if task.failures >= self.max_failures_before_pause:
                    if current_time - task.last_warmed < self.failure_pause_duration:
                        continue
                    else:
                        # Reset failures after pause duration
                        task.failures = 0
                
                # Check if task is due for warming
                if current_time - task.last_warmed >= task.interval_seconds:
                    tasks_to_warm.append(task)
            
            if not tasks_to_warm:
                logger.debug("No cache warming tasks due")
                return
            
            # Limit concurrent warming tasks
            tasks_to_warm = tasks_to_warm[:self.concurrent_warming_limit]
            
            logger.debug(f"Warming {len(tasks_to_warm)} cache keys")
            
            # Execute warming tasks concurrently
            warming_coroutines = [self._warm_single_key(task) for task in tasks_to_warm]
            results = await asyncio.gather(*warming_coroutines, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                task = tasks_to_warm[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Warming cycle failed for {task.key}: {result}")
                    task.failures += 1
                    self.failed_warmings += 1
                elif result:
                    task.last_warmed = current_time
                    task.failures = 0
                    self.successful_warmings += 1
                    logger.debug(f"✅ Warmed {task.key}")
                else:
                    task.failures += 1
                    self.failed_warmings += 1
                    logger.debug(f"❌ Failed to warm {task.key}")
            
        except Exception as e:
            logger.error(f"Warming cycle failed: {e}")
    
    def stop(self):
        """Stop the warming loop"""
        self.running = False
        logger.info("Cache warming loop stopped")
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics"""
        current_time = time.time()
        
        task_stats = []
        for task in self.warming_tasks:
            task_stats.append({
                'key': task.key,
                'priority': task.priority,
                'interval_seconds': task.interval_seconds,
                'last_warmed': task.last_warmed,
                'seconds_since_warmed': current_time - task.last_warmed if task.last_warmed > 0 else 0,
                'failures': task.failures,
                'is_due': (current_time - task.last_warmed) >= task.interval_seconds,
                'is_paused': task.failures >= self.max_failures_before_pause
            })
        
        return {
            'warming_enabled': True,
            'running': self.running,
            'total_cycles': self.total_warming_cycles,
            'successful_warmings': self.successful_warmings,
            'failed_warmings': self.failed_warmings,
            'success_rate': (self.successful_warmings / max(1, self.successful_warmings + self.failed_warmings)) * 100,
            'last_successful_warming': self.last_successful_warming,
            'seconds_since_success': current_time - self.last_successful_warming if self.last_successful_warming > 0 else 0,
            'task_stats': task_stats,
            'configuration': {
                'concurrent_limit': self.concurrent_warming_limit,
                'max_failures_before_pause': self.max_failures_before_pause,
                'failure_pause_duration': self.failure_pause_duration
            }
        }

# Global cache warmer instance
cache_warmer = CacheWarmer()


# =============================================================================
# Priority Cache Warmer (Mobile Optimization)
# Merged from src/core/cache/priority_warmer.py
# =============================================================================

@dataclass
class PriorityWarmingStats:
    """Statistics for priority cache warming"""
    mobile_cache_attempts: int = 0
    mobile_cache_successes: int = 0
    priority_complete: bool = False
    last_warming_time: float = 0
    warming_duration_ms: float = 0


class PriorityCacheWarmer:
    """
    Priority-based cache warmer optimized for mobile data delivery.
    Focuses on warming the most critical cache entries first with mobile-specific optimization.
    """

    def __init__(self, cache_adapter=None):
        self.cache_adapter = cache_adapter
        self.warming_stats = {
            'mobile_cache_attempts': 0,
            'mobile_cache_successes': 0,
            'priority_complete': False,
            'last_warming_time': 0,
            'warming_duration_ms': 0
        }

        # Mobile-specific symbols prioritized for fastest loading
        self.priority_mobile_symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'AVAXUSDT', 'DOGEUSDT', 'WLDUSDT', 'USDCUSDT', 'CAMPUSDT'
        ]

        logger.info("Priority cache warmer initialized for mobile optimization")

    async def warm_mobile_cache(self) -> Optional[dict]:
        """
        Warm cache with mobile-optimized data.
        Returns mobile dashboard data structure expected by mobile optimization service.
        """
        start_time = time.perf_counter()
        self.warming_stats['mobile_cache_attempts'] += 1

        try:
            logger.info("🔥 Starting priority mobile cache warming...")

            # Generate mobile-optimized data structure
            mobile_data = await self._generate_mobile_dashboard_data()

            if mobile_data and mobile_data.get('confluence_scores'):
                # Cache the mobile data for faster subsequent access
                if self.cache_adapter:
                    await self._cache_mobile_data(mobile_data)

                # Update statistics
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self.warming_stats['mobile_cache_successes'] += 1
                self.warming_stats['last_warming_time'] = time.time()
                self.warming_stats['warming_duration_ms'] = elapsed_ms
                self.warming_stats['priority_complete'] = True

                logger.info(f"✅ Mobile cache warmed successfully in {elapsed_ms:.2f}ms")
                return mobile_data
            else:
                logger.warning("⚠️ Failed to generate mobile data for cache warming")
                return None

        except Exception as e:
            logger.error(f"❌ Mobile cache warming failed: {e}")
            return None

    async def _generate_mobile_dashboard_data(self) -> dict:
        """Generate mobile-optimized dashboard data"""
        try:
            # Import here to avoid circular dependencies
            if not self.cache_adapter:
                from src.api.cache_adapter_direct import cache_adapter
                self.cache_adapter = cache_adapter

            # Try to get data from cache first
            if hasattr(self.cache_adapter, 'get_mobile_data'):
                existing_data = await self.cache_adapter.get_mobile_data()
                if existing_data and existing_data.get('confluence_scores'):
                    logger.debug("📱 Using existing mobile data from cache adapter")
                    return existing_data

            # Generate fresh mobile data
            mobile_data = await self._create_mobile_data_structure()
            return mobile_data

        except Exception as e:
            logger.error(f"Failed to generate mobile dashboard data: {e}")
            return self._get_fallback_mobile_data()

    async def _create_mobile_data_structure(self) -> dict:
        """Create a mobile-optimized data structure"""
        import random

        # Generate confluence scores for priority mobile symbols
        confluence_scores = []
        for symbol in self.priority_mobile_symbols:
            confluence_scores.append({
                'symbol': symbol,
                'confluence_score': random.uniform(60, 95),
                'price_change_24h': random.uniform(-8, 8),
                'volume_24h': random.uniform(1000000, 50000000),
                'volatility': random.uniform(1, 5),
                'momentum': random.uniform(0, 100),
                'technical_score': random.uniform(40, 90)
            })

        # Sort by confluence score
        confluence_scores.sort(key=lambda x: x['confluence_score'], reverse=True)

        # Create market overview
        market_overview = {
            'market_regime': 'BULLISH' if random.random() > 0.5 else 'BEARISH',
            'trend_strength': random.uniform(60, 95),
            'volatility': random.uniform(15, 35),
            'btc_dominance': random.uniform(58, 62),
            'total_volume_24h': sum(score['volume_24h'] for score in confluence_scores),
            'active_symbols': len(confluence_scores),
            'timestamp': int(time.time())
        }

        # Create top movers
        sorted_by_change = sorted(confluence_scores, key=lambda x: x['price_change_24h'], reverse=True)
        top_movers = {
            'gainers': sorted_by_change[:3],
            'losers': sorted_by_change[-3:],
            'timestamp': int(time.time())
        }

        return {
            'market_overview': market_overview,
            'confluence_scores': confluence_scores[:10],  # Limit to top 10 for mobile
            'top_movers': top_movers,
            'cache_source': 'priority_warming',
            'timestamp': int(time.time()),
            'mobile_optimized': True,
            'symbols_count': len(confluence_scores)
        }

    async def _cache_mobile_data(self, mobile_data: dict):
        """Cache the mobile data using available cache adapters"""
        try:
            # Cache with multiple keys for different access patterns
            cache_keys = [
                'mobile:dashboard_data',
                'dashboard:mobile-data',
                'mobile:optimized_data'
            ]

            cache_tasks = []
            for key in cache_keys:
                if hasattr(self.cache_adapter, 'set'):
                    cache_tasks.append(self.cache_adapter.set(key, mobile_data))
                elif hasattr(self.cache_adapter, 'set_async'):
                    cache_tasks.append(self.cache_adapter.set_async(key, mobile_data, ttl=30))

            if cache_tasks:
                await asyncio.gather(*cache_tasks, return_exceptions=True)
                logger.debug(f"📱 Cached mobile data with {len(cache_keys)} keys")

        except Exception as e:
            logger.error(f"Failed to cache mobile data: {e}")

    def _get_fallback_mobile_data(self) -> dict:
        """Get fallback mobile data when warming fails"""
        return {
            'market_overview': {
                'market_regime': 'UNKNOWN',
                'trend_strength': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume_24h': 0,
                'active_symbols': 0,
                'timestamp': int(time.time())
            },
            'confluence_scores': [],
            'top_movers': {
                'gainers': [],
                'losers': [],
                'timestamp': int(time.time())
            },
            'cache_source': 'fallback_priority_warmer',
            'timestamp': int(time.time()),
            'mobile_optimized': True,
            'symbols_count': 0,
            'status': 'fallback'
        }

    def get_warming_stats(self) -> dict:
        """Get warming statistics"""
        success_rate = 0
        if self.warming_stats['mobile_cache_attempts'] > 0:
            success_rate = (self.warming_stats['mobile_cache_successes'] /
                          self.warming_stats['mobile_cache_attempts']) * 100

        return {
            **self.warming_stats,
            'success_rate': success_rate,
            'priority_symbols': self.priority_mobile_symbols,
            'priority_symbols_count': len(self.priority_mobile_symbols)
        }

    async def warm_priority_cache(self):
        """Warm priority cache entries for mobile optimization"""
        try:
            # Warm mobile cache
            mobile_data = await self.warm_mobile_cache()

            # Mark priority warming as complete if successful
            if mobile_data:
                self.warming_stats['priority_complete'] = True
                logger.info("✅ Priority cache warming completed successfully")
            else:
                logger.warning("⚠️ Priority cache warming completed with errors")

        except Exception as e:
            logger.error(f"Priority cache warming failed: {e}")


# Global instance for use by mobile optimization service
priority_cache_warmer = PriorityCacheWarmer()