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
- Other common data types
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, List, Union, Optional
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
    """
    
    def default(self, obj: Any) -> Any:
        """Convert object to a JSON serializable type."""
        # NumPy types
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        
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
        
        # Custom objects
        if hasattr(obj, 'to_json') and callable(getattr(obj, 'to_json')):
            return obj.to_json()
        
        # Fallback to __dict__ for objects
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        
        # Let the base class default method raise the TypeError
        return super().default(obj)


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