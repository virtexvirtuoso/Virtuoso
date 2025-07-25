"""
Data processing interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional, List, Union, Callable, runtime_checkable
from datetime import datetime
import pandas as pd

@runtime_checkable
class DataProcessorInterface(Protocol):
    """Interface for data processors."""
    
    @abstractmethod
    def process(self, data: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Process data according to configuration.
        
        Args:
            data: Input data
            config: Processing configuration
            
        Returns:
            Processed data
        """
        pass
    
    @abstractmethod
    def validate_input(self, data: Any) -> bool:
        """Validate input data format."""
        pass
    
    @abstractmethod
    def get_processing_pipeline(self) -> List[Callable]:
        """Get list of processing steps."""
        pass

@runtime_checkable
class DataTransformerInterface(Protocol):
    """Interface for data transformers."""
    
    @abstractmethod
    def transform(self, data: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
        """Apply transformations to data."""
        pass
    
    @abstractmethod
    def get_available_transformations(self) -> List[str]:
        """Get list of available transformations."""
        pass
    
    @abstractmethod
    def validate_transformation(self, transformation: Dict[str, Any]) -> bool:
        """Validate transformation configuration."""
        pass

@runtime_checkable
class DataAggregatorInterface(Protocol):
    """Interface for data aggregators."""
    
    @abstractmethod
    def aggregate(self, data: pd.DataFrame, groupby: List[str], aggregations: Dict[str, str]) -> pd.DataFrame:
        """
        Aggregate data.
        
        Args:
            data: Input data
            groupby: Columns to group by
            aggregations: Column -> aggregation function mapping
            
        Returns:
            Aggregated data
        """
        pass
    
    @abstractmethod
    def resample_timeseries(self, data: pd.DataFrame, frequency: str, aggregation: str = 'mean') -> pd.DataFrame:
        """Resample timeseries data."""
        pass

@runtime_checkable
class DataFilterInterface(Protocol):
    """Interface for data filters."""
    
    @abstractmethod
    def filter(self, data: pd.DataFrame, conditions: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Filter data based on conditions.
        
        Args:
            data: Input data
            conditions: List of filter conditions
            
        Returns:
            Filtered data
        """
        pass
    
    @abstractmethod
    def create_filter_expression(self, conditions: List[Dict[str, Any]]) -> str:
        """Create filter expression from conditions."""
        pass

@runtime_checkable
class DataCacheInterface(Protocol):
    """Interface for data caching."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get data from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set data in cache.
        
        Args:
            key: Cache key
            value: Data to cache
            ttl: Time to live in seconds
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached data."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

@runtime_checkable
class DataPipelineInterface(Protocol):
    """Interface for data pipelines."""
    
    @abstractmethod
    def add_step(self, name: str, processor: Callable, config: Optional[Dict[str, Any]] = None) -> None:
        """Add processing step to pipeline."""
        pass
    
    @abstractmethod
    def remove_step(self, name: str) -> bool:
        """Remove processing step from pipeline."""
        pass
    
    @abstractmethod
    async def execute(self, data: Any) -> Any:
        """Execute pipeline on data."""
        pass
    
    @abstractmethod
    def get_pipeline_config(self) -> List[Dict[str, Any]]:
        """Get pipeline configuration."""
        pass

class DataProcessorAdapter:
    """Adapter to make existing processors compatible with DataProcessorInterface."""
    
    def __init__(self, processor: Any):
        self.processor = processor
        
    def process(self, data: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """Process data according to configuration."""
        if hasattr(self.processor, 'process'):
            if config:
                return self.processor.process(data, config)
            return self.processor.process(data)
        elif hasattr(self.processor, 'transform'):
            return self.processor.transform(data)
        elif hasattr(self.processor, 'apply'):
            return self.processor.apply(data)
        else:
            raise NotImplementedError(f"Processor {type(self.processor)} has no processing method")
            
    def validate_input(self, data: Any) -> bool:
        """Validate input data format."""
        if hasattr(self.processor, 'validate_input'):
            return self.processor.validate_input(data)
        elif hasattr(self.processor, 'is_valid'):
            return self.processor.is_valid(data)
        else:
            # Default validation - check if data is not None
            return data is not None
            
    def get_processing_pipeline(self) -> List[Callable]:
        """Get list of processing steps."""
        if hasattr(self.processor, 'get_processing_pipeline'):
            return self.processor.get_processing_pipeline()
        elif hasattr(self.processor, 'pipeline'):
            return self.processor.pipeline
        else:
            return []