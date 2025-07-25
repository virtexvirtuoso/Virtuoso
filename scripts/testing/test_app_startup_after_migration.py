#!/usr/bin/env python3
"""
Test application startup after migration to ensure no runtime errors.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_app_startup():
    """Test basic application startup components."""
    print("=== Testing Application Startup ===\n")
    
    errors = []
    
    # Test 1: Import main components
    print("1. Testing main component imports...")
    try:
        from src.core.di.container import ServiceContainer
        from src.core.config.config_manager import ConfigManager
        from src.core.validation.service import AsyncValidationService
        from src.core.market.market_data_manager import MarketDataManager
        from src.indicators.technical_indicators import TechnicalIndicators
        from src.monitoring.monitor import MarketMonitor
        from src.signal_generation.signal_generator import SignalGenerator
        
        print("✓ All main components imported successfully")
    except Exception as e:
        print(f"✗ Import error: {e}")
        errors.append(f"Import error: {e}")
        return errors
    
    # Test 2: Initialize DI Container
    print("\n2. Testing DI Container initialization...")
    try:
        container = ServiceContainer()
        await container.initialize()
        print("✓ DI Container initialized successfully")
    except Exception as e:
        print(f"✗ DI Container error: {e}")
        errors.append(f"DI Container error: {e}")
    
    # Test 3: Load configuration
    print("\n3. Testing configuration loading...")
    try:
        config_manager = ConfigManager(
            config_path=str(project_root / 'config' / 'config.yaml')
        )
        config = config_manager.config
        print(f"✓ Configuration loaded successfully")
        print(f"  - Exchange: {config.get('exchange', {}).get('name', 'Unknown')}")
        print(f"  - Symbols: {len(config.get('symbols', []))} configured")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        errors.append(f"Configuration error: {e}")
    
    # Test 4: Test indicator initialization
    print("\n4. Testing indicator initialization...")
    try:
        indicators = TechnicalIndicators(config)
        print("✓ Technical indicators initialized successfully")
    except Exception as e:
        print(f"✗ Indicator error: {e}")
        errors.append(f"Indicator error: {e}")
    
    # Test 5: Test validation service
    print("\n5. Testing validation service...")
    try:
        validation_service = AsyncValidationService()
        print("✓ Validation service initialized successfully")
    except Exception as e:
        print(f"✗ Validation service error: {e}")
        errors.append(f"Validation service error: {e}")
    
    return errors

async def main():
    """Run startup tests."""
    try:
        errors = await test_app_startup()
        
        print("\n" + "="*50)
        print("=== STARTUP TEST SUMMARY ===")
        print("="*50 + "\n")
        
        if not errors:
            print("✅ All startup tests passed!")
            print("The application can start successfully with the migrated modules.")
            return 0
        else:
            print(f"❌ {len(errors)} errors found during startup:")
            for error in errors:
                print(f"  - {error}")
            return 1
            
    except Exception as e:
        print(f"\n❌ Startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))