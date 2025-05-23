#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for JSON serialization of various data types.

This module tests the CustomJSONEncoder's ability to properly serialize:
- NumPy arrays and scalar types
- Pandas DataFrames and Series
- Datetime objects
- Custom objects with to_json method
- Objects with __dict__ attribute
- Decimal values
- Complex nested structures
"""

import unittest
import json
import numpy as np
import pandas as pd
from datetime import datetime, date, time
from decimal import Decimal
import sys
import os
import logging
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.json_encoder import (
    CustomJSONEncoder, 
    json_serialize, 
    json_deserialize,
    json_serialize_to_file,
    json_deserialize_from_file,
    safe_json_serialize
)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CustomObject:
    """Simple custom object for testing serialization."""
    
    def __init__(self, name, value):
        self.name = name
        self.value = value


class SerializableObject:
    """Object with a to_json method for testing serialization."""
    
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def to_json(self):
        return {"name": self.name, "value": self.value}


class TestJSONSerialization(unittest.TestCase):
    """Test suite for CustomJSONEncoder and JSON serialization utilities."""
    
    def test_numpy_scalar_serialization(self):
        """Test serialization of NumPy scalar types."""
        # Integer types
        int_types = {
            'int8': np.int8(42),
            'int16': np.int16(42),
            'int32': np.int32(42),
            'int64': np.int64(42)
        }
        
        for type_name, value in int_types.items():
            serialized = json_serialize(value)
            logger.debug(f"Serialized {type_name}: {serialized}")
            self.assertEqual(serialized, "42")
            self.assertEqual(json_deserialize(serialized), 42)
        
        # Float types
        float_types = {
            'float16': np.float16(3.14),
            'float32': np.float32(3.14),
            'float64': np.float64(3.14)
        }
        
        for type_name, value in float_types.items():
            serialized = json_serialize(value)
            logger.debug(f"Serialized {type_name}: {serialized}")
            deserialized = json_deserialize(serialized)
            self.assertAlmostEqual(deserialized, 3.14, places=2)
        
        # Boolean type
        bool_value = np.bool_(True)
        serialized = json_serialize(bool_value)
        logger.debug(f"Serialized bool: {serialized}")
        self.assertEqual(serialized, "true")
        self.assertEqual(json_deserialize(serialized), True)
    
    def test_numpy_array_serialization(self):
        """Test serialization of NumPy arrays."""
        # 1D array
        arr_1d = np.array([1, 2, 3, 4, 5])
        serialized = json_serialize(arr_1d)
        logger.debug(f"Serialized 1D array: {serialized}")
        self.assertEqual(json_deserialize(serialized), [1, 2, 3, 4, 5])
        
        # 2D array
        arr_2d = np.array([[1, 2, 3], [4, 5, 6]])
        serialized = json_serialize(arr_2d)
        logger.debug(f"Serialized 2D array: {serialized}")
        self.assertEqual(json_deserialize(serialized), [[1, 2, 3], [4, 5, 6]])
        
        # Mixed types array
        arr_mixed = np.array([1, 2.5, 3, 4.5])
        serialized = json_serialize(arr_mixed)
        logger.debug(f"Serialized mixed array: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertEqual(len(deserialized), 4)
        self.assertEqual(deserialized[0], 1.0)
        self.assertEqual(deserialized[1], 2.5)
    
    def test_datetime_serialization(self):
        """Test serialization of datetime objects."""
        # Datetime
        dt = datetime(2023, 1, 15, 12, 30, 45)
        serialized = json_serialize(dt)
        logger.debug(f"Serialized datetime: {serialized}")
        self.assertEqual(serialized, '"2023-01-15T12:30:45"')
        
        # Date
        d = date(2023, 1, 15)
        serialized = json_serialize(d)
        logger.debug(f"Serialized date: {serialized}")
        self.assertEqual(serialized, '"2023-01-15"')
        
        # Time
        t = time(12, 30, 45)
        serialized = json_serialize(t)
        logger.debug(f"Serialized time: {serialized}")
        self.assertEqual(serialized, '"12:30:45"')
    
    def test_pandas_serialization(self):
        """Test serialization of pandas objects."""
        # Series
        s = pd.Series([1, 2, 3, 4, 5], index=['a', 'b', 'c', 'd', 'e'])
        serialized = json_serialize(s)
        logger.debug(f"Serialized Series: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, dict)
        self.assertEqual(deserialized['a'], 1)
        self.assertEqual(deserialized['e'], 5)
        
        # DataFrame
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['a', 'b', 'c'],
            'C': [True, False, True]
        })
        serialized = json_serialize(df)
        logger.debug(f"Serialized DataFrame: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, list)
        self.assertEqual(len(deserialized), 3)
        self.assertEqual(deserialized[0]['A'], 1)
        self.assertEqual(deserialized[1]['B'], 'b')
        self.assertEqual(deserialized[2]['C'], True)
        
        # DataFrame with DatetimeIndex
        df_dates = pd.DataFrame(
            {'value': [1, 2, 3]},
            index=pd.date_range('2023-01-01', periods=3)
        )
        serialized = json_serialize(df_dates)
        logger.debug(f"Serialized DataFrame with DatetimeIndex: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, list)
        self.assertEqual(len(deserialized), 3)
        self.assertEqual(deserialized[0]['value'], 1)
    
    def test_decimal_serialization(self):
        """Test serialization of Decimal objects."""
        d = Decimal('3.14159265358979323846')
        serialized = json_serialize(d)
        logger.debug(f"Serialized Decimal: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, float)
        # Less strict comparison to avoid precision issues
        self.assertGreaterEqual(deserialized, 3.14159)
        self.assertLessEqual(deserialized, 3.1416)
    
    def test_custom_object_serialization(self):
        """Test serialization of custom objects using __dict__."""
        obj = CustomObject("test_name", 42)
        serialized = json_serialize(obj)
        logger.debug(f"Serialized custom object: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, dict)
        self.assertEqual(deserialized['name'], "test_name")
        self.assertEqual(deserialized['value'], 42)
    
    def test_serializable_object(self):
        """Test serialization of objects with to_json method."""
        obj = SerializableObject("test_name", 42)
        serialized = json_serialize(obj)
        logger.debug(f"Serialized SerializableObject: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsInstance(deserialized, dict)
        self.assertEqual(deserialized['name'], "test_name")
        self.assertEqual(deserialized['value'], 42)
    
    def test_complex_nested_structure(self):
        """Test serialization of complex nested structures."""
        # Create a complex nested structure with various data types
        complex_obj = {
            'numpy_array': np.array([1, 2, 3]),
            'dataframe': pd.DataFrame({'A': [1, 2], 'B': [3, 4]}),
            'date': datetime.now().date(),
            'custom_obj': CustomObject("nested", 99),
            'nested_dict': {
                'decimal': Decimal('1.234'),
                'array': np.array([5, 6, 7]),
                'serializable': SerializableObject("inner", 100)
            },
            'list_of_mixed': [
                1,
                np.int32(2),
                pd.Series([3, 4]),
                CustomObject("list_item", 5)
            ]
        }
        
        serialized = json_serialize(complex_obj, pretty=True)
        logger.debug(f"Serialized complex structure: {serialized}")
        deserialized = json_deserialize(serialized)
        
        # Verify key parts of the structure
        self.assertIsInstance(deserialized, dict)
        self.assertEqual(deserialized['numpy_array'], [1, 2, 3])
        self.assertIsInstance(deserialized['dataframe'], list)
        self.assertEqual(len(deserialized['dataframe']), 2)
        self.assertIsInstance(deserialized['date'], str)
        self.assertEqual(deserialized['custom_obj']['name'], "nested")
        self.assertEqual(deserialized['custom_obj']['value'], 99)
        self.assertAlmostEqual(deserialized['nested_dict']['decimal'], 1.234, places=3)
        self.assertEqual(deserialized['nested_dict']['array'], [5, 6, 7])
        self.assertEqual(deserialized['nested_dict']['serializable']['name'], "inner")
        
        # Check the mixed list
        self.assertEqual(deserialized['list_of_mixed'][0], 1)
        self.assertEqual(deserialized['list_of_mixed'][1], 2)
        self.assertIsInstance(deserialized['list_of_mixed'][2], dict)
        self.assertEqual(deserialized['list_of_mixed'][3]['name'], "list_item")
    
    def test_none_values(self):
        """Test serialization of None values."""
        obj = {'key1': None, 'key2': 'value2'}
        serialized = json_serialize(obj)
        logger.debug(f"Serialized with None: {serialized}")
        deserialized = json_deserialize(serialized)
        self.assertIsNone(deserialized['key1'])
        self.assertEqual(deserialized['key2'], 'value2')
    
    def test_file_serialization(self):
        """Test serialization to and from files."""
        obj = {
            'array': np.array([1, 2, 3]),
            'date': datetime.now(),
            'custom': CustomObject("file_test", 42)
        }
        
        # Create temp file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Test serialization to file
            json_serialize_to_file(obj, temp_path)
            
            # Test deserialization from file
            deserialized = json_deserialize_from_file(temp_path)
            
            self.assertEqual(deserialized['array'], [1, 2, 3])
            self.assertEqual(deserialized['custom']['name'], "file_test")
            self.assertEqual(deserialized['custom']['value'], 42)
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_safe_serialization(self):
        """Test safe serialization with fallback values."""
        # Alternative approach: Create a circular reference (unserializable)
        a = {}
        b = {}
        a['b'] = b
        b['a'] = a  # This creates a circular reference that can't be JSON serialized
        
        # Create a fallback value
        fallback = '"fallback"'
        
        # Test with default value - check that it returns the fallback exactly
        result = safe_json_serialize(a, default=fallback)
        logger.debug(f"Safe serialize result with default: '{result}' (type: {type(result)})")
        logger.debug(f"Fallback value: '{fallback}' (type: {type(fallback)})")
        
        # Test that it returned the fallback
        self.assertEqual(result, fallback)
        
        # Test without default value
        result = safe_json_serialize(a)
        logger.debug(f"Safe serialize result without default: '{result}'")
        deserialized = json_deserialize(result)
        # Verify it contains an error message
        self.assertIn('error', deserialized)
    
    def test_list_with_mixed_types(self):
        """Test serialization of lists with mixed types."""
        mixed_list = [
            1,
            "string",
            np.int32(2),
            np.float32(3.14),
            datetime.now(),
            CustomObject("in_list", 42),
            None
        ]
        
        serialized = json_serialize(mixed_list)
        logger.debug(f"Serialized mixed list: {serialized}")
        deserialized = json_deserialize(serialized)
        
        self.assertEqual(len(deserialized), 7)
        self.assertEqual(deserialized[0], 1)
        self.assertEqual(deserialized[1], "string")
        self.assertEqual(deserialized[2], 2)
        self.assertAlmostEqual(deserialized[3], 3.14, places=2)
        self.assertIsInstance(deserialized[4], str)  # datetime becomes string
        self.assertEqual(deserialized[5]["name"], "in_list")
        self.assertIsNone(deserialized[6])
    
    def test_dict_with_nonstring_keys(self):
        """Test serialization of dictionaries with non-string keys."""
        # In standard JSON, keys must be strings, but our encoder should convert appropriately
        weird_dict = {
            1: "value1",
            datetime(2023, 1, 1): "value2",
            (1, 2): "value3"  # Tuple as key
        }
        
        # This should raise a TypeError because JSON requires string keys
        with self.assertRaises(TypeError):
            json_serialize(weird_dict)
        
        # But we can convert to a more friendly format first
        friendly_dict = {str(k): v for k, v in weird_dict.items()}
        serialized = json_serialize(friendly_dict)
        logger.debug(f"Serialized dict with non-string keys (converted): {serialized}")
        deserialized = json_deserialize(serialized)
        
        self.assertEqual(deserialized["1"], "value1")
        self.assertEqual(deserialized["2023-01-01 00:00:00"], "value2")
        self.assertEqual(deserialized["(1, 2)"], "value3")


if __name__ == '__main__':
    unittest.main() 