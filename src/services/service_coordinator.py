"""
Phase 2 Service Coordinator
Manages independent services and provides health monitoring
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from src.services.market_service import MarketDataService
try:
    from src.services.analysis_service_enhanced import EnhancedAnalysisService as AnalysisService
    print("Using Enhanced Analysis Service with signal generation")
except ImportError:
    from src.services.analysis_service import AnalysisService
    print("Using basic Analysis Service")

logger = logging.getLogger(__name__)


class ServiceCoordinator:
    """
    Coordinates Phase 2 independent services
    Services run in parallel and communicate through cache
    """
    
    def __init__(self, cache_host: str = 'localhost', cache_port: int = 11211):
        """
        Initialize the service coordinator
        
        Args:
            cache_host: Memcached host
            cache_port: Memcached port
        """
        self.cache_host = cache_host
        self.cache_port = cache_port
        
        # Initialize services
        self.market_service = MarketDataService(cache_host, cache_port)
        self.analysis_service = AnalysisService(cache_host, cache_port)
        
        # Task references
        self.market_task: Optional[asyncio.Task] = None
        self.analysis_task: Optional[asyncio.Task] = None
        
        self.running = False
        
    async def start(self):
        """Start all services"""
        logger.info("🚀 Starting Phase 2 Service Coordinator...")
        
        self.running = True
        
        # Start services as independent tasks
        self.market_task = asyncio.create_task(
            self.market_service.start(),
            name="market_service"
        )
        
        # Wait a bit for market data to populate before starting analysis
        await asyncio.sleep(2)
        
        self.analysis_task = asyncio.create_task(
            self.analysis_service.start(),
            name="analysis_service"
        )
        
        logger.info("✅ All services started")
        
        # Monitor services
        await self._monitor_services()
        
    async def _monitor_services(self):
        """Monitor service health and restart if needed"""
        while self.running:
            try:
                # Check if services are still running
                if self.market_task and self.market_task.done():
                    exception = self.market_task.exception()
                    if exception:
                        logger.error(f"Market service crashed: {exception}")
                        logger.info("Restarting market service...")
                        self.market_task = asyncio.create_task(
                            self.market_service.start(),
                            name="market_service"
                        )
                
                if self.analysis_task and self.analysis_task.done():
                    exception = self.analysis_task.exception()
                    if exception:
                        logger.error(f"Analysis service crashed: {exception}")
                        logger.info("Restarting analysis service...")
                        self.analysis_task = asyncio.create_task(
                            self.analysis_service.start(),
                            name="analysis_service"
                        )
                
                # Log status
                market_status = self.market_service.get_status()
                logger.debug(f"Market Service: {market_status}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def stop(self):
        """Stop all services gracefully"""
        logger.info("Stopping all services...")
        self.running = False
        
        # Stop services
        await self.market_service.stop()
        await self.analysis_service.stop()
        
        # Cancel tasks
        if self.market_task and not self.market_task.done():
            self.market_task.cancel()
            try:
                await self.market_task
            except asyncio.CancelledError:
                pass
        
        if self.analysis_task and not self.analysis_task.done():
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ All services stopped")


async def run_coordinator():
    """Main entry point for the service coordinator"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    coordinator = ServiceCoordinator()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(coordinator.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await coordinator.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await coordinator.stop()
    except Exception as e:
        logger.error(f"Coordinator error: {e}")
        await coordinator.stop()
        raise


if __name__ == "__main__":
    asyncio.run(run_coordinator())