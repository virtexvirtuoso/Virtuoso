#!/usr/bin/env python3
"""
Bitcoin Beta 7-Day Report Runner - HTML Output

This script runs the Bitcoin Beta 7-Day Analysis Report generator with HTML output.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config.config_manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.reports.bitcoin_beta_7day_report import BitcoinBeta7DayReport, BitcoinBeta7DayReportConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bitcoin_beta_7day_report_html.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run the Bitcoin Beta 7-Day Analysis Report with HTML output."""
    try:
        print("🚀 Bitcoin Beta 7-Day Report Generator (HTML)")
        print("=" * 50)
        logger.info("=== Starting Bitcoin Beta 7-Day Report Generation (HTML) ===")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("Failed to load configuration")
            return 1
            
        logger.info("Configuration loaded successfully")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        logger.info("Exchange manager initialized")
        
        # Create report configuration with HTML output format
        report_config = BitcoinBeta7DayReportConfig(
            output_format='html',  # Request HTML output
            enable_png_export=True,  # Also create PNG charts
            png_resolution=300  # High resolution for web display
        )
        
        # Get top symbols from monitoring configuration if available
        if hasattr(config, 'monitoring') and hasattr(config.monitoring, 'target_symbols'):
            top_symbols = config.monitoring.target_symbols
            formatted_symbols = []
            for symbol in top_symbols:
                if '/' not in symbol:
                    if symbol.endswith('USDT'):
                        base = symbol[:-4]
                        formatted_symbol = f"{base}/USDT"
                        formatted_symbols.append(formatted_symbol)
                    else:
                        formatted_symbols.append(symbol)
                else:
                    formatted_symbols.append(symbol)
            
            if formatted_symbols:
                report_config.symbols = formatted_symbols
                logger.info(f"Using {len(formatted_symbols)} symbols from monitoring configuration")
        
        # Create and run the 7-day report
        report_generator = BitcoinBeta7DayReport(
            exchange_manager=exchange_manager,
            config=report_config
        )
        
        logger.info("Starting 7-day Bitcoin beta analysis (HTML output)...")
        print("\n📊 Generating 7-day Bitcoin beta analysis report (HTML)...")
        
        # Generate the report
        report_path = await report_generator.generate_report()
        
        if report_path:
            print(f"\n✅ 7-Day Bitcoin Beta Report generated successfully!")
            print(f"📄 Report saved to: {report_path}")
            
            # Check if HTML was generated
            html_path = report_path.replace('.pdf', '.html')
            if Path(html_path).exists():
                print(f"🌐 HTML version: {html_path}")
                
                # Open in browser
                import webbrowser
                webbrowser.open(f"file://{Path(html_path).absolute()}")
                print("📱 Opening HTML report in browser...")
            else:
                print("⚠️  HTML output was not generated, only PDF is available")
            
            # Check for PNG exports
            png_dir = Path(report_path).parent / 'png_exports'
            if png_dir.exists():
                png_files = list(png_dir.glob('*.png'))
                if png_files:
                    print(f"\n🖼️  High-resolution PNG exports ({len(png_files)} files):")
                    for png_file in sorted(png_files)[:5]:  # Show first 5
                        file_size = png_file.stat().st_size / (1024 * 1024)  # MB
                        print(f"   • {png_file.name} ({file_size:.1f} MB)")
                    if len(png_files) > 5:
                        print(f"   ... and {len(png_files) - 5} more")
            
            logger.info(f"7-Day Bitcoin Beta Report completed: {report_path}")
        else:
            print("\n❌ Failed to generate 7-day Bitcoin beta report")
            logger.error("7-Day Bitcoin Beta Report generation failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Report generation interrupted by user")
        logger.warning("Report generation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error generating 7-day report: {str(e)}")
        logger.error(f"Error in 7-day report generation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        # Cleanup
        try:
            if 'exchange_manager' in locals():
                await exchange_manager.cleanup()
                logger.info("Exchange manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    return 0

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the report generator
    exit_code = asyncio.run(main())
    sys.exit(exit_code)