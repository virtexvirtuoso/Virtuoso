#!/usr/bin/env python3
"""
Test script to check quarterly futures symbol formats on Bybit
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_quarterly_futures():
    """Test various Bybit quarterly futures symbol formats"""
    try:
        symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'AVAX']
        
        for base_asset in symbols:
            current_year = datetime.now().year % 100
            current_month = datetime.now().month
            year = datetime.now().year
            
            # Get clean base asset
            base_asset_clean = base_asset.strip()
            
            # Try unified formats first (MMDD format)
            def get_last_friday_of_month(year, month):
                """Get the last Friday of a given month"""
                if month == 12:
                    from datetime import datetime, timedelta
                    last_day = datetime(year, 12, 31)
                else:
                    from datetime import datetime, timedelta
                    last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                
                # Find the last Friday
                offset = (4 - last_day.weekday()) % 7  # Friday is 4
                last_friday = last_day - timedelta(days=offset) if offset != 0 else last_day
                return last_friday
            
            unified_quarterly_patterns = []
            
            # June quarterly
            if current_month <= 6:
                june_date = get_last_friday_of_month(year, 6)
                june_pattern = f"{base_asset_clean}USDT{june_date.month:02d}{june_date.day:02d}"
                unified_quarterly_patterns.append(june_pattern)
            
            # September quarterly
            if current_month <= 9:
                sept_date = get_last_friday_of_month(year, 9)
                sept_pattern = f"{base_asset_clean}USDT{sept_date.month:02d}{sept_date.day:02d}"
                unified_quarterly_patterns.append(sept_pattern)
            
            # December quarterly
            dec_date = get_last_friday_of_month(year, 12)
            dec_pattern = f"{base_asset_clean}USDT{dec_date.month:02d}{dec_date.day:02d}"
            unified_quarterly_patterns.append(dec_pattern)
            
            # Old inverse patterns
            inverse_quarterly_patterns = [
                f"{base_asset_clean}USDM{current_year}",
                f"{base_asset_clean}USDU{current_year}",
                f"{base_asset_clean}USDZ{current_year}"
            ]
            
            # Old USDT patterns with hyphens
            usdt_quarterly_patterns = []
            
            if current_month <= 6:
                june_date = get_last_friday_of_month(year, 6)
                usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{june_date.day}JUN{current_year}")
            
            if current_month <= 9:
                sept_date = get_last_friday_of_month(year, 9)
                usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{sept_date.day}SEP{current_year}")
            
            dec_date = get_last_friday_of_month(year, 12)
            usdt_quarterly_patterns.append(f"{base_asset_clean}USDT-{dec_date.day}DEC{current_year}")
            
            # Test all pattern formats
            all_patterns = unified_quarterly_patterns + inverse_quarterly_patterns + usdt_quarterly_patterns
            logger.info(f"Testing patterns for {base_asset}: {all_patterns}")
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_quarterly_futures()) 