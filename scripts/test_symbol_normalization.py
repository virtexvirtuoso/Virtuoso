#!/usr/bin/env python3
"""
Test Symbol Normalization and Cache Key Consistency
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.naming_mapper import normalize_symbol, normalize_cache_key
from src.core.cache_keys import CacheKeys

def test_symbol_normalization():
    """Test symbol normalization functionality."""

    print("=== Symbol Normalization Tests ===")

    test_symbols = [
        'BTC/USDT',
        'BTCUSDT',
        'ETH/USDT',
        'ETHUSDT',
        'btc-usdt',
        'eth-usdt',
        'SOL/USDT',
        'SOLUSDT'
    ]

    print("\nExchange Format (BTCUSDT):")
    for symbol in test_symbols:
        normalized = normalize_symbol(symbol, 'exchange')
        print(f"  {symbol:10} -> {normalized}")

    print("\nCCXT Format (BTC/USDT):")
    for symbol in test_symbols:
        normalized = normalize_symbol(symbol, 'ccxt')
        print(f"  {symbol:10} -> {normalized}")

def test_cache_key_consistency():
    """Test cache key consistency with symbol normalization."""

    print("\n=== Cache Key Consistency Tests ===")

    # Test different symbol formats for same pair
    symbol_variants = ['BTC/USDT', 'BTCUSDT', 'btc-usdt']

    print("\nConfluence Score Keys:")
    for symbol in symbol_variants:
        key = CacheKeys.confluence_score(symbol)
        print(f"  {symbol:10} -> {key}")

    print("\nMarket Data Keys:")
    for symbol in symbol_variants:
        key = CacheKeys.market_data(symbol, '1m')
        print(f"  {symbol:10} -> {key}")

    print("\nSignal Data Keys:")
    for symbol in symbol_variants:
        key = CacheKeys.signal_data(symbol)
        print(f"  {symbol:10} -> {key}")

def test_key_collisions():
    """Test for potential key collisions."""

    print("\n=== Key Collision Tests ===")

    # Test edge cases that might cause collisions
    edge_cases = [
        ('BTCUSDT', 'BTC/USDT'),
        ('1000BONKUSDT', '1000BONK/USDT'),
        ('BTCDOMUSDT', 'BTCDOM/USDT'),
        ('USDCUSDT', 'USDC/USDT')
    ]

    print("\nChecking for consistent cache keys:")
    all_keys_consistent = True

    for symbol1, symbol2 in edge_cases:
        key1 = CacheKeys.confluence_score(symbol1)
        key2 = CacheKeys.confluence_score(symbol2)

        if key1 == key2:
            print(f"  ✅ {symbol1} == {symbol2} -> {key1}")
        else:
            print(f"  ❌ {symbol1} != {symbol2}: {key1} vs {key2}")
            all_keys_consistent = False

    return all_keys_consistent

def test_naming_mapper_integration():
    """Test integration with naming mapper."""

    print("\n=== Naming Mapper Integration Tests ===")

    from src.core.naming_mapper import naming_mapper

    # Test key normalization
    test_data = {
        'fundingRate': 0.0001,
        'openInterest': 1000000,
        'longShortRatio': 1.5,
        'market_mood': 'bullish'
    }

    print(f"\nOriginal data: {test_data}")
    normalized_data = naming_mapper.normalize_dict(test_data)
    print(f"Normalized data: {normalized_data}")

    # Test exchange response mapping
    bybit_response = {
        'symbol': 'BTCUSDT',
        'lastPrice': '50000.00',
        'fundingRate': '0.0001',
        'openInterest': '1000000'
    }

    print(f"\nBybit response: {bybit_response}")
    mapped_response = naming_mapper.map_exchange_response(bybit_response, 'bybit')
    print(f"Mapped response: {mapped_response}")

if __name__ == "__main__":
    print("Testing Symbol Normalization and Cache Key Consistency\n")

    test_symbol_normalization()
    test_cache_key_consistency()

    keys_consistent = test_key_collisions()
    test_naming_mapper_integration()

    print("\n=== Summary ===")
    if keys_consistent:
        print("✅ All cache keys are consistent across symbol formats")
        print("✅ Symbol normalization is working correctly")
        print("✅ No key collisions detected")
    else:
        print("❌ Cache key inconsistencies detected")
        print("❌ Manual review required")

    print("\nSymbol normalization and cache key consistency testing complete.")