#!/usr/bin/env python3
"""
Test Discord Webhook Retry Logic

This script tests the improved Discord webhook retry functionality
to ensure it properly handles connection errors and implements
exponential backoff.
"""

import asyncio
import logging
import os
import sys
import time
from unittest.mock import Mock, patch
import requests
from typing import Dict, Any

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.monitoring.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_config() -> Dict[str, Any]:
    """Create a test configuration with Discord webhook retry settings."""
    return {
        'monitoring': {
            'alerts': {
                'enabled': True,
                'channels': ['discord'],
                'discord_webhook': {
                    'max_retries': 3,
                    'initial_retry_delay': 0.5,  # Shorter delay for testing
                    'timeout_seconds': 10,
                    'exponential_backoff': True,
                    'fallback_enabled': True,
                    'recoverable_status_codes': [429, 500, 502, 503, 504]
                }
            }
        }
    }

async def test_connection_error_retry():
    """Test that connection errors trigger retry logic."""
    logger.info("Testing connection error retry logic...")
    
    config = create_test_config()
    alert_manager = AlertManager(config)
    
    # Set a fake webhook URL (override environment)
    alert_manager.discord_webhook_url = "https://discord.com/api/webhooks/fake/webhook"
    
    # Mock the DiscordWebhook to raise connection errors
    with patch('src.monitoring.alert_manager.DiscordWebhook') as mock_webhook_class:
        mock_webhook = Mock()
        mock_webhook_class.return_value = mock_webhook
        
        # Simulate connection error (like RemoteDisconnected)
        mock_webhook.execute.side_effect = requests.exceptions.ConnectionError(
            "('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"
        )
        
        # Create test alert
        test_alert = {
            'level': 'INFO',
            'message': 'Test connection error handling',
            'details': {'test': 'data'},
            'timestamp': time.time()
        }
        
        start_time = time.time()
        
        # This should attempt retries and eventually fail gracefully
        await alert_manager._send_discord_alert(test_alert)
        
        end_time = time.time()
        
        # Verify retries were attempted (should take at least retry_delay * num_retries)
        expected_min_time = 0.5 + 1.0 + 2.0  # 0.5 + 1.0 + 2.0 (exponential backoff)
        logger.info(f"Test took {end_time - start_time:.2f} seconds (expected min: {expected_min_time:.2f})")
        
        # Verify webhook was called the expected number of times (max_retries)
        assert mock_webhook.execute.call_count == 3, f"Expected 3 calls, got {mock_webhook.execute.call_count}"
        
        logger.info("✅ Connection error retry test passed")

async def test_recoverable_status_codes():
    """Test that recoverable status codes trigger retries."""
    logger.info("Testing recoverable status code retry logic...")
    
    config = create_test_config()
    alert_manager = AlertManager(config)
    # Override webhook URL to prevent environment variable use
    alert_manager.discord_webhook_url = "https://discord.com/api/webhooks/fake/webhook"
    
    with patch('src.monitoring.alert_manager.DiscordWebhook') as mock_webhook_class:
        mock_webhook = Mock()
        mock_webhook_class.return_value = mock_webhook
        
        # Mock response with 429 (rate limited) status code
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_webhook.execute.return_value = mock_response
        
        test_alert = {
            'level': 'WARNING',
            'message': 'Test rate limit handling',
            'details': {},
            'timestamp': time.time()
        }
        
        await alert_manager._send_discord_alert(test_alert)
        
        # Should retry for recoverable status codes
        assert mock_webhook.execute.call_count == 3, f"Expected 3 calls, got {mock_webhook.execute.call_count}"
        
        logger.info("✅ Recoverable status code retry test passed")

async def test_successful_send_no_retry():
    """Test that successful sends don't trigger unnecessary retries."""
    logger.info("Testing successful send without retries...")
    
    config = create_test_config()
    alert_manager = AlertManager(config)
    # Override webhook URL to prevent environment variable use
    alert_manager.discord_webhook_url = "https://discord.com/api/webhooks/fake/webhook"
    
    with patch('src.monitoring.alert_manager.DiscordWebhook') as mock_webhook_class:
        mock_webhook = Mock()
        mock_webhook_class.return_value = mock_webhook
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_webhook.execute.return_value = mock_response
        
        test_alert = {
            'level': 'INFO',
            'message': 'Test successful send',
            'details': {},
            'timestamp': time.time()
        }
        
        await alert_manager._send_discord_alert(test_alert)
        
        # Should only call once for successful send
        assert mock_webhook.execute.call_count == 1, f"Expected 1 call, got {mock_webhook.execute.call_count}"
        
        logger.info("✅ Successful send test passed")

async def test_fallback_mechanism():
    """Test that fallback mechanism works when discord_webhook fails."""
    logger.info("Testing fallback mechanism...")
    
    config = create_test_config()
    alert_manager = AlertManager(config)
    alert_manager.discord_webhook_url = "https://discord.com/api/webhooks/fake/webhook"
    
    with patch('src.monitoring.alert_manager.DiscordWebhook') as mock_webhook_class, \
         patch('aiohttp.ClientSession') as mock_session_class:
        
        # Mock discord_webhook to always fail
        mock_webhook = Mock()
        mock_webhook_class.return_value = mock_webhook
        mock_webhook.execute.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # Mock aiohttp session for fallback
        mock_session_instance = Mock()
        mock_post_context = Mock()
        mock_response = Mock()
        mock_response.status = 200
        
        # Set up the async context manager chain properly
        mock_post_context.__aenter__ = Mock(return_value=mock_response)
        mock_post_context.__aexit__ = Mock(return_value=None)
        mock_session_instance.post = Mock(return_value=mock_post_context)
        
        mock_session_context = Mock()
        mock_session_context.__aenter__ = Mock(return_value=mock_session_instance)
        mock_session_context.__aexit__ = Mock(return_value=None)
        mock_session_class.return_value = mock_session_context
        
        test_alert = {
            'level': 'ERROR',
            'message': 'Test fallback mechanism',
            'details': {'test': 'fallback'},
            'timestamp': time.time()
        }
        
        await alert_manager._send_discord_alert(test_alert)
        
        # Verify discord_webhook was tried and failed
        assert mock_webhook.execute.call_count == 3, f"Expected 3 webhook calls, got {mock_webhook.execute.call_count}"
        
        # Verify fallback was attempted
        assert mock_session_instance.post.called, "Fallback HTTP request should have been made"
        
        logger.info("✅ Fallback mechanism test passed")

async def test_configuration_values():
    """Test that configuration values are properly loaded."""
    logger.info("Testing configuration loading...")
    
    config = create_test_config()
    alert_manager = AlertManager(config)
    
    # Override webhook URL to prevent using environment
    alert_manager.discord_webhook_url = "https://discord.com/api/webhooks/fake/webhook"
    
    # Check that config values are loaded correctly
    assert alert_manager.webhook_max_retries == 3, f"Expected max_retries=3, got {alert_manager.webhook_max_retries}"
    assert alert_manager.webhook_initial_retry_delay == 0.5, f"Expected initial_retry_delay=0.5, got {alert_manager.webhook_initial_retry_delay}"
    assert alert_manager.webhook_timeout == 10, f"Expected timeout=10, got {alert_manager.webhook_timeout}"
    assert alert_manager.webhook_exponential_backoff == True, f"Expected exponential_backoff=True, got {alert_manager.webhook_exponential_backoff}"
    assert alert_manager.webhook_fallback_enabled == True, f"Expected fallback_enabled=True, got {alert_manager.webhook_fallback_enabled}"
    assert 429 in alert_manager.webhook_recoverable_status_codes, "Expected 429 in recoverable status codes"
    
    logger.info("✅ Configuration test passed")

async def run_all_tests():
    """Run all webhook retry tests."""
    logger.info("Starting Discord webhook retry tests...")
    
    try:
        await test_configuration_values()
        await test_connection_error_retry()
        await test_recoverable_status_codes() 
        await test_successful_send_no_retry()
        await test_fallback_mechanism()
        
        logger.info("🎉 All Discord webhook retry tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1) 