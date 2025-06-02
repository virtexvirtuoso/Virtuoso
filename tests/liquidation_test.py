#!/usr/bin/env python3
"""
Test script for liquidation alerts.

This script tests the AlertManager's liquidation alert functionality by 
simulating liquidation events and verifying the alert system processes them correctly.
"""

import sys
import os
import asyncio
import time
from unittest.mock import MagicMock, patch
import json

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import required modules
from src.monitoring.alert_manager import AlertManager


class MockWebhook:
    """Mock DiscordWebhook for testing."""

    def __init__(self, url=None):
        self.url = url
        self.embeds = []
        self.content = None
        self.executed = False
        
    def add_embed(self, embed):
        self.embeds.append(embed)
        return self

    def execute(self):
        """Mock execution that returns a success status code."""
        self.executed = True
        response = MagicMock()
        response.status_code = 200
        return response


async def test_liquidation_alert():
    """Test liquidation alert functionality."""
    print("\n=== Testing Liquidation Alert System ===")
    
    # Create test configuration with both threshold and webhook settings
    config = {
        'monitoring': {
            'alerts': {
                'liquidation': {
                    'threshold': 250000,  # $250k threshold
                    'cooldown': 10  # 10 seconds cooldown for testing
                },
                'discord': {
                    'webhook_url': 'https://discord.example.com/webhook'
                }
            }
        }
    }

    # Track Discord webhook calls
    webhook_calls = []
    mock_webhook_instances = []
    
    # Mock the DiscordWebhook class
    class TestMockWebhook(MockWebhook):
        def __init__(self, url=None, **kwargs):
            super().__init__(url)
            mock_webhook_instances.append(self)
            webhook_calls.append({'url': url})
            
        def add_embed(self, embed):
            webhook_calls[-1]['embed'] = embed
            return super().add_embed(embed)
            
        def execute(self):
            webhook_calls[-1]['executed'] = True
            return super().execute()

    # Create the AlertManager instance with patched Discord webhook
    with patch('src.monitoring.alert_manager.DiscordWebhook', TestMockWebhook):
        alert_manager = AlertManager(config=config)
        alert_manager.discord_webhook_url = 'https://discord.example.com/webhook'
        alert_manager.handlers = ['discord']
        alert_manager.alert_handlers = {'discord': alert_manager._send_discord_alert}
        
        # Force initialize handlers to ensure Discord handler is registered
        alert_manager._initialize_handlers()
        
        print(f"Handlers after initialization: {alert_manager.handlers}")
        print(f"Alert handlers after initialization: {list(alert_manager.alert_handlers.keys())}")

        # Test various liquidation scenarios
        test_cases = [
            # 1. Liquidation above threshold (should trigger alert)
            {
                'name': "Large LONG liquidation",
                'symbol': 'BTCUSDT',
                'data': {
                    'symbol': 'BTCUSDT',
                    'side': 'BUY',  # BUY means LONG position being liquidated
                    'price': 68500,
                    'size': 5.0,  # 5 BTC (value = $342,500 > threshold)
                    'timestamp': int(time.time() * 1000)
                },
                'should_alert': True
            },
            # 2. Small liquidation below threshold (should not trigger alert)
            {
                'name': "Small liquidation below threshold",
                'symbol': 'BTCUSDT',
                'data': {
                    'symbol': 'BTCUSDT',
                    'side': 'SELL',  # SELL means SHORT position being liquidated
                    'price': 68500,
                    'size': 0.5,  # 0.5 BTC (value = $34,250 < threshold)
                    'timestamp': int(time.time() * 1000)
                },
                'should_alert': False
            },
            # 3. Large liquidation of altcoin
            {
                'name': "Large SOL liquidation",
                'symbol': 'SOLUSDT',
                'data': {
                    'symbol': 'SOLUSDT',
                    'side': 'SELL',
                    'price': 150,
                    'size': 2000,  # 2000 SOL (value = $300,000 > threshold)
                    'timestamp': int(time.time() * 1000)
                },
                'should_alert': True
            }
        ]
        
        # Test each case
        for i, case in enumerate(test_cases):
            print(f"\nTesting: {case['name']}")
            
            # Clear previous webhook calls for this test
            webhook_calls_before = len(webhook_calls)
            
            # Call the method that processes liquidation data
            await alert_manager.check_liquidation_threshold(case['symbol'], case['data'])
            
            # Give a moment for async processing
            await asyncio.sleep(0.1)
            
            # Calculate USD value for verification
            usd_value = case['data']['price'] * case['data']['size']
            print(f"Liquidation value: ${usd_value:,.2f} (Threshold: ${config['monitoring']['alerts']['liquidation']['threshold']:,.2f})")
            
            # Count new webhook calls for this test
            new_webhook_calls = webhook_calls[webhook_calls_before:]
            
            # Verify alert was sent (or not) as expected
            if case['should_alert']:
                assert len(new_webhook_calls) > 0, f"Failed to send alert for {case['name']} (${usd_value:,.2f})"
                print(f"✅ Alert correctly sent for {case['name']}")
                
                # Find executed webhook call with embed
                executed_calls = [call for call in new_webhook_calls if call.get('executed', False)]
                assert len(executed_calls) > 0, "Webhook was created but not executed"
                
                # Get the embed data from the most recent executed call
                embed = executed_calls[-1].get('embed')
                assert embed is not None, "No embed found in webhook call"
                
                # Verify the embed content
                assert case['symbol'] in embed.title, f"Symbol not in title: {embed.title}"
                assert "LIQUIDATION" in embed.title, f"LIQUIDATION not in title: {embed.title}"
                
                # Verify the correct position type is in the title
                expected_position = "LONG" if case['data']['side'] == 'BUY' else "SHORT"
                assert expected_position in embed.title, f"Expected position type {expected_position} not in title: {embed.title}"
                
                # Verify USD value is in the description
                usd_formatted = f"${usd_value:,.2f}"
                assert usd_formatted in embed.description, f"USD value {usd_formatted} not found in description"
                
                # Reset cooldown timer to allow next test
                alert_manager._last_liquidation_alert[case['symbol']] = 0
            else:
                # For cases that shouldn't trigger alerts, verify no webhook calls were made
                assert len(new_webhook_calls) == 0, f"Alert incorrectly sent for {case['name']} (${usd_value:,.2f})"
                print(f"✅ No alert sent for {case['name']} as expected")
        
        print("\n✅ All liquidation alert tests passed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(test_liquidation_alert())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 