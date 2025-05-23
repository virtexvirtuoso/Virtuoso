import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary classes
from src.monitoring.monitor import MarketMonitor
from src.monitoring.market_reporter import MarketReporter
from src.core.reporting.report_manager import ReportManager
from src.core.reporting.pdf_generator import ReportGenerator
from src.monitoring.alert_manager import AlertManager
from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockMetricsManager:
    """Mock metrics manager for testing"""
    def __init__(self):
        self.metrics = {}
    
    def store_metric(self, key, value):
        self.metrics[key] = value
        logger.info(f"Stored metric: {key}")
    
    def record_metric(self, key, value, metadata=None):
        self.metrics[key] = {"value": value, "metadata": metadata}
        logger.info(f"Recorded metric: {key}")
    
    async def update_metric(self, key, value, metadata=None):
        self.metrics[key] = {"value": value, "metadata": metadata}
        logger.info(f"Updated metric: {key}")

async def test_market_report():
    logger.info("Starting market report test with live Bybit data")
    
    try:
        # Get the correct template directory path
        template_dir = os.path.join(os.getcwd(), "templates")
        logger.info(f"Using template directory: {template_dir}")
        
        # Set up Bybit API credentials
        bybit_api_key = 'TjaG5KducWssxy9Z1m'
        bybit_api_secret = 'test_api_secret_placeholder'
        
        # Set environment variables for the exchange to use
        os.environ['BYBIT_API_KEY'] = bybit_api_key
        os.environ['BYBIT_API_SECRET'] = bybit_api_secret
        
        # Create a basic configuration for testing
        config = {
            "monitoring": {
                "alerts": {
                    "discord_webhook_url": os.environ.get("DISCORD_WEBHOOK_URL", ""),
                    "enabled": True
                }
            },
            "template_dir": template_dir,  # Add template directory to config
            "base_dir": os.path.join(os.getcwd(), "reports"),  # Set base directory for reports
            "exchanges": {
                "bybit": {
                    "name": "bybit",
                    "enabled": True,
                    "testnet": False,
                    "rest_endpoint": "https://api.bybit.com",
                    "websocket": {
                        "enabled": True,
                        "mainnet_endpoint": "wss://stream.bybit.com/v5/public",
                        "testnet_endpoint": "wss://stream-testnet.bybit.com/v5/public",
                        "channels": [
                            "orderbook.50",
                            "tickers",
                            "kline.1",
                            "publicTrade",
                            "liquidation"
                        ]
                    },
                    "api_credentials": {
                        "api_key": bybit_api_key,
                        "api_secret": bybit_api_secret
                    }
                }
            }
        }
        
        # Create an AlertManager
        logger.info("Creating AlertManager instance")
        alert_manager = AlertManager(config)
        
        # Create a mock MetricsManager
        logger.info("Creating MetricsManager mock")
        metrics_manager = MockMetricsManager()
        
        # Initialize a ReportGenerator (PDF Generator) with proper template_dir
        logger.info("Creating PDF Generator")
        pdf_generator = ReportGenerator(template_dir=template_dir)
        
        # Manually set the template_dir attribute to ensure it's available
        pdf_generator.template_dir = template_dir
        
        # Create a ReportManager with the same config
        logger.info("Creating ReportManager")
        report_manager = ReportManager(config=config)
        
        # Manually set the pdf_generator on the report_manager to ensure consistency
        report_manager.pdf_generator = pdf_generator
        
        # Create a Bybit exchange instance
        logger.info("Creating Bybit exchange instance")
        exchange = BybitExchange(config)
        
        # Initialize the exchange
        logger.info("Initializing Bybit exchange")
        await exchange.initialize()
        
        # Create a MarketMonitor instance first
        logger.info("Creating MarketMonitor instance")
        market_monitor = MarketMonitor(
            alert_manager=alert_manager,
            metrics_manager=metrics_manager,
            config=config,
            exchange=exchange  # Pass the exchange instance
        )
        
        # Now directly set the pdf_generator and report_manager on the MarketMonitor's market_reporter
        logger.info("Adding PDF Generator and ReportManager to MarketMonitor's MarketReporter")
        market_monitor.market_reporter.pdf_generator = pdf_generator
        market_monitor.market_reporter.report_manager = report_manager
        
        # Verify that the market_reporter in the market_monitor has the pdf_generator
        if hasattr(market_monitor.market_reporter, 'pdf_generator'):
            logger.info("PDF Generator properly attached to MarketMonitor's MarketReporter")
            if hasattr(market_monitor.market_reporter.pdf_generator, 'template_dir'):
                logger.info(f"PDF Generator has template_dir: {market_monitor.market_reporter.pdf_generator.template_dir}")
                # Verify the template directory exists
                if os.path.exists(market_monitor.market_reporter.pdf_generator.template_dir):
                    logger.info(f"Template directory exists: {os.listdir(market_monitor.market_reporter.pdf_generator.template_dir)}")
                else:
                    logger.warning(f"Template directory does not exist: {market_monitor.market_reporter.pdf_generator.template_dir}")
            else:
                logger.warning("PDF Generator is missing template_dir attribute")
        else:
            logger.warning("PDF Generator NOT found in MarketMonitor's MarketReporter")
            
        if hasattr(market_monitor.market_reporter, 'report_manager'):
            logger.info("ReportManager properly attached to MarketMonitor's MarketReporter")
            # Verify that ReportManager's pdf_generator has the template_dir
            if hasattr(market_monitor.market_reporter.report_manager.pdf_generator, 'template_dir'):
                logger.info(f"ReportManager's PDF Generator has template_dir: {market_monitor.market_reporter.report_manager.pdf_generator.template_dir}")
                # Set it manually if needed
                market_monitor.market_reporter.report_manager.pdf_generator.template_dir = template_dir
            else:
                logger.warning("ReportManager's PDF Generator is missing template_dir attribute")
                market_monitor.market_reporter.report_manager.pdf_generator.template_dir = template_dir
        else:
            logger.warning("ReportManager NOT found in MarketMonitor's MarketReporter")
        
        # Set exchange on market_reporter for data access
        market_monitor.market_reporter.exchange = exchange
        
        # Generate the market report
        logger.info("Generating market report with PDF attachment using live Bybit data")
        await market_monitor._generate_market_report()
        
        # Check if any PDFs were generated
        pdf_dir = os.path.join("reports", "pdf")
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.startswith("market_report_") and f.endswith(".pdf")]
            if pdf_files:
                logger.info(f"PDFs generated: {pdf_files}")
                # Get the most recent PDF file
                most_recent_pdf = max(pdf_files, key=lambda x: os.path.getmtime(os.path.join(pdf_dir, x)))
                logger.info(f"Most recent PDF: {most_recent_pdf}")
                # Check if it was just created
                pdf_path = os.path.join(pdf_dir, most_recent_pdf)
                file_time = datetime.fromtimestamp(os.path.getmtime(pdf_path))
                now = datetime.now()
                time_diff = (now - file_time).total_seconds()
                logger.info(f"PDF was created {time_diff} seconds ago")
            else:
                logger.warning("No PDF files were generated")
        else:
            logger.warning(f"PDF directory {pdf_dir} does not exist")
        
        logger.info("Market report test completed successfully")
    except Exception as e:
        logger.error(f"Error running market report test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_market_report()) 