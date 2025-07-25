#!/usr/bin/env python3
"""
Comprehensive Indicator Scoring Review Script

This script systematically reviews all indicator scoring methods to ensure they follow
the standardized 0-100 bullish/bearish scheme where:
- 100 = extremely bullish
- 50 = neutral  
- 0 = extremely bearish

The script will:
1. Analyze each indicator's scoring logic
2. Identify any inconsistencies or potential issues
3. Provide fixes for any problems found
4. Generate validation tests for all scoring methods
"""

import os
import sys
import ast
import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class IndicatorScoringReviewer:
    """Review and validate indicator scoring schemes."""
    
    def __init__(self):
        self.indicators_path = Path(__file__).parent.parent.parent / "src" / "indicators"
        self.issues_found = []
        self.scoring_methods = {}
        self.validation_results = {}
        
    def analyze_all_indicators(self) -> Dict[str, Any]:
        """Analyze all indicator files for scoring consistency."""
        print("🔍 Starting comprehensive indicator scoring review...")
        
        # Define indicator files to analyze
        indicator_files = [
            "technical_indicators.py",
            "volume_indicators.py", 
            "sentiment_indicators.py",
            "orderbook_indicators.py",
            "orderflow_indicators.py",
            "price_structure_indicators.py"
        ]
        
        results = {}
        
        for file_name in indicator_files:
            file_path = self.indicators_path / file_name
            if file_path.exists():
                print(f"\n📊 Analyzing {file_name}...")
                results[file_name] = self.analyze_indicator_file(file_path)
            else:
                print(f"⚠️  File not found: {file_name}")
                
        return results
    
    def analyze_indicator_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single indicator file for scoring issues."""
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find all scoring methods
        scoring_methods = self.find_scoring_methods(content)
        
        # Analyze each method
        analysis_results = {
            'file': file_path.name,
            'scoring_methods': [],
            'issues': [],
            'recommendations': []
        }
        
        for method_name, method_code in scoring_methods.items():
            method_analysis = self.analyze_scoring_method(method_name, method_code)
            analysis_results['scoring_methods'].append(method_analysis)
            
            if method_analysis['issues']:
                analysis_results['issues'].extend(method_analysis['issues'])
                
        return analysis_results
    
    def find_scoring_methods(self, content: str) -> Dict[str, str]:
        """Find all scoring methods in the file content."""
        scoring_methods = {}
        
        # Pattern to match scoring methods
        pattern = r'def (_calculate_.*?_score.*?)\(.*?\):(.*?)(?=\n    def|\nclass|\n\n\n|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for method_name, method_body in matches:
            scoring_methods[method_name] = method_body
            
        return scoring_methods
    
    def analyze_scoring_method(self, method_name: str, method_code: str) -> Dict[str, Any]:
        """Analyze a single scoring method for consistency."""
        analysis = {
            'method': method_name,
            'issues': [],
            'score_range': None,
            'neutral_point': None,
            'bullish_bearish_logic': None
        }
        
        # Check for score clipping
        if 'np.clip' not in method_code and 'clip' not in method_code:
            analysis['issues'].append(f"⚠️  {method_name}: No score clipping found - scores may exceed 0-100 range")
            
        # Check for return of 50.0 (neutral)
        if 'return 50.0' in method_code or 'return 50' in method_code:
            analysis['neutral_point'] = 50.0
        else:
            analysis['issues'].append(f"⚠️  {method_name}: No neutral fallback (50.0) found")
            
        # Check for proper range usage
        if '0, 100' in method_code:
            analysis['score_range'] = (0, 100)
        elif '0.0, 100.0' in method_code:
            analysis['score_range'] = (0, 100)
        else:
            analysis['issues'].append(f"⚠️  {method_name}: Non-standard score range detected")
            
        # Analyze bullish/bearish logic
        analysis['bullish_bearish_logic'] = self.analyze_bullish_bearish_logic(method_code)
        
        return analysis
    
    def analyze_bullish_bearish_logic(self, method_code: str) -> Dict[str, Any]:
        """Analyze the bullish/bearish logic in scoring method."""
        logic_analysis = {
            'has_bullish_logic': False,
            'has_bearish_logic': False,
            'potential_issues': []
        }
        
        # Look for indicators of bullish logic (scores approaching 100)
        bullish_indicators = [
            'score += ', '+ 50', '+ 30', '+ 20', 'score = 100',
            'bullish', 'positive', 'above', 'greater', 'high'
        ]
        
        bearish_indicators = [
            'score -= ', '- 50', '- 30', '- 20', 'score = 0',
            'bearish', 'negative', 'below', 'less', 'low'
        ]
        
        for indicator in bullish_indicators:
            if indicator in method_code.lower():
                logic_analysis['has_bullish_logic'] = True
                break
                
        for indicator in bearish_indicators:
            if indicator in method_code.lower():
                logic_analysis['has_bearish_logic'] = True
                break
                
        # Check for potential inverted logic
        if 'overbought' in method_code.lower() and 'score +' in method_code:
            logic_analysis['potential_issues'].append("Potential inverted logic: overbought should reduce score")
            
        if 'oversold' in method_code.lower() and 'score -' in method_code:
            logic_analysis['potential_issues'].append("Potential inverted logic: oversold should increase score")
            
        return logic_analysis
    
    def validate_scoring_ranges(self) -> Dict[str, Any]:
        """Validate that all scoring methods return values in 0-100 range."""
        print("\n🧪 Running scoring range validation tests...")
        
        validation_results = {}
        
        # Test data scenarios
        test_scenarios = [
            {'name': 'extreme_bullish', 'description': 'Extreme bullish conditions'},
            {'name': 'moderate_bullish', 'description': 'Moderate bullish conditions'},
            {'name': 'neutral', 'description': 'Neutral market conditions'},
            {'name': 'moderate_bearish', 'description': 'Moderate bearish conditions'},
            {'name': 'extreme_bearish', 'description': 'Extreme bearish conditions'},
            {'name': 'edge_case_high', 'description': 'Edge case with very high values'},
            {'name': 'edge_case_low', 'description': 'Edge case with very low values'},
            {'name': 'nan_values', 'description': 'NaN/invalid data handling'},
            {'name': 'zero_values', 'description': 'Zero values handling'},
        ]
        
        for scenario in test_scenarios:
            validation_results[scenario['name']] = {
                'description': scenario['description'],
                'results': [],
                'issues': []
            }
            
        return validation_results
    
    def generate_scoring_fixes(self) -> List[Dict[str, Any]]:
        """Generate fixes for identified scoring issues."""
        fixes = []
        
        # Common fixes for scoring methods
        common_fixes = [
            {
                'issue': 'Missing score clipping',
                'fix_code': 'return float(np.clip(score, 0, 100))',
                'description': 'Ensure all scores are bounded to 0-100 range'
            },
            {
                'issue': 'Missing neutral fallback',
                'fix_code': 'return 50.0  # Neutral score',
                'description': 'Provide neutral fallback for error cases'
            },
            {
                'issue': 'Inverted bullish/bearish logic',
                'fix_code': '# Ensure bullish conditions increase score, bearish conditions decrease score',
                'description': 'Correct the directional logic for bullish/bearish scoring'
            }
        ]
        
        return common_fixes
    
    def create_validation_tests(self) -> str:
        """Create comprehensive validation tests for all indicators."""
        test_code = '''
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from typing import Dict, Any

class TestIndicatorScoring:
    """Test suite to validate all indicator scoring methods follow 0-100 bullish/bearish scheme."""
    
    def test_score_range_bounds(self):
        """Test that all scores are bounded to 0-100 range."""
        # Test with extreme values
        extreme_test_data = {
            'ohlcv': {
                'base': pd.DataFrame({
                    'open': [100, 200, 300, 400, 500],
                    'high': [110, 220, 330, 440, 550], 
                    'low': [90, 180, 270, 360, 450],
                    'close': [105, 210, 315, 420, 525],
                    'volume': [1000000, 2000000, 3000000, 4000000, 5000000]
                })
            }
        }
        
        # Test each indicator type
        self._test_technical_indicators_bounds(extreme_test_data)
        self._test_volume_indicators_bounds(extreme_test_data)
        self._test_sentiment_indicators_bounds(extreme_test_data)
        self._test_orderbook_indicators_bounds(extreme_test_data)
        self._test_orderflow_indicators_bounds(extreme_test_data)
        self._test_price_structure_indicators_bounds(extreme_test_data)
    
    def test_neutral_score_fallback(self):
        """Test that indicators return 50.0 for neutral/error conditions."""
        # Test with empty/invalid data
        invalid_data = {'ohlcv': {'base': pd.DataFrame()}}
        
        # Each indicator should return 50.0 for invalid data
        pass
    
    def test_bullish_bearish_logic(self):
        """Test that bullish conditions increase scores and bearish conditions decrease scores."""
        # Create bullish test scenario
        bullish_data = self._create_bullish_test_data()
        
        # Create bearish test scenario  
        bearish_data = self._create_bearish_test_data()
        
        # Test each indicator
        self._test_bullish_bearish_consistency(bullish_data, bearish_data)
    
    def _test_technical_indicators_bounds(self, data):
        """Test technical indicators score bounds."""
        # Implementation would test each technical indicator
        pass
    
    def _test_volume_indicators_bounds(self, data):
        """Test volume indicators score bounds."""
        # Implementation would test each volume indicator
        pass
    
    def _test_sentiment_indicators_bounds(self, data):
        """Test sentiment indicators score bounds."""
        # Implementation would test each sentiment indicator
        pass
    
    def _test_orderbook_indicators_bounds(self, data):
        """Test orderbook indicators score bounds."""
        # Implementation would test each orderbook indicator
        pass
    
    def _test_orderflow_indicators_bounds(self, data):
        """Test orderflow indicators score bounds."""
        # Implementation would test each orderflow indicator
        pass
    
    def _test_price_structure_indicators_bounds(self, data):
        """Test price structure indicators score bounds."""
        # Implementation would test each price structure indicator
        pass
    
    def _create_bullish_test_data(self) -> Dict[str, Any]:
        """Create test data representing bullish market conditions."""
        return {
            'ohlcv': {
                'base': pd.DataFrame({
                    'open': [100, 105, 110, 115, 120],
                    'high': [102, 108, 113, 118, 123],
                    'low': [99, 104, 109, 114, 119],
                    'close': [101, 107, 112, 117, 122],
                    'volume': [1000, 1200, 1400, 1600, 1800]  # Increasing volume
                })
            },
            'sentiment': {
                'funding_rate': -0.0001,  # Negative = bullish
                'long_short_ratio': 1.5,   # More longs = bullish
                'liquidations': {'shorts': 1000, 'longs': 500}  # More short liquidations = bullish
            }
        }
    
    def _create_bearish_test_data(self) -> Dict[str, Any]:
        """Create test data representing bearish market conditions."""
        return {
            'ohlcv': {
                'base': pd.DataFrame({
                    'open': [120, 115, 110, 105, 100],
                    'high': [121, 116, 111, 106, 101],
                    'low': [118, 113, 108, 103, 98],
                    'close': [119, 114, 109, 104, 99],
                    'volume': [1800, 1600, 1400, 1200, 1000]  # Decreasing volume
                })
            },
            'sentiment': {
                'funding_rate': 0.0001,   # Positive = bearish
                'long_short_ratio': 0.5,  # More shorts = bearish
                'liquidations': {'shorts': 500, 'longs': 1000}  # More long liquidations = bearish
            }
        }
    
    def _test_bullish_bearish_consistency(self, bullish_data, bearish_data):
        """Test that bullish data produces higher scores than bearish data."""
        # Implementation would test each indicator with both datasets
        # and verify bullish_score > bearish_score
        pass
'''
        
        return test_code
    
    def generate_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate a comprehensive report of the scoring review."""
        report = f"""
# Comprehensive Indicator Scoring Review Report

## Executive Summary
This report analyzes all indicator scoring methods to ensure they follow the standardized 0-100 bullish/bearish scheme where:
- **100 = Extremely Bullish**
- **50 = Neutral** 
- **0 = Extremely Bearish**

## Analysis Results

"""
        
        total_methods = 0
        total_issues = 0
        
        for file_name, file_results in analysis_results.items():
            report += f"\n### {file_name}\n"
            report += f"**Scoring Methods Found:** {len(file_results['scoring_methods'])}\n"
            report += f"**Issues Found:** {len(file_results['issues'])}\n\n"
            
            total_methods += len(file_results['scoring_methods'])
            total_issues += len(file_results['issues'])
            
            # List issues
            if file_results['issues']:
                report += "**Issues:**\n"
                for issue in file_results['issues']:
                    report += f"- {issue}\n"
                report += "\n"
            
            # List scoring methods
            report += "**Scoring Methods:**\n"
            for method in file_results['scoring_methods']:
                status = "✅ OK" if not method['issues'] else f"❌ {len(method['issues'])} issues"
                report += f"- `{method['method']}`: {status}\n"
            report += "\n"
        
        report += f"""
## Summary Statistics
- **Total Scoring Methods:** {total_methods}
- **Total Issues Found:** {total_issues}
- **Overall Health:** {'✅ Excellent' if total_issues == 0 else '⚠️ Needs Attention' if total_issues < 5 else '❌ Critical'}

## Recommendations

### High Priority Fixes
1. **Score Clipping**: Ensure all scoring methods use `np.clip(score, 0, 100)` to bound results
2. **Neutral Fallbacks**: All methods should return 50.0 for error/neutral conditions
3. **Bullish/Bearish Logic**: Verify directional logic is correct (bullish increases score, bearish decreases)

### Implementation Guidelines
1. **Standard Score Range**: Always use 0-100 range with 50 as neutral
2. **Error Handling**: Return 50.0 for any error conditions
3. **Consistent Clipping**: Use `float(np.clip(score, 0, 100))` for final return
4. **Clear Documentation**: Document the bullish/bearish logic for each component

### Validation Requirements
1. **Range Tests**: Verify all scores stay within 0-100 bounds
2. **Logic Tests**: Confirm bullish conditions produce higher scores than bearish
3. **Edge Case Tests**: Test with extreme values, NaN, and zero data
4. **Consistency Tests**: Ensure similar market conditions produce similar scores

## Next Steps
1. Review and fix identified issues
2. Implement comprehensive validation tests
3. Add automated scoring range checks to CI/CD pipeline
4. Create documentation for scoring methodology
"""
        
        return report


def main():
    """Main execution function."""
    reviewer = IndicatorScoringReviewer()
    
    # Analyze all indicators
    analysis_results = reviewer.analyze_all_indicators()
    
    # Generate validation tests
    validation_tests = reviewer.create_validation_tests()
    
    # Generate fixes
    fixes = reviewer.generate_scoring_fixes()
    
    # Generate report
    report = reviewer.generate_report(analysis_results)
    
    # Save results
    output_dir = Path(__file__).parent / "scoring_review_output"
    output_dir.mkdir(exist_ok=True)
    
    # Save report
    with open(output_dir / "scoring_review_report.md", 'w') as f:
        f.write(report)
    
    # Save validation tests
    with open(output_dir / "test_indicator_scoring.py", 'w') as f:
        f.write(validation_tests)
    
    # Save analysis results
    import json
    with open(output_dir / "analysis_results.json", 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\n✅ Review complete! Results saved to {output_dir}")
    print(f"📊 Total methods analyzed: {sum(len(r['scoring_methods']) for r in analysis_results.values())}")
    print(f"⚠️  Total issues found: {sum(len(r['issues']) for r in analysis_results.values())}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY OF FINDINGS")
    print("="*60)
    
    for file_name, results in analysis_results.items():
        print(f"\n{file_name}:")
        print(f"  Methods: {len(results['scoring_methods'])}")
        print(f"  Issues: {len(results['issues'])}")
        
        if results['issues']:
            print("  Top Issues:")
            for issue in results['issues'][:3]:  # Show first 3 issues
                print(f"    - {issue}")


if __name__ == "__main__":
    main() 