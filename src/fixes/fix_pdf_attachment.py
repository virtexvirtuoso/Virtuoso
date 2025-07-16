#!/usr/bin/env python3
"""
Diagnostic and fix script for PDF attachment issues in webhook alerts.
"""

import os
import sys
import asyncio
import logging
import json
import traceback
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_pdf_attachment.log')
    ]
)

logger = logging.getLogger("pdf_attachment_fix")

# Add the project root to the path if not already there
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

async def diagnose_and_fix_pdf_issue():
    """Diagnose the PDF attachment issue and apply fixes."""
    try:
        # Import necessary modules
        from src.monitoring.alert_manager import AlertManager
        from src.monitoring.monitor import MarketMonitor
        from src.signal_generation.signal_generator import SignalGenerator
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting PDF attachment diagnostic...")
        
        # 1. Check if the necessary directories exist
        logger.info("Checking report directories...")
        required_dirs = [
            'reports',
            'reports/pdf',
            'exports',
            'templates'
        ]
        
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                logger.warning(f"Directory {dir_path} does not exist, creating it...")
                os.makedirs(dir_path, exist_ok=True)
        
        # 2. Load the current configuration
        logger.info("Loading configuration...")
        config_path = os.path.join(os.getcwd(), 'config', 'config.yaml')
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at {config_path}")
            config = {}  # Use empty config as fallback
        else:
            with open(config_path, 'r') as f:
                try:
                    import yaml
                    config = yaml.safe_load(f)
                    logger.info("Configuration loaded successfully")
                except Exception as e:
                    logger.error(f"Error loading configuration: {str(e)}")
                    config = {}  # Use empty config as fallback
        
        # 3. Check reporting configuration
        reporting_config = config.get('reporting', {})
        if not reporting_config.get('enabled', False):
            logger.warning("Reporting is not enabled in configuration")
            logger.info("Enabling reporting in memory configuration...")
            config['reporting'] = config.get('reporting', {})
            config['reporting']['enabled'] = True
            config['reporting']['attach_pdf'] = True
        
        # 4. Check template directory
        template_dir = reporting_config.get('template_dir')
        template_dirs_to_check = [
            os.path.join(os.getcwd(), 'src/core/reporting/templates'),
            os.path.join(os.getcwd(), 'templates')
        ]
        
        template_dir_exists = False
        for dir_path in template_dirs_to_check:
            if os.path.exists(dir_path):
                logger.info(f"Template directory found at {dir_path}")
                template_dir_exists = True
                if not template_dir:
                    config['reporting']['template_dir'] = dir_path
                break
        
        if not template_dir_exists:
            logger.error("No template directory found. PDF generation may fail.")
        
        # 5. Check if ReportManager is initialized in SignalGenerator
        logger.info("Testing ReportManager initialization...")
        try:
            report_manager = ReportManager(config)
            logger.info("ReportManager initialized successfully")
            
            # Check if ReportGenerator was properly initialized inside ReportManager
            if hasattr(report_manager, 'pdf_generator'):
                logger.info("PDF generator is properly initialized in ReportManager")
            else:
                logger.error("PDF generator not initialized in ReportManager")
        except Exception as e:
            logger.error(f"Error initializing ReportManager: {str(e)}")
            logger.error(traceback.format_exc())
        
        # 6. Initialize SignalGenerator with proper configuration
        logger.info("Testing SignalGenerator initialization...")
        try:
            signal_generator = SignalGenerator(config)
            if hasattr(signal_generator, 'report_manager') and signal_generator.report_manager:
                logger.info("Report manager is properly initialized in SignalGenerator")
            else:
                logger.error("Report manager not initialized in SignalGenerator")
                logger.info("Manually setting report_manager in SignalGenerator...")
                signal_generator.report_manager = report_manager
        except Exception as e:
            logger.error(f"Error initializing SignalGenerator: {str(e)}")
            logger.error(traceback.format_exc())
        
        # 7. Test PDF generation directly
        logger.info("Testing PDF generation directly...")
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
            'transaction_id': str(uuid.uuid4()),
            'signal_id': str(uuid.uuid4())[:8]
        }
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_dir = os.path.join("exports")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"BTCUSDT_{timestamp_str}.pdf")
        
        try:
            logger.info(f"Generating test PDF to {pdf_path}...")
            if hasattr(report_manager, 'generate_and_attach_report'):
                success, pdf_path, _ = await report_manager.generate_and_attach_report(
                    signal_data=test_signal,
                    signal_type='test',
                    output_path=pdf_path
                )
                
                if success and pdf_path and os.path.exists(pdf_path):
                    logger.info(f"PDF generated successfully at {pdf_path}")
                    test_signal['pdf_path'] = pdf_path
                else:
                    logger.error("Failed to generate PDF directly")
            else:
                logger.error("ReportManager does not have generate_and_attach_report method")
        except Exception as e:
            logger.error(f"Error generating test PDF: {str(e)}")
            logger.error(traceback.format_exc())
        
        # 8. Verify the PDF was properly generated
        if os.path.exists(pdf_path):
            logger.info(f"PDF file exists at {pdf_path}")
            file_size = os.path.getsize(pdf_path) / 1024  # KB
            logger.info(f"PDF file size: {file_size:.2f} KB")
            
            # Check if it's a valid PDF file
            try:
                with open(pdf_path, 'rb') as f:
                    header = f.read(5)
                    if header[:4] == b'%PDF':
                        logger.info("PDF file has valid PDF header")
                    else:
                        logger.warning("File does not have a valid PDF header")
            except Exception as e:
                logger.error(f"Error checking PDF header: {str(e)}")
        else:
            logger.error(f"PDF file not found at {pdf_path}")
        
        # 9. Test alert manager with PDF attachment
        try:
            if 'pdf_path' in test_signal and os.path.exists(test_signal['pdf_path']):
                logger.info("Testing AlertManager with PDF attachment...")
                
                # Get Discord webhook URL
                discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
                if not discord_webhook:
                    logger.warning("Discord webhook URL not found in environment variables")
                    # Check in config
                    discord_webhook = config.get('monitoring', {}).get('alerts', {}).get('discord_webhook')
                
                if discord_webhook:
                    logger.info("Discord webhook URL found")
                    config['monitoring'] = config.get('monitoring', {})
                    config['monitoring']['alerts'] = config.get('monitoring', {}).get('alerts', {})
                    config['monitoring']['alerts']['discord_webhook'] = discord_webhook
                    
                    # Initialize AlertManager
                    alert_manager = AlertManager(config)
                    await alert_manager.start()
                    
                    # Send test signal with PDF
                    logger.info("Sending test signal with PDF attachment...")
                    await alert_manager.send_signal_alert(test_signal)
                    logger.info("Test signal with PDF attachment sent")
                else:
                    logger.error("Discord webhook URL not found, skipping alert test")
            else:
                logger.error("No valid PDF path in test signal, skipping alert test")
        except Exception as e:
            logger.error(f"Error testing AlertManager: {str(e)}")
            logger.error(traceback.format_exc())
        
        # 10. Create a diagnostic summary
        logger.info("Creating diagnostic summary...")
        diagnostic_summary = {
            "timestamp": datetime.now().isoformat(),
            "config_status": {
                "reporting_enabled": config.get('reporting', {}).get('enabled', False),
                "attach_pdf_enabled": config.get('reporting', {}).get('attach_pdf', False),
                "template_dir_exists": template_dir_exists,
                "required_dirs_exist": all(os.path.exists(d) for d in required_dirs)
            },
            "test_results": {
                "report_manager_initialized": hasattr(locals().get('report_manager', {}), 'pdf_generator'),
                "signal_generator_has_report_manager": hasattr(locals().get('signal_generator', {}), 'report_manager') and locals().get('signal_generator', {}).report_manager is not None,
                "pdf_generated": os.path.exists(locals().get('pdf_path', '')),
                "pdf_valid": locals().get('header', b'')[:4] == b'%PDF' if 'header' in locals() else False,
                "alert_manager_initialized": 'alert_manager' in locals()
            },
            "recommendations": []
        }
        
        # Add recommendations based on test results
        if not config.get('reporting', {}).get('enabled', False):
            diagnostic_summary["recommendations"].append("Enable reporting in config.yaml: reporting.enabled=true")
        
        if not config.get('reporting', {}).get('attach_pdf', False):
            diagnostic_summary["recommendations"].append("Enable PDF attachment in config.yaml: reporting.attach_pdf=true")
        
        if not template_dir_exists:
            diagnostic_summary["recommendations"].append("Create template directory in src/core/reporting/templates")
        
        if not hasattr(locals().get('report_manager', {}), 'pdf_generator'):
            diagnostic_summary["recommendations"].append("Check ReportManager initialization in SignalGenerator")
        
        if not (hasattr(locals().get('signal_generator', {}), 'report_manager') and locals().get('signal_generator', {}).report_manager is not None):
            diagnostic_summary["recommendations"].append("Ensure report_manager is properly initialized in SignalGenerator")
        
        # Save the diagnostic summary
        diagnostic_path = f"pdf_attachment_diagnostic_{timestamp_str}.json"
        with open(diagnostic_path, 'w') as f:
            json.dump(diagnostic_summary, f, indent=2, default=str)
        
        logger.info(f"Diagnostic summary saved to {diagnostic_path}")
        
        # Print summary to console
        logger.info("\n=== PDF ATTACHMENT DIAGNOSTIC SUMMARY ===")
        logger.info(f"Reporting enabled: {diagnostic_summary['config_status']['reporting_enabled']}")
        logger.info(f"Attach PDF enabled: {diagnostic_summary['config_status']['attach_pdf_enabled']}")
        logger.info(f"Template directory exists: {diagnostic_summary['config_status']['template_dir_exists']}")
        logger.info(f"Required directories exist: {diagnostic_summary['config_status']['required_dirs_exist']}")
        logger.info(f"ReportManager initialized: {diagnostic_summary['test_results']['report_manager_initialized']}")
        logger.info(f"SignalGenerator has ReportManager: {diagnostic_summary['test_results']['signal_generator_has_report_manager']}")
        logger.info(f"PDF generated: {diagnostic_summary['test_results']['pdf_generated']}")
        logger.info(f"PDF valid: {diagnostic_summary['test_results']['pdf_valid']}")
        logger.info(f"AlertManager initialized: {diagnostic_summary['test_results']['alert_manager_initialized']}")
        
        if diagnostic_summary["recommendations"]:
            logger.info("\n=== RECOMMENDATIONS ===")
            for i, rec in enumerate(diagnostic_summary["recommendations"], 1):
                logger.info(f"{i}. {rec}")
        
        logger.info("Diagnostic completed")
        
    except Exception as e:
        logger.error(f"Error in diagnostic: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(diagnose_and_fix_pdf_issue()) 