import asyncio
import logging
import sys
import os
import time
from pathlib import Path
import ccxt.async_support as ccxt
from typing import Dict, Any

# Add the project root to the system path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.monitor import MarketMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('market_monitor_example.log')
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory
os.makedirs('logs', exist_ok=True)
os.makedirs('visualizations', exist_ok=True)

async def alert_callback(alert):
    """Callback function for alerts."""
    logger.warning(f"ALERT [{alert.level}]: {alert.message}")
    # In a real application, you might send alerts to Slack, email, etc.

async def main():
    """Run the market monitor example."""
    try:
        logger.info("Starting Market Monitor Example")
        
        # Initialize metrics manager
        metrics_manager = MetricsManager()
        
        # Initialize health monitor with metrics manager
        health_monitor = HealthMonitor(
            metrics_manager=metrics_manager,
            alert_callback=alert_callback,
            config={
                'check_interval_seconds': 10,  # Check every 10 seconds for demo purposes
                'cpu_warning_threshold': 70,
                'memory_warning_threshold': 70
            }
        )
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        logger.info("Health monitoring started")
        
        # Initialize exchange
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # Initialize market monitor
        market_monitor = MarketMonitor(
            logger=logger,
            metrics_manager=metrics_manager
        )
        
        # Set attributes directly
        market_monitor.exchange = exchange
        market_monitor.symbol = 'BTC/USDT'
        market_monitor.timeframes = {'ltf': '1m', 'mtf': '5m', 'htf': '1h'}
        
        # Fetch market data
        logger.info("Fetching market data...")
        market_data = await market_monitor.fetch_market_data()
        
        # Print market data summary
        logger.info(f"Market data fetched successfully: {market_data['fetch_success']}")
        logger.info(f"Fetch duration: {market_data['fetch_duration_seconds']:.2f}s")
        logger.info(f"Validation result: {market_data['validation_result']['overall_valid']}")
        
        # Print OHLCV summary
        for tf_key, df in market_data['ohlcv'].items():
            if not df.empty:
                logger.info(f"OHLCV {tf_key}: {len(df)} candles")
        
        # Print orderbook summary
        if market_data['orderbook']:
            bids_count = len(market_data['orderbook'].get('bids', []))
            asks_count = len(market_data['orderbook'].get('asks', []))
            logger.info(f"Orderbook: {bids_count} bids, {asks_count} asks")
        
        # Print trades summary
        if market_data['trades']:
            logger.info(f"Trades: {len(market_data['trades'])} trades")
        
        # Get health status
        health_status = health_monitor._get_health_status()
        logger.info(f"System health: {health_status.status}")
        logger.info(f"CPU Usage: {health_status.cpu_usage:.1f}%")
        logger.info(f"Memory Usage: {health_status.memory_usage:.1f}%")
        
        # Get API health summary
        api_health = health_monitor.get_api_health_summary()
        for exchange_id, health_data in api_health.items():
            logger.info(f"API Health for {exchange_id}: {health_data['status']}")
            logger.info(f"  Success rate: {health_data['success_rate']:.1%}")
            logger.info(f"  Avg response time: {health_data['avg_response_time']:.3f}s")
        
        # Simulate some activity to demonstrate health monitoring
        logger.info("Simulating activity for 30 seconds...")
        for i in range(3):
            logger.info(f"Fetch iteration {i+1}/3")
            market_data = await market_monitor.fetch_market_data()
            
            # Get updated health status
            health_status = health_monitor._get_health_status()
            logger.info(f"Updated health status: {health_status.status}")
            
            # Sleep for 10 seconds
            await asyncio.sleep(10)
        
        # Generate metrics summary
        metrics_summary = metrics_manager.generate_metrics_report()
        logger.info("Metrics Summary:")
        for category, metrics in metrics_summary.items():
            logger.info(f"  {category}:")
            for metric_name, value in metrics.items():
                logger.info(f"    {metric_name}: {value}")
        
        # Get active alerts
        active_alerts = health_monitor.get_active_alerts()
        if active_alerts:
            logger.info(f"Active Alerts ({len(active_alerts)}):")
            for alert in active_alerts:
                logger.info(f"  [{alert.level}] {alert.source}: {alert.message}")
        else:
            logger.info("No active alerts")
        
        # Clean up
        await exchange.close()
        await health_monitor.stop_monitoring()
        logger.info("Market Monitor Example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        logger.exception("Exception details:")
        
        # Clean up in case of error
        if 'exchange' in locals():
            await exchange.close()
        
        if 'health_monitor' in locals() and health_monitor.is_running:
            await health_monitor.stop_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example terminated by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.exception("Exception details:") 