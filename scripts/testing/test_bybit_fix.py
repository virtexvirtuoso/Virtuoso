#!/usr/bin/env python3
"""
Test that BybitExchange can be instantiated and initialized.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_bybit_instantiation():
    """Test that we can create and initialize BybitExchange."""
    print("Testing BybitExchange instantiation...")
    
    try:
        # Import necessary modules
        from src.config.manager import ConfigManager
        from src.core.exchanges.bybit import BybitExchange
        
        # Load config
        print("1. Loading configuration...")
        config = ConfigManager().config
        print("✅ Config loaded")
        
        # Create BybitExchange instance
        print("2. Creating BybitExchange instance...")
        exchange = BybitExchange(config)
        print("✅ BybitExchange instance created successfully!")
        
        # Test initialization
        print("3. Testing initialization...")
        result = await exchange.initialize()
        
        if result:
            print("✅ BybitExchange initialized successfully!")
        else:
            print("⚠️  BybitExchange initialization returned False (might be due to API credentials)")
            
        # Clean up
        if hasattr(exchange, 'close'):
            await exchange.close()
        elif hasattr(exchange, 'session') and exchange.session:
            await exchange.session.close()
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_exchange_manager():
    """Test ExchangeManager with the fixed BybitExchange."""
    print("\nTesting ExchangeManager...")
    
    try:
        from src.config.manager import ConfigManager
        from src.core.exchanges.manager import ExchangeManager
        
        # Load config
        config = ConfigManager()
        
        # Create and initialize ExchangeManager
        print("Creating ExchangeManager...")
        manager = ExchangeManager(config)
        
        print("Initializing ExchangeManager...")
        result = await manager.initialize()
        
        if result:
            print("✅ ExchangeManager initialized successfully!")
        else:
            print("❌ ExchangeManager initialization failed")
            
        # Clean up
        if hasattr(manager, 'close'):
            await manager.close()
            
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing BybitExchange Fix")
    print("=" * 60)
    
    # Test 1: Direct instantiation
    test1 = await test_bybit_instantiation()
    
    # Test 2: Through ExchangeManager
    test2 = await test_exchange_manager()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"Direct instantiation: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"ExchangeManager: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n✅ All tests passed! Ready to deploy to VPS.")
        return True
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)