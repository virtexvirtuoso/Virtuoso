#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_with_rollout(rollout: int) -> dict:
    env = os.environ.copy()
    env['FF_MULTI_TIER_CACHE'] = 'true'
    env['FF_MULTI_TIER_CACHE_ROLLOUT'] = str(rollout)
    env['FF_CACHE_OPTIMIZATION'] = 'true'
    env['FF_CACHE_OPTIMIZATION_ROLLOUT'] = str(rollout)
    env['PYTHONPATH'] = str(ROOT)

    # Warm cache with real data
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'warm_cache_once.py')], check=False, env=env)
    # Collect baseline metrics
    out = subprocess.check_output([sys.executable, str(ROOT / 'scripts' / 'collect_baseline_metrics.py')], env=env)
    return json.loads(out.decode('utf-8'))


if __name__ == '__main__':
    r10 = run_with_rollout(10)
    r100 = run_with_rollout(100)
    report = {
        'rollout_10': r10,
        'rollout_100': r100,
        'delta': {
            'mean_ms': round(r10['response_time_ms_mean'] - r100['response_time_ms_mean'], 3),
            'median_ms': round(r10['response_time_ms_median'] - r100['response_time_ms_median'], 3),
            'hit_rate_pct': round(r100['cache_hit_rate_pct'] - r10['cache_hit_rate_pct'], 2),
            'latency_ms': round(r10['avg_cache_latency_ms'] - r100['avg_cache_latency_ms'], 3)
        }
    }
    # Write clean JSON to file and to stdout without extra logs
    out_path = ROOT / 'ab_benchmark_report.json'
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


