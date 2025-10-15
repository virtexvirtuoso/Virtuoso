"""
Division Operations Audit Script (Phase 1 - Week 1 Day 3-4)

This script audits all division operations in the codebase and categorizes them by risk level.

Risk Categories:
- HIGH: Division by variable (potentially zero)
- MEDIUM: Division with some protection but could be improved
- LOW: Division by constant or already protected
- SAFE: Path operations (/) not requiring protection

Output: Audit report with prioritized action plan
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict

# Patterns to identify different types of divisions
PATTERNS = {
    'path_operation': r'(Path|os\.path|\/\s*"|\/")',  # Path operations
    'constant_division': r'\/\s*[\d.]+\s*[,\)]',  # Division by numeric constant
    'percentage_calc': r'\*\s*100|\/\s*100',  # Percentage calculations
    'timestamp_conv': r'\/\s*1000',  # Timestamp conversions
    'size_conv': r'\/\s*\(?\s*1024',  # File size conversions (bytes to KB/MB)
    'max_guard': r'\/\s*max\(',  # Already using max() guard
    'variable_division': r'\/\s*[a-zA-Z_]',  # Division by variable (HIGH RISK)
}

def analyze_division_line(line: str, filepath: str, line_num: int) -> Dict:
    """Analyze a single line containing division operation."""
    result = {
        'file': filepath,
        'line_num': line_num,
        'code': line.strip(),
        'risk': 'UNKNOWN',
        'category': None,
        'needs_fix': False
    }

    # Check patterns in priority order
    if re.search(PATTERNS['path_operation'], line):
        result['risk'] = 'SAFE'
        result['category'] = 'path_operation'
    elif re.search(PATTERNS['size_conv'], line):
        result['risk'] = 'LOW'
        result['category'] = 'size_conversion'
    elif re.search(PATTERNS['timestamp_conv'], line):
        result['risk'] = 'LOW'
        result['category'] = 'timestamp_conversion'
    elif re.search(PATTERNS['max_guard'], line):
        result['risk'] = 'MEDIUM'
        result['category'] = 'max_guarded'
        result['needs_fix'] = True  # Could use safe_divide instead
    elif re.search(PATTERNS['constant_division'], line):
        result['risk'] = 'LOW'
        result['category'] = 'constant_division'
    elif re.search(PATTERNS['percentage_calc'], line):
        result['risk'] = 'LOW'
        result['category'] = 'percentage_calc'
    elif re.search(PATTERNS['variable_division'], line):
        result['risk'] = 'HIGH'
        result['category'] = 'variable_division'
        result['needs_fix'] = True

    return result


def audit_divisions(src_dir: str = "src") -> Dict:
    """Audit all division operations in the codebase."""
    divisions = []

    # Find all Python files
    src_path = Path(src_dir)
    py_files = list(src_path.rglob("*.py"))

    print(f"Scanning {len(py_files)} Python files...")

    for py_file in py_files:
        # Skip test files and generated files
        if '/test_' in str(py_file) or '/__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Look for division operator
                    if ' / ' in line and not line.strip().startswith('#'):
                        analysis = analyze_division_line(
                            line,
                            str(py_file.relative_to(Path.cwd())),
                            line_num
                        )
                        divisions.append(analysis)
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    # Categorize results
    stats = {
        'total': len(divisions),
        'by_risk': defaultdict(int),
        'by_category': defaultdict(int),
        'by_file': defaultdict(int),
        'needs_fix': 0,
        'divisions': divisions
    }

    for div in divisions:
        stats['by_risk'][div['risk']] += 1
        stats['by_category'][div['category']] += 1
        stats['by_file'][div['file']] += 1
        if div['needs_fix']:
            stats['needs_fix'] += 1

    return stats


def generate_report(stats: Dict, output_file: str = None):
    """Generate comprehensive audit report."""
    report_lines = []

    def add_line(line=""):
        report_lines.append(line)

    add_line("# Division Operations Audit Report")
    add_line()
    add_line("**Phase 1 - Week 1 Day 3-4: Division Guards**")
    add_line()
    add_line("---")
    add_line()

    # Summary Statistics
    add_line("## Summary Statistics")
    add_line()
    add_line(f"**Total Division Operations**: {stats['total']}")
    add_line(f"**Operations Needing Fixes**: {stats['needs_fix']}")
    add_line()

    # Risk Breakdown
    add_line("### Risk Level Breakdown")
    add_line()
    add_line("| Risk Level | Count | Percentage |")
    add_line("|------------|-------|------------|")
    for risk in ['HIGH', 'MEDIUM', 'LOW', 'SAFE', 'UNKNOWN']:
        count = stats['by_risk'][risk]
        pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
        add_line(f"| {risk} | {count} | {pct:.1f}% |")
    add_line()

    # Category Breakdown
    add_line("### Category Breakdown")
    add_line()
    add_line("| Category | Count | Description |")
    add_line("|----------|-------|-------------|")

    category_descriptions = {
        'path_operation': 'Path operations (/) - Safe',
        'size_conversion': 'File size conversions (bytes/1024) - Low risk',
        'timestamp_conversion': 'Timestamp conversions (/1000) - Low risk',
        'constant_division': 'Division by numeric constant - Low risk',
        'percentage_calc': 'Percentage calculations - Low risk',
        'max_guarded': 'Already using max() guard - Medium risk',
        'variable_division': 'Division by variable - HIGH RISK',
        None: 'Uncategorized'
    }

    for category, desc in category_descriptions.items():
        count = stats['by_category'][category]
        if count > 0:
            cat_name = category if category else "Uncategorized"
            add_line(f"| {cat_name} | {count} | {desc} |")
    add_line()

    # Top Files with Most Divisions
    add_line("### Top 20 Files with Most Divisions")
    add_line()
    add_line("| File | Division Count |")
    add_line("|------|----------------|")

    sorted_files = sorted(stats['by_file'].items(), key=lambda x: x[1], reverse=True)
    for file, count in sorted_files[:20]:
        add_line(f"| `{file}` | {count} |")
    add_line()

    # High-Risk Divisions (Top 30)
    high_risk = [d for d in stats['divisions'] if d['risk'] == 'HIGH']
    if high_risk:
        add_line("## HIGH-RISK Divisions Requiring Immediate Attention")
        add_line()
        add_line(f"**Total**: {len(high_risk)} operations")
        add_line()

        # Group by file
        by_file = defaultdict(list)
        for div in high_risk:
            by_file[div['file']].append(div)

        add_line("### High-Risk by File")
        add_line()

        for file in sorted(by_file.keys()):
            divs = by_file[file]
            add_line(f"#### {file} ({len(divs)} divisions)")
            add_line()

            for div in divs[:10]:  # Limit to first 10 per file
                add_line(f"**Line {div['line_num']}**:")
                add_line(f"```python")
                add_line(div['code'])
                add_line(f"```")
                add_line()

            if len(divs) > 10:
                add_line(f"*...and {len(divs) - 10} more*")
                add_line()

    # Medium-Risk Divisions (already using max())
    medium_risk = [d for d in stats['divisions'] if d['risk'] == 'MEDIUM']
    if medium_risk:
        add_line("## MEDIUM-RISK Divisions (Using max() guard)")
        add_line()
        add_line(f"**Total**: {len(medium_risk)} operations")
        add_line()
        add_line("These divisions already use max() for protection but could be improved with safe_divide():")
        add_line()

        for div in medium_risk[:15]:  # Show first 15
            add_line(f"- `{div['file']}:{div['line_num']}` - {div['code'][:80]}")

        if len(medium_risk) > 15:
            add_line(f"- *...and {len(medium_risk) - 15} more*")
        add_line()

    # Action Plan
    add_line("## Action Plan")
    add_line()
    add_line("### Priority 1: HIGH-RISK Divisions")
    add_line(f"- **Count**: {len(high_risk)}")
    add_line("- **Action**: Replace with `safe_divide()` immediately")
    add_line("- **Files to prioritize**: Indicators, analyzers, core calculation modules")
    add_line()

    add_line("### Priority 2: MEDIUM-RISK Divisions")
    add_line(f"- **Count**: {len(medium_risk)}")
    add_line("- **Action**: Replace `max()` pattern with `safe_divide()`")
    add_line("- **Benefit**: Better default handling, logging, consistency")
    add_line()

    add_line("### Priority 3: LOW-RISK Review")
    low_risk = [d for d in stats['divisions'] if d['risk'] == 'LOW']
    add_line(f"- **Count**: {len(low_risk)}")
    add_line("- **Action**: Review for edge cases")
    add_line("- **Note**: Mostly safe but verify assumptions")
    add_line()

    # Save report
    report_text = "\n".join(report_lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"\n✅ Report saved to: {output_file}")

    return report_text


if __name__ == "__main__":
    print("Starting Division Operations Audit...")
    print("=" * 60)

    stats = audit_divisions("src")

    print(f"\n✅ Audit complete!")
    print(f"   Total divisions found: {stats['total']}")
    print(f"   HIGH-RISK: {stats['by_risk']['HIGH']}")
    print(f"   MEDIUM-RISK: {stats['by_risk']['MEDIUM']}")
    print(f"   LOW-RISK: {stats['by_risk']['LOW']}")
    print(f"   SAFE: {stats['by_risk']['SAFE']}")

    output_file = "docs/implementation/confluence_optimizations/phase1/DIVISION_AUDIT_REPORT.md"
    report = generate_report(stats, output_file)

    print(f"\n📊 Report generated with {len(report.splitlines())} lines")
