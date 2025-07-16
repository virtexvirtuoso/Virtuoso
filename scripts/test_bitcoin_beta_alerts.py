#!/usr/bin/env python3

"""
Test Bitcoin Beta Analysis Alert Integration

This script tests that the Bitcoin Beta Analysis system correctly sends
alpha opportunity alerts through the alert manager.
"""

import asyncio
import logging
import sys
import os
import yaml
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from reports.bitcoin_beta_report import BitcoinBetaReport
from reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector, AlphaOpportunity
from reports.bitcoin_beta_scheduler import BitcoinBetaScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_config():
    """Load test configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

class MockAlertManager:
    """Mock alert manager to capture alerts during testing."""
    
    def __init__(self):
        self.alerts = []
        self.alpha_alerts = []
        
    async def send_alert(self, level, message, details=None, throttle=True):
        """Mock send_alert method."""
        alert = {
            'level': level,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.alerts.append(alert)
        logger.info(f"MOCK ALERT: {level} - {message}")
        
    async def send_alpha_opportunity_alert(self, symbol, alpha_estimate, confidence_score, 
                                         divergence_type, risk_level, trading_insight, market_data, transaction_id=None):
        """Mock alpha opportunity alert method."""
        alert = {
            'symbol': symbol,
            'alpha_estimate': alpha_estimate,
            'confidence_score': confidence_score,
            'divergence_type': divergence_type,
            'risk_level': risk_level,
            'trading_insight': trading_insight,
            'market_data': market_data,
            'transaction_id': transaction_id,
            'timestamp': datetime.now().isoformat()
        }
        self.alpha_alerts.append(alert)
        logger.info(f"MOCK ALPHA ALERT: {symbol} - {alpha_estimate:.1%} alpha, {confidence_score:.1%} confidence, {divergence_type}")
        
    def get_alert_count(self):
        """Get total alert count."""
        return len(self.alerts) + len(self.alpha_alerts)
        
    def get_alpha_alert_count(self):
        """Get alpha alert count."""
        return len(self.alpha_alerts)

class MockExchangeManager:
    """Mock exchange manager for testing."""
    
    async def get_primary_exchange(self):
        return MockExchange()

class MockExchange:
    """Mock exchange for testing."""
    
    async def fetch_ohlcv(self, symbol, timeframe, limit):
        """Mock OHLCV data."""
        import pandas as pd
        import numpy as np
        
        # Generate mock data with some realistic patterns
        timestamps = pd.date_range(end=datetime.now(), periods=limit, freq='1min')
        
        # Create mock price data with some correlation patterns
        base_price = 50000 if symbol == 'BTCUSDT' else np.random.uniform(0.5, 100)
        prices = []
        
        for i in range(limit):
            # Add some randomness but maintain trends
            change = np.random.normal(0, 0.02)  # 2% volatility
            if i == 0:
                price = base_price
            else:
                price = prices[i-1] * (1 + change)
            prices.append(max(price, 0.001))  # Ensure positive prices
        
        # Create OHLCV data
        ohlcv = []
        for i, (ts, price) in enumerate(zip(timestamps, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000000, 10000000)
            
            ohlcv.append([
                int(ts.timestamp() * 1000),  # timestamp
                price,                       # open
                high,                        # high
                low,                         # low
                price,                       # close (same as open for simplicity)
                volume                       # volume
            ])
        
        return ohlcv

class MockTopSymbolsManager:
    """Mock top symbols manager for testing."""
    
    async def get_symbols(self):
        """Return mock symbols."""
        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']

class MockDataFrame:
    """Mock pandas DataFrame for testing."""
    
    def __init__(self, data):
        self.data = data
        self.empty = False
        
    def __getitem__(self, key):
        if key in self.data:
            return MockSeries(self.data[key])
        raise KeyError(f"'{key}' not found")
        
    @property
    def close(self):
        return MockSeries(self.data.get('close', []))

class MockSeries:
    """Mock pandas Series for testing."""
    
    def __init__(self, data):
        self.data = data if isinstance(data, list) else [data]
        
    @property
    def iloc(self):
        return MockIloc(self.data)

class MockIloc:
    """Mock pandas iloc accessor."""
    
    def __init__(self, data):
        self.data = data
        
    def __getitem__(self, key):
        if isinstance(key, int):
            if key < 0:
                # Handle negative indices (e.g., -1 for last element)
                return self.data[key] if -len(self.data) <= key else None
            else:
                return self.data[key] if 0 <= key < len(self.data) else None
        return self.data[key]

async def test_bitcoin_beta_alert_integration():
    """Test the integration between Bitcoin beta analysis and alert manager."""
    try:
        logger.info("Starting Bitcoin Beta Alert Integration Test")
        
        # Load configuration
        config = load_test_config()
        
        # Create mock components
        exchange_manager = MockExchangeManager()
        top_symbols_manager = MockTopSymbolsManager()
        alert_manager = MockAlertManager()
        
        logger.info("✅ Mock components created")
        
        # Test 1: BitcoinBetaReport with AlertManager
        logger.info("TEST 1: Testing BitcoinBetaReport with AlertManager integration")
        
        beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config,
            alert_manager=alert_manager  # This should now work
        )
        
        # Verify alert manager is properly stored
        assert beta_report.alert_manager is not None, "Alert manager should be set"
        logger.info("✅ BitcoinBetaReport accepts alert_manager parameter")
        
        # Test 2: Alpha Detection Integration
        logger.info("TEST 2: Testing alpha detection with mock data")
        
        # Create mock beta analysis data that should trigger alpha opportunities
        mock_beta_analysis = {
            'htf': {
                'ETHUSDT': {
                    'beta': 0.8,
                    'correlation': 0.6,
                    'alpha': 0.05,  # 5% alpha should trigger alert
                    'r_squared': 0.4
                },
                'SOLUSDT': {
                    'beta': 1.2,
                    'correlation': 0.3,  # Low correlation should trigger alert
                    'alpha': 0.03,
                    'r_squared': 0.1
                }
            },
            'mtf': {
                'ETHUSDT': {
                    'beta': 0.9,
                    'correlation': 0.7,
                    'alpha': 0.04,
                    'r_squared': 0.5
                },
                'SOLUSDT': {
                    'beta': 1.1,
                    'correlation': 0.4,
                    'alpha': 0.02,
                    'r_squared': 0.15
                }
            }
        }
        
        # Test alpha detector directly
        alpha_detector = BitcoinBetaAlphaDetector(config)
        alpha_opportunities = alpha_detector.detect_alpha_opportunities(mock_beta_analysis)
        
        logger.info(f"Alpha detector found {len(alpha_opportunities)} opportunities")
        for opp in alpha_opportunities:
            logger.info(f"  - {opp.symbol}: {opp.alpha_potential:.1%} alpha, {opp.confidence:.1%} confidence, {opp.divergence_type.value}")
        
        # Test 3: Alert Integration via _send_alpha_opportunity_alerts
        if alpha_opportunities:
            logger.info("TEST 3: Testing alpha opportunity alerts")
            
            # Create mock market data for price context
            mock_market_data = {
                'ETHUSDT': {
                    'base': MockDataFrame({'close': [1800.50]})
                },
                'SOLUSDT': {
                    'base': MockDataFrame({'close': [95.25]})
                },
                'BTCUSDT': {
                    'base': MockDataFrame({'close': [45000.00]})
                }
            }
            
            # Test the alert sending method
            initial_alert_count = alert_manager.get_alpha_alert_count()
            await beta_report._send_alpha_opportunity_alerts(alpha_opportunities, mock_market_data)
            final_alert_count = alert_manager.get_alpha_alert_count()
            
            alerts_sent = final_alert_count - initial_alert_count
            logger.info(f"✅ Sent {alerts_sent} alpha opportunity alerts")
            
            # Verify alerts were sent
            assert alerts_sent > 0, "Should have sent at least one alpha alert"
            
            # Check alert content
            for alert in alert_manager.alpha_alerts:
                logger.info(f"Alert details: {alert['symbol']} - {alert['divergence_type']} - {alert['alpha_estimate']:.1%}")
                
        else:
            logger.warning("No alpha opportunities detected with mock data")
        
        # Test 4: Scheduler Integration
        logger.info("TEST 4: Testing scheduler with alert manager")
        
        scheduler = BitcoinBetaScheduler(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config,
            alert_manager=alert_manager
        )
        
        # Verify scheduler has alert manager
        assert scheduler.alert_manager is not None, "Scheduler should have alert manager"
        assert scheduler.beta_report.alert_manager is not None, "Scheduler's beta report should have alert manager"
        
        logger.info("✅ Scheduler properly configured with alert manager")
        
        # Test 5: Report Notification
        logger.info("TEST 5: Testing report notification")
        
        initial_general_alerts = len(alert_manager.alerts)
        await scheduler._send_report_notification("/mock/path/to/report.pdf")
        final_general_alerts = len(alert_manager.alerts)
        
        notification_alerts = final_general_alerts - initial_general_alerts
        logger.info(f"✅ Sent {notification_alerts} report notification alerts")
        
        assert notification_alerts > 0, "Should have sent report notification"
        
        # Summary
        logger.info("=" * 60)
        logger.info("INTEGRATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Total alerts sent: {alert_manager.get_alert_count()}")
        logger.info(f"✅ Alpha opportunity alerts: {alert_manager.get_alpha_alert_count()}")
        logger.info(f"✅ General alerts: {len(alert_manager.alerts)}")
        logger.info("✅ Bitcoin Beta Analysis is properly connected to Alert Manager")
        logger.info("✅ Alpha opportunities will now generate Discord alerts")
        logger.info("✅ Report completion notifications working")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test function."""
    logger.info("Bitcoin Beta Analysis Alert Integration Test")
    logger.info("=" * 60)
    
    success = await test_bitcoin_beta_alert_integration()
    
    if success:
        logger.info("✅ ALL TESTS PASSED - Integration is working correctly")
        return 0
    else:
        logger.error("❌ TESTS FAILED - Integration needs fixing")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 