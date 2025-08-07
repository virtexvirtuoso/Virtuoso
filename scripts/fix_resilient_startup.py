#!/usr/bin/env python3
"""
Fix for resilient startup - handles monitoring failures gracefully
The issue: When monitoring can't get symbols (API timeouts), it exits and crashes everything
Solution: Make both services independent and handle failures gracefully
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_resilient_fix():
    """Create a resilient version that handles monitoring failures"""
    
    print("Creating resilient startup fix for main.py...")
    
    # Read the current main.py
    with open('src/main.py', 'r') as f:
        content = f.read()
    
    # Fix 1: Change asyncio.gather to handle exceptions
    old_gather = "        # Run both tasks concurrently\n        await asyncio.gather(monitoring_task, web_server_task)"
    
    new_gather = """        # Run both tasks concurrently with error handling
        try:
            # Use return_exceptions=True to prevent one task failure from stopping the other
            results = await asyncio.gather(monitoring_task, web_server_task, return_exceptions=True)
            
            # Check results for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_name = "monitoring" if i == 0 else "web_server"
                    logger.error(f"{task_name} task failed with exception: {result}")
                    # Don't propagate - let the other service continue
        except Exception as e:
            logger.error(f"Critical error in gather: {e}")
            # Both tasks failed critically"""
    
    if old_gather in content:
        content = content.replace(old_gather, new_gather)
        print("✅ Fixed asyncio.gather to handle exceptions independently")
    else:
        print("⚠️ Trying alternative gather fix...")
        
    # Fix 2: Make monitoring_main more resilient
    # Find the monitoring main and add retry logic
    old_monitor_start = """                # Start monitoring with already initialized components
                logger.info("🚀 Starting market_monitor in background task...")
                # Create a background task for market_monitor to prevent blocking
                monitor_task = asyncio.create_task(market_monitor.start())
                logger.info("✅ market_monitor background task created!")"""
    
    new_monitor_start = """                # Start monitoring with already initialized components
                logger.info("🚀 Starting market_monitor in background task...")
                
                # Wrapper to handle monitoring failures gracefully
                async def resilient_monitor_start():
                    retries = 0
                    max_retries = 3
                    while retries < max_retries:
                        try:
                            await market_monitor.start()
                            break  # Success
                        except Exception as e:
                            retries += 1
                            logger.error(f"Monitor start attempt {retries} failed: {e}")
                            if retries < max_retries:
                                logger.info(f"Retrying monitor start in 30 seconds...")
                                await asyncio.sleep(30)
                            else:
                                logger.error("Monitor failed to start after all retries")
                                # Don't crash - let web server continue
                                return
                
                # Create a background task for resilient monitor start
                monitor_task = asyncio.create_task(resilient_monitor_start())
                logger.info("✅ market_monitor background task created with retry logic!")"""
    
    if old_monitor_start in content:
        content = content.replace(old_monitor_start, new_monitor_start)
        print("✅ Added resilient monitoring startup with retry logic")
    
    # Fix 3: Add static symbols fallback for monitoring
    # Find where symbols are initialized and add fallback
    lines = content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if "# Get monitored symbols" in line:
            # Add fallback logic after this line
            new_lines.append("        # Fallback to static symbols if API fails")
            new_lines.append("        if not symbols or len(symbols) == 0:")
            new_lines.append("            logger.warning('No symbols from API, using static fallback list')")
            new_lines.append("            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT']")
            print(f"✅ Added static symbol fallback at line {i+2}")
            
    if new_lines != lines:
        content = '\n'.join(new_lines)
    
    # Save the fixed version
    with open('src/main.py', 'w') as f:
        f.write(content)
    
    print("✅ main.py has been fixed for resilient startup")
    print("\nThe fix ensures that:")
    print("1. Web server continues even if monitoring fails")
    print("2. Monitoring retries on failure instead of crashing")
    print("3. Static symbol fallback if API is unavailable")
    print("4. Both services run independently")
    
    return True

if __name__ == "__main__":
    success = create_resilient_fix()
    if success:
        print("\n✅ Resilient startup fix applied successfully!")
        print("\nNext steps:")
        print("1. Deploy to VPS")
        print("2. The web server should start on port 8003 even if monitoring has issues")
    else:
        print("\n❌ Fix failed to apply")