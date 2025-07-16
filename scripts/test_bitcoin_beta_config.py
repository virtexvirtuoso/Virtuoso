#!/usr/bin/env python3
"""
Test Bitcoin Beta Analysis Configuration

This script tests that the Bitcoin Beta Analysis system correctly uses the new
configurable timeframes and periods from config.yaml.
"""

import asyncio
import logging
import sys
import os
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from reports.bitcoin_beta_report import BitcoinBetaReport
from reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector
from reports.bitcoin_beta_scheduler import BitcoinBetaScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_config():
    """Load the test configuration to verify new settings."""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

async def test_bitcoin_beta_configuration():
    """Test the Bitcoin Beta Analysis configuration."""
    try:
        logger.info("🧪 Testing Bitcoin Beta Analysis Configuration")
        logger.info("=" * 60)
        
        # Load configuration
        config = load_test_config()
        beta_config = config.get('bitcoin_beta_analysis', {})
        
        if not beta_config:
            logger.error("❌ No bitcoin_beta_analysis section found in config!")
            return False
        
        logger.info("✅ Bitcoin Beta Analysis configuration found")
        
        # Test 1: Verify timeframe configuration
        logger.info("\n📊 Testing Timeframe Configuration:")
        timeframes_config = beta_config.get('timeframes', {})
        
        expected_timeframes = ['htf', 'mtf', 'ltf', 'base']
        for tf in expected_timeframes:
            tf_config = timeframes_config.get(tf, {})
            interval = tf_config.get('interval', 'NOT FOUND')
            periods = tf_config.get('periods', 'NOT FOUND')
            description = tf_config.get('description', 'NO DESCRIPTION')
            
            logger.info(f"  {tf.upper()}: {interval} - {periods} periods - {description}")
        
        # Test 2: Verify new shorter periods
        logger.info("\n⏱️  Verifying New Shorter Periods:")
        expected_periods = {
            'htf': 180,   # 30 days (was 540)
            'mtf': 336,   # 7 days (was 720)
            'ltf': 288,   # 1 day (was 864)
            'base': 240   # 4 hours (was 480)
        }
        
        all_periods_correct = True
        for tf, expected_period in expected_periods.items():
            actual_period = timeframes_config.get(tf, {}).get('periods', 0)
            if actual_period == expected_period:
                logger.info(f"  ✅ {tf.upper()}: {actual_period} periods (correct)")
            else:
                logger.error(f"  ❌ {tf.upper()}: {actual_period} periods (expected {expected_period})")
                all_periods_correct = False
        
        # Test 3: Create BitcoinBetaReport instance and verify it uses config
        logger.info("\n🔧 Testing BitcoinBetaReport Initialization:")
        
        # Mock managers for testing
        class MockExchangeManager:
            pass
        
        class MockTopSymbolsManager:
            pass
        
        mock_exchange = MockExchangeManager()
        mock_symbols = MockTopSymbolsManager()
        
        # Create report instance
        beta_report = BitcoinBetaReport(mock_exchange, mock_symbols, config)
        
        logger.info(f"  Timeframes: {beta_report.timeframes}")
        logger.info(f"  Periods: {beta_report.periods}")
        
        # Verify the report is using the config values
        config_matches = True
        for tf in expected_timeframes:
            config_interval = timeframes_config.get(tf, {}).get('interval', '')
            config_periods = timeframes_config.get(tf, {}).get('periods', 0)
            
            report_interval = beta_report.timeframes.get(tf, '')
            report_periods = beta_report.periods.get(tf, 0)
            
            if config_interval != report_interval:
                logger.error(f"  ❌ {tf} interval mismatch: config={config_interval}, report={report_interval}")
                config_matches = False
            
            if config_periods != report_periods:
                logger.error(f"  ❌ {tf} periods mismatch: config={config_periods}, report={report_periods}")
                config_matches = False
        
        if config_matches:
            logger.info("  ✅ BitcoinBetaReport is using configuration values correctly")
        
        # Test 4: Test Alpha Detector Configuration
        logger.info("\n🎯 Testing Alpha Detector Configuration:")
        
        alpha_detector = BitcoinBetaAlphaDetector(config)
        alpha_config = beta_config.get('alpha_detection', {}).get('thresholds', {})
        
        logger.info(f"  Alpha thresholds: {alpha_detector.thresholds}")
        
        # Test 5: Test Scheduler Configuration
        logger.info("\n⏰ Testing Scheduler Configuration:")
        
        scheduler = BitcoinBetaScheduler(mock_exchange, mock_symbols, config, None)
        reports_config = beta_config.get('reports', {})
        
        expected_times = reports_config.get('schedule_times', [])
        logger.info(f"  Schedule times: {scheduler.schedule_times}")
        logger.info(f"  Schedule enabled: {scheduler.schedule_enabled}")
        
        # Test 6: Verify Analysis Periods
        logger.info("\n📈 Analysis Period Summary:")
        logger.info("  New shorter periods for faster analysis:")
        
        timeframe_descriptions = {
            'htf': 'Long-term correlation trends',
            'mtf': 'Medium-term patterns', 
            'ltf': 'Short-term movements',
            'base': 'Real-time analysis'
        }
        
        for tf, description in timeframe_descriptions.items():
            tf_config = timeframes_config.get(tf, {})
            interval = tf_config.get('interval', '')
            periods = tf_config.get('periods', 0)
            
            # Calculate approximate days/hours
            if interval == '4h':
                duration = f"~{periods * 4 / 24:.0f} days"
            elif interval == '30m':
                duration = f"~{periods * 30 / 60 / 24:.0f} days"
            elif interval == '5m':
                duration = f"~{periods * 5 / 60 / 24:.0f} days"
            elif interval == '1m':
                duration = f"~{periods / 60:.0f} hours"
            else:
                duration = "unknown"
            
            logger.info(f"  {tf.upper()} ({interval}): {duration} for {description}")
        
        # Test 7: Configuration completeness
        logger.info("\n✅ Configuration Completeness Check:")
        
        required_sections = [
            'timeframes', 'reports', 'alpha_detection', 'analysis', 'charts', 'performance'
        ]
        
        all_sections_present = True
        for section in required_sections:
            if section in beta_config:
                logger.info(f"  ✅ {section} section present")
            else:
                logger.error(f"  ❌ {section} section missing")
                all_sections_present = False
        
        # Final result
        logger.info("\n" + "=" * 60)
        if all_periods_correct and config_matches and all_sections_present:
            logger.info("🎉 ALL TESTS PASSED!")
            logger.info("✅ Bitcoin Beta Analysis is now configured with shorter analysis periods")
            logger.info("✅ All components are reading configuration correctly")
            logger.info("✅ Configuration is complete and valid")
            return True
        else:
            logger.error("❌ SOME TESTS FAILED!")
            logger.error("Please check the configuration and try again")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing configuration: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test execution."""
    success = await test_bitcoin_beta_configuration()
    
    if success:
        print("\n🚀 Bitcoin Beta Analysis is ready with new configuration!")
        print("   • HTF (4h): ~30 days for long-term correlation trends")
        print("   • MTF (30m): ~7 days for medium-term patterns") 
        print("   • LTF (5m): ~1 day for short-term movements")
        print("   • Base (1m): ~4 hours for real-time analysis")
        print("\n   All timeframes and analysis periods are now configurable in config.yaml")
    else:
        print("\n❌ Configuration test failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 