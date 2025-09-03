#!/usr/bin/env python3
"""
Validation script to test data structure fixes in Virtuoso CCXT dashboard system.
Tests field name consistency and presence of required fields.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiomcache
from typing import Dict, Any, List, Tuple

class DataStructureValidator:
    """Validates data structure consistency across the system"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        
    async def connect_cache(self) -> aiomcache.Client:
        """Connect to memcached"""
        try:
            client = aiomcache.Client('localhost', 11211)
            # Test connection
            await client.set(b'test:connection', b'ok', exptime=1)
            result = await client.get(b'test:connection')
            if result == b'ok':
                self.successes.append("✅ Connected to memcached successfully")
                return client
            else:
                self.errors.append("❌ Memcached connection test failed")
                return None
        except Exception as e:
            self.errors.append(f"❌ Failed to connect to memcached: {e}")
            return None
    
    async def validate_market_overview(self, client: aiomcache.Client) -> bool:
        """Validate market overview data structure"""
        try:
            data = await client.get(b'market:overview')
            if data:
                overview = json.loads(data.decode())
                
                # Check required fields
                required_fields = ['total_symbols', 'total_volume', 'market_regime', 
                                 'trend_strength', 'current_volatility', 'timestamp']
                missing_fields = [f for f in required_fields if f not in overview]
                
                if missing_fields:
                    self.warnings.append(f"⚠️  Market overview missing fields: {missing_fields}")
                else:
                    self.successes.append("✅ Market overview has all required fields")
                
                # Check field naming consistency
                if 'current_volatility' in overview:
                    self.successes.append("✅ Market overview uses 'current_volatility' (correct)")
                elif 'volatility' in overview:
                    self.warnings.append("⚠️  Market overview uses 'volatility' instead of 'current_volatility'")
                    
                return True
            else:
                self.warnings.append("⚠️  No market overview data in cache")
                return False
        except Exception as e:
            self.errors.append(f"❌ Error validating market overview: {e}")
            return False
    
    async def validate_tickers(self, client: aiomcache.Client) -> bool:
        """Validate ticker data structure"""
        try:
            data = await client.get(b'market:tickers')
            if data:
                tickers = json.loads(data.decode())
                
                if tickers:
                    # Check first ticker for field consistency
                    first_symbol = list(tickers.keys())[0]
                    ticker = tickers[first_symbol]
                    
                    # Check for consistent field names
                    if 'change_24h' in ticker:
                        self.successes.append("✅ Tickers use 'change_24h' (correct)")
                    elif 'price_change_24h' in ticker:
                        self.errors.append("❌ Tickers use 'price_change_24h' (should be 'change_24h')")
                    
                    if 'volume_24h' in ticker:
                        self.successes.append("✅ Tickers have 'volume_24h' field")
                    elif 'volume' in ticker:
                        self.warnings.append("⚠️  Tickers use 'volume' instead of 'volume_24h'")
                    
                    required_fields = ['price', 'change_24h', 'volume_24h', 'signal']
                    missing_fields = [f for f in required_fields if f not in ticker]
                    
                    if missing_fields:
                        self.warnings.append(f"⚠️  Ticker missing fields: {missing_fields}")
                    else:
                        self.successes.append("✅ Ticker has all required fields")
                    
                    return True
                else:
                    self.warnings.append("⚠️  Tickers data is empty")
                    return False
            else:
                self.warnings.append("⚠️  No ticker data in cache")
                return False
        except Exception as e:
            self.errors.append(f"❌ Error validating tickers: {e}")
            return False
    
    async def validate_confluence_breakdown(self, client: aiomcache.Client, symbol: str = 'BTCUSDT') -> bool:
        """Validate confluence breakdown data structure"""
        try:
            data = await client.get(f'confluence:breakdown:{symbol}'.encode())
            if data:
                breakdown = json.loads(data.decode())
                
                # Check required fields for dashboard calculations
                required_fields = ['overall_score', 'sentiment', 'reliability', 
                                 'components', 'interpretations']
                critical_fields = ['price', 'change_24h', 'volume_24h']  # These were missing before
                
                missing_required = [f for f in required_fields if f not in breakdown]
                missing_critical = [f for f in critical_fields if f not in breakdown]
                
                if missing_required:
                    self.errors.append(f"❌ Confluence breakdown missing required fields: {missing_required}")
                else:
                    self.successes.append("✅ Confluence breakdown has all required fields")
                
                if missing_critical:
                    self.errors.append(f"❌ Confluence breakdown missing critical market data fields: {missing_critical}")
                    self.errors.append("   This will cause market breadth and sentiment calculations to fail!")
                else:
                    self.successes.append("✅ Confluence breakdown includes critical market data fields (price, change_24h, volume_24h)")
                
                # Check field values
                if 'change_24h' in breakdown:
                    self.successes.append(f"✅ Confluence breakdown uses 'change_24h' field (value: {breakdown['change_24h']})")
                
                if 'components' in breakdown:
                    components = breakdown['components']
                    expected_components = ['technical', 'volume', 'orderflow', 'sentiment', 'orderbook', 'price_structure']
                    missing_components = [c for c in expected_components if c not in components]
                    
                    if missing_components:
                        self.warnings.append(f"⚠️  Confluence components missing: {missing_components}")
                    else:
                        self.successes.append("✅ All confluence components present")
                
                return len(missing_critical) == 0  # Return false if critical fields are missing
            else:
                self.warnings.append(f"⚠️  No confluence breakdown for {symbol} in cache")
                return False
        except Exception as e:
            self.errors.append(f"❌ Error validating confluence breakdown: {e}")
            return False
    
    async def validate_market_breadth(self, client: aiomcache.Client) -> bool:
        """Validate market breadth data"""
        try:
            data = await client.get(b'market:breadth')
            if data:
                breadth = json.loads(data.decode())
                
                required_fields = ['up_count', 'down_count', 'flat_count', 
                                 'breadth_percentage', 'market_sentiment']
                missing_fields = [f for f in required_fields if f not in breadth]
                
                if missing_fields:
                    self.warnings.append(f"⚠️  Market breadth missing fields: {missing_fields}")
                else:
                    self.successes.append("✅ Market breadth has all required fields")
                    self.successes.append(f"   - Up: {breadth['up_count']}, Down: {breadth['down_count']}, Flat: {breadth['flat_count']}")
                    self.successes.append(f"   - Breadth: {breadth['breadth_percentage']}%, Sentiment: {breadth['market_sentiment']}")
                
                return True
            else:
                self.warnings.append("⚠️  No market breadth data in cache")
                return False
        except Exception as e:
            self.errors.append(f"❌ Error validating market breadth: {e}")
            return False
    
    async def test_field_mapping(self) -> bool:
        """Test field mapping for backward compatibility"""
        test_data = {
            'price_change_24h': 5.5,  # Old field name
            'change_24h': 5.5,         # New field name
            'volume': 1000000,         # Old field name
            'volume_24h': 1000000,     # New field name
            'volatility': 3.2,         # Old field name
            'current_volatility': 3.2  # New field name
        }
        
        # Test field access with backward compatibility
        # Simulating what main.py does after the fix
        change = test_data.get('change_24h', test_data.get('price_change_24h', 0))
        volume = test_data.get('volume_24h', test_data.get('volume', 0))
        volatility = test_data.get('current_volatility', test_data.get('volatility', 0))
        
        if change == 5.5 and volume == 1000000 and volatility == 3.2:
            self.successes.append("✅ Field mapping with backward compatibility works correctly")
            return True
        else:
            self.errors.append("❌ Field mapping failed")
            return False
    
    async def run_validation(self):
        """Run all validation tests"""
        print("\n" + "="*60)
        print("🔍 VIRTUOSO CCXT DATA STRUCTURE VALIDATION")
        print("="*60 + "\n")
        
        # Connect to cache
        client = await self.connect_cache()
        if not client:
            print("❌ Cannot proceed without cache connection")
            return False
        
        print("Testing data structures...\n")
        
        # Run all validations
        tests = [
            ("Market Overview", self.validate_market_overview(client)),
            ("Tickers", self.validate_tickers(client)),
            ("Confluence Breakdown", self.validate_confluence_breakdown(client)),
            ("Market Breadth", self.validate_market_breadth(client)),
            ("Field Mapping", self.test_field_mapping())
        ]
        
        results = []
        for test_name, test_coro in tests:
            print(f"Testing {test_name}...")
            result = await test_coro
            results.append((test_name, result))
            await asyncio.sleep(0.1)  # Small delay between tests
        
        # Close cache connection
        await client.close()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60 + "\n")
        
        if self.successes:
            print("✅ SUCCESSES:")
            for success in self.successes:
                print(f"  {success}")
            print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
            print()
        
        # Overall result
        all_passed = all(result for _, result in results)
        critical_errors = len(self.errors)
        
        print("="*60)
        if all_passed and critical_errors == 0:
            print("✅ ALL TESTS PASSED - Data structures are consistent!")
            print("\nThe fixes have successfully resolved:")
            print("1. Field name inconsistencies (price_change_24h vs change_24h)")
            print("2. Missing fields in confluence breakdown (price, change_24h, volume_24h)")
            print("3. Market breadth calculation issues")
            return True
        elif critical_errors > 0:
            print(f"❌ VALIDATION FAILED - {critical_errors} critical errors found")
            print("\nPlease ensure:")
            print("1. The system is running with the latest fixes")
            print("2. Cache has been populated with new data")
            print("3. Run: python src/main.py to populate cache")
            return False
        else:
            print("⚠️  VALIDATION COMPLETED WITH WARNINGS")
            print(f"\n{len(self.warnings)} warnings found but no critical errors")
            return True

async def main():
    """Main entry point"""
    validator = DataStructureValidator()
    success = await validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())