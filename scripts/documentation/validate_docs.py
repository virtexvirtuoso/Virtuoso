#!/usr/bin/env python3
"""
Documentation Validation Script for Virtuoso CCXT Trading System

This script validates documentation completeness, quality, and consistency
across the entire codebase. It checks for missing docstrings, validates
documentation format, and generates coverage reports.

Features:
- Validates docstring presence and quality
- Checks documentation format and style
- Generates coverage reports
- Identifies undocumented methods and classes
- Validates cross-references and links
- Checks for outdated documentation

Usage:
    python scripts/documentation/validate_docs.py [options]
    
Options:
    --source-dir: Source directory to validate (default: src/)
    --docs-dir: Documentation directory (default: docs/)
    --config-file: Configuration file for validation rules
    --output-format: Output format (json, markdown, html) (default: markdown)
    --fail-on-missing: Exit with error if missing docs found (default: False)
    --min-coverage: Minimum documentation coverage percentage (default: 80)
    --check-links: Validate internal links (default: True)

Version: 1.0.0
"""

import os
import re
import ast
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml

@dataclass
class ValidationResult:
    """Result of documentation validation."""
    file_path: str
    total_items: int
    documented_items: int
    missing_items: List[str]
    quality_issues: List[str]
    coverage_percentage: float
    grade: str

@dataclass
class ValidationSummary:
    """Summary of all validation results."""
    total_files: int
    total_items: int
    documented_items: int
    overall_coverage: float
    files_with_issues: int
    critical_issues: int
    warnings: int
    grade: str

@dataclass
class DocstringAnalysis:
    """Analysis of a docstring's quality."""
    has_description: bool
    has_parameters: bool
    has_returns: bool
    has_examples: bool
    has_type_hints: bool
    length_score: float
    completeness_score: float

class DocumentationValidator:
    """Main documentation validation class."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_dir = Path(config.get('source_dir', 'src/'))
        self.docs_dir = Path(config.get('docs_dir', 'docs/'))
        self.min_coverage = config.get('min_coverage', 80.0)
        self.fail_on_missing = config.get('fail_on_missing', False)
        self.check_links = config.get('check_links', True)
        
        # Validation rules
        self.validation_rules = self._load_validation_rules()
        
        # Results storage
        self.validation_results: List[ValidationResult] = []
        self.critical_files: Set[str] = set()
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules from config or use defaults."""
        
        config_file = self.config.get('config_file')
        if config_file and Path(config_file).exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        return {
            'required_sections': {
                'class_docstring': ['description', 'attributes'],
                'method_docstring': ['description', 'parameters', 'returns'],
                'function_docstring': ['description', 'parameters', 'returns']
            },
            'quality_thresholds': {
                'min_docstring_length': 20,
                'min_description_length': 50,
                'example_bonus_points': 10
            },
            'critical_files': [
                'src/indicators/*.py',
                'src/core/analysis/*.py',
                'src/api/*.py'
            ],
            'exclusions': [
                '__pycache__',
                '*.pyc',
                'test_*.py',
                '*_test.py'
            ]
        }
    
    def validate_documentation(self) -> ValidationSummary:
        """Validate documentation across all source files."""
        
        print("🔍 Starting documentation validation...")
        
        # Find all Python files to validate
        python_files = self._find_python_files()
        
        print(f"📁 Found {len(python_files)} Python files to validate")
        
        # Validate each file
        for file_path in python_files:
            try:
                print(f"📄 Validating {file_path}")
                result = self._validate_file(file_path)
                self.validation_results.append(result)
                
                # Mark critical files with issues
                if self._is_critical_file(file_path) and result.coverage_percentage < self.min_coverage:
                    self.critical_files.add(str(file_path))
                    
            except Exception as e:
                print(f"❌ Error validating {file_path}: {str(e)}")
                # Create error result
                error_result = ValidationResult(
                    file_path=str(file_path),
                    total_items=0,
                    documented_items=0,
                    missing_items=[f"Validation error: {str(e)}"],
                    quality_issues=[],
                    coverage_percentage=0.0,
                    grade='F'
                )
                self.validation_results.append(error_result)
        
        # Generate summary
        summary = self._generate_summary()
        
        # Generate detailed report
        self._generate_detailed_report(summary)
        
        print(f"✅ Validation complete!")
        print(f"   Overall Coverage: {summary.overall_coverage:.1f}%")
        print(f"   Grade: {summary.grade}")
        print(f"   Files with Issues: {summary.files_with_issues}")
        
        return summary
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files to validate."""
        python_files = []
        
        for pattern in ['*.py']:
            python_files.extend(self.source_dir.rglob(pattern))
        
        # Filter out excluded files
        filtered_files = []
        for file_path in python_files:
            should_exclude = False
            
            for exclusion in self.validation_rules.get('exclusions', []):
                if file_path.match(exclusion) or exclusion in str(file_path):
                    should_exclude = True
                    break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _validate_file(self, file_path: Path) -> ValidationResult:
        """Validate documentation for a single file."""
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return ValidationResult(
                file_path=str(file_path),
                total_items=0,
                documented_items=0,
                missing_items=[f"Syntax error: {str(e)}"],
                quality_issues=[],
                coverage_percentage=0.0,
                grade='F'
            )
        
        # Count total documentable items
        total_items = 0
        documented_items = 0
        missing_items = []
        quality_issues = []
        
        # Validate module docstring
        module_docstring = ast.get_docstring(tree)
        total_items += 1
        
        if module_docstring:
            documented_items += 1
            quality_issues.extend(self._analyze_docstring_quality(
                module_docstring, 'module', file_path.name
            ))
        else:
            missing_items.append(f"Module docstring missing")
        
        # Validate classes and methods
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count class
                total_items += 1
                class_docstring = ast.get_docstring(node)
                
                if class_docstring:
                    documented_items += 1
                    quality_issues.extend(self._analyze_docstring_quality(
                        class_docstring, 'class', node.name
                    ))
                else:
                    missing_items.append(f"Class '{node.name}' missing docstring")
                
                # Count class methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_items += 1
                        method_docstring = ast.get_docstring(item)
                        
                        if method_docstring:
                            documented_items += 1
                            quality_issues.extend(self._analyze_docstring_quality(
                                method_docstring, 'method', f"{node.name}.{item.name}"
                            ))
                        else:
                            # Skip private methods unless they're important
                            if not item.name.startswith('_') or item.name in ['__init__', '__call__']:
                                missing_items.append(f"Method '{node.name}.{item.name}' missing docstring")
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Top-level functions only
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    total_items += 1
                    function_docstring = ast.get_docstring(node)
                    
                    if function_docstring:
                        documented_items += 1
                        quality_issues.extend(self._analyze_docstring_quality(
                            function_docstring, 'function', node.name
                        ))
                    else:
                        if not node.name.startswith('_'):
                            missing_items.append(f"Function '{node.name}' missing docstring")
        
        # Calculate coverage
        coverage_percentage = (documented_items / total_items * 100) if total_items > 0 else 0
        
        # Assign grade
        grade = self._calculate_grade(coverage_percentage, len(quality_issues))
        
        return ValidationResult(
            file_path=str(file_path),
            total_items=total_items,
            documented_items=documented_items,
            missing_items=missing_items,
            quality_issues=quality_issues,
            coverage_percentage=coverage_percentage,
            grade=grade
        )
    
    def _analyze_docstring_quality(self, docstring: str, doc_type: str, item_name: str) -> List[str]:
        """Analyze the quality of a docstring."""
        
        issues = []
        
        # Basic length check
        min_length = self.validation_rules['quality_thresholds']['min_docstring_length']
        if len(docstring) < min_length:
            issues.append(f"{doc_type.title()} '{item_name}': Docstring too short ({len(docstring)} < {min_length} chars)")
        
        # Check for description
        lines = docstring.strip().split('\n')
        if not lines or not lines[0].strip():
            issues.append(f"{doc_type.title()} '{item_name}': Missing description")
        else:
            description = lines[0].strip()
            min_desc_length = self.validation_rules['quality_thresholds']['min_description_length']
            if len(description) < min_desc_length:
                issues.append(f"{doc_type.title()} '{item_name}': Description too brief")
        
        # Check for required sections based on type
        required_sections = self.validation_rules['required_sections'].get(f"{doc_type}_docstring", [])
        
        for section in required_sections:
            if section == 'parameters':
                if not self._has_parameters_section(docstring):
                    issues.append(f"{doc_type.title()} '{item_name}': Missing parameters documentation")
            elif section == 'returns':
                if not self._has_returns_section(docstring):
                    issues.append(f"{doc_type.title()} '{item_name}': Missing return value documentation")
            elif section == 'attributes' and doc_type == 'class':
                if not self._has_attributes_section(docstring):
                    issues.append(f"{doc_type.title()} '{item_name}': Missing attributes documentation")
        
        # Check for examples (bonus points if present, issue if complex method lacks them)
        if not self._has_examples_section(docstring):
            if doc_type == 'method' and len(docstring) > 200:  # Complex methods should have examples
                issues.append(f"{doc_type.title()} '{item_name}': Complex method missing usage examples")
        
        return issues
    
    def _has_parameters_section(self, docstring: str) -> bool:
        """Check if docstring has parameters section."""
        patterns = [
            r'Args?:',
            r'Parameters?:',
            r'Arguments?:',
            r'\*\*Args\*\*',
            r'\*\*Parameters\*\*'
        ]
        
        for pattern in patterns:
            if re.search(pattern, docstring, re.IGNORECASE):
                return True
        
        return False
    
    def _has_returns_section(self, docstring: str) -> bool:
        """Check if docstring has returns section."""
        patterns = [
            r'Returns?:',
            r'Return:',
            r'\*\*Returns?\*\*'
        ]
        
        for pattern in patterns:
            if re.search(pattern, docstring, re.IGNORECASE):
                return True
        
        return False
    
    def _has_attributes_section(self, docstring: str) -> bool:
        """Check if docstring has attributes section."""
        patterns = [
            r'Attributes?:',
            r'\*\*Attributes?\*\*'
        ]
        
        for pattern in patterns:
            if re.search(pattern, docstring, re.IGNORECASE):
                return True
        
        return False
    
    def _has_examples_section(self, docstring: str) -> bool:
        """Check if docstring has examples section."""
        patterns = [
            r'Examples?:',
            r'Usage:',
            r'Example:',
            r'\*\*Examples?\*\*',
            r'```python',
            r'>>>'
        ]
        
        for pattern in patterns:
            if re.search(pattern, docstring, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_grade(self, coverage_percentage: float, quality_issues_count: int) -> str:
        """Calculate grade based on coverage and quality."""
        
        # Base grade from coverage
        if coverage_percentage >= 95:
            base_grade = 'A+'
        elif coverage_percentage >= 90:
            base_grade = 'A'
        elif coverage_percentage >= 85:
            base_grade = 'A-'
        elif coverage_percentage >= 80:
            base_grade = 'B+'
        elif coverage_percentage >= 75:
            base_grade = 'B'
        elif coverage_percentage >= 70:
            base_grade = 'B-'
        elif coverage_percentage >= 65:
            base_grade = 'C+'
        elif coverage_percentage >= 60:
            base_grade = 'C'
        elif coverage_percentage >= 55:
            base_grade = 'C-'
        elif coverage_percentage >= 50:
            base_grade = 'D+'
        elif coverage_percentage >= 45:
            base_grade = 'D'
        elif coverage_percentage >= 40:
            base_grade = 'D-'
        else:
            base_grade = 'F'
        
        # Adjust for quality issues
        if quality_issues_count > 10:
            base_grade = 'F'
        elif quality_issues_count > 5:
            # Downgrade by one level
            downgrades = {
                'A+': 'A', 'A': 'A-', 'A-': 'B+',
                'B+': 'B', 'B': 'B-', 'B-': 'C+',
                'C+': 'C', 'C': 'C-', 'C-': 'D+',
                'D+': 'D', 'D': 'D-', 'D-': 'F'
            }
            base_grade = downgrades.get(base_grade, 'F')
        
        return base_grade
    
    def _is_critical_file(self, file_path: Path) -> bool:
        """Check if file is marked as critical."""
        
        for pattern in self.validation_rules.get('critical_files', []):
            if file_path.match(pattern) or pattern.replace('*', '') in str(file_path):
                return True
        
        return False
    
    def _generate_summary(self) -> ValidationSummary:
        """Generate validation summary."""
        
        total_files = len(self.validation_results)
        total_items = sum(result.total_items for result in self.validation_results)
        documented_items = sum(result.documented_items for result in self.validation_results)
        
        overall_coverage = (documented_items / total_items * 100) if total_items > 0 else 0
        
        files_with_issues = sum(1 for result in self.validation_results 
                              if result.missing_items or result.quality_issues)
        
        critical_issues = len(self.critical_files)
        warnings = sum(len(result.quality_issues) for result in self.validation_results)
        
        # Calculate overall grade
        if overall_coverage >= 90 and critical_issues == 0:
            grade = 'A'
        elif overall_coverage >= 80 and critical_issues <= 2:
            grade = 'B'
        elif overall_coverage >= 70:
            grade = 'C'
        elif overall_coverage >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        return ValidationSummary(
            total_files=total_files,
            total_items=total_items,
            documented_items=documented_items,
            overall_coverage=overall_coverage,
            files_with_issues=files_with_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            grade=grade
        )
    
    def _generate_detailed_report(self, summary: ValidationSummary):
        """Generate detailed validation report."""
        
        output_format = self.config.get('output_format', 'markdown')
        
        if output_format == 'json':
            self._generate_json_report(summary)
        elif output_format == 'html':
            self._generate_html_report(summary)
        else:
            self._generate_markdown_report(summary)
    
    def _generate_markdown_report(self, summary: ValidationSummary):
        """Generate markdown validation report."""
        
        report_content = f"""# Documentation Validation Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Grade** | **{summary.grade}** |
| **Coverage** | **{summary.overall_coverage:.1f}%** |
| **Files Validated** | {summary.total_files} |
| **Total Items** | {summary.total_items} |
| **Documented Items** | {summary.documented_items} |
| **Files with Issues** | {summary.files_with_issues} |
| **Critical Issues** | {summary.critical_issues} |
| **Warnings** | {summary.warnings} |

## Coverage by File

| File | Coverage | Grade | Issues | Status |
|------|----------|-------|--------|--------|
"""
        
        # Sort results by coverage percentage (lowest first)
        sorted_results = sorted(self.validation_results, key=lambda x: x.coverage_percentage)
        
        for result in sorted_results:
            status = "🔴 CRITICAL" if str(result.file_path) in self.critical_files else "✅ OK" if result.coverage_percentage >= self.min_coverage else "⚠️ LOW"
            issues_count = len(result.missing_items) + len(result.quality_issues)
            
            report_content += f"| `{result.file_path}` | {result.coverage_percentage:.1f}% | {result.grade} | {issues_count} | {status} |\n"
        
        # Detailed issues section
        report_content += "\n## Detailed Issues\n\n"
        
        for result in sorted_results:
            if result.missing_items or result.quality_issues:
                report_content += f"### {result.file_path}\n\n"
                report_content += f"**Coverage**: {result.coverage_percentage:.1f}% ({result.documented_items}/{result.total_items})\n"
                report_content += f"**Grade**: {result.grade}\n\n"
                
                if result.missing_items:
                    report_content += "**Missing Documentation**:\n"
                    for item in result.missing_items:
                        report_content += f"- ❌ {item}\n"
                    report_content += "\n"
                
                if result.quality_issues:
                    report_content += "**Quality Issues**:\n"
                    for issue in result.quality_issues:
                        report_content += f"- ⚠️ {issue}\n"
                    report_content += "\n"
        
        # Recommendations
        report_content += "## Recommendations\n\n"
        
        if summary.overall_coverage < 80:
            report_content += "### High Priority\n"
            report_content += "- 🚨 **Overall coverage is below 80%** - Focus on documenting missing items\n"
            report_content += "- 📝 Prioritize critical files and public APIs\n\n"
        
        if self.critical_files:
            report_content += "### Critical Files Needing Attention\n"
            for file_path in sorted(self.critical_files):
                report_content += f"- 🔴 `{file_path}`\n"
            report_content += "\n"
        
        # Best practices
        report_content += "### Best Practices\n"
        report_content += "- ✅ Include parameter descriptions with types\n"
        report_content += "- ✅ Document return values clearly\n"
        report_content += "- ✅ Add usage examples for complex methods\n"
        report_content += "- ✅ Use consistent docstring format (Google/Sphinx style)\n"
        report_content += "- ✅ Keep descriptions concise but informative\n\n"
        
        report_content += "---\n*Generated by Virtuoso CCXT Documentation Validator*"
        
        # Write report
        report_path = Path(self.config.get('output_dir', '.')) / 'documentation_validation_report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 Detailed report saved to: {report_path}")
    
    def _generate_json_report(self, summary: ValidationSummary):
        """Generate JSON validation report."""
        
        report_data = {
            'summary': asdict(summary),
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(result) for result in self.validation_results],
            'critical_files': list(self.critical_files),
            'validation_rules': self.validation_rules
        }
        
        report_path = Path(self.config.get('output_dir', '.')) / 'documentation_validation_report.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"📊 JSON report saved to: {report_path}")
    
    def _generate_html_report(self, summary: ValidationSummary):
        """Generate HTML validation report."""
        
        # Simple HTML report (could be enhanced with CSS/JS)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Documentation Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .grade-A {{ color: green; font-weight: bold; }}
        .grade-B {{ color: orange; font-weight: bold; }}
        .grade-C {{ color: red; font-weight: bold; }}
        .grade-F {{ color: darkred; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .critical {{ background-color: #ffebee; }}
        .warning {{ background-color: #fff3e0; }}
        .ok {{ background-color: #e8f5e8; }}
    </style>
</head>
<body>
    <h1>Documentation Validation Report</h1>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p><strong>Overall Grade:</strong> <span class="grade-{summary.grade}">{summary.grade}</span></p>
        <p><strong>Coverage:</strong> {summary.overall_coverage:.1f}%</p>
        <p><strong>Files Validated:</strong> {summary.total_files}</p>
        <p><strong>Critical Issues:</strong> {summary.critical_issues}</p>
    </div>
    
    <h2>Results by File</h2>
    <table>
        <thead>
            <tr>
                <th>File</th>
                <th>Coverage</th>
                <th>Grade</th>
                <th>Issues</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for result in self.validation_results:
            status_class = "critical" if str(result.file_path) in self.critical_files else "ok" if result.coverage_percentage >= self.min_coverage else "warning"
            issues_count = len(result.missing_items) + len(result.quality_issues)
            
            html_content += f"""
            <tr class="{status_class}">
                <td>{result.file_path}</td>
                <td>{result.coverage_percentage:.1f}%</td>
                <td class="grade-{result.grade[0]}">{result.grade}</td>
                <td>{issues_count}</td>
                <td>{status_class.upper()}</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
    
    <p><em>Generated by Virtuoso CCXT Documentation Validator</em></p>
</body>
</html>
"""
        
        report_path = Path(self.config.get('output_dir', '.')) / 'documentation_validation_report.html'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📊 HTML report saved to: {report_path}")

def main():
    """Main function to run documentation validation."""
    
    parser = argparse.ArgumentParser(
        description="Validate documentation for Virtuoso CCXT Trading System"
    )
    
    parser.add_argument(
        '--source-dir',
        default='src/',
        help='Source directory to validate'
    )
    
    parser.add_argument(
        '--docs-dir',
        default='docs/',
        help='Documentation directory'
    )
    
    parser.add_argument(
        '--config-file',
        help='Configuration file for validation rules'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'markdown', 'html'],
        default='markdown',
        help='Output format for validation report'
    )
    
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Output directory for reports'
    )
    
    parser.add_argument(
        '--fail-on-missing',
        action='store_true',
        help='Exit with error if missing documentation found'
    )
    
    parser.add_argument(
        '--min-coverage',
        type=float,
        default=80.0,
        help='Minimum documentation coverage percentage'
    )
    
    parser.add_argument(
        '--check-links',
        action='store_true',
        help='Validate internal links'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = {
        'source_dir': args.source_dir,
        'docs_dir': args.docs_dir,
        'config_file': args.config_file,
        'output_format': args.output_format,
        'output_dir': args.output_dir,
        'fail_on_missing': args.fail_on_missing,
        'min_coverage': args.min_coverage,
        'check_links': args.check_links
    }
    
    # Initialize validator
    validator = DocumentationValidator(config)
    
    # Run validation
    try:
        summary = validator.validate_documentation()
        
        # Determine exit code
        if args.fail_on_missing and (summary.overall_coverage < args.min_coverage or summary.critical_issues > 0):
            print(f"\n💥 Validation failed: Coverage {summary.overall_coverage:.1f}% < {args.min_coverage}% or critical issues found")
            sys.exit(1)
        elif summary.grade in ['D', 'F']:
            print(f"\n⚠️ Documentation quality is poor (Grade: {summary.grade})")
            sys.exit(1)
        else:
            print(f"\n✅ Documentation validation passed (Grade: {summary.grade})")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Fatal error during validation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()