"""
Comprehensive test suite for circular reference detection in PDF generator and JSON encoder.

This test suite validates that circular references are properly detected and handled
in both the PDF generator's _prepare_for_json method and the CustomJSONEncoder's
_preprocess_for_circular_refs method.
"""

import pytest
import json
import time
import sys
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
import numpy as np

# Import the modules to test
from src.core.reporting.pdf_generator import ReportGenerator
from src.utils.json_encoder import CustomJSONEncoder


class TestCircularReferenceDetection:
    """Test suite for circular reference detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pdf_generator = ReportGenerator()
        self.json_encoder = CustomJSONEncoder()
    
    def test_simple_circular_reference_dict(self):
        """Test simple circular reference: A -> B -> A."""
        # Create circular reference
        dict_a = {"name": "A", "value": 1}
        dict_b = {"name": "B", "value": 2}
        dict_a["ref"] = dict_b
        dict_b["ref"] = dict_a
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(dict_a)
        assert isinstance(result_pdf, dict)
        assert "name" in result_pdf
        assert "ref" in result_pdf
        # Check that circular reference is detected
        assert "<circular_reference:" in str(result_pdf["ref"]["ref"])
        
        # Test JSON encoder
        result_json = json.dumps(dict_a, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_self_referencing_object(self):
        """Test self-referencing object: A -> A."""
        # Create self-referencing dictionary
        self_ref = {"name": "self", "value": 42}
        self_ref["self"] = self_ref
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(self_ref)
        assert isinstance(result_pdf, dict)
        assert "name" in result_pdf
        assert "<circular_reference:" in str(result_pdf["self"])
        
        # Test JSON encoder
        result_json = json.dumps(self_ref, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_complex_circular_reference_chain(self):
        """Test complex circular reference: A -> B -> C -> A."""
        # Create complex circular reference chain
        dict_a = {"name": "A", "value": 1}
        dict_b = {"name": "B", "value": 2}
        dict_c = {"name": "C", "value": 3}
        
        dict_a["next"] = dict_b
        dict_b["next"] = dict_c
        dict_c["next"] = dict_a
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(dict_a)
        assert isinstance(result_pdf, dict)
        assert "name" in result_pdf
        assert "next" in result_pdf
        # Navigate the chain and check for circular reference detection
        assert "next" in result_pdf["next"]
        assert "next" in result_pdf["next"]["next"]
        assert "<circular_reference:" in str(result_pdf["next"]["next"]["next"])
        
        # Test JSON encoder
        result_json = json.dumps(dict_a, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_circular_reference_in_list(self):
        """Test circular reference involving lists."""
        # Create circular reference with lists
        list_a = [1, 2, 3]
        dict_a = {"name": "A", "list": list_a}
        list_a.append(dict_a)
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(dict_a)
        assert isinstance(result_pdf, dict)
        assert "list" in result_pdf
        assert isinstance(result_pdf["list"], list)
        assert len(result_pdf["list"]) == 4
        assert "<circular_reference:" in str(result_pdf["list"][3])
        
        # Test JSON encoder
        result_json = json.dumps(dict_a, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_multiple_circular_references(self):
        """Test multiple circular references in the same object graph."""
        # Create multiple circular references
        root = {"name": "root"}
        branch1 = {"name": "branch1"}
        branch2 = {"name": "branch2"}
        leaf1 = {"name": "leaf1"}
        leaf2 = {"name": "leaf2"}
        
        # Create circular references
        root["branch1"] = branch1
        root["branch2"] = branch2
        branch1["leaf1"] = leaf1
        branch2["leaf2"] = leaf2
        
        # Create circles
        leaf1["back_to_root"] = root
        leaf2["back_to_branch1"] = branch1
        branch1["back_to_root"] = root
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(root)
        assert isinstance(result_pdf, dict)
        # Should contain circular reference markers
        result_str = str(result_pdf)
        assert result_str.count("<circular_reference:") >= 2
        
        # Test JSON encoder
        result_json = json.dumps(root, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert result_json.count("circular_reference") >= 2
    
    def test_deep_nesting_with_circular_reference(self):
        """Test deep nesting with circular reference at the end."""
        # Create deeply nested structure
        current = {"level": 0}
        root = current
        
        # Create 10 levels of nesting
        for i in range(1, 11):
            next_level = {"level": i}
            current["next"] = next_level
            current = next_level
        
        # Create circular reference at the deepest level
        current["back_to_root"] = root
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(root)
        assert isinstance(result_pdf, dict)
        
        # Navigate to deep level and check for circular reference
        current_result = result_pdf
        for i in range(10):
            assert "next" in current_result
            current_result = current_result["next"]
        
        assert "<circular_reference:" in str(current_result["back_to_root"])
        
        # Test JSON encoder
        result_json = json.dumps(root, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_circular_reference_with_custom_objects(self):
        """Test circular reference with custom objects having __dict__."""
        class CustomObject:
            def __init__(self, name):
                self.name = name
                self.ref = None
        
        # Create circular reference with custom objects
        obj1 = CustomObject("obj1")
        obj2 = CustomObject("obj2")
        obj1.ref = obj2
        obj2.ref = obj1
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(obj1)
        assert isinstance(result_pdf, dict)
        assert "name" in result_pdf
        assert "ref" in result_pdf
        assert "<circular_reference:" in str(result_pdf["ref"]["ref"])
        
        # Test JSON encoder
        result_json = json.dumps(obj1, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_circular_reference_with_pandas_objects(self):
        """Test circular reference involving pandas objects."""
        # Create DataFrame
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        
        # Create circular reference
        data = {"dataframe": df}
        data["self_ref"] = data
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(data)
        assert isinstance(result_pdf, dict)
        assert "dataframe" in result_pdf
        assert "<circular_reference:" in str(result_pdf["self_ref"])
        
        # Test JSON encoder
        result_json = json.dumps(data, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_circular_reference_with_numpy_objects(self):
        """Test circular reference involving numpy objects."""
        # Create numpy array
        arr = np.array([1, 2, 3, 4, 5])
        
        # Create circular reference
        data = {"array": arr}
        data["self_ref"] = data
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(data)
        assert isinstance(result_pdf, dict)
        assert "array" in result_pdf
        assert isinstance(result_pdf["array"], list)
        assert "<circular_reference:" in str(result_pdf["self_ref"])
        
        # Test JSON encoder
        result_json = json.dumps(data, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_mixed_data_structures_with_circular_reference(self):
        """Test circular reference with mixed data structures."""
        # Create complex mixed structure
        root = {
            "name": "root",
            "list": [1, 2, 3],
            "nested": {
                "level1": {
                    "level2": {
                        "data": "deep_data"
                    }
                }
            }
        }
        
        # Add circular references at different levels
        root["list"].append(root)
        root["nested"]["level1"]["level2"]["back_to_root"] = root
        root["nested"]["back_to_nested"] = root["nested"]
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(root)
        assert isinstance(result_pdf, dict)
        result_str = str(result_pdf)
        assert result_str.count("<circular_reference:") >= 2
        
        # Test JSON encoder
        result_json = json.dumps(root, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert result_json.count("circular_reference") >= 2
    
    def test_empty_containers_with_circular_reference(self):
        """Test circular reference with empty containers."""
        # Create empty containers with circular references
        empty_dict = {}
        empty_list = []
        
        empty_dict["list"] = empty_list
        empty_list.append(empty_dict)
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(empty_dict)
        assert isinstance(result_pdf, dict)
        assert "list" in result_pdf
        assert isinstance(result_pdf["list"], list)
        assert len(result_pdf["list"]) == 1
        assert "<circular_reference:" in str(result_pdf["list"][0])
        
        # Test JSON encoder
        result_json = json.dumps(empty_dict, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
    
    def test_performance_with_large_circular_structure(self):
        """Test performance with large circular structure."""
        # Create large structure with circular reference
        large_dict = {}
        for i in range(1000):
            large_dict[f"key_{i}"] = f"value_{i}"
        
        # Add circular reference
        large_dict["self"] = large_dict
        
        # Test PDF generator performance
        start_time = time.time()
        result_pdf = self.pdf_generator._prepare_for_json(large_dict)
        pdf_time = time.time() - start_time
        
        assert isinstance(result_pdf, dict)
        assert len(result_pdf) == 1001  # 1000 + 1 for self reference
        assert "<circular_reference:" in str(result_pdf["self"])
        assert pdf_time < 5.0  # Should complete within 5 seconds
        
        # Test JSON encoder performance
        start_time = time.time()
        result_json = json.dumps(large_dict, cls=CustomJSONEncoder)
        json_time = time.time() - start_time
        
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json
        assert json_time < 5.0  # Should complete within 5 seconds
    
    def test_real_world_trading_data_structure(self):
        """Test with real-world trading data structure that might have circular references."""
        # Simulate a trading signal data structure
        signal_data = {
            "symbol": "BTCUSDT",
            "timestamp": datetime.now(),
            "price": 50000.0,
            "score": 75.5,
            "components": {
                "technical": {"rsi": 65.0, "macd": 0.5},
                "volume": {"obv": 1000000, "vwap": 49500.0},
                "sentiment": {"funding_rate": 0.01, "long_short_ratio": 0.6}
            },
            "market_data": {
                "ohlcv": pd.DataFrame({
                    "open": [49000, 49500, 50000],
                    "high": [49500, 50000, 50500],
                    "low": [48500, 49000, 49500],
                    "close": [49500, 50000, 50500],
                    "volume": [1000, 1500, 2000]
                }),
                "orderbook": {
                    "bids": [[49900, 100], [49800, 200]],
                    "asks": [[50100, 150], [50200, 250]]
                }
            }
        }
        
        # Add circular reference
        signal_data["parent"] = signal_data
        signal_data["components"]["parent_signal"] = signal_data
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(signal_data)
        assert isinstance(result_pdf, dict)
        assert "symbol" in result_pdf
        assert "components" in result_pdf
        assert "market_data" in result_pdf
        assert "<circular_reference:" in str(result_pdf["parent"])
        assert "<circular_reference:" in str(result_pdf["components"]["parent_signal"])
        
        # Test JSON encoder
        result_json = json.dumps(signal_data, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "BTCUSDT" in result_json
        assert "circular_reference" in result_json
    
    def test_no_false_positives(self):
        """Test that non-circular structures are not flagged as circular."""
        # Create non-circular structure with similar objects
        dict1 = {"name": "dict1", "value": 1}
        dict2 = {"name": "dict2", "value": 2}
        dict3 = {"name": "dict3", "value": 3}
        
        # Create structure without circular references
        root = {
            "branch1": dict1,
            "branch2": dict2,
            "nested": {
                "dict1_copy": dict1,  # Same object, but not circular
                "dict3": dict3
            }
        }
        
        # Test PDF generator
        result_pdf = self.pdf_generator._prepare_for_json(root)
        assert isinstance(result_pdf, dict)
        # Should not contain circular reference markers
        result_str = str(result_pdf)
        assert "<circular_reference:" not in result_str
        
        # Test JSON encoder
        result_json = json.dumps(root, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" not in result_json
    
    def test_memory_usage_with_circular_references(self):
        """Test that circular reference detection doesn't cause memory leaks."""
        import gc
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create and process multiple circular structures
        for i in range(100):
            circular_dict = {"id": i}
            circular_dict["self"] = circular_dict
            
            # Process with both methods
            self.pdf_generator._prepare_for_json(circular_dict)
            json.dumps(circular_dict, cls=CustomJSONEncoder)
            
            # Clear reference
            del circular_dict
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not have grown significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Memory leak detected: {object_growth} new objects"
    
    def test_error_handling_in_circular_detection(self):
        """Test error handling in circular reference detection."""
        class ProblematicObject:
            def __init__(self):
                self.name = "problematic"
            
            def __getattribute__(self, name):
                if name == "problematic_attr":
                    raise ValueError("Problematic attribute access")
                return super().__getattribute__(name)
        
        # Create circular reference with problematic object
        obj = ProblematicObject()
        data = {"obj": obj}
        data["self"] = data
        
        # Test PDF generator handles errors gracefully
        result_pdf = self.pdf_generator._prepare_for_json(data)
        assert isinstance(result_pdf, dict)
        assert "<circular_reference:" in str(result_pdf["self"])
        
        # Test JSON encoder handles errors gracefully
        result_json = json.dumps(data, cls=CustomJSONEncoder)
        assert isinstance(result_json, str)
        assert "circular_reference" in result_json


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 