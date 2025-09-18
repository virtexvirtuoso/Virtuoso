import asyncio
import time
import uuid
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass
import logging
from collections import defaultdict, deque

from src.core.exchanges.manager import ExchangeManager
from src.core.exchanges.liquidation_collector import LiquidationDataCollector
from src.data_storage.liquidation_storage import LiquidationStorage
from src.core.models.liquidation import (
    LiquidationEvent, MarketStressIndicator, LiquidationRisk, CascadeAlert,
    LiquidationSeverity, MarketStressLevel, LiquidationType, LeverageMetrics
)

@dataclass
class MarketData:
    symbol: str
    exchange: str
    ohlcv: pd.DataFrame
    orderbook: Dict
    trades: List[Dict]
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None

@dataclass
class LiquidationSignal:
    timestamp: datetime
    symbol: str
    signal_type: str
    strength: float
    price: float
    volume: float
    context: Dict

class LiquidationDetectionEngine:
    """Advanced liquidation detection engine for real-time market monitoring."""
    
    def __init__(self, exchange_manager: ExchangeManager, database_url: Optional[str] = None):
        self.exchange_manager = exchange_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize data collection and storage
        self.liquidation_collector = LiquidationDataCollector(
            exchange_manager, 
            storage_callback=self._store_real_liquidation_event
        )
        
        # Initialize storage if database URL provided
        self.storage = None
        if database_url:
            self.storage = LiquidationStorage(database_url)
        
        # Detection parameters
        self.volume_spike_threshold = 3.0  # 3x normal volume
        self.price_impact_threshold = 0.02  # 2% price impact
        self.volatility_spike_threshold = 2.0  # 2x normal volatility
        self.funding_rate_stress_threshold = 0.01  # 1% funding rate
        
        # Historical data storage for pattern recognition
        self.historical_events = deque(maxlen=1000)
        self.market_state_history = deque(maxlen=100)
        self.funding_rate_cache = {}
        
        # Real-time monitoring state
        self.active_monitors = {}
        self.alert_cooldowns = defaultdict(lambda: datetime.min)
        
        # Data collection state
        self.is_collecting_real_data = False
        self.collection_stats = {
            'total_real_liquidations': 0,
            'total_inferred_liquidations': 0,
            'last_real_liquidation': None
        }
        
    async def detect_liquidation_events(self, 
                                      symbols: List[str],
                                      exchanges: Optional[List[str]] = None,
                                      sensitivity: float = 0.7,
                                      lookback_minutes: int = 60) -> List[LiquidationEvent]:
        """Detect liquidation events across specified markets."""
        
        start_time = time.time()
        detected_events = []
        
        target_exchanges = exchanges or list(self.exchange_manager.exchanges.keys())
        
        # Gather market data in parallel
        market_data_tasks = []
        for exchange_id in target_exchanges:
            for symbol in symbols:
                task = self._fetch_liquidation_analysis_data(
                    symbol, exchange_id, lookback_minutes
                )
                market_data_tasks.append(task)
        
        market_data_results = await asyncio.gather(*market_data_tasks, return_exceptions=True)
        
        # Analyze each market for liquidation signals
        for result in market_data_results:
            if isinstance(result, MarketData):
                events = await self._analyze_liquidation_patterns(result, sensitivity)
                detected_events.extend(events)
        
        # Sort by severity and timestamp
        detected_events.sort(key=lambda x: (x.severity.value, x.timestamp), reverse=True)
        
        # Combine with real liquidation data if available
        if self.is_collecting_real_data:
            real_events = await self._get_recent_real_liquidations(symbols, target_exchanges, lookback_minutes)
            detected_events.extend(real_events)
            
            # Remove duplicates and merge similar events
            detected_events = self._merge_similar_events(detected_events)
        
        # Store detected events if storage is available
        if self.storage and detected_events:
            await self._store_detected_events(detected_events)
        
        self.logger.info(f"Detected {len(detected_events)} liquidation events in {time.time() - start_time:.2f}s")
        return detected_events
    
    async def assess_market_stress(self, 
                                 symbols: List[str],
                                 exchanges: Optional[List[str]] = None) -> MarketStressIndicator:
        """Assess overall market stress levels."""
        
        try:
            target_exchanges = exchanges or list(self.exchange_manager.exchanges.keys())
            
            # Collect stress indicators
            volatility_readings = []
            funding_rate_readings = []
            liquidity_readings = []
            correlation_matrix = {}
            total_liquidation_volume = 0.0
            
            # Gather market data for stress assessment
            for exchange_id in target_exchanges:
                exchange = self.exchange_manager.exchanges[exchange_id]
                
                for symbol in symbols:
                    try:
                        # Get recent market data
                        ohlcv = await exchange.fetch_ohlcv(symbol, '5m', limit=100)
                        if not ohlcv:
                            continue
                        
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        
                        # Calculate volatility stress
                        returns = df['close'].pct_change().dropna()
                        current_vol = returns.std() * np.sqrt(288)  # Annualized
                        historical_vol = returns.rolling(50).std().mean() * np.sqrt(288)
                        vol_stress = min(100, (current_vol / historical_vol) * 50) if historical_vol > 0 else 50
                        volatility_readings.append(vol_stress)
                        
                        # Get funding rate if available
                        try:
                            funding_info = await exchange.fetch_funding_rate(symbol)
                            if funding_info and 'fundingRate' in funding_info:
                                funding_rate = abs(funding_info['fundingRate']) * 100
                                funding_stress = min(100, funding_rate / self.funding_rate_stress_threshold * 100)
                                funding_rate_readings.append(funding_stress)
                        except Exception as e:
                            pass
                        
                        # Assess liquidity stress from order book
                        try:
                            orderbook = await exchange.fetch_order_book(symbol, limit=20)
                            spread = self._calculate_spread_percentage(orderbook)
                            liquidity_stress = min(100, spread * 1000)  # Convert to 0-100 scale
                            liquidity_readings.append(liquidity_stress)
                        except Exception as e:
                            pass
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing {symbol} on {exchange_id}: {e}")
                        continue
            
            # Calculate component stress scores
            avg_volatility_stress = np.mean(volatility_readings) if volatility_readings else 30
            avg_funding_stress = np.mean(funding_rate_readings) if funding_rate_readings else 30
            avg_liquidity_stress = np.mean(liquidity_readings) if liquidity_readings else 30
            
            # Calculate correlation stress (simplified)
            correlation_stress = 50  # Placeholder - would need more sophisticated correlation analysis
            leverage_stress = 40  # Placeholder - would integrate with leverage metrics
            
            # Calculate overall stress score
            overall_stress = np.mean([
                avg_volatility_stress,
                avg_funding_stress, 
                avg_liquidity_stress,
                correlation_stress,
                leverage_stress
            ])
            
            # Determine stress level
            if overall_stress < 25:
                stress_level = MarketStressLevel.CALM
            elif overall_stress < 50:
                stress_level = MarketStressLevel.ELEVATED
            elif overall_stress < 75:
                stress_level = MarketStressLevel.HIGH
            else:
                stress_level = MarketStressLevel.EXTREME
            
            # Generate risk factors and recommendations
            risk_factors = []
            warning_signals = []
            recommendations = []
            
            if avg_volatility_stress > 60:
                risk_factors.append("elevated_volatility")
                warning_signals.append("Volatility significantly above normal levels")
                recommendations.append("Reduce position sizes and increase stop-loss buffers")
            
            if avg_funding_stress > 70:
                risk_factors.append("funding_rate_stress")
                warning_signals.append("Extreme funding rates indicate high leverage")
                recommendations.append("Monitor for potential cascade liquidations")
            
            if avg_liquidity_stress > 50:
                risk_factors.append("liquidity_shortage")
                warning_signals.append("Reduced market liquidity detected")
                recommendations.append("Avoid large market orders, use limit orders")
            
            return MarketStressIndicator(
                overall_stress_level=stress_level,
                stress_score=overall_stress,
                volatility_stress=avg_volatility_stress,
                funding_rate_stress=avg_funding_stress,
                liquidity_stress=avg_liquidity_stress,
                correlation_stress=correlation_stress,
                leverage_stress=leverage_stress,
                avg_funding_rate=np.mean(funding_rate_readings) / 100 if funding_rate_readings else 0.0,
                total_open_interest_change=0.0,  # Would need historical OI data
                liquidation_volume_24h=total_liquidation_volume,
                btc_dominance=50.0,  # Would fetch from external API
                correlation_breakdown=correlation_stress > 70,
                active_risk_factors=risk_factors,
                warning_signals=warning_signals,
                recommended_actions=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error assessing market stress: {e}")
            # Return default stress indicator
            return MarketStressIndicator(
                overall_stress_level=MarketStressLevel.ELEVATED,
                stress_score=50.0,
                volatility_stress=50.0,
                funding_rate_stress=50.0,
                liquidity_stress=50.0,
                correlation_stress=50.0,
                leverage_stress=50.0,
                avg_funding_rate=0.0,
                total_open_interest_change=0.0,
                liquidation_volume_24h=0.0,
                btc_dominance=50.0,
                correlation_breakdown=False,
                active_risk_factors=["data_insufficient"],
                warning_signals=["Unable to fully assess market conditions"],
                recommended_actions=["Exercise increased caution"]
            )
    
    async def assess_liquidation_risk(self, 
                                    symbol: str, 
                                    exchange_id: str,
                                    time_horizon_minutes: int = 60) -> LiquidationRisk:
        """Assess liquidation risk for a specific symbol."""
        
        try:
            # Fetch market data
            market_data = await self._fetch_liquidation_analysis_data(
                symbol, exchange_id, time_horizon_minutes
            )
            
            if not market_data:
                raise ValueError(f"Unable to fetch market data for {symbol}")
            
            # Calculate risk components
            funding_pressure = await self._calculate_funding_rate_pressure(market_data)
            liquidity_risk = self._calculate_liquidity_risk(market_data)
            technical_weakness = self._assess_technical_weakness(market_data)
            
            # Calculate overall liquidation probability
            risk_factors = [funding_pressure, liquidity_risk, technical_weakness]
            liquidation_probability = np.mean(risk_factors) / 100  # Convert to 0-1 scale
            
            # Determine risk level
            if liquidation_probability < 0.25:
                risk_level = LiquidationSeverity.LOW
            elif liquidation_probability < 0.5:
                risk_level = LiquidationSeverity.MEDIUM
            elif liquidation_probability < 0.75:
                risk_level = LiquidationSeverity.HIGH
            else:
                risk_level = LiquidationSeverity.CRITICAL
            
            # Calculate support/resistance levels
            support_levels, resistance_levels = self._calculate_key_levels(market_data)
            
            current_price = market_data.ohlcv['close'].iloc[-1]
            
            # Estimate distance to risk zone
            nearest_support = min(support_levels) if support_levels else current_price * 0.9
            distance_to_risk = ((current_price - nearest_support) / current_price) * 100
            
            return LiquidationRisk(
                symbol=symbol,
                exchange=exchange_id,
                liquidation_probability=liquidation_probability,
                risk_level=risk_level,
                time_horizon_minutes=time_horizon_minutes,
                funding_rate_pressure=funding_pressure,
                liquidity_risk=liquidity_risk,
                technical_weakness=technical_weakness,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                current_price=current_price,
                price_distance_to_risk=distance_to_risk,
                volume_profile_support=self._calculate_volume_support(market_data),
                similar_events_count=self._count_similar_historical_events(market_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error assessing liquidation risk for {symbol}: {e}")
            raise
    
    async def detect_cascade_risk(self, 
                                symbols: List[str],
                                exchanges: Optional[List[str]] = None) -> List[CascadeAlert]:
        """Detect potential cascade liquidation risks."""
        
        alerts = []
        
        try:
            # Assess individual symbol risks
            risk_assessments = []
            for symbol in symbols:
                for exchange_id in (exchanges or list(self.exchange_manager.exchanges.keys())):
                    try:
                        risk = await self.assess_liquidation_risk(symbol, exchange_id)
                        risk_assessments.append(risk)
                    except Exception as e:
                        continue
            
            # Look for cascade patterns
            high_risk_symbols = [r for r in risk_assessments if r.liquidation_probability > 0.6]
            
            if len(high_risk_symbols) >= 3:  # Multiple symbols at risk
                # Calculate cascade probability
                avg_risk = np.mean([r.liquidation_probability for r in high_risk_symbols])
                correlation_factor = 0.8  # Simplified - would calculate actual correlations
                cascade_probability = min(1.0, avg_risk * correlation_factor)
                
                if cascade_probability > 0.5:
                    # Generate cascade alert
                    alert = CascadeAlert(
                        alert_id=str(uuid.uuid4()),
                        severity=LiquidationSeverity.HIGH if cascade_probability > 0.7 else LiquidationSeverity.MEDIUM,
                        initiating_symbol=high_risk_symbols[0].symbol,
                        affected_symbols=[r.symbol for r in high_risk_symbols],
                        cascade_probability=cascade_probability,
                        estimated_total_liquidations=sum(
                            self._estimate_liquidation_volume(r) for r in high_risk_symbols
                        ),
                        price_impact_range={
                            r.symbol: r.liquidation_probability * 10  # Simplified impact estimate
                            for r in high_risk_symbols
                        },
                        duration_estimate_minutes=int(30 + cascade_probability * 60),
                        overall_leverage=3.5,  # Would calculate from market data
                        liquidity_adequacy=60 - cascade_probability * 30,
                        correlation_strength=correlation_factor,
                        immediate_actions=[
                            "Reduce leverage across correlated positions",
                            "Set tight stop-losses",
                            "Monitor order book depth closely"
                        ],
                        risk_mitigation=[
                            "Diversify across uncorrelated assets",
                            "Maintain higher cash reserves",
                            "Use smaller position sizes"
                        ],
                        monitoring_priorities=[s.symbol for s in high_risk_symbols[:5]]
                    )
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error detecting cascade risk: {e}")
            return []
    
    async def _fetch_liquidation_analysis_data(self, symbol: str, exchange_id: str, lookback_minutes: int) -> Optional[MarketData]:
        """Fetch comprehensive market data for liquidation analysis."""
        
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            
            # Fetch OHLCV data
            timeframe = '1m' if lookback_minutes <= 120 else '5m'
            limit = min(500, lookback_minutes if timeframe == '1m' else lookback_minutes // 5)
            
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 10:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Fetch order book
            orderbook = await exchange.fetch_order_book(symbol, limit=50)
            
            # Fetch recent trades
            trades = []
            try:
                recent_trades = await exchange.fetch_trades(symbol, limit=100)
                trades = recent_trades or []
            except Exception as e:
                pass
            
            # Fetch funding rate if available
            funding_rate = None
            try:
                funding_info = await exchange.fetch_funding_rate(symbol)
                if funding_info and 'fundingRate' in funding_info:
                    funding_rate = funding_info['fundingRate']
            except Exception as e:
                pass
            
            return MarketData(
                symbol=symbol,
                exchange=exchange_id,
                ohlcv=df,
                orderbook=orderbook,
                trades=trades,
                funding_rate=funding_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    async def _analyze_liquidation_patterns(self, market_data: MarketData, sensitivity: float) -> List[LiquidationEvent]:
        """Analyze market data for liquidation patterns."""
        
        events = []
        df = market_data.ohlcv
        
        if len(df) < 20:
            return events
        
        # Calculate technical indicators
        df['returns'] = df['close'].pct_change()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volatility'] = df['returns'].rolling(20).std()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        # Detect volume spikes
        volume_threshold = df['volume_sma'].iloc[-1] * self.volume_spike_threshold * sensitivity
        recent_data = df.tail(10)  # Last 10 periods
        
        for idx, row in recent_data.iterrows():
            if row['volume'] > volume_threshold:
                # Potential liquidation event detected
                price_change = abs(row['returns']) if not pd.isna(row['returns']) else 0
                
                if price_change > self.price_impact_threshold * sensitivity:
                    # Classify liquidation type
                    liquidation_type = self._classify_liquidation_type(row, df, market_data)
                    
                    # Calculate severity
                    severity = self._calculate_event_severity(row, df, sensitivity)
                    
                    # Calculate confidence score
                    confidence = self._calculate_detection_confidence(row, df, market_data)
                    
                    if confidence > sensitivity:
                        event = LiquidationEvent(
                            event_id=str(uuid.uuid4()),
                            symbol=market_data.symbol,
                            exchange=market_data.exchange,
                            timestamp=idx,
                            liquidation_type=liquidation_type,
                            severity=severity,
                            confidence_score=confidence,
                            trigger_price=row['close'],
                            price_impact=price_change * 100,
                            volume_spike_ratio=row['volume'] / df['volume_sma'].iloc[-1],
                            bid_ask_spread_pct=self._calculate_spread_percentage(market_data.orderbook),
                            order_book_imbalance=self._calculate_orderbook_imbalance(market_data.orderbook),
                            market_depth_impact=self._calculate_depth_impact(market_data.orderbook, row['volume']),
                            rsi=row['rsi'],
                            volume_weighted_price=self._calculate_vwap(df.tail(20)),
                            volatility_spike=row['volatility'] / df['volatility'].mean() if df['volatility'].mean() > 0 else 1,
                            funding_rate=market_data.funding_rate,
                            duration_seconds=300,  # Simplified - would calculate actual duration
                            suspected_triggers=self._identify_triggers(row, df, market_data) + ['pattern_detection'],
                            market_conditions=self._extract_market_conditions(df, market_data)
                        )
                        events.append(event)
        
        return events
    
    def _calculate_spread_percentage(self, orderbook: Dict) -> float:
        """Calculate bid-ask spread percentage."""
        try:
            if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                return 1.0  # Default high spread for missing data
            
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            spread = (best_ask - best_bid) / best_bid * 100
            return spread
        except Exception as e:
            return 1.0
    
    def _calculate_orderbook_imbalance(self, orderbook: Dict) -> float:
        """Calculate order book imbalance (-1 to 1)."""
        try:
            if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                return 0.0
            
            bid_volume = sum(bid[1] for bid in orderbook['bids'][:10])
            ask_volume = sum(ask[1] for ask in orderbook['asks'][:10])
            total_volume = bid_volume + ask_volume
            
            if total_volume == 0:
                return 0.0
            
            imbalance = (bid_volume - ask_volume) / total_volume
            return imbalance
        except Exception as e:
            return 0.0
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _classify_liquidation_type(self, row: pd.Series, df: pd.DataFrame, market_data: MarketData) -> LiquidationType:
        """Classify the type of liquidation event."""
        
        price_change = row['returns']
        volume_ratio = row['volume'] / df['volume'].mean()
        
        # Simple classification logic
        if volume_ratio > 5 and abs(price_change) > 0.05:
            return LiquidationType.CASCADE_EVENT
        elif price_change < -0.03:
            return LiquidationType.LONG_LIQUIDATION
        elif price_change > 0.03:
            return LiquidationType.SHORT_LIQUIDATION
        else:
            return LiquidationType.FLASH_CRASH
    
    def _calculate_event_severity(self, row: pd.Series, df: pd.DataFrame, sensitivity: float) -> LiquidationSeverity:
        """Calculate event severity."""
        
        price_impact = abs(row['returns'])
        volume_impact = row['volume'] / df['volume'].mean()
        
        severity_score = (price_impact * 100 + volume_impact * 10) / 2
        
        if severity_score < 2:
            return LiquidationSeverity.LOW
        elif severity_score < 5:
            return LiquidationSeverity.MEDIUM
        elif severity_score < 10:
            return LiquidationSeverity.HIGH
        else:
            return LiquidationSeverity.CRITICAL
    
    def _calculate_detection_confidence(self, row: pd.Series, df: pd.DataFrame, market_data: MarketData) -> float:
        """Calculate confidence in liquidation detection."""
        
        # Factors that increase confidence:
        # 1. Volume spike magnitude
        # 2. Price impact
        # 3. Order book disruption
        # 4. Technical indicator confluence
        
        volume_confidence = min(1.0, (row['volume'] / df['volume'].mean()) / 5)
        price_confidence = min(1.0, abs(row['returns']) / 0.05)
        
        # Additional factors would be added here
        overall_confidence = (volume_confidence + price_confidence) / 2
        
        return overall_confidence
    
    # Helper methods for additional calculations
    def _calculate_depth_impact(self, orderbook: Dict, volume: float) -> float:
        """Calculate impact on market depth."""
        # Simplified calculation
        return min(100, volume / 1000000 * 10)
    
    def _calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate Volume Weighted Average Price."""
        return (df['close'] * df['volume']).sum() / df['volume'].sum()
    
    def _identify_triggers(self, row: pd.Series, df: pd.DataFrame, market_data: MarketData) -> List[str]:
        """Identify potential liquidation triggers."""
        triggers = []
        
        if market_data.funding_rate and abs(market_data.funding_rate) > 0.005:
            triggers.append("high_funding_rate")
        
        if row['volume'] > df['volume'].mean() * 5:
            triggers.append("volume_spike")
        
        if abs(row['returns']) > 0.03:
            triggers.append("price_shock")
        
        return triggers
    
    def _extract_market_conditions(self, df: pd.DataFrame, market_data: MarketData) -> Dict:
        """Extract current market conditions."""
        return {
            "volatility": df['volatility'].iloc[-1] if not df['volatility'].empty else 0,
            "volume_trend": "increasing" if df['volume'].iloc[-1] > df['volume'].mean() else "normal",
            "funding_rate": market_data.funding_rate or 0
        }
    
    async def _calculate_funding_rate_pressure(self, market_data: MarketData) -> float:
        """Calculate funding rate pressure score (0-100)."""
        if not market_data.funding_rate:
            return 30.0  # Default moderate pressure when data unavailable
        
        funding_rate = abs(market_data.funding_rate)
        # Convert funding rate to pressure score
        pressure = min(100, (funding_rate / self.funding_rate_stress_threshold) * 50)
        return pressure
    
    def _calculate_liquidity_risk(self, market_data: MarketData) -> float:
        """Calculate liquidity risk score (0-100)."""
        spread = self._calculate_spread_percentage(market_data.orderbook)
        imbalance = abs(self._calculate_orderbook_imbalance(market_data.orderbook))
        
        # Combine spread and imbalance for liquidity risk
        spread_risk = min(100, spread * 100)  # High spread = high risk
        imbalance_risk = imbalance * 100  # High imbalance = high risk
        
        liquidity_risk = (spread_risk + imbalance_risk) / 2
        return min(100, liquidity_risk)
    
    def _assess_technical_weakness(self, market_data: MarketData) -> float:
        """Assess technical weakness score (0-100)."""
        df = market_data.ohlcv
        
        # Calculate various technical indicators
        current_rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns and not df['rsi'].empty else 50
        current_price = df['close'].iloc[-1]
        
        # Price relative to recent high/low
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        price_position = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
        
        # Volume trend weakness
        recent_volume = df['volume'].tail(5).mean()
        historical_volume = df['volume'].mean()
        volume_weakness = max(0, (historical_volume - recent_volume) / historical_volume * 100) if historical_volume > 0 else 0
        
        # Combine indicators
        rsi_weakness = max(0, 30 - current_rsi) + max(0, current_rsi - 70)  # Extreme RSI levels
        position_weakness = (1 - price_position) * 100 if price_position < 0.5 else 0  # Near lows
        
        technical_weakness = (rsi_weakness + position_weakness + volume_weakness) / 3
        return min(100, technical_weakness)
    
    def _calculate_key_levels(self, market_data: MarketData) -> Tuple[List[float], List[float]]:
        """Calculate key support and resistance levels."""
        df = market_data.ohlcv
        
        # Simple pivot-based support/resistance
        highs = df['high'].rolling(5, center=True).max()
        lows = df['low'].rolling(5, center=True).min()
        
        # Find pivot points
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(df) - 2):
            if df['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append(df['high'].iloc[i])
            if df['low'].iloc[i] == lows.iloc[i]:
                support_levels.append(df['low'].iloc[i])
        
        # Keep only recent and significant levels
        current_price = df['close'].iloc[-1]
        support_levels = [level for level in support_levels if level < current_price][-5:]
        resistance_levels = [level for level in resistance_levels if level > current_price][-5:]
        
        return support_levels, resistance_levels
    
    def _calculate_volume_support(self, market_data: MarketData) -> float:
        """Calculate volume-based support strength (0-100)."""
        df = market_data.ohlcv
        
        # Calculate volume at different price levels (simplified)
        current_price = df['close'].iloc[-1]
        
        # Volume below current price (support)
        below_current = df[df['close'] < current_price]
        support_volume = below_current['volume'].sum() if not below_current.empty else 0
        
        # Total volume
        total_volume = df['volume'].sum()
        
        support_strength = (support_volume / total_volume * 100) if total_volume > 0 else 50
        return min(100, support_strength)
    
    def _count_similar_historical_events(self, market_data: MarketData) -> int:
        """Count similar historical liquidation events."""
        # Simplified - would implement proper pattern matching
        df = market_data.ohlcv
        
        # Look for similar volume spikes in recent history
        volume_mean = df['volume'].mean()
        volume_threshold = volume_mean * self.volume_spike_threshold
        
        similar_events = (df['volume'] > volume_threshold).sum()
        return int(similar_events)
    
    def _estimate_liquidation_volume(self, risk_assessment: LiquidationRisk) -> float:
        """Estimate potential liquidation volume in USD."""
        # Simplified estimation based on risk probability and market conditions
        base_volume = 1000000  # $1M base
        risk_multiplier = risk_assessment.liquidation_probability * 5
        
        estimated_volume = base_volume * risk_multiplier
        return estimated_volume
    
    # ==================== REAL LIQUIDATION DATA METHODS ====================
    
    async def start_real_liquidation_collection(self, symbols: List[str]) -> bool:
        """Start collecting real liquidation data from exchanges."""
        try:
            if self.storage:
                await self.storage.create_tables()
            
            # Start the liquidation data collector
            await self.liquidation_collector.start_collection(symbols)
            self.is_collecting_real_data = True
            
            self.logger.info(f"Started real liquidation data collection for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting real liquidation collection: {e}")
            return False
    
    async def stop_real_liquidation_collection(self):
        """Stop collecting real liquidation data."""
        try:
            await self.liquidation_collector.stop_collection()
            self.is_collecting_real_data = False
            self.logger.info("Stopped real liquidation data collection")
        except Exception as e:
            self.logger.error(f"Error stopping real liquidation collection: {e}")
    
    async def _store_real_liquidation_event(self, liquidation_event: LiquidationEvent):
        """Callback to store real liquidation events."""
        try:
            # Update statistics
            self.collection_stats['total_real_liquidations'] += 1
            self.collection_stats['last_real_liquidation'] = datetime.utcnow()
            
            # Store to database if available
            if self.storage:
                await self.storage.store_liquidation_event(liquidation_event)
            
            # Add to historical events for pattern recognition
            self.historical_events.append(liquidation_event)
            
            self.logger.debug(f"Stored real liquidation event: {liquidation_event.event_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing real liquidation event: {e}")
    
    async def _get_recent_real_liquidations(self, symbols: List[str], exchanges: List[str], lookback_minutes: int) -> List[LiquidationEvent]:
        """Get recent real liquidation events from collector and storage."""
        real_events = []
        
        try:
            # Get from in-memory collector first (most recent)
            for symbol in symbols:
                for exchange in exchanges:
                    events = self.liquidation_collector.get_recent_liquidations(
                        symbol, exchange, lookback_minutes
                    )
                    real_events.extend(events)
            
            # Get additional events from database if available
            if self.storage:
                start_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)
                for symbol in symbols:
                    for exchange in exchanges:
                        db_events = await self.storage.get_liquidation_events(
                            symbol=symbol,
                            exchange=exchange,
                            start_time=start_time,
                            limit=100
                        )
                        real_events.extend(db_events)
            
            # Remove duplicates based on event_id
            seen_ids = set()
            unique_events = []
            for event in real_events:
                if event.event_id not in seen_ids:
                    seen_ids.add(event.event_id)
                    unique_events.append(event)
            
            self.logger.debug(f"Retrieved {len(unique_events)} real liquidation events")
            return unique_events
            
        except Exception as e:
            self.logger.error(f"Error getting recent real liquidations: {e}")
            return []
    
    async def _store_detected_events(self, events: List[LiquidationEvent]):
        """Store pattern-detected events to database."""
        try:
            if not self.storage:
                return
            
            pattern_events = [e for e in events if 'pattern_detection' in e.suspected_triggers]
            if pattern_events:
                stored_count = await self.storage.store_liquidation_events_batch(pattern_events)
                self.collection_stats['total_inferred_liquidations'] += stored_count
                self.logger.debug(f"Stored {stored_count} pattern-detected liquidation events")
                
        except Exception as e:
            self.logger.error(f"Error storing detected events: {e}")
    
    def _merge_similar_events(self, events: List[LiquidationEvent]) -> List[LiquidationEvent]:
        """Merge similar liquidation events to avoid duplicates."""
        if not events:
            return events
        
        # Group events by symbol, exchange, and time window (5 minutes)
        grouped_events = defaultdict(list)
        
        for event in events:
            # Create grouping key
            time_bucket = event.timestamp.replace(second=0, microsecond=0)
            time_bucket = time_bucket.replace(minute=(time_bucket.minute // 5) * 5)
            
            group_key = (event.symbol, event.exchange, time_bucket)
            grouped_events[group_key].append(event)
        
        # Merge events in each group
        merged_events = []
        for group_key, group_events in grouped_events.items():
            if len(group_events) == 1:
                merged_events.append(group_events[0])
            else:
                # Merge multiple events into one
                merged_event = self._merge_event_group(group_events)
                merged_events.append(merged_event)
        
        return merged_events
    
    def _merge_event_group(self, events: List[LiquidationEvent]) -> LiquidationEvent:
        """Merge a group of similar liquidation events."""
        # Sort by timestamp to get the earliest event as base
        events.sort(key=lambda x: x.timestamp)
        base_event = events[0]
        
        # Aggregate metrics from all events
        total_volume = sum(e.liquidated_amount_usd for e in events)
        max_price_impact = max(e.price_impact for e in events)
        avg_confidence = sum(e.confidence_score for e in events) / len(events)
        
        # Determine highest severity
        severities = [e.severity for e in events]
        max_severity = max(severities, key=lambda x: x.value)
        
        # Combine suspected triggers
        all_triggers = set()
        for event in events:
            all_triggers.update(event.suspected_triggers)
        
        # Create merged event
        merged_event = LiquidationEvent(
            event_id=f"merged_{base_event.event_id}_{len(events)}",
            symbol=base_event.symbol,
            exchange=base_event.exchange,
            timestamp=base_event.timestamp,
            liquidation_type=base_event.liquidation_type,
            severity=max_severity,
            confidence_score=avg_confidence,
            trigger_price=base_event.trigger_price,
            price_impact=max_price_impact,
            volume_spike_ratio=max(e.volume_spike_ratio for e in events),
            liquidated_amount_usd=total_volume,
            bid_ask_spread_pct=base_event.bid_ask_spread_pct,
            order_book_imbalance=base_event.order_book_imbalance,
            market_depth_impact=max(e.market_depth_impact for e in events),
            duration_seconds=sum(e.duration_seconds for e in events),
            suspected_triggers=list(all_triggers),
            market_conditions={
                **base_event.market_conditions,
                'merged_events_count': len(events),
                'data_sources': ['real_data', 'pattern_detection']
            }
        )
        
        return merged_event
    
    async def get_liquidation_statistics(self, 
                                       symbol: Optional[str] = None,
                                       exchange: Optional[str] = None,
                                       hours: int = 24) -> Dict:
        """Get comprehensive liquidation statistics."""
        try:
            stats = {
                'collection_stats': self.collection_stats.copy(),
                'is_collecting_real_data': self.is_collecting_real_data,
                'collector_stats': self.liquidation_collector.get_collection_stats() if self.is_collecting_real_data else {},
                'database_stats': {}
            }
            
            # Get database statistics if storage available
            if self.storage:
                db_stats = await self.storage.get_liquidation_statistics(symbol, exchange, hours)
                stats['database_stats'] = db_stats
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting liquidation statistics: {e}")
            return {'error': str(e)}
    
    async def get_historical_liquidations(self,
                                        symbol: Optional[str] = None,
                                        exchange: Optional[str] = None,
                                        start_time: Optional[datetime] = None,
                                        end_time: Optional[datetime] = None,
                                        limit: int = 1000) -> List[LiquidationEvent]:
        """Get historical liquidation events from storage."""
        try:
            if not self.storage:
                self.logger.warning("No storage configured for historical liquidations")
                return []
            
            events = await self.storage.get_liquidation_events(
                symbol=symbol,
                exchange=exchange,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting historical liquidations: {e}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """Clean up old liquidation data."""
        try:
            cleanup_result = {'deleted_count': 0, 'success': False}
            
            if self.storage:
                deleted_count = await self.storage.cleanup_old_events(days_to_keep)
                cleanup_result = {
                    'deleted_count': deleted_count,
                    'success': True,
                    'days_kept': days_to_keep
                }
            
            return cleanup_result
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return {'error': str(e), 'success': False} 