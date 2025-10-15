#!/usr/bin/env python3
"""
Comprehensive Mock Data Scanner for Phase 0 Crisis Stabilization
Scans all Python files for mock data patterns and categorizes by criticality
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

# Mock data patterns to detect
MOCK_PATTERNS = {
    'random_generation': [
        r'random\.(uniform|randint|choice|random|gauss|normal)',
        r'np\.random\.',
        r'random\.seed',
    ],
    'mock_values': [
        r'mock_.*=',
        r'fake_.*=',
        r'dummy_.*=',
        r'test_.*data',
    ],
    'hardcoded_fake': [
        r'["\']mock["\']',
        r'["\']fake["\']',
        r'["\']dummy["\']',
        r'["\']test.*data["\']',
    ],
    'simulation': [
        r'simulate_',
        r'generate_fake_',
        r'create_mock_',
    ]
}

# File criticality based on path patterns
CRITICALITY_MAPPING = {
    'CRITICAL': [
        'src/core/market/',
        'src/core/analysis/',
        'src/monitoring/alert_manager.py',
        'src/signal_generation/',
        'src/api/routes/dashboard.py',
        'src/main.py',
        'src/web_server.py'
    ],
    'HIGH': [
        'src/core/exchanges/',
        'src/data_processing/',
        'src/monitoring/',
        'src/api/routes/',
        'src/trade_execution/',
    ],
    'MEDIUM': [
        'src/core/',
        'src/indicators/',
        'src/services/',
        'src/utils/',
    ],
    'LOW': [
        'src/fixes/',
        'src/testing/',
        'src/tools/',
        'src/demo_',
        'examples/',
        'test_',
    ]
}

def get_file_criticality(file_path):
    """Determine file criticality based on path"""
    for level, patterns in CRITICALITY_MAPPING.items():
        for pattern in patterns:
            if pattern in file_path:
                return level
    return 'UNKNOWN'

def scan_file_for_patterns(file_path):
    """Scan a single file for mock data patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        found_patterns = {}
        for category, patterns in MOCK_PATTERNS.items():
            matches = []
            for pattern in patterns:
                regex_matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in regex_matches:
                    line_num = content[:match.start()].count('\n') + 1
                    matches.append({
                        'pattern': pattern,
                        'match': match.group(),
                        'line': line_num
                    })
            if matches:
                found_patterns[category] = matches

        return found_patterns
    except Exception as e:
        return {'error': str(e)}

def main():
    """Main scanning function"""
    src_dir = Path('src')
    results = {
        'total_files': 0,
        'files_with_mock': 0,
        'by_criticality': defaultdict(list),
        'by_pattern': defaultdict(list),
        'files': {}
    }

    print("🔍 Scanning for mock data patterns...")

    # Scan all Python files
    for py_file in src_dir.rglob('*.py'):
        results['total_files'] += 1
        file_path = str(py_file)

        # Skip already fixed files
        if any(fixed in file_path for fixed in [
            'market_data_manager.py',
            'confluence.py',
            'alert_manager.py',
            'signal_processor.py',
            'dashboard.py'
        ]):
            continue

        patterns = scan_file_for_patterns(file_path)

        if patterns and 'error' not in patterns:
            results['files_with_mock'] += 1
            criticality = get_file_criticality(file_path)

            file_info = {
                'path': file_path,
                'criticality': criticality,
                'patterns': patterns,
                'pattern_count': sum(len(matches) for matches in patterns.values())
            }

            results['files'][file_path] = file_info
            results['by_criticality'][criticality].append(file_info)

            for pattern_type in patterns.keys():
                results['by_pattern'][pattern_type].append(file_info)

    # Print summary
    print(f"\n📊 SCAN RESULTS:")
    print(f"Total Python files: {results['total_files']}")
    print(f"Files with mock patterns: {results['files_with_mock']}")
    print(f"Clean files: {results['total_files'] - results['files_with_mock']}")

    print(f"\n🎯 BY CRITICALITY:")
    for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']:
        count = len(results['by_criticality'][level])
        if count > 0:
            print(f"  {level}: {count} files")

    print(f"\n🔍 BY PATTERN TYPE:")
    for pattern_type, files in results['by_pattern'].items():
        print(f"  {pattern_type}: {len(files)} files")

    # Show most critical files first
    print(f"\n🚨 TOP 20 CRITICAL FILES TO FIX:")
    critical_files = sorted(
        [f for f in results['files'].values() if f['criticality'] == 'CRITICAL'],
        key=lambda x: x['pattern_count'],
        reverse=True
    )

    for i, file_info in enumerate(critical_files[:20], 1):
        print(f"  {i:2d}. {file_info['path']} ({file_info['pattern_count']} patterns)")

    # Save detailed results
    output_file = 'scripts/mock_data_scan_results.json'
    with open(output_file, 'w') as f:
        # Convert defaultdict to regular dict for JSON serialization
        results_serializable = dict(results)
        results_serializable['by_criticality'] = dict(results['by_criticality'])
        results_serializable['by_pattern'] = dict(results['by_pattern'])
        json.dump(results_serializable, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")

    return results

if __name__ == "__main__":
    main()