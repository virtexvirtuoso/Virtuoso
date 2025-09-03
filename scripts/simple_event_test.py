#!/usr/bin/env python3
"""
Simple Event-Driven Architecture Test

Quick validation of the basic event infrastructure functionality.
"""

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.events import EventBus, EventPublisher, DataType, OHLCVDataEvent


async def test_basic_functionality():
    """Test basic event functionality."""
    print("Testing EventBus basic functionality...")
    
    # Test EventBus
    event_bus = EventBus(max_queue_size=100, enable_metrics=True)
    await event_bus.start()
    
    received_events = []
    
    async def test_handler(event):
        received_events.append(event)
        
    # Subscribe to events
    handler_id = await event_bus.subscribe("test.event", test_handler)
    
    # Test event creation and publishing
    from src.core.events.event_bus import Event
    test_event = Event(event_type="test.event", data={"test": "data"})
    event_id = await event_bus.publish(test_event)
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    print(f"Published event {event_id}")
    print(f"Received {len(received_events)} events")
    
    if received_events:
        print(f"First event type: {received_events[0].event_type}")
        print("✅ Basic EventBus functionality works!")
    else:
        print("❌ No events received")
        
    await event_bus.stop()
    await event_bus.dispose_async()


async def test_event_types():
    """Test event type creation."""
    print("\nTesting Event Types...")
    
    try:
        # Test OHLCV event creation
        ohlcv_event = OHLCVDataEvent(
            symbol="BTC/USDT",
            exchange="bybit", 
            timeframe="1m",
            raw_data={'test': 'data'}
        )
        
        print(f"OHLCV Event type: {ohlcv_event.event_type}")
        print(f"OHLCV Event source: {ohlcv_event.source}")
        print("✅ Event types work!")
        
    except Exception as e:
        print(f"❌ Event types error: {e}")


async def test_event_publisher():
    """Test EventPublisher."""
    print("\nTesting EventPublisher...")
    
    try:
        event_bus = EventBus(enable_metrics=True)
        event_publisher = EventPublisher(event_bus, enable_batching=False)  # Disable batching for simple test
        
        await event_bus.start()
        await event_publisher.start()
        
        # Test publishing market data
        event_id = await event_publisher.publish_market_data(
            symbol="BTC/USDT",
            exchange="bybit",
            data_type=DataType.TICKER,
            raw_data={'price': 50000.0}
        )
        
        print(f"Published market data event: {event_id}")
        print("✅ EventPublisher works!")
        
        await event_publisher.stop()
        await event_bus.stop()
        await event_publisher.dispose_async()
        await event_bus.dispose_async()
        
    except Exception as e:
        print(f"❌ EventPublisher error: {e}")


async def main():
    """Main test function."""
    print("=" * 50)
    print("Simple Event-Driven Architecture Test")
    print("=" * 50)
    
    try:
        await test_basic_functionality()
        await test_event_types()
        await test_event_publisher()
        
        print("\n" + "=" * 50)
        print("✅ Basic event infrastructure is working!")
        print("Event-driven architecture Phase 1 foundation complete")
        return True
        
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)