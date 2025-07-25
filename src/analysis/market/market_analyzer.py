"""Market analysis functionality."""

import logging
from logging import Logger
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from ..core.confluence import ConfluenceAnalyzer

@dataclass
class MarketAnalyzer:
    """Analyzes market data using standardized CCXT fields."""

    def __init__(self, config: Dict[str, Any], logger: Logger, confluence_analyzer: Optional[ConfluenceAnalyzer] = None):
        self.config = config
        self.logger = logger
        
        # Initialize indicators
        self.orderbook_indicators = OrderbookIndicators(config)
        self.orderflow_indicators = OrderflowIndicators(config)
        
        # Initialize or use provided confluence analyzer
        self.confluence_analyzer = confluence_analyzer or ConfluenceAnalyzer(config)

    async def get_market_conditions(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get market conditions using CCXT standardized data."""
        try:
            if not market_data:
                return {}

            ticker = market_data.get('ticker', {})
            orderbook = market_data.get('orderbook', {})
            trades = market_data.get('trades', [])
            ohlcv = market_data.get('ohlcv', [])

            # Calculate core market conditions
            conditions = {
                'volatility': self._calculate_volatility(ohlcv),
                'liquidity': self._calculate_liquidity(orderbook),
                'trend': self._calculate_trend(ohlcv),
                'market_impact': self._calculate_market_impact(orderbook, trades)
            }

            # Get confluence analysis
            confluence_scores = await self.confluence_analyzer.calculate(market_data)
            conditions['confluence'] = confluence_scores

            return conditions

        except Exception as e:
            self.logger.error(f"Error calculating market conditions for {symbol}: {str(e)}")
            return {}

    def _calculate_volatility(self, ohlcv: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate volatility metrics using CCXT OHLCV data."""
        try:
            if not ohlcv:
                return {'score': 0, 'level': 'unknown'}

            # Handle nested OHLCV structure
            # First try to get base timeframe data
            base_data = None
            if isinstance(ohlcv, dict):
                # Try to get data from the first available timeframe
                for tf_name, tf_data in ohlcv.items():
                    if isinstance(tf_data, dict) and 'data' in tf_data:
                        base_data = tf_data['data']
                        self.logger.debug(f"Using {tf_name} timeframe data for volatility calculation")
                        break
                    elif isinstance(tf_data, list):
                        base_data = tf_data
                        self.logger.debug(f"Using direct list data for volatility calculation")
                        break
            elif isinstance(ohlcv, list):
                base_data = ohlcv

            if not base_data:
                self.logger.warning("No valid OHLCV data found for volatility calculation")
                return {'score': 0, 'level': 'unknown'}

            # Calculate true range using CCXT OHLCV format [timestamp, open, high, low, close, volume]
            true_ranges = []
            for i in range(1, len(base_data)):
                current = base_data[i]
                prev = base_data[i-1]
                
                if len(current) < 6 or len(prev) < 6:
                    self.logger.warning("Invalid OHLCV data format")
                    continue
                    
                high = float(current[2])    # high
                low = float(current[3])     # low
                prev_close = float(prev[4]) # previous close
                
                true_range = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(true_range)

            if not true_ranges:
                return {'score': 0, 'level': 'unknown'}

            # Calculate ATR
            atr = sum(true_ranges) / len(true_ranges)
            
            # Calculate volatility score
            latest_price = float(base_data[-1][4])  # close price
            volatility_pct = (atr / latest_price) * 100
            
            # Determine volatility level
            if volatility_pct < 0.5:
                level = 'very_low'
                score = 20
            elif volatility_pct < 1.0:
                level = 'low'
                score = 40
            elif volatility_pct < 2.0:
                level = 'moderate'
                score = 60
            elif volatility_pct < 3.0:
                level = 'high'
                score = 80
            else:
                level = 'very_high'
                score = 100

            return {
                'score': score,
                'level': level,
                'atr': atr,
                'volatility_pct': volatility_pct
            }

        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            return {'score': 0, 'level': 'unknown'}

    def _calculate_liquidity(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate liquidity metrics using CCXT orderbook data."""
        try:
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return {'score': 0, 'level': 'unknown'}

            bids = orderbook['bids']
            asks = orderbook['asks']

            if not bids or not asks:
                return {'score': 0, 'level': 'unknown'}

            # Calculate bid-ask spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = (best_ask - best_bid) / best_bid * 100

            # Calculate depth
            bid_depth = sum(float(bid[1]) for bid in bids[:10])
            ask_depth = sum(float(ask[1]) for ask in asks[:10])
            total_depth = bid_depth + ask_depth

            # Calculate liquidity score
            spread_score = max(0, min(100, (1 - spread/0.1) * 100))  # Normalize spread score
            depth_score = min(100, total_depth / 100 * 100)  # Normalize depth score
            liquidity_score = (spread_score + depth_score) / 2

            # Determine liquidity level
            if liquidity_score < 20:
                level = 'very_low'
            elif liquidity_score < 40:
                level = 'low'
            elif liquidity_score < 60:
                level = 'moderate'
            elif liquidity_score < 80:
                level = 'high'
            else:
                level = 'very_high'

            return {
                'score': liquidity_score,
                'level': level,
                'spread': spread,
                'depth': total_depth,
                'bid_depth': bid_depth,
                'ask_depth': ask_depth
            }

        except Exception as e:
            self.logger.error(f"Error calculating liquidity: {str(e)}")
            return {'score': 0, 'level': 'unknown'}

    def _calculate_trend(self, ohlcv: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trend metrics using CCXT OHLCV data."""
        try:
            if not ohlcv:
                return {'score': 0, 'direction': 'unknown'}

            # Handle nested OHLCV structure
            # First try to get base timeframe data
            base_data = None
            if isinstance(ohlcv, dict):
                # Try to get data from the first available timeframe
                for tf_name, tf_data in ohlcv.items():
                    if isinstance(tf_data, dict) and 'data' in tf_data:
                        base_data = tf_data['data']
                        self.logger.debug(f"Using {tf_name} timeframe data for trend calculation")
                        break
                    elif isinstance(tf_data, list):
                        base_data = tf_data
                        self.logger.debug(f"Using direct list data for trend calculation")
                        break
            elif isinstance(ohlcv, list):
                base_data = ohlcv

            if not base_data or len(base_data) < 2:
                return {'score': 0, 'direction': 'unknown'}

            # Calculate price changes using CCXT OHLCV format
            price_changes = []
            for i in range(1, len(base_data)):
                current = base_data[i]
                prev = base_data[i-1]
                
                if len(current) < 6 or len(prev) < 6:
                    self.logger.warning("Invalid OHLCV data format")
                    continue
                    
                current_close = float(current[4])  # close price
                prev_close = float(prev[4])      # previous close
                
                if prev_close == 0:
                    self.logger.warning("Invalid previous close price of 0")
                    continue
                    
                change = (current_close - prev_close) / prev_close
                price_changes.append(change)

            if not price_changes:
                return {'score': 0, 'direction': 'unknown'}

            # Calculate trend metrics
            avg_change = sum(price_changes) / len(price_changes)
            trend_strength = abs(avg_change)
            
            # Calculate trend score and direction
            if avg_change > 0:
                direction = 'uptrend'
                score = min(100, trend_strength * 1000)
            elif avg_change < 0:
                direction = 'downtrend'
                score = min(100, trend_strength * 1000)
            else:
                direction = 'sideways'
                score = 0

            return {
                'score': score,
                'direction': direction,
                'strength': trend_strength,
                'avg_change': avg_change
            }

        except Exception as e:
            self.logger.error(f"Error calculating trend: {str(e)}")
            return {'score': 0, 'direction': 'unknown'}

    def _calculate_market_impact(self, orderbook: Dict[str, Any], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate market impact metrics."""
        try:
            if not orderbook or not trades:
                return {'score': 0, 'level': 'unknown'}

            # Calculate average trade size using CCXT trade format
            trade_sizes = []
            for trade in trades:
                try:
                    # CCXT unified trade format uses 'amount' field
                    if 'amount' in trade:
                        amount = float(trade['amount'])
                    # Some exchanges might use 'quantity' or 'size'
                    elif 'quantity' in trade:
                        amount = float(trade['quantity'])
                    elif 'size' in trade:
                        amount = float(trade['size'])
                    else:
                        self.logger.warning(f"Trade missing amount field: {trade}")
                        continue
                        
                    trade_sizes.append(amount)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Error processing trade: {e}")
                    continue

            avg_trade_size = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0

            # Calculate available liquidity (sum of top 10 levels)
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            bid_liquidity = sum(float(bid[1]) for bid in bids[:10]) if bids else 0
            ask_liquidity = sum(float(ask[1]) for ask in asks[:10]) if asks else 0
            total_liquidity = bid_liquidity + ask_liquidity

            # Calculate impact ratio
            impact_ratio = avg_trade_size / total_liquidity if total_liquidity > 0 else 1

            # Score based on impact ratio
            if impact_ratio < 0.001:
                score = 90  # Negligible impact
                level = 'negligible'
            elif impact_ratio < 0.005:
                score = 70  # Low impact
                level = 'low'
            elif impact_ratio < 0.01:
                score = 50  # Moderate impact
                level = 'moderate'
            elif impact_ratio < 0.05:
                score = 30  # High impact
                level = 'high'
            else:
                score = 10  # Very high impact
                level = 'very_high'

            return {
                'score': score,
                'level': level,
                'impact_ratio': impact_ratio,
                'avg_trade_size': avg_trade_size,
                'total_liquidity': total_liquidity
            }

        except Exception as e:
            self.logger.error(f"Error calculating market impact: {str(e)}")
            return {'score': 0, 'level': 'unknown'} 