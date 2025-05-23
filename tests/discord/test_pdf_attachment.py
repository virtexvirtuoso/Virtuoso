#!/usr/bin/env python3
"""
Test script to verify PDF attachment functionality in webhook signals.
"""

import os
import sys
import asyncio
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/tests/test_pdf_attachment.log')
    ]
)

logger = logging.getLogger("pdf_attachment_test")

# Add the project root to the path if not already there
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

async def test_pdf_generation_and_attachment():
    """Test PDF generation and attachment to webhook signal."""
    try:
        # Import necessary modules
        from src.monitoring.alert_manager import AlertManager
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Creating minimal test configuration...")
        
        # Create a minimal configuration for testing
        config = {
            'alerts': {
                'discord': {
                    'webhook_url': None  # Will be set later
                }
            },
            'reporting': {
                'enabled': True,
                'attach_pdf': True,
                'output_dir': 'reports'
            }
        }
        
        # Get the Discord webhook URL
        logger.info("Getting Discord webhook URL...")
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/example')
        
        # Set the webhook URL in the config
        config['alerts']['discord']['webhook_url'] = webhook_url
        logger.info(f"Using webhook URL: {webhook_url[:20]}...{webhook_url[-8:]}")
        
        # Create and initialize AlertManager
        logger.info("Creating AlertManager...")
        alert_manager = AlertManager(config)
        await alert_manager.start()
        
        # Create a test signal
        test_signal = {
            'symbol': 'BTC/USDT',
            'confluence_score': 85.0,
            'components': {
                'volume': 90,
                'technical': 85,
                'orderflow': 80,
                'orderbook': 78,
                'sentiment': 75
            },
            'results': {
                'volume': {'score': 90, 'components': {}, 'interpretation': 'Strong volume'},
                'technical': {'score': 85, 'components': {}, 'interpretation': 'Bullish trend'},
                'orderflow': {'score': 80, 'components': {}, 'interpretation': 'Positive momentum'},
                'orderbook': {'score': 78, 'components': {}, 'interpretation': 'Supportive book'},
                'sentiment': {'score': 75, 'components': {}, 'interpretation': 'Positive sentiment'}
            },
            'reliability': 0.9,
            'buy_threshold': 80,
            'sell_threshold': 20,
            'price': 65000.0,
            'transaction_id': 'test123',
            'signal_id': 'sig456'
        }
        
        # Create ReportManager
        logger.info("Creating ReportManager...")
        report_manager = ReportManager(config)
        
        # Generate OHLCV data for the report
        logger.info("Generating test OHLCV data...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
        ohlcv_data = pd.DataFrame({
            'open': np.random.normal(64000, 500, 100),
            'high': np.random.normal(65000, 500, 100),
            'low': np.random.normal(63000, 500, 100),
            'close': np.random.normal(65000, 500, 100),
            'volume': np.random.normal(1000, 100, 100)
        }, index=dates)
        
        # Generate PDF report
        logger.info("Generating PDF report...")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_dir = os.path.join("reports", "pdf")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"test_report_{timestamp_str}.pdf")
        
        success, pdf_path, _ = await report_manager.generate_and_attach_report(
            signal_data=test_signal,
            ohlcv_data=ohlcv_data,
            signal_type='buy'
        )
        
        if success and pdf_path:
            logger.info(f"PDF generated successfully at {pdf_path}")
            test_signal['pdf_path'] = pdf_path
        else:
            logger.error("Failed to generate PDF")
            return
        
        # Test 1: Send direct webhook message with attachment
        logger.info("Test 1: Sending direct webhook message with PDF attachment...")
        if pdf_path and os.path.exists(pdf_path):
            webhook_message = {
                'content': f"📊 Test PDF attachment for BTC/USDT BUY signal (score: 85.0)",
                'username': "Virtuoso Test"
            }
            
            files = [{
                'path': pdf_path,
                'filename': os.path.basename(pdf_path),
                'description': "Test report for BTC/USDT"
            }]
            
            await alert_manager.send_discord_webhook_message(webhook_message, files=files)
            logger.info("Test 1: Direct webhook message with PDF attachment sent")
        
        # Test 2: Send through send_signal_alert
        logger.info("Test 2: Testing send_signal_alert method with PDF attachment...")
        await alert_manager.send_signal_alert(test_signal)
        logger.info("Test 2: Signal alert with PDF attachment sent")
        
        logger.info("All tests completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)
    finally:
        # Cleanup
        if 'alert_manager' in locals():
            await alert_manager.stop()
        
        logger.info("Test script completed")

if __name__ == "__main__":
    asyncio.run(test_pdf_generation_and_attachment()) 