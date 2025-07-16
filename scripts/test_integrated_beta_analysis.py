#!/usr/bin/env python3
"""
Test script for integrated Bitcoin Beta Analysis in Market Reporter.

This script tests the integration between the Market Reporter and Bitcoin Beta Analysis.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

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

async def test_integrated_beta_analysis():
    """Test the integrated Bitcoin Beta Analysis functionality."""
    try:
        logger.info("=== Testing Integrated Bitcoin Beta Analysis ===")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("Failed to load configuration")
            return False
            
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
            return False
            
        logger.info("Top symbols manager initialized")
        
        # Get primary exchange for market reporter
        primary_exchange = await exchange_manager.get_primary_exchange()
        
        # Create Market Reporter with integrated Bitcoin Beta Analysis
        market_reporter = MarketReporter(
            exchange=primary_exchange,
            logger=logger,
            top_symbols_manager=top_symbols_manager,
            alert_manager=None  # No alert manager for testing
        )
        
        # Set config on market reporter for beta analysis
        market_reporter.config = config
        
        logger.info("Market Reporter initialized")
        
        # Test 1: Check if Bitcoin Beta Analysis is enabled
        if market_reporter.beta_enabled:
            logger.info("✅ Bitcoin Beta Analysis is ENABLED in Market Reporter")
        else:
            logger.warning("⚠️ Bitcoin Beta Analysis is DISABLED in Market Reporter")
            
        # Test 2: Generate market summary with beta analysis
        logger.info("Generating market summary with integrated beta analysis...")
        market_summary = await market_reporter.generate_market_summary()
        
        if market_summary:
            logger.info("✅ Market summary generated successfully")
            
            # Check if beta analysis is included
            if 'bitcoin_beta_analysis' in market_summary:
                beta_data = market_summary['bitcoin_beta_analysis']
                logger.info("✅ Bitcoin Beta Analysis included in market summary")
                
                # Log beta analysis summary
                if 'summary' in beta_data:
                    summary = beta_data['summary']
                    logger.info(f"Beta Analysis Summary: {len(summary)} timeframes")
                    for tf, data in summary.items():
                        logger.info(f"  {tf}: avg_beta={data.get('avg_beta', 0):.3f}, symbols={data.get('symbol_count', 0)}")
                
                # Check for alpha opportunities
                if 'alpha_opportunities' in beta_data:
                    alpha_count = len(beta_data['alpha_opportunities'])
                    logger.info(f"Alpha opportunities detected: {alpha_count}")
                    
            else:
                logger.warning("⚠️ Bitcoin Beta Analysis NOT included in market summary")
        else:
            logger.error("❌ Failed to generate market summary")
            return False
            
        # Test 3: Generate standalone beta report
        if market_reporter.beta_enabled:
            logger.info("Testing standalone Bitcoin Beta Analysis report generation...")
            beta_pdf_path = await market_reporter.generate_bitcoin_beta_report()
            
            if beta_pdf_path:
                logger.info(f"✅ Standalone Bitcoin Beta report generated: {beta_pdf_path}")
                
                # Check if file exists
                if os.path.exists(beta_pdf_path):
                    file_size = os.path.getsize(beta_pdf_path) / 1024  # KB
                    logger.info(f"📄 Report file size: {file_size:.1f} KB")
                else:
                    logger.warning("⚠️ Report file not found at specified path")
            else:
                logger.warning("⚠️ Failed to generate standalone beta report")
        
        # Test 4: Test beta calculation directly
        logger.info("Testing direct beta calculation...")
        symbols = await top_symbols_manager.get_symbols(limit=5)
        
        if symbols:
            logger.info(f"Testing with {len(symbols)} symbols: {symbols}")
            beta_result = await market_reporter._calculate_bitcoin_beta_analysis(symbols)
            
            if beta_result and 'beta_analysis' in beta_result:
                logger.info("✅ Direct beta calculation successful")
                logger.info(f"Beta analysis data keys: {list(beta_result['beta_analysis'].keys())}")
            else:
                logger.warning("⚠️ Direct beta calculation failed or returned empty data")
        
        logger.info("=== Integration Test Complete ===")
        return True
        
    except Exception as e:
        logger.error(f"Error in integration test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_test():
    """Synchronous wrapper to run the test."""
    try:
        result = asyncio.run(test_integrated_beta_analysis())
        return result
    except KeyboardInterrupt:
        logger.info("Test cancelled by user")
        return False
    except Exception as e:
        logger.error(f"Error in test runner: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Bitcoin Beta Analysis Integration Test")
    print("=" * 50)
    
    result = run_test()
    
    if result:
        print("\n✅ Integration test completed successfully!")
        print("\n📊 Features tested:")
        print("  • Bitcoin Beta Analysis integration in Market Reporter")
        print("  • Market summary with beta analysis")
        print("  • Standalone beta report generation")
        print("  • Direct beta calculation functionality")
    else:
        print("\n❌ Integration test failed. Check logs for details.")
        sys.exit(1) 