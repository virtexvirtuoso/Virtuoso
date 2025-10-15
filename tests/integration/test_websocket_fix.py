
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.core.exchanges.websocket_manager import WebSocketManager

async def test_connectivity():
    # Test configuration
    config = {
        'websocket': {'enabled': True},
        'exchanges': {'bybit': {'testnet': False}},
        'market_data': {'websocket_logging': {'verbose': True}}
    }

    # Create WebSocket manager
    ws_manager = WebSocketManager(config)

    # Test symbols
    test_symbols = ['BTCUSDT', 'ETHUSDT']

    try:
        print("Testing WebSocket initialization...")
        await ws_manager.initialize(test_symbols)

        # Check status
        status = ws_manager.get_status()
        print(f"Connection status: {status}")

        if status['connected']:
            print("✅ WebSocket connectivity test PASSED")
        else:
            print("❌ WebSocket connectivity test FAILED")

        # Wait a few seconds for messages
        await asyncio.sleep(5)

        # Get final status
        final_status = ws_manager.get_status()
        print(f"Final status: {final_status}")

    except Exception as e:
        print(f"❌ WebSocket test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connectivity())
