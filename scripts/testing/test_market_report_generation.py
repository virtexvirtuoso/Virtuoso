#!/usr/bin/env python3
"""
Test script to diagnose market report PDF generation issues.
This script will test the market report generation process step by step.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

async def test_market_report_generation():
    """Test the complete market report generation process."""
    
    logger = setup_logging()
    logger.info("🧪 Testing Market Report Generation Process")
    print("=" * 60)
    
    try:
        # Test 1: Import required modules
        print("📦 Testing imports...")
        try:
            from monitoring.market_reporter import MarketReporter
            from monitoring.alert_manager import AlertManager
            from core.reporting.report_manager import ReportManager
            from core.reporting.pdf_generator import ReportGenerator
            print("  ✅ All required modules imported successfully")
        except ImportError as e:
            print(f"  ❌ Import error: {e}")
            return False
        
        # Test 2: Check template directory
        print("\n📁 Testing template directory...")
        template_dir = os.path.join(os.getcwd(), 'src', 'core', 'reporting', 'templates')
        if os.path.exists(template_dir):
            print(f"  ✅ Template directory exists: {template_dir}")
            template_files = [f for f in os.listdir(template_dir) if f.endswith('.html')]
            print(f"  📄 Template files found: {template_files}")
            
            market_template = os.path.join(template_dir, 'market_report_dark.html')
            if os.path.exists(market_template):
                print(f"  ✅ Market report template exists: {market_template}")
            else:
                print(f"  ❌ Market report template missing: {market_template}")
                return False
        else:
            print(f"  ❌ Template directory missing: {template_dir}")
            return False
        
        # Test 3: Check output directories
        print("\n📂 Testing output directories...")
        reports_dir = os.path.join(os.getcwd(), 'reports')
        pdf_dir = os.path.join(reports_dir, 'pdf')
        html_dir = os.path.join(reports_dir, 'html')
        
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)
        
        print(f"  ✅ PDF directory: {pdf_dir}")
        print(f"  ✅ HTML directory: {html_dir}")
        
        # Test 4: Initialize components
        print("\n🔧 Testing component initialization...")
        
        # Create alert manager in test mode
        test_config = {
            'monitoring': {
                'alerts': {
                    'mock_mode': True,
                    'capture_alerts': True
                }
            }
        }
        alert_manager = AlertManager(test_config)
        print("  ✅ Alert manager initialized")
        
        # Create market reporter
        market_reporter = MarketReporter(alert_manager=alert_manager)
        print("  ✅ Market reporter initialized")
        
        # Test 5: Generate sample market data
        print("\n📊 Testing market data generation...")
        try:
            # Generate a simple market summary
            market_summary = await market_reporter.generate_market_summary()
            if market_summary:
                print("  ✅ Market summary generated successfully")
                print(f"  📈 Market overview available: {'market_overview' in market_summary}")
                print(f"  🏦 Smart money data available: {'smart_money_index' in market_summary}")
                print(f"  🐋 Whale activity available: {'whale_activity' in market_summary}")
            else:
                print("  ❌ Failed to generate market summary")
                return False
        except Exception as e:
            print(f"  ❌ Error generating market summary: {e}")
            return False
        
        # Test 6: Test PDF generation components
        print("\n📄 Testing PDF generation components...")
        try:
            # Initialize report manager
            report_manager = ReportManager()
            await report_manager.start()
            print("  ✅ Report manager initialized")
            
            # Check if PDF generator is available
            if hasattr(report_manager, 'pdf_generator') and report_manager.pdf_generator:
                print("  ✅ PDF generator available")
                
                # Test template directory
                pdf_template_dir = getattr(report_manager.pdf_generator, 'template_dir', None)
                print(f"  📁 PDF generator template dir: {pdf_template_dir}")
                
            else:
                print("  ❌ PDF generator not available")
                return False
                
        except Exception as e:
            print(f"  ❌ Error initializing PDF components: {e}")
            return False
        
        # Test 7: Test actual PDF generation
        print("\n🎯 Testing actual PDF generation...")
        try:
            timestamp = int(datetime.now().timestamp())
            readable_time = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
            report_id = f"TEST_{readable_time}"
            
            # Define paths
            html_path = os.path.join(html_dir, f"market_report_{report_id}.html")
            pdf_path = os.path.join(pdf_dir, f"market_report_{report_id}.pdf")
            
            print(f"  📄 HTML path: {html_path}")
            print(f"  📑 PDF path: {pdf_path}")
            
            # Prepare market data for PDF generation
            market_pdf_data = {
                'timestamp': timestamp,
                'market_overview': market_summary.get('market_overview', {}),
                'smart_money_index': market_summary.get('smart_money_index', {}),
                'whale_activity': market_summary.get('whale_activity', {}),
                'futures_premium': market_summary.get('futures_premium', {}),
                'performance_metrics': market_summary.get('performance_metrics', {})
            }
            
            # Test PDF generation
            pdf_success = await report_manager.pdf_generator.generate_market_html_report(
                market_data=market_pdf_data,
                output_path=html_path,
                generate_pdf=True
            )
            
            if pdf_success:
                print("  ✅ PDF generation reported success")
                
                # Check if files actually exist
                if os.path.exists(html_path):
                    print(f"  ✅ HTML file created: {os.path.getsize(html_path)} bytes")
                else:
                    print("  ❌ HTML file not found")
                
                expected_pdf_path = pdf_path  # Use the correct PDF path
                if os.path.exists(expected_pdf_path):
                    print(f"  ✅ PDF file created: {os.path.getsize(expected_pdf_path)} bytes")
                    print(f"  📑 PDF location: {expected_pdf_path}")
                else:
                    print(f"  ❌ PDF file not found at: {expected_pdf_path}")
                    return False
                    
            else:
                print("  ❌ PDF generation failed")
                return False
                
        except Exception as e:
            print(f"  ❌ Error during PDF generation: {e}")
            import traceback
            print(f"  🔍 Traceback: {traceback.format_exc()}")
            return False
        
        # Test 8: Test Discord message formatting
        print("\n💬 Testing Discord message formatting...")
        try:
            formatted_report = await market_reporter.format_market_report(
                overview=market_summary.get('market_overview', {}),
                top_pairs=['BTC/USDT', 'ETH/USDT'],
                smart_money=market_summary.get('smart_money_index', {}),
                whale_activity=market_summary.get('whale_activity', {})
            )
            
            if formatted_report and 'embeds' in formatted_report:
                print(f"  ✅ Discord message formatted with {len(formatted_report['embeds'])} embeds")
                embed_titles = [e.get('title', 'No title') for e in formatted_report['embeds']]
                print(f"  📋 Embed titles: {embed_titles}")
            else:
                print("  ❌ Failed to format Discord message")
                return False
                
        except Exception as e:
            print(f"  ❌ Error formatting Discord message: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! Market report generation should work correctly.")
        print("\n📋 Summary:")
        print("  ✅ All modules imported successfully")
        print("  ✅ Template directory and files exist")
        print("  ✅ Output directories created")
        print("  ✅ Components initialized correctly")
        print("  ✅ Market data generated successfully")
        print("  ✅ PDF generation working")
        print("  ✅ Discord message formatting working")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_market_report_generation())
    if not success:
        print("\n💥 Tests failed! Check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ All tests completed successfully!") 