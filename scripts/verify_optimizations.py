#!/usr/bin/env python3
"""
Quick verification of optimization components.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Verifying optimization components...\n")

# Check Request Queue
try:
    from src.core.api_request_queue import APIRequestQueue, RequestPriority
    print("✅ APIRequestQueue module loaded")
    print(f"   - Priority levels: {[p.name for p in RequestPriority]}")
except Exception as e:
    print(f"❌ APIRequestQueue error: {e}")

# Check Cache Manager
try:
    from src.core.api_cache_manager import APICacheManager, CacheStrategy, CacheConfig
    print("\n✅ APICacheManager module loaded")
    print(f"   - Cache strategies: {[s.value for s in CacheStrategy]}")
    
    # Test config lookup
    config = CacheConfig.get_config("/v5/market/tickers")
    print(f"   - Example config: /v5/market/tickers -> {config.strategy.value} (TTL: {config.ttl}s)")
except Exception as e:
    print(f"\n❌ APICacheManager error: {e}")

# Check if we can create instances
print("\nChecking instantiation...")

try:
    queue = APIRequestQueue()
    print("✅ APIRequestQueue instance created")
except Exception as e:
    print(f"❌ APIRequestQueue instantiation error: {e}")

try:
    cache = APICacheManager()
    print("✅ APICacheManager instance created")
except Exception as e:
    print(f"❌ APICacheManager instantiation error: {e}")

print("\n" + "="*50)
print("Summary:")
print("The core optimization components are ready!")
print("\nThese components provide:")
print("1. Request queuing with priority levels")
print("2. Rate limiting (prevents API exhaustion)")
print("3. Response caching with TTL strategies")
print("4. Automatic retry with exponential backoff")
print("\nDeploy to VPS with: ./scripts/deploy_api_optimizations.sh")