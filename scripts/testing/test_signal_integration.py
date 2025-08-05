#!/usr/bin/env python3
"""
Test Script for Signal Tracking Integration

This script tests the integration between monitor.py and the signal tracking system.
Run this after implementing the integration to verify everything works correctly.
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    'api_base_url': 'http://localhost:8001/api/signal-tracking',
    'websocket_url': 'ws://localhost:8001/ws',
    'test_symbol': 'BTC/USDT'
}

class SignalTrackingTester:
    """Test the signal tracking integration."""
    
    def __init__(self):
        self.api_url = TEST_CONFIG['api_base_url']
        
    def test_api_endpoints(self):
        """Test all signal tracking API endpoints."""
        print("🧪 Testing Signal Tracking API Endpoints...")
        
        # Test 1: Health check (GET /api/signals/active)
        try:
            response = requests.get(f"{self.api_url}/active", timeout=5)
            if response.status_code == 200:
                print("✅ GET /api/signals/active - OK")
            else:
                print(f"❌ GET /api/signals/active - Failed ({response.status_code})")
        except Exception as e:
            print(f"❌ GET /api/signals/active - Error: {e}")
        
        # Test 2: Add a test signal (POST /api/signals/track)
        test_signal = {
            'symbol': TEST_CONFIG['test_symbol'],
            'action': 'buy',
            'entry_price': 45000.0,
            'confidence': 75.5,
            'confluence_score': 75.5,
            'quantity': 1.0,
            'source': 'test_integration',
            'metadata': {
                'test': True,
                'timestamp': int(time.time() * 1000)
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/track",
                json=test_signal,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    signal_id = result.get('tracking_id')
                    print(f"✅ POST /api/signals/track - OK (ID: {signal_id})")
                    return signal_id
                else:
                    print(f"❌ POST /api/signals/track - Failed: {result.get('message')}")
            else:
                print(f"❌ POST /api/signals/track - Failed ({response.status_code})")
        except Exception as e:
            print(f"❌ POST /api/signals/track - Error: {e}")
        
        return None
    
    def test_signal_lifecycle(self, signal_id: str):
        """Test the complete signal lifecycle."""
        if not signal_id:
            print("❌ Skipping lifecycle test - no signal ID")
            return
            
        print(f"🔄 Testing Signal Lifecycle for ID: {signal_id}")
        
        # Test 3: Fetch active signals
        try:
            response = requests.get(f"{self.api_url}/active", timeout=5)
            if response.status_code == 200:
                signals = response.json().get('signals', [])
                found = any(s.get('id') == signal_id for s in signals)
                if found:
                    print("✅ Signal found in active list")
                else:
                    print("❌ Signal not found in active list")
            else:
                print(f"❌ Failed to fetch active signals ({response.status_code})")
        except Exception as e:
            print(f"❌ Error fetching active signals: {e}")
        
        # Test 4: Stop tracking the signal
        try:
            response = requests.delete(f"{self.api_url}/tracked/{signal_id}", timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Signal stopped successfully")
                else:
                    print(f"❌ Failed to stop signal: {result.get('message')}")
            else:
                print(f"❌ Failed to stop signal ({response.status_code})")
        except Exception as e:
            print(f"❌ Error stopping signal: {e}")
    
    def test_integration_format(self):
        """Test the signal format expected by the integration."""
        print("📝 Testing Integration Signal Format...")
        
        # This is the format monitor.py should send
        monitor_signal_format = {
            'action': 'buy',
            'price': 45000.0,
            'confidence': 75.5,
            'confluence_score': 75.5,
            'quantity': 1.0,
            'source_data': {
                'components': {
                    'technical': {'score': 80, 'signals': ['bullish_divergence']},
                    'volume': {'score': 70, 'signals': ['volume_spike']},
                    'orderbook': {'score': 75, 'signals': ['bid_wall']}
                },
                'results': {
                    'technical': 0.8,
                    'volume': 0.7,
                    'orderbook': 0.75
                },
                'reliability': 0.85,
                'transaction_id': 'test_txn_123',
                'signal_id': 'test_sig_456'
            }
        }
        
        # Validate format
        required_fields = ['action', 'price', 'confidence', 'source_data']
        missing_fields = [field for field in required_fields if field not in monitor_signal_format]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
        else:
            print("✅ Signal format validation passed")
        
        # Test API with this format
        api_payload = {
            'symbol': TEST_CONFIG['test_symbol'],
            **monitor_signal_format,
            'source': 'confluence_analysis'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/track",
                json=api_payload,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Integration format test passed")
                    return result.get('tracking_id')
                else:
                    print(f"❌ Integration format test failed: {result.get('message')}")
            else:
                print(f"❌ Integration format test failed ({response.status_code})")
        except Exception as e:
            print(f"❌ Integration format test error: {e}")
        
        return None
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 Starting Signal Tracking Integration Tests...\n")
        
        # Test API endpoints
        signal_id = self.test_api_endpoints()
        print()
        
        # Test signal lifecycle
        if signal_id:
            self.test_signal_lifecycle(signal_id)
            print()
        
        # Test integration format
        integration_signal_id = self.test_integration_format()
        print()
        
        # Cleanup integration test signal
        if integration_signal_id:
            try:
                requests.delete(f"{self.api_url}/tracked/{integration_signal_id}", timeout=5)
                print("🧹 Cleaned up test signals")
            except:
                pass
        
        print("✅ All tests completed!")

def main():
    """Run the test suite."""
    tester = SignalTrackingTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main() 