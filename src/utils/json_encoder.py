#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON encoder utility for handling various data types in the trading application.

This module provides a custom JSON encoder that handles:
- NumPy arrays and scalar types
- Pandas DataFrames and Series
- Datetime objects
- Custom objects with to_json method
- Decimal values
- Mappingproxy objects (from numpy and other sources)
- Circular reference detection
- Other common data types
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, List, Union, Optional, Set
from types import MappingProxyType
import logging

# Set up logging
logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles special data types used in trading applications.
    
    Handles:
    - NumPy arrays and scalar types
    - Pandas DataFrames and Series
    - Datetime objects
    - Custom objects with to_json method
    - Objects with __dict__ attribute
    - Decimal values
    - Mappingproxy objects
    - Complex numpy objects
    - Circular reference detection
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visited = set()
    
    def encode(self, obj):
        """Override encode to handle circular references at the top level."""
        self._visited = set()
        # Pre-process the object to handle circular references
        processed_obj = self._preprocess_for_circular_refs(obj)
        return super().encode(processed_obj)
    
    def _preprocess_for_circular_refs(self, obj, visited=None):
        """Preprocess object to remove circular references before JSON encoding."""
        if visited is None:
            visited = set()
            
        obj_id = id(obj)
        
        # Check for circular reference
        if obj_id in visited:
            return f"<circular_reference:{type(obj).__name__}@{hex(obj_id)}>"
        
        # Add to visited for complex types
        if isinstance(obj, (dict, list, tuple, set, frozenset)):
            visited.add(obj_id)
        
        try:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    result[str(k)] = self._preprocess_for_circular_refs(v, visited.copy())
                return result
            elif isinstance(obj, (list, tuple)):
                result = []
                for item in obj:
                    result.append(self._preprocess_for_circular_refs(item, visited.copy()))
                return result if isinstance(obj, list) else tuple(result)
            elif isinstance(obj, (set, frozenset)):
                result = []
                for item in obj:
                    result.append(self._preprocess_for_circular_refs(item, visited.copy()))
                return result
            else:
                return obj
        finally:
            # Remove from visited set when done
            if isinstance(obj, (dict, list, tuple, set, frozenset)) and obj_id in visited:
                visited.discard(obj_id)
    
    def default(self, obj: Any) -> Any:
        """Convert object to a JSON serializable type with circular reference detection."""
        
        # Get object ID for circular reference detection
        obj_id = id(obj)
        
        # Check for circular reference in complex objects
        if isinstance(obj, (dict, list, tuple, set, frozenset)) and obj_id in self._visited:
            return f"<circular_reference:{type(obj).__name__}@{hex(obj_id)}>"
        
        # Add to visited set for complex objects
        if isinstance(obj, (dict, list, tuple, set, frozenset)):
            self._visited.add(obj_id)
        
        try:
            # Handle mappingproxy objects (common in numpy)
            if isinstance(obj, MappingProxyType):
                return dict(obj)
            
            # NumPy types - Enhanced handling
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.str_):
                return str(obj)
            if isinstance(obj, np.bytes_):
                return obj.decode('utf-8')
            
            # Handle numpy void types and structured arrays
            if hasattr(obj, 'dtype') and hasattr(obj, 'item'):
                try:
                    return obj.item()
                except (ValueError, TypeError):
                    return str(obj)
            
            # Datetime types
            if isinstance(obj, (datetime, date, time)):
                return obj.isoformat()
            
            # Pandas types
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient='records')
            if isinstance(obj, pd.Series):
                return obj.to_dict()
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            
            # Decimal type
            if isinstance(obj, Decimal):
                return float(obj)
            
            # Set and frozenset types
            if isinstance(obj, (set, frozenset)):
                return list(obj)
            
            # Complex number types
            if isinstance(obj, complex):
                return {'real': obj.real, 'imag': obj.imag}
            
            # Custom objects
            if hasattr(obj, 'to_json') and callable(getattr(obj, 'to_json')):
                try:
                    return obj.to_json()
                except Exception as e:
                    logger.warning(f"Failed to call to_json() on {type(obj).__name__}: {e}")
                    return f"<to_json_failed:{type(obj).__name__}>"
            
            # Handle objects with __dict__ but exclude functions and classes
            if hasattr(obj, '__dict__') and not callable(obj) and not isinstance(obj, type):
                try:
                    # Recursively process the __dict__ but avoid circular references
                    if obj_id not in self._visited:
                        self._visited.add(obj_id)
                        return obj.__dict__
                    else:
                        return f"<circular_object:{type(obj).__name__}@{hex(obj_id)}>"
                except (TypeError, AttributeError):
                    return f"<object_dict_error:{type(obj).__name__}>"
            
            # Handle iterables that aren't strings
            if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                try:
                    return list(obj)
                except (TypeError, ValueError):
                    return f"<iterable_error:{type(obj).__name__}>"
            
            # Fallback to string representation for unhandled types
            try:
                return str(obj)
            except Exception:
                return f"<unserializable:{type(obj).__name__}@{hex(obj_id)}>"
                
        finally:
            # Remove from visited set when done processing this object
            if isinstance(obj, (dict, list, tuple, set, frozenset)) and obj_id in self._visited:
                self._visited.discard(obj_id)


def json_serialize(obj: Any, pretty: bool = False) -> str:
    """
    Serialize an object to a JSON string, handling special data types.
    
    Args:
        obj: The object to serialize
        pretty: If True, format the output with indentation for readability
    
    Returns:
        JSON string representation of the object
    """
    indent = 4 if pretty else None
    return json.dumps(obj, cls=CustomJSONEncoder, indent=indent)


def json_serialize_to_file(obj: Any, filepath: str, pretty: bool = True) -> None:
    """
    Serialize an object to a JSON file, handling special data types.
    
    Args:
        obj: The object to serialize
        filepath: The path to the output file
        pretty: If True, format the output with indentation for readability
    """
    indent = 4 if pretty else None
    with open(filepath, 'w') as f:
        json.dump(obj, f, cls=CustomJSONEncoder, indent=indent)


def json_deserialize(json_str: str) -> Any:
    """
    Deserialize a JSON string to Python objects.
    
    Args:
        json_str: JSON string to deserialize
    
    Returns:
        Python object representation of the JSON
    """
    return json.loads(json_str)


def json_deserialize_from_file(filepath: str) -> Any:
    """
    Deserialize a JSON file to Python objects.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        Python object representation of the JSON file contents
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def safe_json_serialize(obj: Any, default: Optional[str] = None) -> str:
    """
    Safely serialize an object to JSON, returning a default value on error.
    
    Args:
        obj: The object to serialize
        default: Default value to return if serialization fails (a JSON string)
    
    Returns:
        JSON string or the default value if serialization fails
    """
    # Fix: First check if the object is a function or otherwise unserializable
    if callable(obj) and not hasattr(obj, 'to_json') and not hasattr(obj, '__dict__'):
        logger.debug(f"Object is a function and not serializable")
        if default is not None:
            logger.debug(f"Returning default: {default}")
            return default
        else:
            logger.debug("No default provided, returning error object")
            return json_serialize({"error": "Cannot serialize function object"})
    
    # Attempt serialization
    try:
        return json_serialize(obj)
    except (TypeError, OverflowError, ValueError) as e:
        logger.debug(f"Error in safe_json_serialize: {str(e)}")
        if default is not None:
            logger.debug(f"Returning default: {default}")
            return default
        # If no default is provided, return an error object as JSON
        logger.debug("No default provided, returning error object")
        return json_serialize({"error": str(e)}) 