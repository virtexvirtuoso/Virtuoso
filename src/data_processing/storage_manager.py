"""
Data Storage Manager
Implements configurable data storage with support for parquet, compression, and partitioning.
"""

import logging
import asyncio
import json
import gzip
import bz2
import lzma
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class StorageFormat(str, Enum):
    JSON = "json"
    PARQUET = "parquet"
    CSV = "csv"
    PICKLE = "pickle"


class CompressionType(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    SNAPPY = "snappy"
    LZ4 = "lz4"
    BROTLI = "brotli"
    ZSTD = "zstd"
    BZ2 = "bz2"
    LZMA = "lzma"


@dataclass
class StorageMetrics:
    """Storage operation metrics."""
    files_written: int = 0
    files_read: int = 0
    bytes_written: int = 0
    bytes_read: int = 0
    compression_ratio: float = 0.0
    avg_write_time_ms: float = 0.0
    avg_read_time_ms: float = 0.0
    errors: int = 0
    last_operation: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'files_written': self.files_written,
            'files_read': self.files_read,
            'bytes_written': self.bytes_written,
            'bytes_read': self.bytes_read,
            'compression_ratio': self.compression_ratio,
            'avg_write_time_ms': self.avg_write_time_ms,
            'avg_read_time_ms': self.avg_read_time_ms,
            'errors': self.errors,
            'last_operation': self.last_operation.isoformat() if self.last_operation else None
        }


@dataclass
class PartitionConfig:
    """Partition configuration for data storage."""
    enabled: bool
    columns: List[str]
    max_files_per_partition: int = 1000
    partition_size_mb: int = 100
    
    def generate_partition_path(self, data: Dict[str, Any]) -> str:
        """Generate partition path based on data and columns."""
        if not self.enabled or not self.columns:
            return ""
        
        parts = []
        for column in self.columns:
            if column in data:
                value = data[column]
                if isinstance(value, datetime):
                    # Date-based partitioning
                    if column == 'date':
                        parts.append(f"year={value.year}/month={value.month:02d}/day={value.day:02d}")
                    else:
                        parts.append(f"{column}={value.strftime('%Y-%m-%d')}")
                else:
                    parts.append(f"{column}={value}")
        
        return "/".join(parts)


class StorageManager:
    """Manages data storage with configurable formats, compression, and partitioning."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_config = config.get('data_processing', {}).get('storage', {})
        self.logger = logging.getLogger(__name__)
        
        # Storage configuration
        self.format = StorageFormat(self.storage_config.get('format', 'json'))
        self.compression = CompressionType(self.storage_config.get('compression', 'none'))
        self.base_path = Path(self.storage_config.get('base_path', './data'))
        
        # Partition configuration
        partition_config = self.storage_config.get('partition_by', [])
        self.partition_config = PartitionConfig(
            enabled=bool(partition_config),
            columns=partition_config if isinstance(partition_config, list) else []
        )
        
        # Performance settings
        self.buffer_size = self.storage_config.get('buffer_size', 8192)
        self.batch_size = self.storage_config.get('batch_size', 1000)
        self.enable_caching = self.storage_config.get('enable_caching', True)
        
        # Feature flags integration
        feature_flags = config.get('feature_flags', {})
        self.parquet_enabled = feature_flags.get('data', {}).get('parquet_storage', False)
        self.compression_enabled = feature_flags.get('data', {}).get('data_compression', False)
        
        # Metrics tracking
        self.metrics = StorageMetrics()
        self.operation_times: List[float] = []
        
        # Cache for frequently accessed data
        self.cache: Dict[str, Any] = {}
        self.cache_max_size = 100
        self.cache_ttl = timedelta(minutes=30)
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Storage Manager initialized")
        self.logger.info(f"Format: {self.format.value}, Compression: {self.compression.value}")
        self.logger.info(f"Base path: {self.base_path}")
        self.logger.info(f"Partitioning: {self.partition_config.enabled}")
        self.logger.info(f"Parquet enabled: {self.parquet_enabled}")
    
    async def store_data(self, 
                        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
                        filename: str,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data with configured format and compression.
        
        Args:
            data: Data to store
            filename: Base filename (without extension)
            metadata: Optional metadata to store alongside data
            
        Returns:
            True if successful, False otherwise
        """
        start_time = datetime.now()
        
        try:
            # Determine storage format
            actual_format = self.format
            if self.parquet_enabled and isinstance(data, (list, pd.DataFrame)):
                actual_format = StorageFormat.PARQUET
            
            # Generate file path with partitioning
            file_path = self._generate_file_path(filename, actual_format, data)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Store data based on format
            success = await self._store_by_format(data, file_path, actual_format, metadata)
            
            if success:
                # Update metrics
                file_size = file_path.stat().st_size if file_path.exists() else 0
                self.metrics.files_written += 1
                self.metrics.bytes_written += file_size
                self.metrics.last_operation = datetime.now()
                
                # Calculate operation time
                operation_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_avg_time('write', operation_time)
                
                self.logger.debug(f"Stored data to {file_path} ({file_size} bytes)")
                return True
            
        except Exception as e:
            self.metrics.errors += 1
            self.logger.error(f"Error storing data to {filename}: {str(e)}")
            
        return False
    
    async def load_data(self,
                       filename: str,
                       use_cache: bool = True) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]]:
        """
        Load data with automatic format detection and decompression.
        
        Args:
            filename: Filename to load
            use_cache: Whether to use cache for loading
            
        Returns:
            Loaded data or None if failed
        """
        start_time = datetime.now()
        
        # Check cache first
        if use_cache and self.enable_caching:
            cached_data = self._get_from_cache(filename)
            if cached_data is not None:
                return cached_data
        
        try:
            # Find the actual file (may have different extension/path due to partitioning)
            file_path = self._find_file_path(filename)
            if not file_path or not file_path.exists():
                self.logger.warning(f"File not found: {filename}")
                return None
            
            # Detect format from file extension
            format_detected = self._detect_format(file_path)
            
            # Load data based on format
            data = await self._load_by_format(file_path, format_detected)
            
            if data is not None:
                # Update metrics
                file_size = file_path.stat().st_size
                self.metrics.files_read += 1
                self.metrics.bytes_read += file_size
                self.metrics.last_operation = datetime.now()
                
                # Calculate operation time
                operation_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_avg_time('read', operation_time)
                
                # Cache the data
                if use_cache and self.enable_caching:
                    self._add_to_cache(filename, data)
                
                self.logger.debug(f"Loaded data from {file_path} ({file_size} bytes)")
                return data
            
        except Exception as e:
            self.metrics.errors += 1
            self.logger.error(f"Error loading data from {filename}: {str(e)}")
        
        return None
    
    def _generate_file_path(self, 
                          filename: str, 
                          format: StorageFormat, 
                          data: Any) -> Path:
        """Generate full file path with partitioning and extension."""
        # Add format extension
        if not filename.endswith(f".{format.value}"):
            filename = f"{filename}.{format.value}"
        
        # Add compression extension
        if self.compression_enabled and self.compression != CompressionType.NONE:
            filename = f"{filename}.{self.compression.value}"
        
        # Generate partition path
        partition_path = ""
        if self.partition_config.enabled:
            if isinstance(data, dict):
                partition_path = self.partition_config.generate_partition_path(data)
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                partition_path = self.partition_config.generate_partition_path(data[0])
            elif isinstance(data, pd.DataFrame) and not data.empty:
                # Use first row for partitioning
                first_row = data.iloc[0].to_dict()
                partition_path = self.partition_config.generate_partition_path(first_row)
        
        if partition_path:
            return self.base_path / partition_path / filename
        else:
            return self.base_path / filename
    
    def _find_file_path(self, filename: str) -> Optional[Path]:
        """Find actual file path considering different formats and partitions."""
        # Direct path first
        direct_path = self.base_path / filename
        if direct_path.exists():
            return direct_path
        
        # Try with different extensions
        for format in StorageFormat:
            for compression in CompressionType:
                test_name = filename
                
                if not test_name.endswith(f".{format.value}"):
                    test_name = f"{test_name}.{format.value}"
                
                if compression != CompressionType.NONE:
                    test_name = f"{test_name}.{compression.value}"
                
                test_path = self.base_path / test_name
                if test_path.exists():
                    return test_path
        
        # Search in partition directories (simplified search)
        for path in self.base_path.rglob(f"*{filename}*"):
            if path.is_file():
                return path
        
        return None
    
    def _detect_format(self, file_path: Path) -> StorageFormat:
        """Detect storage format from file extension."""
        path_str = str(file_path)
        
        if '.parquet' in path_str:
            return StorageFormat.PARQUET
        elif '.csv' in path_str:
            return StorageFormat.CSV
        elif '.pickle' in path_str:
            return StorageFormat.PICKLE
        else:
            return StorageFormat.JSON
    
    async def _store_by_format(self,
                             data: Any,
                             file_path: Path,
                             format: StorageFormat,
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store data based on specified format."""
        try:
            if format == StorageFormat.PARQUET:
                return await self._store_parquet(data, file_path, metadata)
            elif format == StorageFormat.CSV:
                return await self._store_csv(data, file_path)
            elif format == StorageFormat.PICKLE:
                return await self._store_pickle(data, file_path)
            else:  # JSON
                return await self._store_json(data, file_path, metadata)
        except Exception as e:
            self.logger.error(f"Error storing {format.value} data: {str(e)}")
            return False
    
    async def _load_by_format(self, file_path: Path, format: StorageFormat) -> Any:
        """Load data based on specified format."""
        try:
            if format == StorageFormat.PARQUET:
                return await self._load_parquet(file_path)
            elif format == StorageFormat.CSV:
                return await self._load_csv(file_path)
            elif format == StorageFormat.PICKLE:
                return await self._load_pickle(file_path)
            else:  # JSON
                return await self._load_json(file_path)
        except Exception as e:
            self.logger.error(f"Error loading {format.value} data: {str(e)}")
            return None
    
    async def _store_parquet(self, data: Any, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store data in Parquet format."""
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                raise ValueError(f"Cannot convert {type(data)} to DataFrame for Parquet storage")
            
            # Store metadata as Parquet metadata if provided
            parquet_metadata = {}
            if metadata:
                parquet_metadata.update(metadata)
            
            # Write with compression if enabled
            compression_arg = None
            if self.compression_enabled and self.compression != CompressionType.NONE:
                if self.compression == CompressionType.SNAPPY:
                    compression_arg = 'snappy'
                elif self.compression == CompressionType.GZIP:
                    compression_arg = 'gzip'
                elif self.compression == CompressionType.BROTLI:
                    compression_arg = 'brotli'
            
            df.to_parquet(
                file_path,
                compression=compression_arg,
                index=False
            )
            
            return True
            
        except ImportError:
            self.logger.error("Parquet support requires 'pyarrow' or 'fastparquet' package")
            return False
        except Exception as e:
            self.logger.error(f"Error storing Parquet data: {str(e)}")
            return False
    
    async def _load_parquet(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load data from Parquet format."""
        try:
            return pd.read_parquet(file_path)
        except ImportError:
            self.logger.error("Parquet support requires 'pyarrow' or 'fastparquet' package")
            return None
    
    async def _store_csv(self, data: Any, file_path: Path) -> bool:
        """Store data in CSV format."""
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                raise ValueError(f"Cannot convert {type(data)} to DataFrame for CSV storage")
            
            df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            self.logger.error(f"Error storing CSV data: {str(e)}")
            return False
    
    async def _load_csv(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load data from CSV format."""
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            self.logger.error(f"Error loading CSV data: {str(e)}")
            return None
    
    async def _store_pickle(self, data: Any, file_path: Path) -> bool:
        """Store data in Pickle format."""
        try:
            import pickle
            
            with open(file_path, 'wb') as f:
                if self.compression_enabled and self.compression != CompressionType.NONE:
                    data_bytes = pickle.dumps(data)
                    compressed_data = self._compress_data(data_bytes)
                    f.write(compressed_data)
                else:
                    pickle.dump(data, f)
            return True
        except Exception as e:
            self.logger.error(f"Error storing Pickle data: {str(e)}")
            return False
    
    async def _load_pickle(self, file_path: Path) -> Any:
        """Load data from Pickle format."""
        try:
            import pickle
            
            with open(file_path, 'rb') as f:
                if self.compression_enabled and self.compression != CompressionType.NONE:
                    compressed_data = f.read()
                    data_bytes = self._decompress_data(compressed_data)
                    return pickle.loads(data_bytes)
                else:
                    return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Error loading Pickle data: {str(e)}")
            return None
    
    async def _store_json(self, data: Any, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store data in JSON format."""
        try:
            # Prepare data for JSON serialization
            json_data = data
            if metadata:
                json_data = {
                    'data': data,
                    'metadata': metadata
                }
            
            # Convert numpy types to native Python types
            if isinstance(json_data, dict):
                json_data = self._convert_numpy_types(json_data)
            
            json_str = json.dumps(json_data, default=str, indent=2)
            
            if self.compression_enabled and self.compression != CompressionType.NONE:
                compressed_data = self._compress_data(json_str.encode())
                with open(file_path, 'wb') as f:
                    f.write(compressed_data)
            else:
                with open(file_path, 'w') as f:
                    f.write(json_str)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing JSON data: {str(e)}")
            return False
    
    async def _load_json(self, file_path: Path) -> Any:
        """Load data from JSON format."""
        try:
            if self.compression_enabled and self.compression != CompressionType.NONE:
                with open(file_path, 'rb') as f:
                    compressed_data = f.read()
                json_str = self._decompress_data(compressed_data).decode()
            else:
                with open(file_path, 'r') as f:
                    json_str = f.read()
            
            data = json.loads(json_str)
            
            # Extract data from metadata wrapper if present
            if isinstance(data, dict) and 'data' in data and 'metadata' in data:
                return data['data']
            
            return data
        except Exception as e:
            self.logger.error(f"Error loading JSON data: {str(e)}")
            return None
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using configured compression method."""
        if self.compression == CompressionType.GZIP:
            return gzip.compress(data)
        elif self.compression == CompressionType.BZ2:
            return bz2.compress(data)
        elif self.compression == CompressionType.LZMA:
            return lzma.compress(data)
        else:
            # Fallback to gzip
            return gzip.compress(data)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data using configured compression method."""
        if self.compression == CompressionType.GZIP:
            return gzip.decompress(data)
        elif self.compression == CompressionType.BZ2:
            return bz2.decompress(data)
        elif self.compression == CompressionType.LZMA:
            return lzma.decompress(data)
        else:
            # Try different methods
            for decompress_func in [gzip.decompress, bz2.decompress, lzma.decompress]:
                try:
                    return decompress_func(data)
                except:
                    continue
            raise ValueError("Unable to decompress data")
    
    def _convert_numpy_types(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def _get_from_cache(self, key: str) -> Any:
        """Get data from cache if available and not expired."""
        if key not in self.cache:
            return None
        
        timestamp = self.cache_timestamps.get(key)
        if timestamp and datetime.now() - timestamp > self.cache_ttl:
            # Cache expired
            del self.cache[key]
            del self.cache_timestamps[key]
            return None
        
        return self.cache[key]
    
    def _add_to_cache(self, key: str, data: Any):
        """Add data to cache with size management."""
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.cache_max_size:
            oldest_key = min(self.cache_timestamps.keys(), 
                           key=lambda k: self.cache_timestamps[k])
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
        
        self.cache[key] = data
        self.cache_timestamps[key] = datetime.now()
    
    def _update_avg_time(self, operation: str, time_ms: float):
        """Update average operation time."""
        self.operation_times.append(time_ms)
        
        # Keep only last 100 operations
        if len(self.operation_times) > 100:
            self.operation_times = self.operation_times[-100:]
        
        avg_time = sum(self.operation_times) / len(self.operation_times)
        
        if operation == 'write':
            self.metrics.avg_write_time_ms = avg_time
        else:
            self.metrics.avg_read_time_ms = avg_time
    
    def get_storage_metrics(self) -> Dict[str, Any]:
        """Get comprehensive storage metrics."""
        return {
            'metrics': self.metrics.to_dict(),
            'configuration': {
                'format': self.format.value,
                'compression': self.compression.value,
                'compression_enabled': self.compression_enabled,
                'parquet_enabled': self.parquet_enabled,
                'partitioning_enabled': self.partition_config.enabled,
                'partition_columns': self.partition_config.columns,
                'cache_enabled': self.enable_caching,
                'cache_size': len(self.cache),
                'cache_max_size': self.cache_max_size
            },
            'storage_info': {
                'base_path': str(self.base_path),
                'total_files': len(list(self.base_path.rglob('*.*'))),
                'total_size_mb': sum(f.stat().st_size for f in self.base_path.rglob('*.*') if f.is_file()) / (1024 * 1024)
            }
        }


def create_storage_manager(config: Dict[str, Any]) -> StorageManager:
    """Factory function to create storage manager from configuration."""
    return StorageManager(config)


async def test_storage_manager():
    """Test storage manager functionality."""
    config = {
        'data_processing': {
            'storage': {
                'format': 'json',
                'compression': 'gzip',
                'base_path': './test_data',
                'partition_by': ['date', 'symbol'],
                'buffer_size': 8192,
                'batch_size': 1000,
                'enable_caching': True
            }
        },
        'feature_flags': {
            'data': {
                'parquet_storage': True,
                'data_compression': True
            }
        }
    }
    
    # Create storage manager
    storage = StorageManager(config)
    
    # Test data
    test_data = [
        {
            'symbol': 'BTCUSDT',
            'timestamp': '2025-07-20T12:00:00',
            'price': 50000.0,
            'volume': 1000.0,
            'date': datetime.now()
        },
        {
            'symbol': 'ETHUSDT',
            'timestamp': '2025-07-20T12:01:00',
            'price': 3000.0,
            'volume': 500.0,
            'date': datetime.now()
        }
    ]
    
    metadata = {
        'source': 'test',
        'version': '1.0',
        'created_at': datetime.now().isoformat()
    }
    
    # Test storing data
    print("Testing data storage:")
    success = await storage.store_data(test_data, 'test_market_data', metadata)
    print(f"Store operation successful: {success}")
    
    # Test loading data
    print(f"\nTesting data loading:")
    loaded_data = await storage.load_data('test_market_data')
    print(f"Load operation successful: {loaded_data is not None}")
    if loaded_data:
        print(f"Loaded {len(loaded_data)} records")
    
    # Test DataFrame storage (Parquet)
    print(f"\nTesting DataFrame/Parquet storage:")
    df = pd.DataFrame(test_data)
    success = await storage.store_data(df, 'test_dataframe')
    print(f"DataFrame store successful: {success}")
    
    loaded_df = await storage.load_data('test_dataframe')
    print(f"DataFrame load successful: {loaded_df is not None}")
    if loaded_df is not None:
        print(f"Loaded DataFrame shape: {loaded_df.shape}")
    
    # Get metrics
    metrics = storage.get_storage_metrics()
    print(f"\nStorage Metrics:")
    print(f"Files written: {metrics['metrics']['files_written']}")
    print(f"Files read: {metrics['metrics']['files_read']}")
    print(f"Bytes written: {metrics['metrics']['bytes_written']}")
    print(f"Bytes read: {metrics['metrics']['bytes_read']}")
    print(f"Cache size: {metrics['configuration']['cache_size']}")
    print(f"Total files: {metrics['storage_info']['total_files']}")
    print(f"Total size: {metrics['storage_info']['total_size_mb']:.2f} MB")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_storage_manager())