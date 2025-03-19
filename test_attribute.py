from src.monitoring.alert_manager import AlertManager

# Create a basic configuration
config = {'monitoring': {'alerts': {}}}

# Create an AlertManager instance
alert_manager = AlertManager(config)

# Check if the attribute exists
if hasattr(alert_manager, '_last_liquidation_alert'):
    print("Success: _last_liquidation_alert is properly initialized!")
else:
    print("Error: _last_liquidation_alert is not initialized.")

# Print the value to verify it's an empty dictionary
print(f"Value: {alert_manager._last_liquidation_alert}") 