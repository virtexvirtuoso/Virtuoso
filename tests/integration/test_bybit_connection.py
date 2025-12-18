#!/usr/bin/env python3
"""
Test Bybit Exchange Connection
==============================

This script tests if the Bybit exchange credentials are working
and the exchange manager can successfully connect.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

async def test_bybit_connection():
    """Test Bybit connection with current credentials."""
    print("🔍 Testing Bybit Exchange Connection")
    print("=" * 50)

    # Check environment variables
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    testnet = os.getenv('BYBIT_TESTNET', 'false').lower() == 'true'

    print(f"📊 Configuration:")
    print(f"  API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"  API Secret: {'✅ Set' if api_secret else '❌ Missing'}")
    print(f"  Testnet: {testnet}")
    print()

    if not api_key or not api_secret:
        print("❌ Missing Bybit credentials in environment")
        return False

    # Test direct CCXT connection
    try:
        import ccxt

        exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': testnet,
            'enableRateLimit': True,
        })

        print("🔄 Testing direct CCXT connection...")

        # Test basic connection
        markets = await exchange.load_markets()
        print(f"✅ Successfully loaded {len(markets)} markets")

        # Test ticker fetch
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"✅ BTC/USDT Price: ${ticker['last']:,.2f}")

        await exchange.close()
        print("✅ Direct CCXT connection successful!")
        return True

    except Exception as e:
        print(f"❌ Direct CCXT connection failed: {e}")
        return False

async def test_system_exchange_manager():
    """Test the system's exchange manager."""
    print("\n🔍 Testing System Exchange Manager")
    print("=" * 50)

    try:
        from config.manager import ConfigManager
        from core.exchanges.manager import ExchangeManager

        # Initialize config
        config_manager = ConfigManager()
        print("✅ Config manager initialized")

        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        print("✅ Exchange manager created")

        # Try to initialize
        result = await exchange_manager.initialize()
        print(f"Exchange Manager Initialize: {result}")

        if result:
            primary = await exchange_manager.get_primary_exchange()
            print(f"Primary Exchange: {primary}")

            if primary:
                print("✅ System exchange manager working!")

                # Test market data fetch
                try:
                    ticker = await primary.interface.fetch_ticker('BTC/USDT')
                    print(f"✅ System BTC/USDT Price: ${ticker['last']:,.2f}")
                except Exception as e:
                    print(f"⚠️ System ticker fetch error: {e}")

                return True
            else:
                print("❌ No primary exchange available")
                return False
        else:
            print("❌ Exchange manager initialization failed")
            return False

    except Exception as e:
        print(f"❌ System exchange manager error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all connection tests."""
    print(f"🚀 Bybit Connection Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: Direct CCXT
    ccxt_success = await test_bybit_connection()

    # Test 2: System Exchange Manager
    system_success = await test_system_exchange_manager()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Direct CCXT: {'✅ PASS' if ccxt_success else '❌ FAIL'}")
    print(f"System Manager: {'✅ PASS' if system_success else '❌ FAIL'}")

    if ccxt_success and system_success:
        print("🎉 All tests passed! Bybit connection is working.")
        return 0
    elif ccxt_success:
        print("⚠️ Direct connection works, but system integration needs fixing.")
        return 1
    else:
        print("❌ Connection failed. Check credentials and network.")
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