#!/usr/bin/env python3
"""
Simple script to apply optimizations to the Bybit exchange on VPS.
This modifies the manager.py file to apply optimizations after exchange creation.
"""

# The patch to apply
patch_content = '''
# Find the line after exchange creation and add optimization
sed -i '/self.exchanges\[exchange_id\] = exchange/a\\
                    # Apply optimizations to Bybit exchange\\
                    if exchange_id == "bybit":\\
                        try:\\
                            # Increase timeouts for high-latency environment\\
                            import aiohttp\\
                            exchange.timeout = aiohttp.ClientTimeout(total=60, connect=20, sock_read=30)\\
                            if hasattr(exchange, "connector") and exchange.connector:\\
                                exchange.connector._limit_per_host = 30\\
                            self.logger.info("Applied timeout optimizations to Bybit exchange")\\
                        except Exception as e:\\
                            self.logger.warning(f"Failed to apply optimizations: {e}")' src/core/exchanges/manager.py
'''

import subprocess
import sys

# Execute on VPS
cmd = f'ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && {patch_content}"'

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    print("Successfully applied optimizations to exchange manager")
else:
    print(f"Failed to apply patch: {result.stderr}")
    sys.exit(1)