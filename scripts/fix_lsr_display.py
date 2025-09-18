#!/usr/bin/env python3
"""
Fix LSR (Long/Short Ratio) display issue in confluence analysis.

The issue: LSR data is being fetched correctly from Bybit but showing as 50/50 in confluence.
This script adds logging and fixes to ensure proper data flow.
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_lsr_logging():
    """Add comprehensive LSR logging to the sentiment processor"""
    
    sentiment_file = "src/indicators/sentiment_indicators.py"
    
    # Read the current file
    with open(sentiment_file, 'r') as f:
        content = f.read()
    
    # Check if we already have enhanced logging
    if "[LSR-FIX]" in content:
        logger.info("LSR fix logging already in place")
        return
    
    # Find the calculate_long_short_ratio method and enhance logging
    lines = content.split('\n')
    new_lines = []
    in_lsr_method = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Add logging at the start of calculate_long_short_ratio
        if "def calculate_long_short_ratio(self, market_data:" in line:
            in_lsr_method = True
            # Insert comprehensive logging after the docstring
            for j in range(i+1, min(i+20, len(lines))):
                new_lines.append(lines[j])
                if '"""' in lines[j] and j > i+1:  # End of docstring
                    new_lines.append("        # [LSR-FIX] Enhanced logging for debugging")
                    new_lines.append("        self.logger.info(f'[LSR-FIX] Input market_data keys: {list(market_data.keys())}')")
                    new_lines.append("        if 'sentiment' in market_data:")
                    new_lines.append("            self.logger.info(f'[LSR-FIX] Sentiment data keys: {list(market_data[\"sentiment\"].keys())}')")
                    new_lines.append("            if 'long_short_ratio' in market_data['sentiment']:")
                    new_lines.append("                self.logger.info(f'[LSR-FIX] LSR data found in sentiment: {market_data[\"sentiment\"][\"long_short_ratio\"]}')")
                    break
    
    # Write the enhanced file
    with open(sentiment_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    logger.info(f"Enhanced LSR logging added to {sentiment_file}")

def fix_confluence_lsr_processing():
    """Fix the confluence analyzer to properly process LSR data"""
    
    confluence_file = "src/core/analysis/confluence.py"
    
    # Read the current file
    with open(confluence_file, 'r') as f:
        content = f.read()
    
    # Check if we already have the fix
    if "[LSR-FIX]" in content:
        logger.info("Confluence LSR fix already in place")
        return
    
    # Find where sentiment data is prepared and ensure LSR is passed correctly
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Look for where sentiment data is prepared
        if "sentiment_data = self._prepare_sentiment_data(market_data)" in line:
            # Add logging and ensure LSR is preserved
            new_lines.append("            # [LSR-FIX] Ensure LSR data is preserved")
            new_lines.append("            if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:")
            new_lines.append("                self.logger.info(f'[LSR-FIX] Preserving LSR data: {market_data[\"sentiment\"][\"long_short_ratio\"]}')")
            new_lines.append("                if 'sentiment' not in sentiment_data:")
            new_lines.append("                    sentiment_data['sentiment'] = {}")
            new_lines.append("                sentiment_data['sentiment']['long_short_ratio'] = market_data['sentiment']['long_short_ratio']")
    
    # Write the enhanced file
    with open(confluence_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    logger.info(f"Confluence LSR processing fix added to {confluence_file}")

def verify_lsr_in_dashboard_api():
    """Verify that LSR data is properly included in dashboard API responses"""
    
    dashboard_file = "src/api/routes/dashboard.py"
    
    # Read the current file
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Check if we have LSR verification
    if "[LSR-FIX]" in content:
        logger.info("Dashboard API LSR verification already in place")
        return
    
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Look for where confluence data is returned
        if "return confluence_data" in line or "return response" in line:
            # Add logging before return
            indent = len(line) - len(line.lstrip())
            spaces = ' ' * indent
            new_lines.insert(-1, f"{spaces}# [LSR-FIX] Log LSR data in response")
            new_lines.insert(-1, f"{spaces}if 'results' in confluence_data and 'sentiment' in confluence_data['results']:")
            new_lines.insert(-1, f"{spaces}    sentiment_data = confluence_data['results']['sentiment']")
            new_lines.insert(-1, f"{spaces}    if 'signals' in sentiment_data and 'long_short_ratio' in sentiment_data['signals']:")
            new_lines.insert(-1, f"{spaces}        logger.info(f'[LSR-FIX] Dashboard API returning LSR: {{sentiment_data[\"signals\"][\"long_short_ratio\"]}}')")
    
    # Write the enhanced file
    with open(dashboard_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    logger.info(f"Dashboard API LSR verification added to {dashboard_file}")

def main():
    """Run all LSR fixes"""
    logger.info("="*60)
    logger.info("Starting LSR Display Fix")
    logger.info("="*60)
    
    # Apply all fixes
    logger.info("\n1. Adding enhanced LSR logging to sentiment processor...")
    add_lsr_logging()
    
    logger.info("\n2. Fixing confluence LSR data processing...")
    fix_confluence_lsr_processing()
    
    logger.info("\n3. Adding LSR verification to dashboard API...")
    verify_lsr_in_dashboard_api()
    
    logger.info("\n" + "="*60)
    logger.info("LSR Display Fix Complete!")
    logger.info("="*60)
    logger.info("\nNext steps:")
    logger.info("1. Restart the web server")
    logger.info("2. Check the logs for [LSR-FIX] entries")
    logger.info("3. Verify LSR values are no longer 50/50")
    
    # Also create a test endpoint to directly check LSR
    test_script = """#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exchanges.bybit import BybitExchange
from src.config.config_loader import load_config

async def test_lsr():
    config = load_config()
    exchange = BybitExchange(config)
    
    # Test LSR for BTC
    lsr_data = await exchange._fetch_long_short_ratio('BTCUSDT')
    print(f"Direct LSR fetch for BTCUSDT: {lsr_data}")
    
    # Test full market data
    market_data = await exchange.fetch_market_data('BTCUSDT')
    if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
        print(f"LSR in market_data: {market_data['sentiment']['long_short_ratio']}")
    else:
        print("LSR not found in market_data!")

if __name__ == "__main__":
    asyncio.run(test_lsr())
"""
    
    with open("scripts/test_direct_lsr.py", "w") as f:
        f.write(test_script)
    os.chmod("scripts/test_direct_lsr.py", 0o755)
    
    logger.info("\nCreated test script: scripts/test_direct_lsr.py")
    logger.info("Run it to test direct LSR fetching from Bybit")

if __name__ == "__main__":
    main()