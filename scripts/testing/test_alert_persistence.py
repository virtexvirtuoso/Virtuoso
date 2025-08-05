#!/usr/bin/env python3
"""Test script for alert persistence functionality."""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.alert_storage import AlertStorage
from src.monitoring.alert_manager import AlertManager
from src.core.config.config_manager import ConfigManager


async def test_alert_persistence():
    """Test alert persistence to database."""
    print("🧪 Testing Alert Persistence System")
    print("=" * 50)
    
    # Initialize config
    config_manager = ConfigManager()
    config = config_manager._config
    
    # Initialize alert storage directly
    print("\n1. Testing AlertStorage directly...")
    storage = AlertStorage()
    
    # Test storing an alert
    test_alert = {
        'alert_id': f'test_{int(time.time() * 1000)}',
        'alert_type': 'high_confluence',
        'symbol': 'BTCUSDT',
        'severity': 'WARNING',
        'title': 'High Confluence Score Alert',
        'message': 'BTC showing strong bullish signals with confluence score of 85',
        'confluence_score': 85.5,
        'price': 103456.78,
        'volume': 1234567890,
        'change_24h': 2.45,
        'timestamp': int(time.time() * 1000),
        'sent_to_discord': True,
        'details': {
            'technical_score': 88,
            'volume_score': 82,
            'orderflow_score': 90,
            'sentiment_score': 85,
            'orderbook_score': 78,
            'price_structure_score': 87
        }
    }
    
    stored = storage.store_alert(test_alert)
    print(f"✅ Alert stored: {stored}")
    
    # Test retrieving alerts
    print("\n2. Testing alert retrieval...")
    alerts = storage.get_alerts(limit=10)
    print(f"Retrieved {len(alerts)} alerts")
    
    if alerts:
        latest = alerts[0]
        print(f"\nLatest alert:")
        print(f"  - ID: {latest.get('alert_id')}")
        print(f"  - Symbol: {latest.get('symbol')}")
        print(f"  - Type: {latest.get('alert_type')}")
        print(f"  - Score: {latest.get('confluence_score')}")
        print(f"  - Sent to Discord: {latest.get('sent_to_discord')}")
    
    # Test alert stats
    print("\n3. Testing alert statistics...")
    stats = storage.get_alert_stats(hours=24)
    print(f"Stats for last 24 hours:")
    print(f"  - Total alerts: {stats['total_alerts']}")
    print(f"  - By type: {stats['alerts_by_type']}")
    print(f"  - By severity: {stats['alerts_by_severity']}")
    print(f"  - Top symbols: {stats['top_symbols']}")
    
    # Test AlertManager integration
    print("\n4. Testing AlertManager integration...")
    alert_manager = AlertManager(config)
    
    # Check if storage was initialized
    if alert_manager.alert_storage:
        print("✅ AlertManager has alert storage initialized")
        
        # Send a test alert
        await alert_manager.send_alert(
            level="INFO",
            message="Test alert for persistence",
            details={
                'type': 'test',
                'symbol': 'ETHUSDT',
                'price': 5678.90,
                'confluence_score': 72.3,
                'timestamp': time.time()
            }
        )
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Retrieve through AlertManager
        manager_alerts = alert_manager.get_alerts(limit=5)
        print(f"\nRetrieved {len(manager_alerts)} alerts through AlertManager")
        
        if manager_alerts:
            test_alert = manager_alerts[0]
            print(f"Latest alert from AlertManager:")
            print(f"  - Level: {test_alert.get('level', test_alert.get('severity'))}")
            print(f"  - Message: {test_alert.get('message', '')[:50]}...")
            print(f"  - Has alert_id: {'alert_id' in test_alert}")
    else:
        print("❌ AlertManager storage not initialized")
    
    # Test cleanup
    print("\n5. Testing cleanup (keeping last 7 days)...")
    deleted = storage.cleanup_old_alerts(days=7)
    print(f"Cleaned up {deleted} old alerts")
    
    print("\n✅ Alert persistence test completed!")
    print("\nTo verify in the mobile dashboard:")
    print("1. Ensure the application is running with these changes")
    print("2. Access http://your-vps-ip:8080/dashboard")
    print("3. Navigate to the Alerts tab")
    print("4. You should see historical alerts from the database")


if __name__ == "__main__":
    asyncio.run(test_alert_persistence())