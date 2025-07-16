import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.core.models.liquidation import (
    LiquidationEvent, MarketStressIndicator, LiquidationRisk, CascadeAlert,
    LiquidationSeverity, MarketStressLevel, LiquidationType
)
from src.core.analysis.liquidation_detector import LiquidationDetectionEngine

class TestLiquidationAPI:
    
    @pytest.fixture
    def mock_liquidation_detector(self):
        """Mock liquidation detector for testing."""
        detector = Mock(spec=LiquidationDetectionEngine)
        
        # Mock liquidation event
        mock_event = LiquidationEvent(
            event_id="test_event_1",
            symbol="BTCUSDT",
            exchange="binance",
            timestamp=datetime.utcnow(),
            liquidation_type=LiquidationType.LONG_LIQUIDATION,
            severity=LiquidationSeverity.HIGH,
            confidence_score=0.85,
            trigger_price=45000.0,
            price_impact=-3.5,
            volume_spike_ratio=4.2,
            bid_ask_spread_pct=0.02,
            order_book_imbalance=-0.3,
            market_depth_impact=25.0,
            rsi=25.0,
            volume_weighted_price=45100.0,
            volatility_spike=2.1,
            duration_seconds=180,
            suspected_triggers=["funding_rate_stress", "volume_spike"],
            market_conditions={"volatility": 0.05, "volume_trend": "increasing"}
        )
        
        # Mock market stress indicator
        mock_stress = MarketStressIndicator(
            overall_stress_level=MarketStressLevel.HIGH,
            stress_score=75.0,
            volatility_stress=80.0,
            funding_rate_stress=70.0,
            liquidity_stress=65.0,
            correlation_stress=60.0,
            leverage_stress=85.0,
            avg_funding_rate=0.008,
            total_open_interest_change=-12.5,
            liquidation_volume_24h=50000000.0,
            btc_dominance=42.5,
            correlation_breakdown=True,
            active_risk_factors=["elevated_volatility", "funding_rate_stress"],
            warning_signals=["Extreme funding rates detected"],
            recommended_actions=["Reduce leverage", "Monitor closely"]
        )
        
        # Mock liquidation risk
        mock_risk = LiquidationRisk(
            symbol="BTCUSDT",
            exchange="binance",
            liquidation_probability=0.65,
            risk_level=LiquidationSeverity.HIGH,
            time_horizon_minutes=60,
            funding_rate_pressure=75.0,
            liquidity_risk=45.0,
            technical_weakness=55.0,
            support_levels=[44000.0, 43500.0, 43000.0],
            resistance_levels=[46000.0, 46500.0, 47000.0],
            current_price=45000.0,
            price_distance_to_risk=2.2,
            volume_profile_support=60.0,
            similar_events_count=3
        )
        
        # Mock cascade alert
        mock_cascade = CascadeAlert(
            alert_id="cascade_001",
            severity=LiquidationSeverity.CRITICAL,
            initiating_symbol="BTCUSDT",
            affected_symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            cascade_probability=0.75,
            estimated_total_liquidations=100000000.0,
            price_impact_range={"BTCUSDT": -5.0, "ETHUSDT": -7.0, "ADAUSDT": -8.0},
            duration_estimate_minutes=45,
            overall_leverage=4.2,
            liquidity_adequacy=35.0,
            correlation_strength=0.85,
            immediate_actions=["Reduce all leveraged positions"],
            risk_mitigation=["Diversify holdings"],
            monitoring_priorities=["BTCUSDT", "ETHUSDT"]
        )
        
        # Configure mock methods
        detector.detect_liquidation_events = AsyncMock(return_value=[mock_event])
        detector.assess_market_stress = AsyncMock(return_value=mock_stress)
        detector.assess_liquidation_risk = AsyncMock(return_value=mock_risk)
        detector.detect_cascade_risk = AsyncMock(return_value=[mock_cascade])
        detector.historical_events = [mock_event]
        detector.active_monitors = {}
        detector.exchange_manager = Mock()
        detector.exchange_manager.exchanges = {"binance": Mock()}
        
        return detector
    
    @pytest.fixture
    def client(self, mock_liquidation_detector):
        """Test client with mocked dependencies."""
        from src.main import app
        
        # Override dependency
        async def get_mock_detector():
            return mock_liquidation_detector
        
        app.dependency_overrides[get_liquidation_detector] = get_mock_detector
        
        with TestClient(app) as client:
            yield client
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_detect_liquidation_events(self, client):
        """Test liquidation event detection endpoint."""
        response = client.post("/api/liquidation/detect", json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "exchanges": ["binance"],
            "sensitivity": 0.7,
            "lookback_minutes": 60
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "detected_events" in data
        assert "market_stress" in data
        assert "risk_assessments" in data
        assert "cascade_alerts" in data
        assert "analysis_timestamp" in data
        assert "detection_duration_ms" in data
        
        # Check event structure
        events = data["detected_events"]
        assert len(events) > 0
        event = events[0]
        assert event["symbol"] == "BTCUSDT"
        assert event["severity"] == "high"
        assert event["liquidation_type"] == "long_liquidation"
    
    def test_get_active_alerts(self, client):
        """Test active liquidation alerts endpoint."""
        response = client.get("/api/liquidation/alerts?min_severity=medium&limit=10")
        
        assert response.status_code == 200
        alerts = response.json()
        
        assert isinstance(alerts, list)
        if alerts:  # Check structure if alerts exist
            alert = alerts[0]
            assert "event_id" in alert
            assert "symbol" in alert
            assert "severity" in alert
            assert "confidence_score" in alert
    
    def test_get_market_stress_indicators(self, client):
        """Test market stress indicators endpoint."""
        response = client.get("/api/liquidation/stress-indicators")
        
        assert response.status_code == 200
        stress = response.json()
        
        assert "overall_stress_level" in stress
        assert "stress_score" in stress
        assert "volatility_stress" in stress
        assert "funding_rate_stress" in stress
        assert "liquidity_stress" in stress
        assert "active_risk_factors" in stress
        assert "warning_signals" in stress
        assert "recommended_actions" in stress
        
        assert stress["overall_stress_level"] == "high"
        assert isinstance(stress["stress_score"], (int, float))
    
    def test_get_cascade_risk_assessment(self, client):
        """Test cascade risk assessment endpoint."""
        response = client.get("/api/liquidation/cascade-risk?min_probability=0.5")
        
        assert response.status_code == 200
        cascades = response.json()
        
        assert isinstance(cascades, list)
        if cascades:
            cascade = cascades[0]
            assert "alert_id" in cascade
            assert "severity" in cascade
            assert "initiating_symbol" in cascade
            assert "affected_symbols" in cascade
            assert "cascade_probability" in cascade
            assert "estimated_total_liquidations" in cascade
    
    def test_get_symbol_liquidation_risk(self, client):
        """Test symbol-specific liquidation risk endpoint."""
        response = client.get("/api/liquidation/risk/BTCUSDT?time_horizon_minutes=60")
        
        assert response.status_code == 200
        risk = response.json()
        
        assert "symbol" in risk
        assert "liquidation_probability" in risk
        assert "risk_level" in risk
        assert "funding_rate_pressure" in risk
        assert "liquidity_risk" in risk
        assert "technical_weakness" in risk
        assert "support_levels" in risk
        assert "resistance_levels" in risk
        assert "current_price" in risk
        
        assert risk["symbol"] == "BTCUSDT"
        assert 0 <= risk["liquidation_probability"] <= 1
    
    def test_get_leverage_metrics(self, client, mock_liquidation_detector):
        """Test leverage metrics endpoint."""
        # Mock exchange methods
        mock_exchange = Mock()
        mock_exchange.fetch_funding_rate = AsyncMock(return_value={
            "fundingRate": 0.005,
            "fundingTimestamp": datetime.utcnow().timestamp() * 1000
        })
        mock_exchange.fetch_market = AsyncMock(return_value={
            "limits": {"leverage": {"max": 125}}
        })
        mock_exchange.fetch_open_interest = AsyncMock(return_value={
            "openInterestAmount": 1000000000
        })
        
        mock_liquidation_detector.exchange_manager.exchanges = {"binance": mock_exchange}
        
        response = client.get("/api/liquidation/leverage-metrics/BTCUSDT")
        
        assert response.status_code == 200
        metrics = response.json()
        
        assert "symbol" in metrics
        assert "funding_rate" in metrics
        assert "funding_rate_8h_avg" in metrics
        assert "funding_rate_24h_avg" in metrics
        assert "open_interest" in metrics
        assert "max_leverage_available" in metrics
        assert "leverage_stress_score" in metrics
        
        assert metrics["symbol"] == "BTCUSDT"
    
    def test_setup_liquidation_monitoring(self, client):
        """Test liquidation monitoring setup endpoint."""
        response = client.post("/api/liquidation/monitor", json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "exchanges": ["binance"],
            "sensitivity_level": 0.8,
            "alert_threshold": "medium",
            "webhook_url": "https://webhook.example.com"
        })
        
        assert response.status_code == 200
        result = response.json()
        
        assert "monitor_id" in result
        assert "status" in result
        assert "message" in result
        assert result["status"] == "monitoring_started"
    
    def test_stop_liquidation_monitoring(self, client, mock_liquidation_detector):
        """Test stopping liquidation monitoring."""
        # Setup a monitor first
        monitor_id = "test_monitor_123"
        mock_liquidation_detector.active_monitors[monitor_id] = {"test": "data"}
        
        response = client.delete(f"/api/liquidation/monitor/{monitor_id}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "monitoring_stopped"
        assert monitor_id not in mock_liquidation_detector.active_monitors
    
    def test_get_liquidation_history(self, client):
        """Test liquidation history endpoint."""
        response = client.get("/api/liquidation/history/BTCUSDT?days_back=7&limit=50")
        
        assert response.status_code == 200
        history = response.json()
        
        assert isinstance(history, list)
        if history:
            event = history[0]
            assert "event_id" in event
            assert "symbol" in event
            assert "timestamp" in event
            assert event["symbol"] == "BTCUSDT"
    
    def test_invalid_symbol_risk_assessment(self, client, mock_liquidation_detector):
        """Test error handling for invalid symbol."""
        # Configure mock to raise exception
        mock_liquidation_detector.assess_liquidation_risk.side_effect = Exception("Symbol not found")
        
        response = client.get("/api/liquidation/risk/INVALID")
        
        assert response.status_code == 500
        assert "Risk assessment failed" in response.json()["detail"]
    
    def test_detection_with_empty_symbols(self, client):
        """Test detection with empty symbol list."""
        response = client.post("/api/liquidation/detect", json={
            "symbols": [],
            "sensitivity": 0.7,
            "lookback_minutes": 60
        })
        
        assert response.status_code == 422  # Validation error for empty list
    
    def test_invalid_sensitivity_parameter(self, client):
        """Test invalid sensitivity parameter."""
        response = client.post("/api/liquidation/detect", json={
            "symbols": ["BTCUSDT"],
            "sensitivity": 1.5,  # Invalid - should be 0-1
            "lookback_minutes": 60
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_monitoring_with_invalid_threshold(self, client):
        """Test monitoring setup with invalid threshold."""
        response = client.post("/api/liquidation/monitor", json={
            "symbols": ["BTCUSDT"],
            "alert_threshold": "invalid_severity"  # Invalid enum value
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_stop_nonexistent_monitor(self, client):
        """Test stopping non-existent monitor."""
        response = client.delete("/api/liquidation/monitor/nonexistent_id")
        
        assert response.status_code == 404
        assert "Monitor ID not found" in response.json()["detail"]

@pytest.mark.asyncio
class TestLiquidationDetectorEngine:
    """Test the core liquidation detection engine."""
    
    @pytest.fixture
    async def mock_exchange_manager(self):
        """Mock exchange manager for testing."""
        manager = Mock()
        exchange = Mock()
        
        # Mock OHLCV data
        exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1640995200000, 45000, 45500, 44800, 45200, 1000000],
            [1640998800000, 45200, 45600, 45000, 45400, 5000000],  # Volume spike
            [1641002400000, 45400, 45300, 43000, 43500, 8000000],  # Liquidation event
        ])
        
        # Mock order book
        exchange.fetch_order_book = AsyncMock(return_value={
            "bids": [[45000, 10], [44950, 15], [44900, 20]],
            "asks": [[45100, 8], [45150, 12], [45200, 18]]
        })
        
        # Mock funding rate
        exchange.fetch_funding_rate = AsyncMock(return_value={
            "fundingRate": 0.008  # High funding rate
        })
        
        # Mock trades
        exchange.fetch_trades = AsyncMock(return_value=[])
        
        manager.exchanges = {"binance": exchange}
        return manager
    
    @pytest.fixture
    def liquidation_detector(self, mock_exchange_manager):
        """Liquidation detector with mocked exchange manager."""
        return LiquidationDetectionEngine(mock_exchange_manager)
    
    async def test_detect_liquidation_events_basic(self, liquidation_detector):
        """Test basic liquidation event detection."""
        events = await liquidation_detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.7,
            lookback_minutes=60
        )
        
        assert isinstance(events, list)
        # Should detect the volume spike + price drop pattern
        
    async def test_market_stress_assessment(self, liquidation_detector):
        """Test market stress assessment."""
        stress = await liquidation_detector.assess_market_stress(
            symbols=["BTCUSDT", "ETHUSDT"],
            exchanges=["binance"]
        )
        
        assert isinstance(stress, MarketStressIndicator)
        assert hasattr(stress, "overall_stress_level")
        assert hasattr(stress, "stress_score")
        assert 0 <= stress.stress_score <= 100
    
    async def test_liquidation_risk_assessment(self, liquidation_detector):
        """Test liquidation risk assessment for specific symbol."""
        risk = await liquidation_detector.assess_liquidation_risk(
            symbol="BTCUSDT",
            exchange_id="binance",
            time_horizon_minutes=60
        )
        
        assert isinstance(risk, LiquidationRisk)
        assert risk.symbol == "BTCUSDT"
        assert 0 <= risk.liquidation_probability <= 1
        assert isinstance(risk.support_levels, list)
        assert isinstance(risk.resistance_levels, list)
    
    async def test_cascade_risk_detection(self, liquidation_detector):
        """Test cascade liquidation risk detection."""
        alerts = await liquidation_detector.detect_cascade_risk(
            symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            exchanges=["binance"]
        )
        
        assert isinstance(alerts, list)
        # Cascade detection depends on multiple high-risk symbols
    
    async def test_insufficient_data_handling(self, liquidation_detector, mock_exchange_manager):
        """Test handling of insufficient market data."""
        # Mock exchange to return insufficient data
        exchange = mock_exchange_manager.exchanges["binance"]
        exchange.fetch_ohlcv = AsyncMock(return_value=[])
        
        events = await liquidation_detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.7,
            lookback_minutes=60
        )
        
        # Should handle gracefully and return empty list
        assert isinstance(events, list)
    
    async def test_sensitivity_adjustment(self, liquidation_detector):
        """Test that sensitivity affects detection results."""
        # High sensitivity - should detect more events
        high_sens_events = await liquidation_detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.3,  # Low threshold
            lookback_minutes=60
        )
        
        # Low sensitivity - should detect fewer events
        low_sens_events = await liquidation_detector.detect_liquidation_events(
            symbols=["BTCUSDT"],
            exchanges=["binance"],
            sensitivity=0.9,  # High threshold
            lookback_minutes=60
        )
        
        # High sensitivity should detect >= low sensitivity events
        assert len(high_sens_events) >= len(low_sens_events) 