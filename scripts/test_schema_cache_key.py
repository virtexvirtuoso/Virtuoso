"""Test if schema.CACHE_KEY is being set correctly"""
import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

from src.core.schemas import SignalsSchema, MarketOverviewSchema

# Test SignalsSchema
print("="*70)
print("Testing SignalsSchema.CACHE_KEY")
print("="*70)

# Class attribute
print(f"Class attribute: SignalsSchema.CACHE_KEY = '{SignalsSchema.CACHE_KEY}'")

# Instance attribute
schema = SignalsSchema(signals=[])
print(f"Instance attribute: schema.CACHE_KEY = '{schema.CACHE_KEY}'")
print(f"Type: {type(schema.CACHE_KEY)}")
print(f"Repr: {repr(schema.CACHE_KEY)}")
print(f"Bool: {bool(schema.CACHE_KEY)}")

# Test with actual data
schema_with_data = SignalsSchema(signals=[
    {'symbol': 'BTCUSDT', 'confluence_score': 65}
])
print(f"\nWith data: schema_with_data.CACHE_KEY = '{schema_with_data.CACHE_KEY}'")

print("\n" + "="*70)
print("Testing MarketOverviewSchema.CACHE_KEY")
print("="*70)

print(f"Class attribute: MarketOverviewSchema.CACHE_KEY = '{MarketOverviewSchema.CACHE_KEY}'")
overview_schema = MarketOverviewSchema(
    total_symbols=15,
    trend_strength=50.0,
    btc_dominance=58.5,
    total_volume_24h=1000000
)
print(f"Instance attribute: overview_schema.CACHE_KEY = '{overview_schema.CACHE_KEY}'")
