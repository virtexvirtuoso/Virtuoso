#!/usr/bin/env python3
"""
Simple test script to verify PDF report generation and Discord webhook attachment.
"""

import os
import logging
import sys
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
sys.path.append(os.getcwd())

async def main():
    """Run a simple test of the PDF generation and Discord attachment."""
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.error("No webhook URL provided. Please provide as argument or set DISCORD_WEBHOOK_URL environment variable.")
        return
    
    logger.info(f"Using webhook URL: {webhook_url[:20]}...")
    
    try:
        from src.core.reporting.report_manager import ReportManager
        
        # Create a simple message to test Discord webhook
        webhook_message = {
            "content": "Test message for PDF attachment",
            "embeds": [{
                "title": "Test PDF Report",
                "description": "This is a test to verify PDF generation and attachment",
                "color": 0x00ff00  # Green
            }]
        }
        
        # Create a simple signal to test PDF generation
        signal_data = {
            "symbol": "BTCUSDT",
            "signal": "BULLISH",
            "score": 75.0,
            "reliability": 0.9,
            "price": 55000.0,
            "components": {
                "price_action": {
                    "score": 80,
                    "impact": 4.0,
                    "interpretation": "Strong bullish price action"
                },
                "momentum": {
                    "score": 70,
                    "impact": 3.0,
                    "interpretation": "Positive momentum indicators"
                }
            }
        }
        
        # Initialize ReportManager
        report_manager = ReportManager()
        
        # Start client session
        await report_manager.start()
        
        # Generate and attach report
        logger.info("Generating and attaching PDF report...")
        success, pdf_path, json_path = await report_manager.generate_and_attach_report(
            signal_data=signal_data,
            webhook_message=webhook_message,
            webhook_url=webhook_url
        )
        
        # Report results
        if success:
            logger.info(f"✅ Successfully generated and attached report!")
            logger.info(f"📄 PDF report: {pdf_path}")
            logger.info(f"📊 JSON data: {json_path}")
        else:
            logger.error(f"❌ Failed to generate and attach report")
            if pdf_path:
                logger.info(f"📄 PDF report (may be incomplete): {pdf_path}")
            if json_path:
                logger.info(f"📊 JSON data: {json_path}")
        
        # Stop client session
        await report_manager.stop()
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 