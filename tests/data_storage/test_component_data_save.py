import asyncio
import os
import json
from datetime import datetime
from src.monitoring.alert_manager import AlertManager

def test_save_component_data():
    """Test the updated _save_component_data method."""
    print("Testing component data save functionality")
    
    # Initialize the AlertManager
    alert_manager = AlertManager({})
    
    # Test data
    symbol = "BTCUSDT"
    components = {
        "volume": 75.5,
        "technical": 73.2,
        "orderflow": 68.7,
        "orderbook": 82.3,
        "sentiment": 69.5,
        "price_structure": 77.2
    }
    results = {
        "volume": {
            "score": 75.5,
            "interpretation": "Strong Bullish Volume - Heavy Buying Flow 📈"
        },
        "technical": {
            "score": 73.2,
            "interpretation": "Bullish Momentum - Trend Continuation 📈"
        }
    }
    
    # Test with different signal types
    signal_types = ["BUY", "SELL", "NEUTRAL"]
    
    for signal_type in signal_types:
        filepath = alert_manager._save_component_data(symbol, components, results, signal_type)
        print(f"Saved {signal_type} signal data to: {filepath}")
        
        # Verify the saved file
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"  - File contains signal_type: {data.get('signal_type')}")
                print(f"  - File contains components: {len(data.get('components', {}))} components")
        else:
            print(f"  - Failed to save file for {signal_type}")

if __name__ == "__main__":
    test_save_component_data() 