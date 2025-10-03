from src.utils.task_tracker import create_tracked_task
#!/usr/bin/env python3
"""
Bitcoin Beta Report Scheduler

Automatically runs the Bitcoin Beta Analysis Report every 6 hours starting at 00:00 UTC.
Schedules: 00:00, 06:00, 12:00, 18:00 UTC daily.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, timezone
from typing import Optional
import threading

from .bitcoin_beta_report import BitcoinBetaReport

logger = logging.getLogger(__name__)

class BitcoinBetaScheduler:
    """
    Scheduler for Bitcoin Beta Analysis Reports.
    
    Runs reports every 6 hours starting at midnight UTC:
    - 00:00 UTC
    - 06:00 UTC  
    - 12:00 UTC
    - 18:00 UTC
    """
    
    def __init__(self, exchange_manager, top_symbols_manager, config, alert_manager=None):
        """
        Initialize the scheduler.
        
        Args:
            exchange_manager: Exchange manager instance
            top_symbols_manager: Top symbols manager instance
            config: System configuration
            alert_manager: Optional alert manager for notifications
        """
        self.exchange_manager = exchange_manager
        self.top_symbols_manager = top_symbols_manager
        self.config = config
        self.alert_manager = alert_manager
        self.logger = logging.getLogger(__name__)
        
        # Get bitcoin beta analysis configuration
        beta_config = config.get('bitcoin_beta_analysis', {})
        reports_config = beta_config.get('reports', {})
        
        # Get configurable schedule times
        self.schedule_times = reports_config.get('schedule_times', [
            "00:00", "06:00", "12:00", "18:00"
        ])
        self.schedule_enabled = reports_config.get('schedule_enabled', True)
        
        self.logger.info(f"Bitcoin Beta Scheduler configured with times: {self.schedule_times}")
        self.logger.info(f"Scheduling enabled: {self.schedule_enabled}")
        
        # Initialize the beta report generator
        self.beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config,
            alert_manager=alert_manager  # Pass alert manager to enable alpha opportunity alerts
        )
        
        # Scheduler state
        self.is_running = False
        self.scheduler_thread = None
        self.last_report_time = None
        self.last_report_path = None
        
    def start_scheduler(self):
        """Start the report scheduler."""
        try:
            if self.is_running:
                self.logger.warning("Scheduler is already running")
                return
                
            if not self.schedule_enabled:
                self.logger.info("Bitcoin Beta Report Scheduler is disabled in configuration")
                return
                
            self.logger.info("Starting Bitcoin Beta Report Scheduler")
            
            # Schedule the report to run at configured times
            for schedule_time in self.schedule_times:
                schedule.every().day.at(schedule_time).do(self._run_scheduled_report)
                self.logger.info(f"Scheduled Bitcoin Beta Report at {schedule_time} UTC")
            
            self.is_running = True
            
            # Start the scheduler in a separate thread
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            self.logger.info("Bitcoin Beta Report Scheduler started successfully")
            self.logger.info(f"Reports will be generated at: {', '.join(self.schedule_times)} UTC")
            
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
            
    def stop_scheduler(self):
        """Stop the report scheduler."""
        try:
            if not self.is_running:
                self.logger.warning("Scheduler is not running")
                return
                
            self.logger.info("Stopping Bitcoin Beta Report Scheduler")
            
            self.is_running = False
            schedule.clear()
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
                
            self.logger.info("Bitcoin Beta Report Scheduler stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {str(e)}")
            
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)
                
    def _run_scheduled_report(self):
        """Run a scheduled report."""
        try:
            current_time = datetime.now(timezone.utc)
            self.logger.info(f"Running scheduled Bitcoin Beta Report at {current_time}")
            
            # Run the report in an async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                pdf_path = loop.run_until_complete(self.beta_report.generate_report())
                
                if pdf_path:
                    self.last_report_time = current_time
                    self.last_report_path = pdf_path
                    
                    self.logger.info(f"✅ Scheduled Bitcoin Beta Report completed: {pdf_path}")
                    
                    # Send notification if alert manager is available
                    if self.alert_manager:
                        create_tracked_task(self._send_report_notification, name="_send_report_notification_task")
                        
                else:
                    self.logger.error("❌ Scheduled Bitcoin Beta Report failed")
                    
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"Error in scheduled report: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
    async def _send_report_notification(self, pdf_path: str):
        """Send notification about completed report."""
        try:
            if not self.alert_manager:
                return
                
            # Format proper alert message
            report_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            message = f"📊 Bitcoin Beta Analysis Report completed at {report_time}"
            
            # Create alert details
            alert_details = {
                'type': 'market_report',
                'report_type': 'bitcoin_beta_analysis',
                'report_path': pdf_path,
                'report_time': datetime.now(timezone.utc).isoformat(),
                'timestamp': int(time.time() * 1000)
            }
            
            # Send the alert using proper format
            await self.alert_manager.send_alert(
                level="INFO",
                message=message,
                details=alert_details,
                throttle=False  # Don't throttle report completion notifications
            )
            
            self.logger.info("Bitcoin Beta Report notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"Error sending report notification: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            
    async def run_manual_report(self) -> Optional[str]:
        """Run a manual report outside the schedule."""
        try:
            self.logger.info("Running manual Bitcoin Beta Report")
            
            pdf_path = await self.beta_report.generate_report()
            
            if pdf_path:
                self.logger.info(f"✅ Manual Bitcoin Beta Report completed: {pdf_path}")
                return pdf_path
            else:
                self.logger.error("❌ Manual Bitcoin Beta Report failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in manual report: {str(e)}")
            return None
            
    def get_status(self) -> dict:
        """Get scheduler status information."""
        return {
            'is_running': self.is_running,
            'last_report_time': self.last_report_time.isoformat() if self.last_report_time else None,
            'last_report_path': self.last_report_path,
            'next_scheduled_times': self.schedule_times,
            'schedule_info': {
                'frequency': 'Every 6 hours',
                'times': self.schedule_times,
                'timezone': 'UTC'
            }
        }
        
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        try:
            next_run = schedule.next_run()
            return next_run
        except Exception:
            return None


# Utility function to integrate with main system
async def initialize_beta_scheduler(exchange_manager, top_symbols_manager, config, alert_manager=None) -> BitcoinBetaScheduler:
    """
    Initialize and start the Bitcoin Beta Report Scheduler.
    
    Args:
        exchange_manager: Exchange manager instance
        top_symbols_manager: Top symbols manager instance
        config: System configuration
        alert_manager: Alert manager for notifications and alpha opportunity alerts
        
    Returns:
        BitcoinBetaScheduler: Initialized scheduler
    """
    try:
        scheduler = BitcoinBetaScheduler(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config,
            alert_manager=alert_manager  # Pass alert manager for full integration
        )
        
        # Start the scheduler
        scheduler.start_scheduler()
        
        if alert_manager:
            logger.info("Bitcoin Beta Report Scheduler initialized with AlertManager integration")
            logger.info("✅ Alpha opportunity alerts will be sent to Discord")
            logger.info("✅ Report completion notifications enabled")
        else:
            logger.info("Bitcoin Beta Report Scheduler initialized without AlertManager")
            logger.warning("⚠️ Alpha opportunity alerts will NOT be sent (no AlertManager)")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Error initializing Bitcoin Beta Scheduler: {str(e)}")
        raise


if __name__ == "__main__":
    # This would be called during system startup to enable automatic reporting
    pass 