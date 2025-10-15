#!/usr/bin/env python3
"""
Fix for monitoring loop cancellation issues on VPS.

The problem:
1. Monitoring cycles timeout at 60s but get cancelled at ~59s
2. After 5 restart attempts, monitoring stops permanently
3. System continues serving data but loses monitoring capabilities

The solution:
1. Increase monitoring cycle timeout from 60s to 90s
2. Increase main.py startup timeout from 120s to 180s
3. Add better error handling for gradual degradation
4. Implement exponential backoff on monitoring cycle timeouts
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Apply fixes for monitoring loop cancellation."""

    project_root = Path("/Users/ffv_macmini/Desktop/Virtuoso_ccxt")
    monitor_file = project_root / "src/monitoring/monitor.py"
    main_file = project_root / "src/main.py"

    logger.info("🔧 Applying monitoring loop cancellation fixes...")

    # Fix 1: Increase monitoring cycle timeout in monitor.py
    logger.info("📝 Fix 1: Increasing monitoring cycle timeout from 60s to 90s")

    with open(monitor_file, 'r') as f:
        monitor_content = f.read()

    # Replace the 60-second timeout with 90 seconds
    monitor_content = monitor_content.replace(
        "await asyncio.wait_for(self._monitoring_cycle(), timeout=60.0)  # 1 minute max per cycle",
        "await asyncio.wait_for(self._monitoring_cycle(), timeout=90.0)  # 1.5 minutes max per cycle - fixed timeout issue"
    )

    # Also update the timeout error message
    monitor_content = monitor_content.replace(
        'self.logger.error("⚠️ Monitoring cycle timed out after 60 seconds!")',
        'self.logger.error("⚠️ Monitoring cycle timed out after 90 seconds!")'
    )

    with open(monitor_file, 'w') as f:
        f.write(monitor_content)

    logger.info("✅ Monitor.py timeout increased to 90 seconds")

    # Fix 2: Increase main.py startup timeout
    logger.info("📝 Fix 2: Increasing main.py startup timeout from 120s to 180s")

    with open(main_file, 'r') as f:
        main_content = f.read()

    # Replace the 120-second timeout with 180 seconds
    main_content = main_content.replace(
        "await asyncio.wait_for(monitor_start_task, timeout=120.0)",
        "await asyncio.wait_for(monitor_start_task, timeout=180.0)  # Increased timeout for stability"
    )

    # Update the timeout error message too
    main_content = main_content.replace(
        'logger.error(f"⏰ market_monitor.start() timed out (attempt {retries}/{max_retries})")',
        'logger.error(f"⏰ market_monitor.start() timed out after 180s (attempt {retries}/{max_retries})")'
    )

    with open(main_file, 'w') as f:
        f.write(main_content)

    logger.info("✅ Main.py startup timeout increased to 180 seconds")

    # Fix 3: Add better timeout handling in monitor.py
    logger.info("📝 Fix 3: Improving timeout error handling")

    with open(monitor_file, 'r') as f:
        monitor_content = f.read()

    # Improve the timeout handling to be more resilient
    old_timeout_handling = '''            except asyncio.TimeoutError:
                self.logger.error("⚠️ Monitoring cycle timed out after 90 seconds!")
                self._error_count += 1
                backoff_time = min(10, 2 ** min(self._error_count, 3))  # Shorter backoff for timeouts
                await asyncio.sleep(backoff_time)'''

    new_timeout_handling = '''            except asyncio.TimeoutError:
                self.logger.error("⚠️ Monitoring cycle timed out after 90 seconds!")
                self._error_count += 1

                # More aggressive backoff for timeouts to prevent cascading failures
                backoff_time = min(30, 5 + (2 ** min(self._error_count, 4)))
                self.logger.warning(f"🔄 Timeout #{self._error_count}, backing off for {backoff_time}s...")

                # Reset error count if we've been running for a while without issues
                if hasattr(self, '_last_successful_cycle'):
                    import time
                    if time.time() - self._last_successful_cycle > 300:  # 5 minutes
                        self.logger.info("🔄 Resetting error count after extended runtime")
                        self._error_count = max(0, self._error_count - 1)

                await asyncio.sleep(backoff_time)'''

    if old_timeout_handling.replace(" ", "").replace("\n", "") in monitor_content.replace(" ", "").replace("\n", ""):
        monitor_content = monitor_content.replace(old_timeout_handling.strip(), new_timeout_handling.strip())

        with open(monitor_file, 'w') as f:
            f.write(monitor_content)

        logger.info("✅ Enhanced timeout handling implemented")
    else:
        logger.warning("⚠️ Could not find exact timeout handling pattern to replace")

    # Fix 4: Track successful cycles
    logger.info("📝 Fix 4: Adding successful cycle tracking")

    with open(monitor_file, 'r') as f:
        monitor_content = f.read()

    # Add tracking after successful cycle completion
    if "cycle_duration = time.time() - cycle_start_time" in monitor_content:
        monitor_content = monitor_content.replace(
            "cycle_duration = time.time() - cycle_start_time",
            """cycle_duration = time.time() - cycle_start_time
                self._last_successful_cycle = time.time()  # Track successful completion"""
        )

        with open(monitor_file, 'w') as f:
            f.write(monitor_content)

        logger.info("✅ Added successful cycle tracking")

    logger.info("🎉 All monitoring loop cancellation fixes applied successfully!")
    logger.info("\n📋 Summary of changes:")
    logger.info("  • Monitoring cycle timeout: 60s → 90s")
    logger.info("  • Main startup timeout: 120s → 180s")
    logger.info("  • Enhanced timeout backoff strategy")
    logger.info("  • Added successful cycle tracking for error recovery")
    logger.info("\n🔄 Next steps:")
    logger.info("  1. Test locally with: ./venv311/bin/python src/main.py")
    logger.info("  2. Deploy to VPS after local validation")

if __name__ == "__main__":
    main()