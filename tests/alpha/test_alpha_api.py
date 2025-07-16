import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime

# Python 3.7 compatible AsyncMock
class AsyncMock(Mock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

# Mock the dependencies at module level
mock_exchange_manager = Mock()
mock_exchange = Mock()
mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
    [1640995200000, 47000, 47500, 46800, 47200, 1000],
    [1640998800000, 47200, 47600, 47000, 47400, 1200],
])
mock_exchange.fetch_order_book = AsyncMock(return_value={
    'bids': [[47300, 10], [47200, 15]],
    'asks': [[47400, 8], [47500, 12]]
})
mock_exchange.fetch_ticker = AsyncMock(return_value={
    'last': 47300,
    'quoteVolume': 2000000,
    'baseVolume': 42.3
})
mock_exchange.load_markets = AsyncMock(return_value={
            'BTCUSDT': {},
        'ETHUSDT': {},
        'SOLUSDT': {}
})
mock_exchange_manager.exchanges = {'binance': mock_exchange}

@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    
    with patch('src.api.routes.alpha.get_exchange_manager') as mock_get_em:
        mock_get_em.return_value = mock_exchange_manager
        
        # Import after patching
        from src.main import app
        
        # Set up app state
        app.state.exchange_manager = mock_exchange_manager
        
        return TestClient(app)

def test_scan_alpha_opportunities(client):
    """Test the main alpha scanning endpoint."""
    
    with patch('src.core.analysis.confluence.ConfluenceAnalyzer.analyze') as mock_analyze:
        # Mock confluence analysis result
        mock_analyze.return_value = {
            'score': 75.0,
            'signal': 'BULLISH',
            'reliability': 0.85,
            'components': {
                'technical': {'score': 80.0},
                'volume': {'score': 70.0},
                'sentiment': {'score': 60.0}
            }
        }
        
        response = client.post("/api/alpha/scan", json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h"],
            "min_score": 50.0,
            "max_results": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "opportunities" in data
        assert "scan_timestamp" in data
        assert "scan_duration_ms" in data
        assert isinstance(data["opportunities"], list)

def test_get_top_opportunities(client):
    """Test the top opportunities endpoint."""
    
    with patch('src.core.analysis.confluence.ConfluenceAnalyzer.analyze') as mock_analyze:
        mock_analyze.return_value = {
            'score': 85.0,
            'signal': 'BULLISH',
            'reliability': 0.90,
            'components': {
                'technical': {'score': 90.0},
                'volume': {'score': 80.0},
                'sentiment': {'score': 85.0}
            }
        }
        
        response = client.get("/api/alpha/opportunities/top?limit=5&min_score=60")
        
        assert response.status_code == 200
        opportunities = response.json()
        
        assert isinstance(opportunities, list)

def test_get_symbol_opportunity(client):
    """Test symbol-specific analysis endpoint."""
    
    with patch('src.core.analysis.confluence.ConfluenceAnalyzer.analyze') as mock_analyze:
        mock_analyze.return_value = {
            'score': 70.0,
            'signal': 'BULLISH',
            'reliability': 0.75,
            'components': {
                'technical': {'score': 75.0},
                'volume': {'score': 65.0},
                'sentiment': {'score': 70.0}
            }
        }
        
        response = client.get("/api/alpha/opportunities/BTCUSDT")
        
        assert response.status_code == 200
        opportunity = response.json()
        
        if opportunity:  # May be None if score too low
            assert "symbol" in opportunity
            assert "score" in opportunity
            assert "strength" in opportunity

def test_scan_status(client):
    """Test scan status endpoint."""
    
    response = client.get("/api/alpha/scan/status")
    
    assert response.status_code == 200
    status = response.json()
    
    assert "status" in status
    assert "scanner_version" in status
    assert "supported_exchanges" in status

def test_alpha_scanner_health(client):
    """Test health check endpoint."""
    
    response = client.get("/api/alpha/health")
    
    assert response.status_code == 200
    health = response.json()
    
    assert "status" in health
    assert "timestamp" in health

def test_scan_with_invalid_data(client):
    """Test scanning with invalid request data."""
    
    response = client.post("/api/alpha/scan", json={
        "min_score": -10,  # Invalid score
        "max_results": 1000  # Too many results
    })
    
    # Should return 422 for validation error
    assert response.status_code == 422

def test_scan_with_no_opportunities(client):
    """Test scanning when no opportunities meet criteria."""
    
    with patch('src.core.analysis.confluence.ConfluenceAnalyzer.analyze') as mock_analyze:
        # Mock low score that doesn't meet threshold
        mock_analyze.return_value = {
            'score': 30.0,
            'signal': 'NEUTRAL',
            'reliability': 0.40,
            'components': {
                'technical': {'score': 35.0},
                'volume': {'score': 25.0},
                'sentiment': {'score': 30.0}
            }
        }
        
        response = client.post("/api/alpha/scan", json={
            "symbols": ["BTCUSDT"],
            "min_score": 80.0,  # High threshold
            "max_results": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty opportunities list
        assert len(data["opportunities"]) == 0 