"""
Configure A/B rollout for cache optimization and multi-tier cache.
"""
import os

def set_rollout(percent: float) -> None:
    os.environ['FF_MULTI_TIER_CACHE'] = 'true'
    os.environ['FF_MULTI_TIER_CACHE_ROLLOUT'] = str(percent)
    os.environ['FF_CACHE_OPTIMIZATION'] = 'true'
    os.environ['FF_CACHE_OPTIMIZATION_ROLLOUT'] = str(percent)

if __name__ == "__main__":
    import sys
    pct = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    set_rollout(pct)
    print(f"Set rollout to {pct}% for multi-tier cache + cache optimization")


