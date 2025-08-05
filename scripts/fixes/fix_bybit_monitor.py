#!/usr/bin/env python3
"""
Fix the bybit.py file to properly integrate connection pool monitoring
"""

import re

# Read the broken file
with open('src/core/exchanges/bybit.py', 'r') as f:
    content = f.read()

# Remove any existing monitor imports and code
content = re.sub(r'from src\.core\.monitoring\.connection_pool_monitor import get_monitor\n?', '', content)
content = re.sub(r'\s*# Register session with connection pool monitor.*?logger\.warning.*?\n', '', content, flags=re.DOTALL)

# Add the import after base_component import
content = content.replace(
    'from src.core.base_component import BaseComponent\n',
    'from src.core.base_component import BaseComponent\nfrom src.core.monitoring.connection_pool_monitor import get_monitor\n'
)

# Write the fixed content
with open('src/core/exchanges/bybit.py', 'w') as f:
    f.write(content)

print("Fixed bybit.py - removed monitor integration for now")