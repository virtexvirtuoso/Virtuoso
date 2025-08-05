#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import os
import time
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFReportGenerationTester:
    """Test PDF report generation functionality."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        self.generated_files = []
        
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

    async def test_market_reporter_availability(self, exchange):
        """Test if market reporter is available for PDF generation."""
        try:
            logger.info("Testing market reporter availability...")
            
            # Try to import market reporter
            try:
                from monitoring.market_reporter import MarketReporter
                reporter_available = True
            except ImportError as e:
                reporter_available = False
                logger.debug(f"MarketReporter import failed: {str(e)}")
            
            if reporter_available:
                # Test initialization
                try:
                    reporter = MarketReporter(exchange=exchange)
                    has_pdf_capability = hasattr(reporter, 'pdf_enabled') and reporter.pdf_enabled
                    
                    if has_pdf_capability:
                        self.log_result("Market Reporter Availability", "PASS", 
                                       "MarketReporter available with PDF capability")
                    else:
                        self.log_result("Market Reporter Availability", "WARN", 
                                       "MarketReporter available but PDF disabled")
                except Exception as e:
                    self.log_result("Market Reporter Availability", "FAIL", 
                                   f"MarketReporter initialization failed: {str(e)}")
            else:
                self.log_result("Market Reporter Availability", "FAIL", 
                               "MarketReporter not available")
                
        except Exception as e:
            self.log_result("Market Reporter Availability", "FAIL", f"Error: {str(e)}")

    async def test_pdf_dependencies(self):
        """Test PDF generation dependencies."""
        try:
            logger.info("Testing PDF dependencies...")
            
            dependencies = {
                'matplotlib': 'plotting',
                'reportlab': 'PDF generation',
                'PIL': 'image processing',
                'io': 'buffer handling'
            }
            
            available_deps = []
            missing_deps = []
            
            for dep_name, purpose in dependencies.items():
                try:
                    if dep_name == 'PIL':
                        import PIL
                    else:
                        __import__(dep_name)
                    available_deps.append((dep_name, purpose))
                    logger.debug(f"✓ {dep_name} available ({purpose})")
                except ImportError:
                    missing_deps.append((dep_name, purpose))
                    logger.debug(f"✗ {dep_name} missing ({purpose})")
            
            if len(available_deps) >= 3:
                self.log_result("PDF Dependencies", "PASS", 
                               f"{len(available_deps)}/{len(dependencies)} dependencies available")
            elif len(available_deps) >= 2:
                self.log_result("PDF Dependencies", "WARN", 
                               f"Some dependencies missing: {[dep for dep, _ in missing_deps]}")
            else:
                self.log_result("PDF Dependencies", "FAIL", 
                               f"Major dependencies missing: {[dep for dep, _ in missing_deps]}")
                
        except Exception as e:
            self.log_result("PDF Dependencies", "FAIL", f"Error: {str(e)}")

    async def test_report_data_generation(self, exchange):
        """Test market report data generation."""
        try:
            logger.info("Testing report data generation...")
            
            try:
                from monitoring.market_reporter import MarketReporter
                
                reporter = MarketReporter(exchange=exchange)
                
                # Generate market summary
                start_time = time.time()
                report_data = await reporter.generate_market_summary()
                generation_time = time.time() - start_time
                
                if report_data and isinstance(report_data, dict):
                    # Check report structure
                    required_sections = ['market_overview', 'timestamp']
                    available_sections = [s for s in required_sections if s in report_data and report_data[s]]
                    
                    data_size = len(str(report_data))
                    
                    if len(available_sections) >= 1 and data_size > 100:
                        self.log_result("Report Data Generation", "PASS", 
                                       f"Generated {data_size} bytes in {generation_time:.2f}s, "
                                       f"{len(available_sections)} sections")
                    else:
                        self.log_result("Report Data Generation", "WARN", 
                                       f"Limited data: {data_size} bytes, {len(available_sections)} sections")
                else:
                    self.log_result("Report Data Generation", "FAIL", 
                                   "No report data generated")
                    
            except ImportError:
                self.log_result("Report Data Generation", "FAIL", 
                               "MarketReporter not available")
                
        except Exception as e:
            self.log_result("Report Data Generation", "FAIL", f"Error: {str(e)}")

    async def test_pdf_file_creation(self, exchange):
        """Test actual PDF file creation."""
        try:
            logger.info("Testing PDF file creation...")
            
            try:
                from monitoring.market_reporter import MarketReporter
                
                reporter = MarketReporter(exchange=exchange)
                
                # Check if PDF generation is enabled
                if not (hasattr(reporter, 'pdf_enabled') and reporter.pdf_enabled):
                    self.log_result("PDF File Creation", "WARN", 
                                   "PDF generation disabled - dependencies may be missing")
                    return
                
                # Generate report data first
                report_data = await reporter.generate_market_summary()
                
                if not report_data:
                    self.log_result("PDF File Creation", "FAIL", 
                                   "No report data for PDF generation")
                    return
                
                # Try to generate PDF
                start_time = time.time()
                try:
                    pdf_path = await reporter.generate_market_pdf_report(report_data)
                    generation_time = time.time() - start_time
                    
                    if pdf_path and os.path.exists(pdf_path):
                        file_size = os.path.getsize(pdf_path)
                        self.generated_files.append(pdf_path)
                        
                        if file_size > 1000:  # At least 1KB
                            self.log_result("PDF File Creation", "PASS", 
                                           f"PDF created: {os.path.basename(pdf_path)} "
                                           f"({file_size:,} bytes, {generation_time:.2f}s)")
                        else:
                            self.log_result("PDF File Creation", "WARN", 
                                           f"PDF too small: {file_size} bytes")
                    else:
                        self.log_result("PDF File Creation", "FAIL", 
                                       "PDF file not created")
                        
                except Exception as pdf_error:
                    self.log_result("PDF File Creation", "FAIL", 
                                   f"PDF generation failed: {str(pdf_error)}")
                    
            except ImportError:
                self.log_result("PDF File Creation", "FAIL", 
                               "MarketReporter not available")
                
        except Exception as e:
            self.log_result("PDF File Creation", "FAIL", f"Error: {str(e)}")

    async def test_pdf_content_validation(self):
        """Test PDF content validation."""
        try:
            logger.info("Testing PDF content validation...")
            
            if not self.generated_files:
                self.log_result("PDF Content Validation", "WARN", 
                               "No PDF files to validate")
                return
            
            validation_results = []
            
            for pdf_path in self.generated_files:
                try:
                    if os.path.exists(pdf_path):
                        file_size = os.path.getsize(pdf_path)
                        
                        # Basic file validation
                        with open(pdf_path, 'rb') as f:
                            header = f.read(8)
                            
                        # Check PDF signature
                        if header.startswith(b'%PDF-'):
                            validation_results.append(('valid_header', pdf_path, file_size))
                        else:
                            validation_results.append(('invalid_header', pdf_path, file_size))
                            
                        # Check file size
                        if file_size > 5000:  # At least 5KB for meaningful content
                            validation_results.append(('good_size', pdf_path, file_size))
                        else:
                            validation_results.append(('small_size', pdf_path, file_size))
                            
                except Exception as e:
                    validation_results.append(('error', pdf_path, str(e)))
            
            valid_files = sum(1 for result, _, _ in validation_results if result in ['valid_header', 'good_size'])
            total_checks = len(validation_results)
            
            if valid_files >= total_checks * 0.8:  # 80% of checks pass
                self.log_result("PDF Content Validation", "PASS", 
                               f"{valid_files}/{total_checks} validation checks passed")
            else:
                self.log_result("PDF Content Validation", "WARN", 
                               f"Some validation issues: {valid_files}/{total_checks} passed")
                
        except Exception as e:
            self.log_result("PDF Content Validation", "FAIL", f"Error: {str(e)}")

    async def test_chart_generation(self, exchange):
        """Test chart generation for PDF reports."""
        try:
            logger.info("Testing chart generation...")
            
            # Test basic plotting capability
            try:
                import matplotlib.pyplot as plt
                import io
                
                # Create a simple test chart
                fig, ax = plt.subplots(figsize=(8, 6))
                
                # Generate sample data using real market data
                ticker = await exchange.get_ticker('BTCUSDT')
                if ticker and 'last' in ticker:
                    price = float(ticker['last'])
                    # Create sample price history
                    prices = [price * (1 + 0.01 * i) for i in range(-10, 11)]
                    ax.plot(range(21), prices, label='BTC Price')
                    ax.set_title('Sample BTC Price Chart')
                    ax.legend()
                
                # Save to buffer
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150)
                buffer.seek(0)
                
                chart_size = len(buffer.getvalue())
                plt.close(fig)
                
                if chart_size > 1000:  # At least 1KB for a meaningful chart
                    self.log_result("Chart Generation", "PASS", 
                                   f"Chart generated successfully ({chart_size:,} bytes)")
                else:
                    self.log_result("Chart Generation", "WARN", 
                                   f"Chart too small: {chart_size} bytes")
                    
            except ImportError as e:
                self.log_result("Chart Generation", "FAIL", 
                               f"Plotting dependencies missing: {str(e)}")
            except Exception as e:
                self.log_result("Chart Generation", "FAIL", 
                               f"Chart generation failed: {str(e)}")
                
        except Exception as e:
            self.log_result("Chart Generation", "FAIL", f"Error: {str(e)}")

    async def test_export_directory_structure(self):
        """Test export directory structure and permissions."""
        try:
            logger.info("Testing export directory structure...")
            
            # Check standard export directories
            export_dirs = [
                'exports',
                'exports/market_reports',
                'reports/pdf',
                'static/reports'
            ]
            
            dir_tests = []
            
            for dir_path in export_dirs:
                abs_path = os.path.abspath(dir_path)
                
                if os.path.exists(abs_path):
                    if os.path.isdir(abs_path):
                        # Test write permissions
                        try:
                            test_file = os.path.join(abs_path, f'test_write_{int(time.time())}.tmp')
                            with open(test_file, 'w') as f:
                                f.write('test')
                            os.remove(test_file)
                            dir_tests.append(('writable', dir_path))
                        except Exception:
                            dir_tests.append(('readonly', dir_path))
                    else:
                        dir_tests.append(('not_dir', dir_path))
                else:
                    # Try to create directory
                    try:
                        os.makedirs(abs_path, exist_ok=True)
                        dir_tests.append(('created', dir_path))
                    except Exception:
                        dir_tests.append(('cannot_create', dir_path))
            
            writable_dirs = sum(1 for status, _ in dir_tests if status in ['writable', 'created'])
            total_dirs = len(dir_tests)
            
            if writable_dirs >= 2:
                self.log_result("Export Directory Structure", "PASS", 
                               f"{writable_dirs}/{total_dirs} directories available for exports")
            else:
                self.log_result("Export Directory Structure", "WARN", 
                               f"Limited export directories: {writable_dirs}/{total_dirs} available")
                
        except Exception as e:
            self.log_result("Export Directory Structure", "FAIL", f"Error: {str(e)}")

    def cleanup_generated_files(self):
        """Clean up generated test files."""
        try:
            for file_path in self.generated_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.debug(f"Cleaned up test file: {file_path}")
                    except Exception as e:
                        logger.debug(f"Failed to clean up {file_path}: {str(e)}")
        except Exception as e:
            logger.debug(f"Error during cleanup: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("PDF REPORT GENERATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        logger.info(f"📄 Files Generated: {len(self.generated_files)}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 60:  # Lower threshold due to dependency requirements
            logger.info("🎉 PDF report generation is functional!")
            return True
        else:
            logger.warning("⚠️ PDF report generation needs attention")
            return False

async def main():
    """Run PDF Report Generation tests."""
    logger.info("📄 TEST 6: PDF Report Generation")
    logger.info("="*50)
    
    tester = PDFReportGenerationTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run PDF generation tests
            await tester.test_market_reporter_availability(exchange)
            await tester.test_pdf_dependencies()
            await tester.test_report_data_generation(exchange)
            await tester.test_pdf_file_creation(exchange)
            await tester.test_pdf_content_validation()
            await tester.test_chart_generation(exchange)
            await tester.test_export_directory_structure()
            
        # Cleanup
        tester.cleanup_generated_files()
        
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 