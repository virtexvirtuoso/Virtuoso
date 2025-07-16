#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import os
import time
import psutil
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionEnvironmentTester:
    """Test production environment readiness."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        
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

    async def test_system_resources(self):
        """Test system resource availability."""
        try:
            logger.info("Testing system resources...")
            
            # Memory check
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            memory_usage_pct = memory.percent
            
            # CPU check
            cpu_count = psutil.cpu_count()
            cpu_usage_pct = psutil.cpu_percent(interval=1)
            
            # Disk check
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / (1024**3)
            disk_usage_pct = (disk.used / disk.total) * 100
            
            # Evaluate resources
            resource_issues = []
            
            if available_gb < 1.0:  # Less than 1GB available
                resource_issues.append(f"Low memory: {available_gb:.1f}GB available")
            
            if memory_usage_pct > 90:
                resource_issues.append(f"High memory usage: {memory_usage_pct:.1f}%")
            
            if cpu_count < 2:
                resource_issues.append(f"Limited CPU cores: {cpu_count}")
            
            if cpu_usage_pct > 80:
                resource_issues.append(f"High CPU usage: {cpu_usage_pct:.1f}%")
            
            if disk_free_gb < 1.0:  # Less than 1GB free
                resource_issues.append(f"Low disk space: {disk_free_gb:.1f}GB free")
            
            if len(resource_issues) == 0:
                self.log_result("System Resources", "PASS", 
                               f"Resources adequate: {available_gb:.1f}GB RAM, "
                               f"{cpu_count} CPUs, {disk_free_gb:.1f}GB disk")
            elif len(resource_issues) <= 2:
                self.log_result("System Resources", "WARN", 
                               f"Some resource constraints: {'; '.join(resource_issues)}")
            else:
                self.log_result("System Resources", "FAIL", 
                               f"Resource limitations: {'; '.join(resource_issues)}")
                
        except Exception as e:
            self.log_result("System Resources", "FAIL", f"Error: {str(e)}")

    async def test_environment_variables(self):
        """Test environment variables and configuration."""
        try:
            logger.info("Testing environment variables...")
            
            # Check for common environment variables
            env_checks = {
                'PATH': 'System PATH',
                'HOME': 'Home directory',
                'USER': 'Current user',
                'PYTHONPATH': 'Python path (optional)'
            }
            
            env_results = []
            
            for var_name, description in env_checks.items():
                value = os.environ.get(var_name)
                if value:
                    env_results.append((var_name, True, len(value)))
                else:
                    env_results.append((var_name, False, 0))
            
            # Check configuration availability
            try:
                config_manager = ConfigManager()
                config_available = True
                config_sections = len(config_manager.config) if hasattr(config_manager, 'config') else 0
            except Exception:
                config_available = False
                config_sections = 0
            
            required_vars = sum(1 for var, exists, _ in env_results if var in ['PATH', 'HOME'] and exists)
            total_required = 2
            
            if required_vars == total_required and config_available:
                self.log_result("Environment Variables", "PASS", 
                               f"Environment configured: {required_vars}/{total_required} required vars, "
                               f"config with {config_sections} sections")
            elif required_vars == total_required:
                self.log_result("Environment Variables", "WARN", 
                               "Basic environment OK, but config issues detected")
            else:
                self.log_result("Environment Variables", "FAIL", 
                               f"Environment incomplete: {required_vars}/{total_required} required vars")
                
        except Exception as e:
            self.log_result("Environment Variables", "FAIL", f"Error: {str(e)}")

    async def test_network_connectivity(self, exchange):
        """Test network connectivity and latency."""
        try:
            logger.info("Testing network connectivity...")
            
            # Test multiple endpoint connectivity
            connectivity_tests = []
            
            # Test 1: Basic ticker fetch
            start_time = time.time()
            try:
                ticker = await exchange.get_ticker('BTCUSDT')
                latency = (time.time() - start_time) * 1000  # ms
                if ticker and 'last' in ticker:
                    connectivity_tests.append(('ticker', True, latency))
                else:
                    connectivity_tests.append(('ticker', False, latency))
            except Exception:
                connectivity_tests.append(('ticker', False, 5000))
            
            # Test 2: Market data fetch
            start_time = time.time()
            try:
                orderbook = await exchange.get_order_book('BTCUSDT', 10)
                latency = (time.time() - start_time) * 1000  # ms
                if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                    connectivity_tests.append(('orderbook', True, latency))
                else:
                    connectivity_tests.append(('orderbook', False, latency))
            except Exception:
                connectivity_tests.append(('orderbook', False, 5000))
            
            # Test 3: Futures data fetch
            start_time = time.time()
            try:
                oi = await exchange.get_open_interest('BTCUSDT')
                latency = (time.time() - start_time) * 1000  # ms
                if oi is not None:
                    connectivity_tests.append(('futures', True, latency))
                else:
                    connectivity_tests.append(('futures', False, latency))
            except Exception:
                connectivity_tests.append(('futures', False, 5000))
            
            # Evaluate connectivity
            successful_tests = sum(1 for _, success, _ in connectivity_tests if success)
            total_tests = len(connectivity_tests)
            avg_latency = sum(latency for _, success, latency in connectivity_tests if success) / max(successful_tests, 1)
            
            if successful_tests == total_tests and avg_latency < 2000:  # < 2 seconds
                self.log_result("Network Connectivity", "PASS", 
                               f"{successful_tests}/{total_tests} endpoints responsive, "
                               f"avg latency: {avg_latency:.0f}ms")
            elif successful_tests >= total_tests * 0.7:  # 70% success
                self.log_result("Network Connectivity", "WARN", 
                               f"Some connectivity issues: {successful_tests}/{total_tests} successful, "
                               f"avg latency: {avg_latency:.0f}ms")
            else:
                self.log_result("Network Connectivity", "FAIL", 
                               f"Poor connectivity: {successful_tests}/{total_tests} successful")
                
        except Exception as e:
            self.log_result("Network Connectivity", "FAIL", f"Error: {str(e)}")

    async def test_error_handling_robustness(self, exchange):
        """Test error handling robustness."""
        try:
            logger.info("Testing error handling robustness...")
            
            error_scenarios = []
            
            # Test 1: Invalid symbol handling
            try:
                await exchange.get_ticker('INVALIDSYMBOL')
                error_scenarios.append(('invalid_symbol', False, 'No error raised'))
            except Exception as e:
                error_scenarios.append(('invalid_symbol', True, type(e).__name__))
            
            # Test 2: Malformed request handling
            try:
                await exchange.get_order_book('BTCUSDT', -1)  # Invalid limit
                error_scenarios.append(('invalid_limit', False, 'No error raised'))
            except Exception as e:
                error_scenarios.append(('invalid_limit', True, type(e).__name__))
            
            # Test 3: Network timeout simulation (very short timeout)
            try:
                original_timeout = getattr(exchange, 'timeout', 30)
                if hasattr(exchange, 'set_timeout'):
                    exchange.set_timeout(0.001)  # 1ms timeout
                
                await exchange.get_ticker('BTCUSDT')
                error_scenarios.append(('timeout_handling', False, 'No timeout occurred'))
                
                # Restore timeout
                if hasattr(exchange, 'set_timeout'):
                    exchange.set_timeout(original_timeout)
            except Exception as e:
                error_scenarios.append(('timeout_handling', True, type(e).__name__))
                # Restore timeout
                if hasattr(exchange, 'set_timeout'):
                    exchange.set_timeout(original_timeout)
            
            # Evaluate error handling
            proper_errors = sum(1 for _, handled, _ in error_scenarios if handled)
            total_scenarios = len(error_scenarios)
            
            if proper_errors >= total_scenarios * 0.8:  # 80% proper error handling
                self.log_result("Error Handling Robustness", "PASS", 
                               f"{proper_errors}/{total_scenarios} error scenarios handled properly")
            else:
                self.log_result("Error Handling Robustness", "WARN", 
                               f"Error handling needs improvement: {proper_errors}/{total_scenarios} handled")
                
        except Exception as e:
            self.log_result("Error Handling Robustness", "FAIL", f"Error: {str(e)}")

    async def test_concurrent_operations(self, exchange):
        """Test concurrent operations handling."""
        try:
            logger.info("Testing concurrent operations...")
            
            # Create multiple concurrent operations
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
            operations = []
            
            # Add ticker fetches
            for symbol in symbols:
                operations.append(('ticker', exchange.get_ticker(symbol)))
            
            # Add order book fetches
            for symbol in symbols[:2]:  # Limit to prevent rate limiting
                operations.append(('orderbook', exchange.get_order_book(symbol, 10)))
            
            # Execute all operations concurrently
            start_time = time.time()
            results = await asyncio.gather(*[op for _, op in operations], return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            operations_per_second = len(operations) / total_time if total_time > 0 else 0
            
            if successful >= len(operations) * 0.8 and operations_per_second >= 2:
                self.log_result("Concurrent Operations", "PASS", 
                               f"{successful}/{len(operations)} operations successful, "
                               f"{operations_per_second:.1f} ops/s")
            elif successful >= len(operations) * 0.6:
                self.log_result("Concurrent Operations", "WARN", 
                               f"Some concurrency issues: {successful}/{len(operations)} successful")
            else:
                self.log_result("Concurrent Operations", "FAIL", 
                               f"Poor concurrent performance: {successful}/{len(operations)} successful")
                
        except Exception as e:
            self.log_result("Concurrent Operations", "FAIL", f"Error: {str(e)}")

    async def test_memory_usage_patterns(self, exchange):
        """Test memory usage patterns under load."""
        try:
            logger.info("Testing memory usage patterns...")
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / (1024**2)  # MB
            
            # Perform memory-intensive operations
            memory_measurements = [initial_memory]
            
            for i in range(5):
                # Fetch data multiple times
                tasks = [exchange.get_ticker(f'BTC{base}') for base in ['USDT', 'USDT', 'USDT']]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Measure memory
                current_memory = process.memory_info().rss / (1024**2)  # MB
                memory_measurements.append(current_memory)
                
                await asyncio.sleep(0.5)  # Small delay
            
            # Analyze memory usage
            peak_memory = max(memory_measurements)
            memory_increase = peak_memory - initial_memory
            memory_growth_rate = memory_increase / len(memory_measurements)
            
            if memory_increase < 50:  # Less than 50MB increase
                self.log_result("Memory Usage Patterns", "PASS", 
                               f"Memory stable: {memory_increase:.1f}MB increase, "
                               f"peak: {peak_memory:.1f}MB")
            elif memory_increase < 100:  # Less than 100MB increase
                self.log_result("Memory Usage Patterns", "WARN", 
                               f"Moderate memory growth: {memory_increase:.1f}MB increase")
            else:
                self.log_result("Memory Usage Patterns", "FAIL", 
                               f"High memory usage: {memory_increase:.1f}MB increase")
                
        except Exception as e:
            self.log_result("Memory Usage Patterns", "FAIL", f"Error: {str(e)}")

    async def test_logging_and_monitoring(self):
        """Test logging and monitoring capabilities."""
        try:
            logger.info("Testing logging and monitoring...")
            
            # Check log directories
            log_dirs = ['logs', 'logs/alerts', 'logs/reports', 'logs/diagnostics']
            log_dir_status = []
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir) and os.path.isdir(log_dir):
                    # Check if writable
                    try:
                        test_file = os.path.join(log_dir, f'test_{int(time.time())}.log')
                        with open(test_file, 'w') as f:
                            f.write('test log entry')
                        os.remove(test_file)
                        log_dir_status.append((log_dir, 'writable'))
                    except Exception:
                        log_dir_status.append((log_dir, 'readonly'))
                else:
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                        log_dir_status.append((log_dir, 'created'))
                    except Exception:
                        log_dir_status.append((log_dir, 'missing'))
            
            # Test logging functionality
            test_logger = logging.getLogger('test_production')
            test_logger.setLevel(logging.INFO)
            
            # Check if we can log to different levels
            log_levels_working = []
            try:
                test_logger.info("Test info message")
                log_levels_working.append('info')
                test_logger.warning("Test warning message")
                log_levels_working.append('warning')
                test_logger.error("Test error message")
                log_levels_working.append('error')
            except Exception:
                pass
            
            writable_dirs = sum(1 for _, status in log_dir_status if status in ['writable', 'created'])
            total_dirs = len(log_dirs)
            
            if writable_dirs >= total_dirs * 0.75 and len(log_levels_working) >= 2:
                self.log_result("Logging and Monitoring", "PASS", 
                               f"{writable_dirs}/{total_dirs} log directories available, "
                               f"{len(log_levels_working)} log levels working")
            else:
                self.log_result("Logging and Monitoring", "WARN", 
                               f"Logging setup incomplete: {writable_dirs}/{total_dirs} dirs, "
                               f"{len(log_levels_working)} levels")
                
        except Exception as e:
            self.log_result("Logging and Monitoring", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("PRODUCTION ENVIRONMENT TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 75:
            logger.info("🎉 Production environment is ready!")
            return True
        else:
            logger.warning("⚠️ Production environment needs attention before deployment")
            return False

async def main():
    """Run Production Environment tests."""
    logger.info("🏭 TEST 7: Production Environment Readiness")
    logger.info("="*50)
    
    tester = ProductionEnvironmentTester()
    
    try:
        # Run system tests first (don't require exchange)
        await tester.test_system_resources()
        await tester.test_environment_variables()
        await tester.test_logging_and_monitoring()
        
        # Initialize exchange for network tests
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run network and performance tests
            await tester.test_network_connectivity(exchange)
            await tester.test_error_handling_robustness(exchange)
            await tester.test_concurrent_operations(exchange)
            await tester.test_memory_usage_patterns(exchange)
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 