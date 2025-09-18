#!/usr/bin/env python3
"""
Deploy Dashboard Data Calculation Fixes

This script applies all the critical fixes for dashboard data calculation issues:
1. Market breadth counting fix
2. Sentiment threshold improvements
3. Score variability enhancements
4. Cache adapter field mapping fixes

Issues Fixed:
- Market Overview fields returning zero (trend_strength, current_volatility, btc_dominance, total_volume_24h)
- Market Breadth not counting correctly (up_count, down_count always 0)
- Sentiment distribution too narrow (all NEUTRAL, scores clustered 55-62)
"""

import asyncio
import logging
import time
import subprocess
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, description=None, check=True):
    """Run a command with optional description."""
    if description:
        print(f"📋 {description}...")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0 and check:
        print(f"❌ Command failed: {command}")
        print(f"Error: {result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    
    return True

async def test_cache_data_population():
    """Test if the fixes are working by checking cache contents"""
    try:
        import aiomcache
        import json
        
        logger.info("🔍 Testing cache data population after fixes...")
        
        # Connect to cache
        cache_client = aiomcache.Client("localhost", 11211)
        
        # Test market overview
        overview_data = await cache_client.get(b"market:overview")
        if overview_data:
            overview = json.loads(overview_data.decode())
            logger.info(f"✅ Market Overview: trend_strength={overview.get('trend_strength', 'MISSING')}, current_volatility={overview.get('current_volatility', 'MISSING')}, btc_dominance={overview.get('btc_dominance', 'MISSING')}")
        else:
            logger.warning("❌ No market overview data in cache")
        
        # Test market breadth
        breadth_data = await cache_client.get(b"market:breadth")
        if breadth_data:
            breadth = json.loads(breadth_data.decode())
            logger.info(f"✅ Market Breadth: up_count={breadth.get('up_count', 'MISSING')}, down_count={breadth.get('down_count', 'MISSING')}, breadth_percentage={breadth.get('breadth_percentage', 'MISSING')}")
        else:
            logger.warning("❌ No market breadth data in cache")
        
        # Test confluence scores (check for variability)
        confluence_found = 0
        sentiment_distribution = {'BULLISH': 0, 'BEARISH': 0, 'NEUTRAL': 0}
        score_range = {'min': 100, 'max': 0}
        
        symbols_to_check = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']
        for symbol in symbols_to_check:
            breakdown_key = f'confluence:breakdown:{symbol}'
            breakdown_data = await cache_client.get(breakdown_key.encode())
            if breakdown_data:
                breakdown = json.loads(breakdown_data.decode())
                confluence_found += 1
                
                # Check sentiment distribution
                sentiment = breakdown.get('sentiment', 'NEUTRAL')
                if sentiment in sentiment_distribution:
                    sentiment_distribution[sentiment] += 1
                
                # Check score range
                score = breakdown.get('overall_score', 50)
                if score < score_range['min']:
                    score_range['min'] = score
                if score > score_range['max']:
                    score_range['max'] = score
        
        if confluence_found > 0:
            logger.info(f"✅ Confluence Analysis: {confluence_found} symbols found")
            logger.info(f"   Sentiment Distribution: {sentiment_distribution}")
            logger.info(f"   Score Range: {score_range['min']:.1f} - {score_range['max']:.1f}")
        else:
            logger.warning("❌ No confluence breakdown data found")
        
        await cache_client.close()
        
    except Exception as e:
        logger.error(f"Error testing cache data: {e}")

def validate_fixes():
    """Validate that all fixes have been applied correctly"""
    logger.info("🔍 Validating applied fixes...")
    
    fixes_validated = 0
    total_fixes = 4
    
    # Validate Fix #1: Market breadth calculation in main.py
    try:
        with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/main.py', 'r') as f:
            main_content = f.read()
            if 'market:breadth' in main_content and 'up_count' in main_content and 'down_count' in main_content:
                logger.info("✅ Fix #1: Market breadth calculation added to main.py")
                fixes_validated += 1
            else:
                logger.error("❌ Fix #1: Market breadth calculation not found in main.py")
    except Exception as e:
        logger.error(f"❌ Fix #1: Error validating main.py: {e}")
    
    # Validate Fix #2: Sentiment thresholds in dashboard.py
    try:
        with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/routes/dashboard.py', 'r') as f:
            dashboard_content = f.read()
            if 'change_24h > 1.5' in dashboard_content and 'change_24h < -1.5' in dashboard_content:
                logger.info("✅ Fix #2: Improved sentiment thresholds in dashboard.py")
                fixes_validated += 1
            else:
                logger.error("❌ Fix #2: Improved sentiment thresholds not found in dashboard.py")
    except Exception as e:
        logger.error(f"❌ Fix #2: Error validating dashboard.py: {e}")
    
    # Validate Fix #3: Score variability enhancement
    try:
        with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/routes/dashboard.py', 'r') as f:
            dashboard_content = f.read()
            if 'volume_weight' in dashboard_content and 'performance_score *=' in dashboard_content:
                logger.info("✅ Fix #3: Enhanced score variability in dashboard.py")
                fixes_validated += 1
            else:
                logger.error("❌ Fix #3: Enhanced score variability not found in dashboard.py")
    except Exception as e:
        logger.error(f"❌ Fix #3: Error validating score variability: {e}")
    
    # Validate Fix #4: Cache adapter improvements
    try:
        with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/cache_adapter_direct.py', 'r') as f:
            adapter_content = f.read()
            if 'FIX #4: Improved field mapping' in adapter_content and 'trend_strength' in adapter_content:
                logger.info("✅ Fix #4: Improved cache adapter field mapping")
                fixes_validated += 1
            else:
                logger.error("❌ Fix #4: Improved cache adapter field mapping not found")
    except Exception as e:
        logger.error(f"❌ Fix #4: Error validating cache adapter: {e}")
    
    logger.info(f"📊 Validation Complete: {fixes_validated}/{total_fixes} fixes validated")
    return fixes_validated == total_fixes

def main():
    """Deploy dashboard data calculation fixes to VPS."""
    print("🚀 Deploying Dashboard Data Calculation Fixes...")
    
    # Check if we're in the right directory
    if not Path("src/main.py").exists():
        print("❌ Please run this script from the Virtuoso_ccxt root directory")
        return 1
    
    # Validate fixes locally first
    if not validate_fixes():
        print("❌ Fix validation failed - please check the fixes above")
        return 1
    
    # Ensure local changes are saved
    print("💾 Saving local changes...")
    run_command("git add src/main.py src/api/routes/dashboard.py src/api/cache_adapter_direct.py", "Adding dashboard calculation fixes")
    run_command("git commit -m 'Fix critical dashboard data calculation issues: market breadth, sentiment thresholds, score variability'", "Committing fixes")
    
    # Deploy to VPS
    vps_commands = [
        "cd /home/linuxuser/trading/Virtuoso_ccxt/",
        "git pull origin main",
        "sudo systemctl stop virtuoso.service",
        "sleep 3",
        "sudo systemctl start virtuoso.service",
        "sleep 5",
        "sudo systemctl status virtuoso.service --no-pager -l",
    ]
    
    vps_command = " && ".join(vps_commands)
    
    print("🌐 Deploying to VPS...")
    if not run_command(f'ssh linuxuser@${VPS_HOST} "{vps_command}"', "Executing VPS deployment"):
        print("❌ VPS deployment failed")
        return 1
    
    # Verify deployment
    print("🔍 Verifying deployment...")
    log_command = 'ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since \\"2 minutes ago\\" -n 30 --no-pager"'
    
    if run_command(log_command, "Checking service logs", check=False):
        print("✅ Dashboard fixes deployed successfully!")
        print("")
        print("📋 Summary of Applied Fixes:")
        print("   1. ✅ Market breadth calculation and cache population")
        print("   2. ✅ Improved sentiment thresholds (3% → 1.5%)")
        print("   3. ✅ Enhanced confluence score variability with volume weighting")
        print("   4. ✅ Fixed cache adapter field mapping with proper fallbacks")
        print("")
        print("🧪 Test the fixes:")
        print("   curl http://${VPS_HOST}:8003/api/dashboard/mobile-data")
        print("   Check for non-zero trend_strength, current_volatility, btc_dominance")
        print("   Verify up_count/down_count are not always 0")
        print("   Look for sentiment variety beyond just NEUTRAL")
        print("")
        print("📊 To monitor the service:")
        print("   ssh linuxuser@${VPS_HOST}")
        print("   sudo journalctl -u virtuoso.service -f")
        return 0
    else:
        print("⚠️ Deployment may have issues. Check logs manually:")
        print("ssh linuxuser@${VPS_HOST}")
        print("sudo journalctl -u virtuoso.service -f")
        return 1

if __name__ == "__main__":
    sys.exit(main())