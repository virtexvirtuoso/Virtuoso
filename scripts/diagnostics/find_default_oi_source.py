#!/usr/bin/env python3
"""
Find where the default OI structure with 0.0 values is created.
"""

import os
import re

def find_oi_default_source():
    """Search for where OI defaults to 0.0."""
    
    # Patterns to search for
    patterns = [
        # Looking for where sentiment data is created with defaults
        (r"'open_interest':\s*{[^}]*'value':\s*0", "OI with value 0"),
        (r"'liquidations':\s*{[^}]*'long':\s*0", "Liquidations with 0"),
        (r"sentiment.*=.*{.*'open_interest'", "Sentiment creation with OI"),
        (r"get_default.*sentiment", "Default sentiment getter"),
        (r"create.*default.*sentiment", "Create default sentiment"),
        (r"'value':\s*0.*'change_24h':\s*0", "Value and change_24h = 0"),
        (r"timestamp.*time\.time.*\* 1000", "Timestamp creation pattern"),
    ]
    
    # Files to search
    search_paths = [
        'src/monitoring/monitor.py',
        'src/data_processing/data_processor.py',
        'src/monitoring/monitor_data.py',
        'src/core/data_cache.py',
        'src/monitoring/monitor_utils.py',
    ]
    
    # Expand to find actual files
    files_to_search = []
    for path in search_paths:
        if os.path.exists(path):
            files_to_search.append(path)
        else:
            # Try to find similar files
            dir_path = os.path.dirname(path)
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.endswith('.py') and 'monitor' in file:
                        files_to_search.append(os.path.join(dir_path, file))
    
    print(f"Searching {len(files_to_search)} files...\n")
    
    for file_path in files_to_search:
        print(f"\nChecking {file_path}...")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.splitlines()
            
            found_patterns = []
            
            for pattern, description in patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                if matches:
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        found_patterns.append((line_num, description, match.group()[:100]))
            
            if found_patterns:
                print(f"  Found {len(found_patterns)} matches:")
                for line_num, desc, match in found_patterns:
                    print(f"    Line {line_num}: {desc}")
                    print(f"      Match: {match}")
                    
                    # Show context
                    start = max(0, line_num - 3)
                    end = min(len(lines), line_num + 3)
                    print("      Context:")
                    for i in range(start, end):
                        prefix = ">>>" if i == line_num - 1 else "   "
                        print(f"      {prefix} {i+1}: {lines[i]}")
                    print()
                    
        except Exception as e:
            print(f"  Error reading file: {e}")


def check_monitor_data_classes():
    """Check if there are data classes that define default structures."""
    
    print("\n" + "="*60)
    print("CHECKING FOR DATA CLASSES WITH DEFAULTS")
    print("="*60)
    
    # Look for class definitions that might have default sentiment
    class_patterns = [
        r"class.*Sentiment",
        r"class.*MarketData",
        r"@dataclass",
        r"def __init__.*sentiment",
    ]
    
    for root, dirs, files in os.walk('src'):
        if '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    for pattern in class_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Check if this file has OI defaults
                            if "'value': 0" in content or "value=0" in content:
                                print(f"\nFound potential default in {file_path}")
                                # Show the class definition
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    line_num = content[:match.start()].count('\n') + 1
                                    print(f"  Line {line_num}: {match.group()}")
                                
                except Exception as e:
                    pass


if __name__ == "__main__":
    print("Finding OI Default Source")
    print("========================\n")
    
    find_oi_default_source()
    check_monitor_data_classes()
    
    print("\n\nConclusion:")
    print("-----------")
    print("The default OI structure is likely created when:")
    print("1. Market data is missing OI data")
    print("2. A fallback/default is used")
    print("3. Check the monitor's data assembly methods")