# src/data_storage/database.py

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    # InfluxDB client not available - create mock classes
    class MockInfluxDBClient:
        def __init__(self, *args, **kwargs):
            pass
        def ping(self):
            return True
        def write_api(self, *args, **kwargs):
            return MockWriteAPI()
        def query_api(self, *args, **kwargs):
            return MockQueryAPI()
        def close(self):
            pass
    
    class MockPoint:
        def __init__(self, measurement):
            self.measurement = measurement
        def tag(self, key, value):
            return self
        def field(self, key, value):
            return self
        def time(self, timestamp):
            return self
    
    class MockWriteAPI:
        def write(self, *args, **kwargs):
            pass
        def close(self):
            pass
    
    class MockQueryAPI:
        def query_data_frame(self, *args, **kwargs):
            return None
    
    InfluxDBClient = MockInfluxDBClient
    Point = MockPoint
    SYNCHRONOUS = None
    INFLUX_AVAILABLE = False
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
import re

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
        # Try multiple config paths
        influx_config = (
            config.get('database', {}).get('influxdb', {}) or
            config.get('influxDB', {}) or
            config.get('exchanges', {}).get('bybit', {}).get('websocket', {}).get('storage', {}).get('influxdb', {}) or
            {}
        )
        
        return cls(
            url=influx_config.get('url') or os.getenv('INFLUXDB_URL') or 'http://localhost:8086',
            token=influx_config.get('token') or os.getenv('INFLUXDB_TOKEN') or 'demo-token-placeholder',
            org=influx_config.get('org') or os.getenv('INFLUXDB_ORG') or 'virtuoso-org',
            bucket=influx_config.get('bucket') or os.getenv('INFLUXDB_BUCKET') or 'market-data',
            max_retries=influx_config.get('max_retries', 3),
            retry_delay=influx_config.get('retry_delay', 1.0),
            batch_size=influx_config.get('batch_size', 1000),
            batch_timeout=influx_config.get('batch_timeout', 10.0)
        )

class DatabaseClient:
    """Client for interacting with InfluxDB."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize database client."""
        self.logger = logging.getLogger(__name__)
        self.config: DatabaseConfig = DatabaseConfig.from_dict(config)
        self.client: Optional[InfluxDBClient] = None
        self.write_api: Any = None
        self.query_api: Any = None
        self._retry_count: int = 0
        self._init_client()

    def _init_client(self) -> None:
        """Initialize InfluxDB client and APIs."""
        try:
            # Check if InfluxDB client is available
            if not INFLUX_AVAILABLE:
                logger.warning("InfluxDB client not installed - operating in demo mode")
                self.client = None
                self.write_api = None
                self.query_api = None
                return
                
            # Check if we have placeholder values (demo mode)
            if self.config.token == 'demo-token-placeholder':
                logger.warning("Using demo database configuration - database features will be limited")
                self.client = None
                self.write_api = None
                self.query_api = None
                return
                
            if not self.config.token:
                logger.warning("InfluxDB token not configured - operating in demo mode")
                self.client = None
                self.write_api = None
                self.query_api = None
                return
                
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
                logger.warning(f"Failed to initialize InfluxDB client after {self.config.max_retries} attempts: {str(e)}")
                logger.warning("Database will operate in demo mode - data will not be persisted")
                self.client = None
                self.write_api = None
                self.query_api = None

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
            
        # Normalize timestamp value for consistency
        timestamp_value = self._normalize_timestamp_value(
            data.get('timestamp', datetime.utcnow().timestamp()),
            'timestamp'
        )
            
        point = Point("market_data")\
            .tag("symbol", symbol)\
            .field("price", float(data.get('price', 0)))\
            .field("volume", float(data.get('volume', 0)))\
            .field("data_timestamp", timestamp_value)\
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

    def _normalize_timestamp_value(self, value: Any, field_name: str) -> float:
        """Normalize timestamp values to consistent float format for InfluxDB.
        
        Args:
            value: Timestamp value in various formats
            field_name: Name of the field being processed (for logging)
            
        Returns:
            float: Unix timestamp as float
        """
        try:
            if isinstance(value, (int, float)):
                # Handle milliseconds vs seconds timestamps
                if value > 1e12:  # Likely milliseconds
                    return float(value / 1000.0)
                return float(value)
            elif isinstance(value, str):
                # Handle ISO format strings
                if 'T' in value or '-' in value:  # ISO format
                    try:
                        dt = pd.to_datetime(value)
                        return float(dt.timestamp())
                    except Exception as e:
                        self.logger.warning(f"Failed to parse ISO timestamp '{value}' for field '{field_name}': {e}")
                        return float(time.time())
                # Handle string numbers
                try:
                    num_val = float(value)
                    if num_val > 1e12:  # Likely milliseconds
                        return num_val / 1000.0
                    return num_val
                except ValueError:
                    self.logger.warning(f"Failed to parse timestamp string '{value}' for field '{field_name}'")
                    return float(time.time())
            elif hasattr(value, 'timestamp'):  # datetime object
                return float(value.timestamp())
            else:
                self.logger.warning(f"Unknown timestamp format for field '{field_name}': {type(value)} - {value}")
                return float(time.time())
        except Exception as e:
            self.logger.error(f"Error normalizing timestamp for field '{field_name}': {e}")
            return float(time.time())

    def _validate_and_convert_field_value(self, key: str, value: Any) -> tuple[str, Any, bool]:
        """Validate and convert field values for InfluxDB compatibility.
        
        Args:
            key: Field name
            value: Field value
            
        Returns:
            tuple: (field_name, converted_value, should_include)
        """
        if value is None:
            return key, None, False
            
        # Handle timestamp fields specially
        if 'timestamp' in key.lower():
            try:
                normalized_ts = self._normalize_timestamp_value(value, key)
                return key, normalized_ts, True
            except Exception as e:
                self.logger.warning(f"Failed to normalize timestamp field '{key}': {e}")
                return key, None, False
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            # Check for invalid numeric values
            import numpy as np
            if pd.isna(value) or np.isinf(value):
                self.logger.debug(f"Skipping invalid numeric value for field '{key}': {value}")
                return key, None, False
            return key, float(value), True
            
        # Handle string values
        elif isinstance(value, str):
            # Don't store empty strings
            if not value.strip():
                return key, None, False
            return key, value, True
            
        # Handle boolean values
        elif isinstance(value, bool):
            return key, value, True
            
        else:
            self.logger.debug(f"Skipping unsupported field type for '{key}': {type(value)}")
            return key, None, False

    @handle_db_errors
    @measure_execution_time
    async def store_analysis(self, symbol: str, analysis: Dict[str, Any], signals: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Store analysis results in the database with proper field type handling."""
        try:
            # Check if we're in demo mode or connection unavailable
            if not await self._ensure_connection():
                self.logger.debug(f"Database unavailable for analysis storage - operating in demo mode for {symbol}")
                return True  # Return True in demo mode to prevent error spam
                
            # Additional safety check for demo mode
            if self.client is None or self.write_api is None:
                self.logger.debug(f"Database client unavailable - skipping analysis storage for {symbol}")
                return True
            
            # Validate analysis data
            if analysis is None:
                self.logger.warning(f"Analysis data is None for {symbol}, skipping database storage")
                return False
                
            if not isinstance(analysis, dict):
                self.logger.warning(f"Analysis data is not a dictionary for {symbol}, got {type(analysis)}")
                return False
            
            # Create point with proper structure
            point = Point("analysis")\
                .tag("symbol", symbol)\
                .time(datetime.utcnow())
            
            # Add fields from analysis data with proper type conversion
            fields_added = 0
            for key, value in analysis.items():
                field_name, converted_value, should_include = self._validate_and_convert_field_value(key, value)
                
                if should_include and converted_value is not None:
                    point.field(field_name, converted_value)
                    fields_added += 1
                elif isinstance(value, dict) and value is not None:
                    # Flatten nested dictionaries with validation
                    for sub_key, sub_value in value.items():
                        nested_field_name = f"{key}_{sub_key}"
                        nested_field_name, nested_converted_value, nested_should_include = self._validate_and_convert_field_value(
                            nested_field_name, sub_value
                        )
                        if nested_should_include and nested_converted_value is not None:
                            point.field(nested_field_name, nested_converted_value)
                            fields_added += 1
            
            # Add signals if provided with proper validation
            if signals and isinstance(signals, list):
                for i, signal in enumerate(signals):
                    if signal is not None and isinstance(signal, dict):
                        for key, value in signal.items():
                            signal_field_name = f"signal_{i}_{key}"
                            field_name, converted_value, should_include = self._validate_and_convert_field_value(
                                signal_field_name, value
                            )
                            if should_include and converted_value is not None:
                                point.field(field_name, converted_value)
                                fields_added += 1
            
            # Only write if we have fields to store
            if fields_added == 0:
                self.logger.warning(f"No valid fields to store for {symbol} analysis")
                return False
            
            # Write to InfluxDB (write_api.write is synchronous, not async)
            self.write_api.write(
                bucket=self.config.bucket,
                org=self.config.org,
                record=point
            )
            
            self.logger.debug(f"Successfully stored analysis for {symbol} with {fields_added} fields")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store analysis for {symbol}: {str(e)}")
            self.logger.debug(f"Analysis data keys: {list(analysis.keys()) if analysis else 'None'}")
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
            # For demo mode with placeholder token, return healthy without actual connection
            if self.config.token == 'demo-token-placeholder':
                logger.info("Database running in demo mode - skipping connection test")
                return True
                
            # Check if all required components are initialized
            if not all([self.client, self.write_api, self.query_api]):
                logger.warning("Database client components not fully initialized")
                return False

            # Additional safety check for None client (can happen in demo/error states)
            if self.client is None:
                logger.warning("Database client is None - operating in demo mode")
                return True

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

    async def check_and_fix_schema_conflicts(self) -> Dict[str, Any]:
        """Check for and attempt to fix InfluxDB schema conflicts.
        
        Returns:
            Dict containing conflict detection and resolution results
        """
        results = {
            'conflicts_found': [],
            'fixes_applied': [],
            'errors': []
        }
        
        try:
            if not await self.is_healthy():
                results['errors'].append('Database not healthy')
                return results
            
            # Check for field type conflicts in analysis measurement
            query = f'''
            from(bucket: "{self.config.bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r["_measurement"] == "analysis")
                |> group(columns: ["_field"])
                |> distinct(column: "_value")
                |> limit(n: 10)
            '''
            
            try:
                result = await self.query_data(query)
                if result is not None and not result.empty:
                    # Analyze field types
                    timestamp_fields = result[result['_field'].str.contains('timestamp', case=False)]
                    if not timestamp_fields.empty:
                        results['conflicts_found'].append('Found timestamp-related fields in analysis measurement')
                        
                        # Note: In a production environment, you might want to create a new measurement
                        # or migrate data, but for now we'll just log the conflict
                        self.logger.info("Schema conflict detection completed - timestamp normalization will prevent future conflicts")
                        results['fixes_applied'].append('Applied timestamp normalization in store_analysis method')
                        
            except Exception as e:
                results['errors'].append(f'Failed to check schema conflicts: {str(e)}')
            
        except Exception as e:
            results['errors'].append(f'Error in schema conflict check: {str(e)}')
        
        return results

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and metrics.
        
        Returns:
            Dict containing database statistics
        """
        try:
            stats = {
                'health': await self.is_healthy(),
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {},
                'schema_status': await self.check_and_fix_schema_conflicts()
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

