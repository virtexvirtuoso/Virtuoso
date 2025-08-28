"""Test intelligence configuration with fresh instance."""
import os

# Set intelligence environment variables
test_env_vars = {
    'INTELLIGENCE_ENABLED': 'true',
    'INTELLIGENCE_CONNECTION_POOL_ENABLED': 'true',
    'INTELLIGENCE_POOL_MIN_SIZE': '5',
    'INTELLIGENCE_POOL_MAX_SIZE': '30',
    'INTELLIGENCE_DEBUG_MODE': 'false'
}

print("Setting test environment variables...")
for key, value in test_env_vars.items():
    os.environ[key] = value
    print(f"  {key} = {value}")

# Import after setting environment variables
from src.config.settings import Settings, IntelligenceSettings

print("\nTesting fresh Settings instance...")
settings = Settings()

print(f"✅ Intelligence System Status:")
print(f"  ENABLED: {settings.intelligence.ENABLED} (type: {type(settings.intelligence.ENABLED)})")
print(f"  CONNECTION_POOL_ENABLED: {settings.intelligence.CONNECTION_POOL_ENABLED}")
print(f"  POOL_MIN_SIZE: {settings.intelligence.POOL_MIN_SIZE}")
print(f"  POOL_MAX_SIZE: {settings.intelligence.POOL_MAX_SIZE}")
print(f"  DEBUG_MODE: {settings.intelligence.DEBUG_MODE}")

print("\nTesting direct IntelligenceSettings instance...")
intel_settings = IntelligenceSettings()
print(f"  Direct ENABLED: {intel_settings.ENABLED} (type: {type(intel_settings.ENABLED)})")
print(f"  Direct CONNECTION_POOL_ENABLED: {intel_settings.CONNECTION_POOL_ENABLED}")

# Test the main.py usage pattern
if hasattr(settings, 'intelligence') and settings.intelligence.ENABLED:
    print("\n✅ Intelligence system can activate! (main.py pattern works)")
else:
    print("\n❌ Intelligence system cannot activate")
    print(f"  hasattr check: {hasattr(settings, 'intelligence')}")
    print(f"  ENABLED value: {settings.intelligence.ENABLED}")
    print(f"  ENABLED truth: {bool(settings.intelligence.ENABLED)}")

print("\n✅ Test completed!")
