import asyncio
import json
from src.monitoring.alert_manager import AlertManager

async def test_liquidation_alert():
    # Create a basic configuration
    config = {'monitoring': {'alerts': {}}}
    
    # Create an AlertManager instance
    alert_manager = AlertManager(config)
    
    # Create sample liquidation data
    liquidation_data = {
        'symbol': 'TRUMPUSDT',
        'side': 'Buy',
        'price': 13.002,
        'size': 1.3,
        'timestamp': 1741271608433
    }
    
    # Call the method that was failing
    await alert_manager.check_liquidation_threshold('TRUMPUSDT', liquidation_data)
    
    print('Test completed successfully')

# Run the test
if __name__ == "__main__":
    asyncio.run(test_liquidation_alert()) 