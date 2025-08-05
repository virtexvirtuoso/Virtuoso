#!/usr/bin/env python3
"""
Real-Time Alpha Opportunity Monitor

Production script for monitoring alpha opportunities across all timeframes.
Provides real-time alerts and actionable trading insights.
"""

import sys
import os
import asyncio
import logging
import signal
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import core modules
try:
    from src.monitoring.monitor import MarketMonitor
    from src.monitoring.alert_manager import AlertManager
    from src.monitoring.metrics_manager import MetricsManager
    from src.core.market.top_symbols import TopSymbolsManager
    from src.core.market.market_data_manager import MarketDataManager
    from src.core.exchanges.manager import ExchangeManager
    from src.core.validation.service import AsyncValidationService
    from src.config.manager import ConfigManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/alpha_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class AlphaOpportunityMonitor:
    """Production alpha opportunity monitoring system."""
    
    def __init__(self):
        self.config = None
        self.monitor = None
        self.running = False
        self.scan_count = 0
        self.total_opportunities = 0
        self.priority_stats = {'ultra_fast': 0, 'fast': 0, 'stable': 0}
        
    async def initialize(self):
        """Initialize the monitoring system."""
        try:
            logger.info("🚀 Starting Alpha Opportunity Monitor")
            logger.info("=" * 60)
            
            # Load configuration
            config_manager = ConfigManager()
            self.config = config_manager.get_config()
            
            # Validate alpha scanning is enabled
            alpha_config = self.config.get('alpha_scanning', {})
            if not alpha_config.get('enabled', False):
                logger.error("❌ Alpha scanning is disabled in configuration")
                return False
            
            logger.info(f"✅ Alpha scanning configuration loaded:")
            logger.info(f"   Scan interval: {alpha_config.get('interval_minutes', 15)} minutes")
            logger.info(f"   Timeframes: {alpha_config.get('timeframes', [])}")
            logger.info(f"   Performance tiers: {alpha_config.get('performance_tiers', {})}")
            
            # Initialize dependencies
            await self._initialize_dependencies()
            
            logger.info("✅ Alpha Opportunity Monitor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitor: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    async def _initialize_dependencies(self):
        """Initialize all required dependencies."""
        try:
            # Initialize exchange manager
            exchange_manager = ExchangeManager(self.config, logger)
            await exchange_manager.initialize()
            
            # Get primary exchange
            exchange = exchange_manager.get_primary_exchange()
            if not exchange:
                raise Exception("No primary exchange available")
            
            # Initialize validation service
            validation_service = AsyncValidationService()
            
            # Initialize alert manager
            alert_manager = AlertManager(self.config, logger)
            
            # Initialize top symbols manager
            top_symbols_manager = TopSymbolsManager(
                exchange_manager=exchange_manager,
                config=self.config,
                validation_service=validation_service
            )
            
            # Initialize market data manager
            market_data_manager = MarketDataManager(
                exchange=exchange,
                config=self.config,
                logger=logger
            )
            
            # Initialize metrics manager
            metrics_manager = MetricsManager(logger)
            
            # Initialize market monitor with alpha scanner
            self.monitor = MarketMonitor(
                exchange=exchange,
                config=self.config,
                alert_manager=alert_manager,
                top_symbols_manager=top_symbols_manager,
                market_data_manager=market_data_manager,
                metrics_manager=metrics_manager,
                logger=logger
            )
            
            # Verify alpha scanner is initialized
            if not hasattr(self.monitor, 'alpha_scanner') or self.monitor.alpha_scanner is None:
                raise Exception("Alpha scanner not properly initialized")
            
            logger.info("✅ All dependencies initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize dependencies: {str(e)}")
            raise
    
    async def start_monitoring(self):
        """Start the alpha opportunity monitoring loop."""
        self.running = True
        logger.info("🔍 Starting real-time alpha opportunity monitoring...")
        logger.info(f"⏰ Scanning every {self.monitor.alpha_scanner.interval_minutes} minutes")
        logger.info("📊 Monitoring for:")
        logger.info("   🔥 Ultra-fast opportunities (1m, 5m timeframes)")
        logger.info("   ⚡ Fast opportunities (30m timeframe)")  
        logger.info("   📈 Stable opportunities (4h timeframe)")
        logger.info("-" * 60)
        
        try:
            while self.running:
                await self._monitoring_cycle()
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            self.running = False
    
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle."""
        try:
            # Check if it's time to scan
            if not self.monitor.alpha_scanner.should_scan():
                return
            
            self.scan_count += 1
            scan_start = datetime.now(timezone.utc)
            
            logger.info(f"🔍 Alpha Scan #{self.scan_count} - {scan_start.strftime('%H:%M:%S UTC')}")
            
            # Execute alpha scan
            opportunities = await self.monitor.alpha_scanner.scan_for_opportunities(self.monitor)
            
            if opportunities:
                self.total_opportunities += len(opportunities)
                logger.info(f"🎯 Found {len(opportunities)} actionable alpha opportunities:")
                
                for i, opp in enumerate(opportunities, 1):
                    await self._process_opportunity(opp, i)
                
                # Update stats
                self._update_priority_stats(opportunities)
                
                # Send alerts if enabled
                if self.monitor.alpha_scanner.alerts_enabled:
                    await self._send_alpha_alerts(opportunities)
                
            else:
                logger.info("   No actionable opportunities found")
            
            # Log scan summary
            scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
            logger.info(f"   Scan completed in {scan_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring cycle: {str(e)}")
    
    async def _process_opportunity(self, opp, index: int):
        """Process and display an alpha opportunity."""
        priority_emoji = {
            'ultra_fast': '🔥',
            'fast': '⚡', 
            'stable': '📈'
        }
        
        # Determine priority from recommendation
        priority = 'medium'
        for p in ['ultra_fast', 'fast', 'stable']:
            if f'{p} priority' in opp.recommended_action:
                priority = p
                break
        
        emoji = priority_emoji.get(priority, '💡')
        
        logger.info(f"   {emoji} #{index}: {opp.symbol} - {opp.divergence_type.value.upper()}")
        logger.info(f"      Confidence: {opp.confidence:.1%} | Alpha: {opp.alpha_potential:.1%} | Risk: {opp.risk_level}")
        logger.info(f"      Duration: {opp.expected_duration} | Priority: {priority.upper()}")
        logger.info(f"      💡 {opp.trading_insight}")
        logger.info(f"      📋 Action: {opp.recommended_action}")
        
        # Show timeframe signals
        tf_signals = []
        for tf, signal in opp.timeframe_signals.items():
            tf_signals.append(f"{tf}:{signal:.2f}")
        logger.info(f"      🎯 Signals: {', '.join(tf_signals)}")
        
        logger.info("")  # Empty line for readability
    
    def _update_priority_stats(self, opportunities):
        """Update priority statistics."""
        for opp in opportunities:
            for priority in ['ultra_fast', 'fast', 'stable']:
                if f'{priority} priority' in opp.recommended_action:
                    self.priority_stats[priority] += 1
                    break
    
    async def _send_alpha_alerts(self, opportunities):
        """Send Discord alerts for alpha opportunities."""
        try:
            alert_manager = self.monitor.alert_manager
            
            for opp in opportunities:
                # Prepare alert data
                alert_data = {
                    'symbol': opp.symbol,
                    'type': opp.divergence_type.value,
                    'confidence': opp.confidence,
                    'alpha_potential': opp.alpha_potential,
                    'risk_level': opp.risk_level,
                    'expected_duration': opp.expected_duration,
                    'trading_insight': opp.trading_insight,
                    'recommended_action': opp.recommended_action,
                    'timeframe_signals': opp.timeframe_signals,
                    'entry_conditions': opp.entry_conditions,
                    'exit_conditions': opp.exit_conditions,
                    'timestamp': opp.timestamp
                }
                
                # Send alert
                await alert_manager.send_alpha_opportunity_alert(alert_data)
                self.monitor.alpha_scanner.total_alerts_sent += 1
                
        except Exception as e:
            logger.error(f"❌ Failed to send alpha alerts: {str(e)}")
    
    def print_statistics(self):
        """Print monitoring statistics."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 ALPHA MONITORING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total Scans: {self.scan_count}")
        logger.info(f"Total Opportunities: {self.total_opportunities}")
        logger.info(f"Alerts Sent: {self.monitor.alpha_scanner.total_alerts_sent if self.monitor else 0}")
        logger.info(f"Average per Scan: {self.total_opportunities/self.scan_count:.1f}" if self.scan_count > 0 else "N/A")
        
        logger.info("\n📈 Priority Distribution:")
        for priority, count in self.priority_stats.items():
            percentage = (count/self.total_opportunities*100) if self.total_opportunities > 0 else 0
            logger.info(f"   {priority.title()}: {count} ({percentage:.1f}%)")
        
        if self.monitor and self.monitor.alpha_scanner:
            scanner_stats = self.monitor.alpha_scanner.get_stats()
            logger.info(f"\n⚙️ Scanner Settings:")
            logger.info(f"   Interval: {scanner_stats['interval_minutes']} minutes")
            logger.info(f"   Timeframes: {scanner_stats['timeframes']}")
            logger.info(f"   Patterns: {scanner_stats['pattern_types']}")
    
    async def shutdown(self):
        """Gracefully shutdown the monitor."""
        logger.info("🛑 Shutting down Alpha Opportunity Monitor...")
        self.running = False
        
        # Print final statistics
        self.print_statistics()
        
        # Cleanup resources
        if self.monitor and hasattr(self.monitor, 'cleanup'):
            await self.monitor.cleanup()
        
        logger.info("✅ Alpha Opportunity Monitor stopped")

# Global monitor instance for signal handling
monitor_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global monitor_instance
    logger.info(f"Received signal {signum}")
    if monitor_instance:
        asyncio.create_task(monitor_instance.shutdown())

async def main():
    """Main entry point."""
    global monitor_instance
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize monitor
        monitor_instance = AlphaOpportunityMonitor()
        
        # Initialize and start monitoring
        if await monitor_instance.initialize():
            await monitor_instance.start_monitoring()
        else:
            logger.error("❌ Failed to initialize monitor")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Monitor interrupted by user")
    except Exception as e:
        logger.error(f"❌ Monitor crashed: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
    finally:
        if monitor_instance:
            await monitor_instance.shutdown()
    
    return 0

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Run the monitor
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 