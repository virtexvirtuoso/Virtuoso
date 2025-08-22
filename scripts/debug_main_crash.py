#!/usr/bin/env python3
"""Debug why main service keeps crashing"""
import sys
import traceback

def debug_startup():
    """Step through main.py initialization to find crash point"""
    
    print("=== Starting Debug ===")
    
    try:
        print("1. Setting up paths...")
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        print("2. Importing asyncio...")
        import asyncio
        
        print("3. Loading config manager...")
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        print(f"   ✓ Config loaded")
        
        print("4. Importing exchange manager...")
        from src.core.exchanges.manager import ExchangeManager
        print("   ✓ Exchange manager imported")
        
        print("5. Creating exchange manager...")
        exchange_config = config_manager.config.get('exchanges', {})
        exchange_manager = ExchangeManager(exchange_config)
        print("   ✓ Exchange manager created")
        
        print("6. Testing exchange initialization...")
        async def test_init():
            await exchange_manager.initialize()
            print("   ✓ Exchange manager initialized")
            
            # Try to get primary exchange
            primary = exchange_manager.get_primary_exchange()
            if primary:
                print(f"   ✓ Primary exchange: {primary.__class__.__name__}")
            else:
                print("   ✗ No primary exchange")
                
            await exchange_manager.cleanup()
            print("   ✓ Cleanup successful")
        
        asyncio.run(test_init())
        
        print("\n✅ All basic components work!")
        print("\n7. Testing market monitor...")
        
        from src.monitoring.monitor import MarketMonitor
        print("   ✓ Market monitor imported")
        
        print("\n=== Debug Complete ===")
        print("Main components are working. Issue might be in:")
        print("- Port binding (8003/8004)")
        print("- Concurrent task startup")
        print("- WebSocket initialization")
        
    except Exception as e:
        print(f"\n❌ CRASH POINT FOUND:")
        print(f"   Error: {e}")
        print(f"   Type: {type(e).__name__}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = debug_startup()
    sys.exit(0 if success else 1)