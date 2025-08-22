#\!/usr/bin/env python3
"""Fix the startup issue where cleanup is called immediately"""

import os

def fix_main_py():
    main_path = "src/main.py"
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    # The issue is in monitoring_main - it's checking market_monitor.running before start() completes
    # Let's fix the logic
    
    # Find and fix the monitoring_main function
    old_code = """                # Wait for shutdown signal or monitor to stop
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
    
    new_code = """                # Wait for shutdown signal or monitor to stop
                while not shutdown_event.is_set():
                    # Check if monitor task is done
                    if monitor_task.done():
                        # Monitor task completed, check if it failed
                        try:
                            await monitor_task  # This will raise if task failed
                        except Exception as e:
                            logger.error(f"Monitor task failed: {e}")
                            break
                    # Don't check market_monitor.running here - let the monitor task handle its own lifecycle
                    await asyncio.sleep(1)  # Check every second"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ Fixed monitoring_main shutdown logic")
    else:
        print("⚠️  Could not find exact code block to fix")
        # Try alternative fix
        old_alt = "if not market_monitor.running:\n                        break"
        new_alt = "# Removed premature exit check - let monitor handle its own lifecycle"
        if old_alt in content:
            content = content.replace(old_alt, new_alt)
            print("✅ Applied alternative fix")
    
    # Also ensure the cleanup is only called when truly shutting down
    old_cleanup = """            finally:
                # Use centralized cleanup
                if shutdown_event.is_set() or (market_monitor and not market_monitor.running):
                    await cleanup_all_components()
                    logger.info("Monitoring cleanup completed")"""
    
    new_cleanup = """            finally:
                # Use centralized cleanup only on shutdown
                if shutdown_event.is_set():
                    await cleanup_all_components()
                    logger.info("Monitoring cleanup completed")"""
    
    if old_cleanup in content:
        content = content.replace(old_cleanup, new_cleanup)
        print("✅ Fixed cleanup condition")
    
    with open(main_path, 'w') as f:
        f.write(content)
    
    print("✅ main.py fixed")

if __name__ == "__main__":
    fix_main_py()
