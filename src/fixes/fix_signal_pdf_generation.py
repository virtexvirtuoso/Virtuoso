#!/usr/bin/env python3
"""
Fix script for ensuring PDF reports are generated with signals.
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime
import uuid
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_signal_pdf_generation.log')
    ]
)

logger = logging.getLogger("fix_signal_pdf")

# Add the project root to the path if not already there
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

async def fix_signal_pdf_generation():
    """Fix PDF generation in signal generator to ensure reports are attached to signals."""
    try:
        # Import necessary modules
        from src.monitoring.alert_manager import AlertManager
        from src.signal_generation.signal_generator import SignalGenerator
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting signal PDF generation fix...")
        
        # 1. Load the current configuration
        config_path = os.path.join(os.getcwd(), 'config', 'config.yaml')
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at {config_path}")
            config = {}  # Use empty config as fallback
        else:
            with open(config_path, 'r') as f:
                try:
                    config = yaml.safe_load(f)
                    logger.info("Configuration loaded successfully")
                except Exception as e:
                    logger.error(f"Error loading configuration: {str(e)}")
                    config = {}  # Use empty config as fallback
        
        # 2. Ensure reporting is enabled in config
        if 'reporting' not in config:
            config['reporting'] = {}
        
        if not config['reporting'].get('enabled', False):
            logger.info("Enabling reporting in configuration...")
            config['reporting']['enabled'] = True
            
            # Save the updated configuration
            try:
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                logger.info("Updated configuration saved")
            except Exception as e:
                logger.error(f"Error saving configuration: {str(e)}")
        
        # 3. Create the signal generator test function
        async def test_report_generation(symbol="BTC/USDT"):
            """Test report generation with a sample signal."""
            logger.info(f"Testing report generation for {symbol}...")
            
            # Create a test signal
            test_signal = {
                'symbol': symbol,
                'confluence_score': 75.0,
                'components': {
                    'technical': 80,
                    'volume': 75,
                    'orderbook': 70,
                    'orderflow': 65,
                    'sentiment': 60,
                    'price_structure': 55
                },
                'results': {
                    'technical': {'score': 80, 'components': {}},
                    'volume': {'score': 75, 'components': {}},
                    'orderbook': {'score': 70, 'components': {}},
                    'orderflow': {'score': 65, 'components': {}},
                    'sentiment': {'score': 60, 'components': {}},
                    'price_structure': {'score': 55, 'components': {}}
                },
                'reliability': 0.9,
                'buy_threshold': 70,
                'sell_threshold': 30,
                'price': 65000.0,
                'transaction_id': str(uuid.uuid4()),
                'signal_id': str(uuid.uuid4())[:8],
                'market_interpretations': [
                    {'component': 'technical', 'display_name': 'Technical', 'interpretation': 'Bullish trend with strong momentum'},
                    {'component': 'volume', 'display_name': 'Volume', 'interpretation': 'Increasing volume supporting the move'}
                ],
                'actionable_insights': [
                    'Consider entering on pullbacks to support',
                    'Set stops below recent swing low'
                ]
            }
            
            # Initialize ReportManager
            report_manager = ReportManager(config)
            
            # Generate timestamp for filenames
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create export directories
            export_dir = os.path.join('exports')
            os.makedirs(export_dir, exist_ok=True)
            
            # Define PDF path
            symbol_safe = symbol.replace('/', '')
            pdf_path = os.path.join(export_dir, f"{symbol_safe}_{timestamp_str}.pdf")
            
            # Generate the report
            logger.info(f"Generating PDF report to {pdf_path}...")
            success, pdf_path, json_path = await report_manager.generate_and_attach_report(
                signal_data=test_signal,
                signal_type='buy',
                output_path=pdf_path
            )
            
            if success and pdf_path and os.path.exists(pdf_path):
                logger.info(f"PDF generated successfully at {pdf_path}")
                test_signal['pdf_path'] = pdf_path
                
                # Initialize AlertManager
                alert_manager = AlertManager(config)
                await alert_manager.start()
                
                # Send signal with PDF
                logger.info("Sending signal with PDF attachment...")
                await alert_manager.send_signal_alert(test_signal)
                logger.info("Signal with PDF attachment sent")
                
                return pdf_path
            else:
                logger.error("Failed to generate PDF report")
                return None
        
        # 4. Execute the test
        pdf_path = await test_report_generation()
        
        if pdf_path and os.path.exists(pdf_path):
            logger.info(f"PDF generation test successful: {pdf_path}")
            
            # 5. Provide instructions for fixing the code
            logger.info("\n=== RECOMMENDATIONS FOR FIXING PDF GENERATION ===")
            logger.info("1. Ensure the 'reporting' section is enabled in your config.yaml:")
            logger.info("   reporting:")
            logger.info("     enabled: true")
            logger.info("     attach_pdf: true")
            logger.info("\n2. Verify that your code is properly adding the PDF path to the signal_data before sending alerts.")
            logger.info("   Check in src/monitoring/monitor.py that the PDF generation is happening before send_signal_alert.")
            logger.info("\n3. Ensure the SignalGenerator has report_manager initialized:")
            logger.info("   if reporting_config.get('enabled', False):")
            logger.info("       self.report_manager = ReportManager(config)")
            logger.info("\n4. In the AlertManager, verify that the PDF path is checked before attempting to send attachments:")
            logger.info("   pdf_path = signal_data.get('pdf_path')")
            logger.info("   if pdf_path and os.path.exists(pdf_path):")
            logger.info("       # Attach PDF to webhook")
            
            # Create a simple patch that could be applied
            patch_content = """
# Add this to src/monitoring/monitor.py in the _generate_signal method
# After generating the signal data but before sending the alert

if signal_data and not signal_data.get('pdf_path') and hasattr(self.signal_generator, 'report_manager') and self.signal_generator.report_manager:
    try:
        # Get cached OHLCV data for the report
        ohlcv_data = self.get_ohlcv_for_report(symbol)
        
        # Generate timestamp for filenames
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_safe = symbol.replace('/', '')
        pdf_path = os.path.join('exports', f"{symbol_safe}_{timestamp_str}.pdf")
        
        # Generate the report
        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Generating PDF report to {pdf_path}...")
        success, pdf_path, _ = await self.signal_generator.report_manager.generate_and_attach_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            signal_type='signal',
            output_path=pdf_path
        )
        
        if success and pdf_path and os.path.exists(pdf_path):
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] PDF generated successfully: {pdf_path}")
            signal_data['pdf_path'] = pdf_path
        else:
            self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Failed to generate PDF report")
    except Exception as e:
        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Error generating PDF: {str(e)}")
        self.logger.debug(traceback.format_exc())
"""
            
            # Save the patch file
            patch_path = "pdf_generation_patch.txt"
            with open(patch_path, "w") as f:
                f.write(patch_content)
            logger.info(f"\nPatch example saved to {patch_path}")
            
        else:
            logger.error("PDF generation test failed")
        
    except Exception as e:
        logger.error(f"Error in fix script: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(fix_signal_pdf_generation()) 