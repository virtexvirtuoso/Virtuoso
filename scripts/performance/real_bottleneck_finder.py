#!/usr/bin/env python3
"""
Real Bottleneck Finder

This script looks for actual performance bottlenecks that matter in the codebase.
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

class RealBottleneckFinder:
    """Find actual performance bottlenecks that impact system performance."""
    
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.real_issues = []
        
    def find_pandas_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find real pandas performance issues."""
        issues = []
        
        # Search for pandas bottlenecks
        pandas_patterns = [
            (r'\.iterrows\(\)', 'iterrows() is extremely slow - use vectorization'),
            (r'for.*\.iloc\[', 'iloc in loop - vectorize or use .values'),
            (r'for.*\.loc\[', 'loc in loop - vectorize or use boolean indexing'),
            (r'pd\.concat\([^)]*for\s', 'concat in comprehension - collect first then concat'),
            (r'\.apply\(lambda.*\+.*\)', 'apply with complex lambda - consider vectorization'),
            (r'\.rolling\(.*\)\.apply\(', 'rolling.apply() - consider using built-in functions'),
        ]
        
        for file_path in self.src_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines, 1):
                    for pattern, message in pandas_patterns:
                        if re.search(pattern, line):
                            issues.append({
                                'type': 'pandas_bottleneck',
                                'file': str(file_path),
                                'line': i,
                                'severity': 'high',
                                'issue': message,
                                'code': line.strip(),
                                'pattern': pattern
                            })
            except Exception:
                continue
                
        return issues
    
    def find_loop_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find real loop performance issues."""
        issues = []
        
        loop_patterns = [
            (r'for.*range\((\d+)\)', 'Large range loop'),
            (r'while.*len\(.*\)\s*>', 'While loop with len() - consider for loop'),
            (r'for.*\.keys\(\):', 'Iterating over .keys() - iterate directly'),
            (r'for.*in.*\.values\(\).*if', 'Filter in loop - use dict comprehension'),
        ]
        
        for file_path in self.src_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines, 1):
                    # Check for nested loops (real complexity issue)
                    if re.search(r'^\s*for\s+.*:\s*$', line):
                        # Look ahead for nested loops
                        indent_level = len(line) - len(line.lstrip())
                        for j in range(i, min(i + 20, len(lines))):
                            next_line = lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            if (next_indent > indent_level and 
                                re.search(r'for\s+.*:\s*$', next_line)):
                                issues.append({
                                    'type': 'nested_loop',
                                    'file': str(file_path),
                                    'line': i,
                                    'severity': 'high',
                                    'issue': 'Nested loops - potential O(n²) complexity',
                                    'code': f'{line.strip()} ... {next_line.strip()}'
                                })
                                break
                    
                    # Check specific patterns
                    for pattern, message in loop_patterns:
                        match = re.search(pattern, line)
                        if match:
                            severity = 'high'
                            if 'range(' in pattern:
                                try:
                                    range_size = int(match.group(1))
                                    if range_size < 100:
                                        continue  # Skip small ranges
                                    severity = 'high' if range_size > 10000 else 'medium'
                                    message = f'{message} ({range_size} iterations)'
                                except (ValueError, IndexError):
                                    continue
                            
                            issues.append({
                                'type': 'loop_bottleneck',
                                'file': str(file_path),
                                'line': i,
                                'severity': severity,
                                'issue': message,
                                'code': line.strip()
                            })
            except Exception:
                continue
                
        return issues
    
    def find_io_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find real I/O bottlenecks."""
        issues = []
        
        # Only check files that likely have async functions
        async_files = []
        for file_path in self.src_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'async def' in content:
                        async_files.append((file_path, content))
            except Exception:
                continue
        
        blocking_patterns = [
            (r'time\.sleep\(', 'Blocking sleep in async context'),
            (r'requests\.(?:get|post|put|delete)', 'Synchronous HTTP request'),
            (r'json\.dump\([^,]*,\s*open\(', 'Synchronous JSON file write'),
            (r'json\.load\(open\(', 'Synchronous JSON file read'),
            (r'psutil\.', 'Blocking psutil operations'),
            (r'subprocess\.run\((?!.*async)', 'Blocking subprocess call'),
        ]
        
        for file_path, content in async_files:
            lines = content.split('\n')
            
            # Find async functions
            async_functions = []
            for i, line in enumerate(lines):
                if re.match(r'\s*async def ', line):
                    # Find the end of this function
                    indent = len(line) - len(line.lstrip())
                    end_line = len(lines)
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if (next_line.strip() and 
                            len(next_line) - len(next_line.lstrip()) <= indent):
                            end_line = j
                            break
                    async_functions.append((i, end_line))
            
            # Check for blocking operations in async functions
            for start, end in async_functions:
                for line_num in range(start, end):
                    line = lines[line_num]
                    for pattern, message in blocking_patterns:
                        if re.search(pattern, line):
                            issues.append({
                                'type': 'blocking_in_async',
                                'file': str(file_path),
                                'line': line_num + 1,
                                'severity': 'high',
                                'issue': message,
                                'code': line.strip()
                            })
        
        return issues
    
    def find_memory_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find real memory bottlenecks."""
        issues = []
        
        memory_patterns = [
            (r'\[.*for.*in.*range\((\d+)\)', 'Large list comprehension'),
            (r'pd\.read_csv\([^)]*\)(?!.*chunksize)', 'Reading entire CSV without chunking'),
            (r'\.values\.tolist\(\)', 'Converting large DataFrame to list'),
            (r'np\.zeros\(\((\d+)', 'Large numpy array allocation'),
            (r'\.copy\(\).*\.copy\(\)', 'Multiple DataFrame copies'),
        ]
        
        for file_path in self.src_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines, 1):
                    for pattern, message in memory_patterns:
                        match = re.search(pattern, line)
                        if match:
                            severity = 'medium'
                            
                            # Check for large allocations
                            if 'range(' in pattern or 'zeros(' in pattern:
                                try:
                                    size = int(match.group(1))
                                    if size < 1000:
                                        continue
                                    severity = 'high' if size > 100000 else 'medium'
                                    message = f'{message} (size: {size})'
                                except (ValueError, IndexError):
                                    continue
                            
                            issues.append({
                                'type': 'memory_bottleneck',
                                'file': str(file_path),
                                'line': i,
                                'severity': severity,
                                'issue': message,
                                'code': line.strip()
                            })
            except Exception:
                continue
                
        return issues
    
    def find_calculation_bottlenecks(self) -> List[Dict[str, Any]]:
        """Find computational bottlenecks."""
        issues = []
        
        calc_patterns = [
            (r'\.sort\(.*key=lambda.*\)', 'Complex sorting with lambda'),
            (r'sorted\(.*key=lambda.*\)', 'Complex sorting with lambda'),
            (r'\.groupby\(.*\)\.apply\(', 'GroupBy with apply - consider agg()'),
            (r'np\.linalg\.', 'Linear algebra operations - check if needed'),
            (r'scipy\.optimize\.', 'Optimization algorithms - potentially slow'),
            (r'talib\.', 'TA-Lib calculations - check caching'),
        ]
        
        for file_path in self.src_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines, 1):
                    for pattern, message in calc_patterns:
                        if re.search(pattern, line):
                            issues.append({
                                'type': 'calculation_bottleneck',
                                'file': str(file_path),
                                'line': i,
                                'severity': 'medium',
                                'issue': message,
                                'code': line.strip()
                            })
            except Exception:
                continue
                
        return issues
    
    def analyze_all_bottlenecks(self) -> List[Dict[str, Any]]:
        """Run all bottleneck analyses."""
        all_issues = []
        
        print("🔍 Looking for pandas bottlenecks...")
        all_issues.extend(self.find_pandas_bottlenecks())
        
        print("🔍 Looking for loop bottlenecks...")
        all_issues.extend(self.find_loop_bottlenecks())
        
        print("🔍 Looking for I/O bottlenecks...")
        all_issues.extend(self.find_io_bottlenecks())
        
        print("🔍 Looking for memory bottlenecks...")
        all_issues.extend(self.find_memory_bottlenecks())
        
        print("🔍 Looking for calculation bottlenecks...")
        all_issues.extend(self.find_calculation_bottlenecks())
        
        return all_issues
    
    def generate_actionable_report(self, issues: List[Dict[str, Any]]) -> str:
        """Generate an actionable performance report."""
        # Remove duplicates and sort by severity
        unique_issues = []
        seen = set()
        for issue in issues:
            key = (issue['file'], issue['line'], issue['type'])
            if key not in seen:
                unique_issues.append(issue)
                seen.add(key)
        
        # Sort by severity and potential impact
        unique_issues.sort(key=lambda x: (
            0 if x['severity'] == 'high' else 1,
            x['type'],
            x['file']
        ))
        
        report = []
        report.append("# Real Performance Bottlenecks Report\n")
        report.append(f"Found {len(unique_issues)} real performance issues\n")
        
        # Summary
        high_priority = [i for i in unique_issues if i['severity'] == 'high']
        medium_priority = [i for i in unique_issues if i['severity'] == 'medium']
        
        report.append("## Priority Summary")
        report.append(f"- 🔴 High Priority: {len(high_priority)} (fix these first!)")
        report.append(f"- 🟡 Medium Priority: {len(medium_priority)}")
        report.append("")
        
        # Top issues by type
        type_counts = {}
        for issue in unique_issues:
            type_counts[issue['type']] = type_counts.get(issue['type'], 0) + 1
        
        report.append("## Issues by Category")
        for issue_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {issue_type}: {count}")
        report.append("")
        
        # High priority issues first
        if high_priority:
            report.append("## 🔴 High Priority Issues (Fix These First!)")
            report.append("")
            
            current_file = None
            for issue in high_priority:
                if issue['file'] != current_file:
                    current_file = issue['file']
                    relative_path = Path(current_file).name  # Just use filename
                    report.append(f"### {relative_path}")
                    report.append("")
                
                report.append(f"**Line {issue['line']}** - {issue['type']}")
                report.append(f"- Issue: {issue['issue']}")
                report.append(f"- Code: `{issue['code']}`")
                report.append("")
        
        # Recommendations
        report.append("## 💡 Optimization Recommendations")
        report.append("")
        
        recommendations = {
            'pandas_bottleneck': [
                "Replace .iterrows() with vectorized operations",
                "Use .values or .to_numpy() for numerical operations",
                "Batch operations instead of row-by-row processing"
            ],
            'nested_loop': [
                "Consider using numpy operations for numerical data",
                "Use dictionary lookups instead of nested searches",
                "Implement early break conditions where possible"
            ],
            'blocking_in_async': [
                "Use asyncio.sleep() instead of time.sleep()",
                "Replace requests with aiohttp for HTTP calls",
                "Use asyncio.run_in_executor() for blocking operations"
            ],
            'memory_bottleneck': [
                "Use generators instead of large list comprehensions",
                "Process data in chunks for large files",
                "Consider using numpy arrays for numerical data"
            ]
        }
        
        for issue_type, recs in recommendations.items():
            if any(i['type'] == issue_type for i in unique_issues):
                report.append(f"### {issue_type}")
                for rec in recs:
                    report.append(f"- {rec}")
                report.append("")
        
        return '\n'.join(report)

def main():
    """Main entry point."""
    finder = RealBottleneckFinder()
    
    print("🚀 Starting real bottleneck analysis...")
    
    # Find all real bottlenecks
    issues = finder.analyze_all_bottlenecks()
    
    # Generate actionable report
    report = finder.generate_actionable_report(issues)
    
    # Save report
    output_dir = Path("performance_analysis")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / "real_bottlenecks_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Analysis complete! Found {len(issues)} real performance issues.")
    print(f"📄 Report saved to: {report_path}")
    
    # Show immediate actionable items
    high_priority = [i for i in issues if i['severity'] == 'high']
    if high_priority:
        print(f"\n🔴 {len(high_priority)} HIGH PRIORITY issues found:")
        
        # Group by type for summary
        type_counts = {}
        for issue in high_priority:
            type_counts[issue['type']] = type_counts.get(issue['type'], 0) + 1
        
        for issue_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {issue_type}: {count} issues")
        
        print(f"\n🎯 Focus on these files first:")
        file_counts = {}
        for issue in high_priority[:10]:  # Top 10
            file_path = Path(issue['file']).name
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
        
        for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {file_path}: {count} issues")
    else:
        print("\n🎉 No high-priority performance issues found!")

if __name__ == "__main__":
    main()