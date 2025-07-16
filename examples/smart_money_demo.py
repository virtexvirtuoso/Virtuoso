#!/usr/bin/env python3
"""
Smart Money Monitoring System Demo

This script demonstrates the smart money detection system and shows
how it complements the existing whale detection system.

Features demonstrated:
1. Smart Money Event Detection
2. Discord Alert Formatting
3. Sophistication Scoring
4. Pattern Recognition
"""

import asyncio
import logging
import time
import yaml
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock market data for demonstration
MOCK_MARKET_DATA = {
    'BTCUSDT': {
        'ticker': {
            'last': 97450.0,
            'baseVolume': 25000.0,
            'change24h': 2.3
        },
        'orderbook': {
            'bids': [
                [97440.0, 2.5], [97435.0, 1.8], [97430.0, 3.2], [97425.0, 1.5],
                [97420.0, 2.1], [97415.0, 1.9], [97410.0, 2.8], [97405.0, 1.3],
                [97400.0, 4.5], [97395.0, 2.2], [97390.0, 1.7], [97385.0, 3.1]
            ],
            'asks': [
                [97450.0, 1.2], [97455.0, 2.1], [97460.0, 1.8], [97465.0, 2.5],
                [97470.0, 1.4], [97475.0, 2.3], [97480.0, 1.6], [97485.0, 2.0],
                [97490.0, 1.9], [97495.0, 2.7], [97500.0, 1.5], [97505.0, 2.4]
            ]
        },
        'open_interest': 1250000000.0
    },
    'ETHUSDT': {
        'ticker': {
            'last': 3420.5,
            'baseVolume': 45000.0,
            'change24h': -1.2
        },
        'orderbook': {
            'bids': [
                [3419.0, 12.5], [3418.5, 8.3], [3418.0, 15.2], [3417.5, 6.8],
                [3417.0, 11.1], [3416.5, 9.4], [3416.0, 13.7], [3415.5, 7.2],
                [3415.0, 18.5], [3414.5, 10.1], [3414.0, 14.3], [3413.5, 8.9]
            ],
            'asks': [
                [3420.5, 5.2], [3421.0, 8.7], [3421.5, 6.4], [3422.0, 11.3],
                [3422.5, 4.8], [3423.0, 9.1], [3423.5, 7.6], [3424.0, 12.4],
                [3424.5, 5.9], [3425.0, 10.8], [3425.5, 6.7], [3426.0, 13.2]
            ]
        },
        'open_interest': 850000000.0
    }
}

async def demo_smart_money_detection():
    """Demonstrate smart money detection capabilities."""
    print("🧠 Smart Money Detection System Demo")
    print("=" * 50)
    
    try:
        # Import the smart money detector
        from src.monitoring.smart_money_detector import SmartMoneyDetector, SmartMoneyEventType
        
        # Load configuration
        try:
            with open('config/config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                
            # Extract smart money config from nested structure
            smart_money_config = config.get('monitoring', {}).get('alerts', {}).get('smart_money_detection', {})
            if not smart_money_config:
                raise KeyError("smart_money_detection config not found")
                
        except (FileNotFoundError, KeyError):
            print("⚠️  Config file not found or smart money config missing, using default configuration")
            smart_money_config = {
                'enabled': True,
                'min_sophistication_score': 4.0,  # Lower for demo to see more events
                'min_confidence': 0.5,            # Lower for demo
                'cooldown_minutes': 1,            # Shorter for demo
                'max_alerts_per_hour': 50,
                'orderflow_imbalance_threshold': 0.5,  # Lower to trigger more events
                'volume_spike_multiplier': 1.8,       # Lower to trigger more events
                'depth_change_threshold': 0.10,       # Lower to trigger more events
                'position_change_threshold': 0.08     # Lower to trigger more events
            }
            
            # Create config structure for detector
            config = {'smart_money_detection': smart_money_config}
        
        # Initialize detector
        detector = SmartMoneyDetector(config, logger)
        print(f"✅ SmartMoneyDetector initialized")
        print(f"📊 Configuration: min_sophistication={smart_money_config['min_sophistication_score']}")
        print()
        
        # Simulate detection over multiple time periods
        print("🔄 Simulating market data analysis...")
        print()
        
        for i, (symbol, market_data) in enumerate(MOCK_MARKET_DATA.items()):
            print(f"📈 Analyzing {symbol}...")
            
            # Simulate multiple data points to build history
            for j in range(15):  # Build up historical data
                # Slightly modify data each iteration to simulate real market movement
                modified_data = simulate_market_movement(market_data, j)
                
                # Analyze for smart money patterns
                events = await detector.analyze_market_data(symbol, modified_data)
                
                if events:
                    print(f"   🎯 Detected {len(events)} smart money events")
                    
                    for event in events:
                        print(f"      • {event.event_type.value}: "
                              f"sophistication={event.sophistication_score:.1f}/10, "
                              f"confidence={event.confidence:.1%}")
                        
                        # Show event details
                        if event.event_type == SmartMoneyEventType.ORDERFLOW_IMBALANCE:
                            side = event.data.get('side', 'unknown')
                            imbalance = event.data.get('imbalance', 0)
                            print(f"        → {side.upper()} side imbalance: {abs(imbalance):.1%}")
                            
                        elif event.event_type == SmartMoneyEventType.VOLUME_SPIKE:
                            spike_ratio = event.data.get('spike_ratio', 0)
                            print(f"        → Volume spike: {spike_ratio:.1f}x normal")
                            
                        elif event.event_type == SmartMoneyEventType.DEPTH_CHANGE:
                            side = event.data.get('side', 'unknown')
                            change = event.data.get('change_ratio', 0)
                            print(f"        → {side.upper()} depth change: {change:.1%}")
                            
                        elif event.event_type == SmartMoneyEventType.POSITION_CHANGE:
                            direction = event.data.get('direction', 'unknown')
                            change = event.data.get('change_value', 0)
                            print(f"        → Position {direction}: {change:,.0f}")
                
                # Small delay to simulate real-time processing
                await asyncio.sleep(0.1)
            
            print()
        
        # Show detection statistics
        stats = detector.get_statistics()
        print("📊 Detection Statistics:")
        print(f"   • Total detections: {stats['detection_stats']['total_detections']}")
        print(f"   • Alerts sent: {stats['detection_stats']['alerts_sent']}")
        print(f"   • Active symbols: {stats['active_symbols']}")
        print()
        
        # Show sophistication distribution
        if stats['sophistication_distribution']:
            print("🎯 Sophistication Level Distribution:")
            for level, count in stats['sophistication_distribution'].items():
                print(f"   • {level.upper()}: {count} events")
            print()
        
        # Show event type distribution
        if stats['event_type_counts']:
            print("📈 Event Type Distribution:")
            for event_type, count in stats['event_type_counts'].items():
                print(f"   • {event_type.replace('_', ' ').title()}: {count} events")
            print()
        
    except ImportError as e:
        print(f"❌ Could not import SmartMoneyDetector: {e}")
        print("   Make sure the smart money detector module is properly installed.")
        return
    
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return

def simulate_market_movement(base_data: Dict[str, Any], iteration: int) -> Dict[str, Any]:
    """Simulate market data movement for demonstration."""
    import copy
    import random
    
    data = copy.deepcopy(base_data)
    
    # Simulate price movement
    price_change = (random.random() - 0.5) * 0.02  # ±1% movement
    current_price = data['ticker']['last']
    new_price = current_price * (1 + price_change)
    data['ticker']['last'] = new_price
    
    # Simulate volume changes
    volume_multiplier = 0.8 + random.random() * 0.4  # 0.8x to 1.2x
    data['ticker']['baseVolume'] *= volume_multiplier
    
    # Simulate orderbook imbalances (create patterns for detection)
    if iteration > 5:  # Start creating patterns after some history
        if iteration % 3 == 0:  # Every 3rd iteration, create buy imbalance
            # Increase bid volumes
            for i, (price, volume) in enumerate(data['orderbook']['bids']):
                data['orderbook']['bids'][i] = [price, volume * (1.5 + random.random() * 0.5)]
        elif iteration % 4 == 0:  # Every 4th iteration, create sell imbalance
            # Increase ask volumes
            for i, (price, volume) in enumerate(data['orderbook']['asks']):
                data['orderbook']['asks'][i] = [price, volume * (1.5 + random.random() * 0.5)]
    
    # Simulate open interest changes for position change detection
    if 'open_interest' in data:
        oi_change = (random.random() - 0.5) * 0.3  # ±15% change
        data['open_interest'] *= (1 + oi_change)
    
    return data

def demo_discord_formatting():
    """Demonstrate Discord alert formatting."""
    print("💬 Discord Alert Formatting Demo")
    print("=" * 40)
    
    # Example smart money events for Discord formatting
    example_events = [
        {
            'event_type': 'orderflow_imbalance',
            'symbol': 'BTCUSDT',
            'sophistication_score': 8.5,
            'confidence': 0.87,
            'data': {
                'side': 'buy',
                'imbalance': 0.72,
                'execution_quality': 0.85
            }
        },
        {
            'event_type': 'volume_spike',
            'symbol': 'ETHUSDT',
            'sophistication_score': 7.2,
            'confidence': 0.91,
            'data': {
                'spike_ratio': 4.3,
                'timing_score': 0.78,
                'coordination_evidence': 0.65
            }
        },
        {
            'event_type': 'depth_change',
            'symbol': 'SOLUSDT',
            'sophistication_score': 9.1,
            'confidence': 0.94,
            'data': {
                'side': 'bid',
                'change_ratio': 0.28,
                'stealth_score': 0.88
            }
        },
        {
            'event_type': 'position_change',
            'symbol': 'ADAUSDT',
            'sophistication_score': 6.8,
            'confidence': 0.76,
            'data': {
                'direction': 'increase',
                'change_value': 15000000,
                'institutional_pattern': 0.72
            }
        }
    ]
    
    for event in example_events:
        print(f"🎯 {event['event_type'].replace('_', ' ').title()} Alert")
        print(f"   Symbol: {event['symbol']}")
        print(f"   Sophistication: {event['sophistication_score']:.1f}/10")
        print(f"   Confidence: {event['confidence']:.1%}")
        
        # Show what would appear in Discord
        if event['sophistication_score'] >= 9:
            level_text = "🎯 EXPERT"
            color_desc = "Purple"
        elif event['sophistication_score'] >= 7:
            level_text = "🔥 HIGH"
            color_desc = "Orange"
        elif event['sophistication_score'] >= 4:
            level_text = "⚡ MEDIUM"
            color_desc = "Gold"
        else:
            level_text = "📊 LOW"
            color_desc = "Green"
        
        print(f"   Discord: {level_text} alert with {color_desc} color")
        print(f"   Title: 🧠 Smart Money Alert - {event['event_type'].replace('_', ' ').title()}")
        print()

async def main():
    """Main demo function."""
    print("🚀 Virtuoso Smart Money Monitoring System")
    print("=" * 60)
    print()
    print("This demo shows how the smart money detection system works")
    print("alongside the existing whale detection system.")
    print()
    print("Key Differences:")
    print("🐋 Whale Detection  → Focuses on SIZE (large orders/trades)")
    print("🧠 Smart Money     → Focuses on SOPHISTICATION (execution patterns)")
    print()
    print("=" * 60)
    print()
    
    # Run smart money detection demo
    await demo_smart_money_detection()
    
    print()
    print("=" * 60)
    print()
    
    # Show Discord formatting demo
    demo_discord_formatting()
    
    print()
    print("✅ Demo completed!")
    print()
    print("To enable smart money monitoring in production:")
    print("1. Ensure Discord webhook is configured")
    print("2. Adjust thresholds in config/config.yaml")
    print("3. Monitor alerts in your Discord channel")
    print("4. Fine-tune sophistication scoring as needed")

if __name__ == "__main__":
    asyncio.run(main()) 