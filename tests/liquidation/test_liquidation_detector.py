import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from src.core.analysis.liquidation_detector import LiquidationDetectionEngine, MarketData
from src.core.models.liquidation import LiquidationSeverity, LiquidationType


class TestLiquidationDetectionEngine:
    
    @pytest.fixture
    def mock_exchange_manager(self):
        """Create mock exchange manager for testing."""
        manager = Mock()
        exchange = Mock()
        
        # Mock successful OHLCV data
        ohlcv_data = [
            [1640995200000, 45000, 45500, 44800, 45200, 1000000],
            [1640998800000, 45200, 45600, 45000, 45400, 1200000],
            [1641002400000, 45400, 45300, 43000, 43500, 8000000],  # Large volume spike + price drop
            [1641006000000, 43500, 44000, 43200, 43800, 2000000],
        ]
        
        exchange.fetch_ohlcv = AsyncMock(return_value=ohlcv_data)
        exchange.fetch_order_book = AsyncMock(return_value={
            "bids": [[43750, 100], [43700, 150], [43650, 200]],
            "asks": [[43850, 80], [43900, 120], [43950, 160]]
        })
        exchange.fetch_trades = AsyncMock(return_value=[])
        exchange.fetch_funding_rate = AsyncMock(return_value={"fundingRate": 0.005})
        
        manager.exchanges = {"binance": exchange}
        return manager
    
    @pytest.fixture
    def detector(self, mock_exchange_manager):
        """Create liquidation detector instance."""
        return LiquidationDetectionEngine(mock_exchange_manager)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        timestamps = pd.date_range('2024-01-01', periods=100, freq='5min')
        np.random.seed(42)  # For reproducible tests
        
        prices = 45000 + np.cumsum(np.random.randn(100) * 10)
        volumes = np.random.lognormal(13, 0.5, 100)  # Log-normal distribution for volumes
        
        # Create a liquidation event at index 80
        volumes[80] = volumes[80] * 5  # Volume spike
        prices[80] = prices[79] * 0.95  # Price drop
        
        df = pd.DataFrame({
            'open': prices,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volumes
        }, index=timestamps)
        
        return MarketData(
            symbol="BTCUSDT",
            exchange="binance", 
            ohlcv=df,
            orderbook={
                "bids": [[44000, 100], [43950, 150]],
                "asks": [[44100, 80], [44150, 120]]
            },
            trades=[],
            funding_rate=0.005
        )
    
    @pytest.mark.asyncio
    async def test_fetch_liquidation_analysis_data(self, detector):
        """Test fetching market data for analysis."""
        data = await detector._fetch_liquidation_analysis_data("BTCUSDT", "binance", 60)
        
        assert data is not None
        assert data.symbol == "BTCUSDT"
        assert data.exchange == "binance"
        assert isinstance(data.ohlcv, pd.DataFrame)
        assert not data.ohlcv.empty
        assert data.funding_rate is not None
    
    @pytest.mark.asyncio
    async def test_analyze_liquidation_patterns(self, detector, sample_market_data):
        """Test liquidation pattern analysis."""
        events = await detector._analyze_liquidation_patterns(sample_market_data, sensitivity=0.7)
        
        assert isinstance(events, list)
        # Should detect the artificial liquidation event we created
        assert len(events) > 0
        
        event = events[0]
        assert event.symbol == "BTCUSDT"
        assert event.exchange == "binance"
        assert isinstance(event.severity, LiquidationSeverity)
        assert isinstance(event.liquidation_type, LiquidationType)
    
    def test_calculate_spread_percentage(self, detector):
        """Test bid-ask spread calculation."""
        orderbook = {
            "bids": [[100, 10], [99, 15]],
            "asks": [[101, 8], [102, 12]]
        }
        
        spread = detector._calculate_spread_percentage(orderbook)
        expected_spread = (101 - 100) / 100 * 100  # 1%
        
        assert abs(spread - expected_spread) < 0.01
    
    def test_calculate_orderbook_imbalance(self, detector):
        """Test order book imbalance calculation."""
        # More bids than asks
        orderbook = {
            "bids": [[100, 100], [99, 50]],  # Total: 150
            "asks": [[101, 50], [102, 25]]   # Total: 75
        }
        
        imbalance = detector._calculate_orderbook_imbalance(orderbook)
        expected = (150 - 75) / (150 + 75)  # Positive imbalance (more bids)
        
        assert abs(imbalance - expected) < 0.01
    
    def test_calculate_rsi(self, detector):
        """Test RSI calculation."""
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106])
        rsi = detector._calculate_rsi(prices, period=6)
        
        # RSI should be between 0 and 100
        assert rsi.dropna().min() >= 0
        assert rsi.dropna().max() <= 100
    
    def test_classify_liquidation_type(self, detector, sample_market_data):
        """Test liquidation type classification."""
        df = sample_market_data.ohlcv
        df['returns'] = df['close'].pct_change()
        
        # Test long liquidation (price drop)
        row_down = pd.Series({
            'returns': -0.04,  # 4% drop
            'volume': df['volume'].mean() * 3
        })
        liquidation_type = detector._classify_liquidation_type(row_down, df, sample_market_data)
        assert liquidation_type == LiquidationType.LONG_LIQUIDATION
        
        # Test short liquidation (price rise)
        row_up = pd.Series({
            'returns': 0.04,  # 4% rise
            'volume': df['volume'].mean() * 3
        })
        liquidation_type = detector._classify_liquidation_type(row_up, df, sample_market_data)
        assert liquidation_type == LiquidationType.SHORT_LIQUIDATION
    
    def test_calculate_event_severity(self, detector, sample_market_data):
        """Test event severity calculation."""
        df = sample_market_data.ohlcv
        
        # High impact event
        high_impact_row = pd.Series({
            'returns': -0.05,  # 5% drop
            'volume': df['volume'].mean() * 8  # 8x volume
        })
        severity = detector._calculate_event_severity(high_impact_row, df, 0.7)
        assert severity in [LiquidationSeverity.HIGH, LiquidationSeverity.CRITICAL]
        
        # Low impact event
        low_impact_row = pd.Series({
            'returns': -0.01,  # 1% drop
            'volume': df['volume'].mean() * 1.5  # 1.5x volume
        })
        severity = detector._calculate_event_severity(low_impact_row, df, 0.7)
        assert severity in [LiquidationSeverity.LOW, LiquidationSeverity.MEDIUM]
    
    def test_calculate_detection_confidence(self, detector, sample_market_data):
        """Test confidence calculation for detection."""
        df = sample_market_data.ohlcv
        
        # High confidence scenario
        high_conf_row = pd.Series({
            'returns': -0.06,  # Large price impact
            'volume': df['volume'].mean() * 6  # Large volume spike
        })
        confidence = detector._calculate_detection_confidence(high_conf_row, df, sample_market_data)
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should be high confidence
        
        # Low confidence scenario
        low_conf_row = pd.Series({
            'returns': -0.005,  # Small price impact
            'volume': df['volume'].mean() * 1.1  # Small volume increase
        })
        confidence = detector._calculate_detection_confidence(low_conf_row, df, sample_market_data)
        assert 0 <= confidence <= 1
        assert confidence < 0.5  # Should be low confidence
    
    @pytest.mark.asyncio
    async def test_calculate_funding_rate_pressure(self, detector, sample_market_data):
        """Test funding rate pressure calculation."""
        # High funding rate
        sample_market_data.funding_rate = 0.02  # 2%
        pressure = await detector._calculate_funding_rate_pressure(sample_market_data)
        assert pressure > 50  # Should be high pressure
        
        # Normal funding rate
        sample_market_data.funding_rate = 0.001  # 0.1%
        pressure = await detector._calculate_funding_rate_pressure(sample_market_data)
        assert pressure < 50  # Should be lower pressure
        
        # No funding rate data
        sample_market_data.funding_rate = None
        pressure = await detector._calculate_funding_rate_pressure(sample_market_data)
        assert pressure == 30.0  # Default value
    
    def test_calculate_liquidity_risk(self, detector, sample_market_data):
        """Test liquidity risk calculation."""
        # Modify orderbook for high spread (low liquidity)
        sample_market_data.orderbook = {
            "bids": [[44000, 10]],
            "asks": [[45000, 10]]  # 2.3% spread
        }
        
        risk = detector._calculate_liquidity_risk(sample_market_data)
        assert 0 <= risk <= 100
        assert risk > 50  # Should indicate high liquidity risk
    
    def test_assess_technical_weakness(self, detector, sample_market_data):
        """Test technical weakness assessment."""
        df = sample_market_data.ohlcv
        
        # Add RSI to dataframe (simulate oversold condition)
        df['rsi'] = 25.0  # Oversold
        
        weakness = detector._assess_technical_weakness(sample_market_data)
        assert 0 <= weakness <= 100
        # Should show some weakness due to oversold RSI
    
    def test_calculate_key_levels(self, detector, sample_market_data):
        """Test support and resistance level calculation."""
        support_levels, resistance_levels = detector._calculate_key_levels(sample_market_data)
        
        assert isinstance(support_levels, list)
        assert isinstance(resistance_levels, list)
        
        current_price = sample_market_data.ohlcv['close'].iloc[-1]
        
        # Support levels should be below current price
        for level in support_levels:
            assert level < current_price
        
        # Resistance levels should be above current price
        for level in resistance_levels:
            assert level > current_price
    
    def test_calculate_volume_support(self, detector, sample_market_data):
        """Test volume-based support calculation."""
        support = detector._calculate_volume_support(sample_market_data)
        
        assert 0 <= support <= 100
        assert isinstance(support, (int, float))
    
    def test_count_similar_historical_events(self, detector, sample_market_data):
        """Test counting similar historical events."""
        count = detector._count_similar_historical_events(sample_market_data)
        
        assert isinstance(count, int)
        assert count >= 0
        # Should find the artificial volume spike we created
        assert count > 0
    
    @pytest.mark.asyncio
    async def test_detect_liquidation_events_integration(self, detector):
        """Integration test for full liquidation detection."""
        events = await detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.5,  # Lower sensitivity to catch our artificial event
            lookback_minutes=60
        )
        
        assert isinstance(events, list)
        # The mock data includes a liquidation pattern
    
    @pytest.mark.asyncio 
    async def test_assess_market_stress_integration(self, detector):
        """Integration test for market stress assessment."""
        stress = await detector.assess_market_stress(
            symbols=["BTCUSDT", "ETHUSDT"],
            exchanges=["binance"]
        )
        
        assert hasattr(stress, "overall_stress_level")
        assert hasattr(stress, "stress_score")
        assert 0 <= stress.stress_score <= 100
        assert isinstance(stress.active_risk_factors, list)
        assert isinstance(stress.warning_signals, list)
        assert isinstance(stress.recommended_actions, list)
    
    @pytest.mark.asyncio
    async def test_assess_liquidation_risk_integration(self, detector):
        """Integration test for liquidation risk assessment."""
        risk = await detector.assess_liquidation_risk(
            symbol="BTCUSDT",
            exchange_id="binance",
            time_horizon_minutes=60
        )
        
        assert risk.symbol == "BTCUSDT"
        assert risk.exchange == "binance"
        assert 0 <= risk.liquidation_probability <= 1
        assert isinstance(risk.risk_level, LiquidationSeverity)
        assert risk.time_horizon_minutes == 60
    
    @pytest.mark.asyncio
    async def test_detect_cascade_risk_integration(self, detector):
        """Integration test for cascade risk detection."""
        alerts = await detector.detect_cascade_risk(
            symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            exchanges=["binance"]
        )
        
        assert isinstance(alerts, list)
        # Cascade detection requires multiple high-risk symbols
        for alert in alerts:
            assert hasattr(alert, "cascade_probability")
            assert hasattr(alert, "affected_symbols")
            assert hasattr(alert, "immediate_actions")
    
    @pytest.mark.asyncio
    async def test_error_handling_insufficient_data(self, detector, mock_exchange_manager):
        """Test error handling when insufficient data is available."""
        # Mock exchange to return empty data
        exchange = mock_exchange_manager.exchanges["binance"]
        exchange.fetch_ohlcv = AsyncMock(return_value=[])
        
        events = await detector.detect_liquidation_events(
            symbols=["INVALID"],
            exchanges=["binance"],
            sensitivity=0.7,
            lookback_minutes=60
        )
        
        # Should handle gracefully
        assert isinstance(events, list)
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_exchange_failure(self, detector, mock_exchange_manager):
        """Test error handling when exchange calls fail."""
        # Mock exchange to raise exceptions
        exchange = mock_exchange_manager.exchanges["binance"]
        exchange.fetch_ohlcv = AsyncMock(side_effect=Exception("Network error"))
        
        events = await detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.7,
            lookback_minutes=60
        )
        
        # Should handle gracefully and return empty list
        assert isinstance(events, list)
        assert len(events) == 0 