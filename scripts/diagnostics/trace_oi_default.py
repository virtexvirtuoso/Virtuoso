#!/usr/bin/env python3
"""
Trace where the default OI values (0.0) are being created.
"""

import os
import re

def find_default_oi_creation():
    """Find where OI is defaulted to 0.0 in the codebase."""
    
    patterns_to_search = [
        # Direct assignment patterns
        (r"'value':\s*0\.0.*'change_24h':\s*0\.0", "Direct default OI structure"),
        (r"'value':\s*0,.*'change_24h':\s*0", "Direct default OI structure (int)"),
        
        # Function that might create defaults
        (r"def.*default.*sentiment", "Default sentiment function"),
        (r"def.*create.*sentiment", "Create sentiment function"),
        (r"def.*get.*sentiment.*default", "Get sentiment with default"),
        
        # Places where sentiment is assembled
        (r"sentiment\s*=\s*{[^}]*'open_interest'", "Sentiment assembly with OI"),
        (r"'open_interest':\s*{.*}", "OI dictionary creation"),
        
        # Monitor specific patterns
        (r"liquidations.*long.*0\.0.*short.*0\.0", "Default liquidations (might be near OI)"),
    ]
    
    files_to_check = []
    
    # Find all Python files
    for root, dirs, files in os.walk('src'):
        # Skip __pycache__ directories
        if '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                files_to_check.append(os.path.join(root, file))
    
    print(f"Checking {len(files_to_check)} Python files...\n")
    
    findings = []
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for pattern, description in patterns_to_search:
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                if matches:
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        findings.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': description,
                            'match': match.group()[:100],
                            'context_start': max(0, line_num - 3),
                            'context_end': min(len(lines), line_num + 3)
                        })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Group findings by file
    findings_by_file = {}
    for finding in findings:
        if finding['file'] not in findings_by_file:
            findings_by_file[finding['file']] = []
        findings_by_file[finding['file']].append(finding)
    
    # Print findings
    for file_path, file_findings in findings_by_file.items():
        print(f"\n{'='*60}")
        print(f"File: {file_path}")
        print(f"{'='*60}")
        
        # Read file for context
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for finding in file_findings:
            print(f"\nLine {finding['line']}: {finding['pattern']}")
            print(f"Match: {finding['match']}")
            print("\nContext:")
            
            for i in range(finding['context_start'], finding['context_end']):
                prefix = ">>> " if i + 1 == finding['line'] else "    "
                print(f"{prefix}{i+1}: {lines[i].rstrip()}")


def check_monitor_sentiment_assembly():
    """Specifically check how monitor.py assembles sentiment data."""
    
    monitor_path = 'src/monitoring/monitor.py'
    if not os.path.exists(monitor_path):
        print(f"\n{monitor_path} not found")
        return
    
    print(f"\n\n{'='*60}")
    print("CHECKING MONITOR.PY SENTIMENT ASSEMBLY")
    print('='*60)
    
    with open(monitor_path, 'r') as f:
        content = f.read()
        lines = content.splitlines()
    
    # Look for calculate_indicators or similar methods
    method_pattern = r'async def.*calculate.*indicators.*\(.*\):'
    matches = list(re.finditer(method_pattern, content, re.IGNORECASE))
    
    if matches:
        print(f"\nFound {len(matches)} indicator calculation methods:")
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            print(f"  Line {line_num}: {match.group()}")
            
            # Look for sentiment assembly within the method
            method_start = match.start()
            # Find the end of the method (next method or class end)
            next_method = re.search(r'\n(async )?def ', content[method_start + 10:])
            method_end = method_start + next_method.start() if next_method else len(content)
            
            method_content = content[method_start:method_end]
            
            # Look for sentiment data creation
            if 'open_interest' in method_content and ('0.0' in method_content or 'default' in method_content):
                print(f"\n  Found potential OI default in this method!")
                # Show relevant lines
                method_lines = method_content.splitlines()
                for i, line in enumerate(method_lines):
                    if 'open_interest' in line or ('sentiment' in line and '{' in line):
                        print(f"    {line_num + i}: {line.strip()}")


if __name__ == "__main__":
    print("Tracing OI Default Value Creation")
    print("=================================\n")
    
    find_default_oi_creation()
    check_monitor_sentiment_assembly()
    
    print("\n\nSummary:")
    print("--------")
    print("The default OI values (0.0) are likely created in one of these places:")
    print("1. When sentiment data is assembled in monitor.py")
    print("2. When market data is missing OI and defaults are used")
    print("3. In a data processor that creates sentiment structure")
    print("\nCheck the findings above to locate the exact source.")