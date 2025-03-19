from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request
import psutil
import time
import os

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

@router.get("/status")
async def get_system_status(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get overall system status including CPU, memory, disk usage and exchange status"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Exchange status
        exchange_status = {}
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                status = await exchange.fetch_status()
                exchange_status[exchange_id] = {
                    'online': status.get('online', False),
                    'has_trading': status.get('has_trading', False),
                    'rate_limit': status.get('rate_limit', {}),
                    'timestamp': status.get('timestamp', int(time.time() * 1000))
                }
            except Exception as e:
                exchange_status[exchange_id] = {
                    'online': False,
                    'error': str(e)
                }
        
        return {
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free
            },
            'exchanges': exchange_status,
            'timestamp': int(time.time() * 1000)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config")
async def get_config(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get system configuration (excluding sensitive data)"""
    try:
        config = {
            'exchanges': {},
            'system': {
                'version': os.getenv('VERSION', '1.0.0'),
                'environment': os.getenv('ENVIRONMENT', 'production'),
                'log_level': os.getenv('LOG_LEVEL', 'INFO')
            }
        }
        
        # Get exchange configs (excluding API keys)
        for exchange_id, exchange in exchange_manager.exchanges.items():
            exchange_config = exchange.describe()
            # Remove sensitive data
            exchange_config.pop('apiKey', None)
            exchange_config.pop('secret', None)
            exchange_config.pop('password', None)
            config['exchanges'][exchange_id] = exchange_config
            
        return config
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/exchanges/status")
async def get_exchanges_status(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get detailed status for each exchange"""
    try:
        status = {}
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                # Get exchange status
                exchange_status = await exchange.fetch_status()
                
                # Get trading limits
                markets = await exchange.fetch_markets()
                trading_limits = {
                    market['symbol']: {
                        'min_amount': market.get('limits', {}).get('amount', {}).get('min'),
                        'max_amount': market.get('limits', {}).get('amount', {}).get('max'),
                        'min_price': market.get('limits', {}).get('price', {}).get('min'),
                        'max_price': market.get('limits', {}).get('price', {}).get('max'),
                        'min_cost': market.get('limits', {}).get('cost', {}).get('min'),
                        'max_cost': market.get('limits', {}).get('cost', {}).get('max')
                    }
                    for market in markets
                }
                
                status[exchange_id] = {
                    'online': exchange_status.get('online', False),
                    'trading_enabled': exchange_status.get('has_trading', False),
                    'rate_limits': exchange_status.get('rate_limit', {}),
                    'trading_limits': trading_limits,
                    'timestamp': exchange_status.get('timestamp', int(time.time() * 1000))
                }
                
            except Exception as e:
                status[exchange_id] = {
                    'online': False,
                    'error': str(e)
                }
                
        return status
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/performance")
async def get_performance_metrics() -> Dict:
    """Get system performance metrics"""
    try:
        # CPU metrics
        cpu_times = psutil.cpu_times()
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        
        # Network I/O metrics
        net_io = psutil.net_io_counters()
        
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'times': {
                    'user': cpu_times.user,
                    'system': cpu_times.system,
                    'idle': cpu_times.idle
                },
                'frequency': {
                    'current': cpu_freq.current,
                    'min': cpu_freq.min,
                    'max': cpu_freq.max
                },
                'stats': {
                    'ctx_switches': cpu_stats.ctx_switches,
                    'interrupts': cpu_stats.interrupts,
                    'soft_interrupts': cpu_stats.soft_interrupts,
                    'syscalls': cpu_stats.syscalls
                }
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free,
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                }
            },
            'disk_io': {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            },
            'network_io': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            },
            'timestamp': int(time.time() * 1000)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 