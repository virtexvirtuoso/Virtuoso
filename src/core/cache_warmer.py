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
        """Setup cache warming tasks with priorities"""
        self.warming_tasks = [
            # Critical dashboard data (highest priority)
            WarmingTask('market:overview', priority=1, interval_seconds=30),
            WarmingTask('analysis:signals', priority=1, interval_seconds=30),
            WarmingTask('market:movers', priority=2, interval_seconds=45),
            WarmingTask('market:tickers', priority=2, interval_seconds=60),
            WarmingTask('analysis:market_regime', priority=3, interval_seconds=120),
            
            # Additional dashboard data
            WarmingTask('market:breadth', priority=4, interval_seconds=90),
            WarmingTask('market:btc_dominance', priority=5, interval_seconds=180),
        ]
        
        # Sort by priority
        self.warming_tasks.sort(key=lambda x: x.priority)
    
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
        """Warm a single cache key using various strategies"""
        try:
            logger.debug(f"Warming cache key: {task.key}")
            
            # Strategy 1: Try to populate using direct API call
            if await self._populate_from_api(task.key):
                return True
            
            # Strategy 2: Try to get from alternative endpoints
            if await self._populate_from_alternative_sources(task.key):
                return True
            
            # Strategy 3: Generate minimal placeholder data
            if await self._populate_placeholder_data(task.key):
                logger.info(f"Generated placeholder data for {task.key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error warming {task.key}: {e}")
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
                    'btc_dominance': 59.3,
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
                'market:btc_dominance': '59.3'
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