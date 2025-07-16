#!/usr/bin/env python3
"""
Bitcoin Beta 7-Day Report Runner

This script runs the Bitcoin Beta 7-Day Analysis Report generator.
Analyzes correlations between Bitcoin and other cryptocurrencies over the last 7 days.
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
from src.core.market.top_symbols import TopSymbolsManager
from src.core.validation.service import AsyncValidationService
from src.reports.bitcoin_beta_7day_report import BitcoinBeta7DayReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bitcoin_beta_7day_report.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run the Bitcoin Beta 7-Day Analysis Report."""
    try:
        print("🚀 Bitcoin Beta 7-Day Report Generator")
        print("=" * 50)
        logger.info("=== Starting Bitcoin Beta 7-Day Report Generation ===")
        
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
            return 1
            
        logger.info("Top symbols manager initialized")
        
        # Create and run the 7-day report
        report_generator = BitcoinBeta7DayReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config
        )
        
        logger.info("Starting 7-day Bitcoin beta analysis...")
        print("\n📊 Generating 7-day Bitcoin beta analysis report...")
        
        # Generate the report
        report_path = await report_generator.generate_report()
        
        if report_path:
            print(f"\n✅ 7-Day Bitcoin Beta Report generated successfully!")
            print(f"📄 Report saved to: {report_path}")
            
            # Check for PNG exports
            png_dir = Path(report_path).parent / 'png_exports'
            if png_dir.exists():
                png_files = list(png_dir.glob('*.png'))
                if png_files:
                    print(f"\n🖼️  High-resolution PNG exports ({len(png_files)} files):")
                    for png_file in sorted(png_files):
                        file_size = png_file.stat().st_size / (1024 * 1024)  # MB
                        print(f"   • {png_file.name} ({file_size:.1f} MB)")
            
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