#!/usr/bin/env python3
"""
Simple Sentiment Data Verification Script

This script directly tests the Bybit API and identifies data pipeline issues
without complex imports that might cause module loading problems.
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any
from datetime import datetime

class SimpleSentimentVerifier:
    """Simple verifier for sentiment data sources."""
    
    def __init__(self):
        self.base_url = 'https://api.bybit.com'
        
    async def verify_api_endpoints(self, symbol: str = 'VIRTUALUSDT') -> Dict[str, Any]:
        """Verify API endpoints provide complete sentiment data."""
        print(f"=== Verifying Sentiment Data Sources for {symbol} ===\n")
        
        results = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'api_tests': {},
            'data_completeness': {},
            'issues_found': []
        }
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Ticker endpoint (funding rate, open interest)
            print("1. Testing Ticker Endpoint...")
            ticker_url = f'{self.base_url}/v5/market/tickers?category=linear&symbol={symbol}'
            
            try:
                async with session.get(ticker_url) as response:
                    ticker_data = await response.json()
                    
                    if ticker_data.get('retCode') == 0 and 'result' in ticker_data:
                        ticker_list = ticker_data['result'].get('list', [])
                        if ticker_list:
                            ticker = ticker_list[0]
                            results['api_tests']['ticker'] = {
                                'success': True,
                                'funding_rate': ticker.get('fundingRate'),
                                'open_interest': ticker.get('openInterest'),
                                'open_interest_value': ticker.get('openInterestValue'),
                                'next_funding_time': ticker.get('nextFundingTime')
                            }
                            print(f"   ✓ Funding Rate: {ticker.get('fundingRate')}")
                            print(f"   ✓ Open Interest: {ticker.get('openInterest')}")
                            print(f"   ✓ OI Value: {ticker.get('openInterestValue')}")
                        else:
                            results['api_tests']['ticker'] = {'success': False, 'error': 'No ticker data'}
                            results['issues_found'].append("Ticker API returned no data")
                    else:
                        results['api_tests']['ticker'] = {'success': False, 'error': ticker_data}
                        results['issues_found'].append(f"Ticker API error: {ticker_data}")
                        
            except Exception as e:
                results['api_tests']['ticker'] = {'success': False, 'error': str(e)}
                results['issues_found'].append(f"Ticker API exception: {str(e)}")
                print(f"   ✗ Error: {str(e)}")
            
            # Test 2: Long/Short Ratio endpoint
            print("\n2. Testing Long/Short Ratio Endpoint...")
            lsr_url = f'{self.base_url}/v5/market/account-ratio?category=linear&symbol={symbol}&period=1d&limit=1'
            
            try:
                async with session.get(lsr_url) as response:
                    lsr_data = await response.json()
                    
                    if lsr_data.get('retCode') == 0 and 'result' in lsr_data:
                        lsr_list = lsr_data['result'].get('list', [])
                        if lsr_list:
                            lsr = lsr_list[0]
                            results['api_tests']['long_short_ratio'] = {
                                'success': True,
                                'buy_ratio': lsr.get('buyRatio'),
                                'sell_ratio': lsr.get('sellRatio'),
                                'timestamp': lsr.get('timestamp')
                            }
                            print(f"   ✓ Buy Ratio: {lsr.get('buyRatio')}")
                            print(f"   ✓ Sell Ratio: {lsr.get('sellRatio')}")
                        else:
                            results['api_tests']['long_short_ratio'] = {'success': False, 'error': 'No LSR data'}
                            results['issues_found'].append("Long/Short Ratio API returned no data")
                    else:
                        results['api_tests']['long_short_ratio'] = {'success': False, 'error': lsr_data}
                        results['issues_found'].append(f"Long/Short Ratio API error: {lsr_data}")
                        
            except Exception as e:
                results['api_tests']['long_short_ratio'] = {'success': False, 'error': str(e)}
                results['issues_found'].append(f"Long/Short Ratio API exception: {str(e)}")
                print(f"   ✗ Error: {str(e)}")
            
            # Test 3: Funding History endpoint
            print("\n3. Testing Funding History Endpoint...")
            funding_url = f'{self.base_url}/v5/market/funding/history?category=linear&symbol={symbol}&limit=1'
            
            try:
                async with session.get(funding_url) as response:
                    funding_data = await response.json()
                    
                    if funding_data.get('retCode') == 0 and 'result' in funding_data:
                        funding_list = funding_data['result'].get('list', [])
                        if funding_list:
                            funding = funding_list[0]
                            results['api_tests']['funding_history'] = {
                                'success': True,
                                'funding_rate': funding.get('fundingRate'),
                                'funding_time': funding.get('fundingRateTimestamp')
                            }
                            print(f"   ✓ Historical Funding Rate: {funding.get('fundingRate')}")
                            print(f"   ✓ Funding Time: {funding.get('fundingRateTimestamp')}")
                        else:
                            results['api_tests']['funding_history'] = {'success': False, 'error': 'No funding history'}
                            results['issues_found'].append("Funding History API returned no data")
                    else:
                        results['api_tests']['funding_history'] = {'success': False, 'error': funding_data}
                        results['issues_found'].append(f"Funding History API error: {funding_data}")
                        
            except Exception as e:
                results['api_tests']['funding_history'] = {'success': False, 'error': str(e)}
                results['issues_found'].append(f"Funding History API exception: {str(e)}")
                print(f"   ✗ Error: {str(e)}")
        
        # Analyze data completeness
        self._analyze_data_completeness(results)
        
        return results
    
    def _analyze_data_completeness(self, results: Dict[str, Any]) -> None:
        """Analyze data completeness and identify issues."""
        print("\n4. Analyzing Data Completeness...")
        
        api_tests = results['api_tests']
        completeness = {}
        
        # Check ticker data completeness
        ticker = api_tests.get('ticker', {})
        if ticker.get('success'):
            completeness['ticker'] = {
                'funding_rate_available': ticker.get('funding_rate') is not None,
                'open_interest_available': ticker.get('open_interest') is not None,
                'open_interest_value_available': ticker.get('open_interest_value') is not None,
                'next_funding_time_available': ticker.get('next_funding_time') is not None
            }
            
            # Check for missing fields
            if not completeness['ticker']['funding_rate_available']:
                results['issues_found'].append("Ticker API missing funding rate")
            if not completeness['ticker']['open_interest_available']:
                results['issues_found'].append("Ticker API missing open interest")
        else:
            completeness['ticker'] = {'available': False}
            results['issues_found'].append("Ticker API not available")
        
        # Check LSR data completeness
        lsr = api_tests.get('long_short_ratio', {})
        if lsr.get('success'):
            completeness['long_short_ratio'] = {
                'buy_ratio_available': lsr.get('buy_ratio') is not None,
                'sell_ratio_available': lsr.get('sell_ratio') is not None
            }
            
            if not completeness['long_short_ratio']['buy_ratio_available']:
                results['issues_found'].append("LSR API missing buy ratio")
            if not completeness['long_short_ratio']['sell_ratio_available']:
                results['issues_found'].append("LSR API missing sell ratio")
        else:
            completeness['long_short_ratio'] = {'available': False}
            results['issues_found'].append("Long/Short Ratio API not available")
        
        # Check funding history completeness
        funding = api_tests.get('funding_history', {})
        if funding.get('success'):
            completeness['funding_history'] = {
                'funding_rate_available': funding.get('funding_rate') is not None,
                'funding_time_available': funding.get('funding_time') is not None
            }
        else:
            completeness['funding_history'] = {'available': False}
            results['issues_found'].append("Funding History API not available")
        
        results['data_completeness'] = completeness
        
        # Print completeness summary
        for source, data in completeness.items():
            if isinstance(data, dict) and 'available' in data:
                print(f"   {source}: {'✗ Not Available' if not data['available'] else '✓ Available'}")
            else:
                available_fields = sum(1 for v in data.values() if v)
                total_fields = len(data)
                print(f"   {source}: {available_fields}/{total_fields} fields available")
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print a summary of the verification results."""
        print("\n" + "="*60)
        print("SENTIMENT DATA VERIFICATION SUMMARY")
        print("="*60)
        
        issues = results.get('issues_found', [])
        
        if not issues:
            print("✓ ALL SENTIMENT DATA SOURCES ARE WORKING CORRECTLY")
            print("\nThe API is providing complete sentiment data:")
            
            api_tests = results.get('api_tests', {})
            if api_tests.get('ticker', {}).get('success'):
                ticker = api_tests['ticker']
                print(f"  • Funding Rate: {ticker.get('funding_rate')}")
                print(f"  • Open Interest: {ticker.get('open_interest')}")
            
            if api_tests.get('long_short_ratio', {}).get('success'):
                lsr = api_tests['long_short_ratio']
                print(f"  • Long/Short Ratio: {lsr.get('buy_ratio')}/{lsr.get('sell_ratio')}")
            
            print("\nThe warnings in your logs are likely due to:")
            print("  1. Data transformation issues in the exchange implementation")
            print("  2. Validation logic expecting different data formats")
            print("  3. Timing issues where data isn't available when validation runs")
            
        else:
            print("✗ ISSUES FOUND WITH SENTIMENT DATA SOURCES")
            print(f"\nFound {len(issues)} issue(s):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict[str, Any], filename: str = 'sentiment_verification.json') -> None:
        """Save results to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {filename}")

async def main():
    """Main verification function."""
    verifier = SimpleSentimentVerifier()
    
    # Test with VIRTUALUSDT (the symbol from the log)
    results = await verifier.verify_api_endpoints('VIRTUALUSDT')
    
    # Print summary
    verifier.print_summary(results)
    
    # Save results
    verifier.save_results(results)
    
    # Return exit code based on issues found
    return 1 if results.get('issues_found') else 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 