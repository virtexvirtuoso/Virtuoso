#!/usr/bin/env python3
"""
Fix main.py to handle connection pool monitor import gracefully
"""

# Read main.py
with open('src/main.py', 'r') as f:
    lines = f.readlines()

# Find and comment out the problematic import and usage
new_lines = []
for line in lines:
    if 'from src.core.monitoring.connection_pool_monitor import' in line:
        new_lines.append('# ' + line)  # Comment out the import
    elif 'asyncio.create_task(start_monitoring())' in line:
        new_lines.append('        # ' + line)  # Comment out the usage
    elif 'await stop_monitoring()' in line:
        new_lines.append('    # ' + line)  # Comment out the cleanup
    else:
        new_lines.append(line)

# Write back
with open('src/main.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed main.py - commented out connection pool monitoring for now")