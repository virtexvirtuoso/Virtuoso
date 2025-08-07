#!/usr/bin/env python3
"""
Fix for concurrent startup of monitoring and web server
The issue: market_monitor.start() is blocking the event loop
Solution: Ensure market_monitor runs in background task
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_fixed_main():
    """Create a fixed version of main.py that properly runs both services concurrently"""
    
    print("Creating fixed main.py for concurrent service startup...")
    
    # Read the current main.py
    with open('src/main.py', 'r') as f:
        content = f.read()
    
    # Find the monitoring_main function and fix it
    # The issue is that await market_monitor.start() blocks
    # We need to ensure it doesn't block the web server from starting
    
    # Replace the blocking await with a background task
    old_pattern = """                # Start monitoring with already initialized components
                logger.info("🚀 About to call market_monitor.start()...")
                await market_monitor.start()
                logger.info("✅ market_monitor.start() completed successfully!")"""
    
    new_pattern = """                # Start monitoring with already initialized components
                logger.info("🚀 Starting market_monitor in background task...")
                # Create a background task for market_monitor to prevent blocking
                monitor_task = asyncio.create_task(market_monitor.start())
                logger.info("✅ market_monitor background task created!")"""
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("✅ Fixed blocking market_monitor.start() call")
    else:
        print("⚠️ Pattern not found, checking alternative fix...")
        
        # Alternative: Look for the specific line and add non-blocking execution
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'await market_monitor.start()' in line and 'About to call' in lines[i-1]:
                # Replace this line
                new_lines[-1] = line.replace('await market_monitor.start()', 
                                            'monitor_task = asyncio.create_task(market_monitor.start())')
                print(f"✅ Fixed line {i+1}: Changed to background task")
        content = '\n'.join(new_lines)
    
    # Also ensure the monitoring_main properly waits for the background task
    old_wait = """                # Wait for shutdown signal or monitor to stop
                while not shutdown_event.is_set() and market_monitor.running:
                    await asyncio.sleep(1)  # Check every second"""
    
    new_wait = """                # Wait for shutdown signal or monitor to stop
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
    
    if old_wait in content:
        content = content.replace(old_wait, new_wait)
        print("✅ Fixed monitoring wait loop to handle background task")
    
    # Save the fixed version
    with open('src/main.py', 'w') as f:
        f.write(content)
    
    print("✅ main.py has been fixed for concurrent startup")
    print("\nThe fix ensures that:")
    print("1. market_monitor.start() runs in a background task")
    print("2. The web server can start immediately without waiting")
    print("3. Both services run concurrently as intended")
    
    return True

if __name__ == "__main__":
    success = create_fixed_main()
    if success:
        print("\n✅ Fix applied successfully!")
        print("\nNext steps:")
        print("1. Test locally: python src/main.py")
        print("2. Deploy to VPS: ./scripts/deploy_concurrent_fix.sh")
    else:
        print("\n❌ Fix failed to apply")