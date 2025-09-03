#!/usr/bin/env python3
"""
Test script to verify alert system is working
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.alert_manager import AlertManager
import yaml

async def test_alerts():
    """Test the alert system with a simulated BUY signal"""
    
    # Load config directly
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create alert manager
    alert_manager = AlertManager(config)
    
    print("Testing alert system...")
    
    # Test 1: Simple alert
    print("\n1. Testing simple alert...")
    await alert_manager.send_alert(
        level="INFO",
        message="TEST: Alert system is working!",
        details={"test": True, "source": "test_script"}
    )
    print("✅ Simple alert sent")
    
    # Test 2: Simulated BUY signal alert
    print("\n2. Testing BUY signal alert...")
    try:
        await alert_manager.send_confluence_alert(
            symbol="BTCUSDT",
            confluence_score=75.5,  # Above buy threshold
            components={
                "technical": 72.0,
                "volume": 78.0,
                "orderbook": 76.5,
                "orderflow": 74.0,
                "sentiment": 73.5,
                "price_structure": 77.0
            },
            results={},
            reliability=1.0,
            buy_threshold=71,
            sell_threshold=35,
            price=58500.50,
            transaction_id="TEST001",
            signal_id="SIG001"
        )
        print("✅ BUY signal alert sent")
    except Exception as e:
        print(f"❌ Error sending BUY signal alert: {e}")
    
    # Test 3: Simulated SELL signal alert
    print("\n3. Testing SELL signal alert...")
    try:
        await alert_manager.send_confluence_alert(
            symbol="ETHUSDT",
            confluence_score=32.5,  # Below sell threshold
            components={
                "technical": 30.0,
                "volume": 28.0,
                "orderbook": 35.5,
                "orderflow": 33.0,
                "sentiment": 31.5,
                "price_structure": 37.0
            },
            results={},
            reliability=1.0,
            buy_threshold=71,
            sell_threshold=35,
            price=2250.75,
            transaction_id="TEST002",
            signal_id="SIG002"
        )
        print("✅ SELL signal alert sent")
    except Exception as e:
        print(f"❌ Error sending SELL signal alert: {e}")
    
    print("\n✅ Alert tests completed!")
    print("Check your Discord channel for the alerts.")
    
    # Give time for alerts to be sent
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_alerts())