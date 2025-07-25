#!/usr/bin/env python3
"""
Script to run the Bitcoin Beta Report - Simple version without high-res PNG exports

This version generates the report faster by skipping the time-consuming high-resolution PNG exports.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path to import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.exchanges.manager import ExchangeManager
from src.core.market.top_symbols import TopSymbolsManager
from src.validation import AsyncValidationService
from src.reports.bitcoin_beta_report import BitcoinBetaReport
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the Bitcoin Beta Report."""
    exchange_manager = None
    try:
        logger.info("=== Starting Bitcoin Beta Report Generation (Simple Mode) ===")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("Failed to load configuration")
            return
            
        logger.info("Configuration loaded successfully")
        
        # Temporarily disable PNG exports in config
        if hasattr(config, 'bitcoin_beta_analysis'):
            config.bitcoin_beta_analysis['enable_png_export'] = False
            config.bitcoin_beta_analysis['png_resolution'] = 150  # Lower resolution if needed
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        
        logger.info("Exchange manager initialized")
        
        # Initialize validation service
        validation_service = AsyncValidationService()
        
        # Initialize top symbols manager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config,
            validation_service=validation_service
        )
        
        # Initialize the top symbols manager
        init_success = await top_symbols_manager.initialize()
        if not init_success:
            logger.error("Failed to initialize top symbols manager")
            return
            
        logger.info("Top symbols manager initialized")
        
        # Create Bitcoin Beta Report generator
        beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config
        )
        
        # Disable PNG exports at runtime
        beta_report.enable_png_export = False
        
        logger.info("Bitcoin Beta Report generator created (PNG exports disabled)")
        
        # Generate the report
        logger.info("Starting report generation...")
        pdf_path = await beta_report.generate_report()
        
        if pdf_path:
            logger.info(f"✅ Bitcoin Beta Report generated successfully!")
            logger.info(f"📄 Report saved to: {pdf_path}")
            
            # Get file size for info
            file_size = Path(pdf_path).stat().st_size
            logger.info(f"📊 Report size: {file_size / 1024:.1f} KB")
            
            # Check if HTML version was also created
            html_path = Path(pdf_path).with_suffix('.html')
            if html_path.exists():
                logger.info(f"🌐 HTML version also created: {html_path}")
            
            return pdf_path
        else:
            logger.error("❌ Failed to generate Bitcoin Beta Report")
            return None
            
    except Exception as e:
        logger.error(f"Error running Bitcoin Beta Report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        # Cleanup
        if exchange_manager:
            try:
                await exchange_manager.cleanup()
                logger.info("Exchange manager cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

def run_report():
    """Synchronous wrapper to run the report."""
    try:
        result = asyncio.run(main())
        return result
    except KeyboardInterrupt:
        logger.info("Report generation cancelled by user")
        return None
    except Exception as e:
        logger.error(f"Error in report runner: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚀 Bitcoin Beta Report Generator (Simple Mode)")
    print("=" * 50)
    print("📌 Note: High-resolution PNG exports are disabled for faster generation")
    print()
    
    result = run_report()
    
    if result:
        print(f"\n✅ Report generated successfully: {result}")
        print("\n📈 The report includes:")
        print("  • Multi-timeframe beta analysis (4H, 30M, 5M, 1M)")
        print("  • Normalized price performance charts")
        print("  • Beta comparison across timeframes")
        print("  • Correlation heatmap")
        print("  • Statistical measures for traders")
        print("  • Key trading insights")
        print("  • Alpha opportunity detection")
        print("\n💡 To generate high-resolution PNG exports, use the full version")
    else:
        print("\n❌ Report generation failed. Check logs for details.")
        sys.exit(1)