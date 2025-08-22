#!/usr/bin/env python3
"""Fix WebSocket timeout issues by adding proper timeout configuration"""

import os
import sys

def fix_websocket_manager():
    """Fix the WebSocket manager timeout issues"""
    
    websocket_manager_path = "/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py"
    
    # Read the current file
    with open(websocket_manager_path, 'r') as f:
        lines = f.readlines()
    
    # Find and replace the _create_connection method
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Add timeout import at the top if not present
        if i == 0 and "import aiohttp" in lines[1]:
            new_lines.append("import asyncio\n")
            new_lines.append("import aiohttp\n")
            new_lines.append("from aiohttp import ClientTimeout\n")  # Add timeout import
            i = 3  # Skip original imports
            continue
            
        # Fix the _create_connection method
        if "async def _create_connection(self, topics: List[str], connection_id: str)" in line:
            # Keep the method signature
            new_lines.append(line)
            
            # Skip to the try block
            while i < len(lines) and "try:" not in lines[i]:
                new_lines.append(lines[i])
                i += 1
            
            # Insert the improved connection code
            new_lines.append("        try:\n")
            new_lines.append("            # Configure timeout settings\n")
            new_lines.append("            timeout = ClientTimeout(\n")
            new_lines.append("                total=30,  # Total timeout for the entire request\n")
            new_lines.append("                connect=10,  # Connection timeout\n")
            new_lines.append("                sock_connect=10,  # Socket connection timeout\n")
            new_lines.append("                sock_read=30  # Socket read timeout\n")
            new_lines.append("            )\n")
            new_lines.append("            \n")
            new_lines.append("            # Create session with timeout configuration\n")
            new_lines.append("            connector = aiohttp.TCPConnector(\n")
            new_lines.append("                limit=100,  # Connection pool limit\n")
            new_lines.append("                limit_per_host=30,  # Per-host connection limit\n")
            new_lines.append("                force_close=False,  # Keep connections alive\n")
            new_lines.append("                enable_cleanup_closed=True  # Cleanup closed connections\n")
            new_lines.append("            )\n")
            new_lines.append("            \n")
            new_lines.append("            session = aiohttp.ClientSession(\n")
            new_lines.append("                timeout=timeout,\n")
            new_lines.append("                connector=connector\n")
            new_lines.append("            )\n")
            new_lines.append("            \n")
            new_lines.append("            # Connect with timeout and retry logic\n")
            new_lines.append("            max_retries = 3\n")
            new_lines.append("            retry_delay = 2\n")
            new_lines.append("            \n")
            new_lines.append("            for attempt in range(max_retries):\n")
            new_lines.append("                try:\n")
            new_lines.append("                    ws = await asyncio.wait_for(\n")
            new_lines.append("                        session.ws_connect(\n")
            new_lines.append("                            self.ws_url,\n")
            new_lines.append("                            heartbeat=30,\n")
            new_lines.append("                            autoping=True,\n")
            new_lines.append("                            max_msg_size=0  # No message size limit\n")
            new_lines.append("                        ),\n")
            new_lines.append("                        timeout=15  # WebSocket connection timeout\n")
            new_lines.append("                    )\n")
            new_lines.append("                    break  # Connection successful\n")
            new_lines.append("                except asyncio.TimeoutError:\n")
            new_lines.append("                    if attempt < max_retries - 1:\n")
            new_lines.append("                        logger.warning(f\"WebSocket connection timeout (attempt {attempt + 1}/{max_retries}), retrying...\")\n")
            new_lines.append("                        await asyncio.sleep(retry_delay)\n")
            new_lines.append("                        retry_delay *= 2  # Exponential backoff\n")
            new_lines.append("                    else:\n")
            new_lines.append("                        logger.error(f\"WebSocket connection failed after {max_retries} attempts\")\n")
            new_lines.append("                        await session.close()\n")
            new_lines.append("                        raise\n")
            new_lines.append("                except Exception as e:\n")
            new_lines.append("                    logger.error(f\"WebSocket connection error: {e}\")\n")
            new_lines.append("                    await session.close()\n")
            new_lines.append("                    raise\n")
            
            # Skip the original session and ws creation lines
            while i < len(lines):
                if "await ws.send_json(subscription_message)" in lines[i]:
                    break
                i += 1
            
            # Continue with the rest of the method
            continue
            
        new_lines.append(line)
        i += 1
    
    # Write the fixed file
    with open(websocket_manager_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ WebSocket manager timeout issues fixed")
    print("Added:")
    print("  - Proper timeout configuration for ClientSession")
    print("  - Connection timeout for ws_connect")
    print("  - Retry logic with exponential backoff")
    print("  - Better connection pool management")

if __name__ == "__main__":
    # Check if running on VPS
    if not os.path.exists("/home/linuxuser/trading/Virtuoso_ccxt"):
        print("❌ This script should be run on the VPS")
        sys.exit(1)
    
    fix_websocket_manager()