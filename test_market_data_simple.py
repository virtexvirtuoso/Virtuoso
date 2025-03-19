import asyncio
import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSymbolsManager:
    """Mock implementation of the TopSymbolsManager for testing."""
    
    def __init__(self):
        self.test_data = self._load_test_data()
        
    def _load_test_data(self):
        """Load some test market data for various symbols."""
        data = {
            "BTC/USDT": {
                "price": 65000.0,
                "ticker": {
                    "last": 65000.0,
                    "high": 66500.0,
                    "low": 63500.0,
                    "volume": 1200000000.0,
                    "change": 0.05  # 5% change
                },
                "raw_ticker": {
                    "openInterest": 2500000000.0
                },
                "ohlcv": {
                    "base": {
                        "data": pd.DataFrame({
                            "open": [62000, 63000, 64000, 65000],
                            "high": [63000, 64000, 65000, 66500],
                            "low": [61000, 62000, 63000, 63500],
                            "close": [63000, 64000, 65000, 65000],
                            "volume": [1000000000, 1100000000, 1200000000, 1200000000]
                        })
                    }
                }
            },
            "ETH/USDT": {
                "price": 3500.0,
                "ticker": {
                    "last": 3500.0,
                    "high": 3600.0,
                    "low": 3400.0,
                    "volume": 800000000.0,
                    "change": 0.03  # 3% change
                },
                "raw_ticker": {
                    "openInterest": 1500000000.0
                },
                "ohlcv": {
                    "base": {
                        "data": pd.DataFrame({
                            "open": [3300, 3400, 3450, 3500],
                            "high": [3400, 3500, 3550, 3600],
                            "low": [3200, 3300, 3400, 3400],
                            "close": [3400, 3450, 3500, 3500],
                            "volume": [700000000, 750000000, 800000000, 800000000]
                        })
                    }
                }
            },
            "SOL/USDT": {
                "price": 150.0,
                "ticker": {
                    "last": 150.0,
                    "high": 155.0,
                    "low": 145.0,
                    "volume": 400000000.0,
                    "change": -0.02  # -2% change
                },
                "raw_ticker": {
                    "openInterest": 800000000.0
                },
                "ohlcv": {
                    "base": {
                        "data": pd.DataFrame({
                            "open": [160, 155, 152, 150],
                            "high": [165, 160, 155, 155],
                            "low": [155, 150, 148, 145],
                            "close": [155, 152, 150, 150],
                            "volume": [450000000, 420000000, 400000000, 400000000]
                        })
                    }
                }
            }
        }
        return data
    
    async def get_top_traded_symbols(self, limit: int = 10) -> List[str]:
        """Return a list of top traded symbols."""
        return list(self.test_data.keys())[:limit]
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for the specified symbol."""
        return self.test_data.get(symbol)

class MarketDataExtractor:
    """Test implementation for market data extraction and calculations."""
    
    def __init__(self):
        self.top_symbols_manager = MockSymbolsManager()
        self.logger = logger
        self.cache = {}
    
    async def test_extract_market_data(self):
        """Test the extract_market_data method."""
        test_symbols = await self.top_symbols_manager.get_top_traded_symbols(3)
        
        print("\n=== Testing Market Data Extraction ===")
        for symbol in test_symbols:
            market_data = await self.top_symbols_manager.get_market_data(symbol)
            metrics = await self._extract_market_data(market_data)
            
            print(f"\nExtracted data for {symbol}:")
            for key, value in metrics.items():
                formatted_value = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else value
                print(f"  {key}: {formatted_value}")
    
    async def test_market_regime(self):
        """Test the calculate_market_regime method."""
        test_symbols = await self.top_symbols_manager.get_top_traded_symbols(3)
        
        print("\n=== Testing Market Regime Calculation ===")
        regime_data = await self._calculate_market_regime(test_symbols)
        
        print("\nMarket Regime Results:")
        for key, value in regime_data.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    async def test_market_overview(self):
        """Test the calculate_market_overview method."""
        test_symbols = await self.top_symbols_manager.get_top_traded_symbols(3)
        
        print("\n=== Testing Market Overview Calculation ===")
        overview_data = await self._calculate_market_overview(test_symbols)
        
        print("\nMarket Overview Results:")
        for key, value in overview_data.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    # Implementation of the fixed methods to test
    
    async def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant market data metrics from the provided market data.
        
        Args:
            market_data: Dictionary containing market data information
            
        Returns:
            Dictionary with extracted metrics
        """
        metrics = {
            'last_price': None,
            'high': None,
            'low': None,
            'change_24h': None,
            'change_24h_pct': None,
            'volume': None,
            'turnover': None,
            'open_interest': None
        }
        
        try:
            # Extract price data if available
            price_data = market_data.get('price')
            ticker_data = market_data.get('ticker')
            raw_ticker = market_data.get('raw_ticker', {})
            
            # Log for debugging
            self.logger.debug(f"Extracting market data from: price_data={bool(price_data)}, ticker_data={bool(ticker_data)}, raw_ticker={bool(raw_ticker)}")
            
            # Last price
            if price_data and isinstance(price_data, (int, float)):
                metrics['last_price'] = price_data
            elif ticker_data and 'last' in ticker_data:
                metrics['last_price'] = ticker_data['last']
                
            # High & Low
            if ticker_data:
                metrics['high'] = ticker_data.get('high')
                metrics['low'] = ticker_data.get('low')
            
            # OHLCV data for additional metrics if available
            ohlcv_data = None
            if 'ohlcv' in market_data and market_data['ohlcv']:
                base_data = market_data['ohlcv'].get('base', {})
                if base_data and 'data' in base_data:
                    ohlcv_data = base_data['data']
            
            # Calculate 24h change and percentage
            # First check if we have open price from 24h ago in OHLCV data
            if isinstance(ohlcv_data, pd.DataFrame) and not ohlcv_data.empty and metrics['last_price']:
                # Find data point closest to 24h ago
                if len(ohlcv_data) >= 2:
                    prev_price = ohlcv_data['close'].iloc[-2]  # Use second-to-last close price
                    if prev_price > 0 and metrics['last_price'] > 0:
                        metrics['change_24h'] = metrics['last_price'] - prev_price
                        metrics['change_24h_pct'] = (metrics['change_24h'] / prev_price) * 100
            
            # If we couldn't get 24h change from OHLCV, try ticker data
            if (metrics['change_24h'] is None or metrics['change_24h_pct'] is None) and ticker_data:
                if 'change' in ticker_data and ticker_data['change'] is not None:
                    metrics['change_24h_pct'] = ticker_data['change'] * 100  # Convert to percentage
                
                # Calculate absolute change if we have percentage but not absolute
                if metrics['change_24h'] is None and metrics['change_24h_pct'] is not None and metrics['last_price']:
                    # Reverse calculate the previous price
                    prev_price = metrics['last_price'] / (1 + metrics['change_24h_pct'] / 100)
                    metrics['change_24h'] = metrics['last_price'] - prev_price
            
            # Sanity check for change percentage - cap at reasonable values
            if metrics['change_24h_pct'] is not None:
                # Cap at ±100% for sanity unless in extreme market conditions
                if abs(metrics['change_24h_pct']) > 100:
                    self.logger.warning(f"Unrealistic 24h change detected: {metrics['change_24h_pct']}%, capping at ±100%")
                    metrics['change_24h_pct'] = 100 if metrics['change_24h_pct'] > 0 else -100
                    
                    # Recalculate absolute change
                    if metrics['last_price']:
                        prev_price = metrics['last_price'] / (1 + metrics['change_24h_pct'] / 100)
                        metrics['change_24h'] = metrics['last_price'] - prev_price
            
            # Volume from ticker or OHLCV
            if ticker_data and 'volume' in ticker_data:
                metrics['volume'] = ticker_data['volume']
            elif isinstance(ohlcv_data, pd.DataFrame) and not ohlcv_data.empty:
                metrics['volume'] = ohlcv_data['volume'].iloc[-1]
            
            # Turnover (baseVolume * last_price) if available
            if ticker_data and 'baseVolume' in ticker_data and metrics['last_price']:
                metrics['turnover'] = ticker_data['baseVolume'] * metrics['last_price']
            elif metrics['volume'] and metrics['last_price']:
                # Estimate turnover from volume
                metrics['turnover'] = metrics['volume'] * metrics['last_price']
            
            # Extract open interest if available
            if raw_ticker and 'openInterest' in raw_ticker and raw_ticker['openInterest'] is not None:
                metrics['open_interest'] = raw_ticker['openInterest']
            
            # Log for debugging
            self.logger.debug(f"Extracted metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error extracting market data: {str(e)}")
            self.logger.debug("Extraction error details:", exc_info=True)
            return metrics
    
    async def _calculate_market_regime(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate current market regime characteristics.
        
        This method analyzes price trends, volatility, and correlation
        to determine the current market regime.
        """
        try:
            # Initialize regime metrics
            volatility_readings = []
            volume_change = []
            price_trends = []
            correlation_values = []
            price_strengths = []
            
            # Get BTC data as reference
            btc_data = await self.top_symbols_manager.get_market_data("BTC/USDT")
            btc_ohlcv = None
            if btc_data and 'ohlcv' in btc_data:
                btc_ohlcv = btc_data['ohlcv'].get('base', {}).get('data')
            
            # Analyze data across top pairs
            for symbol in top_pairs:
                try:
                    # Extract market data metrics
                    market_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Get price change data
                    metrics = await self._extract_market_data(market_data)
                    change_24h_pct = metrics.get('change_24h_pct', 0)
                    
                    # Determine price trend (positive/negative)
                    price_trends.append(1 if change_24h_pct > 0 else -1)
                    price_strengths.append(abs(change_24h_pct))
                    
                    # Get OHLCV data if available
                    ohlcv = None
                    if 'ohlcv' in market_data:
                        ohlcv = market_data['ohlcv'].get('base', {}).get('data')
                    
                    if isinstance(ohlcv, pd.DataFrame) and not ohlcv.empty and len(ohlcv) >= 4:
                        # Calculate volatility (simplified for test)
                        high_low = ohlcv['high'] - ohlcv['low']
                        high_close = abs(ohlcv['high'] - ohlcv['close'].shift(1))
                        low_close = abs(ohlcv['low'] - ohlcv['close'].shift(1))
                        ranges = pd.concat([high_low, high_close, low_close], axis=1)
                        true_range = ranges.max(axis=1)
                        atr = true_range.iloc[-1]  # Just use the last TR for test
                        current_price = ohlcv['close'].iloc[-1]
                        volatility_readings.append(atr / current_price * 100)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for market regime: {str(e)}")
                    continue
            
            # Calculate average metrics
            avg_volatility = sum(volatility_readings) / max(len(volatility_readings), 1) if volatility_readings else 2.5
            
            # Calculate trend bias (-1 to 1 scale)
            trend_bias = sum(price_trends) / max(len(price_trends), 1)
            
            # Calculate average price strength
            avg_price_strength = sum(price_strengths) / max(len(price_strengths), 1) if price_strengths else 1.5
            
            # Log metrics for debugging
            self.logger.debug(f"Market regime metrics: volatility={avg_volatility:.2f}, trend_bias={trend_bias:.2f}, price_strength={avg_price_strength:.2f}")
            
            # Determine market regime components
            
            # Volatility regime
            if avg_volatility > 4:
                volatility_regime = "HIGH"
            elif avg_volatility > 2:
                volatility_regime = "MODERATE"
            else:
                volatility_regime = "LOW"
                
            # Trend regime
            if trend_bias > 0.5 and avg_price_strength > 3:
                trend_regime = "STRONG_BULLISH"
            elif trend_bias > 0.2:
                trend_regime = "BULLISH"
            elif trend_bias < -0.5 and avg_price_strength > 3:
                trend_regime = "STRONG_BEARISH"
            elif trend_bias < -0.2:
                trend_regime = "BEARISH"
            else:
                trend_regime = "SIDEWAYS"
                
            # Determine overall market regime
            if trend_regime in ("STRONG_BULLISH", "BULLISH") and volatility_regime == "HIGH":
                regime = "BULLISH_TRENDING"
            elif trend_regime in ("STRONG_BULLISH", "BULLISH") and volatility_regime != "HIGH":
                regime = "BULLISH_SIDEWAYS"
            elif trend_regime in ("STRONG_BEARISH", "BEARISH") and volatility_regime == "HIGH":
                regime = "BEARISH_TRENDING"
            elif trend_regime in ("STRONG_BEARISH", "BEARISH") and volatility_regime != "HIGH":
                regime = "BEARISH_SIDEWAYS"
            elif trend_regime == "SIDEWAYS" and trend_bias >= 0:
                regime = "ACCUMULATION"
            elif trend_regime == "SIDEWAYS" and trend_bias < 0:
                regime = "DISTRIBUTION"
            else:
                regime = "NEUTRAL"
                
            # Calculate normalized trend strength (0-1)
            trend_strength = (abs(trend_bias) * (1 + avg_price_strength / 10)) / 2
            trend_strength = min(max(trend_strength, 0.1), 0.95)  # Ensure minimum value is 0.1
            
            # Calculate normalized volatility (0-1)
            volatility = min(avg_volatility / 8, 0.95)
            # Ensure volatility is never zero or extremely low
            volatility = max(volatility, 0.1)
            
            self.logger.debug(f"Calculated market regime: {regime}, trend_strength={trend_strength:.2f}, volatility={volatility:.2f}")
            
            return {
                "regime": regime,
                "trend_regime": trend_regime,
                "volatility_regime": volatility_regime,
                "trend_strength": trend_strength,
                "volatility": volatility
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market regime: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "regime": "NEUTRAL",
                "trend_regime": "SIDEWAYS",
                "volatility_regime": "MODERATE",
                "trend_strength": 0.5,
                "volatility": 0.3
            }
    
    async def _calculate_market_overview(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate market overview statistics.
        
        This method calculates various market overview statistics based on the
        given top trading pairs, including total volume, turnover, and 
        week-over-week comparisons.
        """
        try:
            # Initialize overview metrics
            total_volume = 0.0
            total_turnover = 0.0
            total_open_interest = 0.0
            symbols_with_data = 0
            
            # For testing, we'll use mock historical data
            historical_volume = 4500000000.0
            historical_turnover = 9000000000.0
            historical_open_interest = 2800000000.0
            
            self.logger.debug(f"Historical metrics: volume={historical_volume}, turnover={historical_turnover}, open_interest={historical_open_interest}")
            
            # Process each symbol to gather metrics
            for symbol in top_pairs:
                try:
                    # Get market data for the symbol
                    market_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not market_data:
                        self.logger.warning(f"No market data available for {symbol}")
                        continue
                    
                    # Extract metrics from market data
                    metrics = await self._extract_market_data(market_data)
                    
                    # Skip if we don't have valid volume data
                    if not metrics.get('volume'):
                        continue
                    
                    # Add to totals
                    total_volume += metrics.get('volume', 0)
                    total_turnover += metrics.get('turnover', 0) if metrics.get('turnover') else 0
                    total_open_interest += metrics.get('open_interest', 0) if metrics.get('open_interest') else 0
                    symbols_with_data += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for market overview: {str(e)}")
                    continue
            
            # Calculate week-over-week changes
            volume_wow = ((total_volume - historical_volume) / historical_volume * 100) if historical_volume > 0 else 0.0
            turnover_wow = ((total_turnover - historical_turnover) / historical_turnover * 100) if historical_turnover > 0 else 0.0
            open_interest_wow = ((total_open_interest - historical_open_interest) / historical_open_interest * 100) if historical_open_interest > 0 else 0.0
            
            # Set fallback values if calculations result in extreme values
            if abs(volume_wow) > 500:
                self.logger.warning(f"Extreme volume_wow value detected: {volume_wow}%. Using fallback.")
                volume_wow = 10.0 if volume_wow > 0 else -10.0
                
            if abs(turnover_wow) > 500:
                self.logger.warning(f"Extreme turnover_wow value detected: {turnover_wow}%. Using fallback.")
                turnover_wow = 10.0 if turnover_wow > 0 else -10.0
                
            if abs(open_interest_wow) > 500:
                self.logger.warning(f"Extreme open_interest_wow value detected: {open_interest_wow}%. Using fallback.")
                open_interest_wow = 10.0 if open_interest_wow > 0 else -10.0
            
            # Return the calculated overview
            return {
                "total_volume": total_volume,
                "total_turnover": total_turnover,
                "total_open_interest": total_open_interest,
                "volume_wow": volume_wow,
                "turnover_wow": turnover_wow,
                "open_interest_wow": open_interest_wow,
                "symbols_with_data": symbols_with_data
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market overview: {str(e)}")
            self.logger.debug("Calculate market overview error details:", exc_info=True)
            return {
                "total_volume": 0.0,
                "total_turnover": 0.0,
                "total_open_interest": 0.0,
                "volume_wow": 0.0,
                "turnover_wow": 0.0,
                "open_interest_wow": 0.0,
                "symbols_with_data": 0
            }

async def main():
    """Main test function."""
    extractor = MarketDataExtractor()
    await extractor.test_extract_market_data()
    await extractor.test_market_regime()
    await extractor.test_market_overview()

if __name__ == "__main__":
    asyncio.run(main()) 