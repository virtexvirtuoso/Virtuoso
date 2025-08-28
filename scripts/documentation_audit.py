#!/usr/bin/env python3
"""
Comprehensive Documentation Audit Tool for Virtuoso CCXT Trading System

This tool performs a thorough analysis of documentation coverage across the entire
codebase, providing detailed metrics, quality assessments, and actionable recommendations.

Author: Documentation Audit System
Date: 2025-08-28
Version: 1.0.0
"""

import ast
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from collections import defaultdict
import textwrap

class DocumentationAuditor:
    """
    A comprehensive documentation auditor that analyzes Python and Shell script files
    for documentation completeness, quality, and compliance with best practices.
    """
    
    # Documentation quality grading thresholds
    GRADE_THRESHOLDS = {
        'A': 90,  # Excellent documentation
        'B': 75,  # Good documentation
        'C': 60,  # Adequate documentation
        'D': 40,  # Poor documentation
        'F': 0    # Failing documentation
    }
    
    # File criticality patterns (files matching these are considered critical)
    CRITICAL_PATTERNS = [
        r'main\.py$',
        r'core/.*\.py$',
        r'api/.*\.py$',
        r'exchanges/.*\.py$',
        r'signal_generation/.*\.py$',
        r'monitoring/.*\.py$',
        r'dashboard.*\.py$',
        r'deploy.*\.sh$'
    ]
    
    def __init__(self, root_path: str):
        """
        Initialize the documentation auditor.
        
        Args:
            root_path: Root directory path of the project to audit
        """
        self.root_path = Path(root_path)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': 0,
            'total_lines': 0,
            'documented_lines': 0,
            'directories': defaultdict(dict),
            'critical_files': [],
            'best_documented': [],
            'worst_documented': [],
            'quality_grades': defaultdict(int),
            'file_details': {}
        }
        
    def audit_project(self) -> Dict:
        """
        Perform a comprehensive audit of the entire project.
        
        Returns:
            Dictionary containing detailed audit results
        """
        print("Starting comprehensive documentation audit...")
        
        # Analyze Python files
        python_files = list(self.root_path.rglob('*.py'))
        for py_file in python_files:
            if not self._should_skip_file(py_file):
                self._analyze_python_file(py_file)
                
        # Analyze Shell scripts
        shell_files = list(self.root_path.rglob('*.sh'))
        for sh_file in shell_files:
            if not self._should_skip_file(sh_file):
                self._analyze_shell_file(sh_file)
                
        # Calculate metrics and generate report
        self._calculate_metrics()
        self._identify_critical_files()
        self._rank_documentation_quality()
        
        return self.results
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be skipped from analysis.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be skipped, False otherwise
        """
        skip_patterns = [
            r'\.git/',
            r'__pycache__',
            r'\.pyc$',
            r'venv',
            r'\.egg-info',
            r'build/',
            r'dist/',
            r'\.coverage',
            r'\.pytest_cache'
        ]
        
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in skip_patterns)
    
    def _analyze_python_file(self, file_path: Path) -> None:
        """
        Analyze a Python file for documentation coverage.
        
        Args:
            file_path: Path to the Python file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                # Skip files with syntax errors
                return
                
            # Get relative path for reporting
            rel_path = file_path.relative_to(self.root_path)
            directory = str(rel_path.parent)
            
            # Analyze documentation
            stats = self._analyze_python_ast(tree, content)
            
            # Update results
            self.results['files_analyzed'] += 1
            self.results['total_lines'] += stats['total_lines']
            self.results['documented_lines'] += stats['documented_lines']
            
            # Store file details
            self.results['file_details'][str(rel_path)] = {
                'type': 'python',
                'stats': stats,
                'grade': self._calculate_grade(stats['coverage']),
                'critical': self._is_critical_file(str(rel_path))
            }
            
            # Update directory stats
            if directory not in self.results['directories']:
                self.results['directories'][directory] = {
                    'files': 0,
                    'documented': 0,
                    'total_lines': 0,
                    'documented_lines': 0
                }
                
            self.results['directories'][directory]['files'] += 1
            self.results['directories'][directory]['total_lines'] += stats['total_lines']
            self.results['directories'][directory]['documented_lines'] += stats['documented_lines']
            if stats['coverage'] > 60:
                self.results['directories'][directory]['documented'] += 1
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _analyze_python_ast(self, tree: ast.AST, content: str) -> Dict:
        """
        Analyze Python AST for documentation metrics.
        
        Args:
            tree: AST tree of the Python file
            content: Raw content of the file
            
        Returns:
            Dictionary containing documentation statistics
        """
        stats = {
            'total_lines': len(content.splitlines()),
            'documented_lines': 0,
            'module_docstring': False,
            'classes': {'total': 0, 'documented': 0},
            'functions': {'total': 0, 'documented': 0},
            'methods': {'total': 0, 'documented': 0},
            'coverage': 0
        }
        
        # Check module docstring
        if ast.get_docstring(tree):
            stats['module_docstring'] = True
            stats['documented_lines'] += len(ast.get_docstring(tree).splitlines())
        
        # Create a map of parent-child relationships
        parent_map = {}
        for parent in ast.walk(tree):
            if hasattr(parent, 'body'):
                for child in parent.body:
                    parent_map[child] = parent
        
        # Walk through AST nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                stats['classes']['total'] += 1
                if ast.get_docstring(node):
                    stats['classes']['documented'] += 1
                    stats['documented_lines'] += len(ast.get_docstring(node).splitlines())
                    
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Determine if it's a method or function
                parent = parent_map.get(node)
                is_method = isinstance(parent, ast.ClassDef)
                
                if is_method:
                    stats['methods']['total'] += 1
                    if ast.get_docstring(node):
                        stats['methods']['documented'] += 1
                        stats['documented_lines'] += len(ast.get_docstring(node).splitlines())
                else:
                    stats['functions']['total'] += 1
                    if ast.get_docstring(node):
                        stats['functions']['documented'] += 1
                        stats['documented_lines'] += len(ast.get_docstring(node).splitlines())
        
        # Calculate coverage percentage
        total_entities = (1 if stats['total_lines'] > 0 else 0) + \
                        stats['classes']['total'] + \
                        stats['functions']['total'] + \
                        stats['methods']['total']
        
        documented_entities = (1 if stats['module_docstring'] else 0) + \
                            stats['classes']['documented'] + \
                            stats['functions']['documented'] + \
                            stats['methods']['documented']
        
        if total_entities > 0:
            stats['coverage'] = (documented_entities / total_entities) * 100
        else:
            stats['coverage'] = 100 if stats['total_lines'] == 0 else 0
            
        return stats
    
    def _analyze_shell_file(self, file_path: Path) -> None:
        """
        Analyze a Shell script file for documentation coverage.
        
        Args:
            file_path: Path to the Shell script file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get relative path for reporting
            rel_path = file_path.relative_to(self.root_path)
            directory = str(rel_path.parent)
            
            stats = {
                'total_lines': len(lines),
                'documented_lines': 0,
                'has_header': False,
                'functions_documented': 0,
                'functions_total': 0,
                'coverage': 0
            }
            
            # Check for file header documentation
            header_lines = 0
            for i, line in enumerate(lines[:20]):  # Check first 20 lines for header
                if line.strip().startswith('#') and not line.strip().startswith('#!'):
                    header_lines += 1
                    
            if header_lines >= 3:  # At least 3 comment lines for a header
                stats['has_header'] = True
                stats['documented_lines'] += header_lines
                
            # Count functions and their documentation
            for i, line in enumerate(lines):
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\(\)', line.strip()):
                    stats['functions_total'] += 1
                    # Check if previous lines have documentation
                    if i > 0 and lines[i-1].strip().startswith('#'):
                        stats['functions_documented'] += 1
                        
            # Count all comment lines as documentation
            for line in lines:
                if line.strip().startswith('#') and not line.strip().startswith('#!'):
                    stats['documented_lines'] += 1
                    
            # Calculate coverage
            if stats['total_lines'] > 0:
                stats['coverage'] = (stats['documented_lines'] / stats['total_lines']) * 100
                
            # Update results
            self.results['files_analyzed'] += 1
            self.results['total_lines'] += stats['total_lines']
            self.results['documented_lines'] += stats['documented_lines']
            
            # Store file details
            self.results['file_details'][str(rel_path)] = {
                'type': 'shell',
                'stats': stats,
                'grade': self._calculate_grade(stats['coverage']),
                'critical': self._is_critical_file(str(rel_path))
            }
            
            # Update directory stats
            if directory not in self.results['directories']:
                self.results['directories'][directory] = {
                    'files': 0,
                    'documented': 0,
                    'total_lines': 0,
                    'documented_lines': 0
                }
                
            self.results['directories'][directory]['files'] += 1
            self.results['directories'][directory]['total_lines'] += stats['total_lines']
            self.results['directories'][directory]['documented_lines'] += stats['documented_lines']
            if stats['coverage'] > 60:
                self.results['directories'][directory]['documented'] += 1
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _calculate_grade(self, coverage: float) -> str:
        """
        Calculate documentation grade based on coverage percentage.
        
        Args:
            coverage: Coverage percentage
            
        Returns:
            Letter grade (A, B, C, D, or F)
        """
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if coverage >= threshold:
                return grade
        return 'F'
    
    def _is_critical_file(self, file_path: str) -> bool:
        """
        Determine if a file is critical based on patterns.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            True if file is critical, False otherwise
        """
        return any(re.search(pattern, file_path) for pattern in self.CRITICAL_PATTERNS)
    
    def _calculate_metrics(self) -> None:
        """Calculate overall metrics and statistics."""
        # Overall coverage
        if self.results['total_lines'] > 0:
            self.results['overall_coverage'] = (
                self.results['documented_lines'] / self.results['total_lines']
            ) * 100
        else:
            self.results['overall_coverage'] = 0
            
        # Grade distribution
        for file_details in self.results['file_details'].values():
            grade = file_details['grade']
            self.results['quality_grades'][grade] += 1
            
        # Directory coverage
        for dir_name, dir_stats in self.results['directories'].items():
            if dir_stats['total_lines'] > 0:
                dir_stats['coverage'] = (
                    dir_stats['documented_lines'] / dir_stats['total_lines']
                ) * 100
            else:
                dir_stats['coverage'] = 0
                
    def _identify_critical_files(self) -> None:
        """Identify critical files that need documentation."""
        critical_undocumented = []
        
        for file_path, details in self.results['file_details'].items():
            if details['critical'] and details['stats']['coverage'] < 60:
                critical_undocumented.append({
                    'path': file_path,
                    'coverage': details['stats']['coverage'],
                    'grade': details['grade']
                })
                
        # Sort by coverage (lowest first)
        critical_undocumented.sort(key=lambda x: x['coverage'])
        self.results['critical_files'] = critical_undocumented[:10]
        
    def _rank_documentation_quality(self) -> None:
        """Rank files by documentation quality."""
        all_files = []
        
        for file_path, details in self.results['file_details'].items():
            all_files.append({
                'path': file_path,
                'coverage': details['stats']['coverage'],
                'grade': details['grade'],
                'type': details['type']
            })
            
        # Sort by coverage
        all_files.sort(key=lambda x: x['coverage'], reverse=True)
        
        # Get best documented
        self.results['best_documented'] = [
            f for f in all_files[:10] if f['coverage'] > 80
        ]
        
        # Get worst documented (non-empty files)
        worst = [f for f in all_files if f['coverage'] < 20]
        worst.reverse()
        self.results['worst_documented'] = worst[:10]
        
    def generate_report(self) -> str:
        """
        Generate a comprehensive markdown report.
        
        Returns:
            Formatted markdown report string
        """
        report = []
        
        # Header
        report.append("# Virtuoso CCXT Trading System - Documentation Audit Report")
        report.append(f"\n**Generated:** {self.results['timestamp']}")
        report.append(f"**Total Files Analyzed:** {self.results['files_analyzed']}")
        report.append(f"**Total Lines of Code:** {self.results['total_lines']:,}")
        report.append(f"**Documented Lines:** {self.results['documented_lines']:,}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        coverage = self.results['overall_coverage']
        grade = self._calculate_grade(coverage)
        report.append(f"### Overall Documentation Coverage: {coverage:.1f}% (Grade: {grade})")
        report.append("")
        
        if coverage >= 75:
            report.append("✅ **Status:** Good documentation coverage")
        elif coverage >= 50:
            report.append("⚠️ **Status:** Moderate documentation coverage - improvements needed")
        else:
            report.append("❌ **Status:** Poor documentation coverage - immediate attention required")
        report.append("")
        
        # Grade Distribution
        report.append("### Documentation Quality Distribution")
        report.append("")
        report.append("| Grade | Count | Percentage |")
        report.append("|-------|-------|------------|")
        
        total_files = sum(self.results['quality_grades'].values())
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = self.results['quality_grades'].get(grade, 0)
            percentage = (count / total_files * 100) if total_files > 0 else 0
            bar = '█' * int(percentage / 5)
            report.append(f"| {grade} | {count} | {percentage:.1f}% {bar} |")
        report.append("")
        
        # Directory Analysis
        report.append("## Directory-Level Analysis")
        report.append("")
        report.append("| Directory | Files | Coverage | Grade | Status |")
        report.append("|-----------|-------|----------|-------|--------|")
        
        # Sort directories by coverage
        sorted_dirs = sorted(
            self.results['directories'].items(),
            key=lambda x: x[1].get('coverage', 0),
            reverse=True
        )
        
        for dir_name, stats in sorted_dirs[:15]:  # Top 15 directories
            if stats['files'] > 0:
                coverage = stats.get('coverage', 0)
                grade = self._calculate_grade(coverage)
                status = '✅' if coverage >= 75 else '⚠️' if coverage >= 50 else '❌'
                report.append(
                    f"| {dir_name} | {stats['files']} | {coverage:.1f}% | {grade} | {status} |"
                )
        report.append("")
        
        # Critical Files Needing Documentation
        report.append("## Critical Files Requiring Documentation")
        report.append("")
        report.append("**Top 10 critical files with poor documentation:**")
        report.append("")
        report.append("| File | Coverage | Grade | Priority |")
        report.append("|------|----------|-------|----------|")
        
        for file_info in self.results['critical_files']:
            priority = "🔴 Critical" if file_info['coverage'] < 20 else "🟠 High"
            report.append(
                f"| {file_info['path']} | {file_info['coverage']:.1f}% | "
                f"{file_info['grade']} | {priority} |"
            )
        report.append("")
        
        # Best Documented Files
        report.append("## Best Documented Files (Examples to Follow)")
        report.append("")
        report.append("| File | Coverage | Grade |")
        report.append("|------|----------|-------|")
        
        for file_info in self.results['best_documented']:
            report.append(
                f"| {file_info['path']} | {file_info['coverage']:.1f}% | {file_info['grade']} |"
            )
        report.append("")
        
        # Worst Documented Files
        report.append("## Files Needing Immediate Attention")
        report.append("")
        report.append("| File | Coverage | Type | Action Required |")
        report.append("|------|----------|------|-----------------|")
        
        for file_info in self.results['worst_documented']:
            action = "Add docstrings" if file_info['type'] == 'python' else "Add comments"
            report.append(
                f"| {file_info['path']} | {file_info['coverage']:.1f}% | "
                f"{file_info['type']} | {action} |"
            )
        report.append("")
        
        # Technical Debt Assessment
        report.append("## Technical Debt Assessment")
        report.append("")
        
        # Calculate estimated hours
        undocumented_files = sum(
            1 for details in self.results['file_details'].values()
            if details['stats']['coverage'] < 60
        )
        
        estimated_hours = undocumented_files * 0.5  # Assume 30 minutes per file
        report.append(f"### Estimated Effort to Achieve 100% Coverage")
        report.append("")
        report.append(f"- **Files needing documentation:** {undocumented_files}")
        report.append(f"- **Estimated hours:** {estimated_hours:.1f}")
        report.append(f"- **Recommended timeline:** {int(estimated_hours / 20)} weeks (at 20 hours/week)")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        report.append("### Priority 1 - Critical (Complete within 1 week)")
        report.append("1. Document all files in `/src/core/` directory")
        report.append("2. Add comprehensive docstrings to main.py")
        report.append("3. Document all API endpoints in `/src/api/`")
        report.append("4. Add function documentation to critical exchange integrations")
        report.append("")
        
        report.append("### Priority 2 - High (Complete within 2 weeks)")
        report.append("1. Document all monitoring and signal generation modules")
        report.append("2. Add examples to complex mathematical functions")
        report.append("3. Document all configuration parameters")
        report.append("4. Create API documentation for external integrations")
        report.append("")
        
        report.append("### Priority 3 - Medium (Complete within 1 month)")
        report.append("1. Document all utility scripts in `/scripts/`")
        report.append("2. Add inline comments for complex algorithms")
        report.append("3. Create comprehensive test documentation")
        report.append("4. Document deployment procedures")
        report.append("")
        
        # Action Plan
        report.append("## Action Plan")
        report.append("")
        report.append("### Week 1: Critical Documentation")
        report.append("- [ ] Document core trading engine modules")
        report.append("- [ ] Add docstrings to all API endpoints")
        report.append("- [ ] Document exchange integration classes")
        report.append("- [ ] Create main.py comprehensive documentation")
        report.append("")
        
        report.append("### Week 2: System Components")
        report.append("- [ ] Document monitoring system")
        report.append("- [ ] Add signal generation documentation")
        report.append("- [ ] Document dashboard components")
        report.append("- [ ] Create cache layer documentation")
        report.append("")
        
        report.append("### Week 3: Supporting Systems")
        report.append("- [ ] Document all utility scripts")
        report.append("- [ ] Add deployment script documentation")
        report.append("- [ ] Document test suites")
        report.append("- [ ] Create configuration documentation")
        report.append("")
        
        report.append("### Week 4: Polish and Standards")
        report.append("- [ ] Review and update existing documentation")
        report.append("- [ ] Ensure consistency across all files")
        report.append("- [ ] Add examples where needed")
        report.append("- [ ] Create documentation templates")
        report.append("")
        
        # Compliance Check
        report.append("## Documentation Standards Compliance")
        report.append("")
        report.append("### Python Files (PEP 257 Compliance)")
        
        python_files = [
            (p, d) for p, d in self.results['file_details'].items()
            if d['type'] == 'python'
        ]
        
        compliant = sum(
            1 for _, d in python_files
            if d['stats'].get('module_docstring', False)
        )
        
        report.append(f"- Module docstrings: {compliant}/{len(python_files)} files")
        
        class_coverage = sum(
            d['stats']['classes']['documented']
            for _, d in python_files
        )
        class_total = sum(
            d['stats']['classes']['total']
            for _, d in python_files
        )
        
        if class_total > 0:
            report.append(f"- Class docstrings: {class_coverage}/{class_total} "
                        f"({class_coverage/class_total*100:.1f}%)")
            
        func_coverage = sum(
            d['stats']['functions']['documented']
            for _, d in python_files
        )
        func_total = sum(
            d['stats']['functions']['total']
            for _, d in python_files
        )
        
        if func_total > 0:
            report.append(f"- Function docstrings: {func_coverage}/{func_total} "
                        f"({func_coverage/func_total*100:.1f}%)")
        report.append("")
        
        # Footer
        report.append("## Next Steps")
        report.append("")
        report.append("1. **Immediate:** Review and prioritize critical files listed above")
        report.append("2. **This Week:** Begin documentation sprint for Priority 1 items")
        report.append("3. **Ongoing:** Establish documentation review in PR process")
        report.append("4. **Future:** Implement automated documentation generation")
        report.append("")
        report.append("---")
        report.append("*This report was generated by the Virtuoso CCXT Documentation Auditor*")
        
        return '\n'.join(report)


def main():
    """Main execution function."""
    # Set project root
    project_root = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt"
    
    # Initialize auditor
    auditor = DocumentationAuditor(project_root)
    
    # Perform audit
    print("=" * 80)
    print("VIRTUOSO CCXT DOCUMENTATION AUDIT")
    print("=" * 80)
    print()
    
    results = auditor.audit_project()
    
    # Generate report
    report = auditor.generate_report()
    
    # Save report to file
    report_path = Path(project_root) / "DOCUMENTATION_AUDIT_REPORT.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Print summary to console
    print(f"\n✅ Audit complete!")
    print(f"📊 Files analyzed: {results['files_analyzed']}")
    print(f"📈 Overall coverage: {results['overall_coverage']:.1f}%")
    print(f"📝 Report saved to: {report_path}")
    
    # Also save raw results as JSON for further analysis
    json_path = Path(project_root) / "documentation_audit_results.json"
    with open(json_path, 'w') as f:
        # Convert defaultdict to regular dict for JSON serialization
        json_results = {
            k: dict(v) if isinstance(v, defaultdict) else v
            for k, v in results.items()
        }
        json.dump(json_results, f, indent=2, default=str)
    
    print(f"🔍 Raw data saved to: {json_path}")
    
    return results


if __name__ == "__main__":
    main()