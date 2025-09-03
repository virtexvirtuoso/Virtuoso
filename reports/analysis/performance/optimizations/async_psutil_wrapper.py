
import asyncio
import psutil
from typing import Dict, Any

class AsyncPsutilWrapper:
    """Async wrapper for psutil operations to prevent blocking."""
    
    @staticmethod
    async def get_cpu_percent(interval: float = 1.0) -> float:
        """Get CPU percentage asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, psutil.cpu_percent, interval)
    
    @staticmethod 
    async def get_memory_info() -> Dict[str, Any]:
        """Get memory information asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _get_memory():
            vm = psutil.virtual_memory()
            return {
                'percent': vm.percent,
                'total': vm.total,
                'available': vm.available,
                'used': vm.used
            }
        
        return await loop.run_in_executor(None, _get_memory)
    
    @staticmethod
    async def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system info asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _get_info():
            try:
                cpu_times = psutil.cpu_times()
                cpu_freq = psutil.cpu_freq()  
                cpu_stats = psutil.cpu_stats()
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()
                
                return {
                    'cpu': {
                        'percent': psutil.cpu_percent(interval=1),
                        'times': cpu_times._asdict(),
                        'freq': cpu_freq._asdict() if cpu_freq else {},
                        'stats': cpu_stats._asdict()
                    },
                    'memory': {
                        'virtual': memory._asdict(),
                        'swap': swap._asdict()
                    },
                    'io': {
                        'disk': disk_io._asdict() if disk_io else {},
                        'network': net_io._asdict() if net_io else {}
                    }
                }
            except Exception as e:
                return {'error': str(e)}
        
        return await loop.run_in_executor(None, _get_info)

# Usage in async functions:
# async def get_system_metrics():
#     wrapper = AsyncPsutilWrapper()
#     cpu_percent = await wrapper.get_cpu_percent()
#     memory_info = await wrapper.get_memory_info()
#     return {'cpu': cpu_percent, 'memory': memory_info}
