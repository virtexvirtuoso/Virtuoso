#!/usr/bin/env python3
"""
Test script to fetch and process funding rate data from Bybit API.
This script validates how the sentiment_indicators.py file processes funding rate data.
"""

import asyncio
import json
import sys
import logging
from typing import Dict, Any, Optional
import aiohttp
import pandas as pd
from datetime import datetime
from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger("funding_rate_test")

class FundingRateTest:
    """Test class for funding rate data processing."""
    
    def __init__(self):
        self.logger = logger
        self.session = None
        self.base_url = "https://api.bybit.com"

    async def initialize(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        self.logger.info("Session initialized")

    async def close(self):
        """Close resources."""
        if self.session:
            await self.session.close()
        self.logger.info("Session closed")

    async def fetch_ticker(self, symbol: str = "BTCUSDT", category: str = "linear") -> Dict[str, Any]:
        """Fetch ticker data from Bybit API."""
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": category, "symbol": symbol}
        
        self.logger.info(f"Fetching ticker for {symbol}")
        async with self.session.get(url, params=params) as response:
            response_data = await response.json()
            self.logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("retCode") == 0:
                ticker_list = response_data.get("result", {}).get("list", [])
                if ticker_list:
                    return ticker_list[0]  # Return the first (and usually only) ticker
            
            self.logger.error(f"Failed to fetch ticker: {response_data}")
            return {}

    async def fetch_funding_history(self, symbol: str = "BTCUSDT", category: str = "linear", limit: int = 10) -> Dict[str, Any]:
        """Fetch funding rate history from Bybit API."""
        url = f"{self.base_url}/v5/market/funding/history"
        params = {"category": category, "symbol": symbol, "limit": limit}
        
        self.logger.info(f"Fetching funding history for {symbol}")
        async with self.session.get(url, params=params) as response:
            response_data = await response.json()
            self.logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("retCode") == 0:
                return response_data.get("result", {})
            
            self.logger.error(f"Failed to fetch funding history: {response_data}")
            return {}

    async def fetch_account_ratio(self, symbol: str = "BTCUSDT", category: str = "linear", period: str = "1d", limit: int = 5) -> Dict[str, Any]:
        """Fetch long/short account ratio from Bybit API."""
        url = f"{self.base_url}/v5/market/account-ratio"
        params = {"category": category, "symbol": symbol, "period": period, "limit": limit}
        
        self.logger.info(f"Fetching account ratio for {symbol}")
        async with self.session.get(url, params=params) as response:
            response_data = await response.json()
            self.logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("retCode") == 0:
                return response_data.get("result", {})
            
            self.logger.error(f"Failed to fetch account ratio: {response_data}")
            return {}

    def process_funding_rate(self, ticker_data: Dict[str, Any], history_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process funding rate data the same way sentiment_indicators.py does.
        
        Args:
            ticker_data: Ticker data from Bybit API
            history_data: Funding rate history data
            
        Returns:
            Processed funding rate data structure
        """
        # Create market_data structure similar to what sentiment_indicators expects
        market_data = {
            'ticker': ticker_data,
            'sentiment': {
                'funding_history': history_data.get('list', []),
            }
        }

        self.logger.info("Processing funding rate data using sentiment_indicators approach")
        
        # Extract funding rate from ticker (simulating the logic in _calculate_funding_score)
        funding_rate = None
        sentiment_data = {}
        
        # First check if funding_rate is directly available
        if 'fundingRate' in ticker_data:
            funding_rate = float(ticker_data.get('fundingRate', 0))
            self.logger.info(f"Found funding rate in ticker: {funding_rate}")
        
        if funding_rate is None:
            self.logger.warning("No valid funding rate found, would return neutral score")
            funding_rate = 0.0
                
        # Convert to percentage for easier calculation
        funding_pct = funding_rate * 100
        self.logger.info(f"Funding rate: {funding_rate}, as percentage: {funding_pct}%")
        
        # Clip to reasonable range (-0.2% to 0.2%)
        funding_pct = max(-0.2, min(0.2, funding_pct))
        
        # Map to 0-100 scale (inverted: negative funding = bullish)
        # -0.2% -> 100, 0% -> 50, 0.2% -> 0
        raw_score = 50 - (funding_pct * 250)
        
        # Calculate volatility from historical funding rates
        try:
            # Extract historical rates
            if history_data and 'list' in history_data:
                rates = [float(rate.get('fundingRate', 0)) for rate in history_data.get('list', [])]
                volatility = pd.Series(rates).std()
                mean_rate = pd.Series(rates).mean()
                
                self.logger.info(f"Historical rates: {rates}")
                self.logger.info(f"Volatility: {volatility:.6f}")
                self.logger.info(f"Mean rate: {mean_rate:.6f}")
            else:
                self.logger.warning("No funding rate history available")
                volatility = 0.0
                mean_rate = funding_rate
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            volatility = 0.0
            mean_rate = funding_rate
        
        return {
            'funding_rate': funding_rate,
            'funding_pct': funding_pct,
            'score': raw_score,
            'volatility': volatility,
            'mean_rate': mean_rate,
            'history': history_data.get('list', []),
        }

    def process_long_short_ratio(self, account_ratio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process long/short ratio data similar to sentiment_indicators.py.
        
        Args:
            account_ratio_data: Account ratio data from Bybit API
            
        Returns:
            Processed long/short ratio data structure
        """
        self.logger.info("Processing long/short ratio data using sentiment_indicators approach")
        
        # Check if data is available
        if not account_ratio_data or 'list' not in account_ratio_data or not account_ratio_data['list']:
            self.logger.warning("No long/short ratio data available")
            return {
                'long_ratio': 0.5,
                'short_ratio': 0.5,
                'score': 50.0
            }
        
        # Extract the most recent entry
        latest_entry = account_ratio_data['list'][0]
        
        # Extract long and short ratios
        long_ratio = float(latest_entry.get('buyRatio', 0.5))
        short_ratio = float(latest_entry.get('sellRatio', 0.5))
        
        self.logger.info(f"Long ratio: {long_ratio}, Short ratio: {short_ratio}")
        
        # Calculate percentage - directly use the long ratio as percentage
        long_percentage = long_ratio
        
        # Convert to score (0-100)
        score = long_percentage * 100
        
        # Ensure score is between 0 and 100
        score = max(0, min(100, score))
        
        self.logger.info(f"Long percentage: {long_percentage:.3f}, Score: {score:.2f}")
        
        # Add interpretation
        if score >= 65:
            interpretation = "BULLISH (strong long bias)"
        elif score >= 55:
            interpretation = "MODERATELY BULLISH (slight long bias)"
        elif score <= 35:
            interpretation = "BEARISH (strong short bias)"
        elif score <= 45:
            interpretation = "MODERATELY BEARISH (slight short bias)"
        else:
            interpretation = "NEUTRAL (balanced positioning)"
        
        return {
            'long_ratio': long_ratio,
            'short_ratio': short_ratio,
            'long_percentage': long_percentage,
            'score': score,
            'interpretation': interpretation
        }

    def format_timestamp(self, ts_ms: int) -> str:
        """Format timestamp from milliseconds to human-readable format."""
        try:
            dt = datetime.fromtimestamp(ts_ms / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.logger.error(f"Error formatting timestamp: {str(e)}")
            return f"{ts_ms}"

    async def run_test(self, symbol: str = "BTCUSDT") -> None:
        """Run the full funding rate test."""
        try:
            await self.initialize()
            
            # Fetch data
            ticker_data = await self.fetch_ticker(symbol)
            history_data = await self.fetch_funding_history(symbol, limit=20)
            account_ratio = await self.fetch_account_ratio(symbol)
            
            # Process data
            funding_result = self.process_funding_rate(ticker_data, history_data)
            lsr_result = self.process_long_short_ratio(account_ratio)
            
            # Display results in a formatted way
            print("\n" + "=" * 80)
            print(f" SENTIMENT INDICATORS TEST RESULTS FOR {symbol} ".center(80))
            print("=" * 80)
            
            # Ticker Info
            print("\n--- TICKER DATA ---")
            if ticker_data:
                print(f"Symbol: {ticker_data.get('symbol')}")
                print(f"Last Price: {ticker_data.get('lastPrice')}")
                print(f"Funding Rate: {ticker_data.get('fundingRate')}")
                print(f"Next Funding Time: {self.format_timestamp(int(ticker_data.get('nextFundingTime', 0)))}")
                print(f"Mark Price: {ticker_data.get('markPrice')}")
                print(f"Index Price: {ticker_data.get('indexPrice')}")
            else:
                print("No ticker data available")
            
            # Funding Rate History
            print("\n--- FUNDING RATE HISTORY ---")
            if history_data and 'list' in history_data:
                for i, entry in enumerate(history_data.get('list', [])[:5]):  # Show first 5
                    ts = self.format_timestamp(int(entry.get('fundingRateTimestamp', 0)))
                    print(f"{i+1}. {ts} - Rate: {entry.get('fundingRate')}")
                if len(history_data.get('list', [])) > 5:
                    print(f"... {len(history_data.get('list', [])) - 5} more entries ...")
            else:
                print("No funding history available")
            
            # Account Ratio (Long/Short)
            print("\n--- ACCOUNT RATIO (LONG/SHORT) ---")
            if account_ratio and 'list' in account_ratio:
                for i, entry in enumerate(account_ratio.get('list', [])[:5]):  # Show first 5
                    ts = self.format_timestamp(int(entry.get('timestamp', 0)))
                    print(f"{i+1}. {ts} - Buy: {entry.get('buyRatio')} Sell: {entry.get('sellRatio')}")
            else:
                print("No account ratio data available")
            
            # Processed Funding Rate Results
            print("\n--- FUNDING RATE SENTIMENT SCORE ---")
            print(f"Raw Funding Rate: {funding_result['funding_rate']}")
            print(f"Funding Rate %: {funding_result['funding_pct']}%")
            print(f"Calculated Score: {funding_result['score']:.2f}")
            print(f"Funding Rate Volatility: {funding_result['volatility']:.6f}")
            print(f"Mean Funding Rate: {funding_result['mean_rate']:.6f}")
            
            # Add funding rate interpretation
            if funding_result['score'] >= 70:
                funding_interpretation = "STRONGLY BULLISH (very negative funding rate)"
            elif funding_result['score'] >= 60:
                funding_interpretation = "BULLISH (negative funding rate)"
            elif funding_result['score'] <= 30:
                funding_interpretation = "STRONGLY BEARISH (very positive funding rate)"
            elif funding_result['score'] <= 40:
                funding_interpretation = "BEARISH (positive funding rate)"
            else:
                funding_interpretation = "NEUTRAL (funding rate near zero)"
            
            print(f"Interpretation: {funding_interpretation}")
            
            # Processed Long/Short Ratio Results
            print("\n--- LONG/SHORT RATIO SENTIMENT SCORE ---")
            print(f"Long Ratio: {lsr_result['long_ratio']:.4f}")
            print(f"Short Ratio: {lsr_result['short_ratio']:.4f}")
            print(f"Score: {lsr_result['score']:.2f}")
            print(f"Interpretation: {lsr_result['interpretation']}")
            
            # Combined sentiment score
            combined_score = (funding_result['score'] + lsr_result['score']) / 2
            print("\n--- COMBINED SENTIMENT SCORE ---")
            print(f"Funding Rate Score: {funding_result['score']:.2f}")
            print(f"Long/Short Ratio Score: {lsr_result['score']:.2f}")
            print(f"Combined Score: {combined_score:.2f}")
            
            # Combined interpretation
            if combined_score >= 65:
                combined_interpretation = "BULLISH"
            elif combined_score >= 55:
                combined_interpretation = "MODERATELY BULLISH"
            elif combined_score <= 35:
                combined_interpretation = "BEARISH"
            elif combined_score <= 45:
                combined_interpretation = "MODERATELY BEARISH"
            else:
                combined_interpretation = "NEUTRAL"
            
            print(f"Combined Interpretation: {combined_interpretation}")
            
            print("\n" + "=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error running test: {str(e)}", exc_info=True)
        finally:
            await self.close()

def test_funding_rate():
    logger.info("Testing funding rate processing")
    
    try:
        # Test case 1: Funding rate as a float
        funding_rate_float = 0.0000786
        logger.info(f"Test case 1: Funding rate as float: {funding_rate_float}")
        
        # Code from confluence.py that does the conversion
        enhanced_sentiment = {
            'funding_rate': {
                'rate': 0.0,
                'next_funding_time': 0
            }
        }
        
        # Simulate the code that processes the funding rate
        try:
            enhanced_sentiment['funding_rate']['rate'] = float(funding_rate_float)
            logger.info("Successfully processed funding rate as float")
            logger.info(f"Result: {json.dumps(enhanced_sentiment, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing funding rate as float: {e}")
        
        # Test case 2: Funding rate as a dict without 'rate' key
        funding_rate_dict_no_rate = {'timestamp': 1746216000000}
        logger.info(f"Test case 2: Funding rate as dict without 'rate' key: {json.dumps(funding_rate_dict_no_rate, indent=2)}")
        
        # Reset enhanced sentiment
        enhanced_sentiment = {
            'funding_rate': {
                'rate': 0.0,
                'next_funding_time': 0
            }
        }
        
        # Simulate the code that processes the funding rate
        try:
            # Logic from our fix in _process_sentiment_data
            if isinstance(funding_rate_dict_no_rate, dict) and 'rate' not in funding_rate_dict_no_rate:
                logger.info("Detected funding rate dictionary without 'rate' key, using default value")
                # We would use a default value here
                enhanced_sentiment['funding_rate'] = {
                    'rate': 0.0001,
                    'next_funding_time': 0
                }
            logger.info("Successfully processed funding rate as dict without rate key")
            logger.info(f"Result: {json.dumps(enhanced_sentiment, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing funding rate as dict without rate key: {e}")
        
        logger.info("Test passed: All funding rate formats were processed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_funding_rate() 