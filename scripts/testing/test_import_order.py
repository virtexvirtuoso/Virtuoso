#!/usr/bin/env python3
"""
Test different import orders to identify circular import.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
sys.path.insert(0, str(project_root))

def test_import_scenarios():
    """Test different import scenarios."""
    
    print("=== Testing Import Scenarios ===\n")
    
    # Scenario 1: Direct import
    print("1. Direct import of TechnicalIndicators...")
    try:
        from src.indicators.technical_indicators import TechnicalIndicators
        print("✓ Success")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Clear modules to test fresh
    if 'src.indicators.technical_indicators' in sys.modules:
        del sys.modules['src.indicators.technical_indicators']
    
    # Scenario 2: Import after DI container
    print("\n2. Import after DI container...")
    try:
        from src.core.di.container import ServiceContainer
        from src.indicators.technical_indicators import TechnicalIndicators
        print("✓ Success")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Clear modules
    modules_to_clear = [m for m in sys.modules if m.startswith('src.')]
    for m in modules_to_clear:
        del sys.modules[m]
    
    # Scenario 3: Import with all main components
    print("\n3. Import with main components...")
    try:
        from src.core.di.container import ServiceContainer
        from src.core.config.config_manager import ConfigManager
        from src.core.validation.service import AsyncValidationService
        from src.indicators.technical_indicators import TechnicalIndicators
        print("✓ Success")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_import_scenarios()