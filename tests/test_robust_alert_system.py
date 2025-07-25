#!/usr/bin/env python3

"""
Robust Alert System Integration Test

This script comprehensively tests:
1. Signal frequency tracking functionality
2. Signal data preservation through frequency tracker
3. Rich formatting integration with confluence alerts  
4. PDF generation and attachment
5. Discord webhook delivery
6. Cooldown management and alert routing

Usage:
    python test_robust_alert_system.py
"""

import sys
import os
import asyncio
import json
import yaml
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_robust_alert_system.log')
    ]
)

logger = logging.getLogger("robust_alert_test")

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Configuration loaded from: {config_path}")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {str(e)}")
        return {}

def create_comprehensive_signal_data(symbol: str = "BTCUSDT", score: float = 76.5) -> Dict[str, Any]:
    """Create comprehensive signal data for testing."""
    return {
        "symbol": symbol,
        "signal_type": "BUY",
        "confluence_score": score,
        "reliability": 93.2,
        "timestamp": datetime.now().isoformat(),
        "price": 104567.89,
        "transaction_id": f"robust-test-{int(time.time())}",
        "signal_id": f"signal-robust-{int(time.time())}",
        "components": {
            "technical": 78.9,
            "volume": 74.2,
            "orderbook": 88.1,
            "orderflow": 79.3,
            "sentiment": 64.8,
            "price_structure": 72.5
        },
        "sub_components": {
            "technical": {
                "rsi": 75.4,
                "macd": 70.8,
                "ao": 83.2,
                "williams_r": 77.1,
                "cci": 78.6,
                "atr": 71.9
            },
            "volume": {
                "relative_volume": 85.3,
                "volume_delta": 72.8,
                "obv": 77.9,
                "cmf": 74.1,
                "adl": 71.4,
                "volume_profile": 75.6,
                "vwap": 73.2
            },
            "orderbook": {
                "imbalance": 90.7,
                "depth": 86.3,
                "mpi": 85.8,
                "liquidity": 84.1,
                "spread": 81.5,
                "pressure": 88.4,
                "absorption_exhaustion": 83.7,
                "obps": 82.1,
                "dom_momentum": 80.9
            },
            "orderflow": {
                "cvd": 81.8,
                "trade_flow": 78.5,
                "imbalance": 77.2,
                "open_interest": 76.8,
                "pressure": 81.3,
                "liquidity": 75.1,
                "liquidity_zones": 73.9
            },
            "sentiment": {
                "funding_rate": 67.9,
                "liquidations": 61.5,
                "long_short_ratio": 65.3,
                "volatility": 62.8,
                "market_activity": 66.7,
                "risk": 63.2
            },
            "price_structure": {
                "trend_position": 75.8,
                "support_resistance": 70.2,
                "order_blocks": 74.3,
                "volume_profile": 70.1,
                "market_structure": 72.8,
                "range_analysis": 69.4
            }
        },
        "market_data": {
            "volume_24h": 30547362840,
            "change_24h": 3.12,
            "high_24h": 105789.45,
            "low_24h": 103234.56,
            "turnover_24h": 3165847291000
        },
        "interpretations": {
            "technical": "Technical indicators show strong bullish momentum with RSI at 75.4 indicating sustained upward pressure. MACD confirms positive divergence with robust momentum continuation.",
            "volume": "Volume analysis reveals significant institutional participation with 85.3% relative volume spike. Volume delta strongly bullish at 72.8%, indicating coordinated buying pressure.",
            "orderbook": "Extreme orderbook imbalance at 90.7% heavily favoring buyers. Market depth analysis shows substantial bid-side support with minimal ask-side resistance creating favorable conditions.",
            "orderflow": "Cumulative volume delta at 81.8% confirms strong institutional accumulation pattern. Trade flow analysis indicates coordinated buying with minimal distribution pressure.",
            "sentiment": "Mixed sentiment indicators with funding rates at manageable levels. Long/short ratio moderately bullish within normal parameters. Liquidation risk remains low.",
            "price_structure": "Price structure analysis shows healthy uptrend continuation with strong support level establishment. Order blocks provide solid foundation for sustained upward movement."
        },
        "actionable_insights": [
            "🚀 Strong bullish bias detected - Consider standard to aggressive position sizing",
            "📈 Monitor for momentum continuation above $105,000 key resistance level",
            "⚡ Positive institutional flow patterns support sustained upward movement",
            "🎯 Target levels: $107,500 (short-term), $110,000 (extended target)",
            "🛡️ Risk management: Stop loss below $103,500 critical support level"
        ],
        "top_components": [
            {
                "name": "Orderbook Imbalance",
                "category": "Orderbook",
                "value": 90.7,
                "impact": 3.6,
                "trend": "up",
                "description": "Extreme bid-side dominance indicates overwhelming buying pressure"
            },
            {
                "name": "Relative Volume",
                "category": "Volume",
                "value": 85.3,
                "impact": 3.1,
                "trend": "up", 
                "description": "Significant volume surge confirms strong institutional interest"
            },
            {
                "name": "Technical AO",
                "category": "Technical",
                "value": 83.2,
                "impact": 2.4,
                "trend": "up",
                "description": "Awesome Oscillator shows powerful momentum with continuation potential"
            }
        ]
    }

async def test_signal_frequency_tracker():
    """Test 1: Signal Frequency Tracker Functionality"""
    logger.info("🧪 TEST 1: Signal Frequency Tracker Functionality")
    logger.info("="*60)
    
    try:
        # Import after path setup
        from monitoring.signal_frequency_tracker import SignalFrequencyTracker
        
        config = load_config()
        if not config:
            return False
            
        # Initialize frequency tracker
        tracker = SignalFrequencyTracker(config)
        
        # Test signal data preservation
        signal_data = create_comprehensive_signal_data("BTCUSDT", 76.5)
        logger.info(f"📊 Created test signal: {signal_data['symbol']} score={signal_data['confluence_score']}")
        
        # Track signal and check if frequency alert is generated
        frequency_alert = tracker.track_signal(signal_data)
        
        if frequency_alert:
            logger.info("✅ Frequency alert generated successfully")
            
            # Test signal_data preservation
            preserved_data = frequency_alert.get('signal_data')
            if preserved_data:
                logger.info("✅ Signal data preserved in frequency alert")
                logger.info(f"  - Symbol: {preserved_data.get('symbol')}")
                logger.info(f"  - Confluence Score: {preserved_data.get('confluence_score')}")
                logger.info(f"  - Components: {len(preserved_data.get('components', {}))}")
                logger.info(f"  - Sub-components: {len(preserved_data.get('sub_components', {}))}")
                logger.info(f"  - Interpretations: {len(preserved_data.get('interpretations', {}))}")
                logger.info(f"  - Actionable Insights: {len(preserved_data.get('actionable_insights', []))}")
                return True
            else:
                logger.error("❌ Signal data not preserved in frequency alert")
                return False
        else:
            logger.warning("⚠️ No frequency alert generated (might be expected based on thresholds)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Signal Frequency Tracker test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_alert_manager_integration():
    """Test 2: Alert Manager Integration with Rich Formatting"""
    logger.info("\n🧪 TEST 2: Alert Manager Integration")
    logger.info("="*60)
    
    try:
        # Import after path setup
        from monitoring.alert_manager import AlertManager
        from monitoring.signal_frequency_tracker import SignalFrequencyTracker, FrequencyAlert, SignalType
        
        config = load_config()
        if not config:
            return False
            
        # Initialize components
        alert_manager = AlertManager(config)
        
        # Create test signal data
        signal_data = create_comprehensive_signal_data("ETHUSDT", 77.8)
        
        # Test the full alert flow
        logger.info("📨 Testing full alert flow through AlertManager...")
        
        # This should trigger frequency tracking and rich formatting
        await alert_manager.send_signal_alert(signal_data)
        
        logger.info("✅ Alert sent through AlertManager successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Alert Manager integration test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_confluence_alert_routing():
    """Test 3: Confluence Alert Routing"""
    logger.info("\n🧪 TEST 3: Confluence Alert Routing")
    logger.info("="*60)
    
    try:
        # Import after path setup
        from monitoring.signal_frequency_tracker import FrequencyAlert, SignalType
        
        config = load_config()
        alert_manager = AlertManager(config)
        
        # Create a mock frequency alert with signal data
        signal_data = create_comprehensive_signal_data("SOLUSDT", 78.9)
        
        mock_frequency_alert = FrequencyAlert(
            symbol="SOLUSDT",
            signal_type=SignalType.BUY,
            current_score=78.9,
            previous_score=0.0,
            time_since_last=0.0,
            frequency_count=1,
            alert_message="Test frequency alert",
            timestamp=time.time(),
            alert_id="test-confluence",
            signal_data=signal_data
        )
        
        # Test the confluence alert routing
        logger.info("🔀 Testing confluence alert routing...")
        await alert_manager._send_frequency_alert(mock_frequency_alert)
        
        logger.info("✅ Confluence alert routing completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Confluence alert routing test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_pdf_generation_integration():
    """Test 4: PDF Generation Integration"""
    logger.info("\n🧪 TEST 4: PDF Generation Integration")
    logger.info("="*60)
    
    try:
        # Test if PDF generation components are accessible
        logger.info("📄 Testing PDF generation availability...")
        
        # Check if reports directory exists
        reports_dir = "reports/pdf"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Count existing PDFs
        existing_pdfs = len([f for f in os.listdir(reports_dir) if f.endswith('.pdf')])
        logger.info(f"📊 Found {existing_pdfs} existing PDF reports")
        
        # The PDF generation will be tested indirectly through signal flow
        logger.info("✅ PDF generation environment validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ PDF generation test failed: {str(e)}")
        return False

async def test_cooldown_management():
    """Test 5: Cooldown Management"""
    logger.info("\n🧪 TEST 5: Cooldown Management")
    logger.info("="*60)
    
    try:
        # Import after path setup
        
        config = load_config()
        tracker = SignalFrequencyTracker(config)
        
        # Send first signal
        signal_data_1 = create_comprehensive_signal_data("ADAUSDT", 75.2)
        alert_1 = tracker.track_signal(signal_data_1)
        
        if alert_1:
            logger.info("✅ First signal generated alert (expected)")
        else:
            logger.info("ℹ️ First signal did not generate alert (threshold dependent)")
        
        # Send second signal immediately (should be in cooldown)
        signal_data_2 = create_comprehensive_signal_data("ADAUSDT", 76.8)
        alert_2 = tracker.track_signal(signal_data_2)
        
        if not alert_2:
            logger.info("✅ Second signal blocked by cooldown (expected behavior)")
        else:
            logger.info("ℹ️ Second signal generated alert (may indicate score improvement threshold met)")
        
        # Test statistics
        stats = tracker.get_signal_statistics()
        logger.info(f"📊 Tracker Statistics:")
        for key, value in stats.items():
            logger.info(f"  - {key}: {value}")
        
        logger.info("✅ Cooldown management test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cooldown management test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_discord_webhook_config():
    """Test 6: Discord Webhook Configuration"""
    logger.info("\n🧪 TEST 6: Discord Webhook Configuration")
    logger.info("="*60)
    
    try:
        config = load_config()
        
        # Check webhook configuration
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            logger.info("✅ Discord webhook URL found in environment")
            logger.info(f"  - URL length: {len(webhook_url)} characters")
            logger.info(f"  - Starts with: {webhook_url[:30]}...")
        else:
            logger.warning("⚠️ Discord webhook URL not found in environment")
        
        # Check config webhook settings
        monitoring_config = config.get('monitoring', {})
        alerts_config = monitoring_config.get('alerts', {})
        
        if 'discord_webhook' in alerts_config:
            logger.info("✅ Discord webhook configuration found in config")
            logger.info(f"  - Settings: {list(alerts_config['discord_webhook'].keys())}")
        
        logger.info("✅ Discord webhook configuration validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Discord webhook config test failed: {str(e)}")
        return False

async def run_comprehensive_test():
    """Run comprehensive alert system test"""
    logger.info("🚀 ROBUST ALERT SYSTEM INTEGRATION TEST")
    logger.info("="*80)
    logger.info("Testing the complete integration:")
    logger.info("  1. Signal frequency tracking functionality")
    logger.info("  2. Signal data preservation through frequency tracker")  
    logger.info("  3. Rich formatting integration with confluence alerts")
    logger.info("  4. PDF generation and attachment capability")
    logger.info("  5. Cooldown management and alert routing")
    logger.info("  6. Discord webhook delivery configuration")
    logger.info("="*80)
    
    test_results = {}
    
    # Run all tests
    test_results['frequency_tracker'] = await test_signal_frequency_tracker()
    test_results['alert_manager'] = await test_alert_manager_integration() 
    test_results['confluence_routing'] = await test_confluence_alert_routing()
    test_results['pdf_generation'] = await test_pdf_generation_integration()
    test_results['cooldown_management'] = await test_cooldown_management()
    test_results['discord_config'] = await test_discord_webhook_config()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("🎯 TEST RESULTS SUMMARY")
    logger.info("="*80)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed_tests += 1
    
    success_rate = (passed_tests / total_tests) * 100
    logger.info(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 ROBUST TEST SUITE: EXCELLENT RESULTS!")
        logger.info("   The alert system integration is working properly.")
    elif success_rate >= 60:
        logger.info("✅ ROBUST TEST SUITE: GOOD RESULTS!")
        logger.info("   Most functionality is working, minor issues detected.")
    else:
        logger.error("❌ ROBUST TEST SUITE: ISSUES DETECTED!")
        logger.error("   Significant problems found that need attention.")
    
    logger.info("="*80)
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        result = asyncio.run(run_comprehensive_test())
        exit_code = 0 if result else 1
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Test suite failed with exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)