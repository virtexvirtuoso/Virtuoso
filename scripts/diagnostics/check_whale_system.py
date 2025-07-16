#!/usr/bin/env python3
"""
Check which whale monitoring system is running and verify its configuration.
"""

import sys
import os
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_whale_monitoring_system():
    """Check the whale monitoring system configuration and status."""
    
    logger.info("🔍 Checking Whale Monitoring System Status...")
    
    # 1. Check which processes are running
    logger.info("\n📋 Checking running processes...")
    
    try:
        import psutil
        
        # Look for Python processes that might be running the monitoring system
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if any(keyword in cmdline.lower() for keyword in ['main.py', 'monitor', 'whale', 'virtuoso']):
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if python_processes:
            logger.info("✅ Found Python monitoring processes:")
            for proc in python_processes:
                logger.info(f"  - PID {proc['pid']}: {proc['cmdline']}")
        else:
            logger.warning("⚠️  No Python monitoring processes found")
            
    except ImportError:
        logger.warning("psutil not available, skipping process check")
    
    # 2. Check configuration
    logger.info("\n⚙️  Checking whale activity configuration...")
    
    try:
        import yaml
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        whale_config = config.get('monitoring', {}).get('whale_activity', {})
        
        logger.info("✅ Whale activity configuration found:")
        logger.info(f"  - Enabled: {whale_config.get('enabled', 'NOT SET')}")
        logger.info(f"  - Accumulation threshold: ${whale_config.get('accumulation_threshold', 'NOT SET'):,}")
        logger.info(f"  - Distribution threshold: ${whale_config.get('distribution_threshold', 'NOT SET'):,}")
        logger.info(f"  - Imbalance threshold: {whale_config.get('imbalance_threshold', 'NOT SET'):.1%}" if whale_config.get('imbalance_threshold') else f"  - Imbalance threshold: NOT SET")
        logger.info(f"  - Min order count: {whale_config.get('min_order_count', 'NOT SET')}")
        logger.info(f"  - Market percentage: {whale_config.get('market_percentage', 'NOT SET'):.1%}" if whale_config.get('market_percentage') else f"  - Market percentage: NOT SET")
        logger.info(f"  - Cooldown: {whale_config.get('cooldown', 'NOT SET')} seconds")
        
        # Check if thresholds are reasonable
        if whale_config.get('enabled', False):
            logger.info("✅ Whale monitoring is ENABLED")
            
            accumulation_threshold = whale_config.get('accumulation_threshold', 0)
            if accumulation_threshold >= 5000000:
                logger.warning(f"⚠️  High accumulation threshold: ${accumulation_threshold:,} (very restrictive)")
            elif accumulation_threshold >= 1000000:
                logger.info(f"ℹ️  Moderate accumulation threshold: ${accumulation_threshold:,}")
            else:
                logger.info(f"ℹ️  Low accumulation threshold: ${accumulation_threshold:,}")
                
        else:
            logger.error("❌ Whale monitoring is DISABLED in config!")
            
    except Exception as e:
        logger.error(f"❌ Error reading configuration: {str(e)}")
    
    # 3. Check recent logs for whale activity
    logger.info("\n📄 Checking recent logs for whale monitoring activity...")
    
    log_files = ['logs/app.log', 'logs/monitoring.log', 'logs/whale.log']
    
    whale_log_entries = []
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    
                # Look for whale-related log entries in last 100 lines
                for line in lines[-100:]:
                    if any(keyword in line.lower() for keyword in ['whale', 'imbalance', '_monitor_whale_activity']):
                        whale_log_entries.append(line.strip())
                        
            except Exception as e:
                logger.warning(f"Could not read {log_file}: {str(e)}")
    
    if whale_log_entries:
        logger.info("✅ Found whale monitoring log entries:")
        for entry in whale_log_entries[-5:]:  # Show last 5 entries
            logger.info(f"  {entry}")
    else:
        logger.warning("⚠️  No whale monitoring log entries found in recent logs")
    
    # 4. Check Discord webhook configuration
    logger.info("\n🔗 Checking Discord webhook configuration...")
    
    try:
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if discord_webhook:
            logger.info("✅ Discord webhook URL is configured")
            # Don't log the actual URL for security
            if discord_webhook.startswith('https://discord.com/api/webhooks/'):
                logger.info("✅ Discord webhook URL format looks correct")
            else:
                logger.warning("⚠️  Discord webhook URL format may be incorrect")
        else:
            logger.warning("⚠️  DISCORD_WEBHOOK_URL environment variable not set")
            
    except Exception as e:
        logger.error(f"❌ Error checking Discord webhook: {str(e)}")
    
    # 5. Check which whale monitoring system files exist
    logger.info("\n📁 Checking whale monitoring system files...")
    
    monitor_file = 'src/monitoring/monitor.py'
    reporter_file = 'src/monitoring/market_reporter.py'
    
    if os.path.exists(monitor_file):
        logger.info("✅ MarketMonitor file found (robust whale system)")
        
        # Check if the robust _monitor_whale_activity method exists
        try:
            with open(monitor_file, 'r') as f:
                content = f.read()
                if '_monitor_whale_activity' in content and 'imbalance' in content:
                    logger.info("✅ Robust whale monitoring method found in MarketMonitor")
                else:
                    logger.warning("⚠️  Whale monitoring method may be incomplete in MarketMonitor")
        except Exception as e:
            logger.warning(f"Could not analyze MarketMonitor file: {str(e)}")
    else:
        logger.error("❌ MarketMonitor file not found!")
    
    if os.path.exists(reporter_file):
        logger.info("✅ MarketReporter file found (basic whale system)")
        
        # Check if this has whale activity calculation
        try:
            with open(reporter_file, 'r') as f:
                content = f.read()
                if '_calculate_whale_activity' in content:
                    if 'imbalance' in content:
                        logger.info("✅ MarketReporter has imbalance calculations")
                    else:
                        logger.warning("⚠️  MarketReporter whale method lacks imbalance calculations")
                else:
                    logger.info("ℹ️  MarketReporter does not have whale activity method")
        except Exception as e:
            logger.warning(f"Could not analyze MarketReporter file: {str(e)}")
    
    # 6. Summary and recommendations
    logger.info("\n📊 SYSTEM STATUS SUMMARY:")
    logger.info("=" * 50)
    
    # Check if MarketMonitor is likely the active system
    has_monitor = os.path.exists(monitor_file)
    config_enabled = whale_config.get('enabled', False) if 'whale_config' in locals() else False
    has_webhook = bool(os.getenv('DISCORD_WEBHOOK_URL'))
    has_logs = len(whale_log_entries) > 0
    
    if has_monitor and config_enabled:
        logger.info("✅ ROBUST WHALE SYSTEM (MarketMonitor) appears to be configured")
    else:
        logger.warning("⚠️  Robust whale system may not be properly configured")
    
    if has_webhook:
        logger.info("✅ Discord alerts are configured")
    else:
        logger.warning("⚠️  Discord alerts may not be working")
        
    if has_logs:
        logger.info("✅ Whale monitoring appears to be active (found log entries)")
    else:
        logger.warning("⚠️  No recent whale monitoring activity detected")
    
    # Provide specific recommendations
    logger.info("\n💡 RECOMMENDATIONS:")
    if not config_enabled:
        logger.info("1. Enable whale monitoring in config/config.yaml")
    if not has_webhook:
        logger.info("2. Set DISCORD_WEBHOOK_URL environment variable")
    if not has_logs:
        logger.info("3. Check if MarketMonitor is running (python src/main.py)")
        logger.info("4. Check if symbols are being monitored")
    
    logger.info("\n🎯 To verify whale monitoring is working:")
    logger.info("1. Check if main.py is running")
    logger.info("2. Look for 'Monitoring whale activity for [SYMBOL]' in logs")
    logger.info("3. Verify whale threshold calculations are producing non-zero values")
    
if __name__ == "__main__":
    check_whale_monitoring_system() 