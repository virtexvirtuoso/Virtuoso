# src/data_storage/database.py

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Sequence
from datetime import datetime, timedelta
from dataclasses import dataclass
import os
import traceback
from functools import wraps
from ..utils.cache import cached
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

def handle_db_errors(func: Callable):
    """Decorator for handling database operation errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    return wrapper

def measure_execution_time(func: Callable):
    """Decorator to measure and log function execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
            raise
    return wrapper

@dataclass
class DatabaseConfig:
    """Configuration for InfluxDB connection."""
    url: str
    token: str
    org: str
    bucket: str
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    batch_size: int = 1000  # Maximum points per batch
    batch_timeout: float = 10.0  # Maximum seconds to wait before writing batch

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'DatabaseConfig':
        """Create config from dictionary."""
        influx_config = (
            config.get('influxDB', {}) or
            config.get('exchanges', {}).get('bybit', {}).get('websocket', {}).get('storage', {}).get('influxdb', {}) or
            {}
        )
        
        return cls(
            url=influx_config.get('url') or os.getenv('INFLUXDB_URL') or 'http://localhost:8086',
            token=influx_config.get('token') or os.getenv('INFLUXDB_TOKEN'),
            org=influx_config.get('org') or os.getenv('INFLUXDB_ORG') or 'default',
            bucket=influx_config.get('bucket') or os.getenv('INFLUXDB_BUCKET') or 'market_data',
            max_retries=influx_config.get('max_retries', 3),
            retry_delay=influx_config.get('retry_delay', 1.0),
            batch_size=influx_config.get('batch_size', 1000),
            batch_timeout=influx_config.get('batch_timeout', 10.0)
        )

class DatabaseClient:
    """Client for interacting with InfluxDB."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize database client."""
        self.config: DatabaseConfig = DatabaseConfig.from_dict(config)
        self.client: Optional[InfluxDBClient] = None
        self.write_api: Any = None
        self.query_api: Any = None
        self._init_client()
        self._retry_count: int = 0

    def _init_client(self) -> None:
        """Initialize InfluxDB client and APIs."""
        try:
            if not self.config.token:
                raise ValueError("InfluxDB token is required")
                
            self.client = InfluxDBClient(
                url=self.config.url,
                token=self.config.token,
                org=self.config.org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            self.client.ping()
            logger.debug("Successfully connected to InfluxDB")
            self._retry_count = 0
            
        except Exception as e:
            self._retry_count += 1
            if self._retry_count < self.config.max_retries:
                logger.warning(f"Retrying connection ({self._retry_count}/{self.config.max_retries})")
                time.sleep(self.config.retry_delay)
                self._init_client()
            else:
                logger.error(f"Failed to initialize InfluxDB client after {self.config.max_retries} attempts: {str(e)}")
                raise

    async def _ensure_connection(self) -> bool:
        """Ensure database connection is active."""
        try:
            if not await self.is_healthy():
                logger.warning("Unhealthy connection detected, attempting to reconnect")
                self._init_client()
            return await self.is_healthy()
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False

    @handle_db_errors
    async def store_market_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Store market data in InfluxDB.
        
        Args:
            symbol: Trading symbol
            data: Market data including price, volume, and timestamp
        """
        if not await self._ensure_connection():
            return None
            
        point = Point("market_data")\
            .tag("symbol", symbol)\
            .field("price", float(data.get('price', 0)))\
            .field("volume", float(data.get('volume', 0)))\
            .field("timestamp", data.get('timestamp', datetime.utcnow().timestamp()))\
            .time(datetime.utcnow())
        
        self.write_api.write(bucket=self.config.bucket, record=point)
        logger.debug(f"Stored market data for {symbol}")

    @handle_db_errors
    async def store_signal(self, symbol: str, signal_data: Dict[str, Any]) -> None:
        """Store trading signal in InfluxDB.
        
        Args:
            symbol: Trading symbol
            signal_data: Signal data including type, value, and confidence
        """
        if not await self._ensure_connection():
            return None
            
        point = Point("signals")\
            .tag("symbol", symbol)\
            .field("signal_type", signal_data.get('type', 'unknown'))\
            .field("value", float(signal_data.get('value', 0)))\
            .field("confidence", float(signal_data.get('confidence', 0)))\
            .time(datetime.utcnow())
        
        self.write_api.write(bucket=self.config.bucket, record=point)
        logger.debug(f"Stored signal for {symbol}")

    @handle_db_errors
    @measure_execution_time
    async def store_analysis(self, symbol: str, analysis: Dict[str, Any], signals: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Store analysis results in the database"""
        try:
            if not await self._ensure_connection():
                return False
            
            # Create point with proper structure
            point = Point("analysis")\
                .tag("symbol", symbol)\
                .time(datetime.utcnow())
            
            # Add fields from analysis data
            for key, value in analysis.items():
                if isinstance(value, (int, float)):
                    point.field(key, float(value))
                elif isinstance(value, str):
                    point.field(key, value)
                elif isinstance(value, dict):
                    # Flatten nested dictionaries
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            point.field(f"{key}_{sub_key}", float(sub_value))
            
            # Add signals if provided
            if signals:
                for i, signal in enumerate(signals):
                    for key, value in signal.items():
                        if isinstance(value, (int, float, str)):
                            point.field(f"signal_{i}_{key}", value)
            
            await self.write_api.write(
                bucket=self.config.bucket,
                org=self.config.org,
                record=point
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store analysis: {str(e)}")
            return False

    @handle_db_errors
    async def get_analysis_history(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        components: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """Get analysis history for a symbol.
        
        Args:
            symbol: Trading symbol
            start_time: Start time for query range
            end_time: End time for query range
            components: Optional list of specific components to retrieve
            
        Returns:
            DataFrame containing analysis history or None if error
        """
        if not await self._ensure_connection():
            return None
            
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()
            
        # Build component filter
        component_filter = ""
        if components:
            component_list = [f'r["_field"] == "{c}_score"' for c in components]
            component_filter = f'|> filter(fn: (r) => {" or ".join(component_list)})'
            
        query = f'''
        from(bucket: "{self.config.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r["_measurement"] == "market_analysis")
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            {component_filter}
        '''
        
        try:
            result = self.query_api.query_data_frame(query)
            if result is not None and not result.empty:
                return result
            logger.warning(f"No analysis history found for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error querying analysis history: {str(e)}")
            return None

    @handle_db_errors
    async def write_dataframe(self, df: pd.DataFrame, measurement: str) -> None:
        """Write DataFrame to InfluxDB.
        
        Args:
            df: DataFrame to write
            measurement: Measurement name in InfluxDB
        """
        if not await self._ensure_connection():
            return None
            
        df = self._convert_df_types(df)
        
        # Convert DataFrame to InfluxDB line protocol
        for index, row in df.iterrows():
            point = Point(measurement)
            
            # Add all columns as fields
            for column in df.columns:
                value = row[column]
                if pd.notna(value):  # Skip NaN values
                    point.field(column, value)
            
            point.time(index if isinstance(index, datetime) else datetime.utcnow())
            self.write_api.write(bucket=self.config.bucket, record=point)
        
        logger.debug(f"Successfully wrote DataFrame to measurement: {measurement}")

    def _convert_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame types to be compatible with InfluxDB."""
        try:
            # Convert numeric columns
            numeric_columns = df.select_dtypes(include=['int', 'float']).columns
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Convert timestamp columns
            timestamp_columns = df.select_dtypes(include=['datetime64']).columns
            for col in timestamp_columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

            return df
        except Exception as e:
            logger.error(f"Error converting DataFrame types: {str(e)}")
            return df

    @cached(ttl=300)  # 5 minute cache
    @handle_db_errors
    async def get_imbalance_history(
        self, 
        symbol: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Get order book imbalance history with caching.
        
        Args:
            symbol: Trading symbol
            start_time: Start time for query range
            end_time: End time for query range
            
        Returns:
            DataFrame containing imbalance history or None if error
        """
        if not await self._ensure_connection():
            return None
            
        if not start_time:
            start_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_time:
            end_time = datetime.utcnow()

        query = f'''
        from(bucket: "{self.config.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r["_measurement"] == "orderbook_imbalance")
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
        '''
        
        return await self.query_data(query)

    @handle_db_errors
    async def query_data(self, query: str) -> Optional[pd.DataFrame]:
        """Query data from InfluxDB.
        
        Args:
            query: Flux query string
            
        Returns:
            DataFrame containing query results or None if error
        """
        if not await self._ensure_connection():
            return None
            
        result = self.query_api.query_data_frame(query=query, org=self.config.org)
        logger.debug(f"Queried data from InfluxDB: {query}")
        return result

    async def close(self) -> None:
        """Close all database connections."""
        try:
            if self.write_api:
                self.write_api.close()
            if self.client:
                self.client.close()
            logger.info("Closed all database connections")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            logger.debug(traceback.format_exc())

    async def is_healthy(self) -> bool:
        """Check if the database client is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Check if all required components are initialized
            if not all([self.client, self.write_api, self.query_api]):
                logger.warning("Database client components not fully initialized")
                return False

            # Check connection with ping
            logger.info("Checking database connection...")
            if not self.client.ping():
                logger.warning("Database ping failed")
                return False
            logger.info("Database ping successful")

            # Try a simple write operation
            try:
                logger.info("Testing write operation...")
                test_point = Point("health_check")\
                    .tag("type", "test")\
                    .field("value", 1)\
                    .time(datetime.utcnow())
                self.write_api.write(bucket=self.config.bucket, record=test_point)
                logger.info("Write operation successful")
            except Exception as e:
                logger.error(f"Write operation failed: {str(e)}")
                return False

            # Try a simple query operation
            try:
                logger.info("Testing query operation...")
                query = f'from(bucket:"{self.config.bucket}") |> range(start: -1m) |> limit(n:1)'
                self.query_api.query(query=query, org=self.config.org)
                logger.info("Query operation successful")
            except Exception as e:
                logger.error(f"Query operation failed: {str(e)}")
                return False

            # All checks passed
            logger.info("Database health check passed")
            return True

        except Exception as e:
            logger.error(f"Error checking database health: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    @handle_db_errors
    @measure_execution_time
    async def write_batch(self, points: Sequence[Point]) -> None:
        """Write multiple points in batches.
        
        Args:
            points: Sequence of Point objects to write
        """
        if not await self._ensure_connection():
            return None
            
        total_points = len(points)
        batch_size = self.config.batch_size
        
        for i in range(0, total_points, batch_size):
            batch = points[i:i + batch_size]
            self.write_api.write(bucket=self.config.bucket, record=batch)
            logger.debug(f"Wrote batch of {len(batch)} points ({i + len(batch)}/{total_points})")

    @handle_db_errors
    @measure_execution_time
    async def write_dataframe_batch(self, df: pd.DataFrame, measurement: str) -> None:
        """Write DataFrame to InfluxDB using batching.
        
        Args:
            df: DataFrame to write
            measurement: Measurement name in InfluxDB
        """
        if not await self._ensure_connection():
            return None
            
        df = self._convert_df_types(df)
        points = []
        
        for index, row in df.iterrows():
            point = Point(measurement)
            
            # Add all columns as fields
            for column in df.columns:
                value = row[column]
                if pd.notna(value):  # Skip NaN values
                    point.field(column, value)
            
            point.time(index if isinstance(index, datetime) else datetime.utcnow())
            points.append(point)
            
            # Write batch if we've reached batch size
            if len(points) >= self.config.batch_size:
                await self.write_batch(points)
                points = []
        
        # Write any remaining points
        if points:
            await self.write_batch(points)

    @contextmanager
    def batch_context(self):
        """Context manager for batch operations.
        
        Usage:
            async with client.batch_context() as batch:
                batch.write(point1)
                batch.write(point2)
        """
        try:
            batch = self.write_api.write(bucket=self.config.bucket, record=[])
            yield batch
        finally:
            batch.close()

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and metrics.
        
        Returns:
            Dict containing database statistics
        """
        try:
            stats = {
                'health': await self.is_healthy(),
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {}
            }
            
            # Query bucket statistics
            if await self.is_healthy():
                query = f'''
                from(bucket: "{self.config.bucket}")
                    |> range(start: -1h)
                    |> count()
                '''
                result = await self.query_data(query)
                if result is not None and not result.empty:
                    stats['metrics']['points_last_hour'] = int(result.iloc[0]['_value'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {
                'health': False,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }

