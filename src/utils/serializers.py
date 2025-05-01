"""
Serialization utilities for consistent data handling.

This module provides standardized serialization functions to ensure
consistent handling of complex data types across components.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Union, Optional
from datetime import datetime, date, time
import json
import logging

logger = logging.getLogger(__name__)

def serialize_for_json(obj: Any) -> Any:
    """
    Universal serializer that converts complex objects to JSON-compatible types.
    
    Handles:
    - NumPy types (arrays, scalars)
    - Pandas objects
    - Datetime objects
    - Custom objects with __dict__ attribute
    - Nested dictionaries and lists
    
    Args:
        obj: Any Python object to serialize
        
    Returns:
        JSON-compatible representation of the object
    """
    try:
        # Handle None
        if obj is None:
            return None
            
        # Handle numpy arrays
        if isinstance(obj, np.ndarray):
            return obj.tolist()
            
        # Handle numpy scalars (float64, int64, etc.)
        if hasattr(obj, 'item') and callable(getattr(obj, 'item')):
            return obj.item()
            
        # Handle pandas Series or DataFrame
        if isinstance(obj, (pd.Series, pd.DataFrame)):
            return obj.to_dict()
            
        # Handle datetime objects
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
            
        # Handle dictionaries (recursive)
        if isinstance(obj, dict):
            return {k: serialize_for_json(v) for k, v in obj.items()}
            
        # Handle lists and tuples (recursive)
        if isinstance(obj, (list, tuple)):
            return [serialize_for_json(item) for item in obj]
            
        # Handle objects with __dict__ attribute
        if hasattr(obj, '__dict__'):
            return serialize_for_json(obj.__dict__)
            
        # Default: try direct conversion or string representation
        try:
            # Try direct json serialization
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            # Fall back to string representation
            return str(obj)
            
    except Exception as e:
        logger.error(f"Error serializing object of type {type(obj)}: {str(e)}")
        # Return a safe fallback
        return str(obj)

def prepare_data_for_transmission(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare a data dictionary for transmission between components.
    Ensures all values are JSON serializable.
    
    Args:
        data: Dictionary containing potentially non-serializable values
        
    Returns:
        Dictionary with all values serialized to JSON-compatible types
    """
    if not isinstance(data, dict):
        logger.warning(f"Expected dict for serialization, got {type(data)}")
        if hasattr(data, '__dict__'):
            data = data.__dict__
        else:
            return {"error": f"Cannot serialize non-dict type: {type(data)}"}
    
    return serialize_for_json(data) 