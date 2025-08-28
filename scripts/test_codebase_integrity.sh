#!/bin/bash

echo "🔍 Comprehensive Codebase Integrity Test"
echo "========================================"

cd ~/trading/Virtuoso_ccxt

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create test results directory
mkdir -p test_results
REPORT="test_results/integrity_report_$(date +%Y%m%d_%H%M%S).txt"

echo "Running comprehensive tests..." | tee $REPORT
echo "==============================" | tee -a $REPORT
echo "" | tee -a $REPORT

# Test 1: Find config mismatches
echo -e "${BLUE}Test 1: Configuration Access Patterns${NC}" | tee -a $REPORT
echo "--------------------------------------" | tee -a $REPORT
python3 << 'EOF' | tee -a $REPORT
import os
import re
import ast

print("Checking for config access mismatches...\n")

# Pattern to find where configs are extracted but not used
unused_config_pattern = re.compile(r'(\w+_config)\s*=\s*config\.get\([\'"](\w+)[\'"].*?\)(?:(?!ReportManager\(\1)(?!self\.\1)(?!\1\[).)*?$', re.MULTILINE | re.DOTALL)

# Pattern to find inconsistent config access
config_access_patterns = [
    (r'config\.get\([\'"](\w+)[\'"]', 'config.get() calls'),
    (r'config\[[\'"](\w+)[\'"]\]', 'config[] access'),
    (r'self\.config\.get\([\'"](\w+)[\'"]', 'self.config.get() calls'),
]

issues_found = 0

for root, dirs, files in os.walk('src'):
    # Skip __pycache__ directories
    dirs[:] = [d for d in dirs if d != '__pycache__']
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Check for extracted but unused configs
                matches = unused_config_pattern.findall(content)
                if matches:
                    print(f"\n⚠️  {filepath}:")
                    print(f"   Config extracted but potentially not used correctly:")
                    for match in matches:
                        print(f"   - Variable '{match[0]}' extracted from config['{match[1]}']")
                    issues_found += 1
                
                # Check for mixed config access patterns in same file
                patterns_found = {}
                for pattern, desc in config_access_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        patterns_found[desc] = len(matches)
                
                if len(patterns_found) > 1:
                    print(f"\n⚠️  {filepath}:")
                    print(f"   Mixed config access patterns:")
                    for pattern, count in patterns_found.items():
                        print(f"   - {pattern}: {count} occurrences")
                    issues_found += 1
                    
            except Exception as e:
                print(f"Error reading {filepath}: {e}")

print(f"\n{'❌' if issues_found else '✅'} Found {issues_found} potential config issues")
EOF

echo "" | tee -a $REPORT

# Test 2: Find initialization order issues
echo -e "${BLUE}Test 2: Initialization Order Issues${NC}" | tee -a $REPORT
echo "-----------------------------------" | tee -a $REPORT
python3 << 'EOF' | tee -a $REPORT
import os
import re

print("Checking for initialization order issues...\n")

# Pattern to find class __init__ methods that might have order dependencies
init_pattern = re.compile(r'def __init__\(self.*?\):\s*(.*?)(?=\n    def|\nclass|\Z)', re.DOTALL)
dependency_pattern = re.compile(r'self\.(\w+)\s*=\s*(\w+)\((.*?)\)')

issues_found = 0

for root, dirs, files in os.walk('src'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Find all __init__ methods
                init_matches = init_pattern.findall(content)
                for init_body in init_matches:
                    lines = init_body.split('\n')
                    dependencies = {}
                    
                    for i, line in enumerate(lines):
                        # Check if line uses something before it's defined
                        for j in range(i+1, len(lines)):
                            if f'self.{line.strip().split("=")[0].strip()}' in lines[j]:
                                if '=' in line and '=' in lines[j]:
                                    print(f"\n⚠️  {filepath}:")
                                    print(f"   Potential initialization order issue:")
                                    print(f"   Line {i}: {line.strip()}")
                                    print(f"   Used in line {j}: {lines[j].strip()}")
                                    issues_found += 1
                                    break
                                    
            except Exception as e:
                pass

print(f"\n{'❌' if issues_found else '✅'} Found {issues_found} potential initialization order issues")
EOF

echo "" | tee -a $REPORT

# Test 3: Find missing error handling
echo -e "${BLUE}Test 3: Missing Error Handling${NC}" | tee -a $REPORT
echo "------------------------------" | tee -a $REPORT
grep -r "\.get(" src --include="*.py" | grep -v "\.get(.*,.*)" | head -20 | tee -a $REPORT
echo "Note: .get() calls without defaults might cause issues" | tee -a $REPORT

echo "" | tee -a $REPORT

# Test 4: Find hardcoded paths
echo -e "${BLUE}Test 4: Hardcoded Paths${NC}" | tee -a $REPORT
echo "-----------------------" | tee -a $REPORT
grep -r "src/" src --include="*.py" | grep -v "import" | grep -v "from" | head -20 | tee -a $REPORT

echo "" | tee -a $REPORT

# Test 5: Import consistency
echo -e "${BLUE}Test 5: Import Consistency${NC}" | tee -a $REPORT
echo "--------------------------" | tee -a $REPORT
python3 << 'EOF' | tee -a $REPORT
import os
import re

print("Checking import consistency...\n")

# Check for relative vs absolute imports
relative_imports = {}
absolute_imports = {}

for root, dirs, files in os.walk('src'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Find relative imports
                rel_matches = re.findall(r'from \.(.*?) import', content)
                if rel_matches:
                    relative_imports[filepath] = len(rel_matches)
                
                # Find absolute imports from src
                abs_matches = re.findall(r'from src\.(.*?) import', content)
                if abs_matches:
                    absolute_imports[filepath] = len(abs_matches)
                    
            except Exception as e:
                pass

# Report files with mixed import styles
mixed_files = set(relative_imports.keys()) & set(absolute_imports.keys())
if mixed_files:
    print("⚠️  Files with mixed import styles:")
    for file in mixed_files:
        print(f"   {file}: {relative_imports[file]} relative, {absolute_imports[file]} absolute")
else:
    print("✅ No mixed import styles found")
EOF

echo "" | tee -a $REPORT

# Test 6: Configuration key usage
echo -e "${BLUE}Test 6: Config Key Consistency${NC}" | tee -a $REPORT
echo "------------------------------" | tee -a $REPORT
python3 << 'EOF' | tee -a $REPORT
import yaml
import os
import re

print("Checking config key usage...\n")

# Load config
try:
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Get all config keys (flattened)
    def get_keys(d, prefix=''):
        keys = []
        for k, v in d.items():
            if isinstance(v, dict):
                keys.extend(get_keys(v, f"{prefix}{k}."))
            else:
                keys.append(f"{prefix}{k}")
        return keys
    
    config_keys = set(get_keys(config))
    
    # Find config key usage in code
    used_keys = set()
    for root, dirs, files in os.walk('src'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Find config access
                    matches = re.findall(r'[\'"](\w+)[\'"]', content)
                    used_keys.update(matches)
                    
                except Exception as e:
                    pass
    
    # Find unused config keys
    potentially_unused = config_keys - used_keys
    if potentially_unused:
        print("⚠️  Potentially unused config keys:")
        for key in sorted(potentially_unused)[:10]:
            print(f"   - {key}")
    
except Exception as e:
    print(f"Could not analyze config: {e}")
EOF

echo "" | tee -a $REPORT

# Test 7: Run actual tests if they exist
echo -e "${BLUE}Test 7: Running Unit Tests${NC}" | tee -a $REPORT
echo "--------------------------" | tee -a $REPORT
if [ -d "tests" ]; then
    echo "Running pytest..." | tee -a $REPORT
    python -m pytest tests -v --tb=short 2>&1 | tail -20 | tee -a $REPORT
else
    echo "No tests directory found" | tee -a $REPORT
fi

echo "" | tee -a $REPORT
echo "======================================" | tee -a $REPORT
echo -e "${GREEN}Test Summary${NC}" | tee -a $REPORT
echo "======================================" | tee -a $REPORT
echo "Report saved to: $REPORT" | tee -a $REPORT
echo "" | tee -a $REPORT
echo "Review the report for potential issues that might cause similar problems." | tee -a $REPORT
echo "Key areas to focus on:" | tee -a $REPORT
echo "1. Config access patterns" | tee -a $REPORT
echo "2. Initialization order" | tee -a $REPORT
echo "3. Error handling" | tee -a $REPORT
echo "4. Import consistency" | tee -a $REPORT