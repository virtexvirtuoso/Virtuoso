#!/usr/bin/env python3
"""
Comprehensive Indicator Scoring Review Script

This script analyzes all indicator scoring methods to ensure they follow the standardized 
0-100 bullish/bearish scoring system where:
- 100 = extremely bullish
- 50 = neutral  
- 0 = extremely bearish

The script will:
1. Find all scoring methods in indicator files
2. Analyze their implementation for consistency
3. Check for proper score clipping (0-100 range)
4. Verify neutral fallback behavior
5. Generate a comprehensive report
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import ast
import inspect

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class ScoringMethodAnalyzer:
    """Analyzes indicator scoring methods for consistency."""
    
    def __init__(self):
        self.indicators_dir = Path(__file__).parent.parent / "src" / "indicators"
        self.results = {}
        self.issues = []
        
    def analyze_all_indicators(self) -> Dict[str, Any]:
        """Analyze all indicator files for scoring method consistency."""
        print("🔍 Starting comprehensive indicator scoring review...")
        print("=" * 70)
        
        # Get all indicator files
        indicator_files = list(self.indicators_dir.glob("*_indicators.py"))
        
        for file_path in indicator_files:
            if file_path.name == "base_indicator.py":
                continue
                
            print(f"\n📊 Analyzing {file_path.name}...")
            self.analyze_indicator_file(file_path)
        
        # Generate summary
        self.generate_summary()
        return self.results
    
    def analyze_indicator_file(self, file_path: Path) -> None:
        """Analyze a single indicator file for scoring methods."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all scoring methods
            scoring_methods = self.find_scoring_methods(content, file_path.name)
            
            # Analyze each method
            file_issues = []
            for method_name, method_content, line_num in scoring_methods:
                issues = self.analyze_scoring_method(method_name, method_content, file_path.name, line_num)
                file_issues.extend(issues)
            
            self.results[file_path.name] = {
                'total_methods': len(scoring_methods),
                'methods': [m[0] for m in scoring_methods],
                'issues': file_issues,
                'issues_count': len(file_issues)
            }
            
            print(f"   ✅ Found {len(scoring_methods)} scoring methods")
            print(f"   ⚠️  Found {len(file_issues)} issues")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {file_path.name}: {str(e)}")
            self.results[file_path.name] = {
                'error': str(e),
                'total_methods': 0,
                'methods': [],
                'issues': [],
                'issues_count': 0
            }
    
    def find_scoring_methods(self, content: str, filename: str) -> List[Tuple[str, str, int]]:
        """Find all scoring methods in the file content."""
        methods = []
        
        # Pattern to match scoring methods
        pattern = r'def\s+(_calculate_.*?_score|_.*?_score)\s*\([^)]*\)\s*->\s*float:'
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                method_name = re.search(r'def\s+(\w+)', line).group(1)
                
                # Extract the full method content
                method_content = self.extract_method_content(lines, i)
                methods.append((method_name, method_content, i + 1))
        
        return methods
    
    def extract_method_content(self, lines: List[str], start_line: int) -> str:
        """Extract the full content of a method."""
        method_lines = [lines[start_line]]
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                method_lines.append(line)
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
            # If we encounter a line with same or less indentation that's not empty, method ends
            if current_indent <= indent_level and line.strip():
                break
                
            method_lines.append(line)
        
        return '\n'.join(method_lines)
    
    def analyze_scoring_method(self, method_name: str, method_content: str, filename: str, line_num: int) -> List[Dict[str, Any]]:
        """Analyze a single scoring method for issues."""
        issues = []
        
        # Check 1: Score clipping
        if not self.has_score_clipping(method_content):
            issues.append({
                'type': 'missing_score_clipping',
                'method': method_name,
                'file': filename,
                'line': line_num,
                'description': 'Method does not use np.clip(score, 0, 100) to ensure score bounds',
                'severity': 'high'
            })
        
        # Check 2: Neutral fallback
        if not self.has_neutral_fallback(method_content):
            issues.append({
                'type': 'missing_neutral_fallback',
                'method': method_name,
                'file': filename,
                'line': line_num,
                'description': 'Method does not return 50.0 for error/neutral conditions',
                'severity': 'medium'
            })
        
        # Check 3: Score range validation
        if not self.uses_proper_score_range(method_content):
            issues.append({
                'type': 'non_standard_score_range',
                'method': method_name,
                'file': filename,
                'line': line_num,
                'description': 'Method may not use standard 0-100 score range',
                'severity': 'medium'
            })
        
        # Check 4: Bullish/bearish logic consistency
        logic_issues = self.check_bullish_bearish_logic(method_content, method_name)
        for issue in logic_issues:
            issue.update({
                'method': method_name,
                'file': filename,
                'line': line_num
            })
            issues.append(issue)
        
        return issues
    
    def has_score_clipping(self, content: str) -> bool:
        """Check if method uses proper score clipping."""
        patterns = [
            r'np\.clip\s*\(\s*\w*score\w*\s*,\s*0\s*,\s*100\s*\)',
            r'float\s*\(\s*np\.clip\s*\(\s*\w*score\w*\s*,\s*0\s*,\s*100\s*\)\s*\)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def has_neutral_fallback(self, content: str) -> bool:
        """Check if method has neutral fallback (return 50.0)."""
        patterns = [
            r'return\s+50\.0',
            r'return\s+50',
            r'score\s*=\s*50\.0',
            r'score\s*=\s*50'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def uses_proper_score_range(self, content: str) -> bool:
        """Check if method uses proper 0-100 score range."""
        # Look for score assignments and calculations
        score_patterns = [
            r'score\s*=\s*\d+\.?\d*',
            r'return\s+\d+\.?\d*',
            r'score\s*[+\-*/]\s*\d+\.?\d*'
        ]
        
        # Extract all numeric values used with scores
        numbers = []
        for pattern in score_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                nums = re.findall(r'\d+\.?\d*', match)
                numbers.extend([float(n) for n in nums])
        
        # Check if numbers are generally in 0-100 range
        if not numbers:
            return False
            
        # Allow some flexibility but flag if most numbers are outside 0-100
        out_of_range = sum(1 for n in numbers if n < 0 or n > 100)
        return out_of_range / len(numbers) < 0.5
    
    def check_bullish_bearish_logic(self, content: str, method_name: str) -> List[Dict[str, Any]]:
        """Check for consistent bullish/bearish logic."""
        issues = []
        
        # Look for comments or variable names that suggest bullish/bearish logic
        bullish_indicators = ['bullish', 'positive', 'up', 'high', 'strong', 'buy']
        bearish_indicators = ['bearish', 'negative', 'down', 'low', 'weak', 'sell']
        
        lines = content.lower().split('\n')
        
        for i, line in enumerate(lines):
            # Check for potential logic inconsistencies
            if any(indicator in line for indicator in bullish_indicators):
                # Look for score assignments in the same or nearby lines
                context_lines = lines[max(0, i-2):i+3]
                context = '\n'.join(context_lines)
                
                # Check if bullish conditions lead to high scores (>50)
                if 'score' in context and ('= 0' in context or '- 50' in context):
                    issues.append({
                        'type': 'bullish_logic_inconsistency',
                        'description': f'Bullish condition may lead to low score (line {i+1})',
                        'severity': 'medium',
                        'context': line.strip()
                    })
            
            if any(indicator in line for indicator in bearish_indicators):
                # Look for score assignments in the same or nearby lines
                context_lines = lines[max(0, i-2):i+3]
                context = '\n'.join(context_lines)
                
                # Check if bearish conditions lead to low scores (<50)
                if 'score' in context and ('= 100' in context or '+ 50' in context):
                    issues.append({
                        'type': 'bearish_logic_inconsistency',
                        'description': f'Bearish condition may lead to high score (line {i+1})',
                        'severity': 'medium',
                        'context': line.strip()
                    })
        
        return issues
    
    def generate_summary(self) -> None:
        """Generate a comprehensive summary of the analysis."""
        print("\n" + "=" * 70)
        print("📋 COMPREHENSIVE INDICATOR SCORING REVIEW SUMMARY")
        print("=" * 70)
        
        total_files = len(self.results)
        total_methods = sum(r.get('total_methods', 0) for r in self.results.values())
        total_issues = sum(r.get('issues_count', 0) for r in self.results.values())
        
        print(f"\n📊 Overall Statistics:")
        print(f"   • Files analyzed: {total_files}")
        print(f"   • Scoring methods found: {total_methods}")
        print(f"   • Total issues found: {total_issues}")
        
        if total_issues > 0:
            print(f"\n⚠️  Issues by Type:")
            issue_types = {}
            for file_result in self.results.values():
                for issue in file_result.get('issues', []):
                    issue_type = issue['type']
                    if issue_type not in issue_types:
                        issue_types[issue_type] = 0
                    issue_types[issue_type] += 1
            
            for issue_type, count in sorted(issue_types.items()):
                print(f"   • {issue_type}: {count}")
        
        print(f"\n📁 Issues by File:")
        for filename, result in sorted(self.results.items()):
            if result.get('error'):
                print(f"   • {filename}: ERROR - {result['error']}")
            else:
                methods = result.get('total_methods', 0)
                issues = result.get('issues_count', 0)
                status = "✅" if issues == 0 else "⚠️"
                print(f"   • {filename}: {status} {methods} methods, {issues} issues")
        
        if total_issues > 0:
            print(f"\n🔧 Detailed Issues:")
            for filename, result in sorted(self.results.items()):
                if result.get('issues'):
                    print(f"\n   📄 {filename}:")
                    for issue in result['issues']:
                        severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
                        print(f"      {severity_icon} {issue['method']} (line {issue['line']})")
                        print(f"         {issue['description']}")
                        if 'context' in issue:
                            print(f"         Context: {issue['context']}")
        
        print(f"\n💡 Recommendations:")
        if total_issues > 0:
            print("   1. All scoring methods should use float(np.clip(score, 0, 100)) for return values")
            print("   2. Add neutral fallback (return 50.0) for error conditions")
            print("   3. Ensure bullish conditions lead to scores > 50, bearish to scores < 50")
            print("   4. Use consistent 0-100 scoring range throughout")
            print("   5. Add comprehensive error handling with neutral fallbacks")
        else:
            print("   ✅ All scoring methods appear to follow the standardized 0-100 system!")
        
        print("\n" + "=" * 70)

def main():
    """Main function to run the comprehensive scoring review."""
    analyzer = ScoringMethodAnalyzer()
    results = analyzer.analyze_all_indicators()
    
    print(f"\n🎯 Analysis complete! Check the detailed output above.")
    
    # Return exit code based on issues found
    total_issues = sum(r.get('issues_count', 0) for r in results.values())
    return 0 if total_issues == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 