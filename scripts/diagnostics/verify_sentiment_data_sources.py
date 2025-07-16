#!/usr/bin/env python3
"""
Sentiment Data Source Verification Script

This script verifies that the exchange API is providing complete sentiment data
and identifies any gaps in the data pipeline that could cause the warnings:
- Missing recommended sentiment fields: ['funding_rate']
- Missing liquidations data, setting defaults
- Open interest dict missing 'value' field, setting default
"""

import asyncio
import sys
import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.exchanges.bybit import BybitExchange
from core.analysis.confluence import ConfluenceAnalyzer
from core.logger import Logger

class SentimentDataVerifier:
    """Verifies sentiment data sources and pipeline integrity."""
    
    def __init__(self):
        self.logger = Logger(__name__)
        self.config = self._load_config()
        self.exchange = None
        self.confluence_analyzer = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration for testing."""
        return {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'testnet': False,
                    'api_key': '',  # Not needed for public data
                    'api_secret': '',
                    'timeout': 30000,
                    'rate_limit': True
                }
            },
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'parameters': {
                            'sigmoid_transformation': {
                                'default_sensitivity': 0.12,
                                'long_short_sensitivity': 0.12,
                                'funding_sensitivity': 0.15,
                                'liquidation_sensitivity': 0.1
                            }
                        }
                    }
                }
            }
        }
    
    async def verify_api_data_sources(self, symbol: str = 'VIRTUALUSDT') -> Dict[str, Any]:
        """Verify that the API provides all required sentiment data."""
        self.logger.info(f"=== Verifying API Data Sources for {symbol} ===")
        
        results = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'api_sources': {},
            'data_completeness': {},
            'issues_found': []
        }
        
        try:
            # Initialize exchange
            self.exchange = BybitExchange(self.config, None)
            await self.exchange.initialize()
            
            # Test 1: Direct API calls to verify data availability
            self.logger.info("1. Testing direct API endpoints...")
            
            # Test ticker endpoint (funding rate, open interest)
            ticker_data = await self.exchange._fetch_ticker(symbol)
            results['api_sources']['ticker'] = {
                'success': bool(ticker_data),
                'funding_rate_present': 'fundingRate' in ticker_data if ticker_data else False,
                'open_interest_present': 'openInterest' in ticker_data if ticker_data else False,
                'next_funding_time_present': 'nextFundingTime' in ticker_data if ticker_data else False,
                'funding_rate_value': ticker_data.get('fundingRate') if ticker_data else None,
                'open_interest_value': ticker_data.get('openInterest') if ticker_data else None
            }
            
            # Test long/short ratio endpoint
            lsr_data = await self.exchange._fetch_long_short_ratio(symbol)
            results['api_sources']['long_short_ratio'] = {
                'success': bool(lsr_data),
                'format': type(lsr_data).__name__ if lsr_data else None,
                'has_list': 'list' in lsr_data if isinstance(lsr_data, dict) else False,
                'data_present': bool(lsr_data.get('list', [])) if isinstance(lsr_data, dict) else False
            }
            
            if lsr_data and isinstance(lsr_data, dict) and 'list' in lsr_data and lsr_data['list']:
                latest_lsr = lsr_data['list'][0]
                results['api_sources']['long_short_ratio'].update({
                    'buy_ratio_present': 'buyRatio' in latest_lsr,
                    'sell_ratio_present': 'sellRatio' in latest_lsr,
                    'buy_ratio_value': latest_lsr.get('buyRatio'),
                    'sell_ratio_value': latest_lsr.get('sellRatio')
                })
            
            # Test liquidations (WebSocket data)
            liquidations = self.exchange.get_recent_liquidations(symbol)
            results['api_sources']['liquidations'] = {
                'websocket_data_available': bool(liquidations),
                'liquidation_count': len(liquidations) if liquidations else 0,
                'sample_liquidation': liquidations[0] if liquidations else None
            }
            
            # Test 2: Exchange fetch_market_data method
            self.logger.info("2. Testing exchange fetch_market_data method...")
            market_data = await self.exchange.fetch_market_data(symbol)
            
            results['data_completeness']['market_data_structure'] = {
                'has_sentiment': 'sentiment' in market_data,
                'has_ticker': 'ticker' in market_data,
                'has_ohlcv': 'ohlcv' in market_data
            }
            
            if 'sentiment' in market_data:
                sentiment = market_data['sentiment']
                results['data_completeness']['sentiment_fields'] = {
                    'funding_rate': {
                        'present': 'funding_rate' in sentiment,
                        'type': type(sentiment.get('funding_rate')).__name__ if 'funding_rate' in sentiment else None,
                        'structure': self._analyze_structure(sentiment.get('funding_rate')) if 'funding_rate' in sentiment else None
                    },
                    'long_short_ratio': {
                        'present': 'long_short_ratio' in sentiment,
                        'type': type(sentiment.get('long_short_ratio')).__name__ if 'long_short_ratio' in sentiment else None,
                        'structure': self._analyze_structure(sentiment.get('long_short_ratio')) if 'long_short_ratio' in sentiment else None
                    },
                    'liquidations': {
                        'present': 'liquidations' in sentiment,
                        'type': type(sentiment.get('liquidations')).__name__ if 'liquidations' in sentiment else None,
                        'structure': self._analyze_structure(sentiment.get('liquidations')) if 'liquidations' in sentiment else None
                    },
                    'open_interest': {
                        'present': 'open_interest' in sentiment,
                        'type': type(sentiment.get('open_interest')).__name__ if 'open_interest' in sentiment else None,
                        'structure': self._analyze_structure(sentiment.get('open_interest')) if 'open_interest' in sentiment else None
                    }
                }
            
            # Test 3: Confluence analyzer validation
            self.logger.info("3. Testing confluence analyzer validation...")
            self.confluence_analyzer = ConfluenceAnalyzer(self.config)
            
            # Test sentiment data validation
            validation_result = self.confluence_analyzer._validate_sentiment_data(market_data)
            results['data_completeness']['confluence_validation'] = {
                'passes_validation': validation_result,
                'market_data_keys': list(market_data.keys()),
                'sentiment_keys': list(market_data.get('sentiment', {}).keys()) if 'sentiment' in market_data else []
            }
            
            # Test data preparation
            prepared_data = self.confluence_analyzer._prepare_data_for_sentiment(market_data)
            results['data_completeness']['prepared_sentiment'] = {
                'preparation_successful': bool(prepared_data),
                'prepared_keys': list(prepared_data.keys()) if prepared_data else [],
                'sentiment_keys': list(prepared_data.get('sentiment', {}).keys()) if prepared_data and 'sentiment' in prepared_data else []
            }
            
            # Analyze issues
            self._analyze_issues(results)
            
        except Exception as e:
            self.logger.error(f"Error during verification: {str(e)}")
            results['error'] = str(e)
            results['issues_found'].append(f"Verification failed with error: {str(e)}")
        
        finally:
            if self.exchange:
                await self.exchange.close()
        
        return results
    
    def _analyze_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of a data field."""
        if data is None:
            return {'type': 'None'}
        elif isinstance(data, dict):
            return {
                'type': 'dict',
                'keys': list(data.keys()),
                'sample_values': {k: type(v).__name__ for k, v in list(data.items())[:3]}
            }
        elif isinstance(data, list):
            return {
                'type': 'list',
                'length': len(data),
                'sample_item': type(data[0]).__name__ if data else None
            }
        else:
            return {
                'type': type(data).__name__,
                'value': str(data)[:100]  # Truncate long values
            }
    
    def _analyze_issues(self, results: Dict[str, Any]) -> None:
        """Analyze the results and identify potential issues."""
        issues = results['issues_found']
        
        # Check API data sources
        api_sources = results.get('api_sources', {})
        
        # Ticker issues
        ticker = api_sources.get('ticker', {})
        if not ticker.get('success'):
            issues.append("Ticker API call failed")
        if not ticker.get('funding_rate_present'):
            issues.append("Funding rate not present in ticker data")
        if not ticker.get('open_interest_present'):
            issues.append("Open interest not present in ticker data")
        
        # LSR issues
        lsr = api_sources.get('long_short_ratio', {})
        if not lsr.get('success'):
            issues.append("Long/Short ratio API call failed")
        if not lsr.get('data_present'):
            issues.append("Long/Short ratio data not available")
        
        # Liquidations issues
        liquidations = api_sources.get('liquidations', {})
        if not liquidations.get('websocket_data_available'):
            issues.append("No liquidation data available from WebSocket")
        
        # Data completeness issues
        completeness = results.get('data_completeness', {})
        
        # Market data structure issues
        structure = completeness.get('market_data_structure', {})
        if not structure.get('has_sentiment'):
            issues.append("Market data missing sentiment section")
        
        # Sentiment field issues
        sentiment_fields = completeness.get('sentiment_fields', {})
        
        funding_rate = sentiment_fields.get('funding_rate', {})
        if not funding_rate.get('present'):
            issues.append("Funding rate field missing from sentiment data")
        elif funding_rate.get('type') != 'dict':
            issues.append(f"Funding rate has unexpected type: {funding_rate.get('type')}")
        
        lsr_field = sentiment_fields.get('long_short_ratio', {})
        if not lsr_field.get('present'):
            issues.append("Long/Short ratio field missing from sentiment data")
        elif lsr_field.get('type') != 'dict':
            issues.append(f"Long/Short ratio has unexpected type: {lsr_field.get('type')}")
        
        liquidations_field = sentiment_fields.get('liquidations', {})
        if not liquidations_field.get('present'):
            issues.append("Liquidations field missing from sentiment data")
        
        open_interest_field = sentiment_fields.get('open_interest', {})
        if not open_interest_field.get('present'):
            issues.append("Open interest field missing from sentiment data")
        elif open_interest_field.get('type') == 'dict':
            structure = open_interest_field.get('structure', {})
            if isinstance(structure, dict) and 'keys' in structure:
                if 'value' not in structure['keys']:
                    issues.append("Open interest dict missing 'value' field")
        
        # Confluence validation issues
        confluence = completeness.get('confluence_validation', {})
        if not confluence.get('passes_validation'):
            issues.append("Confluence analyzer validation failed")
    
    def print_results(self, results: Dict[str, Any]) -> None:
        """Print verification results in a readable format."""
        print("\n" + "="*80)
        print("SENTIMENT DATA SOURCE VERIFICATION RESULTS")
        print("="*80)
        
        print(f"\nSymbol: {results['symbol']}")
        print(f"Timestamp: {results['timestamp']}")
        
        # API Sources
        print(f"\n{'API DATA SOURCES':<30}")
        print("-" * 50)
        
        api_sources = results.get('api_sources', {})
        
        # Ticker
        ticker = api_sources.get('ticker', {})
        print(f"Ticker API:                    {'✓' if ticker.get('success') else '✗'}")
        print(f"  - Funding Rate:              {'✓' if ticker.get('funding_rate_present') else '✗'} ({ticker.get('funding_rate_value', 'N/A')})")
        print(f"  - Open Interest:             {'✓' if ticker.get('open_interest_present') else '✗'} ({ticker.get('open_interest_value', 'N/A')})")
        print(f"  - Next Funding Time:         {'✓' if ticker.get('next_funding_time_present') else '✗'}")
        
        # Long/Short Ratio
        lsr = api_sources.get('long_short_ratio', {})
        print(f"Long/Short Ratio API:          {'✓' if lsr.get('success') else '✗'}")
        print(f"  - Data Available:            {'✓' if lsr.get('data_present') else '✗'}")
        if lsr.get('buy_ratio_value') and lsr.get('sell_ratio_value'):
            print(f"  - Buy/Sell Ratio:            {lsr.get('buy_ratio_value')}/{lsr.get('sell_ratio_value')}")
        
        # Liquidations
        liquidations = api_sources.get('liquidations', {})
        print(f"Liquidations WebSocket:        {'✓' if liquidations.get('websocket_data_available') else '✗'}")
        print(f"  - Liquidation Count:         {liquidations.get('liquidation_count', 0)}")
        
        # Data Completeness
        print(f"\n{'DATA PIPELINE COMPLETENESS':<30}")
        print("-" * 50)
        
        completeness = results.get('data_completeness', {})
        
        # Market data structure
        structure = completeness.get('market_data_structure', {})
        print(f"Market Data Structure:         {'✓' if all(structure.values()) else '✗'}")
        print(f"  - Has Sentiment:             {'✓' if structure.get('has_sentiment') else '✗'}")
        print(f"  - Has Ticker:                {'✓' if structure.get('has_ticker') else '✗'}")
        print(f"  - Has OHLCV:                 {'✓' if structure.get('has_ohlcv') else '✗'}")
        
        # Sentiment fields
        sentiment_fields = completeness.get('sentiment_fields', {})
        print(f"Sentiment Fields:")
        for field_name, field_info in sentiment_fields.items():
            present = field_info.get('present', False)
            field_type = field_info.get('type', 'Unknown')
            print(f"  - {field_name:<20}     {'✓' if present else '✗'} ({field_type})")
        
        # Confluence validation
        confluence = completeness.get('confluence_validation', {})
        print(f"Confluence Validation:         {'✓' if confluence.get('passes_validation') else '✗'}")
        
        # Issues Found
        issues = results.get('issues_found', [])
        if issues:
            print(f"\n{'ISSUES IDENTIFIED':<30}")
            print("-" * 50)
            for i, issue in enumerate(issues, 1):
                print(f"{i:2d}. {issue}")
        else:
            print(f"\n{'✓ NO ISSUES FOUND':<30}")
        
        print("\n" + "="*80)

async def main():
    """Main verification function."""
    verifier = SentimentDataVerifier()
    
    # Test with VIRTUALUSDT (the symbol from the log)
    results = await verifier.verify_api_data_sources('VIRTUALUSDT')
    
    # Print results
    verifier.print_results(results)
    
    # Save detailed results to file
    output_file = 'sentiment_data_verification_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Return exit code based on issues found
    return 1 if results.get('issues_found') else 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 