#!/usr/bin/env python3
"""
Test script for enhanced PDF generation error handling and Discord webhook delivery.
"""

import os
import sys
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.reporting.pdf_generator import ReportGenerator, PDFGenerationError, DataValidationError
from monitoring.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pdf_generation_error_handling():
    """Test PDF generation with various error scenarios."""
    logger.info("Testing PDF generation error handling...")
    
    # Initialize report generator
    config = {
        'pdf_generation': {
            'max_retries': 2,
            'retry_delay': 0.5,
            'exponential_backoff': True
        }
    }
    
    report_generator = ReportGenerator(config=config, log_level=logging.DEBUG)
    
    # Test 1: Invalid signal data
    logger.info("Test 1: Invalid signal data")
    try:
        result = await report_generator.generate_report(signal_data=None)
        logger.error("Expected DataValidationError but got success")
    except Exception as e:
        logger.info(f"✓ Correctly caught error: {type(e).__name__}: {str(e)}")
    
    # Test 2: Missing required fields
    logger.info("Test 2: Missing required fields")
    try:
        result = await report_generator.generate_report(signal_data={})
        logger.error("Expected DataValidationError but got success")
    except Exception as e:
        logger.info(f"✓ Correctly caught error: {type(e).__name__}: {str(e)}")
    
    # Test 3: Valid signal data (should work)
    logger.info("Test 3: Valid signal data")
    valid_signal_data = {
        'symbol': 'BTCUSDT',
        'signal_type': 'BUY',
        'score': 75.5,
        'confluence_score': 75.5,
        'components': {
            'technical': 80.0,
            'sentiment': 70.0,
            'volume': 75.0
        },
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        result = await report_generator.generate_report(signal_data=valid_signal_data)
        if result:
            pdf_path, json_path = result
            logger.info(f"✓ PDF generation successful: {pdf_path}")
            
            # Verify file exists and is valid
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                logger.info(f"✓ PDF file exists and is {file_size} bytes")
            else:
                logger.error("✗ PDF file was not created")
        else:
            logger.error("✗ PDF generation returned False")
    except Exception as e:
        logger.error(f"✗ Unexpected error: {type(e).__name__}: {str(e)}")
    
    # Test 4: Invalid OHLCV data
    logger.info("Test 4: Invalid OHLCV data")
    try:
        import pandas as pd
        invalid_ohlcv = pd.DataFrame()  # Empty DataFrame
        result = await report_generator.generate_report(
            signal_data=valid_signal_data,
            ohlcv_data=invalid_ohlcv
        )
        logger.error("Expected DataValidationError but got success")
    except Exception as e:
        logger.info(f"✓ Correctly caught error: {type(e).__name__}: {str(e)}")


async def test_discord_webhook_error_handling():
    """Test Discord webhook delivery with various error scenarios."""
    logger.info("Testing Discord webhook error handling...")
    
    # Initialize alert manager with test configuration
    config = {
        'monitoring': {
            'alerts': {
                'webhook_max_retries': 2,
                'webhook_retry_delay': 0.5,
                'webhook_exponential_backoff': True,
                'webhook_timeout': 10.0,
                'max_file_size': 1024 * 1024,  # 1MB for testing
                'allowed_file_types': ['.pdf', '.txt', '.png']
            }
        }
    }
    
    alert_manager = AlertManager(config=config)
    
    # Test 1: No webhook URL
    logger.info("Test 1: No webhook URL configured")
    alert_manager.discord_webhook_url = ""
    
    message = {
        'content': 'Test message',
        'username': 'Test Bot'
    }
    
    success, response = await alert_manager.send_discord_webhook_message(message)
    if not success and 'no_webhook_url' in str(response.get('error', '')):
        logger.info("✓ Correctly handled missing webhook URL")
    else:
        logger.error(f"✗ Unexpected result: success={success}, response={response}")
    
    # Test 2: Invalid webhook URL
    logger.info("Test 2: Invalid webhook URL")
    alert_manager.discord_webhook_url = "https://invalid-webhook-url.com/webhook"
    
    success, response = await alert_manager.send_discord_webhook_message(message)
    if not success:
        logger.info(f"✓ Correctly handled invalid webhook URL: {response.get('error', 'Unknown error')}")
    else:
        logger.error(f"✗ Unexpected success with invalid URL")
    
    # Test 3: File validation
    logger.info("Test 3: File attachment validation")
    
    # Create test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Valid PDF file (mock)
        valid_pdf = os.path.join(temp_dir, "test.pdf")
        with open(valid_pdf, 'wb') as f:
            f.write(b'%PDF-1.4\n%Test PDF content')
        
        # Invalid file (too large)
        large_file = os.path.join(temp_dir, "large.txt")
        with open(large_file, 'wb') as f:
            f.write(b'x' * (2 * 1024 * 1024))  # 2MB file
        
        # Non-existent file
        missing_file = os.path.join(temp_dir, "missing.pdf")
        
        # Test file validation
        files = [valid_pdf, large_file, missing_file]
        validated_files = alert_manager._validate_attachment_files(files, "test123")
        
        if len(validated_files) == 1 and validated_files[0]['filename'] == 'test.pdf':
            logger.info("✓ File validation working correctly")
        else:
            logger.error(f"✗ File validation failed: {validated_files}")
    
    # Test 4: Delivery statistics
    logger.info("Test 4: Delivery statistics")
    stats = alert_manager.get_delivery_stats()
    logger.info(f"✓ Delivery stats: {stats}")


async def test_integration():
    """Test integration between PDF generation and Discord delivery."""
    logger.info("Testing PDF generation + Discord delivery integration...")
    
    # This would be a full integration test if we had a valid webhook URL
    # For now, we'll just test the error handling paths
    
    config = {
        'pdf_generation': {
            'max_retries': 1,
            'retry_delay': 0.1
        },
        'monitoring': {
            'alerts': {
                'webhook_max_retries': 1,
                'webhook_retry_delay': 0.1
            }
        }
    }
    
    report_generator = ReportGenerator(config=config)
    alert_manager = AlertManager(config=config)
    
    # Generate a PDF
    signal_data = {
        'symbol': 'ETHUSDT',
        'signal_type': 'SELL',
        'score': 45.0,
        'confluence_score': 45.0,
        'components': {
            'technical': 40.0,
            'sentiment': 50.0
        }
    }
    
    try:
        result = await report_generator.generate_report(signal_data=signal_data)
        if result:
            pdf_path, json_path = result
            logger.info(f"✓ PDF generated: {pdf_path}")
            
            # Test Discord delivery (will fail due to no webhook URL, but tests error handling)
            message = {
                'content': f'📊 Trading Signal Report for {signal_data["symbol"]}',
                'username': 'Virtuoso Trading Bot'
            }
            
            files = [pdf_path] if pdf_path else []
            success, response = await alert_manager.send_discord_webhook_message(
                message=message,
                files=files,
                alert_type='trading_signal'
            )
            
            if not success:
                logger.info(f"✓ Discord delivery handled gracefully: {response.get('error', 'Unknown error')}")
            else:
                logger.info("✓ Discord delivery successful (unexpected but good)")
                
        else:
            logger.error("✗ PDF generation failed")
            
    except Exception as e:
        logger.error(f"✗ Integration test failed: {type(e).__name__}: {str(e)}")


async def main():
    """Run all tests."""
    logger.info("Starting enhanced error handling tests...")
    
    try:
        await test_pdf_generation_error_handling()
        print("\n" + "="*50 + "\n")
        
        await test_discord_webhook_error_handling()
        print("\n" + "="*50 + "\n")
        
        await test_integration()
        
        logger.info("All tests completed!")
        
    except Exception as e:
        logger.error(f"Test suite failed: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main()) 