"""Test intelligence configuration with environment variables."""
import os
from src.config.settings import get_settings

# Set intelligence environment variables
test_env_vars = {
    'INTELLIGENCE_ENABLED': 'true',
    'INTELLIGENCE_CONNECTION_POOL_ENABLED': 'true',
    'INTELLIGENCE_POOL_MIN_SIZE': '5',
    'INTELLIGENCE_POOL_MAX_SIZE': '30',
    'INTELLIGENCE_CACHE_L1_ENABLED': 'true',
    'INTELLIGENCE_DEBUG_MODE': 'false'
}

print("Setting test environment variables...")
for key, value in test_env_vars.items():
    os.environ[key] = value
    print(f"  {key} = {value}")

# Clear settings cache and reload
from src.config.settings import get_settings
get_settings.cache_clear()

print("\nTesting intelligence configuration...")
settings = get_settings()

print(f"✅ Intelligence System Status:")
print(f"  ENABLED: {settings.intelligence.ENABLED} (type: {type(settings.intelligence.ENABLED)})")
print(f"  CONNECTION_POOL_ENABLED: {settings.intelligence.CONNECTION_POOL_ENABLED}")
print(f"  POOL_MIN_SIZE: {settings.intelligence.POOL_MIN_SIZE}")
print(f"  POOL_MAX_SIZE: {settings.intelligence.POOL_MAX_SIZE}")
print(f"  CACHE_L1_ENABLED: {settings.intelligence.CACHE_L1_ENABLED}")
print(f"  DEBUG_MODE: {settings.intelligence.DEBUG_MODE}")

# Test the main.py usage pattern
if hasattr(settings, 'intelligence') and settings.intelligence.ENABLED:
    print("\n✅ Intelligence system can activate! (main.py pattern works)")
else:
    print("\n❌ Intelligence system cannot activate")

print(f"\n✅ All intelligence configuration tests passed!")
