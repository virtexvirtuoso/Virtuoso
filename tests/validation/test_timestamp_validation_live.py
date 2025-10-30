#!/usr/bin/env python3
"""
Test script to verify timestamp validation is integrated and working.
This creates a test scenario to validate the integration.
"""
import sys
import yaml
import asyncio
from src.core.market.market_data_manager import MarketDataManager
from src.core.exchanges.manager import ExchangeManager


async def main():
    print("=" * 80)
    print("TIMESTAMP VALIDATION INTEGRATION TEST")
    print("=" * 80)

    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Check config
    validation_config = config.get('data_validation', {}).get('timestamp_sync', {})
    print(f"\n1. CONFIG CHECK:")
    print(f"   - Enabled: {validation_config.get('enabled', False)}")
    print(f"   - Max Delta: {validation_config.get('max_delta_seconds', 60)}s")
    print(f"   - Strict Mode: {validation_config.get('strict_mode', False)}")
    print(f"   - Fallback: {validation_config.get('fallback_to_base', True)}")

    # Create instances
    print(f"\n2. CREATING INSTANCES:")
    exchange_manager = ExchangeManager(config)
    await exchange_manager.initialize()
    print(f"   - ExchangeManager initialized")

    market_data_manager = MarketDataManager(config, exchange_manager)
    print(f"   - MarketDataManager initialized")

    # Check if validator was created
    print(f"\n3. VALIDATOR CHECK:")
    has_validator = hasattr(market_data_manager, 'timestamp_validator')
    print(f"   - Has timestamp_validator attribute: {has_validator}")

    if has_validator:
        validator = market_data_manager.timestamp_validator
        is_enabled = market_data_manager.timestamp_validation_enabled
        print(f"   - Validation enabled: {is_enabled}")

        if validator:
            print(f"   - Validator type: {type(validator).__name__}")
            print(f"   - Max delta: {validator.max_delta_seconds}s")
            print(f"   - Strict mode: {validator.strict_mode}")

            # Get initial statistics
            stats = validator.get_statistics()
            print(f"\n4. INITIAL STATISTICS:")
            print(f"   - Validation count: {stats['validation_count']}")
            print(f"   - Failure count: {stats['failure_count']}")
            print(f"   - Failure rate: {stats['failure_rate']:.2%}")
            print(f"   - Max observed delta: {stats['max_observed_delta_seconds']:.2f}s")
        else:
            print(f"   - Validator is None (validation disabled in config)")
    else:
        print(f"   - timestamp_validator attribute not found!")
        print(f"   - Available attributes: {[attr for attr in dir(market_data_manager) if not attr.startswith('_')][:10]}...")

    # Try to get market data to trigger validation
    print(f"\n5. TESTING VALIDATION WITH LIVE DATA:")
    try:
        symbol = "BTCUSDT"
        print(f"   - Fetching market data for {symbol}...")
        market_data = await market_data_manager.get_market_data(symbol)
        print(f"   - Market data fetched successfully")

        if has_validator and validator:
            stats_after = validator.get_statistics()
            print(f"\n6. STATISTICS AFTER get_market_data():")
            print(f"   - Validation count: {stats_after['validation_count']}")
            print(f"   - Failure count: {stats_after['failure_count']}")
            print(f"   - Failure rate: {stats_after['failure_rate']:.2%}")
            print(f"   - Max observed delta: {stats_after['max_observed_delta_seconds']:.2f}s")

            if stats_after['validation_count'] > stats['validation_count']:
                print(f"\n✅ SUCCESS: Timestamp validation is ACTIVE!")
                print(f"   Validations increased from {stats['validation_count']} to {stats_after['validation_count']}")
                return 0
            else:
                print(f"\n⚠️  WARNING: Validation count did not increase")
                print(f"   This might mean:")
                print(f"   - Validation is not being called in get_market_data()")
                print(f"   - OHLCV data was not fetched (cached data used)")
                return 1
        else:
            print(f"\n⚠️  Validator not available for statistics check")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR during market data fetch: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        await exchange_manager.close()

    print("\n" + "=" * 80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
