from src.monitoring.alert_manager import AlertManager

# Create a more complete test configuration
config = {
    'monitoring': {
        'alerts': {
            'discord': {
                'webhook_url': 'https://discord.com/api/webhooks/example'
            },
            'thresholds': {
                'liquidation': 50000,
                'buy': 70,
                'sell': 30
            },
            'cooldowns': {
                'liquidation': 120,
                'large_order': 180,
                'alert': 30
            }
        }
    }
}

# Create an AlertManager instance with the test config
alert_manager = AlertManager(config)

# Define all the attributes we expect to find in the AlertManager
expected_attributes = [
    # Basic attributes
    'config', 'database', 'alerts', 'logger', 'handlers', 'alert_handlers',
    'webhook', 'discord_webhook_url', 'buy_threshold', 'sell_threshold',
    
    # Private attributes
    '_client_session', '_last_alert_times', '_deduplication_window', 
    '_alert_hashes', '_last_liquidation_alert', '_last_large_order_alert',
    '_last_alert', '_price_cache', '_price_cache_time', '_alerts',
    '_alert_stats', '_ohlcv_cache', '_market_data_cache', '_last_ohlcv_update',
    
    # Configuration attributes
    'alert_levels', 'alert_throttle', 'liquidation_threshold',
    'liquidation_cooldown', 'large_order_cooldown', 'discord_client'
]

# Check if all expected attributes exist
missing_attributes = []
for attr in expected_attributes:
    if not hasattr(alert_manager, attr):
        missing_attributes.append(attr)

if missing_attributes:
    print(f"Error: The following attributes are missing: {', '.join(missing_attributes)}")
else:
    print("Success: All expected attributes are properly initialized!")

# Verify that config values were properly loaded
print("\nConfiguration values:")
print(f"discord_webhook_url: {alert_manager.discord_webhook_url}")
print(f"liquidation_threshold: {alert_manager.liquidation_threshold}")
print(f"buy_threshold: {alert_manager.long_threshold}")
print(f"sell_threshold: {alert_manager.short_threshold}")
print(f"liquidation_cooldown: {alert_manager.liquidation_cooldown}")
print(f"large_order_cooldown: {alert_manager.large_order_cooldown}")
print(f"alert_throttle: {alert_manager.alert_throttle}")

# Verify structure of dictionary attributes
dict_attributes = [
    ('_last_alert_times', {}),
    ('_alert_hashes', {}),
    ('_last_liquidation_alert', {}),
    ('_last_large_order_alert', {}),
    ('_last_alert', {}),
    ('_price_cache', {}),
    ('_price_cache_time', {}),
    ('_ohlcv_cache', {}),
    ('_market_data_cache', {}),
    ('_last_ohlcv_update', {})
]

print("\nDictionary attributes:")
for attr_name, expected_value in dict_attributes:
    attr_value = getattr(alert_manager, attr_name)
    print(f"{attr_name}: {type(attr_value).__name__}, Empty: {len(attr_value) == 0}")

# Verify structure of list attributes
print("\nAlert levels:")
print(alert_manager.alert_levels)

# Verify structure of alert_stats
print("\nAlert stats:")
for key, value in alert_manager._alert_stats.items():
    print(f"  {key}: {value}") 