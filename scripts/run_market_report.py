#!/usr/bin/env python3
"""
Script to run the Market Report manually.

This script demonstrates how to generate the Market Intelligence Report
using the current system's exchange manager and top symbols manager.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.exchanges.manager import ExchangeManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.validation.service import AsyncValidationService
from src.monitoring.market_reporter import MarketReporter
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the Market Report."""
    try:
        logger.info("=== Starting Market Intelligence Report Generation ===")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("Failed to load configuration")
            return
            
        logger.info("Configuration loaded successfully")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        
        logger.info("Exchange manager initialized")
        
        # Get the primary exchange for the market reporter
        primary_exchange = await exchange_manager.get_primary_exchange()
        if not primary_exchange:
            logger.error("No primary exchange available")
            return
            
        logger.info(f"Using primary exchange: {primary_exchange.exchange_id}")
        
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
        
        # Create Market Reporter
        market_reporter = MarketReporter(
            exchange=primary_exchange,
            logger=logger,
            top_symbols_manager=top_symbols_manager
        )
        
        logger.info("Market Reporter created")
        
        # Generate the market summary report
        logger.info("Starting market summary generation...")
        report_data = await market_reporter.generate_market_summary()
        
        if not report_data:
            logger.error("❌ Failed to generate market summary data")
            return None
            
        logger.info("✅ Market summary data generated successfully")
        
        # Generate PDF report
        logger.info("Starting PDF report generation...")
        pdf_path = await market_reporter.generate_market_pdf_report(report_data)
        
        if pdf_path:
            logger.info(f"✅ Market Intelligence Report generated successfully!")
            logger.info(f"📄 PDF Report saved to: {pdf_path}")
            
            # Get file size for info
            if os.path.exists(pdf_path):
                file_size = Path(pdf_path).stat().st_size
                logger.info(f"📊 Report size: {file_size / 1024:.1f} KB")
            
            # Also generate Discord-formatted report
            logger.info("Generating Discord-formatted report...")
            discord_report = await market_reporter.format_market_report(
                overview=report_data.get('market_overview', {}),
                top_pairs=report_data.get('top_pairs', []),
                market_regime=report_data.get('market_overview', {}).get('regime', 'UNKNOWN'),
                smart_money=report_data.get('smart_money_index', {}),
                whale_activity=report_data.get('whale_activity', {})
            )
            
            if discord_report and discord_report.get('embeds'):
                logger.info(f"✅ Discord report formatted with {len(discord_report['embeds'])} embeds")
                
                # Save Discord report to JSON for inspection
                import json
                discord_output_path = pdf_path.replace('.pdf', '_discord.json')
                with open(discord_output_path, 'w') as f:
                    json.dump(discord_report, f, indent=2, default=str)
                logger.info(f"📱 Discord report saved to: {discord_output_path}")
            
            return pdf_path
        else:
            logger.error("❌ Failed to generate PDF report")
            return None
            
    except Exception as e:
        logger.error(f"Error running Market Report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

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

def print_report_summary(report_data):
    """Print a summary of the generated report data."""
    if not report_data:
        return
        
    print("\n📊 Report Summary:")
    print("=" * 40)
    
    # Market Overview
    if 'market_overview' in report_data:
        overview = report_data['market_overview']
        print(f"🏛️  Market Regime: {overview.get('regime', 'Unknown')}")
        print(f"📈 Trend Strength: {overview.get('trend_strength', 0):.1f}%")
        print(f"💰 Total Volume: ${overview.get('total_volume', 0):,.0f}")
        print(f"🎯 BTC Dominance: {overview.get('btc_dominance', 0):.1f}%")
    
    # Smart Money Index
    if 'smart_money_index' in report_data:
        smi = report_data['smart_money_index']
        print(f"🧠 Smart Money Index: {smi.get('index', 50):.1f}/100")
        print(f"💡 Sentiment: {smi.get('sentiment', 'NEUTRAL')}")
    
    # Whale Activity
    if 'whale_activity' in report_data:
        whale = report_data['whale_activity']
        transactions = whale.get('transactions', [])
        print(f"🐋 Whale Transactions: {len(transactions)} detected")
        if transactions:
            total_value = sum(tx.get('usd_value', 0) for tx in transactions)
            print(f"💵 Total Whale Volume: ${total_value:,.0f}")
    
    # Futures Premium
    if 'futures_premium' in report_data:
        premium = report_data['futures_premium']
        premiums = premium.get('premiums', {})
        print(f"⚡ Futures Premium Data: {len(premiums)} symbols")
    
    print("=" * 40)

if __name__ == "__main__":
    print("🚀 Market Intelligence Report Generator")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = run_report()
    
    if result:
        print(f"\n✅ Report generated successfully: {result}")
        print("\n📈 The report includes:")
        print("  • Market overview and regime analysis")
        print("  • Smart money index and institutional flow")
        print("  • Whale activity tracking")
        print("  • Futures premium analysis")
        print("  • Performance metrics")
        print("  • Trading outlook and recommendations")
        print("  • Discord-formatted summary")
    else:
        print("\n❌ Report generation failed. Check logs for details.")
        sys.exit(1) 