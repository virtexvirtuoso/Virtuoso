#!/usr/bin/env python3
"""
Singapore VPS Network Configuration
Optimized for 4-core/16GB Singapore VPS with focus on Asian market connectivity

This module provides network optimization settings specifically tuned for:
- Ultra-low latency to Bybit (Singapore-based)
- Optimized connection pooling for 4-core system
- Rate limiting based on geographical advantages
- WebSocket configuration for stable Asian market hours
"""

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExchangeNetworkConfig:
    """Network configuration for specific exchanges"""
    name: str
    base_url: str
    ws_url: str
    max_connections: int
    rate_limit_per_minute: int
    timeout_seconds: int
    retry_attempts: int
    geographical_advantage: bool
    expected_latency_ms: int


class SingaporeNetworkOptimizer:
    """
    Network optimization manager for Singapore VPS deployment
    
    Leverages geographical location advantages:
    - Bybit servers in Singapore: <5ms latency
    - Binance Singapore presence: <20ms latency
    - Optimal Asian trading session connectivity
    """
    
    def __init__(self):
        self.location = "Singapore (sin-dc1)"
        self.cpu_cores = 4
        self.max_memory_gb = 16
        
        # Exchange configurations optimized for Singapore location
        self.exchanges = {
            'bybit': ExchangeNetworkConfig(
                name='bybit',
                base_url='https://api.bybit.com',
                ws_url='wss://stream.bybit.com',
                max_connections=80,  # Higher due to local presence
                rate_limit_per_minute=120,  # Increased from standard 100
                timeout_seconds=5,  # Lower due to proximity
                retry_attempts=3,
                geographical_advantage=True,
                expected_latency_ms=3
            ),
            
            'binance': ExchangeNetworkConfig(
                name='binance',
                base_url='https://api.binance.com',
                ws_url='wss://stream.binance.com:9443',
                max_connections=50,  # Standard allocation
                rate_limit_per_minute=1200,  # Binance standard
                timeout_seconds=10,
                retry_attempts=2,
                geographical_advantage=False,
                expected_latency_ms=20
            )
        }
        
        # Connection pool distribution per CPU core
        self.connection_pool_per_core = 25
        self.total_connections = self.cpu_cores * self.connection_pool_per_core
        
    def get_exchange_config(self, exchange: str) -> ExchangeNetworkConfig:
        """Get optimized configuration for specific exchange"""
        return self.exchanges.get(exchange.lower())
    
    def get_websocket_config(self, exchange: str) -> Dict[str, Any]:
        """
        Get WebSocket configuration optimized for Singapore location
        """
        base_config = {
            'ping_interval': 30,
            'ping_timeout': 10,
            'close_timeout': 5,
            'max_size': 10 * 1024 * 1024,  # 10MB
            'compression': 'deflate',
            'max_queue': 100,
            'write_limit': 16384,
            'read_limit': 65536
        }
        
        exchange_config = self.get_exchange_config(exchange)
        if exchange_config and exchange_config.geographical_advantage:
            # Aggressive settings for low-latency connections
            base_config.update({
                'ping_interval': 20,  # More frequent pings for stability
                'ping_timeout': 5,    # Shorter timeout for fast detection
                'close_timeout': 3,   # Quick cleanup
            })
            
        return base_config
    
    def get_connection_pool_config(self) -> Dict[str, Any]:
        """
        Get connection pool configuration for 4-core system
        """
        return {
            'total_connections': self.total_connections,
            'connections_per_core': self.connection_pool_per_core,
            'connector_limit': 100,
            'connector_limit_per_host': 30,
            'keepalive_timeout': 30,
            'enable_cleanup_closed': True,
            'timeout': asyncio.ClientTimeout(
                total=30,
                connect=10,
                sock_read=10,
                sock_connect=5
            )
        }
    
    def get_rate_limiting_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Get rate limiting configuration leveraging Singapore advantages
        """
        return {
            'bybit': {
                'requests_per_minute': self.exchanges['bybit'].rate_limit_per_minute,
                'burst_allowance': 20,  # Higher burst due to proximity
                'cooldown_seconds': 1,
                'backoff_multiplier': 1.2,
                'max_backoff': 30
            },
            'binance': {
                'requests_per_minute': self.exchanges['binance'].rate_limit_per_minute,
                'burst_allowance': 50,
                'cooldown_seconds': 2,
                'backoff_multiplier': 1.5,
                'max_backoff': 60
            }
        }
    
    def get_market_session_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Trading session configuration optimized for Asian markets
        Singapore timezone: UTC+8
        """
        return {
            'asia_session': {
                'start_utc': '00:00',  # 08:00 SGT
                'end_utc': '09:00',    # 17:00 SGT
                'priority': 'high',
                'connection_multiplier': 1.5,
                'rate_limit_boost': 1.2
            },
            'europe_session': {
                'start_utc': '07:00',  # 15:00 SGT
                'end_utc': '16:00',    # 00:00 SGT
                'priority': 'medium',
                'connection_multiplier': 1.0,
                'rate_limit_boost': 1.0
            },
            'us_session': {
                'start_utc': '13:00',  # 21:00 SGT
                'end_utc': '22:00',    # 06:00 SGT
                'priority': 'high',
                'connection_multiplier': 1.3,
                'rate_limit_boost': 1.1
            }
        }
    
    def apply_kernel_optimizations(self) -> Dict[str, str]:
        """
        Generate sysctl parameters for kernel network optimization
        """
        return {
            # TCP buffer sizes for high-frequency trading
            'net.core.rmem_max': '16777216',
            'net.core.wmem_max': '16777216', 
            'net.ipv4.tcp_rmem': '4096 12582912 16777216',
            'net.ipv4.tcp_wmem': '4096 12582912 16777216',
            
            # Connection tracking
            'net.core.somaxconn': '65535',
            'net.core.netdev_max_backlog': '5000',
            'net.ipv4.tcp_max_syn_backlog': '8192',
            
            # TCP optimization for Singapore network conditions
            'net.ipv4.tcp_congestion_control': 'bbr',
            'net.ipv4.tcp_slow_start_after_idle': '0',
            'net.ipv4.tcp_no_metrics_save': '1',
            
            # Connection reuse optimization
            'net.ipv4.tcp_tw_reuse': '1',
            'net.ipv4.tcp_fin_timeout': '30',
            'net.ipv4.tcp_keepalive_time': '600',
            'net.ipv4.tcp_keepalive_probes': '3',
            'net.ipv4.tcp_keepalive_intvl': '90',
            
            # File descriptor limits
            'fs.file-max': '2097152',
            'fs.nr_open': '2097152'
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Network monitoring configuration for Singapore VPS
        """
        return {
            'latency_targets': {
                'bybit': {'target_ms': 5, 'alert_threshold_ms': 15},
                'binance': {'target_ms': 25, 'alert_threshold_ms': 50}
            },
            'connection_health': {
                'check_interval_seconds': 30,
                'max_failed_checks': 3,
                'reconnect_delay_seconds': 5
            },
            'throughput_monitoring': {
                'sample_interval_seconds': 10,
                'alert_threshold_mbps': 100,
                'max_connections_per_exchange': {
                    'bybit': 80,
                    'binance': 50
                }
            }
        }


# Global instance for application use
singapore_network = SingaporeNetworkOptimizer()


def get_optimized_session_config(exchange: str) -> Dict[str, Any]:
    """
    Convenience function to get complete session configuration
    """
    exchange_config = singapore_network.get_exchange_config(exchange)
    websocket_config = singapore_network.get_websocket_config(exchange)
    pool_config = singapore_network.get_connection_pool_config()
    
    return {
        'exchange': exchange_config,
        'websocket': websocket_config,
        'connection_pool': pool_config,
        'rate_limiting': singapore_network.get_rate_limiting_config()[exchange]
    }


def apply_network_optimizations():
    """
    Apply all network optimizations for Singapore VPS
    Returns dict of sysctl parameters to apply
    """
    return singapore_network.apply_kernel_optimizations()


if __name__ == "__main__":
    # Example usage and validation
    print("Singapore VPS Network Configuration")
    print("="*50)
    
    for exchange in ['bybit', 'binance']:
        config = get_optimized_session_config(exchange)
        print(f"\n{exchange.upper()} Configuration:")
        print(f"  Max Connections: {config['exchange'].max_connections}")
        print(f"  Rate Limit: {config['exchange'].rate_limit_per_minute}/min")
        print(f"  Expected Latency: {config['exchange'].expected_latency_ms}ms")
        print(f"  Geographic Advantage: {config['exchange'].geographical_advantage}")
    
    print(f"\nConnection Pool: {singapore_network.total_connections} total")
    print(f"Per Core: {singapore_network.connection_pool_per_core}")
    
    print(f"\nKernel Optimizations: {len(singapore_network.apply_kernel_optimizations())} parameters")