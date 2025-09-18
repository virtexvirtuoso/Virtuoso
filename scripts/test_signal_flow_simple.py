#!/usr/bin/env python3
"""
Simple test script to verify BUY/SELL signal flow to Discord
This will test the SignalGenerator.process_signal method directly
"""

import asyncio
import sys
import os
import yaml
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

async def test_signal_flow():
    """Test the complete signal flow from generation to Discord"""
    
    print("🧪 Testing BUY/SELL Signal Flow to Discord")
    print("=" * 50)
    
    try:
        # Load config from yaml
        with open('/home/linuxuser/trading/Virtuoso_ccxt/config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✅ Configuration loaded")
        
        # Import after setting path
        from src.monitoring.alert_manager import AlertManager
        from src.signal_generation.signal_generator import SignalGenerator
        
        # Initialize AlertManager
        alert_manager = AlertManager(config)
        print("✅ AlertManager initialized")
        
        # Initialize SignalGenerator
        signal_generator = SignalGenerator(config, alert_manager)
        print("✅ SignalGenerator initialized")
        
        # Create test signal data (BUY signal above 68% threshold)
        test_signal_data = {
            'symbol': 'BTCUSDT',
            'score': 75.2,  # Above 68% BUY threshold
            'confluence_score': 75.2,
            'signal_type': 'BUY',
            'direction': 'BUY',
            'price': 43250.50,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': str(uuid4())[:8],
            'signal_id': str(uuid4())[:8],
            'reliability': 0.95,
            'components': {
                'orderflow': 78.2,
                'orderbook': 82.1,
                'volume': 71.9,
                'price_structure': 74.4,
                'technical': 73.2,
                'sentiment': 68.8
            },
            'results': {
                'orderflow': {
                    'cvd': 0.85,
                    'imbalance': 0.72,
                    'trade_flow': 0.78,
                    'pressure': 0.81,
                    'smart_money_flow': 0.74,
                    'liquidity': 0.69
                },
                'orderbook': {
                    'depth': 0.79,
                    'imbalance': 0.81,
                    'pressure': 0.74,
                    'liquidity': 0.83,
                    'mpi': 0.77,
                    'spread': 0.72
                },
                'volume': {
                    'relative_volume': 2.3,
                    'volume_delta': 0.67,
                    'adl': 0.71,
                    'cmf': 0.69,
                    'obv': 0.74
                },
                'price_structure': {
                    'support_resistance': 0.71,
                    'trend_position': 0.78,
                    'order_blocks': 0.75,
                    'volume_profile': 0.72
                },
                'technical': {
                    'rsi': 68.2,
                    'macd': 0.45,
                    'cci': 72.1,
                    'williams_r': -28.5,
                    'ao': 0.52
                },
                'sentiment': {
                    'funding_rate': 0.0125,
                    'long_short_ratio': 1.35,
                    'liquidations': 0.65,
                    'volatility': 0.70
                }
            }
        }
        
        print(f"📊 Test BUY Signal Created:")
        print(f"   Symbol: {test_signal_data['symbol']}")
        print(f"   Score: {test_signal_data['score']}% (BUY threshold: 68%)")
        print(f"   Signal Type: {test_signal_data['signal_type']}")
        print(f"   Price: ${test_signal_data['price']}")
        print(f"   Reliability: {test_signal_data['reliability']*100}%")
        print(f"   Transaction ID: {test_signal_data['transaction_id']}")
        
        # Test the signal processing
        print("\n🚀 Processing BUY signal through SignalGenerator.process_signal()...")
        
        await signal_generator.process_signal(test_signal_data)
        
        print("✅ BUY signal processing completed successfully!")
        print("📨 Check your Discord channel for the BUY signal alert")
        
        # Wait a moment before SELL test
        await asyncio.sleep(2)
        
        # Test SELL signal as well
        print("\n" + "="*50)
        print("🧪 Testing SELL Signal...")
        
        sell_signal_data = {
            'symbol': 'ETHUSDT',
            'score': 32.0,  # Below 35% SELL threshold
            'confluence_score': 32.0,
            'signal_type': 'SELL',
            'direction': 'SELL',
            'price': 2845.75,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': str(uuid4())[:8],
            'signal_id': str(uuid4())[:8],
            'reliability': 0.88,
            'components': {
                'orderflow': 28.2,
                'orderbook': 31.1,
                'volume': 35.9,
                'price_structure': 29.4,
                'technical': 33.2,
                'sentiment': 34.8
            },
            'results': {
                'orderflow': {
                    'cvd': -0.65,
                    'imbalance': 0.28,
                    'trade_flow': 0.31
                },
                'orderbook': {
                    'depth': 0.32,
                    'imbalance': 0.29,
                    'pressure': 0.34
                },
                'volume': {
                    'relative_volume': 0.8,
                    'volume_delta': 0.36
                },
                'price_structure': {
                    'support_resistance': 0.31,
                    'trend_position': 0.28
                },
                'technical': {
                    'rsi': 28.2,
                    'macd': -0.45,
                    'cci': -52.1
                },
                'sentiment': {
                    'funding_rate': -0.0085,
                    'long_short_ratio': 0.65
                }
            }
        }
        
        print(f"📊 SELL Signal Created:")
        print(f"   Symbol: {sell_signal_data['symbol']}")
        print(f"   Score: {sell_signal_data['score']}% (SELL threshold: 35%)")
        print(f"   Signal Type: {sell_signal_data['signal_type']}")
        print(f"   Price: ${sell_signal_data['price']}")
        print(f"   Transaction ID: {sell_signal_data['transaction_id']}")
        
        print("\n🚀 Processing SELL signal...")
        await signal_generator.process_signal(sell_signal_data)
        
        print("✅ SELL signal processing completed successfully!")
        print("📨 Check your Discord channel for the SELL signal alert")
        
        print("\n" + "="*60)
        print("🎉 SIGNAL FLOW TEST COMPLETED SUCCESSFULLY!")
        print("✅ Both BUY and SELL signals should now appear in Discord")
        print("🔍 If no alerts appeared, check the service logs:")
        print("   sudo journalctl -u virtuoso-trading.service -f")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error during signal flow test: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting VPS Signal Flow Test...")
    success = asyncio.run(test_signal_flow())
    if success:
        print("\n✅ Test completed successfully! Check Discord for alerts.")
    else:
        print("\n❌ Test failed. Check error messages above.")
    sys.exit(0 if success else 1)