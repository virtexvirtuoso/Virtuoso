#!/usr/bin/env python3
"""
Test script to verify BUY/SELL signal flow to Discord
This will create a mock signal above 68% threshold and test the complete flow
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt')

from src.signal_generation.signal_generator import SignalGenerator
from src.monitoring.alert_manager import AlertManager
from src.utils.config_loader import load_config

async def test_signal_flow():
    """Test the complete signal flow from generation to Discord"""
    
    print("🧪 Testing BUY/SELL Signal Flow to Discord")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        print("✅ Configuration loaded")
        
        # Initialize AlertManager
        alert_manager = AlertManager(config)
        print("✅ AlertManager initialized")
        
        # Initialize SignalGenerator
        signal_generator = SignalGenerator(config, alert_manager)
        print("✅ SignalGenerator initialized")
        
        # Create test signal data (BUY signal above 68% threshold)
        test_signal_data = {
            'symbol': 'BTCUSDT',
            'score': 72.5,  # Above 68% BUY threshold
            'confluence_score': 72.5,
            'signal_type': 'BUY',
            'direction': 'BUY',
            'price': 43250.50,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': str(uuid4())[:8],
            'signal_id': str(uuid4())[:8],
            'reliability': 0.95,
            'components': {
                'orderflow': 75.2,
                'orderbook': 78.1,
                'volume': 68.9,
                'price_structure': 69.4,
                'technical': 71.2,
                'sentiment': 70.8
            },
            'results': {
                'orderflow': {
                    'cvd': 0.85,
                    'imbalance': 0.72,
                    'trade_flow': 0.68
                },
                'orderbook': {
                    'depth': 0.79,
                    'imbalance': 0.81,
                    'pressure': 0.74
                },
                'volume': {
                    'relative_volume': 2.3,
                    'volume_delta': 0.67
                },
                'price_structure': {
                    'support_resistance': 0.71,
                    'trend_position': 0.68
                },
                'technical': {
                    'rsi': 65.2,
                    'macd': 0.45,
                    'cci': 52.1
                },
                'sentiment': {
                    'funding_rate': 0.0125,
                    'long_short_ratio': 1.35
                }
            }
        }
        
        print(f"📊 Test Signal Created:")
        print(f"   Symbol: {test_signal_data['symbol']}")
        print(f"   Score: {test_signal_data['score']}% (BUY threshold: 68%)")
        print(f"   Signal Type: {test_signal_data['signal_type']}")
        print(f"   Price: ${test_signal_data['price']}")
        print(f"   Reliability: {test_signal_data['reliability']*100}%")
        
        # Test the signal processing
        print("\n🚀 Processing signal through SignalGenerator.process_signal()...")
        
        await signal_generator.process_signal(test_signal_data)
        
        print("✅ Signal processing completed successfully!")
        print("📨 Check your Discord channel for the BUY signal alert")
        
        # Test SELL signal as well
        print("\n" + "="*50)
        print("🧪 Testing SELL Signal...")
        
        sell_signal_data = test_signal_data.copy()
        sell_signal_data.update({
            'score': 30.0,  # Below 35% SELL threshold
            'confluence_score': 30.0,
            'signal_type': 'SELL',
            'direction': 'SELL',
            'price': 43100.25,
            'transaction_id': str(uuid4())[:8],
            'signal_id': str(uuid4())[:8],
        })
        
        print(f"📊 SELL Signal Created:")
        print(f"   Score: {sell_signal_data['score']}% (SELL threshold: 35%)")
        print(f"   Signal Type: {sell_signal_data['signal_type']}")
        
        print("\n🚀 Processing SELL signal...")
        await signal_generator.process_signal(sell_signal_data)
        
        print("✅ SELL signal processing completed successfully!")
        print("📨 Check your Discord channel for the SELL signal alert")
        
        print("\n" + "="*50)
        print("🎉 Signal Flow Test Completed Successfully!")
        print("✅ Both BUY and SELL signals should appear in Discord")
        print("🔍 Check the logs above for any errors")
        
    except Exception as e:
        print(f"❌ Error during signal flow test: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    print("Starting signal flow test...")
    success = asyncio.run(test_signal_flow())
    sys.exit(0 if success else 1)