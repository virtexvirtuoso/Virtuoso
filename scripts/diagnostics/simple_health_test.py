#!/usr/bin/env python3
"""
Simple health check script to test basic connectivity and configuration
"""

import os
import json
import requests
import time

def test_api_credentials():
    """Test if API credentials are configured"""
    print("=== Testing API Credentials ===")
    
    bybit_key = os.getenv('BYBIT_API_KEY')
    bybit_secret = os.getenv('BYBIT_API_SECRET')
    
    print(f"BYBIT_API_KEY found: {bool(bybit_key)}")
    print(f"BYBIT_API_SECRET found: {bool(bybit_secret)}")
    
    if bybit_key:
        print(f"API key length: {len(bybit_key)}")
        print(f"API key starts with: {bybit_key[:10]}...")
    else:
        print("❌ BYBIT_API_KEY not found in environment")
    
    if bybit_secret:
        print(f"API secret length: {len(bybit_secret)}")
        print(f"API secret starts with: {bybit_secret[:10]}...")
    else:
        print("❌ BYBIT_API_SECRET not found in environment")
    
    return bool(bybit_key and bybit_secret)

def test_bybit_api():
    """Test Bybit API connectivity"""
    print("\n=== Testing Bybit API Connectivity ===")
    
    try:
        # Test public endpoint
        response = requests.get("https://api.bybit.com/v5/market/time", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Bybit public API accessible")
            print(f"Server time: {data.get('result', {}).get('timeSecond', 'unknown')}")
        else:
            print(f"❌ Bybit API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Bybit API connection failed: {str(e)}")
        return False
    
    return True

def test_authenticated_bybit_api():
    """Test authenticated Bybit API call"""
    print("\n=== Testing Authenticated Bybit API ===")
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API credentials not available")
        return False
    
    try:
        import hmac
        import hashlib
        
        # Create signature for account info endpoint
        timestamp = str(int(time.time() * 1000))
        params = f"timestamp={timestamp}"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': '5000'
        }
        
        url = f"https://api.bybit.com/v5/account/wallet-balance?{params}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                print("✅ Authenticated API call successful")
                return True
            else:
                print(f"❌ API returned error: {data.get('retMsg', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Authenticated API test failed: {str(e)}")
        return False

def test_influxdb():
    """Test InfluxDB connectivity"""
    print("\n=== Testing InfluxDB Connectivity ===")
    
    influx_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influx_token = os.getenv('INFLUXDB_TOKEN')
    
    print(f"InfluxDB URL: {influx_url}")
    print(f"InfluxDB token configured: {bool(influx_token)}")
    
    try:
        # Test health endpoint
        response = requests.get(f"{influx_url}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ InfluxDB is accessible")
            print(f"Status: {data.get('status', 'unknown')}")
            print(f"Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ InfluxDB health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ InfluxDB connection failed: {str(e)}")
        return False

def test_config_file():
    """Test if config file exists and is readable"""
    print("\n=== Testing Configuration File ===")
    
    config_path = "config/config.yaml"
    
    try:
        if os.path.exists(config_path):
            print(f"✅ Config file found: {config_path}")
            
            with open(config_path, 'r') as f:
                content = f.read()
                print(f"Config file size: {len(content)} bytes")
                
                # Check for key sections
                if 'exchanges:' in content:
                    print("✅ Exchanges section found")
                if 'bybit:' in content:
                    print("✅ Bybit configuration found")
                if 'database:' in content:
                    print("✅ Database configuration found")
                    
            return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
            
    except Exception as e:
        print(f"❌ Config file test failed: {str(e)}")
        return False

def main():
    """Run all health checks"""
    print("🔍 Starting Simple Health Check Diagnostics\n")
    
    tests = [
        ("API Credentials", test_api_credentials),
        ("Bybit Public API", test_bybit_api),
        ("Bybit Authenticated API", test_authenticated_bybit_api),
        ("InfluxDB", test_influxdb),
        ("Configuration File", test_config_file)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
    
    print("\n" + "="*50)
    print("📊 HEALTH CHECK SUMMARY")
    print("="*50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    failed_tests = [name for name, result in results.items() if not result]
    
    if failed_tests:
        print(f"\n🚨 Failed tests: {', '.join(failed_tests)}")
        print("\n💡 Recommendations:")
        
        if "API Credentials" in failed_tests:
            print("   - Check .env file for BYBIT_API_KEY and BYBIT_API_SECRET")
            print("   - Ensure environment variables are loaded")
        
        if "Bybit Authenticated API" in failed_tests:
            print("   - Verify API keys are valid and active")
            print("   - Check API key permissions on Bybit")
        
        if "InfluxDB" in failed_tests:
            print("   - Start InfluxDB service: brew services start influxdb")
            print("   - Check INFLUXDB_URL in .env file")
        
    else:
        print("\n🎉 All tests passed! System appears healthy.")

if __name__ == "__main__":
    main() 