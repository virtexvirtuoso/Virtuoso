from collections import defaultdict
from typing import Optional, TYPE_CHECKING
import logging
import asyncpg

if TYPE_CHECKING:
    from monitoring.metrics_manager import MetricsManager
    from monitoring.alert_manager import AlertManager

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Client for database operations with improved reliability."""
    
    def __init__(self, metrics_manager: 'MetricsManager', alert_manager: 'AlertManager',
                 db_url: str, max_pool_size: int = 10,
                 connection_timeout: float = 30.0):
        self.metrics_manager = metrics_manager
        self.alert_manager = alert_manager
        self.db_url = db_url
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_stats = defaultdict(int)
        self._last_operation_time = defaultdict(float)
        
    async def connect(self) -> bool:
        """Initialize database connection pool.
        
        Returns:
            bool: True if connection successful
        """
        try:
            if self._pool:
                return True
                
            self._pool = await asyncpg.create_pool(
                self.db_url,
                max_size=self.max_pool_size,
                command_timeout=self.connection_timeout,
                min_size=1
            )
            
            self._connection_stats['pool_created'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            self._connection_stats['connection_errors'] += 1
            self.alert_manager.send_alert(
                level="ERROR",
                message="Database connection failed",
                details={'error': str(e)}
            )
            return False
            
    async def disconnect(self) -> None:
        """Close database connection pool."""
        try:
            if self._pool:
                await self._pool.close()
                self._pool = None
                logger.info("Database connection pool closed")
                
        except Exception as e:
            logger.error(f"Error disconnecting from database: {str(e)}")
            
    async def execute(self, query: str, *args) -> Optional[str]:
        """Execute database query.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Optional[str]: Status message if successful
        """
        try:
            if not self._pool:
                logger.error("Database not connected")
                return None
                
            start_time = time.time()
            async with self._pool.acquire() as conn:
                await conn.execute(query, *args)
                
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                processing_time=execution_time,
                component='database',
                operation='execute'
            )
            
            self._connection_stats['successful_executions'] += 1
            return "Query executed successfully"
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            self._connection_stats['execution_errors'] += 1
            return None
            
    async def fetch(self, query: str, *args) -> Optional[List[Record]]:
        """Fetch data from database.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Optional[List[Record]]: Query results if successful
        """
        try:
            if not self._pool:
                logger.error("Database not connected")
                return None
                
            start_time = time.time()
            async with self._pool.acquire() as conn:
                results = await conn.fetch(query, *args)
                
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                processing_time=execution_time,
                component='database',
                operation='fetch'
            )
            
            self._connection_stats['successful_fetches'] += 1
            return results
            
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            self._connection_stats['fetch_errors'] += 1
            return None
            
    async def fetch_row(self, query: str, *args) -> Optional[Record]:
        """Fetch single row from database.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Optional[Record]: Query result if successful
        """
        try:
            if not self._pool:
                logger.error("Database not connected")
                return None
                
            start_time = time.time()
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(query, *args)
                
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                processing_time=execution_time,
                component='database',
                operation='fetch_row'
            )
            
            self._connection_stats['successful_row_fetches'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Error fetching row: {str(e)}")
            self._connection_stats['row_fetch_errors'] += 1
            return None
            
    async def execute_many(self, query: str, args: List[Tuple]) -> Optional[str]:
        """Execute batch database operations.
        
        Args:
            query: SQL query
            args: List of parameter tuples
            
        Returns:
            Optional[str]: Status message if successful
        """
        try:
            if not self._pool:
                logger.error("Database not connected")
                return None
                
            start_time = time.time()
            async with self._pool.acquire() as conn:
                await conn.executemany(query, args)
                
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                processing_time=execution_time,
                component='database',
                operation='execute_many'
            )
            
            self._connection_stats['successful_batch_executions'] += 1
            return "Batch operation completed successfully"
            
        except Exception as e:
            logger.error(f"Error executing batch operation: {str(e)}")
            self._connection_stats['batch_execution_errors'] += 1
            return None
            
    async def check_connection(self) -> bool:
        """Check database connection health.
        
        Returns:
            bool: True if connection healthy
        """
        try:
            if not self._pool:
                return False
                
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
                
            self._connection_stats['successful_health_checks'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Connection health check failed: {str(e)}")
            self._connection_stats['failed_health_checks'] += 1
            return False
            
    def get_connection_stats(self) -> Dict[str, int]:
        """Get database connection statistics."""
        stats = dict(self._connection_stats)
        if self._pool:
            stats['pool_size'] = self._pool.get_size()
            stats['pool_free'] = self._pool.get_free_size()
        return stats 