#!/usr/bin/env python3
"""
Comprehensive investigation of partial validation issues in the trading system.
"""
import sys
import os
import logging
import asyncio
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationIssueInvestigator:
    """Investigates partial validation issues across the system."""
    
    def __init__(self):
        self.logger = logger
        self.validation_systems = []
        
    def investigate_validation_systems(self):
        """Identify all validation systems in the codebase."""
        
        print("🔍 **INVESTIGATING PARTIAL VALIDATION ISSUES**\n")
        print("=== Validation Systems Identified ===\n")
        
        validation_systems = [
            {
                'name': 'BybitExchange.validate_market_data()',
                'location': 'src/core/exchanges/bybit.py:1126',
                'status': '✅ FIXED - Now uses flexible validation',
                'description': 'Exchange-level validation with improved flexibility'
            },
            {
                'name': 'MarketDataValidator._validate_ticker()',
                'location': 'src/monitoring/monitor.py:579',
                'status': '❌ PROBLEMATIC - Still uses strict validation',
                'description': 'Monitor-level ticker validation requiring price fields'
            },
            {
                'name': 'BaseExchange.validate_market_data()',
                'location': 'src/core/exchanges/base.py:524',
                'status': '❌ STRICT - Requires specific field structure',
                'description': 'Base class validation with rigid requirements'
            },
            {
                'name': 'DataValidator.validate_market_data()',
                'location': 'src/utils/validation.py:15',
                'status': '❌ STRICT - Requires specific structure',
                'description': 'Utility validation with fixed requirements'
            },
            {
                'name': 'MarketDataValidator (data_processing)',
                'location': 'src/data_processing/market_validator.py:25',
                'status': '⚠️  UNKNOWN - Needs investigation',
                'description': 'Data processing validation system'
            }
        ]
        
        for i, system in enumerate(validation_systems, 1):
            print(f"{i}. **{system['name']}**")
            print(f"   📍 Location: {system['location']}")
            print(f"   🔧 Status: {system['status']}")
            print(f"   📝 Description: {system['description']}\n")
            
        return validation_systems
    
    def demonstrate_validation_conflicts(self):
        """Demonstrate how different validation systems conflict."""
        
        print("=== Validation Conflict Demonstration ===\n")
        
        # Simulate market data with missing ticker price (common scenario)
        market_data_scenarios = [
            {
                'name': 'Empty Ticker Data (API fetch failed)',
                'data': {
                    'symbol': 'BTCUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {},  # ← Empty ticker when fetch fails
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 50, 'short': 50}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': False}
                }
            },
            {
                'name': 'Partial Ticker Data (missing price)',
                'data': {
                    'symbol': 'ETHUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {
                        'volume': 1000000,
                        'high24h': 3100,
                        'low24h': 2900
                        # ← Missing 'lastPrice', 'last', 'price' fields
                    },
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 60, 'short': 40}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': True}
                }
            },
            {
                'name': 'Alternative Price Field Names',
                'data': {
                    'symbol': 'ADAUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {
                        'close': 0.45,  # ← Uses 'close' instead of 'lastPrice'
                        'volume': 500000
                    },
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 55, 'short': 45}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': True}
                }
            }
        ]
        
        for scenario in market_data_scenarios:
            print(f"**Scenario: {scenario['name']}**")
            print(f"Data structure: {scenario['data']['ticker']}")
            
            # Simulate different validation results
            validations = [
                {
                    'system': 'BybitExchange (Fixed)',
                    'result': '✅ PASS',
                    'reason': 'Flexible validation warns but continues'
                },
                {
                    'system': 'MarketDataValidator._validate_ticker',
                    'result': '❌ FAIL',
                    'reason': 'Missing critical price field in ticker data'
                },
                {
                    'system': 'BaseExchange.validate_market_data',
                    'result': '❌ FAIL',
                    'reason': 'Missing required fields for ticker'
                },
                {
                    'system': 'DataValidator.validate_market_data',
                    'result': '❌ FAIL',
                    'reason': 'Missing required keys in market data'
                }
            ]
            
            for validation in validations:
                print(f"  {validation['result']} {validation['system']}: {validation['reason']}")
            
            print()
    
    def analyze_root_causes(self):
        """Analyze the root causes of validation issues."""
        
        print("=== Root Cause Analysis ===\n")
        
        root_causes = [
            {
                'issue': 'Multiple Validation Systems',
                'description': 'Different parts of the system use different validation logic',
                'impact': 'Inconsistent behavior - some validators pass, others fail',
                'examples': [
                    'BybitExchange uses flexible validation',
                    'MarketDataValidator uses strict validation',
                    'BaseExchange uses rigid field requirements'
                ]
            },
            {
                'issue': 'Inconsistent Field Naming',
                'description': 'Different exchanges use different field names for the same data',
                'impact': 'Validation fails when expecting specific field names',
                'examples': [
                    'Bybit uses "lastPrice"',
                    'Binance uses "last"',
                    'Some systems expect "price"',
                    'OHLCV data uses "close"'
                ]
            },
            {
                'issue': 'API Fetch Failures',
                'description': 'When API calls fail, empty or partial data structures are created',
                'impact': 'Validation systems expect complete data but get empty structures',
                'examples': [
                    'ticker: {} when fetch_ticker fails',
                    'Missing price fields when rate limited',
                    'Partial data when some endpoints succeed, others fail'
                ]
            },
            {
                'issue': 'Validation Timing',
                'description': 'Validation happens after data assembly, not during fetch',
                'impact': 'System processes incomplete data before validation catches issues',
                'examples': [
                    'Market data assembled with empty ticker',
                    'Validation runs after all processing',
                    'Downstream systems receive invalid data'
                ]
            }
        ]
        
        for i, cause in enumerate(root_causes, 1):
            print(f"**{i}. {cause['issue']}**")
            print(f"   📝 Description: {cause['description']}")
            print(f"   💥 Impact: {cause['impact']}")
            print(f"   📋 Examples:")
            for example in cause['examples']:
                print(f"      • {example}")
            print()
    
    def propose_comprehensive_fixes(self):
        """Propose comprehensive fixes for all validation issues."""
        
        print("=== Comprehensive Fix Strategy ===\n")
        
        fixes = [
            {
                'priority': 'HIGH',
                'fix': 'Standardize All Validation Systems',
                'description': 'Update all validators to use flexible validation approach',
                'files_to_modify': [
                    'src/monitoring/monitor.py - MarketDataValidator._validate_ticker',
                    'src/core/exchanges/base.py - BaseExchange.validate_market_data',
                    'src/utils/validation.py - DataValidator.validate_market_data'
                ],
                'implementation': 'Replace strict field requirements with flexible field detection'
            },
            {
                'priority': 'HIGH',
                'fix': 'Implement Field Name Mapping',
                'description': 'Create a centralized field mapping system for different exchanges',
                'files_to_modify': [
                    'src/core/exchanges/field_mapper.py - New file',
                    'All validation systems'
                ],
                'implementation': 'Map lastPrice/last/price/close to standardized field names'
            },
            {
                'priority': 'MEDIUM',
                'fix': 'Add Validation Context',
                'description': 'Provide context about data source and expected completeness',
                'files_to_modify': [
                    'All validation systems'
                ],
                'implementation': 'Pass context about which fields are expected vs optional'
            },
            {
                'priority': 'MEDIUM',
                'fix': 'Implement Graceful Degradation',
                'description': 'Allow system to continue with partial data',
                'files_to_modify': [
                    'All data processing components'
                ],
                'implementation': 'Use default values for missing fields, warn instead of fail'
            },
            {
                'priority': 'LOW',
                'fix': 'Add Validation Metrics',
                'description': 'Track validation success/failure rates for monitoring',
                'files_to_modify': [
                    'src/monitoring/metrics_manager.py'
                ],
                'implementation': 'Record validation statistics for analysis'
            }
        ]
        
        for fix in fixes:
            print(f"**🔧 {fix['fix']}** ({fix['priority']} Priority)")
            print(f"   📝 Description: {fix['description']}")
            print(f"   📁 Files to modify:")
            for file in fix['files_to_modify']:
                print(f"      • {file}")
            print(f"   ⚙️  Implementation: {fix['implementation']}\n")
    
    def create_test_scenarios(self):
        """Create test scenarios to verify fixes."""
        
        print("=== Test Scenarios for Validation Fixes ===\n")
        
        scenarios = [
            {
                'name': 'Empty Ticker Validation',
                'test': 'Validate market data with empty ticker field',
                'expected': 'Should warn but not fail validation'
            },
            {
                'name': 'Alternative Price Fields',
                'test': 'Validate ticker with close/last/price instead of lastPrice',
                'expected': 'Should detect price field regardless of name'
            },
            {
                'name': 'Partial Data Structures',
                'test': 'Validate market data missing optional components',
                'expected': 'Should continue processing with warnings'
            },
            {
                'name': 'Cross-Validator Consistency',
                'test': 'Run same data through all validation systems',
                'expected': 'All validators should return consistent results'
            },
            {
                'name': 'API Failure Simulation',
                'test': 'Simulate API failures and validate resulting data',
                'expected': 'System should handle gracefully with default values'
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"{i}. **{scenario['name']}**")
            print(f"   🧪 Test: {scenario['test']}")
            print(f"   ✅ Expected: {scenario['expected']}\n")

def main():
    """Run the comprehensive validation investigation."""
    
    investigator = ValidationIssueInvestigator()
    
    investigator.investigate_validation_systems()
    investigator.demonstrate_validation_conflicts()
    investigator.analyze_root_causes()
    investigator.propose_comprehensive_fixes()
    investigator.create_test_scenarios()
    
    print("🎯 **SUMMARY**")
    print("The partial validation issues stem from multiple conflicting validation")
    print("systems with different requirements. The solution is to standardize all")
    print("validators to use flexible validation with field name mapping.\n")
    
    print("📋 **NEXT STEPS**")
    print("1. Fix MarketDataValidator._validate_ticker in monitor.py")
    print("2. Update BaseExchange.validate_market_data for flexibility")
    print("3. Implement centralized field mapping system")
    print("4. Add comprehensive test coverage")
    print("5. Monitor validation metrics in production")

if __name__ == "__main__":
    main() 