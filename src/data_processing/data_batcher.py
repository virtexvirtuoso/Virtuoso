from typing import Dict, Any, List, Optional, TYPE_CHECKING, Callable, Awaitable
import asyncio
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
import traceback

# Type checking imports
if TYPE_CHECKING:
    from monitoring.metrics_manager import MetricsManager
    from monitoring.alert_manager import AlertManager

logger = logging.getLogger(__name__)

class DataBatcher:
    """Batches market data updates for efficient processing."""
    
    def __init__(self, 
                 metrics_manager: 'MetricsManager',
                 alert_manager: 'AlertManager',
                 config: Optional[Dict[str, Any]] = None):
        """Initialize DataBatcher.
        
        Args:
            metrics_manager: Metrics manager for tracking performance (required)
            alert_manager: Alert manager for monitoring (required)
            config: Configuration dictionary containing settings
        """
        # Initialize managers (now required dependencies)
        self.metrics_manager = metrics_manager
        self.alert_manager = alert_manager
        self.config = config or {}
        
        # Initialize batching settings
        self.batch_size = int(self.config.get('batch_size', 100))
        self.flush_interval = float(self.config.get('flush_interval', 1.0))
        
        # Initialize data structures
        self.batches = defaultdict(list)
        self.handlers = {}  # Data type to handler function mapping
        self.last_process_time = defaultdict(float)
        self.processing_stats = defaultdict(lambda: {'count': 0, 'time': 0.0})
        
        logger.debug(f"DataBatcher initialized with batch size: {self.batch_size}")
        
    async def register_handler(self, data_type: str, handler: Callable[[List[Dict[str, Any]]], Awaitable[None]]) -> None:
        """Register an async handler function for a specific data type.
        
        Args:
            data_type: Type of data (e.g., 'ticker', 'trade', 'orderbook')
            handler: Async function to handle the batched data
        """
        self.handlers[data_type] = handler
        logger.debug(f"Registered handler for {data_type} data")
        
    async def add_data(self, data_type: str, data: Dict[str, Any]) -> None:
        """Add data to the appropriate batch.
        
        Args:
            data_type: Type of data being added
            data: The data to batch
        """
        try:
            # Track metrics
            self.metrics_manager.increment_counter('data_batched_total', 1, {'type': data_type})
            
            # Add to batch
            self.batches[data_type].append(data)
            
            # Process batch if it reaches the size limit
            if len(self.batches[data_type]) >= self.batch_size:
                # Create task for async processing
                asyncio.create_task(self._process_batch(data_type))
                
        except Exception as e:
            logger.error(f"Error adding data to batch: {str(e)}")
            logger.debug(traceback.format_exc())
            self.alert_manager.send_alert(
                'error',
                f"Failed to add data to batch: {str(e)}",
                {'data_type': data_type}
            )
            
    async def process_pending(self) -> None:
        """Process any pending batches that haven't reached size limit."""
        try:
            current_time = time.time()
            for data_type in list(self.batches.keys()):
                # Process if there's data and either:
                # 1. Batch size reached, or
                # 2. Flush interval elapsed since last process
                if (self.batches[data_type] and 
                    (len(self.batches[data_type]) >= self.batch_size or
                     current_time - self.last_process_time[data_type] >= self.flush_interval)):
                    await self._process_batch(data_type)
                    
        except Exception as e:
            logger.error(f"Error processing pending batches: {str(e)}")
            logger.debug(traceback.format_exc())
            self.alert_manager.send_alert(
                'error',
                f"Failed to process pending batches: {str(e)}"
            )
            
    async def _process_batch(self, data_type: str) -> None:
        """Process a batch of data using its registered handler.
        
        Args:
            data_type: Type of data to process
        """
        try:
            if data_type not in self.handlers:
                logger.warning(f"No handler registered for {data_type} data")
                return
                
            batch = self.batches[data_type]
            if not batch:
                return
                
            start_time = time.time()
            
            # Call the registered handler
            handler = self.handlers[data_type]
            await handler(batch)
            
            # Update processing stats
            processing_time = time.time() - start_time
            self.processing_stats[data_type]['count'] += len(batch)
            self.processing_stats[data_type]['time'] += processing_time
            
            # Track metrics
            self.metrics_manager.observe_value(
                'batch_processing_duration_seconds',
                processing_time,
                {'type': data_type}
            )
            self.metrics_manager.increment_counter(
                'records_processed_total',
                len(batch),
                {'type': data_type}
            )
            
            # Clear the processed batch
            self.batches[data_type] = []
            self.last_process_time[data_type] = time.time()
            
            logger.debug(f"Processed batch of {len(batch)} {data_type} items in {processing_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error processing {data_type} batch: {str(e)}")
            logger.debug(traceback.format_exc())
            self.alert_manager.send_alert(
                'error',
                f"Failed to process {data_type} batch: {str(e)}"
            )
            
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Dict containing processing stats for each data type
        """
        stats = {}
        for data_type, data in self.processing_stats.items():
            stats[data_type] = {
                'total_processed': data['count'],
                'total_time': data['time'],
                'avg_time': data['time'] / data['count'] if data['count'] > 0 else 0,
                'current_batch_size': len(self.batches[data_type]),
                'last_process_time': self.last_process_time[data_type]
            }
        return stats
        
    def clear(self) -> None:
        """Clear all batched data."""
        self.batches.clear()
        logger.debug("Cleared all batched data")
        
    def get_batch_size(self, data_type: str) -> int:
        """Get current batch size for a data type.
        
        Args:
            data_type: Type of data to check
            
        Returns:
            Current number of items in the batch
        """
        return len(self.batches.get(data_type, []))
        
    def has_data(self, data_type: str) -> bool:
        """Check if there is data for a specific type.
        
        Args:
            data_type: Type of data to check
            
        Returns:
            True if there is data pending for the type
        """
        return bool(self.batches.get(data_type, [])) 