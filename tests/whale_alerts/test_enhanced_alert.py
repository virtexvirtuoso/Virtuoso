#!/usr/bin/env python3
"""
Test script for the enhanced whale activity alerts with improved formatting.
This test focuses on the enhanced alert formatting with market analysis and price predictions.
"""

import asyncio
import sys
import os
import time
import json
import pytest
from unittest.mock import MagicMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from src.monitoring.alert_manager import AlertManager


class TestEnhancedWhaleAlerts:
    """Test class for enhanced whale activity alerts."""
    
    @pytest.fixture
    def mock_webhook(self):
        """Create a mock Discord webhook that captures the sent data."""
        with patch('src.monitoring.alert_manager.DiscordWebhook') as mock_webhook:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = MagicMock(status_code=200)
            mock_webhook.return_value = mock_instance
            yield mock_webhook, mock_instance
    
    @pytest.fixture
    def alert_manager(self):
        """Create an AlertManager instance for testing."""
        # Set environment variable for Discord webhook
        os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.example.com/webhook'
        
        config = {
            'alerts': {
                'enabled': True,
                'handlers': ['console', 'discord'],
                'discord': {
                    'webhook_url': 'https://discord.example.com/webhook'
                }
            }
        }
        
        # Create alert manager with the test config
        manager = AlertManager(config=config)
        
        # Explicitly set webhook URL and handlers
        manager.discord_webhook_url = 'https://discord.example.com/webhook'
        manager.handlers = {'console': print, 'discord': True}
        
        # Ensure logger is set up
        manager.logger.setLevel('INFO')
        
        return manager
    
    @pytest.mark.asyncio
    async def test_enhanced_whale_accumulation_alert(self, alert_manager, mock_webhook):
        """Test the enhanced whale accumulation alert formatting."""
        mock_webhook_class, mock_webhook_instance = mock_webhook
        
        # Sample whale activity data
        whale_data = {
            'type': 'whale_activity',
            'subtype': 'accumulation',
            'symbol': 'SOLUSDT',
            'data': {
                'net_whale_volume': 0.00,  # Units
                'net_usd_value': 5331499.45,  # USD value
                'whale_bid_orders': 9,
                'whale_ask_orders': 2,
                'whale_bid_usd': 6530846,
                'whale_ask_usd': 1199347,
                'bid_percentage': 0.321,  # 32.1% of book
                'imbalance': 0.69,  # 69% imbalance
                'whale_trades_count': 0,
                'whale_buy_volume': 0,
                'whale_sell_volume': 0,
                'net_trade_volume': 0,
                'trade_imbalance': 0.0,
                'trade_confirmation': False
            }
        }
        
        # Send the alert
        await alert_manager.send_alert(
            level='info',
            message='Whale accumulation alert',
            details=whale_data
        )
        
        # Verify the webhook was called
        assert mock_webhook_class.called
        assert mock_webhook_instance.add_embed.called
        
        # Get the embed data
        called_args = mock_webhook_instance.add_embed.call_args[0][0]
        
        # Verify the alert formatting
        assert 'SOLUSDT' in called_args.description
        assert 'POSITIONING' in called_args.description
        assert '👀' in called_args.description
        assert '$5,331,499.45' in called_args.description
        
        # Verify the fields structure
        field_names = [field.get('name') for field in called_args.fields]
        assert 'Order Book' in field_names
        assert 'Trade Execution' in field_names
        assert '👀 POSITIONING' in field_names
        assert 'Market Analysis' in field_names
        
        # Print the actual embed data for debugging
        print("\nEmbed Data:")
        for field in called_args.fields:
            print(f"- {field.get('name')}: {field.get('value')}")
        
        # Verify market analysis is present with risk level and price prediction
        market_analysis = next((f for f in called_args.fields if f.get('name') == 'Market Analysis'), None)
        assert market_analysis is not None
        assert 'Risk Level:' in market_analysis.get('value')
        assert 'Volume Impact:' in market_analysis.get('value')
        assert 'Support:' in market_analysis.get('value') or 'Resistance:' in market_analysis.get('value')
        
        print("\nTest passed: Enhanced whale alert formatting verified")


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 