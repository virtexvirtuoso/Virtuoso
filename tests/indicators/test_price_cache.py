from src.monitoring.alert_manager import AlertManager

# Create a basic configuration
config = {'monitoring': {'alerts': {}}}

# Create an AlertManager instance
alert_manager = AlertManager(config)

# Check if the attributes exist
attributes = ['_price_cache', '_price_cache_time', '_last_liquidation_alert']
for attr in attributes:
    if hasattr(alert_manager, attr):
        print(f"Success: {attr} is properly initialized!")
    else:
        print(f"Error: {attr} is not initialized.")

# Print the values to verify they're empty dictionaries
print(f"_price_cache value: {alert_manager._price_cache}")
print(f"_price_cache_time value: {alert_manager._price_cache_time}")
print(f"_last_liquidation_alert value: {alert_manager._last_liquidation_alert}") 