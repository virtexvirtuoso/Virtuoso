import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass
import logging

from src.core.exchanges.manager import ExchangeManager
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.api.models.alpha import AlphaOpportunity, AlphaStrength

@dataclass
class MarketData:
    symbol: str
    exchange: str
    ohlcv: pd.DataFrame
    orderbook: Dict
    volume_profile: Optional[Dict] = None

class AlphaScannerEngine:
    """Core alpha scanning engine that analyzes market opportunities using confluence analysis."""
    
    def __init__(self, exchange_manager: ExchangeManager, config: Dict = None):
        self.exchange_manager = exchange_manager
        # Provide default config with required timeframes structure
        self.config = config or {
            'timeframes': {
                'base': {
                    'weight': 1.0,
                    'interval': 60,
                    'validation': {'min_candles': 20}
                },
                'ltf': {
                    'weight': 1.0,
                    'interval': 60,
                    'validation': {'min_candles': 20}
                },
                'mtf': {
                    'weight': 0.8,
                    'interval': 240,
                    'validation': {'min_candles': 20}
                }, 
                'htf': {
                    'weight': 0.6,
                    'interval': 1440,
                    'validation': {'min_candles': 20}
                }
            }
        }
        self.logger = logging.getLogger(__name__)
        
        # Initialize confluence analyzer
        self.confluence_analyzer = ConfluenceAnalyzer(self.config)
        
        # Scanning parameters
        self.lookback_periods = {
            "15m": 96,  # 24 hours
            "1h": 168,  # 7 days  
            "4h": 180,  # 30 days
            "1d": 90    # 90 days
        }
        
        # Alpha scoring weights
        self.alpha_weights = {
            'confluence_score': 0.40,
            'momentum_strength': 0.25,
            'volume_confirmation': 0.20,
            'liquidity_factor': 0.15
        }
        
        # Minimum volume thresholds (in USDT)
        self.min_volume_24h = self.config.get('alpha_scanner', {}).get('min_volume_24h', 1000000)
        
    async def scan_opportunities(self, 
                               symbols: Optional[List[str]] = None,
                               exchanges: Optional[List[str]] = None,
                               timeframes: List[str] = ["15m", "1h", "4h"],
                               min_score: float = 60.0,
                               max_results: int = 20) -> List[AlphaOpportunity]:
        """Main scanning method that identifies alpha opportunities."""
        
        start_time = time.time()
        opportunities = []
        
        self.logger.info(f"Starting alpha scan with min_score={min_score}, max_results={max_results}")
        
        # Get symbols to scan
        scan_symbols = symbols or await self._get_top_symbols()
        scan_exchanges = exchanges or list(self.exchange_manager.exchanges.keys())
        
        self.logger.info(f"Scanning {len(scan_symbols)} symbols across {len(scan_exchanges)} exchanges")
        
        # Parallel scanning across exchanges
        tasks = []
        for exchange_id in scan_exchanges:
            if exchange_id not in self.exchange_manager.exchanges:
                self.logger.warning(f"Exchange {exchange_id} not available, skipping")
                continue
                
            for symbol in scan_symbols:
                task = self._analyze_symbol_opportunity(
                    symbol, exchange_id, timeframes, min_score
                )
                tasks.append(task)
        
        if not tasks:
            self.logger.warning("No valid exchange/symbol combinations to scan")
            return []
        
        # Execute analysis in parallel
        self.logger.info(f"Executing {len(tasks)} analysis tasks in parallel")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, AlphaOpportunity):
                opportunities.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Task {i} failed with error: {result}")
        
        # Sort by score and limit results
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        scan_duration = time.time() - start_time
        self.logger.info(f"Alpha scan completed: {len(opportunities)} opportunities found in {scan_duration:.2f}s")
        
        return opportunities[:max_results]
    
    async def _analyze_symbol_opportunity(self, 
                                        symbol: str, 
                                        exchange_id: str,
                                        timeframes: List[str],
                                        min_score: float) -> Optional[AlphaOpportunity]:
        """Analyze a single symbol for alpha opportunities."""
        
        try:
            self.logger.debug(f"Analyzing {symbol} on {exchange_id}")
            
            # Gather market data
            market_data = await self._fetch_market_data(symbol, exchange_id, timeframes)
            
            if not market_data:
                self.logger.debug(f"No market data for {symbol} on {exchange_id}")
                return None
            
            # Run confluence analysis
            analyzer = getattr(self, 'confluence_analyzer', None)
            if not (analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze'))):
                self.logger.debug(f"confluence_analyzer missing or analyze() not callable; skipping {symbol}")
                return None

            try:
                confluence_result = await analyzer.analyze(market_data)
            except Exception as e:
                self.logger.debug(f"confluence_analyzer.analyze error for {symbol}: {e}")
                return None
            
            if not confluence_result or confluence_result.get('score', 0) < 50:
                self.logger.debug(f"Low confluence score for {symbol}: {confluence_result.get('score', 0)}")
                return None
            
            # Calculate alpha score
            alpha_score = self._calculate_alpha_score(confluence_result, market_data)
            
            if alpha_score < min_score:
                self.logger.debug(f"Alpha score {alpha_score:.2f} below threshold {min_score} for {symbol}")
                return None
            
            # Calculate price levels
            levels = self._calculate_price_levels(market_data, confluence_result)
            
            # Extract component scores
            components = confluence_result.get('components', {})
            
            # Create opportunity object
            opportunity = AlphaOpportunity(
                symbol=symbol,
                exchange=exchange_id,
                score=alpha_score,
                strength=self._categorize_strength(alpha_score),
                timeframe=self._determine_primary_timeframe(confluence_result),
                technical_score=components.get('technical', {}).get('score', 50.0),
                momentum_score=self._extract_momentum_score(confluence_result),
                volume_score=components.get('volume', {}).get('score', 50.0),
                sentiment_score=components.get('sentiment', {}).get('score', 50.0),
                volatility=self._calculate_volatility(market_data),
                liquidity_score=self._calculate_liquidity_score(market_data),
                current_price=levels['current'],
                entry_price=levels['entry'],
                stop_loss=levels['stop'],
                target_price=levels['target'],
                confidence=confluence_result.get('reliability', 0.5),
                indicators=self._extract_key_indicators(confluence_result),
                insights=self._generate_insights(confluence_result, levels)
            )
            
            self.logger.info(f"Alpha opportunity found: {symbol} score={alpha_score:.2f}")
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol} on {exchange_id}: {e}")
            return None
    
    async def _fetch_market_data(self, symbol: str, exchange_id: str, timeframes: List[str]) -> Optional[Dict]:
        """Fetch comprehensive market data for analysis."""
        
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            
            # Get OHLCV data for all requested timeframes
            ohlcv_data = {}
            
            for timeframe in timeframes:
                limit = self.lookback_periods.get(timeframe, 100)
                
                try:
                    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    
                    if not ohlcv or len(ohlcv) < 20:  # Minimum data requirement
                        continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    ohlcv_data[timeframe] = df
                    
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {timeframe} data for {symbol}: {e}")
                    continue
            
            if not ohlcv_data:
                return None
            
            # Get order book data
            try:
                orderbook = await exchange.fetch_order_book(symbol, limit=50)
            except Exception as e:
                self.logger.warning(f"Failed to fetch orderbook for {symbol}: {e}")
                orderbook = {'bids': [], 'asks': []}
            
            # Get ticker for 24h volume check
            try:
                ticker = await exchange.fetch_ticker(symbol)
                volume_24h = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) * ticker.get('last', 1)
                
                # Skip low volume symbols
                if volume_24h < self.min_volume_24h:
                    self.logger.debug(f"Skipping {symbol}: volume {volume_24h} below threshold {self.min_volume_24h}")
                    return None
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch ticker for {symbol}: {e}")
                # Continue without volume check
            
            # Structure data for confluence analyzer
            market_data = {
                'ohlcv': ohlcv_data,
                'orderbook': orderbook,
                'symbol': symbol,
                'exchange': exchange_id
            }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def _calculate_alpha_score(self, confluence_result: Dict, market_data: Dict) -> float:
        """Calculate overall alpha score combining multiple factors."""
        
        # Base confluence score
        confluence_score = confluence_result.get('score', 50.0)
        
        # Momentum strength from technical analysis
        momentum_strength = self._assess_momentum_strength(confluence_result)
        
        # Volume confirmation
        volume_confirmation = self._assess_volume_confirmation(confluence_result, market_data)
        
        # Liquidity factor
        liquidity_factor = self._assess_liquidity_factor(market_data)
        
        # Weighted combination
        alpha_score = (
            self.alpha_weights['confluence_score'] * confluence_score +
            self.alpha_weights['momentum_strength'] * momentum_strength +
            self.alpha_weights['volume_confirmation'] * volume_confirmation +
            self.alpha_weights['liquidity_factor'] * liquidity_factor
        )
        
        # Ensure score is within bounds
        return max(0.0, min(100.0, alpha_score))
    
    def _assess_momentum_strength(self, confluence_result: Dict) -> float:
        """Assess momentum strength from confluence analysis."""
        
        components = confluence_result.get('components', {})
        technical = components.get('technical', {})
        
        # Look for momentum indicators in technical analysis
        sub_components = technical.get('sub_components', {})
        momentum_score = 50.0  # Default neutral
        
        # Extract momentum-related scores
        rsi_score = sub_components.get('rsi', {}).get('score', 50.0)
        macd_score = sub_components.get('macd', {}).get('score', 50.0)
        
        # Combine momentum indicators
        momentum_score = (rsi_score + macd_score) / 2
        
        return momentum_score
    
    def _assess_volume_confirmation(self, confluence_result: Dict, market_data: Dict) -> float:
        """Assess volume confirmation of the signal."""
        
        components = confluence_result.get('components', {})
        volume_component = components.get('volume', {})
        
        volume_score = volume_component.get('score', 50.0)
        
        # Boost score if volume is significantly above average
        try:
            # Defensive programming: Check if ohlcv data exists and is not empty
            if 'ohlcv' not in market_data or not market_data['ohlcv']:
                self.logger.debug("No OHLCV data available for volume confirmation")
                return volume_score
            
            # Get primary timeframe data
            ohlcv_keys = list(market_data['ohlcv'].keys())
            if not ohlcv_keys:
                self.logger.debug("OHLCV data exists but has no timeframes")
                return volume_score
                
            primary_tf = ohlcv_keys[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Check if DataFrame is empty or has insufficient data
            if df.empty or len(df) < 20:
                self.logger.debug(f"OHLCV DataFrame for {primary_tf} is empty or has insufficient data for volume analysis")
                return volume_score
            
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            
            if current_volume > avg_volume * 1.5:  # 50% above average
                volume_score = min(100.0, volume_score * 1.2)
                    
        except Exception as e:
            self.logger.debug(f"Error assessing volume confirmation: {e}")
        
        return volume_score
    
    def _assess_liquidity_factor(self, market_data: Dict) -> float:
        """Assess liquidity based on orderbook depth."""
        
        orderbook = market_data.get('orderbook', {})
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 50.0  # Neutral if no orderbook data
        
        # Calculate spread
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        
        if best_bid > 0 and best_ask > 0:
            spread_pct = (best_ask - best_bid) / best_bid * 100
            
            # Lower spread = higher liquidity score
            if spread_pct < 0.1:
                return 90.0
            elif spread_pct < 0.5:
                return 75.0
            elif spread_pct < 1.0:
                return 60.0
            else:
                return 40.0
        
        return 50.0
    
    def _calculate_price_levels(self, market_data: Dict, confluence_result: Dict) -> Dict[str, float]:
        """Calculate entry, stop loss, and target price levels."""
        
        try:
            # Defensive programming: Check if ohlcv data exists and is not empty
            if 'ohlcv' not in market_data or not market_data['ohlcv']:
                self.logger.warning("No OHLCV data available for price level calculation")
                # Return default price levels
                return {
                    'current': 1.0,
                    'entry': 1.0,
                    'stop': 0.98,
                    'target': 1.02
                }
            
            # Get current price from the most recent data
            ohlcv_keys = list(market_data['ohlcv'].keys())
            if not ohlcv_keys:
                self.logger.warning("OHLCV data exists but has no timeframes")
                return {
                    'current': 1.0,
                    'entry': 1.0,
                    'stop': 0.98,
                    'target': 1.02
                }
                
            primary_tf = ohlcv_keys[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Check if DataFrame is empty
            if df.empty:
                self.logger.warning(f"OHLCV DataFrame for {primary_tf} is empty")
                return {
                    'current': 1.0,
                    'entry': 1.0,
                    'stop': 0.98,
                    'target': 1.02
                }
            
            current_price = float(df['close'].iloc[-1])

            # Calculate ATR for dynamic levels
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift(1))
            low_close = abs(df['low'] - df['close'].shift(1))
            atr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(window=14).mean().iloc[-1]
            
            # Determine signal direction from confluence
            signal_direction = confluence_result.get('signal', 'NEUTRAL')
            
            if signal_direction == 'BULLISH':
                entry_price = current_price
                stop_loss = current_price - (1.5 * atr)
                target_price = current_price + (2.0 * atr)
            elif signal_direction == 'BEARISH':
                entry_price = current_price  
                stop_loss = current_price + (1.5 * atr)
                target_price = current_price - (2.0 * atr)
            else:
                # Neutral - use smaller ranges
                entry_price = current_price
                stop_loss = current_price - (1.0 * atr)
                target_price = current_price + (1.0 * atr)
            
            return {
                'current': current_price,
                'entry': entry_price,
                'stop': max(0.01, stop_loss),  # Ensure positive
                'target': max(0.01, target_price)  # Ensure positive
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating price levels: {e}")
            # Fallback to simple percentage-based levels
            current_price = 1.0  # Default fallback
            return {
                'current': current_price,
                'entry': current_price,
                'stop': current_price * 0.98,
                'target': current_price * 1.02
            }
    
    def _categorize_strength(self, alpha_score: float) -> AlphaStrength:
        """Categorize alpha strength based on score."""
        
        if alpha_score >= 85:
            return AlphaStrength.EXCEPTIONAL
        elif alpha_score >= 75:
            return AlphaStrength.STRONG  
        elif alpha_score >= 65:
            return AlphaStrength.MODERATE
        else:
            return AlphaStrength.WEAK
    
    def _determine_primary_timeframe(self, confluence_result: Dict) -> str:
        """Determine the primary timeframe for the signal."""
        
        # Look for the timeframe with the highest contributing score
        components = confluence_result.get('components', {})
        
        # Default to 1h if no clear winner
        return "1h"
    
    def _calculate_volatility(self, market_data: Dict) -> float:
        """Calculate historical volatility."""
        
        try:
            # Defensive programming: Check if ohlcv data exists and is not empty
            if 'ohlcv' not in market_data or not market_data['ohlcv']:
                self.logger.warning("No OHLCV data available for volatility calculation")
                return 0.20  # Default 20% volatility
            
            ohlcv_keys = list(market_data['ohlcv'].keys())
            if not ohlcv_keys:
                self.logger.warning("OHLCV data exists but has no timeframes")
                return 0.20  # Default 20% volatility
                
            primary_tf = ohlcv_keys[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Check if DataFrame is empty or has insufficient data
            if df.empty or len(df) < 2:
                self.logger.warning(f"OHLCV DataFrame for {primary_tf} is empty or has insufficient data")
                return 0.20  # Default 20% volatility
            
            # Calculate daily returns
            returns = df['close'].pct_change().dropna()
            
            # Check if we have enough returns data
            if len(returns) < 2:
                self.logger.warning("Insufficient returns data for volatility calculation")
                return 0.20  # Default 20% volatility
            
            # Annualized volatility
            volatility = returns.std() * np.sqrt(365)
            
            return float(volatility)
            
        except Exception as e:
            self.logger.debug(f"Error calculating volatility: {e}")
            return 0.20  # Default 20% volatility
    
    def _calculate_liquidity_score(self, market_data: Dict) -> float:
        """Calculate liquidity score from orderbook."""
        
        return self._assess_liquidity_factor(market_data)
    
    def _extract_momentum_score(self, confluence_result: Dict) -> float:
        """Extract momentum score from confluence analysis."""
        
        return self._assess_momentum_strength(confluence_result)
    
    def _extract_key_indicators(self, confluence_result: Dict) -> Dict[str, float]:
        """Extract key indicator values for display."""
        
        indicators = {}
        components = confluence_result.get('components', {})
        
        # Extract technical indicators
        technical = components.get('technical', {})
        sub_components = technical.get('sub_components', {})
        
        for indicator_name, indicator_data in sub_components.items():
            if isinstance(indicator_data, dict) and 'score' in indicator_data:
                indicators[indicator_name] = indicator_data['score']
        
        # Add confluence score
        indicators['confluence_score'] = confluence_result.get('score', 50.0)
        
        return indicators
    
    def _generate_insights(self, confluence_result: Dict, levels: Dict[str, float]) -> List[str]:
        """Generate actionable insights from the analysis."""
        
        insights = []
        
        # Add confluence-based insights
        score = confluence_result.get('score', 50.0)
        signal = confluence_result.get('signal', 'NEUTRAL')
        
        if score > 80:
            insights.append(f"Strong {signal.lower()} confluence detected")
        elif score > 70:
            insights.append(f"Moderate {signal.lower()} signal strength")
        
        # Add price level insights
        current = levels['current']
        target = levels['target']
        stop = levels['stop']
        
        if signal == 'BULLISH':
            risk_reward = (target - current) / (current - stop) if current > stop else 1.0
            insights.append(f"Risk/Reward ratio: {risk_reward:.2f}")
            insights.append(f"Target: {target:.4f} (+{((target/current)-1)*100:.1f}%)")
        elif signal == 'BEARISH':
            risk_reward = (current - target) / (stop - current) if stop > current else 1.0
            insights.append(f"Risk/Reward ratio: {risk_reward:.2f}")
            insights.append(f"Target: {target:.4f} ({((target/current)-1)*100:.1f}%)")
        
        # Add component-specific insights
        components = confluence_result.get('components', {})
        for component_name, component_data in components.items():
            if isinstance(component_data, dict):
                comp_score = component_data.get('score', 50.0)
                if comp_score > 75:
                    insights.append(f"Strong {component_name} confirmation")
                elif comp_score < 25:
                    insights.append(f"Weak {component_name} signal")
        
        return insights[:5]  # Limit to top 5 insights
    
    async def _get_top_symbols(self) -> List[str]:
        """Get top trading symbols across all exchanges."""
        
        # Default symbols if we can't fetch dynamically
        default_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'LUNAUSDT', 'MATICUSDT', 'ATOMUSDT'
        ]
        
        try:
            # Try to get symbols from first available exchange
            for exchange_id, exchange in self.exchange_manager.exchanges.items():
                try:
                    markets = await exchange.load_markets()
                    
                    # Filter for USDT pairs with good volume
                    usdt_pairs = [symbol for symbol in markets.keys() if '/USDT' in symbol]
                    
                    # Return top 20 USDT pairs
                    return usdt_pairs[:20] if usdt_pairs else default_symbols
                    
                except Exception as e:
                    self.logger.warning(f"Failed to fetch markets from {exchange_id}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error getting top symbols: {e}")
        
        return default_symbols 