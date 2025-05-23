#!/usr/bin/env python3
"""
Simple script to test the long/short ratio implementation with Bybit API.
"""
import asyncio
import json
import logging
import requests
import time
from src.core.exchanges.bybit import BybitExchange
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LSR_Test")

class TestLSR:
    def __init__(self):
        self.logger = logger
    
    async def fetch_lsr_direct(self, symbol="BTCUSDT"):
        """Fetch LSR data directly from Bybit API without authentication"""
        url = f"https://api.bybit.com/v5/market/account-ratio"
        params = {
            'category': 'linear',
            'symbol': symbol,
            'period': '5min',
            'limit': 1
        }
        
        self.logger.info(f"Fetching LSR data from {url} with params {params}")
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            self.logger.info(f"Raw API response: {json.dumps(data, indent=2)}")
            
            if data.get('retCode') != 0:
                self.logger.error(f"API error: {data.get('retMsg')}")
                return None
            
            ratio_data = data.get('result', {}).get('list', [])
            if not ratio_data:
                self.logger.warning("No LSR data found")
                return None
            
            # Process the data similar to how the exchange class does it
            latest = ratio_data[0]
            
            # Convert string values to float and multiply by 100 for percentages
            buy_ratio = float(latest.get('buyRatio', '0.5')) * 100
            sell_ratio = float(latest.get('sellRatio', '0.5')) * 100
            timestamp = int(latest.get('timestamp', time.time() * 1000))
            
            processed_data = {
                'symbol': symbol,
                'long': buy_ratio,
                'short': sell_ratio,
                'timestamp': timestamp
            }
            
            self.logger.info(f"Processed LSR data: {json.dumps(processed_data, indent=2)}")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error fetching LSR data: {str(e)}")
            return None
    
    def calculate_lsr_score(self, lsr_data):
        """Calculate LSR score similar to sentiment_indicators.py"""
        if not lsr_data:
            return 50.0  # Neutral score
        
        long_ratio = float(lsr_data.get('long', 50.0))
        short_ratio = float(lsr_data.get('short', 50.0))
        
        self.logger.debug(f"Calculating score with Long: {long_ratio}, Short: {short_ratio}")
        
        if long_ratio == 0 and short_ratio == 0:
            return 50.0
        
        total = long_ratio + short_ratio
        long_percentage = (long_ratio / total) if total > 0 else 0.5
        
        # Convert to score (0-100)
        score = long_percentage * 100
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        self.logger.info(f"Long percentage: {long_percentage:.3f}, Final Score: {score:.2f}")
        return score

async def test_lsr():
    tester = TestLSR()
    
    # Fetch LSR data directly from API
    symbol = "BTCUSDT"
    lsr_data = await tester.fetch_lsr_direct(symbol)
    
    # Calculate LSR score
    lsr_score = tester.calculate_lsr_score(lsr_data)
    logger.info(f"LSR Score for {symbol}: {lsr_score}")
    
    # Test with direct test cases
    logger.info("Testing direct test cases:")
    
    # Test case 1: 60/40 long/short
    test_case_1 = {
        'symbol': symbol,
        'long': 60.0,
        'short': 40.0
    }
    score_1 = tester.calculate_lsr_score(test_case_1)
    logger.info(f"Test case 1 (60/40): Score = {score_1}")
    
    # Test case 2: 40/60 long/short
    test_case_2 = {
        'symbol': symbol,
        'long': 40.0,
        'short': 60.0
            }
    score_2 = tester.calculate_lsr_score(test_case_2)
    logger.info(f"Test case 2 (40/60): Score = {score_2}")
    
    # Test case 3: 50/50 long/short
    test_case_3 = {
        'symbol': symbol,
        'long': 50.0,
        'short': 50.0
            }
    score_3 = tester.calculate_lsr_score(test_case_3)
    logger.info(f"Test case 3 (50/50): Score = {score_3}")

if __name__ == "__main__":
    asyncio.run(test_lsr()) 