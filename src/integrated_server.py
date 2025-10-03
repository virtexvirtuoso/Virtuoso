from src.utils.task_tracker import create_tracked_task
"""Integrated server that runs both monitoring system and web dashboard."""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging
from src.utils.logging_config import configure_logging
configure_logging()

logger = logging.getLogger(__name__)

# Import core components
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.core.analysis.portfolio import PortfolioAnalyzer
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.data_storage.database import DatabaseClient
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.monitor import MarketMonitor
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.alert_manager import AlertManager
from src.monitoring.market_reporter import MarketReporter
from src.signal_generation.signal_generator import SignalGenerator
from src.core.validation.service import AsyncValidationService
from src.core.market.market_data_manager import MarketDataManager
from src.monitoring.health_monitor import HealthMonitor

# Import dashboard integration
from src.dashboard.dashboard_integration import DashboardIntegrationService, set_dashboard_integration

# Import web server
from src.web_server import app, main as web_main

import uvicorn


class IntegratedTradingSystem:
    """Integrated trading system that runs both monitoring and web dashboard."""
    
    def __init__(self):
        self.logger = logger
        self.config_manager = None
        self.monitor = None
        self.dashboard_integration = None
        self.web_server_task = None
        self.monitor_task = None
        self.running = False
        
    async def initialize(self):
        """Initialize all components."""
        try:
            self.logger.info("🚀 Initializing Integrated Trading System")
            
            # Use centralized initialization from main.py
            from src.main import initialize_components
            components = await initialize_components()
            
            # Extract components
            self.config_manager = components['config_manager']
            exchange_manager = components['exchange_manager']
            primary_exchange = components['primary_exchange']
            database_client = components['database_client']
            portfolio_analyzer = components['portfolio_analyzer']
            confluence_analyzer = components['confluence_analyzer']
            alert_manager = components['alert_manager']
            metrics_manager = components['metrics_manager']
            validation_service = components['validation_service']
            signal_generator = components['signal_generator']
            top_symbols_manager = components['top_symbols_manager']
            market_data_manager = components['market_data_manager']
            market_reporter = components['market_reporter']
            
            self.logger.info(f"Primary exchange initialized: {primary_exchange.exchange_id}")
            
            # Initialize market monitor
            self.logger.info("Initializing market monitor...")
            self.monitor = MarketMonitor(
                logger=self.logger,
                metrics_manager=metrics_manager,
                exchange=primary_exchange,
                top_symbols_manager=top_symbols_manager,
                alert_manager=alert_manager,
                config=self.config_manager.config,
                market_reporter=market_reporter
            )
            
            # Attach components to monitor
            self.monitor.exchange_manager = exchange_manager
            self.monitor.database_client = database_client
            self.monitor.portfolio_analyzer = portfolio_analyzer
            self.monitor.confluence_analyzer = confluence_analyzer
            self.monitor.alert_manager = alert_manager
            self.monitor.signal_generator = signal_generator
            self.monitor.top_symbols_manager = top_symbols_manager
            self.monitor.market_data_manager = market_data_manager
            self.monitor.market_reporter = market_reporter
            self.monitor.config = self.config_manager.config
            
            # Initialize dashboard integration service
            self.logger.info("Initializing dashboard integration...")
            self.dashboard_integration = DashboardIntegrationService(self.monitor)
            await self.dashboard_integration.initialize()
            
            # Set global dashboard integration instance
            set_dashboard_integration(self.dashboard_integration)
            
            self.logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def start(self):
        """Start the integrated system."""
        try:
            self.logger.info("🔄 Starting Integrated Trading System")
            self.running = True
            
            # Start dashboard integration service
            await self.dashboard_integration.start()
            
            # Start monitoring system
            self.monitor_task = create_tracked_task(self._run_monitor(), name="auto_tracked_task")
            
            # Start web server
            self.web_server_task = create_tracked_task(self._run_web_server(), name="auto_tracked_task")
            
            self.logger.info("✅ Integrated Trading System started successfully")
            self.logger.info("📊 Dashboard available at: http://localhost:8000/dashboard")
            self.logger.info("🔗 API available at: http://localhost:8000/api/dashboard/overview")
            
            # Wait for both tasks
            await asyncio.gather(self.monitor_task, self.web_server_task)
            
        except Exception as e:
            self.logger.error(f"Error starting system: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the integrated system."""
        self.logger.info("🛑 Stopping Integrated Trading System")
        self.running = False
        
        # Stop dashboard integration
        if self.dashboard_integration:
            await self.dashboard_integration.stop()
        
        # Stop monitor
        if self.monitor and self.monitor.running:
            await self.monitor.stop()
        
        # Cancel tasks
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.web_server_task and not self.web_server_task.done():
            self.web_server_task.cancel()
            try:
                await self.web_server_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("✅ Integrated Trading System stopped")
    
    async def _run_monitor(self):
        """Run the monitoring system."""
        try:
            await self.monitor.start()
            
            # Keep monitoring running
            while self.running:
                if not self.monitor.running:
                    self.logger.warning("Monitor stopped unexpectedly")
                    break
                await asyncio.sleep(10)
                
        except asyncio.CancelledError:
            self.logger.info("Monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in monitor: {e}")
    
    async def _run_web_server(self):
        """Run the web server."""
        try:
            # Get web server configuration from config manager
            web_config = self.config_manager.config.get('web_server', {})
            
            # Get host and port from config with fallbacks
            host = web_config.get('host', '0.0.0.0')
            port = web_config.get('port', 8000)
            log_level = web_config.get('log_level', 'info')
            access_log = web_config.get('access_log', True)
            auto_fallback = web_config.get('auto_fallback', True)
            fallback_ports = web_config.get('fallback_ports', [8001, 8002, 8080, 3000, 5000])
            
            self.logger.info(f"Starting web server on {host}:{port}")
            
            # Try primary port first, then fallback ports if enabled
            ports_to_try = [port] + (fallback_ports if auto_fallback else [])
            
            for attempt_port in ports_to_try:
                try:
                    if attempt_port != port:
                        self.logger.info(f"Primary port {port} unavailable, trying fallback port {attempt_port}")
                    
                    config = uvicorn.Config(
                        app=app,
                        host=host,
                        port=attempt_port,
                        log_level=log_level,
                        access_log=access_log
                    )
                    server = uvicorn.Server(config)
                    await server.serve()
                    return  # Success, exit function
                    
                except OSError as e:
                    if e.errno == 48:  # Address already in use
                        if attempt_port == ports_to_try[-1]:  # Last port to try
                            self.logger.error(f"All ports exhausted. Tried: {ports_to_try}")
                            self.logger.error("Solutions:")
                            self.logger.error("1. Kill existing processes: python scripts/port_manager.py --kill 8000")
                            self.logger.error("2. Find available port: python scripts/port_manager.py --find-available")
                            self.logger.error("3. Update config.yaml web_server.port to use different port")
                            raise
                        else:
                            self.logger.warning(f"Port {attempt_port} is in use, trying next port...")
                            continue
                    else:
                        self.logger.error(f"Failed to start web server on {host}:{attempt_port}: {e}")
                        raise
                        
        except asyncio.CancelledError:
            self.logger.info("Web server task cancelled")
        except Exception as e:
            self.logger.error(f"Error in web server: {e}")


async def main():
    """Main entry point."""
    system = IntegratedTradingSystem()
    
    # Setup signal handlers
    def signal_handler():
        logger.info("Received shutdown signal")
        create_tracked_task(system.stop(), name="auto_tracked_task")
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
    
    try:
        await system.initialize()
        await system.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        await system.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Failed to start system: {e}")
        sys.exit(1) 