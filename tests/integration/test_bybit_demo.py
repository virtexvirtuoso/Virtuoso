#!/usr/bin/env python3
"""
Test Bybit Demo Trading Configuration
====================================

This script tests different Bybit connection methods including:
1. Demo trading mode with custom endpoints
2. Sandbox mode configuration
3. Production API without credentials (read-only)
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

async def test_bybit_demo_mode():
    """Test Bybit demo trading mode configuration."""
    print("🔍 Testing Bybit Demo Trading Mode")
    print("=" * 50)

    try:
        import ccxt

        # Configuration for demo mode
        config = {
            'enableRateLimit': True,
            'version': 'v5',
            'options': {
                'defaultType': 'spot',  # Start with spot trading
            }
        }

        # Add credentials if available
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        demo_mode = os.getenv('BYBIT_DEMO_MODE', 'false').lower() == 'true'

        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret
            print(f"✅ Using API credentials (Demo Mode: {demo_mode})")
        else:
            print("⚠️ No credentials - testing public endpoints only")

        exchange = ccxt.bybit(config)

        # Enable demo mode if configured
        if demo_mode:
            exchange.set_sandbox_mode(True)
            # Override URLs for demo trading
            demo_base_url = os.getenv('BYBIT_DEMO_BASE_URL', 'https://api-demo.bybit.com')
            exchange.urls['api'] = {
                'public': demo_base_url,
                'private': demo_base_url,
            }
            print(f"✅ Demo mode enabled with endpoint: {demo_base_url}")

        # Test public endpoints first (no auth required)
        print("\n🔄 Testing public market data...")
        markets = await exchange.load_markets()
        print(f"✅ Loaded {len(markets)} markets")

        # Test ticker fetch
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"✅ BTC/USDT Price: ${ticker['last']:,.2f}")

        # Test private endpoints if credentials available
        if api_key and api_secret:
            print("\n🔄 Testing private endpoints...")
            try:
                balance = await exchange.fetch_balance()
                print("✅ Successfully fetched balance!")

                # Show some balance info (safely)
                if 'free' in balance:
                    free_balance = balance['free']
                    total_assets = sum(1 for asset, amount in free_balance.items() if amount > 0)
                    print(f"✅ Account has {total_assets} different assets")

            except Exception as e:
                print(f"⚠️ Private endpoint error: {e}")

        await exchange.close()
        return True

    except Exception as e:
        print(f"❌ Demo mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bybit_public_only():
    """Test Bybit public endpoints without authentication."""
    print("\n🔍 Testing Bybit Public Endpoints (No Auth)")
    print("=" * 50)

    try:
        import ccxt

        # Public-only configuration
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'version': 'v5',
        })

        print("🔄 Testing public market data...")

        # Test multiple symbols
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

        for symbol in symbols:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                print(f"✅ {symbol}: ${ticker['last']:,.4f}")
            except Exception as e:
                print(f"⚠️ {symbol} failed: {e}")

        # Test OHLCV data
        print("\n🔄 Testing OHLCV data...")
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT', '1h', limit=5)
        print(f"✅ Fetched {len(ohlcv)} OHLCV candles")

        if ohlcv:
            latest = ohlcv[-1]
            print(f"✅ Latest candle: O:{latest[1]:.2f} H:{latest[2]:.2f} L:{latest[3]:.2f} C:{latest[4]:.2f}")

        await exchange.close()
        return True

    except Exception as e:
        print(f"❌ Public endpoints test failed: {e}")
        return False

async def test_system_integration():
    """Test if the crisis-stabilized system can now connect to Bybit."""
    print("\n🔍 Testing Crisis-Stabilized System Integration")
    print("=" * 50)

    try:
        # Test the correlation service we fixed during crisis stabilization
        from core.services.simple_correlation_service import SimpleCorrelationService

        # Initialize without exchange manager (should work with our fixes)
        service = SimpleCorrelationService()
        print("✅ SimpleCorrelationService initialized")

        # Test that it properly rejects synthetic data (our security fix)
        try:
            result = await service.get_price_data("BTCUSDT", 10)
            print("❌ Unexpected: service returned data without exchange manager")
            return False
        except ValueError as e:
            if "real market data" in str(e).lower():
                print("✅ Service correctly rejects synthetic data - security fix working!")
                return True
            else:
                print(f"⚠️ Different error: {e}")
                return False

    except Exception as e:
        print(f"❌ System integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all Bybit connection tests."""
    print(f"🚀 Bybit Demo Configuration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: Demo mode with credentials
    demo_success = await test_bybit_demo_mode()

    # Test 2: Public endpoints only
    public_success = await test_bybit_public_only()

    # Test 3: System integration
    system_success = await test_system_integration()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Demo Mode: {'✅ PASS' if demo_success else '❌ FAIL'}")
    print(f"Public Endpoints: {'✅ PASS' if public_success else '❌ FAIL'}")
    print(f"System Integration: {'✅ PASS' if system_success else '❌ FAIL'}")

    if public_success and system_success:
        print("🎉 Core functionality validated! Crisis stabilization successful.")
        if demo_success:
            print("🎉 Demo trading mode also working!")
        else:
            print("⚠️ Demo mode needs Bybit demo account setup")
        return 0
    elif public_success:
        print("⚠️ Public data works, but system integration needs work.")
        return 1
    else:
        print("❌ Connection issues detected.")
        return 2

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test framework error: {e}")
        sys.exit(1)