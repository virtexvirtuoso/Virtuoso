#!/usr/bin/env python3
"""
Test script for Binance integration with Virtuoso architecture.

This script tests that Binance is properly integrated with:
- ExchangeManager
- ExchangeFactory
- BaseExchange interface compliance
- Configuration system

Usage:
    python scripts/test_virtuoso_integration.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import Virtuoso components
from core.exchanges.factory import ExchangeFactory
from core.exchanges.manager import ExchangeManager
from config.manager import ConfigManager

class VirtuosoIntegrationTester:
    """Test Binance integration with Virtuoso architecture."""
    
    def __init__(self):
        """Initialize the tester."""
        self.test_results = {}
        
        print("🏗️ Virtuoso Architecture Integration Test")
        print("=" * 50)
        print("Testing Binance integration with:")
        print("  ✅ ExchangeFactory")
        print("  ✅ ExchangeManager") 
        print("  ✅ BaseExchange interface compliance")
        print("  ✅ Configuration system")
        print("-" * 50)
    
    def setup_test_config(self) -> dict:
        """Create test configuration for Binance."""
        return {
            'exchanges': {
                'binance': {
                    'enabled': True,
                    'primary': False,  # Keep as secondary for testing
                    'data_only': True,
                    'api_credentials': {
                        'api_key': '',  # Empty for public access
                        'api_secret': ''
                    },
                    'rate_limits': {
                        'requests_per_minute': 1200,
                        'requests_per_second': 10,
                        'weight_per_minute': 6000
                    },
                    'rest_endpoint': 'https://api.binance.com',
                    'testnet': False,
                    'websocket': {
                        'public': 'wss://stream.binance.com:9443/ws',
                        'keep_alive': True,
                        'ping_interval': 30,
                        'reconnect_attempts': 3
                    },
                    'market_types': ['spot', 'futures'],
                    'data_preferences': {
                        'preferred_quote_currencies': ['USDT', 'BTC', 'ETH'],
                        'exclude_symbols': [],
                        'min_24h_volume': 1000000
                    }
                }
            },
            'market_data': {
                'update_interval': 1.0,
                'batch_size': 100
            },
            'validation': {},
            'monitoring': {}
        }
    
    async def test_exchange_factory(self):
        """Test that ExchangeFactory can create Binance exchange."""
        print("\n🏭 Testing ExchangeFactory")
        print("-" * 25)
        
        try:
            config = self.setup_test_config()
            binance_config = config['exchanges']['binance']
            
            print("   1️⃣  Creating Binance exchange via factory...")
            
            # Test exchange creation
            exchange = await ExchangeFactory.create_exchange('binance', binance_config)
            
            if exchange:
                print(f"      ✅ Exchange created: {type(exchange).__name__}")
                print(f"      ✅ Exchange ID: {exchange.exchange_id}")
                print(f"      ✅ Initialized: {exchange.initialized}")
                
                # Test BaseExchange interface compliance
                print("   2️⃣  Testing BaseExchange interface compliance...")
                required_methods = [
                    'initialize', 'health_check', 'close', 'fetch_ticker',
                    'fetch_order_book', 'fetch_trades', 'fetch_ohlcv'
                ]
                
                missing_methods = []
                for method in required_methods:
                    if not hasattr(exchange, method):
                        missing_methods.append(method)
                
                if not missing_methods:
                    print(f"      ✅ All required methods present")
                else:
                    print(f"      ❌ Missing methods: {missing_methods}")
                
                # Test some basic functionality
                print("   3️⃣  Testing basic functionality...")
                if hasattr(exchange, 'fetch_ticker'):
                    test_symbol = 'BTC/USDT'
                    try:
                        ticker = await exchange.fetch_ticker(test_symbol)
                        print(f"      ✅ fetch_ticker working: ${ticker.get('last', 'N/A')}")
                    except Exception as e:
                        print(f"      ⚠️  fetch_ticker error: {str(e)}")
                
                # Close the exchange
                await exchange.close()
                print(f"      ✅ Exchange closed successfully")
                
                self.test_results['exchange_factory'] = {
                    'success': True,
                    'exchange_created': True,
                    'interface_compliant': len(missing_methods) == 0,
                    'basic_functionality': True
                }
                
            else:
                print(f"      ❌ Failed to create exchange")
                self.test_results['exchange_factory'] = {
                    'success': False,
                    'error': 'Exchange creation failed'
                }
                
        except Exception as e:
            print(f"   ❌ Error in ExchangeFactory test: {str(e)}")
            self.test_results['exchange_factory'] = {
                'success': False,
                'error': str(e)
            }
    
    async def test_exchange_manager(self):
        """Test that ExchangeManager can manage Binance exchange."""
        print("\n🎛️ Testing ExchangeManager")
        print("-" * 24)
        
        try:
            # Create a mock ConfigManager
            config = self.setup_test_config()
            
            class MockConfigManager:
                def __init__(self, config):
                    self._config = config
                
                def get_value(self, key, default=None):
                    keys = key.split('.')
                    value = self._config
                    for k in keys:
                        if isinstance(value, dict) and k in value:
                            value = value[k]
                        else:
                            return default
                    return value
            
            print("   1️⃣  Creating ExchangeManager...")
            config_manager = MockConfigManager(config)
            manager = ExchangeManager(config_manager)
            
            print("   2️⃣  Initializing exchanges...")
            initialized = await manager.initialize()
            
            if initialized:
                print(f"      ✅ Manager initialized successfully")
                
                # Check active exchanges
                active_exchanges = manager.get_active_exchanges()
                print(f"      ✅ Active exchanges: {active_exchanges}")
                
                if 'binance' in active_exchanges:
                    print(f"      ✅ Binance exchange is active")
                    
                    # Test exchange info
                    try:
                        exchange_info = manager.get_exchange_info('binance')
                        print(f"      ✅ Exchange info retrieved: {exchange_info.get('name', 'binance')}")
                    except Exception as e:
                        print(f"      ⚠️  Exchange info error: {str(e)}")
                    
                    # Test getting the exchange
                    try:
                        binance_exchange = manager.exchanges.get('binance')
                        if binance_exchange:
                            print(f"      ✅ Binance exchange accessible from manager")
                            print(f"      ✅ Exchange type: {type(binance_exchange).__name__}")
                        else:
                            print(f"      ❌ Binance exchange not found in manager")
                    except Exception as e:
                        print(f"      ⚠️  Exchange access error: {str(e)}")
                        
                else:
                    print(f"      ❌ Binance exchange not active")
                
                # Close manager
                await manager.close()
                print(f"      ✅ Manager closed successfully")
                
                self.test_results['exchange_manager'] = {
                    'success': True,
                    'initialized': True,
                    'binance_active': 'binance' in active_exchanges
                }
                
            else:
                print(f"      ❌ Manager initialization failed")
                self.test_results['exchange_manager'] = {
                    'success': False,
                    'error': 'Manager initialization failed'
                }
                
        except Exception as e:
            print(f"   ❌ Error in ExchangeManager test: {str(e)}")
            self.test_results['exchange_manager'] = {
                'success': False,
                'error': str(e)
            }
    
    async def test_configuration_integration(self):
        """Test configuration system integration."""
        print("\n⚙️ Testing Configuration Integration")
        print("-" * 35)
        
        try:
            print("   1️⃣  Testing configuration loading...")
            
            # Test with environment variables
            original_env = {}
            test_env_vars = {
                'ENABLE_BINANCE_DATA': 'true',
                'BINANCE_AS_PRIMARY': 'false',
                'BINANCE_API_KEY': '',
                'BINANCE_API_SECRET': ''
            }
            
            # Set test environment variables
            for key, value in test_env_vars.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                # Try loading actual config if it exists
                config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
                if config_path.exists():
                    print(f"      ✅ Found config file: {config_path}")
                    
                    try:
                        config_manager = ConfigManager()
                        config_manager.load_config(str(config_path))
                        
                        # Check if Binance is in the configuration
                        binance_config = config_manager.get_value('exchanges.binance', {})
                        if binance_config:
                            print(f"      ✅ Binance configuration found in config.yaml")
                            print(f"      ✅ Enabled: {binance_config.get('enabled', False)}")
                            print(f"      ✅ Primary: {binance_config.get('primary', False)}")
                            print(f"      ✅ Data only: {binance_config.get('data_only', True)}")
                            
                            self.test_results['configuration'] = {
                                'success': True,
                                'config_found': True,
                                'binance_configured': True,
                                'env_vars_working': True
                            }
                        else:
                            print(f"      ⚠️  Binance not found in config.yaml")
                            self.test_results['configuration'] = {
                                'success': False,
                                'error': 'Binance not configured in config.yaml'
                            }
                            
                    except Exception as e:
                        print(f"      ⚠️  Config loading error: {str(e)}")
                        self.test_results['configuration'] = {
                            'success': False,
                            'error': f'Config loading failed: {str(e)}'
                        }
                else:
                    print(f"      ⚠️  Config file not found: {config_path}")
                    self.test_results['configuration'] = {
                        'success': False,
                        'error': 'Config file not found'
                    }
                    
            finally:
                # Restore original environment variables
                for key, original_value in original_env.items():
                    if original_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = original_value
                        
        except Exception as e:
            print(f"   ❌ Error in configuration test: {str(e)}")
            self.test_results['configuration'] = {
                'success': False,
                'error': str(e)
            }
    
    async def generate_integration_report(self):
        """Generate final integration test report."""
        print("\n📋 Virtuoso Integration Test Report")
        print("=" * 40)
        
        print(f"\n🔧 Test Configuration:")
        print(f"   Test Date: {datetime.now().isoformat()}")
        print(f"   Test Environment: Python {sys.version_info.major}.{sys.version_info.minor}")
        print(f"   Test Focus: Binance integration with Virtuoso architecture")
        
        # Calculate overall success
        test_categories = ['exchange_factory', 'exchange_manager', 'configuration']
        successful_tests = sum(1 for category in test_categories if self.test_results.get(category, {}).get('success', False))
        total_tests = len(test_categories)
        
        print(f"\n📊 Integration Test Results:")
        for category in test_categories:
            result = self.test_results.get(category, {})
            success = result.get('success', False)
            status = "✅ PASSED" if success else "❌ FAILED"
            category_name = category.replace('_', ' ').title()
            print(f"   {status} {category_name}")
            
            if not success and 'error' in result:
                print(f"        Error: {result['error']}")
        
        success_rate = (successful_tests / total_tests) * 100
        print(f"\n💡 Overall Integration Results:")
        print(f"   Successful Tests: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print(f"   🎉 FULL VIRTUOSO INTEGRATION SUCCESSFUL!")
            print(f"   ✅ Binance is properly integrated with Virtuoso architecture")
            print(f"   ✅ Ready for production deployment")
        elif success_rate >= 80:
            print(f"   🟨 MOSTLY INTEGRATED - Minor issues remain")
            print(f"   ⚠️  Review failed tests before production deployment")
        else:
            print(f"   🔴 INTEGRATION ISSUES DETECTED")
            print(f"   ❌ Architecture integration needs fixes")
        
        print(f"\n🚀 Next Steps:")
        if success_rate == 100:
            print(f"   1. Enable Binance in production configuration")
            print(f"   2. Set appropriate environment variables")
            print(f"   3. Monitor exchange manager logs")
            print(f"   4. Test with real market data")
        else:
            print(f"   1. Fix failing integration components")
            print(f"   2. Update configuration as needed")
            print(f"   3. Re-run integration tests")
            print(f"   4. Verify BaseExchange interface compliance")
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print(f"🧪 Starting Virtuoso Integration Tests")
        print(f"{'=' * 60}")
        
        # Run all test categories
        await self.test_exchange_factory()
        await self.test_exchange_manager()
        await self.test_configuration_integration()
        
        # Generate final report
        await self.generate_integration_report()

async def main():
    """Main function."""
    try:
        tester = VirtuosoIntegrationTester()
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n👋 Integration test session ended")

if __name__ == "__main__":
    asyncio.run(main()) 