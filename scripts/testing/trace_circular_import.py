#!/usr/bin/env python3
"""
Trace circular import issue in technical_indicators.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
sys.path.insert(0, str(project_root))

# Enable import debugging
import importlib.util
import importlib

def trace_imports():
    """Trace the import chain to find circular dependency."""
    print("=== Tracing Import Chain ===\n")
    
    # List of modules to trace
    modules_to_check = [
        "src.indicators.technical_indicators",
        "src.core.error.utils",
        "src.core.error.unified_exceptions",
        "src.validation.data.analysis_validator",
        "src.indicators.base_indicator",
    ]
    
    for module_name in modules_to_check:
        print(f"\nChecking {module_name}...")
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            print(f"✓ Successfully imported {module_name}")
            
            # Check what it imports
            if hasattr(module, '__file__'):
                print(f"  Location: {module.__file__}")
                
        except ImportError as e:
            print(f"✗ Import error: {e}")
        except Exception as e:
            print(f"✗ Other error: {e}")
    
    # Now try the specific problematic import
    print("\n\n=== Testing Specific Problem ===")
    try:
        print("Attempting: from src.indicators.technical_indicators import TechnicalIndicators")
        from src.indicators.technical_indicators import TechnicalIndicators
        print("✓ Import successful!")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        
        # Try to understand the circular dependency
        print("\nAttempting step-by-step imports to find the cycle...")
        
        # Step 1
        try:
            print("\n1. Import src.indicators")
            import src.indicators
            print("✓ Success")
        except Exception as e:
            print(f"✗ Failed: {e}")
            
        # Step 2
        try:
            print("\n2. Import src.indicators.technical_indicators module")
            import src.indicators.technical_indicators
            print("✓ Success")
        except Exception as e:
            print(f"✗ Failed: {e}")
            
        # Step 3
        try:
            print("\n3. Access TechnicalIndicators class")
            from src.indicators.technical_indicators import TechnicalIndicators
            print("✓ Success")
        except Exception as e:
            print(f"✗ Failed: {e}")

if __name__ == "__main__":
    trace_imports()