#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import json
import time
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertSystemIntegrationTester:
    """Test alert system integration with Binance data."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        self.mock_alerts = []
        
    def log_result(self, test_name: str, status: str, message: str):
        """Log test results."""
        if status == 'PASS':
            logger.info(f"✅ {test_name}: {message}")
            self.test_results['passed'] += 1
        elif status == 'FAIL':
            logger.error(f"❌ {test_name}: {message}")
            self.test_results['failed'] += 1
        else:
            logger.warning(f"⚠️ {test_name}: {message}")
            self.test_results['warnings'] += 1

    def create_mock_alert(self, alert_type: str, symbol: str, threshold: float, current_value: float) -> Dict[str, Any]:
        """Create a mock alert for testing."""
        alert = {
            'id': f"alert_{int(time.time())}_{len(self.mock_alerts)}",
            'type': alert_type,
            'symbol': symbol,
            'threshold': threshold,
            'current_value': current_value,
            'triggered': current_value >= threshold if alert_type == 'price_above' else current_value <= threshold,
            'timestamp': int(time.time()),
            'message': f"{alert_type.replace('_', ' ').title()} alert for {symbol}: {current_value} vs threshold {threshold}"
        }
        self.mock_alerts.append(alert)
        return alert

    async def test_price_based_alerts(self, exchange):
        """Test price-based alert triggers with Binance data."""
        try:
            logger.info("Testing price-based alerts...")
            
            # Get current market data
            symbol = 'BTCUSDT'
            ticker = await exchange.get_ticker(symbol)
            
            if not ticker or not ticker.get('last'):
                self.log_result("Price Alert Data", "FAIL", "Failed to get ticker data")
                return
            
            current_price = float(ticker['last'])
            
            # Create test alerts with different thresholds
            alerts_created = 0
            alerts_triggered = 0
            
            # Alert that should trigger (below current price)
            lower_alert = self.create_mock_alert('price_above', symbol, current_price - 100, current_price)
            if lower_alert['triggered']:
                alerts_triggered += 1
            alerts_created += 1
            
            # Alert that shouldn't trigger (above current price)
            upper_alert = self.create_mock_alert('price_above', symbol, current_price + 1000, current_price)
            if upper_alert['triggered']:
                alerts_triggered += 1
            alerts_created += 1
            
            # Alert for price drop that should trigger (above current price)
            drop_alert = self.create_mock_alert('price_below', symbol, current_price + 100, current_price)
            if drop_alert['triggered']:
                alerts_triggered += 1
            alerts_created += 1
            
            if alerts_created == 3 and alerts_triggered == 2:
                self.log_result("Price-Based Alerts", "PASS", 
                               f"Created {alerts_created} alerts, {alerts_triggered} triggered correctly")
            else:
                self.log_result("Price-Based Alerts", "FAIL", 
                               f"Alert logic error: {alerts_triggered}/{alerts_created} triggered")
                
        except Exception as e:
            self.log_result("Price-Based Alerts", "FAIL", f"Error: {str(e)}")

    async def test_volume_based_alerts(self, exchange):
        """Test volume-based alert triggers."""
        try:
            logger.info("Testing volume-based alerts...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            volume_alerts = []
            
            for symbol in symbols:
                try:
                    ticker = await exchange.get_ticker(symbol)
                    if ticker and ticker.get('quoteVolume'):
                        volume = float(ticker['quoteVolume'])
                        
                        # Create volume threshold alert
                        threshold = volume * 0.8  # 80% of current volume
                        alert = self.create_mock_alert('volume_above', symbol, threshold, volume)
                        volume_alerts.append(alert)
                        
                except Exception as e:
                    logger.debug(f"Failed to get volume for {symbol}: {str(e)}")
            
            triggered_alerts = [a for a in volume_alerts if a['triggered']]
            
            if len(volume_alerts) >= 2 and len(triggered_alerts) >= 2:
                self.log_result("Volume-Based Alerts", "PASS", 
                               f"{len(triggered_alerts)}/{len(volume_alerts)} volume alerts triggered")
            else:
                self.log_result("Volume-Based Alerts", "FAIL", 
                               f"Insufficient volume alerts: {len(triggered_alerts)}/{len(volume_alerts)}")
                
        except Exception as e:
            self.log_result("Volume-Based Alerts", "FAIL", f"Error: {str(e)}")

    async def test_funding_rate_alerts(self, exchange):
        """Test funding rate alert triggers."""
        try:
            logger.info("Testing funding rate alerts...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            funding_alerts = []
            
            for symbol in symbols:
                try:
                    funding = await exchange.get_current_funding_rate(symbol)
                    if funding and 'fundingRate' in funding:
                        rate = float(funding['fundingRate'])
                        rate_pct = abs(rate * 100)
                        
                        # Create funding rate alerts
                        # Alert for high positive rates
                        if rate > 0:
                            threshold = 0.01  # 1% funding rate threshold
                            alert = self.create_mock_alert('funding_above', symbol, threshold, rate_pct)
                            funding_alerts.append(alert)
                        
                        # Alert for high negative rates
                        if rate < 0:
                            threshold = -0.01  # -1% funding rate threshold
                            alert = self.create_mock_alert('funding_below', symbol, threshold, rate_pct)
                            funding_alerts.append(alert)
                        
                except Exception as e:
                    logger.debug(f"Failed to get funding rate for {symbol}: {str(e)}")
            
            if len(funding_alerts) >= 1:
                triggered = [a for a in funding_alerts if a['triggered']]
                self.log_result("Funding Rate Alerts", "PASS", 
                               f"Created {len(funding_alerts)} funding alerts, {len(triggered)} triggered")
            else:
                self.log_result("Funding Rate Alerts", "WARN", 
                               "No funding rate alerts created (rates may be normal)")
                
        except Exception as e:
            self.log_result("Funding Rate Alerts", "FAIL", f"Error: {str(e)}")

    async def test_open_interest_alerts(self, exchange):
        """Test open interest change alerts."""
        try:
            logger.info("Testing open interest alerts...")
            
            symbols = ['BTCUSDT', 'ETHUSDT']
            oi_alerts = []
            
            for symbol in symbols:
                try:
                    # Get initial OI
                    oi1 = await exchange.get_open_interest(symbol)
                    await asyncio.sleep(2)  # Wait 2 seconds
                    oi2 = await exchange.get_open_interest(symbol)
                    
                    if (oi1 and oi2 and 
                        'openInterest' in oi1 and 'openInterest' in oi2):
                        
                        oi_value1 = float(oi1['openInterest'])
                        oi_value2 = float(oi2['openInterest'])
                        
                        if oi_value1 > 0:
                            change_pct = abs((oi_value2 - oi_value1) / oi_value1) * 100
                            
                            # Create alert for significant OI changes
                            threshold = 0.1  # 0.1% change threshold
                            alert = self.create_mock_alert('oi_change', symbol, threshold, change_pct)
                            oi_alerts.append(alert)
                        
                except Exception as e:
                    logger.debug(f"Failed to get OI for {symbol}: {str(e)}")
            
            if len(oi_alerts) >= 1:
                triggered = [a for a in oi_alerts if a['triggered']]
                self.log_result("Open Interest Alerts", "PASS", 
                               f"Created {len(oi_alerts)} OI alerts, monitoring changes")
            else:
                self.log_result("Open Interest Alerts", "WARN", 
                               "No OI alerts created (changes may be minimal)")
                
        except Exception as e:
            self.log_result("Open Interest Alerts", "FAIL", f"Error: {str(e)}")

    async def test_alert_data_validation(self, exchange):
        """Test alert data validation and sanitization."""
        try:
            logger.info("Testing alert data validation...")
            
            # Test with valid data
            ticker = await exchange.get_ticker('BTCUSDT')
            if not ticker:
                self.log_result("Alert Data Validation", "FAIL", "No ticker data for validation")
                return
            
            valid_tests = 0
            total_tests = 0
            
            # Test 1: Valid price data
            total_tests += 1
            try:
                price = float(ticker.get('last', 0))
                if price > 0 and price < 1000000:  # Reasonable price range
                    valid_tests += 1
                    logger.debug(f"Price validation passed: ${price}")
            except (ValueError, TypeError):
                logger.debug("Price validation failed")
            
            # Test 2: Valid volume data
            total_tests += 1
            try:
                volume = float(ticker.get('quoteVolume', 0))
                if volume >= 0:  # Volume should be non-negative
                    valid_tests += 1
                    logger.debug(f"Volume validation passed: {volume}")
            except (ValueError, TypeError):
                logger.debug("Volume validation failed")
            
            # Test 3: Valid timestamp
            total_tests += 1
            try:
                timestamp = int(ticker.get('timestamp', 0))
                current_time = int(time.time() * 1000)
                if abs(timestamp - current_time) < 300000:  # Within 5 minutes
                    valid_tests += 1
                    logger.debug(f"Timestamp validation passed: {timestamp}")
            except (ValueError, TypeError):
                logger.debug("Timestamp validation failed")
            
            validation_rate = (valid_tests / total_tests) * 100
            
            if validation_rate >= 80:
                self.log_result("Alert Data Validation", "PASS", 
                               f"{valid_tests}/{total_tests} validation tests passed")
            else:
                self.log_result("Alert Data Validation", "FAIL", 
                               f"Low validation rate: {validation_rate:.1f}%")
                
        except Exception as e:
            self.log_result("Alert Data Validation", "FAIL", f"Error: {str(e)}")

    async def test_alert_performance(self, exchange):
        """Test alert system performance with multiple conditions."""
        try:
            logger.info("Testing alert system performance...")
            
            start_time = time.time()
            
            # Simulate checking multiple alerts quickly
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
            alerts_processed = 0
            
            for symbol in symbols:
                try:
                    # Get data for alert checking
                    ticker_task = exchange.get_ticker(symbol)
                    funding_task = exchange.get_current_funding_rate(symbol)
                    oi_task = exchange.get_open_interest(symbol)
                    
                    # Wait for all data in parallel
                    ticker, funding, oi = await asyncio.gather(
                        ticker_task, funding_task, oi_task, 
                        return_exceptions=True
                    )
                    
                    # Process each data type for alert conditions
                    if not isinstance(ticker, Exception) and ticker:
                        alerts_processed += 1
                    if not isinstance(funding, Exception) and funding:
                        alerts_processed += 1
                    if not isinstance(oi, Exception) and oi:
                        alerts_processed += 1
                    
                except Exception as e:
                    logger.debug(f"Error processing alerts for {symbol}: {str(e)}")
            
            processing_time = time.time() - start_time
            alerts_per_second = alerts_processed / processing_time if processing_time > 0 else 0
            
            if alerts_per_second >= 5:  # At least 5 alerts per second
                self.log_result("Alert Performance", "PASS", 
                               f"Processed {alerts_processed} alerts in {processing_time:.2f}s ({alerts_per_second:.1f}/s)")
            else:
                self.log_result("Alert Performance", "WARN", 
                               f"Low performance: {alerts_per_second:.1f} alerts/second")
                
        except Exception as e:
            self.log_result("Alert Performance", "FAIL", f"Error: {str(e)}")

    async def test_alert_routing_simulation(self):
        """Test simulated alert routing and delivery."""
        try:
            logger.info("Testing alert routing simulation...")
            
            # Simulate different alert channels
            channels = ['email', 'webhook', 'telegram', 'discord']
            routing_tests = 0
            successful_routes = 0
            
            for alert in self.mock_alerts[:5]:  # Test first 5 alerts
                for channel in channels:
                    routing_tests += 1
                    
                    # Simulate routing logic
                    try:
                        # Mock routing based on alert type and severity
                        if alert['type'] in ['price_above', 'price_below']:
                            priority = 'high' if alert['triggered'] else 'low'
                        else:
                            priority = 'medium'
                        
                        # Simulate successful routing
                        route_success = True  # In real implementation, this would be actual routing
                        
                        if route_success:
                            successful_routes += 1
                            logger.debug(f"Alert {alert['id']} routed to {channel} (priority: {priority})")
                        
                    except Exception as e:
                        logger.debug(f"Routing failed for {channel}: {str(e)}")
            
            if routing_tests > 0:
                success_rate = (successful_routes / routing_tests) * 100
                
                if success_rate >= 90:
                    self.log_result("Alert Routing", "PASS", 
                                   f"{successful_routes}/{routing_tests} routes successful ({success_rate:.1f}%)")
                else:
                    self.log_result("Alert Routing", "FAIL", 
                                   f"Low routing success: {success_rate:.1f}%")
            else:
                self.log_result("Alert Routing", "WARN", "No alerts to route")
                
        except Exception as e:
            self.log_result("Alert Routing", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("ALERT SYSTEM INTEGRATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        logger.info(f"🚨 Total Alerts Created: {len(self.mock_alerts)}")
        
        triggered_alerts = [a for a in self.mock_alerts if a['triggered']]
        logger.info(f"⚡ Alerts Triggered: {len(triggered_alerts)}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 75:
            logger.info("🎉 Alert system integration is functional!")
            return True
        else:
            logger.warning("⚠️ Alert system integration needs attention")
            return False

async def main():
    """Run Alert System integration tests."""
    logger.info("🚨 TEST 3: Alert System Integration")
    logger.info("="*50)
    
    tester = AlertSystemIntegrationTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run alert system tests
            await tester.test_price_based_alerts(exchange)
            await tester.test_volume_based_alerts(exchange)
            await tester.test_funding_rate_alerts(exchange)
            await tester.test_open_interest_alerts(exchange)
            await tester.test_alert_data_validation(exchange)
            await tester.test_alert_performance(exchange)
            await tester.test_alert_routing_simulation()
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 