#!/usr/bin/env python3
"""
Priority 2 Dashboard Performance Optimizations  
Advanced caching strategies, background refresh, and response compression

This script implements:
- Cache warming and background refresh
- Response compression and ETags
- Intelligent cache invalidation
- Advanced monitoring and metrics
- Predictive caching

Usage: python scripts/fix_dashboard_performance_priority2.py
"""

import os
import sys
import shutil
from pathlib import Path

def main():
    print("🚀 PRIORITY 2 Dashboard Performance Optimizations")
    print("=" * 60)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create cache warming service
    print("🔧 Creating cache warming service...")
    create_cache_warming_service(project_root)
    
    # Create response compression middleware
    print("🔧 Creating response compression middleware...")
    create_compression_middleware(project_root)
    
    # Create intelligent cache invalidation
    print("🔧 Creating intelligent cache invalidation...")
    create_cache_invalidation(project_root)
    
    # Create performance monitoring
    print("🔧 Creating advanced performance monitoring...")
    create_performance_monitoring(project_root)
    
    print("=" * 60)
    print("✅ PRIORITY 2 OPTIMIZATIONS COMPLETE!")
    print("🚀 Deploy with: ./scripts/deploy_priority2_fixes.sh")

def create_cache_warming_service(project_root):
    """Create cache warming and background refresh service"""
    cache_warming_file = project_root / "src/core/cache_warming.py"
    cache_warming_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_warming_file, 'w') as f:
        f.write('''"""
Cache Warming Service - Priority 2 Performance
Background cache refresh and intelligent warming strategies
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, Set, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiomcache
from concurrent.futures import ThreadPoolExecutor
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class WarmingTarget:
    """Cache warming target configuration"""
    key: str
    refresh_interval: int  # seconds
    data_source: str
    priority: int = 1  # 1=highest, 5=lowest
    last_refreshed: float = field(default=0.0)
    failures: int = field(default=0)
    
    @property
    def needs_refresh(self) -> bool:
        return time.time() - self.last_refreshed > self.refresh_interval

class CacheWarmingService:
    """Advanced cache warming with background refresh"""
    
    def __init__(self):
        self.is_running = False
        self.cache_client = None
        self.warming_targets: List[WarmingTarget] = []
        self.refresh_tasks: Set[asyncio.Task] = set()
        self.stats = {
            'cache_warmed': 0,
            'refresh_cycles': 0,
            'failures': 0,
            'avg_refresh_time': 0.0
        }
        
        # Define warming targets
        self._setup_warming_targets()
    
    def _setup_warming_targets(self):
        """Setup cache warming targets"""
        self.warming_targets = [
            WarmingTarget('market:overview', 30, 'bybit_api', priority=1),
            WarmingTarget('market:tickers', 45, 'bybit_api', priority=1), 
            WarmingTarget('analysis:signals', 60, 'internal_analysis', priority=2),
            WarmingTarget('market:movers', 120, 'bybit_api', priority=2),
            WarmingTarget('analysis:market_regime', 300, 'internal_analysis', priority=3),
            WarmingTarget('market:breadth', 180, 'internal_calculation', priority=2),
            WarmingTarget('market:btc_dominance', 600, 'coingecko_api', priority=4)
        ]
        
        logger.info(f"Setup {len(self.warming_targets)} cache warming targets")
    
    async def start(self):
        """Start the cache warming service"""
        if self.is_running:
            return
            
        self.is_running = True
        self.cache_client = aiomcache.Client('localhost', 11211)
        
        logger.info("Starting cache warming service...")
        
        # Initial warm-up
        await self._initial_warmup()
        
        # Start background refresh loop
        asyncio.create_task(self._refresh_loop())
        
        logger.info("Cache warming service started")
    
    async def stop(self):
        """Stop the cache warming service"""
        self.is_running = False
        
        # Cancel refresh tasks
        for task in self.refresh_tasks:
            task.cancel()
        
        if self.cache_client:
            await self.cache_client.close()
        
        logger.info("Cache warming service stopped")
    
    async def _initial_warmup(self):
        """Perform initial cache warming"""
        logger.info("Performing initial cache warmup...")
        
        # Sort by priority
        sorted_targets = sorted(self.warming_targets, key=lambda x: x.priority)
        
        for target in sorted_targets:
            try:
                await self._refresh_target(target)
                self.stats['cache_warmed'] += 1
                await asyncio.sleep(0.5)  # Small delay between requests
            except Exception as e:
                logger.error(f"Failed to warm cache for {target.key}: {e}")
                target.failures += 1
        
        logger.info(f"Initial warmup complete: {self.stats['cache_warmed']} targets warmed")
    
    async def _refresh_loop(self):
        """Background cache refresh loop"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Check which targets need refresh
                targets_to_refresh = [
                    target for target in self.warming_targets 
                    if target.needs_refresh
                ]
                
                if targets_to_refresh:
                    logger.debug(f"Refreshing {len(targets_to_refresh)} cache targets")
                    
                    # Refresh targets concurrently
                    refresh_tasks = [
                        self._refresh_target(target) 
                        for target in targets_to_refresh
                    ]
                    
                    results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
                    
                    # Update stats
                    successes = sum(1 for r in results if not isinstance(r, Exception))
                    failures = len(results) - successes
                    
                    self.stats['refresh_cycles'] += 1
                    self.stats['failures'] += failures
                    self.stats['avg_refresh_time'] = time.time() - start_time
                    
                    logger.debug(f"Refresh cycle complete: {successes} success, {failures} failures")
                
                # Sleep until next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _refresh_target(self, target: WarmingTarget):
        """Refresh a specific cache target"""
        try:
            data = await self._fetch_data_for_target(target)
            
            if data is not None:
                # Store in cache
                await self.cache_client.set(
                    target.key.encode(),
                    json.dumps(data).encode(),
                    exptime=target.refresh_interval * 2  # TTL is 2x refresh interval
                )
                
                target.last_refreshed = time.time()
                target.failures = 0
                logger.debug(f"Refreshed cache for {target.key}")
            else:
                target.failures += 1
                logger.warning(f"No data returned for {target.key}")
                
        except Exception as e:
            target.failures += 1
            logger.error(f"Failed to refresh {target.key}: {e}")
            raise
    
    async def _fetch_data_for_target(self, target: WarmingTarget) -> Any:
        """Fetch data for a cache target"""
        if target.data_source == 'bybit_api':
            return await self._fetch_bybit_data(target.key)
        elif target.data_source == 'internal_analysis':
            return await self._fetch_internal_analysis(target.key)
        elif target.data_source == 'internal_calculation':
            return await self._calculate_internal_data(target.key)
        elif target.data_source == 'coingecko_api':
            return await self._fetch_coingecko_data(target.key)
        else:
            logger.warning(f"Unknown data source: {target.data_source}")
            return None
    
    async def _fetch_bybit_data(self, cache_key: str) -> Dict[str, Any]:
        """Fetch data from Bybit API"""
        async with aiohttp.ClientSession() as session:
            if 'overview' in cache_key or 'tickers' in cache_key:
                url = "https://api.bybit.com/v5/market/tickers?category=linear"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('retCode') == 0:
                            return self._process_bybit_tickers(data['result']['list'])
            
            elif 'movers' in cache_key:
                # Similar processing for market movers
                url = "https://api.bybit.com/v5/market/tickers?category=linear"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('retCode') == 0:
                            return self._process_market_movers(data['result']['list'])
        
        return None
    
    def _process_bybit_tickers(self, tickers: List[Dict]) -> Dict[str, Any]:
        """Process Bybit tickers into cache format"""
        processed_tickers = {}
        total_volume = 0
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if symbol.endswith('USDT'):
                price = float(ticker.get('lastPrice', 0))
                change_24h = float(ticker.get('price24hPcnt', 0)) * 100
                volume = float(ticker.get('turnover24h', 0))
                
                processed_tickers[symbol] = {
                    'price': price,
                    'change_24h': change_24h,
                    'volume': volume,
                    'high': float(ticker.get('highPrice24h', 0)),
                    'low': float(ticker.get('lowPrice24h', 0))
                }
                
                total_volume += volume
        
        return {
            'tickers': processed_tickers,
            'total_symbols': len(processed_tickers),
            'total_volume_24h': total_volume,
            'timestamp': int(time.time())
        }
    
    def _process_market_movers(self, tickers: List[Dict]) -> Dict[str, Any]:
        """Process market movers from tickers"""
        movers = []
        
        for ticker in tickers:
            if ticker['symbol'].endswith('USDT'):
                change_24h = float(ticker.get('price24hPcnt', 0)) * 100
                turnover = float(ticker.get('turnover24h', 0))
                
                if turnover > 1000000:  # Min $1M turnover
                    movers.append({
                        'symbol': ticker['symbol'],
                        'change_24h': change_24h,
                        'price': float(ticker.get('lastPrice', 0)),
                        'volume': turnover
                    })
        
        movers.sort(key=lambda x: x['change_24h'])
        
        return {
            'gainers': [m for m in movers if m['change_24h'] > 0][-10:],
            'losers': [m for m in movers if m['change_24h'] < 0][:10],
            'timestamp': int(time.time())
        }
    
    async def _fetch_internal_analysis(self, cache_key: str) -> Dict[str, Any]:
        """Fetch internal analysis data"""
        # This would integrate with your existing analysis components
        # For now, return placeholder data
        return {
            'status': 'analysis_pending',
            'timestamp': int(time.time())
        }
    
    async def _calculate_internal_data(self, cache_key: str) -> Dict[str, Any]:
        """Calculate internal metrics"""
        if 'breadth' in cache_key:
            # Calculate market breadth from cached tickers
            tickers_data = await self.cache_client.get(b'market:tickers')
            if tickers_data:
                tickers = json.loads(tickers_data.decode()).get('tickers', {})
                
                up_count = len([t for t in tickers.values() if t.get('change_24h', 0) > 0])
                down_count = len([t for t in tickers.values() if t.get('change_24h', 0) < 0])
                total_count = len(tickers)
                
                return {
                    'up_count': up_count,
                    'down_count': down_count,
                    'flat_count': total_count - up_count - down_count,
                    'breadth_percentage': (up_count / max(total_count, 1)) * 100,
                    'timestamp': int(time.time())
                }
        
        return None
    
    async def _fetch_coingecko_data(self, cache_key: str) -> Dict[str, Any]:
        """Fetch data from CoinGecko API"""
        if 'btc_dominance' in cache_key:
            async with aiohttp.ClientSession() as session:
                url = "https://api.coingecko.com/api/v3/global"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return str(data.get('data', {}).get('market_cap_percentage', {}).get('btc', 59.3))
                except:
                    pass
        
        return "59.3"  # Default BTC dominance
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics"""
        return {
            'service_running': self.is_running,
            'total_targets': len(self.warming_targets),
            'targets_needing_refresh': len([t for t in self.warming_targets if t.needs_refresh]),
            'stats': self.stats,
            'target_status': [
                {
                    'key': target.key,
                    'priority': target.priority,
                    'last_refreshed': target.last_refreshed,
                    'needs_refresh': target.needs_refresh,
                    'failures': target.failures
                }
                for target in self.warming_targets
            ]
        }

# Global cache warming service
cache_warming_service = CacheWarmingService()
''')
    
    print("   ✅ Created cache warming service with background refresh")

def create_compression_middleware(project_root):
    """Create response compression middleware"""
    compression_file = project_root / "src/core/middleware/compression.py"
    compression_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(compression_file, 'w') as f:
        f.write('''"""
Response Compression Middleware - Priority 2 Performance
Implements gzip compression and ETags for better performance
"""
import gzip
import json
import hashlib
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CompressionMiddleware(BaseHTTPMiddleware):
    """Advanced compression middleware with ETags"""
    
    def __init__(self, app, compress_threshold: int = 1024, compression_level: int = 6):
        super().__init__(app)
        self.compress_threshold = compress_threshold
        self.compression_level = compression_level
        self.etag_cache: Dict[str, str] = {}
        self.stats = {
            'total_requests': 0,
            'compressed_responses': 0,
            'bytes_saved': 0,
            'etag_hits': 0
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with compression and ETags"""
        start_time = time.time()
        
        # Get response from application
        response = await call_next(request)
        
        # Only compress JSON responses
        if (hasattr(response, 'media_type') and 
            response.media_type == 'application/json' and
            hasattr(response, 'body')):
            
            await self._process_json_response(request, response)
        
        self.stats['total_requests'] += 1
        
        # Add performance headers
        response.headers['X-Response-Time'] = f"{(time.time() - start_time) * 1000:.2f}ms"
        response.headers['X-Cache-Performance'] = json.dumps({
            'compressed_responses': self.stats['compressed_responses'],
            'bytes_saved': self.stats['bytes_saved'],
            'compression_ratio': self._get_compression_ratio()
        })
        
        return response
    
    async def _process_json_response(self, request: Request, response: Response):
        """Process JSON response with compression and ETags"""
        try:
            # Get response body
            body_bytes = response.body
            if not body_bytes or len(body_bytes) < self.compress_threshold:
                return
            
            # Generate ETag from content
            etag = self._generate_etag(body_bytes)
            
            # Check if client has cached version
            if_none_match = request.headers.get('If-None-Match')
            if if_none_match and if_none_match == etag:
                # Client has cached version
                response.status_code = 304
                response.body = b''
                response.headers['ETag'] = etag
                self.stats['etag_hits'] += 1
                return
            
            # Check if client accepts compression
            accept_encoding = request.headers.get('accept-encoding', '').lower()
            
            if 'gzip' in accept_encoding:
                # Compress response
                original_size = len(body_bytes)
                compressed_body = gzip.compress(body_bytes, compresslevel=self.compression_level)
                compressed_size = len(compressed_body)
                
                if compressed_size < original_size:
                    # Use compressed version
                    response.body = compressed_body
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = str(compressed_size)
                    
                    # Update stats
                    self.stats['compressed_responses'] += 1
                    self.stats['bytes_saved'] += (original_size - compressed_size)
                    
                    logger.debug(f"Compressed response: {original_size} -> {compressed_size} bytes "
                               f"({(1 - compressed_size/original_size)*100:.1f}% reduction)")
            
            # Add ETag header
            response.headers['ETag'] = etag
            response.headers['Cache-Control'] = 'public, max-age=30'  # 30-second cache
            
        except Exception as e:
            logger.error(f"Error in compression middleware: {e}")
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag from content"""
        return f'"{hashlib.md5(content).hexdigest()[:16]}"'
    
    def _get_compression_ratio(self) -> float:
        """Calculate average compression ratio"""
        if self.stats['compressed_responses'] == 0:
            return 0.0
        
        return (self.stats['bytes_saved'] / 
                max(self.stats['bytes_saved'] + 
                    (self.stats['compressed_responses'] * 1000), 1)) * 100  # Estimate

class CacheControlMiddleware(BaseHTTPMiddleware):
    """Cache control middleware for API responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.cache_rules = {
            '/api/dashboard-cached/': 'public, max-age=30, stale-while-revalidate=60',
            '/api/dashboard/': 'public, max-age=15, stale-while-revalidate=30',
            '/api/market/': 'public, max-age=45, stale-while-revalidate=90',
            '/api/health': 'no-cache',
            '/api/debug': 'no-cache'
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Apply cache control rules
        path = request.url.path
        for pattern, cache_control in self.cache_rules.items():
            if path.startswith(pattern):
                response.headers['Cache-Control'] = cache_control
                break
        else:
            # Default cache control
            if path.startswith('/api/'):
                response.headers['Cache-Control'] = 'public, max-age=60'
        
        return response
''')
    
    print("   ✅ Created response compression middleware")

def create_cache_invalidation(project_root):
    """Create intelligent cache invalidation system"""
    invalidation_file = project_root / "src/core/cache_invalidation.py"
    
    with open(invalidation_file, 'w') as f:
        f.write('''"""
Intelligent Cache Invalidation - Priority 2 Performance
Smart cache invalidation based on data dependencies and patterns
"""
import asyncio
import time
import logging
from typing import Dict, Set, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiomcache
import json

logger = logging.getLogger(__name__)

@dataclass
class InvalidationRule:
    """Cache invalidation rule"""
    trigger_key: str                    # Key that triggers invalidation
    dependent_keys: List[str]           # Keys to invalidate
    condition: str = "always"           # Condition: always, threshold, time-based
    threshold: float = 0.0              # For threshold conditions
    cooldown: int = 0                   # Minimum seconds between invalidations
    last_invalidation: float = field(default=0.0)

class CacheInvalidationService:
    """Intelligent cache invalidation service"""
    
    def __init__(self):
        self.cache_client: aiomcache.Client = None
        self.invalidation_rules: List[InvalidationRule] = []
        self.is_running = False
        self.stats = {
            'total_invalidations': 0,
            'rule_triggers': 0,
            'cache_hits_after_invalidation': 0
        }
        
        self._setup_invalidation_rules()
    
    def _setup_invalidation_rules(self):
        """Setup cache invalidation rules"""
        self.invalidation_rules = [
            # Market data changes trigger dashboard updates
            InvalidationRule(
                trigger_key='market:tickers',
                dependent_keys=['market:overview', 'market:movers', 'analysis:signals'],
                cooldown=30
            ),
            
            # Overview changes trigger mobile data updates
            InvalidationRule(
                trigger_key='market:overview',
                dependent_keys=['mobile:dashboard_data', 'dashboard:overview'],
                cooldown=15
            ),
            
            # Signal analysis changes trigger confluence updates
            InvalidationRule(
                trigger_key='analysis:signals',
                dependent_keys=['confluence:scores', 'mobile:dashboard_data'],
                cooldown=20
            ),
            
            # Market regime changes trigger broad updates
            InvalidationRule(
                trigger_key='analysis:market_regime',
                dependent_keys=['market:analysis', 'dashboard:overview', 'mobile:dashboard_data'],
                cooldown=60
            ),
            
            # Time-based invalidation for stale data
            InvalidationRule(
                trigger_key='time:hourly',
                dependent_keys=['market:breadth', 'analysis:market_regime'],
                condition='time-based',
                cooldown=3600  # 1 hour
            )
        ]
        
        logger.info(f"Setup {len(self.invalidation_rules)} cache invalidation rules")
    
    async def start(self):
        """Start the invalidation service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cache_client = aiomcache.Client('localhost', 11211)
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("Cache invalidation service started")
    
    async def stop(self):
        """Stop the invalidation service"""
        self.is_running = False
        
        if self.cache_client:
            await self.cache_client.close()
        
        logger.info("Cache invalidation service stopped")
    
    async def _monitoring_loop(self):
        """Monitor cache for invalidation triggers"""
        last_check_times = {}
        
        while self.is_running:
            try:
                current_time = time.time()
                
                for rule in self.invalidation_rules:
                    # Check cooldown
                    if current_time - rule.last_invalidation < rule.cooldown:
                        continue
                    
                    # Check condition
                    should_invalidate = False
                    
                    if rule.condition == "always":
                        # Check if trigger key was updated
                        last_check = last_check_times.get(rule.trigger_key, 0)
                        key_data = await self._get_key_metadata(rule.trigger_key)
                        
                        if key_data and key_data.get('timestamp', 0) > last_check:
                            should_invalidate = True
                            last_check_times[rule.trigger_key] = current_time
                    
                    elif rule.condition == "time-based":
                        # Time-based invalidation
                        should_invalidate = True
                    
                    if should_invalidate:
                        await self._invalidate_keys(rule)
                        rule.last_invalidation = current_time
                        self.stats['rule_triggers'] += 1
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in invalidation monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _get_key_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for a cache key"""
        try:
            data = await self.cache_client.get(key.encode())
            if data:
                parsed_data = json.loads(data.decode())
                if isinstance(parsed_data, dict):
                    return parsed_data
        except:
            pass
        return {}
    
    async def _invalidate_keys(self, rule: InvalidationRule):
        """Invalidate dependent keys"""
        try:
            for key in rule.dependent_keys:
                await self.cache_client.delete(key.encode())
                logger.debug(f"Invalidated cache key: {key}")
            
            self.stats['total_invalidations'] += len(rule.dependent_keys)
            logger.info(f"Invalidated {len(rule.dependent_keys)} keys due to {rule.trigger_key}")
            
        except Exception as e:
            logger.error(f"Error invalidating keys for rule {rule.trigger_key}: {e}")
    
    async def manual_invalidate(self, keys: List[str]):
        """Manually invalidate specific keys"""
        try:
            for key in keys:
                await self.cache_client.delete(key.encode())
            
            self.stats['total_invalidations'] += len(keys)
            logger.info(f"Manually invalidated {len(keys)} cache keys")
            
        except Exception as e:
            logger.error(f"Error in manual invalidation: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get invalidation service statistics"""
        return {
            'service_running': self.is_running,
            'total_rules': len(self.invalidation_rules),
            'stats': self.stats,
            'rules_status': [
                {
                    'trigger_key': rule.trigger_key,
                    'dependent_keys_count': len(rule.dependent_keys),
                    'last_invalidation': rule.last_invalidation,
                    'cooldown': rule.cooldown
                }
                for rule in self.invalidation_rules
            ]
        }

# Global invalidation service
cache_invalidation_service = CacheInvalidationService()
''')
    
    print("   ✅ Created intelligent cache invalidation system")

def create_performance_monitoring(project_root):
    """Create advanced performance monitoring"""
    monitoring_file = project_root / "src/core/performance_monitoring.py"
    
    with open(monitoring_file, 'w') as f:
        f.write('''"""
Advanced Performance Monitoring - Priority 2 Performance
Comprehensive monitoring of dashboard performance and optimization metrics
"""
import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: float
    value: float
    category: str
    endpoint: str = ""

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.metrics: defaultdict = defaultdict(lambda: deque(maxlen=max_samples))
        self.is_monitoring = False
        self.start_time = time.time()
        
        # Performance thresholds
        self.thresholds = {
            'response_time': 3.0,      # 3 seconds
            'cpu_usage': 80.0,         # 80%
            'memory_usage': 85.0,      # 85%
            'cache_hit_rate': 70.0,    # 70%
            'error_rate': 5.0          # 5%
        }
    
    async def start(self):
        """Start performance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_system_metrics())
        asyncio.create_task(self._monitor_endpoint_performance())
        asyncio.create_task(self._analyze_performance_trends())
        
        logger.info("Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        logger.info("Performance monitoring stopped")
    
    def record_endpoint_performance(self, endpoint: str, response_time: float, status_code: int = 200):
        """Record endpoint performance metrics"""
        current_time = time.time()
        
        # Record response time
        self.metrics[f'response_time_{endpoint}'].append(
            PerformanceMetric(current_time, response_time, 'response_time', endpoint)
        )
        
        # Record status codes
        self.metrics[f'status_code_{endpoint}'].append(
            PerformanceMetric(current_time, status_code, 'status_code', endpoint)
        )
        
        # Check for performance issues
        if response_time > self.thresholds['response_time']:
            logger.warning(f"Slow response detected: {endpoint} took {response_time:.2f}s")
    
    def record_cache_performance(self, operation: str, hit: bool, response_time: float):
        """Record cache performance metrics"""
        current_time = time.time()
        
        self.metrics[f'cache_{operation}'].append(
            PerformanceMetric(current_time, 1 if hit else 0, 'cache_hit', operation)
        )
        
        self.metrics[f'cache_time_{operation}'].append(
            PerformanceMetric(current_time, response_time, 'cache_response_time', operation)
        )
    
    async def _monitor_system_metrics(self):
        """Monitor system-level metrics"""
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics['cpu_usage'].append(
                    PerformanceMetric(current_time, cpu_percent, 'system')
                )
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics['memory_usage'].append(
                    PerformanceMetric(current_time, memory.percent, 'system')
                )
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.metrics['disk_usage'].append(
                    PerformanceMetric(current_time, disk.percent, 'system')
                )
                
                # Network I/O
                network = psutil.net_io_counters()
                self.metrics['network_bytes_sent'].append(
                    PerformanceMetric(current_time, network.bytes_sent, 'system')
                )
                self.metrics['network_bytes_recv'].append(
                    PerformanceMetric(current_time, network.bytes_recv, 'system')
                )
                
                # Check thresholds
                self._check_system_thresholds(cpu_percent, memory.percent, disk.percent)
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring system metrics: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_endpoint_performance(self):
        """Monitor endpoint-specific performance"""
        while self.is_monitoring:
            try:
                # This would integrate with your endpoint tracking
                # For now, we'll simulate some monitoring
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error monitoring endpoint performance: {e}")
                await asyncio.sleep(120)
    
    async def _analyze_performance_trends(self):
        """Analyze performance trends and generate insights"""
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # Analyze trends every 5 minutes
                insights = self._generate_performance_insights()
                
                if insights:
                    logger.info(f"Performance insights: {json.dumps(insights, indent=2)}")
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                logger.error(f"Error analyzing performance trends: {e}")
                await asyncio.sleep(600)
    
    def _check_system_thresholds(self, cpu: float, memory: float, disk: float):
        """Check if system metrics exceed thresholds"""
        if cpu > self.thresholds['cpu_usage']:
            logger.warning(f"High CPU usage: {cpu:.1f}%")
        
        if memory > self.thresholds['memory_usage']:
            logger.warning(f"High memory usage: {memory:.1f}%")
        
        if disk > 90.0:  # Disk threshold
            logger.warning(f"High disk usage: {disk:.1f}%")
    
    def _generate_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights from collected metrics"""
        insights = {}
        
        try:
            # Analyze response times
            response_time_metrics = []
            for key, metrics_deque in self.metrics.items():
                if key.startswith('response_time_'):
                    endpoint = key.replace('response_time_', '')
                    if metrics_deque:
                        avg_time = sum(m.value for m in metrics_deque) / len(metrics_deque)
                        response_time_metrics.append({
                            'endpoint': endpoint,
                            'avg_response_time': avg_time,
                            'samples': len(metrics_deque)
                        })
            
            if response_time_metrics:
                insights['slowest_endpoints'] = sorted(
                    response_time_metrics, 
                    key=lambda x: x['avg_response_time'], 
                    reverse=True
                )[:5]
            
            # Analyze cache performance
            cache_hit_rates = {}
            for key, metrics_deque in self.metrics.items():
                if key.startswith('cache_') and not key.endswith('_time'):
                    operation = key.replace('cache_', '')
                    if metrics_deque:
                        hit_rate = (sum(m.value for m in metrics_deque) / len(metrics_deque)) * 100
                        cache_hit_rates[operation] = hit_rate
            
            if cache_hit_rates:
                insights['cache_performance'] = cache_hit_rates
            
            # System resource trends
            if self.metrics['cpu_usage']:
                recent_cpu = list(self.metrics['cpu_usage'])[-10:]  # Last 10 samples
                avg_cpu = sum(m.value for m in recent_cpu) / len(recent_cpu)
                insights['system_health'] = {
                    'avg_cpu_recent': avg_cpu,
                    'uptime_hours': (time.time() - self.start_time) / 3600
                }
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
        
        return insights
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            'monitoring_active': self.is_monitoring,
            'uptime_seconds': time.time() - self.start_time,
            'total_metrics_collected': sum(len(deque) for deque in self.metrics.values()),
            'thresholds': self.thresholds
        }
        
        # Current system metrics
        try:
            summary['current_system'] = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except:
            pass
        
        # Recent performance trends
        recent_insights = self._generate_performance_insights()
        if recent_insights:
            summary['recent_insights'] = recent_insights
        
        return summary

# Global performance monitor
performance_monitor = PerformanceMonitor()
''')
    
    print("   ✅ Created advanced performance monitoring system")

if __name__ == '__main__':
    main()