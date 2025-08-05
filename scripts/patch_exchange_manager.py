#!/usr/bin/env python3
"""
Patch the exchange manager to apply optimizations to Bybit exchange.
"""

import sys
from pathlib import Path

# Read the exchange manager file
manager_path = Path("src/core/exchanges/manager.py")
content = manager_path.read_text()

# Check if already patched
if "bybit_wrapper" in content:
    print("Exchange manager already patched")
    sys.exit(0)

# Find the import section
import_section_end = content.find("logger = logging.getLogger(__name__)")

# Add import for wrapper
new_import = "from .bybit_wrapper import apply_optimizations_to_exchange\n"
content = content[:import_section_end] + new_import + content[import_section_end:]

# Find where exchanges are initialized
init_section = content.find("async def initialize_exchange(self, exchange_id: str)")
if init_section == -1:
    print("Could not find initialize_exchange method")
    sys.exit(1)

# Find the end of the initialize_exchange method
method_start = init_section
method_end = content.find("\n    async def", method_start + 1)
if method_end == -1:
    method_end = len(content)

# Extract the method
method_content = content[method_start:method_end]

# Find where exchange is initialized and returned
return_pos = method_content.rfind("return exchange")
if return_pos == -1:
    print("Could not find return statement")
    sys.exit(1)

# Add optimization logic before return
optimization_code = '''
            # Apply optimizations to Bybit exchange
            if exchange_id == 'bybit' and not getattr(exchange, '_optimized', False):
                logger.info("Applying optimizations to Bybit exchange")
                try:
                    wrapper = await apply_optimizations_to_exchange(exchange)
                    exchange._optimization_wrapper = wrapper
                    exchange._optimized = True
                    logger.info("Optimizations applied successfully")
                except Exception as e:
                    logger.warning(f"Failed to apply optimizations: {e}")
            
            '''

# Insert the optimization code before the return statement
insert_pos = method_start + return_pos
new_method = method_content[:return_pos] + optimization_code + method_content[return_pos:]

# Replace the method in the content
content = content[:method_start] + new_method + content[method_end:]

# Write the patched file
manager_path.write_text(content)

print("Successfully patched exchange manager to apply optimizations")