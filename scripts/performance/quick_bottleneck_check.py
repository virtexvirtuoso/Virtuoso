#!/usr/bin/env python3
"""
Quick Bottleneck Analysis

This script analyzes the codebase for common performance bottlenecks without running the code.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import subprocess

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class StaticBottleneckAnalyzer:
    """Analyze code for potential bottlenecks without execution."""
    
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.issues = []
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the source directory."""
        return list(self.src_dir.rglob("*.py"))
    
    def analyze_file_for_bottlenecks(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single file for potential bottlenecks."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for common bottleneck patterns
            issues.extend(self._check_loops(content, file_path))
            issues.extend(self._check_pandas_operations(content, file_path))
            issues.extend(self._check_io_operations(content, file_path))
            issues.extend(self._check_api_calls(content, file_path))
            issues.extend(self._check_blocking_operations(content, file_path))
            issues.extend(self._check_memory_issues(content, file_path))
            
        except Exception as e:
            issues.append({
                'type': 'parse_error',
                'file': str(file_path),
                'line': 0,
                'issue': f"Could not parse file: {e}",
                'severity': 'low'
            })
            
        return issues
    
    def _check_loops(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for potentially slow loops."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Nested loops
            if re.search(r'^\s+for\s+.*:\s*$', line) and i < len(lines):
                # Check if next few lines contain another for loop
                for j in range(i, min(i + 10, len(lines))):
                    if re.search(r'^\s+\s+for\s+.*:\s*$', lines[j]):
                        issues.append({
                            'type': 'nested_loops',
                            'file': str(file_path),
                            'line': i,
                            'issue': 'Nested loops detected - potential O(n²) complexity',
                            'severity': 'medium',
                            'code': line.strip()
                        })
                        break
            
            # DataFrame operations in loops
            if re.search(r'for\s+.*:\s*$', line) and 'df[' in line:
                issues.append({
                    'type': 'dataframe_in_loop',
                    'file': str(file_path),
                    'line': i,
                    'issue': 'DataFrame operations in loop - consider vectorization',
                    'severity': 'high',
                    'code': line.strip()
                })
            
            # Large range loops
            range_match = re.search(r'for\s+\w+\s+in\s+range\((\d+)\)', line)
            if range_match and int(range_match.group(1)) > 1000:
                issues.append({
                    'type': 'large_range_loop',
                    'file': str(file_path),
                    'line': i,
                    'issue': f'Large range loop ({range_match.group(1)} iterations)',
                    'severity': 'medium',
                    'code': line.strip()
                })
        
        return issues
    
    def _check_pandas_operations(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for inefficient pandas operations."""
        issues = []
        lines = content.split('\n')
        
        patterns = {
            r'\.iterrows\(\)': 'iterrows() is slow - consider vectorization',
            r'\.apply\(lambda': 'apply(lambda) can be slow - consider vectorized operations',
            r'pd\.concat\(.*for.*\)': 'concat in loop - use pd.concat on list instead',
            r'\.loc\[.*for.*\]': 'loc in loop - consider vectorized indexing',
            r'\.copy\(\).*\.copy\(\)': 'Multiple copy() calls - unnecessary memory usage'
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        'type': 'pandas_inefficiency',
                        'file': str(file_path),
                        'line': i,
                        'issue': message,
                        'severity': 'high',
                        'code': line.strip()
                    })
        
        return issues
    
    def _check_io_operations(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for blocking I/O operations."""
        issues = []
        lines = content.split('\n')
        
        patterns = {
            r'open\(.*\)(?!.*async)': 'Synchronous file I/O - consider async alternatives',
            r'json\.dump\(.*open\(': 'Synchronous JSON file operations',
            r'json\.load\(.*open\(': 'Synchronous JSON file operations',
            r'requests\.get\(': 'Synchronous HTTP request - consider aiohttp',
            r'requests\.post\(': 'Synchronous HTTP request - consider aiohttp',
            r'time\.sleep\(': 'Blocking sleep - use asyncio.sleep in async code'
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns.items():
                if re.search(pattern, line):
                    # Check if we're in an async function
                    is_async_context = self._is_in_async_function(lines, i)
                    severity = 'high' if is_async_context else 'medium'
                    
                    issues.append({
                        'type': 'blocking_io',
                        'file': str(file_path),
                        'line': i,
                        'issue': message + (' (in async context!)' if is_async_context else ''),
                        'severity': severity,
                        'code': line.strip()
                    })
        
        return issues
    
    def _check_api_calls(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for potentially slow API calls."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # API calls in loops
            if ('for ' in line or 'while ' in line) and i < len(lines):
                for j in range(i, min(i + 20, len(lines))):
                    if any(pattern in lines[j] for pattern in ['requests.', 'aiohttp.', '.get(', '.post(']):
                        issues.append({
                            'type': 'api_in_loop',
                            'file': str(file_path),
                            'line': j + 1,
                            'issue': 'API call in loop - consider batching or rate limiting',
                            'severity': 'high',
                            'code': lines[j].strip()
                        })
                        break
            
            # Multiple sequential API calls
            if any(pattern in line for pattern in ['await ', 'requests.', 'aiohttp.']):
                # Check next few lines for more API calls
                api_count = 1
                for j in range(i, min(i + 5, len(lines))):
                    if any(pattern in lines[j] for pattern in ['await ', 'requests.', '.get(', '.post(']):
                        api_count += 1
                
                if api_count > 3:
                    issues.append({
                        'type': 'sequential_api_calls',
                        'file': str(file_path),
                        'line': i,
                        'issue': f'Multiple sequential API calls ({api_count}) - consider concurrent execution',
                        'severity': 'medium',
                        'code': line.strip()
                    })
        
        return issues
    
    def _check_blocking_operations(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for blocking operations in async contexts."""
        issues = []
        lines = content.split('\n')
        
        blocking_patterns = {
            r'psutil\.': 'psutil operations can be blocking',
            r'os\.system\(': 'os.system() is blocking',
            r'subprocess\.run\(': 'subprocess.run() without async',
            r'\.sort\(.*key=lambda.*\)': 'Complex sorting operations',
            r'hashlib\.': 'Cryptographic operations can be slow'
        }
        
        for i, line in enumerate(lines, 1):
            if self._is_in_async_function(lines, i):
                for pattern, message in blocking_patterns.items():
                    if re.search(pattern, line):
                        issues.append({
                            'type': 'blocking_in_async',
                            'file': str(file_path),
                            'line': i,
                            'issue': f'{message} (in async function)',
                            'severity': 'high',
                            'code': line.strip()
                        })
        
        return issues
    
    def _check_memory_issues(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for potential memory issues."""
        issues = []
        lines = content.split('\n')
        
        patterns = {
            r'\[\s*.*\s+for\s+.*\s+in\s+.*\]': 'Large list comprehension - consider generator',
            r'\.tolist\(\)': 'Converting to list - may use excessive memory',
            r'pd\.read_csv\(.*\)(?!.*chunksize)': 'Reading entire CSV - consider chunking for large files',
            r'\.values\.tolist\(\)': 'DataFrame to list conversion - memory intensive'
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        'type': 'memory_concern',
                        'file': str(file_path),
                        'line': i,
                        'issue': message,
                        'severity': 'medium',
                        'code': line.strip()
                    })
        
        return issues
    
    def _is_in_async_function(self, lines: List[str], line_num: int) -> bool:
        """Check if a line is inside an async function."""
        for i in range(line_num - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('async def '):
                return True
            elif line.startswith('def ') and not line.startswith('async def'):
                return False
        return False
    
    def analyze_all_files(self) -> List[Dict[str, Any]]:
        """Analyze all Python files for bottlenecks."""
        all_issues = []
        files = self.find_python_files()
        
        print(f"Analyzing {len(files)} Python files...")
        
        for file_path in files:
            issues = self.analyze_file_for_bottlenecks(file_path)
            all_issues.extend(issues)
        
        return all_issues
    
    def generate_report(self, issues: List[Dict[str, Any]]) -> str:
        """Generate a bottleneck analysis report."""
        # Sort by severity and file
        issues.sort(key=lambda x: (x['severity'], x['file'], x['line']))
        
        report = []
        report.append("# Static Bottleneck Analysis Report\n")
        report.append(f"Total issues found: {len(issues)}\n")
        
        # Summary by severity
        severity_counts = {}
        for issue in issues:
            severity = issue['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        report.append("## Summary by Severity")
        for severity in ['high', 'medium', 'low']:
            count = severity_counts.get(severity, 0)
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
            report.append(f"- {emoji} {severity.title()}: {count}")
        report.append("")
        
        # Summary by type
        type_counts = {}
        for issue in issues:
            issue_type = issue['type']
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
        
        report.append("## Summary by Type")
        for issue_type, count in sorted(type_counts.items()):
            report.append(f"- {issue_type}: {count}")
        report.append("")
        
        # Detailed issues
        report.append("## Detailed Issues")
        
        current_file = None
        for issue in issues:
            if issue['file'] != current_file:
                current_file = issue['file']
                report.append(f"\n### {current_file}")
            
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[issue['severity']]
            report.append(f"\n{severity_emoji} **Line {issue['line']}** ({issue['type']})")
            report.append(f"- Issue: {issue['issue']}")
            if 'code' in issue:
                report.append(f"- Code: `{issue['code']}`")
        
        return '\n'.join(report)

def main():
    """Main entry point."""
    analyzer = StaticBottleneckAnalyzer()
    
    print("🔍 Starting static bottleneck analysis...")
    
    # Analyze all files
    issues = analyzer.analyze_all_files()
    
    # Generate report
    report = analyzer.generate_report(issues)
    
    # Save report
    output_dir = Path("performance_analysis")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / "static_bottleneck_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Analysis complete! Found {len(issues)} potential issues.")
    print(f"📄 Report saved to: {report_path}")
    
    # Print summary
    if issues:
        high_priority = [i for i in issues if i['severity'] == 'high']
        if high_priority:
            print(f"\n🔴 {len(high_priority)} high-priority issues found:")
            for issue in high_priority[:5]:  # Show top 5
                print(f"   - {Path(issue['file']).name}:{issue['line']} - {issue['issue']}")
        else:
            print("\n✅ No high-priority issues found!")
    else:
        print("\n🎉 No issues found - code looks clean!")

if __name__ == "__main__":
    main()