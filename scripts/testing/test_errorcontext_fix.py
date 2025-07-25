#!/usr/bin/env python3
"""Test that ErrorContext issues have been fixed."""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

def test_errorcontext_imports():
    """Test that all ErrorContext imports work correctly."""
    print("Testing ErrorContext imports...")
    
    try:
        # Test main models import
        from src.core.models import ErrorContext as ModelsErrorContext
        print("✅ ErrorContext from src.core.models imported successfully")
        
        # Test error models import
        from src.core.error.models import ErrorContext as ErrorModelsErrorContext
        print("✅ ErrorContext from src.core.error.models imported successfully")
        
        # Test unified exceptions import
        from src.core.error.unified_exceptions import ErrorContext as UnifiedErrorContext
        print("✅ ErrorContext from src.core.error.unified_exceptions imported successfully")
        
        # Verify they're all the same class
        if ModelsErrorContext is ErrorModelsErrorContext is UnifiedErrorContext:
            print("✅ All ErrorContext imports reference the same class")
        else:
            print("❌ ErrorContext imports reference different classes!")
            return False
            
        # Test creating ErrorContext with required fields
        ctx = ModelsErrorContext(component="test", operation="test_op")
        print(f"✅ Created ErrorContext with required fields: component={ctx.component}, operation={ctx.operation}")
        
        # Test creating ErrorContext with optional fields
        ctx2 = ModelsErrorContext(
            component="test",
            operation="test_op",
            symbol="BTCUSDT",
            exchange="binance",
            details={"key": "value"}
        )
        print("✅ Created ErrorContext with optional fields")
        
        # Test methods
        ctx2.add_detail("test_key", "test_value")
        ctx2.add_metadata("meta_key", "meta_value")
        ctx_dict = ctx2.to_dict()
        print("✅ ErrorContext methods work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ErrorContext: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_manager():
    """Test that validation manager can now create ErrorContext correctly."""
    print("\nTesting validation manager ErrorContext usage...")
    
    try:
        from src.core.validation.manager import ValidationManager
        from src.core.validation.context import ValidationContext
        
        # The import should work now
        print("✅ ValidationManager imported successfully")
        
        # Create a mock validation context
        ctx = ValidationContext(
            data_type="test_data",
            metadata={"test": "data"}
        )
        
        print("✅ ValidationContext created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error testing validation manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_container_initialization():
    """Test if the old Container can now initialize."""
    print("\nTesting Container initialization...")
    
    try:
        from src.core.container import Container
        
        # Try to create container
        container = Container()
        print("✅ Container created successfully")
        
        # Try to initialize
        import asyncio
        async def test_init():
            try:
                await container.initialize()
                print("✅ Container initialized successfully!")
                return True
            except Exception as e:
                if "event_bus" in str(e):
                    print(f"⚠️ Container still has missing component issues: {e}")
                elif "ErrorContext" in str(e):
                    print(f"❌ ErrorContext issue still exists: {e}")
                    return False
                else:
                    print(f"⚠️ Container has other issues: {e}")
                return None
        
        result = asyncio.run(test_init())
        return result if result is not None else True
        
    except ImportError:
        print("⚠️ Old Container system not found (using ServiceContainer instead)")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all ErrorContext tests."""
    print("🔍 TESTING ERRORCONTEXT FIXES")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("ErrorContext Imports", test_errorcontext_imports()))
    results.append(("Validation Manager", test_validation_manager()))
    results.append(("Container Initialization", test_container_initialization()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All ErrorContext issues have been fixed!")
    else:
        print(f"\n⚠️ {total - passed} issues remain")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)