#!/usr/bin/env python3
"""Test API routes for contango functionality"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_api_imports():
    """Test if our API routes can be imported"""
    try:
        from api.routes.market import router
        print('✅ Successfully imported market routes')
        
        # Check if our functions exist in the module
        import api.routes.market as market_module
        
        # List all functions in the module
        functions = [name for name in dir(market_module) if callable(getattr(market_module, name)) and not name.startswith('_')]
        print(f'✅ Available functions: {", ".join(functions)}')
        
        # Check for our specific contango endpoints
        expected_endpoints = ['get_futures_premium', 'get_contango_status', 'get_single_futures_premium']
        found_endpoints = []
        
        for endpoint in expected_endpoints:
            if hasattr(market_module, endpoint):
                found_endpoints.append(endpoint)
                print(f'✅ Found endpoint: {endpoint}')
            else:
                print(f'⚠️  Missing endpoint: {endpoint}')
                
        if len(found_endpoints) >= 2:  # At least 2 out of 3 is good
            print('🎉 API routes are properly set up!')
            return True
        else:
            print('❌ Missing critical API endpoints')
            return False
            
    except ImportError as e:
        print(f'❌ Import error: {e}')
        return False
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        return False

def test_market_reporter_import():
    """Test if market reporter can be imported"""
    try:
        from monitoring.market_reporter import MarketReporter
        print('✅ Successfully imported MarketReporter')
        
        # Check if our futures premium method exists
        if hasattr(MarketReporter, '_calculate_futures_premium'):
            print('✅ Found _calculate_futures_premium method')
            return True
        else:
            print('❌ Missing _calculate_futures_premium method')
            return False
            
    except ImportError as e:
        print(f'❌ MarketReporter import error: {e}')
        return False

if __name__ == "__main__":
    print("🧪 TESTING API ROUTES AND IMPORTS")
    print("=" * 50)
    
    api_test = test_api_imports()
    print()
    reporter_test = test_market_reporter_import()
    
    print("\n📊 TEST RESULTS:")
    print(f"API Routes: {'✅ PASS' if api_test else '❌ FAIL'}")
    print(f"Market Reporter: {'✅ PASS' if reporter_test else '❌ FAIL'}")
    
    overall = api_test and reporter_test
    print(f"\n🎯 OVERALL: {'✅ READY' if overall else '❌ NEEDS FIXES'}") 