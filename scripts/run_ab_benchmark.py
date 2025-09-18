#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def _parse_json_from_output(output: bytes) -> dict:
    text = output.decode('utf-8', errors='ignore')
    # Extract last JSON object from noisy stdout
    idx = text.rfind('{')
    if idx != -1:
        candidate = text[idx:]
        try:
            return json.loads(candidate)
        except Exception:
            pass
    # Fallback: first JSON object
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        return json.loads(m.group(0))
    return json.loads(text)


def run_with_rollout(rollout: int) -> dict:
    env = os.environ.copy()
    env['FF_MULTI_TIER_CACHE'] = 'true'
    env['FF_MULTI_TIER_CACHE_ROLLOUT'] = str(rollout)
    env['FF_CACHE_OPTIMIZATION'] = 'true'
    env['FF_CACHE_OPTIMIZATION_ROLLOUT'] = str(rollout)
    env['PYTHONPATH'] = str(ROOT)

    # Collect baseline metrics (script emits strict JSON)
    out = subprocess.check_output([sys.executable, str(ROOT / 'scripts' / 'collect_baseline_metrics.py')], env=env)
    return _parse_json_from_output(out)


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
    # Write clean JSON to docs path and to stdout
    out_path = ROOT / 'docs' / 'strategic-roadmap' / 'phase-1-foundation' / 'ab_report.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


