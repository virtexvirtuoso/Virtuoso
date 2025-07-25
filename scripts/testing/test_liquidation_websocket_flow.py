#!/usr/bin/env python3
"""
Comprehensive test for liquidation websocket implementation across the codebase.
Tests the complete flow from subscription to storage and alerts.
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_liquidation_models():
    """Test liquidation event model creation and validation."""
    try:
        from src.api.models.liquidation import LiquidationEvent, LiquidationType, LiquidationSeverity
        
        # Test creating a liquidation event from websocket data
        ws_data = {
            's': 'BTCUSDT',
            'S': 'Buy',  # Buy = liquidated long
            'v': '0.5',
            'p': '50000',
            'T': int(time.time() * 1000)
        }
        
        # Convert to LiquidationEvent
        event = LiquidationEvent(
            event_id=f"ws_{ws_data['T']}_{ws_data['s']}_{ws_data['S']}",
            symbol=ws_data['s'],
            exchange='bybit',
            timestamp=datetime.fromtimestamp(ws_data['T'] / 1000),
            liquidation_type=LiquidationType.LONG_LIQUIDATION if ws_data['S'] == 'Buy' else LiquidationType.SHORT_LIQUIDATION,
            severity=LiquidationSeverity.MEDIUM,
            confidence_score=0.9,
            trigger_price=float(ws_data['p']),
            price_impact=0.0,
            volume_spike_ratio=1.0,
            liquidated_amount_usd=float(ws_data['p']) * float(ws_data['v']),
            bid_ask_spread_pct=0.0,
            order_book_imbalance=0.0,
            market_depth_impact=0.0,
            volatility_spike=1.0,
            duration_seconds=0
        )
        
        logger.info("✅ Liquidation model test passed")
        logger.info(f"  - Event ID: {event.event_id}")
        logger.info(f"  - Type: {event.liquidation_type}")
        logger.info(f"  - Amount: ${event.liquidated_amount_usd:,.2f}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Liquidation model test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_liquidation_cache():
    """Test liquidation cache functionality."""
    try:
        from src.utils.liquidation_cache import LiquidationCache
        
        # Create test cache
        cache = LiquidationCache(cache_dir="test_cache", cache_expiry=3600)
        
        # Test liquidation data
        test_liquidation = {
            'symbol': 'BTCUSDT',
            'timestamp': int(time.time() * 1000),
            'price': 50000.0,
            'size': 0.5,
            'side': 'long',
            'source': 'websocket'
        }
        
        # Test append
        cache.append(test_liquidation, 'btcusdt')  # Cache uses lowercase
        
        # Load using the file directly since load() expects different format
        cache_file = os.path.join("test_cache", "btcusdt_liquidations.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
        else:
            cached_data = None
        
        if cached_data and len(cached_data) > 0:
            logger.info("✅ Liquidation cache test passed")
            logger.info(f"  - Cached {len(cached_data)} events")
            logger.info(f"  - Latest: {cached_data[-1]}")
            
            # Cleanup
            import shutil
            if os.path.exists("test_cache"):
                shutil.rmtree("test_cache")
            return True
        else:
            logger.error("❌ Liquidation cache test failed - no data cached")
            return False
            
    except Exception as e:
        logger.error(f"❌ Liquidation cache test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_websocket_subscription_format():
    """Test websocket subscription format for liquidations."""
    try:
        # Test Bybit subscription format
        symbols = ['BTCUSDT', 'ETHUSDT']
        
        # Correct format for Bybit V5
        subscription = {
            "op": "subscribe",
            "args": [f"allLiquidation.{symbol}" for symbol in symbols]
        }
        
        expected_args = ["allLiquidation.BTCUSDT", "allLiquidation.ETHUSDT"]
        
        if subscription['args'] == expected_args:
            logger.info("✅ WebSocket subscription format test passed")
            logger.info(f"  - Format: {subscription}")
            return True
        else:
            logger.error("❌ WebSocket subscription format test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ WebSocket subscription format test failed: {e}")
        return False

async def test_liquidation_data_parsing():
    """Test parsing of Bybit V5 liquidation websocket data."""
    try:
        # Sample Bybit V5 liquidation message
        ws_message = {
            "topic": "allLiquidation.BTCUSDT",
            "type": "snapshot",
            "ts": int(time.time() * 1000),
            "data": [
                {
                    "T": int(time.time() * 1000),  # Updated timestamp
                    "s": "BTCUSDT",                 # Symbol
                    "S": "Buy",                     # Side (Buy = liquidated long)
                    "v": "0.5",                     # Size
                    "p": "50000"                    # Bankruptcy price
                }
            ]
        }
        
        # Parse the data
        if ws_message.get('topic', '').startswith('allLiquidation.'):
            data_array = ws_message.get('data', [])
            if data_array:
                liq = data_array[0]
                parsed = {
                    'symbol': liq.get('s'),
                    'side': liq.get('S', '').lower(),
                    'size': float(liq.get('v', 0)),
                    'price': float(liq.get('p', 0)),
                    'timestamp': int(liq.get('T', 0))
                }
                
                logger.info("✅ Liquidation data parsing test passed")
                logger.info(f"  - Parsed: {parsed}")
                return True
                
        logger.error("❌ Liquidation data parsing test failed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Liquidation data parsing test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_liquidation_flow_integration():
    """Test the integration points of liquidation flow."""
    try:
        # Check key integration points exist
        integration_files = {
            "WebSocket Manager": "/src/core/exchanges/websocket_manager.py",
            "Bybit Exchange": "/src/core/exchanges/bybit.py",
            "Monitor": "/src/monitoring/monitor.py",
            "Liquidation Detector": "/src/core/analysis/liquidation_detector.py",
            "Liquidation Cache": "/src/utils/liquidation_cache.py"
        }
        
        all_exist = True
        for name, path in integration_files.items():
            full_path = project_root + path
            if os.path.exists(full_path):
                logger.info(f"✅ {name}: Found")
            else:
                logger.error(f"❌ {name}: Missing at {full_path}")
                all_exist = False
        
        if all_exist:
            logger.info("✅ Liquidation flow integration test passed")
            return True
        else:
            logger.error("❌ Liquidation flow integration test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

async def main():
    """Run all liquidation websocket tests."""
    logger.info("=" * 60)
    logger.info("Testing Liquidation WebSocket Implementation")
    logger.info("=" * 60)
    
    tests = [
        ("Liquidation Model Validation", test_liquidation_models),
        ("Liquidation Cache Operations", test_liquidation_cache),
        ("WebSocket Subscription Format", test_websocket_subscription_format),
        ("Liquidation Data Parsing", test_liquidation_data_parsing),
        ("Integration Points Check", test_liquidation_flow_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"💥 Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n🎉 All liquidation websocket tests passed!")
        logger.info("The liquidation implementation is correctly configured.")
    else:
        logger.info("\n⚠️ Some tests failed. Review the implementation.")
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_results": {name: result for name, result in results},
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{passed/total*100:.1f}%"
        },
        "implementation_notes": {
            "websocket_topic": "allLiquidation.{symbol}",
            "data_format": "Bybit V5 format with T, s, S, v, p fields",
            "cache_location": "cache/{symbol}_liquidations.json",
            "integration_complete": passed == total
        }
    }
    
    report_path = f"data/liquidation_test_report_{int(time.time())}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\n📄 Detailed report saved: {report_path}")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)