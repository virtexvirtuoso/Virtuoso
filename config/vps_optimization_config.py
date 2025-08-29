"""
VPS Performance Optimization Configuration
Optimized for: 4 vCPU, 16GB RAM, 160GB SSD, Singapore VPS
"""

import os
from typing import Dict, Any

class VPSOptimizationConfig:
    """Configuration class for VPS performance optimization"""
    
    # VPS Hardware Specs
    VCPU_CORES = 4
    MEMORY_GB = 16
    STORAGE_GB = 160
    LOCATION = "Singapore"
    
    # CPU Optimization Settings
    UVICORN_WORKERS = 2  # 50% of CPU cores
    ANALYSIS_WORKERS = 2  # Dedicated background processing
    MAX_WORKER_THREADS = 4  # Thread pool size
    
    # Memory Allocation (Total: 16GB)
    SYSTEM_RESERVED_GB = 2
    PYTHON_APP_MEMORY_GB = 8  # Main application
    MEMCACHED_MEMORY_MB = 4096  # 4GB for dashboard caching
    REDIS_MEMORY_MB = 2048  # 2GB for alerts/sessions
    
    # Connection Pool Optimization
    BYBIT_CONNECTIONS = {
        'max_pool_size': 12,  # Primary exchange
        'timeout': 10,
        'retry_attempts': 3,
        'keepalive': 300
    }
    
    BINANCE_CONNECTIONS = {
        'max_pool_size': 8,   # Secondary exchange
        'timeout': 10,
        'retry_attempts': 3,
        'keepalive': 300
    }
    
    TOTAL_MAX_CONNECTIONS = 20
    
    # Cache Configuration with optimized TTLs
    CACHE_CONFIG = {
        'dashboard_data': {
            'ttl_seconds': 30,    # High frequency updates
            'memory_mb': 1024,    # 1GB
            'compression': True
        },
        'market_metrics': {
            'ttl_seconds': 60,    # Medium frequency
            'memory_mb': 1536,    # 1.5GB
            'compression': True
        },
        'analysis_results': {
            'ttl_seconds': 300,   # Low frequency, high compute cost
            'memory_mb': 1024,    # 1GB
            'compression': True
        },
        'static_data': {
            'ttl_seconds': 3600,  # Static reference data
            'memory_mb': 512,     # 0.5GB
            'compression': False
        }
    }
    
    # FastAPI Optimization Settings
    FASTAPI_CONFIG = {
        'workers': UVICORN_WORKERS,
        'worker_class': 'uvicorn.workers.UvicornWorker',
        'host': '0.0.0.0',
        'port': 8003,
        'keepalive': 65,
        'max_requests': 10000,
        'max_requests_jitter': 1000,
        'timeout': 30
    }
    
    # Database Optimization (SQLite)
    DATABASE_CONFIG = {
        'wal_mode': True,           # Write-Ahead Logging for concurrency
        'cache_size': '-64000',     # 64MB cache (negative = KB)
        'temp_store': 'memory',     # Use memory for temp tables
        'mmap_size': 268435456,     # 256MB memory-mapped I/O
        'journal_mode': 'WAL',
        'synchronous': 'NORMAL',    # Balance safety vs performance
        'foreign_keys': True
    }
    
    # Network Optimization for Singapore Location
    NETWORK_CONFIG = {
        'tcp_keepalive': 300,
        'connect_timeout': 10,
        'read_timeout': 30,
        'max_retries': 3,
        'backoff_factor': 0.3,
        'status_forcelist': [500, 502, 503, 504]
    }
    
    # Logging Configuration for SSD Optimization
    LOGGING_CONFIG = {
        'max_file_size_mb': 100,
        'backup_count': 7,          # Keep 1 week of logs
        'compression': True,
        'log_levels': {
            'critical': True,
            'error': True,
            'warning': True,
            'info': True,
            'debug': False          # Disable in production
        }
    }
    
    # Performance Monitoring Thresholds
    PERFORMANCE_THRESHOLDS = {
        'cpu_warning': 85,          # CPU usage %
        'cpu_critical': 95,
        'memory_warning': 85,       # Memory usage %
        'memory_critical': 95,
        'disk_warning': 80,         # Disk usage %
        'disk_critical': 90,
        'response_time_warning': 100,  # ms
        'response_time_critical': 500,
        'cache_hit_ratio_warning': 80,  # %
        'error_rate_warning': 1,    # %
        'error_rate_critical': 5
    }
    
    # Exchange-Specific Rate Limits (Singapore timezone advantage)
    RATE_LIMITS = {
        'bybit': {
            'requests_per_minute': 600,   # Higher limit due to low latency
            'weight_limit': 120,
            'orders_per_second': 10
        },
        'binance': {
            'requests_per_minute': 1200,  # Binance allows higher rates
            'weight_limit': 1200,
            'orders_per_second': 10
        }
    }
    
    @classmethod
    def get_environment_vars(cls) -> Dict[str, str]:
        """Generate environment variables for the optimized configuration"""
        return {
            # Python optimizations
            'PYTHONMALLOC': 'malloc',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONUNBUFFERED': '1',
            'PYTHONHASHSEED': '0',
            
            # Memory settings
            'MEMCACHED_MEMORY': str(cls.MEMCACHED_MEMORY_MB),
            'REDIS_MAXMEMORY': f"{cls.REDIS_MEMORY_MB}mb",
            
            # CPU settings
            'UVICORN_WORKERS': str(cls.UVICORN_WORKERS),
            'ANALYSIS_WORKERS': str(cls.ANALYSIS_WORKERS),
            'MAX_WORKER_THREADS': str(cls.MAX_WORKER_THREADS),
            
            # Connection pool settings
            'BYBIT_POOL_SIZE': str(cls.BYBIT_CONNECTIONS['max_pool_size']),
            'BINANCE_POOL_SIZE': str(cls.BINANCE_CONNECTIONS['max_pool_size']),
            'MAX_CONCURRENT_CONNECTIONS': str(cls.TOTAL_MAX_CONNECTIONS),
            
            # Cache settings
            'CACHE_TTL_DASHBOARD': str(cls.CACHE_CONFIG['dashboard_data']['ttl_seconds']),
            'CACHE_TTL_MARKET': str(cls.CACHE_CONFIG['market_metrics']['ttl_seconds']),
            'CACHE_TTL_ANALYSIS': str(cls.CACHE_CONFIG['analysis_results']['ttl_seconds']),
            
            # Performance settings
            'FASTAPI_WORKERS': str(cls.FASTAPI_CONFIG['workers']),
            'FASTAPI_KEEPALIVE': str(cls.FASTAPI_CONFIG['keepalive']),
            'FASTAPI_MAX_REQUESTS': str(cls.FASTAPI_CONFIG['max_requests'])
        }
    
    @classmethod
    def get_systemd_resource_limits(cls) -> Dict[str, str]:
        """Generate systemd resource limits"""
        return {
            'MemoryMax': f"{cls.PYTHON_APP_MEMORY_GB}G",
            'CPUQuota': "300%",  # 3 cores max (75% of 4 cores)
            'LimitNOFILE': '65536',
            'LimitNPROC': '4096',
            'TasksMax': '4096'
        }
    
    @classmethod
    def get_cache_memory_distribution(cls) -> Dict[str, int]:
        """Get memory distribution across cache types"""
        total_cache_mb = cls.MEMCACHED_MEMORY_MB
        distribution = {}
        
        for cache_type, config in cls.CACHE_CONFIG.items():
            distribution[cache_type] = config['memory_mb']
            
        return distribution
    
    @classmethod
    def get_optimization_summary(cls) -> Dict[str, Any]:
        """Get complete optimization summary"""
        return {
            'hardware': {
                'vcpu_cores': cls.VCPU_CORES,
                'memory_gb': cls.MEMORY_GB,
                'storage_gb': cls.STORAGE_GB,
                'location': cls.LOCATION
            },
            'resource_allocation': {
                'system_reserved_gb': cls.SYSTEM_RESERVED_GB,
                'python_app_gb': cls.PYTHON_APP_MEMORY_GB,
                'memcached_gb': cls.MEMCACHED_MEMORY_MB / 1024,
                'redis_gb': cls.REDIS_MEMORY_MB / 1024
            },
            'connection_pools': {
                'bybit': cls.BYBIT_CONNECTIONS,
                'binance': cls.BINANCE_CONNECTIONS,
                'total_max': cls.TOTAL_MAX_CONNECTIONS
            },
            'cache_config': cls.CACHE_CONFIG,
            'performance_targets': {
                'cpu_utilization': '70-80%',
                'memory_utilization': '75-85%',
                'response_time': '<100ms',
                'cache_hit_ratio': '>90%',
                'uptime': '>99.9%'
            },
            'singapore_advantages': [
                'Low latency to Asian crypto exchanges',
                'Optimal timezone for Asian trading hours',
                'High-speed network infrastructure',
                'Regulatory-friendly environment'
            ]
        }

# Create singleton instance
vps_config = VPSOptimizationConfig()

# Export key configurations for easy import
VPS_ENV_VARS = vps_config.get_environment_vars()
VPS_RESOURCE_LIMITS = vps_config.get_systemd_resource_limits()
VPS_CACHE_DISTRIBUTION = vps_config.get_cache_memory_distribution()
VPS_OPTIMIZATION_SUMMARY = vps_config.get_optimization_summary()