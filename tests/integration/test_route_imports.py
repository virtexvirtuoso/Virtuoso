#!/usr/bin/env python3
"""
Simple Route Import Test
Tests that all route modules can be imported without errors.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_route_imports():
    """Test that all route modules can be imported."""
    print("🧪 Testing Route Module Imports...")
    
    # List of route modules that should be importable
    route_modules = [
        "src.api.routes.signals",
        "src.api.routes.market", 
        "src.api.routes.system",
        "src.api.routes.trading",
        "src.api.routes.dashboard",
        "src.api.routes.alpha",
        "src.api.routes.liquidation", 
        "src.api.routes.correlation",
        "src.api.routes.bitcoin_beta",
        "src.api.routes.manipulation",
        "src.api.routes.top_symbols",
        "src.api.routes.whale_activity",
        "src.api.routes.sentiment",
        "src.api.routes.admin",
        "src.api.routes.cache",
        "src.api.routes.debug_test",
        "src.api.routes.core_api",
        "src.api.routes.confluence_breakdown",
        "src.api.routes.admin_enhanced"
    ]
    
    # Optional modules that may not be available
    optional_modules = [
        "src.api.routes.cache_dashboard",
        "src.api.routes.market_analysis",
        "src.api.routes.mobile_unified",
        "src.api.routes.health",
    ]
    
    # Test required modules
    success_count = 0
    total_count = len(route_modules)
    
    for module_name in route_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - ImportError: {str(e)[:60]}...")
        except Exception as e:
            print(f"⚠️  {module_name} - Other error: {str(e)[:60]}...")
    
    print(f"\n📊 Required Modules: {success_count}/{total_count} imported successfully")
    
    # Test optional modules
    optional_success = 0
    for module_name in optional_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name} (optional)")
            optional_success += 1
        except ImportError:
            print(f"➖ {module_name} (optional) - not available")
        except Exception as e:
            print(f"⚠️  {module_name} (optional) - error: {str(e)[:60]}...")
    
    print(f"📊 Optional Modules: {optional_success}/{len(optional_modules)} available")
    
    return success_count == total_count

def test_route_file_structure():
    """Test that moved files are in the correct locations."""
    print("\n🗂️  Testing Route File Structure...")
    
    routes_dir = project_root / "src" / "api" / "routes"
    legacy_dir = routes_dir / "_legacy"
    
    # Check that active route files exist
    active_files = [
        "signals.py", "market.py", "system.py", "trading.py", "dashboard.py",
        "alpha.py", "liquidation.py", "correlation.py", "bitcoin_beta.py", 
        "manipulation.py", "top_symbols.py", "whale_activity.py", "sentiment.py",
        "admin.py", "cache.py", "debug_test.py", "core_api.py",
        "confluence_breakdown.py", "admin_enhanced.py"
    ]
    
    active_count = 0
    for filename in active_files:
        file_path = routes_dir / filename
        if file_path.exists():
            print(f"✅ {filename}")
            active_count += 1
        else:
            print(f"❌ {filename} - missing!")
    
    print(f"📊 Active Route Files: {active_count}/{len(active_files)} found")
    
    # Check that legacy files have been moved
    if legacy_dir.exists():
        legacy_files = list(legacy_dir.glob("*.py"))
        print(f"📦 Legacy Files Moved: {len(legacy_files)} files in _legacy/")
        for file_path in legacy_files[:5]:  # Show first 5
            print(f"   📁 {file_path.name}")
        if len(legacy_files) > 5:
            print(f"   ... and {len(legacy_files) - 5} more files")
    else:
        print("📦 No legacy directory found")
    
    return active_count == len(active_files)

def check_archived_files():
    """Check that problematic files have been archived."""
    print("\n🗃️  Checking Archived Files...")
    
    routes_dir = project_root / "src" / "api" / "routes"
    
    # Files that should be archived/moved
    problematic_files = [
        "_archived_confluence_optimized.py",
        "_archived_test_api_endpoints.py", 
        "_archived_test_api_endpoints_simple.py",
        "_archived_test_api_endpoints_summary.py"
    ]
    
    archived_count = 0
    for filename in problematic_files:
        file_path = routes_dir / filename
        if file_path.exists():
            print(f"✅ {filename} - archived")
            archived_count += 1
        else:
            print(f"❓ {filename} - not found (may have been removed)")
    
    print(f"📊 Archived Files: {archived_count}/{len(problematic_files)} processed")
    return True

def main():
    """Main test function."""
    print("🚀 Route Import Structure Test")
    print("=" * 50)
    
    # Test imports
    import_success = test_route_imports()
    
    # Test file structure  
    structure_success = test_route_file_structure()
    
    # Check archived files
    archived_success = check_archived_files()
    
    # Final result
    print("\n" + "=" * 50)
    if import_success and structure_success:
        print("✅ ROUTE CLEANUP SUCCESSFUL!")
        print("🎉 All route modules are properly organized and importable")
        return True
    else:
        print("❌ ROUTE CLEANUP INCOMPLETE")
        print("⚠️  Some issues remain with route organization")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)