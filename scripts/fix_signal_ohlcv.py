#!/usr/bin/env python3
"""
Fix signal generation to include OHLCV data for chart generation
This script patches the monitor to include OHLCV data in signal alerts
"""

import os
import sys

def create_patch():
    """Create a patch to add OHLCV data to signal alerts"""

    patch_content = '''
# Patch to add OHLCV data to signal alerts for chart generation

def add_ohlcv_to_signal(monitor_file):
    """Add OHLCV data fetching to signal preparation"""

    # Read the current monitor.py
    with open(monitor_file, 'r') as f:
        content = f.read()

    # Add OHLCV fetching before send_signal_alert
    patch = """
                # Add OHLCV data for chart generation
                try:
                    # Get OHLCV data from market data manager
                    if hasattr(self, 'market_data_manager'):
                        ohlcv_data = await self.market_data_manager.get_ohlcv_data(
                            symbol=symbol,
                            timeframe='5m',  # Use 5-minute candles for charts
                            limit=100  # Get last 100 candles
                        )
                        if ohlcv_data is not None and len(ohlcv_data) > 0:
                            signal_data['ohlcv_data'] = ohlcv_data
                            self.logger.info(f"Added {len(ohlcv_data)} OHLCV candles to signal for chart generation")
                    else:
                        self.logger.debug("Market data manager not available for OHLCV data")
                except Exception as e:
                    self.logger.warning(f"Could not fetch OHLCV data for chart: {e}")
                    # Continue without OHLCV - will use simulated chart
"""

    # Find where to insert the patch
    if "send_signal_alert" in content:
        # Insert before the send_signal_alert call
        lines = content.split('\\n')
        new_lines = []

        for i, line in enumerate(lines):
            new_lines.append(line)
            # Look for signal_data preparation
            if 'signal_data = {' in line:
                # Find the end of the signal_data dict
                brace_count = 0
                start_idx = i
                for j in range(i, min(i+50, len(lines))):
                    if '{' in lines[j]:
                        brace_count += lines[j].count('{')
                    if '}' in lines[j]:
                        brace_count -= lines[j].count('}')
                    if brace_count == 0 and j > i:
                        # Found the end of signal_data dict
                        # Insert OHLCV fetching after it
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        new_lines.append('')
                        new_lines.append(' ' * indent + '# Fetch OHLCV data for chart generation')
                        new_lines.append(' ' * indent + 'try:')
                        new_lines.append(' ' * (indent + 4) + 'if hasattr(self, "market_data_manager") and self.market_data_manager:')
                        new_lines.append(' ' * (indent + 8) + 'ohlcv_data = self.market_data_manager.get_cached_ohlcv(symbol, "base")')
                        new_lines.append(' ' * (indent + 8) + 'if ohlcv_data is not None and len(ohlcv_data) > 0:')
                        new_lines.append(' ' * (indent + 12) + 'signal_data["ohlcv_data"] = ohlcv_data[-100:]  # Last 100 candles')
                        new_lines.append(' ' * (indent + 12) + 'self.logger.info(f"Added {len(signal_data[\\"ohlcv_data\\"])} OHLCV candles for chart")')
                        new_lines.append(' ' * indent + 'except Exception as e:')
                        new_lines.append(' ' * (indent + 4) + 'self.logger.debug(f"Could not add OHLCV for chart: {e}")')
                        break

        return '\\n'.join(new_lines)

    return content

# Apply the patch
monitor_file = 'src/monitoring/monitor.py'

# Backup the original
import shutil
shutil.copy(monitor_file, f'{monitor_file}.backup_before_ohlcv')

# Apply patch
patched_content = add_ohlcv_to_signal(monitor_file)

# Write the patched file
with open(monitor_file, 'w') as f:
    f.write(patched_content)

print("✅ Patch applied to include OHLCV data in signal alerts")
print("   Charts should now be generated automatically with signals!")
'''

    return patch_content

if __name__ == "__main__":
    print("Creating OHLCV signal patch...")
    patch = create_patch()

    # Save the patch file
    patch_file = "fix_signal_ohlcv_patch.py"
    with open(patch_file, 'w') as f:
        f.write(patch)

    print(f"✅ Patch created: {patch_file}")
    print("To apply: Run this patch file on the VPS")