#!/usr/bin/env python3
"""
Comprehensive Dashboard Fix Testing
Tests all dashboard endpoints to verify field mapping fixes
"""

import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class DashboardTester:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.results = {}
        self.issues = []
        
    def test_endpoint(self, endpoint: str, name: str) -> Tuple[bool, Dict]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        print(f"\n🔍 Testing {name}: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            print(f"  ✅ Response received (status: {response.status_code})")
            return True, data
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
            self.issues.append(f"{name}: Request failed - {e}")
            return False, {}
        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON: {e}")
            self.issues.append(f"{name}: Invalid JSON response")
            return False, {}
    
    def validate_dashboard_data(self, data: Dict) -> bool:
        """Validate dashboard data endpoint"""
        print("\n  📊 Validating Dashboard Data:")
        valid = True
        
        # Check summary
        if 'summary' in data:
            summary = data['summary']
            volume = summary.get('total_volume_24h', 0)
            symbols = summary.get('total_symbols', 0)
            
            print(f"    • Total Volume: {volume:,.2f} {'✅' if volume > 0 else '❌'}")
            print(f"    • Total Symbols: {symbols} {'✅' if symbols > 0 else '❌'}")
            
            if volume == 0:
                self.issues.append("Dashboard: total_volume_24h is 0")
                valid = False
            if symbols == 0:
                self.issues.append("Dashboard: total_symbols is 0")
                valid = False
        else:
            print("    ❌ Missing 'summary' field")
            self.issues.append("Dashboard: Missing summary field")
            valid = False
        
        # Check signals
        if 'signals' in data and len(data['signals']) > 0:
            signal = data['signals'][0]
            price = signal.get('price', 0)
            volume = signal.get('volume', 0)
            
            print(f"    • First Signal Price: {price:,.2f} {'✅' if price > 0 else '❌'}")
            print(f"    • First Signal Volume: {volume:,.2f} {'✅' if volume > 0 else '❌'}")
            
            if price == 0:
                self.issues.append("Dashboard: Signal price is 0")
                valid = False
            if volume == 0:
                self.issues.append("Dashboard: Signal volume is 0")
                valid = False
        else:
            print("    ⚠️  No signals available")
        
        return valid
    
    def validate_mobile_data(self, data: Dict) -> bool:
        """Validate mobile dashboard data"""
        print("\n  📱 Validating Mobile Data:")
        valid = True
        
        # Check confluence scores
        if 'confluence_scores' in data and len(data['confluence_scores']) > 0:
            score = data['confluence_scores'][0]
            price = score.get('price', 0)
            
            print(f"    • First Score Price: {price:,.2f} {'✅' if price > 0 else '❌'}")
            
            if price == 0:
                self.issues.append("Mobile: Confluence score price is 0")
                valid = False
        else:
            print("    ⚠️  No confluence scores available")
        
        # Check market overview
        if 'market_overview' in data:
            overview = data['market_overview']
            volume = overview.get('total_volume_24h', 0)
            
            print(f"    • Market Volume: {volume:,.2f} {'✅' if volume > 0 else '❌'}")
            
            if volume == 0:
                self.issues.append("Mobile: Market overview volume is 0")
                valid = False
        
        # Check market breadth
        if 'market_breadth' in data:
            breadth = data['market_breadth']
            up = breadth.get('up_count', 0)
            down = breadth.get('down_count', 0)
            total = up + down
            
            print(f"    • Market Breadth: {up} up, {down} down (total: {total}) {'✅' if total > 0 else '❌'}")
            
            if total == 0:
                self.issues.append("Mobile: Market breadth counts are 0")
                valid = False
        
        return valid
    
    def validate_market_overview(self, data: Dict) -> bool:
        """Validate market overview endpoint"""
        print("\n  📈 Validating Market Overview:")
        valid = True
        
        active = data.get('active_symbols', 0)
        volume = data.get('total_volume', 0)
        
        print(f"    • Active Symbols: {active} {'✅' if active > 0 else '❌'}")
        print(f"    • Total Volume: {volume:,.2f} {'✅' if volume > 0 else '❌'}")
        
        if active == 0:
            self.issues.append("Market Overview: active_symbols is 0")
            valid = False
        if volume == 0:
            self.issues.append("Market Overview: total_volume is 0")
            valid = False
        
        # Check market breadth
        if 'market_breadth' in data:
            breadth = data['market_breadth']
            up = breadth.get('up', 0)
            down = breadth.get('down', 0)
            total = up + down
            
            print(f"    • Breadth: {up} up, {down} down (total: {total}) {'✅' if total > 0 else '❌'}")
            
            if total == 0:
                self.issues.append("Market Overview: breadth counts are 0")
                valid = False
        
        return valid
    
    def run_all_tests(self) -> bool:
        """Run all dashboard tests"""
        print("=" * 60)
        print("🧪 COMPREHENSIVE DASHBOARD TESTING")
        print(f"📍 Target: {self.base_url}")
        print("=" * 60)
        
        all_valid = True
        
        # Test health endpoint
        success, data = self.test_endpoint("/health", "Health Check")
        if success:
            print(f"  ✅ Service is healthy")
        else:
            all_valid = False
        
        # Test dashboard data
        success, data = self.test_endpoint("/api/dashboard/data", "Dashboard Data")
        if success:
            if not self.validate_dashboard_data(data):
                all_valid = False
        else:
            all_valid = False
        
        # Test mobile data
        success, data = self.test_endpoint("/api/dashboard/mobile-data", "Mobile Data")
        if success:
            if not self.validate_mobile_data(data):
                all_valid = False
        else:
            all_valid = False
        
        # Test market overview
        success, data = self.test_endpoint("/api/dashboard/market-overview", "Market Overview")
        if success:
            if not self.validate_market_overview(data):
                all_valid = False
        else:
            all_valid = False
        
        # Print summary
        print("\n" + "=" * 60)
        if all_valid and len(self.issues) == 0:
            print("✅ ALL TESTS PASSED!")
            print("Dashboard is functioning correctly with proper field mappings.")
        else:
            print("⚠️  ISSUES FOUND:")
            for issue in self.issues:
                print(f"  • {issue}")
        print("=" * 60)
        
        return all_valid and len(self.issues) == 0

def main():
    parser = argparse.ArgumentParser(description='Test dashboard fixes')
    parser.add_argument('--vps', action='store_true', help='Test against VPS')
    parser.add_argument('--both', action='store_true', help='Test both local and VPS')
    args = parser.parse_args()
    
    if args.both:
        # Test local first
        print("\n🏠 TESTING LOCAL ENVIRONMENT")
        local_tester = DashboardTester("http://localhost:8003")
        local_result = local_tester.run_all_tests()
        
        print("\n" + "=" * 60)
        
        # Then test VPS
        print("\n☁️  TESTING VPS ENVIRONMENT")
        vps_tester = DashboardTester("http://VPS_HOST_REDACTED:8003")
        vps_result = vps_tester.run_all_tests()
        
        # Overall result
        print("\n" + "=" * 60)
        print("📊 OVERALL RESULTS:")
        print(f"  • Local: {'✅ PASS' if local_result else '❌ FAIL'}")
        print(f"  • VPS: {'✅ PASS' if vps_result else '❌ FAIL'}")
        print("=" * 60)
        
        return 0 if (local_result and vps_result) else 1
    
    elif args.vps:
        tester = DashboardTester("http://VPS_HOST_REDACTED:8003")
    else:
        tester = DashboardTester("http://localhost:8003")
    
    result = tester.run_all_tests()
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())