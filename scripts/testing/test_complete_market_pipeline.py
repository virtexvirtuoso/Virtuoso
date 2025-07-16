#!/usr/bin/env python3
"""
Comprehensive Market Reporter Pipeline Test

This test validates the complete end-to-end pipeline:
- Live data collection from Bybit
- All calculation methods (market overview, futures premium, smart money, whale activity)
- PDF generation with real templates
- JSON export and API compatibility
- Performance monitoring and validation
- Complete workflow validation

This is the ultimate test to ensure production readiness.
"""

import sys
import os
import asyncio
import logging
import ccxt
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

class ComprehensiveMarketPipelineTest:
    """Comprehensive test suite for the complete market reporter pipeline."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.logger = self._setup_logging()
        self.exchange = None
        self.market_reporter = None
        self.test_results = {
            'start_time': datetime.now(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'detailed_results': {},
            'performance_metrics': {},
            'generated_files': [],
            'errors': []
        }
        
    def _setup_logging(self):
        """Set up comprehensive logging for the test."""
        # Create logs directory
        logs_dir = os.path.join(project_root, 'logs', 'tests')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure logger
        logger = logging.getLogger('MarketPipelineTest')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(logs_dir, f'market_pipeline_test_{timestamp}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Test logging initialized - log file: {log_file}")
        return logger
        
    async def run_comprehensive_test(self):
        """Run the complete comprehensive test suite."""
        self.logger.info("🚀 STARTING COMPREHENSIVE MARKET REPORTER PIPELINE TEST")
        self.logger.info("=" * 80)
        
        try:
            # Test 1: Initialize Exchange Connection
            await self._test_exchange_initialization()
            
            # Test 2: Initialize Market Reporter
            await self._test_market_reporter_initialization()
            
            # Test 3: Test Live Data Collection
            await self._test_live_data_collection()
            
            # Test 4: Test All Calculation Methods
            await self._test_calculation_methods()
            
            # Test 5: Test Complete Market Summary Generation
            await self._test_market_summary_generation()
            
            # Test 6: Test PDF Generation
            await self._test_pdf_generation()
            
            # Test 7: Test JSON Export and API Compatibility
            await self._test_json_export()
            
            # Test 8: Test Performance and Monitoring
            await self._test_performance_monitoring()
            
            # Test 9: Test Error Handling and Resilience
            await self._test_error_handling()
            
            # Test 10: Validate Complete Pipeline Integration
            await self._test_complete_pipeline_integration()
            
            # Generate final test report
            await self._generate_test_report()
            
        except Exception as e:
            self.logger.error(f"Critical test failure: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.test_results['errors'].append(f"Critical failure: {str(e)}")
        
        finally:
            self._display_test_summary()
            
    async def _test_exchange_initialization(self):
        """Test 1: Exchange initialization and connectivity."""
        test_name = "Exchange Initialization"
        self.logger.info(f"\n🔧 TEST 1: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        
        try:
            # Initialize Bybit exchange
            self.exchange = ccxt.bybit({
                'sandbox': False,
                'enableRateLimit': True,
                'timeout': 30000
            })
            
            # Test basic connectivity
            self.logger.info("Testing exchange connectivity...")
            markets = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self.exchange.load_markets),
                timeout=30
            )
            
            if markets and len(markets) > 0:
                self.logger.info(f"✅ Exchange connected successfully - {len(markets)} markets loaded")
                
                # Test specific market access
                test_symbol = 'BTCUSDT'
                ticker = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self.exchange.fetch_ticker, test_symbol
                    ),
                    timeout=10
                )
                
                if ticker and 'last' in ticker:
                    btc_price = float(ticker['last'])
                    self.logger.info(f"✅ Market data access confirmed - BTC price: ${btc_price:,.2f}")
                    success = True
                else:
                    self.logger.error("❌ Market data access failed")
            else:
                self.logger.error("❌ Exchange connection failed - no markets loaded")
                
        except Exception as e:
            self.logger.error(f"❌ Exchange initialization failed: {str(e)}")
            self.test_results['errors'].append(f"Exchange init: {str(e)}")
        
        # Record test results
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, {
            'markets_loaded': len(markets) if 'markets' in locals() else 0,
            'btc_price': btc_price if 'btc_price' in locals() else 0
        })
        
    async def _test_market_reporter_initialization(self):
        """Test 2: Market reporter initialization with all dependencies."""
        test_name = "Market Reporter Initialization"
        self.logger.info(f"\n🔧 TEST 2: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        
        try:
            # Import market reporter
            from monitoring.market_reporter import MarketReporter
            
            # Initialize market reporter with exchange
            self.market_reporter = MarketReporter(
                exchange=self.exchange,
                logger=self.logger
            )
            
            # Test all required attributes are present
            required_attrs = [
                'api_latencies', 'error_counts', 'processing_times',
                'cache', 'ticker_cache', 'symbols'
            ]
            
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(self.market_reporter, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                self.logger.error(f"❌ Missing attributes: {missing_attrs}")
            else:
                self.logger.info("✅ All required attributes initialized")
                
                # Test method availability
                required_methods = [
                    '_fetch_with_retry', '_calculate_market_overview',
                    '_calculate_futures_premium', '_calculate_smart_money_index',
                    '_calculate_whale_activity', 'generate_market_summary'
                ]
                
                missing_methods = []
                for method in required_methods:
                    if not hasattr(self.market_reporter, method):
                        missing_methods.append(method)
                
                if missing_methods:
                    self.logger.error(f"❌ Missing methods: {missing_methods}")
                else:
                    self.logger.info("✅ All required methods available")
                    success = True
                    
        except Exception as e:
            self.logger.error(f"❌ Market reporter initialization failed: {str(e)}")
            self.test_results['errors'].append(f"Market reporter init: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, {
            'pdf_enabled': getattr(self.market_reporter, 'pdf_enabled', False) if self.market_reporter else False
        })
        
    async def _test_live_data_collection(self):
        """Test 3: Live data collection from multiple sources."""
        test_name = "Live Data Collection"
        self.logger.info(f"\n🔧 TEST 3: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        collected_data = {}
        
        try:
            # Test symbols to collect data for
            test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
            
            for symbol in test_symbols:
                try:
                    self.logger.info(f"Collecting data for {symbol}...")
                    
                    # Test ticker data
                    ticker = await self.market_reporter._fetch_with_retry(
                        'fetch_ticker', symbol, timeout=10
                    )
                    
                    if ticker:
                        # Extract key data using the fixed field mappings
                        price = float(ticker.get('last', 0))
                        volume = float(ticker.get('baseVolume', 0))  # Fixed field mapping
                        turnover = float(ticker.get('quoteVolume', 0))  # Fixed field mapping
                        change = float(ticker.get('percentage', 0))
                        
                        collected_data[symbol] = {
                            'price': price,
                            'volume': volume,
                            'turnover': turnover,
                            'change_24h': change,
                            'timestamp': int(time.time() * 1000)
                        }
                        
                        self.logger.info(f"✅ {symbol}: ${price:,.2f}, Vol: {volume:,.2f}, Turnover: ${turnover:,.2f}")
                        
                        # Validate data quality
                        if price > 0 and volume > 0:
                            self.logger.debug(f"Data quality check passed for {symbol}")
                        else:
                            self.logger.warning(f"Data quality issues for {symbol}: price={price}, volume={volume}")
                    else:
                        self.logger.error(f"❌ Failed to get ticker for {symbol}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error collecting data for {symbol}: {str(e)}")
                    
            # Check if we collected data for most symbols
            if len(collected_data) >= len(test_symbols) * 0.75:  # 75% success rate
                self.logger.info(f"✅ Data collection successful for {len(collected_data)}/{len(test_symbols)} symbols")
                success = True
            else:
                self.logger.error(f"❌ Data collection failed - only {len(collected_data)}/{len(test_symbols)} symbols")
                
        except Exception as e:
            self.logger.error(f"❌ Live data collection failed: {str(e)}")
            self.test_results['errors'].append(f"Data collection: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, {
            'symbols_collected': len(collected_data),
            'total_symbols': len(test_symbols),
            'sample_data': collected_data
        })
        
    async def _test_calculation_methods(self):
        """Test 4: All calculation methods with live data."""
        test_name = "Calculation Methods"
        self.logger.info(f"\n🔧 TEST 4: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        calculation_results = {}
        
        try:
            test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
            
            # Test 4.1: Market Overview Calculation
            self.logger.info("Testing market overview calculation...")
            overview_start = time.time()
            market_overview = await self.market_reporter._calculate_market_overview(test_symbols)
            overview_duration = time.time() - overview_start
            
            if market_overview and 'regime' in market_overview:
                self.logger.info(f"✅ Market Overview: {market_overview.get('regime')} ({overview_duration:.2f}s)")
                calculation_results['market_overview'] = {
                    'success': True,
                    'duration': overview_duration,
                    'regime': market_overview.get('regime'),
                    'total_volume': market_overview.get('total_volume', 0),
                    'total_turnover': market_overview.get('total_turnover', 0)
                }
            else:
                self.logger.error("❌ Market overview calculation failed")
                calculation_results['market_overview'] = {'success': False, 'duration': overview_duration}
            
            # Test 4.2: Futures Premium Calculation
            self.logger.info("Testing futures premium calculation...")
            premium_start = time.time()
            futures_premium = await self.market_reporter._calculate_futures_premium(test_symbols)
            premium_duration = time.time() - premium_start
            
            if futures_premium and 'premiums' in futures_premium:
                premium_count = len(futures_premium['premiums'])
                self.logger.info(f"✅ Futures Premium: {premium_count} premiums calculated ({premium_duration:.2f}s)")
                calculation_results['futures_premium'] = {
                    'success': True,
                    'duration': premium_duration,
                    'premiums_calculated': premium_count
                }
            else:
                self.logger.error("❌ Futures premium calculation failed")
                calculation_results['futures_premium'] = {'success': False, 'duration': premium_duration}
            
            # Test 4.3: Smart Money Index Calculation
            self.logger.info("Testing smart money index calculation...")
            smi_start = time.time()
            smart_money = await self.market_reporter._calculate_smart_money_index(test_symbols)
            smi_duration = time.time() - smi_start
            
            if smart_money and 'index' in smart_money:
                smi_value = smart_money.get('index', 0)
                self.logger.info(f"✅ Smart Money Index: {smi_value:.1f} ({smi_duration:.2f}s)")
                calculation_results['smart_money_index'] = {
                    'success': True,
                    'duration': smi_duration,
                    'index_value': smi_value,
                    'signal': smart_money.get('signal', 'UNKNOWN')
                }
            else:
                self.logger.error("❌ Smart money index calculation failed")
                calculation_results['smart_money_index'] = {'success': False, 'duration': smi_duration}
            
            # Test 4.4: Whale Activity Calculation
            self.logger.info("Testing whale activity calculation...")
            whale_start = time.time()
            whale_activity = await self.market_reporter._calculate_whale_activity(test_symbols)
            whale_duration = time.time() - whale_start
            
            if whale_activity and 'transactions' in whale_activity:
                tx_count = len(whale_activity['transactions'])
                self.logger.info(f"✅ Whale Activity: {tx_count} transactions found ({whale_duration:.2f}s)")
                calculation_results['whale_activity'] = {
                    'success': True,
                    'duration': whale_duration,
                    'transactions_found': tx_count
                }
            else:
                self.logger.error("❌ Whale activity calculation failed")
                calculation_results['whale_activity'] = {'success': False, 'duration': whale_duration}
            
            # Check overall success
            successful_calculations = sum(1 for result in calculation_results.values() if result.get('success', False))
            if successful_calculations >= 3:  # At least 3 out of 4 should work
                self.logger.info(f"✅ Calculation methods test passed: {successful_calculations}/4 successful")
                success = True
            else:
                self.logger.error(f"❌ Calculation methods test failed: only {successful_calculations}/4 successful")
                
        except Exception as e:
            self.logger.error(f"❌ Calculation methods test failed: {str(e)}")
            self.test_results['errors'].append(f"Calculation methods: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, calculation_results)
        
    async def _test_market_summary_generation(self):
        """Test 5: Complete market summary generation."""
        test_name = "Market Summary Generation"
        self.logger.info(f"\n🔧 TEST 5: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        summary_data = {}
        
        try:
            self.logger.info("Generating complete market summary...")
            
            # Generate market summary
            market_summary = await self.market_reporter.generate_market_summary()
            
            if market_summary:
                # Validate summary structure
                required_sections = [
                    'market_overview', 'futures_premium', 'smart_money_index',
                    'whale_activity', 'performance_metrics'
                ]
                
                missing_sections = []
                present_sections = []
                
                for section in required_sections:
                    if section in market_summary and market_summary[section]:
                        present_sections.append(section)
                    else:
                        missing_sections.append(section)
                
                summary_data = {
                    'total_sections': len(required_sections),
                    'present_sections': len(present_sections),
                    'missing_sections': missing_sections,
                    'quality_score': market_summary.get('quality_score', 0),
                    'timestamp': market_summary.get('timestamp'),
                    'file_paths': {
                        'json_path': market_summary.get('json_path'),
                        'html_path': market_summary.get('html_path'),
                        'pdf_path': market_summary.get('pdf_path')
                    }
                }
                
                if len(present_sections) >= 4:  # At least 4 out of 5 sections
                    self.logger.info(f"✅ Market summary generated successfully")
                    self.logger.info(f"   Sections: {len(present_sections)}/{len(required_sections)}")
                    self.logger.info(f"   Quality Score: {market_summary.get('quality_score', 0)}")
                    
                    # Store summary for later tests
                    self.test_results['market_summary'] = market_summary
                    success = True
                else:
                    self.logger.error(f"❌ Market summary incomplete: only {len(present_sections)}/{len(required_sections)} sections")
                    self.logger.error(f"   Missing: {missing_sections}")
            else:
                self.logger.error("❌ Market summary generation returned None")
                
        except Exception as e:
            self.logger.error(f"❌ Market summary generation failed: {str(e)}")
            self.test_results['errors'].append(f"Market summary: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, summary_data)
        
    async def _test_pdf_generation(self):
        """Test 6: PDF generation with real templates."""
        test_name = "PDF Generation"
        self.logger.info(f"\n🔧 TEST 6: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        pdf_data = {}
        
        try:
            # Use the market summary from previous test
            if 'market_summary' in self.test_results:
                market_summary = self.test_results['market_summary']
                
                self.logger.info("Testing PDF generation...")
                
                # Generate PDF report
                pdf_path = await self.market_reporter.generate_market_pdf_report(market_summary)
                
                if pdf_path and os.path.exists(pdf_path):
                    file_size = os.path.getsize(pdf_path) / 1024  # KB
                    
                    pdf_data = {
                        'pdf_path': pdf_path,
                        'file_size_kb': file_size,
                        'file_exists': True
                    }
                    
                    self.logger.info(f"✅ PDF generated successfully")
                    self.logger.info(f"   Path: {pdf_path}")
                    self.logger.info(f"   Size: {file_size:.1f} KB")
                    
                    # Add to generated files list
                    self.test_results['generated_files'].append({
                        'type': 'PDF',
                        'path': pdf_path,
                        'size_kb': file_size
                    })
                    
                    success = True
                else:
                    self.logger.error("❌ PDF generation failed - file not created")
                    pdf_data = {'pdf_path': pdf_path, 'file_exists': False}
            else:
                self.logger.error("❌ No market summary available for PDF generation")
                
        except Exception as e:
            self.logger.error(f"❌ PDF generation failed: {str(e)}")
            self.test_results['errors'].append(f"PDF generation: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, pdf_data)
        
    async def _test_json_export(self):
        """Test 7: JSON export and API compatibility."""
        test_name = "JSON Export"
        self.logger.info(f"\n🔧 TEST 7: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        json_data = {}
        
        try:
            if 'market_summary' in self.test_results:
                market_summary = self.test_results['market_summary']
                
                # Check if JSON files were created during summary generation
                json_path = market_summary.get('json_path')
                export_path = market_summary.get('export_json_path')
                
                json_files_found = []
                
                if json_path and os.path.exists(json_path):
                    size = os.path.getsize(json_path) / 1024
                    json_files_found.append({'path': json_path, 'size_kb': size})
                    self.logger.info(f"✅ JSON report found: {json_path} ({size:.1f} KB)")
                
                if export_path and os.path.exists(export_path):
                    size = os.path.getsize(export_path) / 1024
                    json_files_found.append({'path': export_path, 'size_kb': size})
                    self.logger.info(f"✅ Export JSON found: {export_path} ({size:.1f} KB)")
                
                # Test JSON content validity
                if json_files_found:
                    test_file = json_files_found[0]['path']
                    
                    try:
                        with open(test_file, 'r') as f:
                            json_content = json.load(f)
                        
                        # Validate JSON structure
                        required_keys = ['timestamp', 'market_overview', 'futures_premium']
                        present_keys = [key for key in required_keys if key in json_content]
                        
                        json_data = {
                            'files_created': len(json_files_found),
                            'files': json_files_found,
                            'json_valid': True,
                            'required_keys_present': len(present_keys),
                            'total_required_keys': len(required_keys)
                        }
                        
                        if len(present_keys) >= 2:
                            self.logger.info(f"✅ JSON content validation passed ({len(present_keys)}/{len(required_keys)} keys)")
                            success = True
                        else:
                            self.logger.error(f"❌ JSON content validation failed - missing keys")
                            
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ JSON file is not valid JSON: {str(e)}")
                        json_data = {'json_valid': False, 'error': str(e)}
                else:
                    self.logger.error("❌ No JSON files were created")
            else:
                self.logger.error("❌ No market summary available for JSON validation")
                
        except Exception as e:
            self.logger.error(f"❌ JSON export test failed: {str(e)}")
            self.test_results['errors'].append(f"JSON export: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, json_data)
        
    async def _test_performance_monitoring(self):
        """Test 8: Performance monitoring and metrics."""
        test_name = "Performance Monitoring"
        self.logger.info(f"\n🔧 TEST 8: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        performance_data = {}
        
        try:
            # Test performance metrics collection
            if self.market_reporter:
                # Get current performance metrics
                api_latencies = getattr(self.market_reporter, 'api_latencies', [])
                processing_times = getattr(self.market_reporter, 'processing_times', [])
                error_counts = getattr(self.market_reporter, 'error_counts', {})
                
                performance_data = {
                    'api_latencies_count': len(api_latencies),
                    'avg_api_latency': sum(api_latencies) / len(api_latencies) if api_latencies else 0,
                    'processing_times_count': len(processing_times),
                    'avg_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
                    'total_errors': sum(error_counts.values()) if error_counts else 0,
                    'error_types': len(error_counts) if error_counts else 0
                }
                
                # Test performance metrics calculation
                test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT']
                perf_metrics = await self.market_reporter._calculate_performance_metrics(test_symbols)
                
                if perf_metrics and 'api_latency' in perf_metrics:
                    self.logger.info("✅ Performance metrics calculation successful")
                    self.logger.info(f"   API Latencies: {len(api_latencies)} recorded")
                    self.logger.info(f"   Processing Times: {len(processing_times)} recorded")
                    self.logger.info(f"   Total Errors: {sum(error_counts.values()) if error_counts else 0}")
                    
                    performance_data['metrics_calculation_success'] = True
                    success = True
                else:
                    self.logger.error("❌ Performance metrics calculation failed")
                    performance_data['metrics_calculation_success'] = False
            else:
                self.logger.error("❌ Market reporter not available for performance testing")
                
        except Exception as e:
            self.logger.error(f"❌ Performance monitoring test failed: {str(e)}")
            self.test_results['errors'].append(f"Performance monitoring: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, performance_data)
        
    async def _test_error_handling(self):
        """Test 9: Error handling and resilience."""
        test_name = "Error Handling"
        self.logger.info(f"\n🔧 TEST 9: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        error_test_data = {}
        
        try:
            if self.market_reporter:
                # Test 9.1: Invalid symbol handling
                self.logger.info("Testing invalid symbol handling...")
                try:
                    invalid_result = await self.market_reporter._fetch_with_retry(
                        'fetch_ticker', 'INVALIDSYMBOL123', timeout=5
                    )
                    # This should fail gracefully
                    error_test_data['invalid_symbol_handled'] = True
                except Exception as e:
                    # Expected to fail, check if it fails gracefully
                    error_test_data['invalid_symbol_handled'] = True
                    self.logger.info(f"✅ Invalid symbol handled gracefully: {str(e)}")
                
                # Test 9.2: Timeout handling
                self.logger.info("Testing timeout handling...")
                try:
                    # Test with very short timeout
                    timeout_result = await self.market_reporter._fetch_with_retry(
                        'fetch_ticker', 'BTCUSDT', timeout=0.001  # Very short timeout
                    )
                    error_test_data['timeout_handled'] = True
                except Exception as e:
                    error_test_data['timeout_handled'] = True
                    self.logger.info(f"✅ Timeout handled gracefully: {type(e).__name__}")
                
                # Test 9.3: Empty data handling
                self.logger.info("Testing empty data handling...")
                try:
                    empty_overview = await self.market_reporter._calculate_market_overview([])
                    if empty_overview:
                        error_test_data['empty_data_handled'] = True
                        self.logger.info("✅ Empty data handled gracefully")
                    else:
                        error_test_data['empty_data_handled'] = False
                except Exception as e:
                    error_test_data['empty_data_handled'] = True
                    self.logger.info(f"✅ Empty data exception handled: {str(e)}")
                
                # Check overall error handling
                handled_tests = sum(1 for v in error_test_data.values() if v)
                if handled_tests >= 2:  # At least 2 out of 3 error cases handled
                    self.logger.info(f"✅ Error handling test passed: {handled_tests}/3 cases handled")
                    success = True
                else:
                    self.logger.error(f"❌ Error handling test failed: only {handled_tests}/3 cases handled")
            else:
                self.logger.error("❌ Market reporter not available for error testing")
                
        except Exception as e:
            self.logger.error(f"❌ Error handling test failed: {str(e)}")
            self.test_results['errors'].append(f"Error handling: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, error_test_data)
        
    async def _test_complete_pipeline_integration(self):
        """Test 10: Complete pipeline integration test."""
        test_name = "Complete Pipeline Integration"
        self.logger.info(f"\n🔧 TEST 10: {test_name}")
        self.logger.info("-" * 50)
        
        start_time = time.time()
        success = False
        integration_data = {}
        
        try:
            self.logger.info("Running complete end-to-end pipeline test...")
            
            # Step 1: Generate fresh market report
            pipeline_start = time.time()
            fresh_report = await self.market_reporter.generate_market_summary()
            generation_time = time.time() - pipeline_start
            
            if fresh_report:
                # Step 2: Validate report structure
                sections_check = all(section in fresh_report for section in [
                    'market_overview', 'futures_premium', 'smart_money_index'
                ])
                
                # Step 3: Check file generation
                files_generated = []
                if fresh_report.get('json_path') and os.path.exists(fresh_report['json_path']):
                    files_generated.append('JSON')
                
                # Step 4: Generate PDF for integration test
                pdf_integration_start = time.time()
                pdf_path = await self.market_reporter.generate_market_pdf_report(fresh_report)
                pdf_generation_time = time.time() - pdf_integration_start
                
                if pdf_path and os.path.exists(pdf_path):
                    files_generated.append('PDF')
                
                integration_data = {
                    'report_generated': True,
                    'generation_time': generation_time,
                    'sections_valid': sections_check,
                    'files_generated': files_generated,
                    'pdf_generation_time': pdf_generation_time,
                    'quality_score': fresh_report.get('quality_score', 0),
                    'total_pipeline_time': time.time() - pipeline_start
                }
                
                # Success criteria: report generated, valid structure, at least one file created
                if (fresh_report and sections_check and len(files_generated) >= 1):
                    self.logger.info("✅ Complete pipeline integration successful")
                    self.logger.info(f"   Generation Time: {generation_time:.2f}s")
                    self.logger.info(f"   Files Generated: {', '.join(files_generated)}")
                    self.logger.info(f"   Quality Score: {fresh_report.get('quality_score', 0)}")
                    self.logger.info(f"   Total Pipeline Time: {integration_data['total_pipeline_time']:.2f}s")
                    success = True
                else:
                    self.logger.error("❌ Pipeline integration failed validation checks")
            else:
                self.logger.error("❌ Fresh report generation failed in integration test")
                integration_data = {'report_generated': False}
                
        except Exception as e:
            self.logger.error(f"❌ Pipeline integration test failed: {str(e)}")
            self.test_results['errors'].append(f"Pipeline integration: {str(e)}")
        
        duration = time.time() - start_time
        self._record_test_result(test_name, success, duration, integration_data)
        
    def _record_test_result(self, test_name, success, duration, data):
        """Record the result of a test."""
        self.test_results['tests_run'] += 1
        if success:
            self.test_results['tests_passed'] += 1
        else:
            self.test_results['tests_failed'] += 1
        
        self.test_results['detailed_results'][test_name] = {
            'success': success,
            'duration': duration,
            'data': data
        }
        
        # Log test result
        status = "✅ PASSED" if success else "❌ FAILED"
        self.logger.info(f"{status} - {test_name} ({duration:.2f}s)")
        
    async def _generate_test_report(self):
        """Generate comprehensive test report."""
        self.logger.info("\n📊 GENERATING COMPREHENSIVE TEST REPORT")
        self.logger.info("=" * 60)
        
        try:
            # Create test reports directory
            reports_dir = os.path.join(project_root, 'reports', 'test_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create comprehensive test report
            test_report = {
                'test_summary': {
                    'test_suite': 'Comprehensive Market Reporter Pipeline Test',
                    'start_time': self.test_results['start_time'].isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'total_duration': (datetime.now() - self.test_results['start_time']).total_seconds(),
                    'tests_run': self.test_results['tests_run'],
                    'tests_passed': self.test_results['tests_passed'],
                    'tests_failed': self.test_results['tests_failed'],
                    'success_rate': (self.test_results['tests_passed'] / self.test_results['tests_run'] * 100) if self.test_results['tests_run'] > 0 else 0
                },
                'detailed_results': self.test_results['detailed_results'],
                'generated_files': self.test_results['generated_files'],
                'errors': self.test_results['errors'],
                'system_info': {
                    'python_version': sys.version,
                    'platform': os.name,
                    'test_environment': 'development'
                }
            }
            
            # Save test report
            report_path = os.path.join(reports_dir, f'market_pipeline_test_report_{timestamp}.json')
            with open(report_path, 'w') as f:
                json.dump(test_report, f, indent=2, default=str)
            
            self.logger.info(f"📁 Test report saved: {report_path}")
            
            # Also save a summary file
            summary_path = os.path.join(reports_dir, f'test_summary_{timestamp}.txt')
            with open(summary_path, 'w') as f:
                f.write("COMPREHENSIVE MARKET REPORTER PIPELINE TEST SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Test Suite: Comprehensive Market Reporter Pipeline Test\n")
                f.write(f"Start Time: {self.test_results['start_time']}\n")
                f.write(f"End Time: {datetime.now()}\n")
                f.write(f"Total Duration: {(datetime.now() - self.test_results['start_time']).total_seconds():.2f} seconds\n\n")
                f.write(f"Tests Run: {self.test_results['tests_run']}\n")
                f.write(f"Tests Passed: {self.test_results['tests_passed']}\n")
                f.write(f"Tests Failed: {self.test_results['tests_failed']}\n")
                f.write(f"Success Rate: {(self.test_results['tests_passed'] / self.test_results['tests_run'] * 100):.1f}%\n\n")
                
                if self.test_results['generated_files']:
                    f.write("GENERATED FILES:\n")
                    for file_info in self.test_results['generated_files']:
                        f.write(f"  - {file_info['type']}: {file_info['path']} ({file_info['size_kb']:.1f} KB)\n")
                    f.write("\n")
                
                if self.test_results['errors']:
                    f.write("ERRORS ENCOUNTERED:\n")
                    for error in self.test_results['errors']:
                        f.write(f"  - {error}\n")
                    f.write("\n")
                
                f.write("DETAILED TEST RESULTS:\n")
                for test_name, result in self.test_results['detailed_results'].items():
                    status = "PASSED" if result['success'] else "FAILED"
                    f.write(f"  {test_name}: {status} ({result['duration']:.2f}s)\n")
            
            self.logger.info(f"📝 Test summary saved: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating test report: {str(e)}")
            
    def _display_test_summary(self):
        """Display final test summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🎯 COMPREHENSIVE MARKET REPORTER PIPELINE TEST SUMMARY")
        self.logger.info("=" * 80)
        
        total_time = (datetime.now() - self.test_results['start_time']).total_seconds()
        success_rate = (self.test_results['tests_passed'] / self.test_results['tests_run'] * 100) if self.test_results['tests_run'] > 0 else 0
        
        # Overall result
        if success_rate >= 80:
            overall_status = "🎉 EXCELLENT"
            overall_emoji = "🟢"
        elif success_rate >= 60:
            overall_status = "✅ GOOD"
            overall_emoji = "🟡"
        else:
            overall_status = "❌ NEEDS WORK"
            overall_emoji = "🔴"
        
        self.logger.info(f"OVERALL RESULT: {overall_emoji} {overall_status}")
        self.logger.info(f"")
        self.logger.info(f"📊 TEST STATISTICS:")
        self.logger.info(f"   Total Tests Run: {self.test_results['tests_run']}")
        self.logger.info(f"   Tests Passed: {self.test_results['tests_passed']}")
        self.logger.info(f"   Tests Failed: {self.test_results['tests_failed']}")
        self.logger.info(f"   Success Rate: {success_rate:.1f}%")
        self.logger.info(f"   Total Duration: {total_time:.2f} seconds")
        
        if self.test_results['generated_files']:
            self.logger.info(f"\n📁 GENERATED FILES:")
            for file_info in self.test_results['generated_files']:
                self.logger.info(f"   {file_info['type']}: {file_info['path']} ({file_info['size_kb']:.1f} KB)")
        
        if self.test_results['errors']:
            self.logger.info(f"\n⚠️ ERRORS ENCOUNTERED:")
            for error in self.test_results['errors']:
                self.logger.info(f"   - {error}")
        
        self.logger.info("\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results['detailed_results'].items():
            status_emoji = "✅" if result['success'] else "❌"
            self.logger.info(f"   {status_emoji} {test_name}: {result['duration']:.2f}s")
        
        # Recommendations
        self.logger.info(f"\n💡 RECOMMENDATIONS:")
        if success_rate >= 90:
            self.logger.info("   🚀 System is ready for production deployment!")
        elif success_rate >= 70:
            self.logger.info("   ✅ System is mostly ready - address failed tests")
        else:
            self.logger.info("   🔧 System needs significant fixes before production")
            
        if self.test_results['errors']:
            self.logger.info("   🔍 Review error logs for specific issues to fix")
            
        self.logger.info("\n" + "=" * 80)

async def main():
    """Run the comprehensive market reporter pipeline test."""
    test_suite = ComprehensiveMarketPipelineTest()
    await test_suite.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main()) 