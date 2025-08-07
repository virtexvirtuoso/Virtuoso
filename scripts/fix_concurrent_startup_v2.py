#!/usr/bin/env python3
"""
Fix for concurrent startup of monitoring and web server - Version 2
The issue: market_monitor.start() is blocking the event loop
Solution: Properly run market_monitor in background without breaking the wait loop
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_fixed_main():
    """Create a fixed version of main.py that properly runs both services concurrently"""
    
    print("Creating fixed main.py for concurrent service startup (v2)...")
    
    # Read the current main.py
    with open('src/main.py', 'r') as f:
        content = f.read()
    
    # Find the monitoring_main function and fix it properly
    # The issue is that we need to make monitor_task available in the right scope
    
    # Find and replace the entire monitoring_main function section
    old_block = """                # Start monitoring with already initialized components
                logger.info("🚀 Starting market_monitor in background task...")
                # Create a background task for market_monitor to prevent blocking
                monitor_task = asyncio.create_task(market_monitor.start())
                logger.info("✅ market_monitor background task created!")
                logger.info("Monitoring system running. Press Ctrl+C to stop.")
                
                # Wait for shutdown signal or monitor to stop
                while not shutdown_event.is_set():
                    if 'monitor_task' in locals():
                        if monitor_task.done():
                            # Monitor task completed, check if it failed
                            try:
                                await monitor_task  # This will raise if task failed
                            except Exception as e:
                                logger.error(f"Monitor task failed: {e}")
                                break
                    if not market_monitor.running:
                        break
                    await asyncio.sleep(1)  # Check every second"""
    
    new_block = """                # Start monitoring with already initialized components
                logger.info("🚀 Starting market_monitor in background task...")
                # Create a background task for market_monitor to prevent blocking
                monitor_task = asyncio.create_task(market_monitor.start())
                logger.info("✅ market_monitor background task created!")
                logger.info("Monitoring system running. Press Ctrl+C to stop.")
                
                # Wait for shutdown signal or monitor to stop
                while not shutdown_event.is_set():
                    # Check if monitor task is done
                    if monitor_task.done():
                        # Monitor task completed, check if it failed
                        try:
                            await monitor_task  # This will raise if task failed
                        except Exception as e:
                            logger.error(f"Monitor task failed: {e}")
                            break
                    if not market_monitor.running:
                        break
                    await asyncio.sleep(1)  # Check every second"""
    
    if old_block in content:
        content = content.replace(old_block, new_block)
        print("✅ Fixed monitor_task scope issue in wait loop")
    else:
        print("⚠️ Trying alternative fix approach...")
        
        # Alternative: Just fix the specific scope issue
        # Find the line with if 'monitor_task' in locals()
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            if "'monitor_task' in locals()" in line:
                # Skip this line and the next ones that depend on it
                print(f"✅ Removed problematic locals() check at line {i+1}")
                continue
            elif "if monitor_task.done():" in line and i > 0 and "'monitor_task'" in lines[i-1]:
                # This is part of the problematic block, indent it properly
                new_lines.append("                    if monitor_task.done():")
                print(f"✅ Fixed indentation at line {i+1}")
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)
    
    # Save the fixed version
    with open('src/main.py', 'w') as f:
        f.write(content)
    
    print("✅ main.py has been fixed for concurrent startup (v2)")
    print("\nThe fix ensures that:")
    print("1. market_monitor.start() runs in a background task")
    print("2. The monitor_task variable is properly scoped")
    print("3. Both services run concurrently as intended")
    
    return True

if __name__ == "__main__":
    success = create_fixed_main()
    if success:
        print("\n✅ Fix v2 applied successfully!")
        print("\nNext steps:")
        print("1. Deploy to VPS: ./scripts/deploy_concurrent_fix.sh")
    else:
        print("\n❌ Fix failed to apply")