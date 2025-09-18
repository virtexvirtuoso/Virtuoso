import asyncio
import json
import time
from statistics import mean, median

async def main():
    from src.api.cache_adapter_direct import cache_adapter
    # Basic cache timing using representative keys
    keys = ['market:overview', 'market:tickers', 'analysis:signals']
    timings = []
    for key in keys:
        start = time.perf_counter()
        _ = await cache_adapter.get(key)
        timings.append((time.perf_counter() - start) * 1000)

    metrics = cache_adapter.get_cache_metrics()
    result = {
        'response_time_ms_mean': round(mean(timings), 3),
        'response_time_ms_median': round(median(timings), 3),
        'cache_hit_rate_pct': round(metrics['global_metrics']['hit_rate'], 2),
        'avg_cache_latency_ms': round(metrics['global_metrics']['avg_response_time_ms'], 3),
        'backend': metrics['backend_config'],
        'timestamp': int(time.time())
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    asyncio.run(main())


