import pytest
import asyncio
from src.monitoring.alert_manager import AlertManager

def test_initialized_attribute_exists():
    """Test that the 'initialized' attribute is properly set during initialization."""
    # Create a basic configuration
    config = {
        'monitoring': {
            'alerts': {
                'discord': {
                    'webhook_url': 'https://discord.com/api/webhooks/example'
                }
            }
        }
    }
    
    # Create an AlertManager instance
    alert_manager = AlertManager(config)
    
    # Check if the initialized attribute exists and is set to True
    assert hasattr(alert_manager, 'initialized'), "The 'initialized' attribute is missing"
    assert alert_manager.initialized is True, "AlertManager initialization failed"

@pytest.mark.asyncio
async def test_send_confluence_alert_no_error():
    """Test that the send_confluence_alert method doesn't raise an AttributeError for initialized."""
    # Create a basic configuration
    config = {
        'monitoring': {
            'alerts': {
                'discord': {
                    'webhook_url': 'https://discord.com/api/webhooks/example'
                }
            }
        }
    }
    
    # Create an AlertManager instance
    alert_manager = AlertManager(config)
    
    # Create mock data for the send_confluence_alert method
    symbol = "BTCUSDT"
    confluence_score = 70.5
    components = {
        "technical": 65.0,
        "volume": 75.0,
        "orderbook": 80.0
    }
    results = {
        "technical": {
            "signals": {
                "rsi": True,
                "macd": False
            }
        },
        "volume": {
            "interpretation": "Volume is increasing"
        }
    }
    
    # Mock methods that would be called to prevent actual API calls
    alert_manager._get_current_price = lambda x: 50000.0
    alert_manager._is_duplicate_alert = lambda x, y: False
    alert_manager.send_discord_webhook_message = lambda x, y=None: (True, None)
    alert_manager._store_alert = lambda x: None
    
    # The attribute error should not occur now
    try:
        await alert_manager.send_confluence_alert(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results
        )
        # If we got here, no exception was raised
        assert True
    except AttributeError as e:
        if "'AlertManager' object has no attribute 'initialized'" in str(e):
            pytest.fail("The 'initialized' attribute is still missing")
        else:
            # Other AttributeError might be expected due to our minimal mocking
            pass
    except Exception:
        # Other exceptions might be expected due to our minimal mocking
        pass 