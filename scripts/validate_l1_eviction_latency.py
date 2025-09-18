#!/usr/bin/env python3
import asyncio
import json
import time
import random
import string


def _rand_suffix(n: int = 6) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


async def main():
    from src.api.cache_adapter_direct import cache_adapter

    report = {
        'test': 'validate_l1_eviction_latency',
        'l1_capacity_assumed': 1000,
        'counts': {},
        'latency_ms': {},
        'eviction_observed': None,
        'metrics_snapshot': {},
    }

    # Generate a unique namespace to avoid polluting shared keys
    ns = f"l1test:{int(time.time())}:{_rand_suffix()}"

    # 1) Seed > L1 capacity keys
    total_keys = 1200
    set_ok = 0
    for i in range(total_keys):
        key = f"{ns}:k:{i}"
        ok = await cache_adapter.set(key, {'i': i, 'ns': ns}, ttl=60)
        if ok:
            set_ok += 1
    report['counts']['set'] = set_ok

    # 2) First pass reads (promote to L1)
    t0 = time.perf_counter()
    first_pass_hits = 0
    for i in range(total_keys):
        key = f"{ns}:k:{i}"
        val = await cache_adapter.get(key)
        first_pass_hits += 1 if val is not None else 0
    report['counts']['first_pass_non_null'] = first_pass_hits
    report['latency_ms']['first_pass_avg'] = (time.perf_counter() - t0) * 1000.0 / max(total_keys, 1)

    # 3) Second pass reads (should be L1 hot for most-recent items)
    # Read the last 100 keys repeatedly to check sub-ms latency
    hot_keys = [f"{ns}:k:{i}" for i in range(total_keys - 100, total_keys)]
    t1 = time.perf_counter()
    round_trips = 0
    nulls = 0
    for _ in range(3):
        for k in hot_keys:
            v = await cache_adapter.get(k)
            nulls += 1 if v is None else 0
            round_trips += 1
    report['counts']['hot_reads'] = round_trips
    report['counts']['hot_nulls'] = nulls
    report['latency_ms']['hot_avg'] = (time.perf_counter() - t1) * 1000.0 / max(round_trips, 1)

    # 4) Eviction heuristic: oldest keys more likely evicted
    oldest_sample = [f"{ns}:k:{i}" for i in range(100)]
    missing_old = 0
    for k in oldest_sample:
        if await cache_adapter.get(k) is None:
            missing_old += 1
    report['counts']['oldest_missing'] = missing_old
    report['eviction_observed'] = missing_old > 0

    # 5) Metrics snapshot
    metrics = cache_adapter.get_cache_metrics()
    # Keep only key fields
    report['metrics_snapshot'] = {
        'hit_rate_pct': metrics.get('global_metrics', {}).get('hit_rate'),
        'avg_response_time_ms': metrics.get('global_metrics', {}).get('avg_response_time_ms'),
        'ops_per_sec': metrics.get('global_metrics', {}).get('operations_per_second'),
    }

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())


