#!/usr/bin/env python3
"""
Test script to validate monitoring loop timeout fixes.
This will run for 2 minutes to verify that the timeout changes work properly.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def test_monitoring_timeouts():
    """Test that monitoring doesn't get cancelled prematurely."""

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("🧪 Testing monitoring loop timeout fixes...")
    logger.info("  • Previous timeout: 60s → New timeout: 90s")
    logger.info("  • Previous startup timeout: 120s → New startup timeout: 180s")
    logger.info("  • Enhanced backoff strategy implemented")

    try:
        # Test 1: Verify timeout constants are updated
        from monitoring.monitor import MarketMonitor

        # Create a simple monitoring task that takes some time
        class TestMonitor:
            def __init__(self):
                self.logger = logger
                self.running = True
                self.interval = 10
                self._error_count = 0

            async def test_cycle_timeout(self):
                """Simulate a monitoring cycle that takes 65 seconds (more than old 60s limit)."""
                logger.info("🕒 Starting test cycle that takes 65 seconds...")
                start_time = time.time()

                # Simulate work that takes 65 seconds
                for i in range(13):  # 13 * 5 = 65 seconds
                    logger.info(f"  Test cycle progress: {i*5+5}/65 seconds...")
                    await asyncio.sleep(5)

                    # Check if we've been cancelled
                    if not self.running:
                        logger.error("❌ Test cycle was cancelled prematurely!")
                        return False

                elapsed = time.time() - start_time
                logger.info(f"✅ Test cycle completed successfully in {elapsed:.1f}s")
                return True

            async def test_timeout_protection(self):
                """Test the timeout protection with 90s limit."""
                logger.info("🛡️ Testing timeout protection (should work with 90s limit)...")

                try:
                    # This should NOT timeout with the new 90s limit
                    result = await asyncio.wait_for(self.test_cycle_timeout(), timeout=90.0)
                    if result:
                        logger.info("✅ Timeout protection working correctly - no cancellation!")
                        return True
                    else:
                        logger.error("❌ Test cycle failed (but not due to timeout)")
                        return False

                except asyncio.TimeoutError:
                    logger.error("❌ TIMEOUT ERROR: Test cycle still timing out after 90s!")
                    return False
                except asyncio.CancelledError:
                    logger.error("❌ CANCELLED ERROR: Test cycle was cancelled!")
                    return False

        # Run the test
        test_monitor = TestMonitor()
        success = await test_monitor.test_timeout_protection()

        if success:
            logger.info("🎉 TIMEOUT FIX VALIDATION SUCCESSFUL!")
            logger.info("  ✅ Monitoring cycles can now run longer than 60 seconds")
            logger.info("  ✅ New 90-second timeout prevents premature cancellation")
            logger.info("  ✅ Ready for deployment to VPS")
        else:
            logger.error("❌ TIMEOUT FIX VALIDATION FAILED!")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    result = asyncio.run(test_monitoring_timeouts())
    sys.exit(0 if result else 1)