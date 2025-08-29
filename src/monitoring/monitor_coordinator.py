"""
Market Monitor with Service Coordinator - Breaking Circular Dependencies.

This module provides a market monitor that uses service coordination to eliminate
circular dependencies between SignalGenerator, AlertManager, and MarketMonitor.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.coordination import ServiceCoordinator, EventType
from ..signal_generation.signal_generator_adapter import SignalGeneratorAdapter
from .alert_manager_adapter import AlertManagerAdapter

# Import existing components
from .data_collector import DataCollector
from .validator import MarketDataValidator
from .websocket_manager import MonitoringWebSocketManager
from .metrics_tracker import MetricsTracker


class CoordinatedMarketMonitor:
    """
    Market monitor using service coordination to break circular dependencies.
    
    This monitor:
    1. Uses ServiceCoordinator for inter-service communication
    2. Eliminates direct dependencies between services
    3. Maintains the same external interface as the original monitor
    4. Uses event-driven architecture for better decoupling
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        exchange_manager,
        signal_generator,
        alert_manager,
        logger: Optional[logging.Logger] = None,
        **kwargs
    ):
        self.config = config
        self.exchange_manager = exchange_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize service coordinator
        self.coordinator = ServiceCoordinator(self.logger)
        
        # Create service adapters to break circular dependencies
        self.signal_adapter = SignalGeneratorAdapter(
            signal_generator, self.coordinator, self.logger
        )
        self.alert_adapter = AlertManagerAdapter(
            alert_manager, self.coordinator, self.logger
        )
        
        # Initialize monitoring components
        self.data_collector = DataCollector(config, exchange_manager, logger)
        self.validator = MarketDataValidator(logger)
        self.websocket_manager = MonitoringWebSocketManager(config, logger)
        self.metrics_tracker = MetricsTracker(config, logger)
        
        # Monitor state
        self._running = False
        self._monitoring_task = None
        
        # Statistics
        self.stats = {
            'symbols_processed': 0,
            'signals_generated': 0,
            'alerts_sent': 0,
            'errors': 0,
            'uptime': 0
        }
        
        self._start_time = None
    
    async def initialize(self) -> bool:
        \"\"\"Initialize the coordinated monitor.\"\"\"\n        try:\n            self.logger.info(\"Initializing CoordinatedMarketMonitor...\")\n            \n            # Start service coordinator\n            await self.coordinator.start()\n            \n            # Register services with coordinator\n            self._register_services()\n            \n            # Initialize components\n            await self._initialize_components()\n            \n            # Start monitoring components\n            await self._start_components()\n            \n            self._start_time = time.time()\n            self.logger.info(\"✅ CoordinatedMarketMonitor initialized successfully\")\n            \n            return True\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to initialize CoordinatedMarketMonitor: {e}\")\n            return False\n    \n    def _register_services(self) -> None:\n        \"\"\"Register services with the coordinator.\"\"\"\n        self.coordinator.register_service(\"signal_generator\", self.signal_adapter)\n        self.coordinator.register_service(\"alert_manager\", self.alert_adapter)\n        self.coordinator.register_service(\"data_collector\", self.data_collector)\n        self.coordinator.register_service(\"validator\", self.validator)\n        self.coordinator.register_service(\"websocket_manager\", self.websocket_manager)\n        self.coordinator.register_service(\"metrics_tracker\", self.metrics_tracker)\n        self.coordinator.register_service(\"monitor\", self)\n        \n        self.logger.info(\"All services registered with coordinator\")\n    \n    async def _initialize_components(self) -> None:\n        \"\"\"Initialize all monitoring components.\"\"\"\n        # Initialize data collector\n        if hasattr(self.data_collector, 'initialize'):\n            await self.data_collector.initialize()\n        \n        # Initialize websocket manager\n        if hasattr(self.websocket_manager, 'initialize'):\n            await self.websocket_manager.initialize()\n        \n        # Initialize metrics tracker\n        if hasattr(self.metrics_tracker, 'initialize'):\n            await self.metrics_tracker.initialize()\n    \n    async def _start_components(self) -> None:\n        \"\"\"Start all monitoring components.\"\"\"\n        # Start websocket manager\n        if hasattr(self.websocket_manager, 'start'):\n            await self.websocket_manager.start()\n        \n        # Start metrics tracker\n        if hasattr(self.metrics_tracker, 'start'):\n            await self.metrics_tracker.start()\n    \n    async def start_monitoring(self, symbols: List[str]) -> None:\n        \"\"\"Start monitoring the specified symbols.\"\"\"\n        if self._running:\n            self.logger.warning(\"Monitor already running\")\n            return\n        \n        self.logger.info(f\"Starting monitoring for {len(symbols)} symbols\")\n        \n        self._running = True\n        self._monitoring_task = asyncio.create_task(\n            self._monitoring_loop(symbols)\n        )\n        \n        self.logger.info(\"🚀 Monitoring started\")\n    \n    async def stop_monitoring(self) -> None:\n        \"\"\"Stop monitoring.\"\"\"\n        if not self._running:\n            return\n        \n        self.logger.info(\"Stopping monitoring...\")\n        \n        self._running = False\n        \n        if self._monitoring_task:\n            self._monitoring_task.cancel()\n            try:\n                await self._monitoring_task\n            except asyncio.CancelledError:\n                pass\n        \n        # Stop coordinator\n        await self.coordinator.stop()\n        \n        # Stop components\n        await self._stop_components()\n        \n        self.logger.info(\"✅ Monitoring stopped\")\n    \n    async def _stop_components(self) -> None:\n        \"\"\"Stop all monitoring components.\"\"\"\n        # Stop websocket manager\n        if hasattr(self.websocket_manager, 'stop'):\n            await self.websocket_manager.stop()\n        \n        # Stop metrics tracker\n        if hasattr(self.metrics_tracker, 'stop'):\n            await self.metrics_tracker.stop()\n    \n    async def _monitoring_loop(self, symbols: List[str]) -> None:\n        \"\"\"Main monitoring loop using event-driven coordination.\"\"\"\n        self.logger.info(f\"Starting monitoring loop for {len(symbols)} symbols\")\n        \n        while self._running:\n            try:\n                # Process each symbol\n                for symbol in symbols:\n                    if not self._running:\n                        break\n                    \n                    await self._process_symbol(symbol)\n                    self.stats['symbols_processed'] += 1\n                \n                # Update uptime\n                if self._start_time:\n                    self.stats['uptime'] = time.time() - self._start_time\n                \n                # Wait before next iteration\n                await asyncio.sleep(1.0)  # 1 second interval\n                \n            except Exception as e:\n                self.stats['errors'] += 1\n                self.logger.error(f\"Error in monitoring loop: {e}\")\n                await asyncio.sleep(5.0)  # Wait longer on error\n    \n    async def _process_symbol(self, symbol: str) -> None:\n        \"\"\"Process a single symbol using coordinated services.\"\"\"\n        try:\n            # Step 1: Collect market data\n            market_data = await self.data_collector.collect_market_data(symbol)\n            \n            if not market_data:\n                return\n            \n            # Step 2: Validate market data\n            if not await self.validator.validate_market_data(market_data):\n                self.logger.warning(f\"Invalid market data for {symbol}\")\n                return\n            \n            # Step 3: Coordinate signal flow through the service coordinator\n            await self.coordinator.coordinate_signal_flow(symbol, market_data)\n            \n            # Step 4: Update metrics\n            await self._update_metrics(symbol, market_data)\n            \n        except Exception as e:\n            self.logger.error(f\"Error processing symbol {symbol}: {e}\")\n            self.stats['errors'] += 1\n    \n    async def _update_metrics(self, symbol: str, market_data: Dict[str, Any]) -> None:\n        \"\"\"Update metrics for processed symbol.\"\"\"\n        if hasattr(self.metrics_tracker, 'update_symbol_metrics'):\n            await self.metrics_tracker.update_symbol_metrics(symbol, market_data)\n    \n    # External API methods (for backward compatibility)\n    \n    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:\n        \"\"\"Analyze a single symbol and return results.\"\"\"\n        try:\n            market_data = await self.data_collector.collect_market_data(symbol)\n            \n            if not market_data:\n                return {}\n            \n            # Coordinate analysis through service coordinator\n            await self.coordinator.coordinate_signal_flow(symbol, market_data)\n            \n            return {\n                'symbol': symbol,\n                'status': 'analyzed',\n                'timestamp': datetime.now().isoformat(),\n                'market_data': market_data\n            }\n            \n        except Exception as e:\n            self.logger.error(f\"Error analyzing symbol {symbol}: {e}\")\n            return {'error': str(e)}\n    \n    def get_stats(self) -> Dict[str, Any]:\n        \"\"\"Get monitoring statistics.\"\"\"\n        base_stats = dict(self.stats)\n        \n        # Add coordinator stats\n        coordinator_stats = self.coordinator.get_stats()\n        base_stats['coordinator'] = coordinator_stats\n        \n        # Add component stats\n        if hasattr(self.metrics_tracker, 'get_stats'):\n            base_stats['metrics'] = self.metrics_tracker.get_stats()\n        \n        return base_stats\n    \n    def is_running(self) -> bool:\n        \"\"\"Check if monitoring is running.\"\"\"\n        return self._running\n    \n    # Event handling (if this monitor also needs to handle events)\n    \n    def get_subscribed_events(self) -> List[str]:\n        \"\"\"Get events this monitor subscribes to.\"\"\"\n        return [\n            EventType.METRICS_UPDATED.value,\n            EventType.HEALTH_CHECK.value\n        ]\n    \n    async def handle_event(\n        self,\n        event_type: str,\n        event_data: Dict[str, Any],\n        source_service: str\n    ) -> None:\n        \"\"\"Handle events sent to this monitor.\"\"\"\n        if event_type == EventType.METRICS_UPDATED.value:\n            # Update internal metrics\n            pass\n        elif event_type == EventType.HEALTH_CHECK.value:\n            # Respond with health status\n            pass