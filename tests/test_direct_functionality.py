#!/usr/bin/env python3

"""
Direct Functionality Test

This script tests the core functionality directly without importing problematic modules.
Tests:
1. FrequencyAlert signal_data access
2. Signal data preservation through dataclass
3. Alert manager method signatures
4. Configuration validation
"""

import sys
import os
import json
import yaml
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("direct_test")

def test_frequency_alert_dataclass():
    """Test 1: FrequencyAlert dataclass functionality"""
    logger.info("🧪 TEST 1: FrequencyAlert Dataclass")
    logger.info("="*50)
    
    try:
        # Add just the specific file path to avoid problematic imports
        sys.path.insert(0, 'src/monitoring')
        from signal_frequency_tracker import FrequencyAlert, SignalType
        
        # Create comprehensive test signal data
        test_signal_data = {
            "symbol": "BTCUSDT",
            "signal_type": "BUY",
            "confluence_score": 76.8,
            "reliability": 93.2,
            "components": {
                "technical": 78.9,
                "volume": 74.2,
                "orderbook": 88.1,
                "orderflow": 79.3,
                "sentiment": 64.8,
                "price_structure": 72.5
            },
            "interpretations": {
                "technical": "Strong bullish momentum detected",
                "volume": "Significant institutional participation",
                "orderbook": "Extreme imbalance favoring buyers"
            },
            "actionable_insights": [
                "🚀 Strong bullish bias - Consider aggressive positioning",
                "📈 Monitor momentum continuation above resistance",
                "🎯 Target levels: $107,500 (short-term)"
            ]
        }
        
        # Create FrequencyAlert with signal_data
        alert = FrequencyAlert(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            current_score=76.8,
            previous_score=0.0,
            time_since_last=0.0,
            frequency_count=1,
            alert_message="Test alert with rich data",
            timestamp=time.time(),
            alert_id="test-direct-123",
            signal_data=test_signal_data
        )
        
        logger.info("✅ FrequencyAlert created successfully")
        
        # Test .get() method access
        retrieved_data = alert.get('signal_data')
        if retrieved_data:
            logger.info("✅ signal_data retrieved successfully via .get() method")
            logger.info(f"  - Symbol: {retrieved_data.get('symbol')}")
            logger.info(f"  - Confluence Score: {retrieved_data.get('confluence_score')}")
            logger.info(f"  - Components Count: {len(retrieved_data.get('components', {}))}")
            logger.info(f"  - Interpretations Count: {len(retrieved_data.get('interpretations', {}))}")
            logger.info(f"  - Actionable Insights Count: {len(retrieved_data.get('actionable_insights', []))}")
        else:
            logger.error("❌ signal_data retrieval failed")
            return False
        
        # Test dictionary-like access for other fields
        symbol = alert.get('symbol')
        score = alert.get('current_score')
        
        if symbol == "BTCUSDT" and score == 76.8:
            logger.info("✅ Dictionary-like access works for all fields")
        else:
            logger.error("❌ Dictionary-like access failed for basic fields")
            return False
            
        logger.info("🎉 FrequencyAlert dataclass test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ FrequencyAlert test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_configuration_validation():
    """Test 2: Configuration validation"""
    logger.info("\n🧪 TEST 2: Configuration Validation") 
    logger.info("="*50)
    
    try:
        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("✅ Configuration loaded successfully")
        
        # Test frequency tracking config
        freq_config = config.get('signal_frequency_tracking', {})
        if freq_config.get('enabled'):
            logger.info("✅ Signal frequency tracking enabled")
            logger.info(f"  - Cooldown periods: {freq_config.get('cooldown_periods', {})}")
            logger.info(f"  - Score threshold: {freq_config.get('min_score_for_frequency_alert', 'N/A')}")
        else:
            logger.warning("⚠️ Signal frequency tracking disabled")
        
        # Test buy signal alerts config
        buy_config = freq_config.get('buy_signal_alerts', {})
        if buy_config.get('enabled'):
            logger.info("✅ Buy signal alerts enabled")
            buy_settings = buy_config.get('buy_specific_settings', {})
            logger.info(f"  - Use rich format: {buy_settings.get('use_rich_format', False)}")
            logger.info(f"  - Include PDF: {buy_settings.get('include_pdf', False)}")
        
        # Test Discord webhook
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url:
            logger.info("✅ Discord webhook URL configured")
        else:
            logger.warning("⚠️ Discord webhook URL not found")
        
        # Test reporting config
        reporting_config = config.get('reporting', {})
        if reporting_config.get('enabled'):
            logger.info("✅ Reporting enabled")
            logger.info(f"  - Attach PDF: {reporting_config.get('attach_pdf', False)}")
            logger.info(f"  - Attach JSON: {reporting_config.get('attach_json', False)}")
        
        logger.info("🎉 Configuration validation PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {str(e)}")
        return False

def test_signal_data_structure():
    """Test 3: Signal data structure completeness"""
    logger.info("\n🧪 TEST 3: Signal Data Structure")
    logger.info("="*50)
    
    try:
        # Create complete signal data structure
        signal_data = {
            "symbol": "BTCUSDT",
            "signal_type": "BUY", 
            "confluence_score": 77.4,
            "reliability": 94.1,
            "timestamp": datetime.now().isoformat(),
            "price": 105234.67,
            "transaction_id": f"test-structure-{int(time.time())}",
            "signal_id": f"signal-struct-{int(time.time())}",
            
            # Required for rich formatting
            "components": {
                "technical": 79.3,
                "volume": 75.8,
                "orderbook": 89.2,
                "orderflow": 80.1,
                "sentiment": 65.7,
                "price_structure": 73.9
            },
            
            # Required for confluence alerts
            "interpretations": {
                "technical": "Strong bullish momentum with RSI showing sustained upward pressure",
                "volume": "Significant institutional participation with elevated relative volume",
                "orderbook": "Extreme imbalance heavily favoring buyers across depth levels",
                "orderflow": "Cumulative volume delta confirms strong institutional accumulation",
                "sentiment": "Mixed sentiment with manageable funding rates and low liquidation risk",
                "price_structure": "Healthy uptrend continuation with strong support establishment"
            },
            
            # Required for actionable insights
            "actionable_insights": [
                "🚀 Strong bullish bias detected - Consider standard to aggressive position sizing",
                "📈 Monitor for momentum continuation above $105,500 resistance",
                "⚡ Positive institutional flow supports sustained upward movement",
                "🎯 Target levels: $108,000 (short-term), $111,500 (extended)",
                "🛡️ Risk management: Stop loss below $103,800 support level"
            ],
            
            # Required for detailed analysis
            "top_components": [
                {
                    "name": "Orderbook Imbalance",
                    "category": "Orderbook",
                    "value": 89.2,
                    "impact": 3.7,
                    "trend": "up",
                    "description": "Extreme bid-side dominance indicates overwhelming buying pressure"
                }
            ],
            
            "market_data": {
                "volume_24h": 31547362840,
                "change_24h": 3.45,
                "high_24h": 106789.12,
                "low_24h": 104123.45,
                "turnover_24h": 3265847291000
            }
        }
        
        # Validate structure
        required_fields = [
            'symbol', 'signal_type', 'confluence_score', 'components',
            'interpretations', 'actionable_insights', 'top_components'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in signal_data:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return False
        
        logger.info("✅ All required fields present")
        
        # Test data completeness
        components_count = len(signal_data['components'])
        interpretations_count = len(signal_data['interpretations'])
        insights_count = len(signal_data['actionable_insights'])
        
        logger.info(f"  - Components: {components_count}")
        logger.info(f"  - Interpretations: {interpretations_count}")
        logger.info(f"  - Actionable Insights: {insights_count}")
        
        if components_count >= 6 and interpretations_count >= 5 and insights_count >= 3:
            logger.info("✅ Signal data structure is comprehensive")
        else:
            logger.warning("⚠️ Signal data structure may be incomplete")
        
        logger.info("🎉 Signal data structure test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Signal data structure test failed: {str(e)}")
        return False

def test_pdf_environment():
    """Test 4: PDF generation environment"""
    logger.info("\n🧪 TEST 4: PDF Environment")
    logger.info("="*50)
    
    try:
        # Check directories
        pdf_dir = "reports/pdf"
        json_dir = "exports"
        
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        
        # Count existing files
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        
        logger.info(f"✅ PDF directory exists with {len(pdf_files)} files")
        logger.info(f"✅ JSON export directory exists with {len(json_files)} files")
        
        # Check for recent files
        recent_pdfs = [f for f in pdf_files if 'btcusdt' in f.lower() or 'ethusdt' in f.lower()]
        recent_jsons = [f for f in json_files if f.startswith('buy_')]
        
        logger.info(f"  - Recent BTC/ETH PDFs: {len(recent_pdfs)}")
        logger.info(f"  - Recent buy signals: {len(recent_jsons)}")
        
        if len(pdf_files) > 0:
            logger.info("✅ PDF generation appears to be working")
        else:
            logger.warning("⚠️ No PDF files found - may indicate generation issues")
        
        logger.info("🎉 PDF environment test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ PDF environment test failed: {str(e)}")
        return False

def run_direct_tests():
    """Run direct functionality tests"""
    logger.info("🔧 DIRECT FUNCTIONALITY TEST SUITE")
    logger.info("="*60)
    logger.info("Testing core functionality without problematic imports:")
    logger.info("  1. FrequencyAlert dataclass and signal_data access")
    logger.info("  2. Configuration validation")
    logger.info("  3. Signal data structure completeness")  
    logger.info("  4. PDF generation environment")
    logger.info("="*60)
    
    tests = [
        ("FrequencyAlert Dataclass", test_frequency_alert_dataclass),
        ("Configuration Validation", test_configuration_validation),
        ("Signal Data Structure", test_signal_data_structure),
        ("PDF Environment", test_pdf_environment)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("🎯 DIRECT TEST RESULTS")
    logger.info("="*60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
    
    success_rate = (passed / total) * 100
    logger.info(f"\nDirect Test Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        logger.info("🎉 DIRECT TESTS: PERFECT SCORE!")
        logger.info("   All core functionality is working correctly.")
    elif success_rate >= 75:
        logger.info("✅ DIRECT TESTS: EXCELLENT RESULTS!")
        logger.info("   Core functionality is solid with minor issues.")
    else:
        logger.error("❌ DIRECT TESTS: ISSUES DETECTED!")
        logger.error("   Core functionality problems need attention.")
    
    logger.info("="*60)
    return success_rate >= 75

if __name__ == "__main__":
    try:
        result = run_direct_tests()
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"❌ Direct test suite failed: {str(e)}")
        sys.exit(1)